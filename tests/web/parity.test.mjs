// Run: node --test tests/web/
// Checks the browser classifier (site/residual.js) against the Python classifier's truth table,
// the demo fixture, the Python seeded draw, and a mock NEAR RPC.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import * as R from '../../site/residual.js';

const root = new URL('../../', import.meta.url);
const read = (p) => JSON.parse(readFileSync(new URL(p, root), 'utf8'));
const ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
function b58encode(bytes) {
  let n = 0n; for (const b of bytes) n = n * 256n + BigInt(b);
  let out = ''; while (n > 0n) { out = ALPHABET[Number(n % 58n)] + out; n /= 58n; }
  let z = 0; while (z < bytes.length && bytes[z] === 0) z++;
  return '1'.repeat(z) + out;
}
const KEY = {
  CLASSICAL: 'ed25519:' + b58encode(Uint8Array.from({ length: 32 }, (_, i) => i + 1)),
  PQ: 'ml-dsa-65-hash:' + b58encode(Uint8Array.from({ length: 32 }, (_, i) => i + 2)),
};
function entryFor(type) {
  if (type === 'UNKNOWN') return { public_key: 'rsa:abc', access_key: { permission: 'FullAccess' } };
  const [kind, access] = type.split('_');
  return { public_key: KEY[kind], access_key: { permission: access === 'FULL' ? 'FullAccess' : { FunctionCall: { receiver_id: 'x.near', method_names: [] } } } };
}

test('matches the formal model truth table on every row', () => {
  const table = read('formal/truth_table.json');
  assert.ok(table.length >= 128);
  for (const row of table) {
    const got = row.status === 'OK'
      ? R.classifyAccount('a.near', row.key_types.map(entryFor))
      : R.classifyAccount('a.near', null, row.status);
    assert.equal(got.state, row.state, JSON.stringify(row));
  }
});

test('demo fixture gives the same summary as the Python CLI', () => {
  const fx = read('fixtures/demo.json');
  const accounts = fx.accounts.map((a) => R.classifyAccount(a.account_id, a.keys, a.status || 'OK'));
  const s = R.summarize(accounts);
  assert.equal(s.pq_key_present, 4);
  assert.equal(s.classical_full_access_present, 3);
  assert.deepEqual(s.counts, { CLASSICAL_ONLY: 1, INCOMPLETE_WEAKEST_LINK: 2, COMPLETE: 1, PQ_FUNCTION_ONLY: 1, UNDETERMINED: 1 });
});

test('key checks: lengths, malformed base58, full ML-DSA key in a list', () => {
  assert.equal(R.inspectKey({ public_key: 'ed25519:' + b58encode(new Uint8Array(31).fill(7)), access_key: { permission: 'FullAccess' } })[1], 'WRONG_KEY_LENGTH');
  assert.equal(R.inspectKey({ public_key: 'ed25519:0OIl', access_key: { permission: 'FullAccess' } })[1], 'MALFORMED_KEY');
  assert.equal(R.inspectKey({ public_key: 'ml-dsa-65:' + b58encode(new Uint8Array(1952)), access_key: { permission: 'FullAccess' } })[1], 'UNEXPECTED_FULL_PQ_KEY');
  assert.deepEqual([...R.b58decode('1112')], [0, 0, 0, 1]);
});

test('seeded draw orders exactly like residual/sample.py', async () => {
  const ids = ['alice.near', 'bob.near', 'carol.near', 'dave.near', 'erin.near'];
  const seed = 'H3';
  const py = [...ids].sort((a, b) => {
    const ha = createHash('sha256').update(seed + '\n' + a).digest('hex');
    const hb = createHash('sha256').update(seed + '\n' + b).digest('hex');
    return ha < hb ? -1 : 1;
  }).slice(0, 3);
  assert.deepEqual(await R.seededDraw(ids, seed, 3), py);
});

test('end to end against a mock RPC: pinned reads, delegate enrollments, failures kept', async () => {
  const keys = { 'alice.near': [entryFor('CLASSICAL_FULL')], 'bob.near': [entryFor('CLASSICAL_FULL'), entryFor('PQ_FULL')] };
  const blocks = {
    H3: { header: { hash: 'H3', height: 103, prev_hash: 'H2' }, chunks: [{ chunk_hash: 'C3', height_included: 103 }] },
    H2: { header: { hash: 'H2', height: 102, prev_hash: 'H1' }, chunks: [{ chunk_hash: 'C2', height_included: 102 }, { chunk_hash: 'OLD', height_included: 99 }] },
  };
  const chunks = {
    C3: { transactions: [{ hash: 'T1', signer_id: 'alice.near', receiver_id: 'x.near', actions: [] }, { hash: 'T2', signer_id: 'ghost.near', actions: [] }] },
    C2: { transactions: [{ hash: 'T3', signer_id: 'relayer.near', receiver_id: 'bob.near', actions: [{ Delegate: { delegate_action: {
      sender_id: 'bob.near', receiver_id: 'bob.near', actions: [{ AddKey: { public_key: 'ml-dsa-65:abc', access_key: { permission: 'FullAccess' } } }] } } }] }] },
  };
  let first429 = true;
  const fetchImpl = async (_url, init) => {
    const { method, params } = JSON.parse(init.body);
    const json = (o) => ({ ok: true, status: 200, json: async () => o });
    if (method === 'status' && first429) { first429 = false; return { ok: false, status: 429 }; }
    if (method === 'status') return json({ result: { chain_id: 'mainnet', protocol_version: 85, version: { version: '2.13.0' } } });
    if (method === 'block') return json({ result: blocks[params.finality ? 'H3' : params.block_id] || null });
    if (method === 'chunk') return json({ result: chunks[params.chunk_id] });
    if (params.block_id !== 'H3') return json({ error: { name: 'UNPINNED' } });
    if (keys[params.account_id]) return json({ result: { block_hash: 'H3', keys: keys[params.account_id] } });
    return json({ error: { cause: { name: 'UNKNOWN_ACCOUNT' } } });
  };
  const rpc = R.makeRpc('https://mock', { fetchImpl, backoffMs: 1 });
  const net = await R.networkInfo(rpc);
  assert.equal(net.chain_id, 'mainnet');
  const head = await R.finalizedBlock(rpc);
  const { signers, enrollments, frame } = await R.windowFrame(rpc, head, 2);
  assert.deepEqual(signers, ['alice.near', 'ghost.near', 'relayer.near']);
  assert.equal(enrollments.length, 1);
  assert.equal(enrollments[0].account_id, 'bob.near');
  assert.equal(frame.complete, true);
  const recs = await R.readAll(rpc, ['alice.near', 'bob.near', 'ghost.near'], head);
  const states = recs.map((r) => R.classifyAccount(r.account_id, r.keys, r.status).state);
  assert.deepEqual(states, ['CLASSICAL_ONLY', 'INCOMPLETE_WEAKEST_LINK', 'UNDETERMINED']);
  assert.equal(recs[2].status, 'ACCOUNT_NOT_FOUND');
});
