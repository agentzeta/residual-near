// Residual core for the browser: the same classifier, sampler and pinned-block reads as the Python
// package (residual/core.py, residual/sample.py, residual/rpc.py). tests/web/parity.test.mjs checks it
// against the Python classifier's truth table and the demo fixture.

export const STATES = ['CLASSICAL_ONLY', 'INCOMPLETE_WEAKEST_LINK', 'COMPLETE', 'PQ_FUNCTION_ONLY', 'UNDETERMINED'];
const KEY_FORMS = [['ml-dsa-65-hash:', 'PQ', 32], ['ed25519:', 'CLASSICAL', 32], ['secp256k1:', 'CLASSICAL', 64]];
const FULL_PQ_PREFIX = 'ml-dsa-65:';
const ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

export const ENDPOINTS = {
  mainnet: ['https://rpc.mainnet.fastnear.com', 'https://free.rpc.fastnear.com', 'https://rpc.mainnet.near.org'],
  testnet: ['https://rpc.testnet.fastnear.com', 'https://rpc.testnet.near.org'],
};

export function b58decode(text) {
  if (!text) throw new Error('empty base58 string');
  let n = 0n;
  for (const ch of text) {
    const i = ALPHABET.indexOf(ch);
    if (i < 0) throw new Error('invalid base58 character');
    n = n * 58n + BigInt(i);
  }
  const bytes = [];
  while (n > 0n) { bytes.unshift(Number(n % 256n)); n /= 256n; }
  let zeros = 0;
  while (zeros < text.length && text[zeros] === '1') zeros++;
  return new Uint8Array([...new Array(zeros).fill(0), ...bytes]);
}

export function inspectKey(entry) {
  if (!entry || typeof entry !== 'object' || typeof entry.public_key !== 'string') return ['UNKNOWN', 'MISSING_PUBLIC_KEY'];
  const key = entry.public_key;
  const ak = entry.access_key;
  const perm = ak && typeof ak === 'object' ? ak.permission : undefined;
  let access;
  if (perm === 'FullAccess') access = 'FULL';
  else if (perm && typeof perm === 'object' && perm.FunctionCall && typeof perm.FunctionCall === 'object') access = 'FUNCTION';
  else return ['UNKNOWN', 'UNRECOGNIZED_PERMISSION'];
  for (const [prefix, kind, size] of KEY_FORMS) {
    if (key.startsWith(prefix)) {
      let decoded;
      try { decoded = b58decode(key.slice(prefix.length)); } catch { return ['UNKNOWN', 'MALFORMED_KEY']; }
      if (decoded.length !== size) return ['UNKNOWN', 'WRONG_KEY_LENGTH'];
      return [kind + '_' + access, null];
    }
  }
  if (key.startsWith(FULL_PQ_PREFIX)) return ['UNKNOWN', 'UNEXPECTED_FULL_PQ_KEY'];
  return ['UNKNOWN', 'UNSUPPORTED_KEY_TYPE'];
}

export function classifyAccount(accountId, entries, status = 'OK') {
  const base = { account_id: accountId, status, key_types: [], notes: [] };
  if (status !== 'OK') {
    return { ...base, state: 'UNDETERMINED', reason_code: status === 'ACCOUNT_NOT_FOUND' ? 'ACCOUNT_NOT_FOUND' : 'RPC_ERROR',
      reason: 'RPC read unavailable; kept in the denominator as unresolved' };
  }
  if (!Array.isArray(entries)) {
    return { ...base, state: 'UNDETERMINED', reason_code: 'MALFORMED_RESPONSE', reason: 'Access-key list missing or malformed' };
  }
  const inspected = entries.map(inspectKey);
  const types = inspected.map((x) => x[0]);
  const issues = [...new Set(inspected.map((x) => x[1]).filter(Boolean))].sort();
  base.key_types = types;
  if (issues.length) base.notes = issues;
  let state, code = null;
  if (!types.length) { state = 'UNDETERMINED'; code = 'NO_ACCESS_KEYS'; }
  else if (types.includes('UNKNOWN')) { state = 'UNDETERMINED'; code = 'UNRECOGNIZED_KEY'; }
  else if (types.includes('CLASSICAL_FULL') && types.includes('PQ_FULL')) state = 'INCOMPLETE_WEAKEST_LINK';
  else if (types.includes('CLASSICAL_FULL')) state = 'CLASSICAL_ONLY';
  else if (types.includes('PQ_FULL')) state = 'COMPLETE';
  else if (types.includes('PQ_FUNCTION')) state = 'PQ_FUNCTION_ONLY';
  else { state = 'UNDETERMINED'; code = 'CLASSICAL_FUNCTION_ONLY'; }
  if ((state === 'COMPLETE' || state === 'PQ_FUNCTION_ONLY') && types.includes('CLASSICAL_FUNCTION')) base.notes = [...base.notes, 'RESIDUAL_CLASSICAL_FUNCTION_KEYS'];
  if (code === 'UNRECOGNIZED_KEY' && types.includes('CLASSICAL_FULL')) base.notes = [...base.notes, 'CLASSICAL_FULL_ACCESS_OBSERVED'];
  return { ...base, state, reason_code: code, reason: 'Observed access-key layer only; not a claim of quantum safety' };
}

