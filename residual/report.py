"""Static, self-contained HTML dashboard for a Residual report."""
import html, json

LABELS = {'CLASSICAL_ONLY': 'Classical only', 'INCOMPLETE_WEAKEST_LINK': 'Mixed PQ + classical',
          'COMPLETE': 'PQ full-access only', 'PQ_FUNCTION_ONLY': 'PQ function-call only',
          'UNDETERMINED': 'Unresolved'}

CSS = """:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#080f1e;color:#e7edf9;font:15px/1.5 system-ui,Arial,sans-serif}
.wrap{max-width:1160px;margin:auto;padding:40px 20px}header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.logo{font-weight:900;letter-spacing:.09em;font-size:22px}.tag{color:#7de1cf;background:#133c3d;padding:7px 12px;border-radius:30px;font-size:12px}
.banner{margin:22px 0 0;padding:12px 16px;border-radius:10px;background:#5a2a12;color:#ffd9bf;font-weight:600}
.warn{margin:12px 0 0;padding:10px 14px;border-radius:10px;background:#3b2f10;color:#ffe9a8}
h1{font-size:clamp(32px,5vw,58px);max-width:860px;line-height:1.07;margin:48px 0 16px}h2{margin:0 0 12px;font-size:20px}
.muted{color:#a6b6cf;max-width:800px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:30px 0}
.card{background:#111d33;border:1px solid #273a55;border-radius:14px;padding:20px}.card small{color:#a8bad0;display:block;font-size:12px}
.card strong{display:block;font-size:36px;margin-top:10px}.card em{font-style:normal;color:#a8bad0;font-size:12px}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.hero .card strong{font-size:44px;color:#7de1cf}
section{background:#101a2d;border:1px solid #26354d;border-radius:15px;padding:20px;margin:20px 0;overflow:auto}
table{width:100%;border-collapse:collapse;white-space:nowrap}td,th{text-align:left;padding:10px;border-bottom:1px solid #2a3951;font-size:14px}th{color:#a6b6cf}
.pill{padding:4px 9px;border-radius:6px;background:#34405c;font-size:12px}.COMPLETE{background:#126b5e}.INCOMPLETE_WEAKEST_LINK{background:#814b21}
.UNDETERMINED{background:#633445}.PQ_FUNCTION_ONLY{background:#2b4f7a}dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:0}
dt{color:#a6b6cf}dd{margin:0;overflow-wrap:anywhere}pre{font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere;color:#a7d6e5;max-height:420px;overflow:auto}
footer{color:#9bb0c8;padding:24px 0}"""


def _e(x):
    return html.escape('' if x is None else str(x))


def _pct(x):
    return '—' if x is None else '%.1f%%' % (100 * x)


def _interval(iv):
    return '—' if not iv else '%.1f–%.1f%%' % (100 * iv[0], 100 * iv[1])


def _rows(accounts):
    out = []
    for a in accounts:
        detail = ', '.join([a.get('reason_code') or ''] + a.get('notes', [])).strip(', ')
        out.append('<tr><td>%s</td><td><span class="pill %s">%s</span></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            _e(a['account_id']), _e(a['state']), _e(LABELS.get(a['state'], a['state'])),
            _e(', '.join(a['key_types'])), _e(a['status']), _e(detail)))
    return ''.join(out)


def _table(accounts):
    return ('<table><thead><tr><th>Account</th><th>Classification</th><th>Observed key types</th><th>Read status</th>'
            '<th>Reason / notes</th></tr></thead><tbody>' + _rows(accounts) + '</tbody></table>')


