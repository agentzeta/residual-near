"""Print a Markdown summary of a Residual report (used on GitHub Actions run pages).

    python scripts/summary.py live-output/report.json >> "$GITHUB_STEP_SUMMARY"
"""
import json, pathlib, sys

path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'live-output/report.json')
if not path.exists():
    print('No report was written; see the scan step log.')
    sys.exit(0)
r = json.loads(path.read_text())
pv, s = r['provenance'], r['summary']
net = pv.get('network') or {}
print('## Residual mainnet sample\n')
print('| Field | Value |\n| --- | --- |')
rows = [('Chain', net.get('chain_id')), ('Protocol version', net.get('protocol_version')),
        ('Block height', pv['block'].get('height')), ('Block hash', pv['block'].get('hash')),
        ('Selection', pv.get('selection')), ('Accounts read', s['requested']), ('Resolved', s['resolved']),
        ('Unresolved', '%s %s' % (s['unresolved'], s['unresolved_by_reason'])),
        ('PQ key present', s['pq_key_present']), ('Classical full access present', s['classical_full_access_present']),
        ('States', s['counts']), ('Warnings', r['warnings'] or 'none'), ('Report SHA-256', r['report_sha256'])]
for k, v in rows:
    print('| %s | %s |' % (k, str(v).replace('|', '/')))
c = (r.get('cohorts') or {}).get('pq_enrollers')
if c:
    print('\n**ML-DSA enrollers in the window:** %s accounts; states %s' % (c['summary']['requested'], c['summary']['counts']))