export function wilson(k, n, z = 1.959963984540054) {
  if (!n) return null;
  const p = k / n, den = 1 + z * z / n;
  const c = (p + z * z / (2 * n)) / den;
  const h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}

export function summarize(accounts, randomDraw = false) {
  const counts = Object.fromEntries(STATES.map((s) => [s, 0]));
  const reasons = {};
  for (const a of accounts) {
    counts[a.state] += 1;
    if (a.state === 'UNDETERMINED') { const c = a.reason_code || 'UNSPECIFIED'; reasons[c] = (reasons[c] || 0) + 1; }
  }
  const n = accounts.length, resolved = n - counts.UNDETERMINED;
  const pq = accounts.filter((a) => a.key_types.includes('PQ_FULL') || a.key_types.includes('PQ_FUNCTION')).length;
  const classical = accounts.filter((a) => a.key_types.includes('CLASSICAL_FULL')).length;
  const s = { requested: n, resolved, unresolved: counts.UNDETERMINED, unresolved_by_reason: reasons, counts,
    pq_key_present: pq, classical_full_access_present: classical };
  if (randomDraw) {
    s.interval_95 = { pq_key_present_share_of_resolved: wilson(pq, resolved),
      classical_full_access_share_of_resolved: wilson(classical, resolved),
      complete_share_of_resolved: wilson(counts.COMPLETE, resolved) };
  }
  return s;
}

async function sha256hex(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// Same ordering as residual/sample.py seeded_draw: sort by sha256(seed + "\n" + id).
export async function seededDraw(ids, seed, n) {
  const keyed = await Promise.all(ids.map(async (id) => [await sha256hex(seed + '\n' + id), id]));
  keyed.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  return keyed.slice(0, n).map((x) => x[1]);
}

export class RPCError extends Error {
  constructor(message, code = 'RPC_ERROR') { super(message); this.code = code; }
}

function errorCode(err) {
  const text = (typeof err === 'string' ? err : JSON.stringify(err)).toLowerCase();
  return text.includes('unknown_account') || text.includes('does not exist while viewing') ? 'ACCOUNT_NOT_FOUND' : 'RPC_ERROR';
}

export function makeRpc(endpoint, { retries = 3, fetchImpl = (...a) => globalThis.fetch(...a), onCall, backoffMs = 400 } = {}) {
  const RETRYABLE = [408, 425, 429, 500, 502, 503, 504];
  let id = 0;
  return async function rpc(method, params) {
    let last;
    for (let attempt = 0; attempt <= retries; attempt++) {
      if (attempt) await new Promise((r) => setTimeout(r, backoffMs * 2 ** (attempt - 1)));
      onCall && onCall(method);
      let res, body;
      try {
        res = await fetchImpl(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jsonrpc: '2.0', id: 'residual-' + (++id), method, params }) });
      } catch (e) {
        last = new RPCError('network: ' + String((e && e.message) || e).slice(0, 160));
        continue;
      }
      if (!res.ok) {
        last = new RPCError('HTTP ' + res.status);
        if (RETRYABLE.includes(res.status)) continue;
        throw last;
      }
      try { body = await res.json(); } catch { last = new RPCError('invalid JSON'); continue; }
      if (body.error) throw new RPCError(JSON.stringify(body.error).slice(0, 300), errorCode(body.error));
      if (!('result' in body)) throw new RPCError('missing result');
      const inner = body.result;
      if (inner && typeof inner.error === 'string') throw new RPCError(inner.error.slice(0, 300), errorCode(inner.error));
      return inner;
    }
    throw last;
  };
}

