import * as R from './residual.js';

const $ = (id) => document.getElementById(id);
const esc = (x) => String(x == null ? '' : x).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (x) => (x == null ? '–' : (100 * x).toFixed(1) + '%');
const params = new URLSearchParams(location.search);
const RPC_OVERRIDE = params.get('rpc'); // for local testing only; the public page always uses public NEAR RPC
if (RPC_OVERRIDE) {
  const b = document.createElement('div');
  b.className = 'testbanner';
  b.textContent = 'Test mode: reading from ' + RPC_OVERRIDE + ', not a public NEAR endpoint. Results are not NEAR data.';
  document.body.prepend(b);
}
const LABEL = { CLASSICAL_ONLY: 'Classical only', INCOMPLETE_WEAKEST_LINK: 'Mixed PQ + classical', COMPLETE: 'PQ full access only',
  PQ_FUNCTION_ONLY: 'PQ function-call only', UNDETERMINED: 'Undetermined' };
const COLOR = { CLASSICAL_ONLY: '#3a4660', INCOMPLETE_WEAKEST_LINK: '#c27a35', COMPLETE: '#2fb39e', PQ_FUNCTION_ONLY: '#4a7fbf', UNDETERMINED: '#8a4b5e' };
const TYPE_LABEL = { CLASSICAL_FULL: 'Classical · full access', CLASSICAL_FUNCTION: 'Classical · function call', PQ_FULL: 'ML-DSA-65 · full access',
  PQ_FUNCTION: 'ML-DSA-65 · function call', UNKNOWN: 'Unrecognized' };
const VERDICT = {
  CLASSICAL_ONLY: 'No post-quantum key. A classical full-access key controls this account.',
  INCOMPLETE_WEAKEST_LINK: 'Has a post-quantum key, but a classical full-access key is still live. Migration is not finished.',
  COMPLETE: 'Post-quantum full access only. No classical full-access key is left at this block.',
  PQ_FUNCTION_ONLY: 'Only post-quantum function-call keys. No key here has full access.',
  UNDETERMINED: 'Could not be classified.',
};
const REASON = {
  ACCOUNT_NOT_FOUND: 'This account does not exist on the selected network.',
  RPC_ERROR: 'The RPC endpoint did not answer. Try again in a moment.',
  MALFORMED_RESPONSE: 'The RPC answer was not in the expected shape.',
  NO_ACCESS_KEYS: 'The account has no access keys (a locked account, often a contract).',
  UNRECOGNIZED_KEY: 'At least one key is of a type or length Residual does not recognize.',
  CLASSICAL_FUNCTION_ONLY: 'Only classical function-call keys, and no full-access key.',
};

// Connect to the first public endpoint that answers, and remember it per network.
const connections = {};
async function connect(network) {
  if (connections[network]) return connections[network];
  const list = RPC_OVERRIDE ? [RPC_OVERRIDE] : R.ENDPOINTS[network];
  let lastErr;
  for (const endpoint of list) {
    const rpc = R.makeRpc(endpoint, { retries: 2 });
    try {
      const net = await R.networkInfo(rpc);
      connections[network] = { endpoint, rpc, net };
      return connections[network];
    } catch (e) { lastErr = e; }
  }
  throw new Error('No NEAR RPC endpoint answered (' + (lastErr ? lastErr.message : 'unknown') + ').');
}

function shortKey(k) { return k.length > 40 ? k.slice(0, 26) + '…' + k.slice(-8) : k; }
function permission(entry) {
  const p = entry && entry.access_key && entry.access_key.permission;
  if (p === 'FullAccess') return 'Full access';
  if (p && p.FunctionCall) return 'Calls to ' + (p.FunctionCall.receiver_id || '?') + (p.FunctionCall.method_names && p.FunctionCall.method_names.length ? ' (' + p.FunctionCall.method_names.join(', ') + ')' : '');
  return 'Unknown';
}

