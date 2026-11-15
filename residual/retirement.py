"""Conservative, read-only evidence of old classical full-access key retirement.

Two trusted-RPC snapshots can show that an old named key was present at one block
and absent at a later block. They do NOT prove deletion transaction inclusion,
continuous absence, or cryptographic validity of the RPC responses.
"""
from .core import inspect_key


def _extract(report, account_id):
    pv = report.get('provenance') or {}
    chain = (pv.get('network') or {}).get('chain_id')
    block = pv.get('block') or {}
    observations = report.get('observations')
    if not isinstance(observations, list):
        observations = report.get('raw_observations')
    if not isinstance(observations, list):
        return None, 'RAW_OBSERVATIONS_MISSING'
    matches = [x for x in observations if x.get('account_id') == account_id]
    if len(matches) != 1:
        return None, 'ACCOUNT_OBSERVATION_MISSING_OR_DUPLICATED'
    record = matches[0]
    if record.get('status') != 'OK' or not isinstance(record.get('keys'), list):
        return None, 'ACCESS_KEY_READ_UNRESOLVED'
    if not isinstance(block.get('height'), int) or not isinstance(block.get('hash'), str) or not chain:
        return None, 'BLOCK_PROVENANCE_MISSING'
    keys = record['keys']
    mapped = [(x.get('public_key'), *inspect_key(x)) for x in keys if isinstance(x, dict)]
    if len(mapped) != len(keys) or any(k is None or kind == 'UNKNOWN' for k, kind, _ in mapped) or len({k for k, _, _ in mapped}) != len(mapped):
        return None, 'KEY_INVENTORY_UNKNOWN_OR_MALFORMED'
    return {'chain': chain, 'height': block['height'], 'hash': block['hash'],
            'classic_full': {k for k, kind, _ in mapped if kind == 'CLASSICAL_FULL'},
            'pq_full': {k for k, kind, _ in mapped if kind == 'PQ_FULL'},
            'all_keys': {k for k, _, _ in mapped}}, None


def compare_retirement(before, after, account_id):
    """Evaluate one account across two ordered, pinned trusted-RPC observations."""
    base = {'schema': 'residual.retirement-comparison.v1', 'account_id': account_id,
            'proof_type': 'TRUSTED_RPC_PINNED_SNAPSHOTS',
            'cryptographic_proof': False, 'continuous_absence_proven': False,
            'scope': 'observed NEAR access-key authorization only'}
    a, error_a = _extract(before, account_id)
    b, error_b = _extract(after, account_id)
    if error_a or error_b:
        return {**base, 'verdict': 'INSUFFICIENT_EVIDENCE', 'reason': error_a or error_b}
    base.update(before_block={'height': a['height'], 'hash': a['hash']},
                after_block={'height': b['height'], 'hash': b['hash']}, chain_id=b['chain'])
    if a['chain'] != b['chain'] or b['height'] <= a['height'] or a['hash'] == b['hash']:
        return {**base, 'verdict': 'INSUFFICIENT_EVIDENCE', 'reason': 'BLOCK_ORDER_OR_CHAIN_MISMATCH'}
    if not b['pq_full']:
        return {**base, 'verdict': 'NOT_ESTABLISHED', 'reason': 'NO_CURRENT_PQ_FULL_ACCESS'}
    if b['classic_full']:
        return {**base, 'verdict': 'NOT_RETIRED', 'reason': 'CLASSICAL_FULL_ACCESS_STILL_PRESENT',
                'remaining_classical_full_keys': sorted(b['classic_full'])}
    if not a['classic_full']:
        return {**base, 'verdict': 'CURRENT_ABSENCE_ONLY',
                'reason': 'NO_PREVIOUS_CLASSICAL_FULL_ACCESS_KEY_OBSERVED'}
    previous_keys = sorted(a['classic_full'])
    if any(k in b['all_keys'] for k in previous_keys):
        return {**base, 'verdict': 'NOT_RETIRED', 'reason': 'PREVIOUS_KEY_STILL_PRESENT'}
    return {**base, 'verdict': 'RETIREMENT_OBSERVED_BETWEEN_SNAPSHOTS',
            'reason': 'PREVIOUS_CLASSICAL_FULL_ACCESS_KEYS_ABSENT_AT_LATER_BLOCK',
            'previous_classical_full_keys': previous_keys,
            'pq_full_access_key_count_after': len(b['pq_full']),
            'caution': 'Does not identify a DeleteKey receipt, prove absence between blocks, or validate RPC state cryptographically.'}


def main(argv=None):
    """Compare two recorded snapshot files without contacting the network."""
    import argparse
    import json
    from pathlib import Path
    p = argparse.ArgumentParser(description='Compare NEAR classical access-key retirement across two pinned snapshots')
    p.add_argument('--before', required=True, help='Earlier browser report JSON or CLI report.json')
    p.add_argument('--after', required=True, help='Later browser report JSON or CLI report.json')
    p.add_argument('--account', required=True, help='NEAR account ID present in both observations')
    p.add_argument('--before-observations', help='Raw observations.json for earlier Python CLI report')
    p.add_argument('--after-observations', help='Raw observations.json for later Python CLI report')
    p.add_argument('--output', help='Optional JSON result path')
    args = p.parse_args(argv)

    def read(path, raw_path):
        r = json.loads(Path(path).read_text())
        if raw_path:
            r['observations'] = json.loads(Path(raw_path).read_text())
        return r

    output = compare_retirement(read(args.before, args.before_observations),
                                read(args.after, args.after_observations), args.account)
    result = json.dumps(output, indent=2, sort_keys=True) + '
'
    if args.output:
        Path(args.output).write_text(result)
    print(result, end='')
    return 0 if output['verdict'] != 'INSUFFICIENT_EVIDENCE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