export function blockMeta(b) {
  const h = (b && b.header) || {};
  if (!h.hash || h.height == null) throw new RPCError('invalid block header');
  return { hash: h.hash, height: h.height, prev_hash: h.prev_hash, timestamp_nanosec: h.timestamp_nanosec,
    latest_protocol_version: h.latest_protocol_version };
}

export async function networkInfo(rpc) {
  const s = await rpc('status', []);
  return { chain_id: s.chain_id, protocol_version: s.protocol_version, node_version: (s.version || {}).version };
}

export async function finalizedBlock(rpc) {
  return blockMeta(await rpc('block', { finality: 'final' }));
}

export async function readAccount(rpc, accountId, block) {
  try {
    const r = await rpc('query', { request_type: 'view_access_key_list', account_id: accountId, block_id: block.hash });
    if (r.block_hash && r.block_hash !== block.hash) throw new RPCError('inconsistent block hash');
    if (!Array.isArray(r.keys)) throw new RPCError('missing keys');
    return { account_id: accountId, keys: r.keys, status: 'OK' };
  } catch (e) {
    return { account_id: accountId, keys: null, status: e.code === 'ACCOUNT_NOT_FOUND' ? 'ACCOUNT_NOT_FOUND' : 'RPC_ERROR',
      error: String(e.message).slice(0, 300) };
  }
}

function* actions(tx) {
  for (const a of tx.actions || []) {
    if (a && typeof a === 'object' && a.Delegate && typeof a.Delegate === 'object') {
      const da = a.Delegate.delegate_action || {};
      for (const inner of da.actions || []) yield [inner, da.receiver_id, da.sender_id];
    } else yield [a, tx.receiver_id, tx.signer_id];
  }
}

export function pqEnrollments(tx, height) {
  const found = [];
  for (const [action, receiver, signer] of actions(tx)) {
    const add = action && typeof action === 'object' ? action.AddKey : null;
    if (add && typeof add === 'object' && String(add.public_key || '').startsWith(FULL_PQ_PREFIX)) {
      found.push({ account_id: receiver, signer_id: signer, tx_hash: tx.hash, block_height: height });
    }
  }
  return found;
}

export async function windowFrame(rpc, head, nBlocks, onProgress) {
  const signers = new Set(), enrollments = [];
  const stats = { blocks_requested: nBlocks, blocks_read: 0, block_failures: 0, chunks_read: 0, chunk_failures: 0, transactions: 0 };
  let cursor = head.hash, lowest = head.height;
  for (let i = 0; i < nBlocks; i++) {
    let block, meta;
    try { block = await rpc('block', { block_id: cursor }); meta = blockMeta(block); } catch { stats.block_failures++; break; }
    stats.blocks_read++;
    lowest = meta.height;
    const fresh = (block.chunks || []).filter((c) => c.height_included === meta.height);
    const bodies = await Promise.all(fresh.map((c) => rpc('chunk', { chunk_id: c.chunk_hash }).then((b) => b, () => null)));
    for (const body of bodies) {
      if (!body) { stats.chunk_failures++; continue; }
      stats.chunks_read++;
      for (const tx of body.transactions || []) {
        stats.transactions++;
        if (typeof tx.signer_id === 'string') signers.add(tx.signer_id);
        enrollments.push(...pqEnrollments(tx, meta.height));
      }
    }
    onProgress && onProgress({ ...stats, distinct_signers: signers.size });
    cursor = meta.prev_hash;
    if (!cursor) break;
  }
  const frame = { kind: 'distinct transaction signers in a block window', head_height: head.height, head_hash: head.hash,
    lowest_height: lowest, distinct_signers: signers.size, pq_enrollment_events: enrollments.length,
    complete: stats.blocks_read === nBlocks && !stats.chunk_failures, ...stats };
  return { signers: [...signers].sort(), enrollments, frame };
}

// Read accounts a few at a time so a public endpoint is not flooded.
export async function readAll(rpc, ids, block, concurrency = 4, onEach) {
  const out = new Array(ids.length);
  let next = 0;
  async function worker() {
    while (next < ids.length) {
      const i = next++;
      out[i] = await readAccount(rpc, ids[i], block);
      onEach && onEach(i, out[i]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, ids.length) }, worker));
  return out;
}