function blockLine(conn, block) {
  return `<div class="meta"><span>${esc(conn.net.chain_id)} · protocol ${esc(conn.net.protocol_version)}</span><span>block ${esc(block.height)}</span><span>hash ${esc(block.hash)}</span><span>${esc(new URL(conn.endpoint).host)}</span></div>`;
}

async function checkAccount(accountId, network) {
  const out = $('check-out'), btn = $('check-btn');
  btn.disabled = true;
  out.innerHTML = '<p class="muted">Reading ' + esc(accountId) + ' on ' + esc(network) + '…</p>';
  try {
    const conn = await connect(network);
    const block = await R.finalizedBlock(conn.rpc);
    const rec = await R.readAccount(conn.rpc, accountId, block);
    const c = R.classifyAccount(rec.account_id, rec.keys, rec.status);
    const why = c.state === 'UNDETERMINED' ? ' ' + (REASON[c.reason_code] || '') : '';
    const rows = (rec.keys || []).map((k, i) => `<tr><td>${esc(TYPE_LABEL[c.key_types[i]] || c.key_types[i])}</td><td>${esc(permission(k))}</td><td class="key" title="${esc(k.public_key)}">${esc(shortKey(String(k.public_key)))}</td></tr>`).join('');
    const notes = c.notes.length ? `<p class="muted">Notes: ${c.notes.map(esc).join(', ')}</p>` : '';
    out.innerHTML = `<div class="result" data-state="${c.state}">
      <div><span class="pill ${c.state}">${LABEL[c.state]}</span></div>
      <p class="verdict">${esc(accountId)}: ${esc(VERDICT[c.state] + why)}</p>
      ${blockLine(conn, block)}
      ${rows ? `<div class="tbl"><table><thead><tr><th>Key type</th><th>Permission</th><th>Public key</th></tr></thead><tbody>${rows}</tbody></table></div>` : ''}
      ${notes}
      <p class="muted">Access-key layer at one block only. This is not a certificate of quantum safety.</p>
    </div>`;
    const u = new URL(location.href);
    u.searchParams.set('account', accountId);
    if (network !== 'mainnet') u.searchParams.set('network', network); else u.searchParams.delete('network');
    history.replaceState(null, '', u);
  } catch (e) {
    out.innerHTML = '<p class="error">' + esc(e.message) + '</p>';
  } finally {
    btn.disabled = false;
  }
}

function headline(summary, n) {
  const pqFull = summary.counts.COMPLETE + summary.counts.INCOMPLETE_WEAKEST_LINK;
  return `<div class="cards">
    <div class="card"><small>Accounts with a post-quantum key</small><strong>${summary.pq_key_present} / ${n}</strong><em>what a naive adoption count reports</em></div>
    <div class="card"><small>Still hold a classical full-access key</small><strong>${summary.classical_full_access_present} / ${n}</strong><em>includes ${summary.counts.INCOMPLETE_WEAKEST_LINK} that also have a PQ key</em></div>
    <div class="card"><small>Post-quantum full access only</small><strong>${summary.counts.COMPLETE} / ${n}</strong><em>of ${pqFull} with any PQ full-access key</em></div>
  </div>`;
}

function stateBar(summary, n) {
  const segs = R.STATES.filter((s) => summary.counts[s]).map((s) => `<span style="width:${(100 * summary.counts[s]) / n}%;background:${COLOR[s]}" title="${LABEL[s]}: ${summary.counts[s]}"></span>`).join('');
  const legend = R.STATES.map((s) => `<span><span class="pill ${s}">${LABEL[s]}</span> ${summary.counts[s]}</span>`).join('');
  return `<div class="statebar" role="img" aria-label="States">${segs}</div><div class="legend">${legend}</div>`;
}