def render(report):
    s = report['summary']
    prov = report.get('provenance', {})
    block = prov.get('block') or {}
    network = prov.get('network') or {}
    frame = prov.get('sampling_frame')
    synthetic = prov.get('mode') == 'SYNTHETIC_FIXTURE'
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>Residual | NEAR Migration Observatory</title><style>' + CSS + '</style></head><body><div class="wrap">'
             '<header><div class="logo">◈ RESIDUAL <span style="color:#7de1cf">/ NEAR</span></div>'
             '<span class="tag">READ-ONLY OBSERVATORY</span></header>']
    if synthetic:
        parts.append('<div class="banner">SYNTHETIC DATA — fixture accounts for demonstrating every state. '
                     'Not NEAR mainnet measurements.</div>')
    for w in report.get('warnings', []):
        parts.append('<div class="warn">⚠ ' + _e(w) + '</div>')
    parts.append('<h1>Adding a post-quantum key is not the same as retiring classical authority.</h1>'
                 '<p class="muted">Access-key inventory at one pinned block. A classical full-access key remains an '
                 'independent way to authorize anything, even when an ML-DSA-65 key is present. This is not an '
                 'account-security certification.</p>')
    n = s['requested']
    parts.append('<div class="hero">'
                 '<div class="card"><small>Accounts with a PQ key present</small><strong>%d / %d</strong></div>'
                 '<div class="card"><small>Still hold a classical full-access key</small><strong>%d / %d</strong></div>'
                 '<div class="card"><small>Observed PQ-only full access</small><strong>%d / %d</strong></div></div>'
                 % (s['pq_key_present'], n, s['classical_full_access_present'], n, s['counts']['COMPLETE'], n))
    parts.append('<div class="grid">' + ''.join(
        '<div class="card"><small>%s</small><strong>%d</strong><em>%s</em></div>' % (
            _e(LABELS[k]), v, _e(k)) for k, v in s['counts'].items()) + '</div>')
    unresolved = ', '.join('%s: %d' % kv for kv in s.get('unresolved_by_reason', {}).items()) or 'none'
    parts.append('<section><h2>Denominators</h2><dl>'
                 '<dt>Requested</dt><dd>%d</dd><dt>Resolved</dt><dd>%d</dd><dt>Unresolved</dt><dd>%d (%s)</dd>'
                 '<dt>PQ-only share of resolved</dt><dd>%s</dd>'
                 '<dt>PQ-only share of accounts with a PQ full-access key</dt><dd>%s</dd></dl>'
                 % (n, s['resolved'], s['unresolved'], _e(unresolved), _pct(s.get('complete_share_of_resolved')),
                    _pct(s.get('complete_share_of_pq_full_access'))))
    iv = s.get('interval_95')
    if iv:
        parts.append('<p class="muted">95%% intervals (%s): PQ key present %s · classical full access %s · '
                     'PQ-only %s</p>' % (_e(iv['note']), _interval(iv['pq_key_present_share_of_resolved']),
                                         _interval(iv['classical_full_access_share_of_resolved']),
                                         _interval(iv['complete_share_of_resolved'])))
    parts.append('</section>')
    prov_rows = [('Mode', prov.get('mode')), ('Selection', prov.get('selection')),
                 ('Chain', network.get('chain_id')), ('Protocol version', block.get('latest_protocol_version') or network.get('protocol_version')),
                 ('Endpoint', prov.get('endpoint')), ('Block height', block.get('height')), ('Block hash', block.get('hash'))]
    if frame:
        prov_rows += [('Window', '%s–%s (%s of %s blocks read)' % (frame['lowest_height'], frame['head_height'],
                                                                    frame['blocks_read'], frame['blocks_requested'])),
                      ('Frame', '%s transactions, %s distinct signers, %s chunk failures' % (
                          frame['transactions'], frame['distinct_signers'], frame['chunk_failures'])),
                      ('ML-DSA-65 enrollments in window', frame['pq_enrollment_events'])]
    parts.append('<section><h2>Provenance</h2><dl>' + ''.join(
        '<dt>%s</dt><dd>%s</dd>' % (_e(k), _e(v if v is not None else '—')) for k, v in prov_rows) + '</dl></section>')
    enr = (report.get('cohorts') or {}).get('pq_enrollers')
    if enr:
        es = enr['summary']
        parts.append('<section><h2>Accounts that enrolled an ML-DSA-65 key in the window</h2>'
                     '<p class="muted">%s. Still holding a classical full-access key: <strong>%d of %d</strong>.</p>%s</section>'
                     % (_e(enr['definition']), es['classical_full_access_present'], es['requested'], _table(enr['accounts'])))
    parts.append('<section><h2>Account findings</h2>' + _table(report['accounts']) + '</section>')
    payload = json.dumps(report, indent=2).replace('<', '\\u003c')
    parts.append('<section><h2>Reproducibility manifest</h2><pre>' + html.escape(payload) + '</pre></section>'
                 '<footer>Residual reports only the observed access-key layer. It does not evaluate contracts, '
                 'validators, recovery arrangements, external signers or quantum-compromise probabilities. '
                 'Unknown is never counted as complete.</footer></div></body></html>')
    return ''.join(parts)