function accountTable(accounts) {
  const rows = accounts.map((a) => `<tr><td><button type="button" class="link" data-check="${esc(a.account_id)}">${esc(a.account_id)}</button></td><td><span class="pill ${a.state}">${LABEL[a.state]}</span></td><td>${esc(a.reason_code || '')}</td></tr>`).join('');
  return `<div class="tbl"><table><thead><tr><th>Account</th><th>State</th><th>Reason</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

let lastReport = null;
async function runSample(nBlocks, size, network) {
  const out = $('sample-out'), prog = $('sample-progress'), btn = $('sample-btn');
  btn.disabled = true; out.innerHTML = ''; prog.hidden = false;
  const started = Date.now();
  try {
    prog.innerHTML = 'Connecting…';
    const conn = await connect(network);
    const head = await R.finalizedBlock(conn.rpc);
    const warnings = [];
    if (typeof conn.net.protocol_version === 'number' && conn.net.protocol_version < 85) warnings.push('Protocol version is below 85: ML-DSA-65 keys cannot exist at this block.');
    prog.innerHTML = `Pinned block <b>${head.height}</b>. Walking back ${nBlocks} blocks…`;
    const { signers, enrollments, frame } = await R.windowFrame(conn.rpc, head, nBlocks, (s) => {
      prog.innerHTML = `Pinned block <b>${head.height}</b> · blocks read <b>${s.blocks_read}/${nBlocks}</b> · chunks <b>${s.chunks_read}</b> · transactions <b>${s.transactions}</b> · distinct signers <b>${s.distinct_signers}</b>`;
    });
    if (!frame.complete) warnings.push(`Sampling frame incomplete: ${frame.block_failures} block and ${frame.chunk_failures} chunk read failures.`);
    if (!signers.length) throw new Error('No signers found in the block window.');
    const ids = await R.seededDraw(signers, head.hash, size);
    let done = 0;
    const records = await R.readAll(conn.rpc, ids, head, 4, () => {
      done++;
      prog.innerHTML = `Pinned block <b>${head.height}</b> · ${frame.distinct_signers} signers in blocks ${frame.lowest_height}–${frame.head_height} · reading accounts <b>${done}/${ids.length}</b>`;
    });
    const accounts = records.map((r) => R.classifyAccount(r.account_id, r.keys, r.status));
    const randomDraw = ids.length < signers.length;
    const summary = R.summarize(accounts, randomDraw);
    let enrollHtml = '<p class="muted">No account added an ML-DSA-65 key inside this window. Adoption is new; a wider window finds more.</p>';
    let cohort = null;
    const enrollers = [...new Set(enrollments.map((e) => e.account_id).filter((x) => typeof x === 'string'))].sort();
    if (enrollers.length) {
      const er = await R.readAll(conn.rpc, enrollers, head, 4);
      const ea = er.map((r) => R.classifyAccount(r.account_id, r.keys, r.status));
      const es = R.summarize(ea);
      cohort = { definition: 'Accounts that received an ML-DSA-65 AddKey inside the window, read at the same pinned block', events: enrollments, summary: es, accounts: ea };
      enrollHtml = `<p><b>${enrollers.length}</b> account${enrollers.length > 1 ? 's' : ''} added an ML-DSA-65 key inside this window. Of them, <b>${es.counts.INCOMPLETE_WEAKEST_LINK}</b> still hold a classical full-access key and <b>${es.counts.COMPLETE}</b> hold post-quantum full access only.</p>${accountTable(ea)}`;
    }
    const iv = summary.interval_95;
    lastReport = {
      schema: 'residual.near.report.v2-web',
      generated_at: new Date().toISOString(),
      provenance: { mode: 'LIVE_RPC_BROWSER', block: head, network: conn.net, endpoint: conn.endpoint,
        selection: `seeded random draw of ${ids.length} from ${signers.length} distinct transaction signers in blocks ${frame.lowest_height}-${frame.head_height}; seed = pinned block hash`,
        sampling_frame: frame },
      warnings, summary, accounts, observations: records, cohorts: cohort ? { pq_enrollers: cohort } : {},
    };
    const secs = Math.round((Date.now() - started) / 1000);
    prog.innerHTML = `Done in ${secs} s · ${conn.endpoint}`;
    out.innerHTML = `
      ${warnings.map((w) => `<p class="warn">${esc(w)}</p>`).join('')}
      <div class="result">
        ${blockLine(conn, head)}
        <p class="muted">${esc(lastReport.provenance.selection)}.</p>
        ${headline(summary, accounts.length)}
        ${stateBar(summary, accounts.length)}
        ${iv ? `<p class="muted">95% intervals for this frame only (recently active signers, not all accounts): PQ key present ${pct(iv.pq_key_present_share_of_resolved && iv.pq_key_present_share_of_resolved[0])}–${pct(iv.pq_key_present_share_of_resolved && iv.pq_key_present_share_of_resolved[1])} of resolved accounts.</p>` : ''}
        <h3>Accounts that enrolled an ML-DSA-65 key in this window</h3>
        ${enrollHtml}
        <h3>Sampled accounts</h3>
        ${accountTable(accounts)}
        <div class="actions"><button type="button" class="btn" id="dl">Download report (JSON)</button></div>
      </div>`;
    $('dl').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `residual-${network}-${head.height}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
  } catch (e) {
    prog.innerHTML = '<span class="error">' + esc(e.message) + '</span>';
  } finally {
    btn.disabled = false;
  }
}

async function loadSnapshot() {
  const out = $('snap-out');
  try {
    const res = await fetch('data/latest/report.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('none');
    const r = await res.json();
    const s = r.summary, pv = r.provenance, n = s.requested;
    const when = new Date(r.generated_at);
    const cohort = r.cohorts && r.cohorts.pq_enrollers;
    const synthetic = pv.mode === 'SYNTHETIC_FIXTURE' ? '<p class="warn">Synthetic fixture, not NEAR data.</p>' : '';
    out.innerHTML = `<div class="result">${synthetic}
      <div class="meta"><span>${esc((pv.network || {}).chain_id)} · protocol ${esc((pv.network || {}).protocol_version)}</span><span>block ${esc(pv.block.height)}</span><span>hash ${esc(pv.block.hash)}</span><span>${esc(when.toUTCString())}</span></div>
      <p class="muted">${esc(pv.selection)}.</p>
      ${(r.warnings || []).map((w) => `<p class="warn">${esc(w)}</p>`).join('')}
      ${headline(s, n)}
      ${stateBar(s, n)}
      ${cohort ? `<p><b>${cohort.summary.requested}</b> accounts added an ML-DSA-65 key in the window; <b>${cohort.summary.counts.INCOMPLETE_WEAKEST_LINK}</b> still hold a classical full-access key.</p>` : '<p class="muted">No ML-DSA-65 enrollments inside this snapshot\'s window.</p>'}
      <div class="actions"><a class="btn" href="data/latest/index.html">Full report</a><a class="btn" href="data/latest/report.json">report.json</a><a class="btn" href="data/latest/observations.json">Raw RPC data</a></div>
      <p class="muted">Report SHA-256 ${esc(r.report_sha256)}</p>
    </div>`;
  } catch {
    out.innerHTML = '<p class="muted">No snapshot has been published yet. It appears after the repository\'s "Deploy site" workflow runs.</p>';
  }
}

$('check-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const v = $('acct').value.trim().toLowerCase();
  if (v) checkAccount(v, $('net').value);
});
document.querySelectorAll('.chip[data-acct]').forEach((b) => b.addEventListener('click', () => {
  $('acct').value = b.dataset.acct; $('net').value = 'mainnet'; checkAccount(b.dataset.acct, 'mainnet');
}));
$('sample-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const w = Math.max(1, Math.min(120, parseInt($('win').value, 10) || 10));
  const n = Math.max(1, Math.min(300, parseInt($('size').value, 10) || 50));
  runSample(w, n, $('snet').value);
});
document.addEventListener('click', (e) => {
  const t = e.target.closest('[data-check]');
  if (!t) return;
  $('acct').value = t.dataset.check;
  $('net').value = $('snet').value;
  $('check').scrollIntoView();
  checkAccount(t.dataset.check, $('snet').value);
});

loadSnapshot();
if (params.get('account')) {
  const net = params.get('network') === 'testnet' ? 'testnet' : 'mainnet';
  $('acct').value = params.get('account'); $('net').value = net;
  checkAccount(params.get('account'), net);
}
