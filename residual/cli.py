import argparse, datetime, json, os, pathlib, sys, urllib.parse
from .core import classify_account, summarize, canonical_digest
from .rpc import DEFAULT_ENDPOINT, RPCError, finalized_block, network_info, scan
from .sample import seeded_draw, window_frame
from .report import render

PQ_MIN_PROTOCOL = 85  # NEP-645 ML-DSA-65 keys are stabilized at protocol version 85 (neard 2.13)


def _endpoint_ok(url):
    u = urllib.parse.urlparse(url)
    return u.scheme == 'https' or (u.scheme == 'http' and u.hostname in ('127.0.0.1', 'localhost'))


def _classify(records):
    return [classify_account(r['account_id'], r.get('keys'), r.get('status', 'OK')) for r in records]


def main(argv=None):
    p = argparse.ArgumentParser(description='Residual: read-only NEAR post-quantum migration observatory')
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--fixture', help='synthetic fixture JSON with an accounts array')
    src.add_argument('--accounts', help='UTF-8 text file, one NEAR account ID per line (convenience sample)')
    src.add_argument('--sample-signers', type=int, metavar='N',
                     help='seeded random draw of N distinct transaction signers from a recent block window')
    p.add_argument('--window-blocks', type=int, default=60, help='blocks to walk back for --sample-signers')
    p.add_argument('--no-enrollers', action='store_true', help='skip scanning accounts seen enrolling ML-DSA keys')
    p.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    p.add_argument('--output', default='out')
    p.add_argument('--delay', type=float, default=0.05)
    p.add_argument('--retries', type=int, default=3)
    a = p.parse_args(argv)

    warnings, frame, cohorts, random_draw, network = [], None, {}, False, None
    if a.fixture:
        raw = json.loads(pathlib.Path(a.fixture).read_text())
        records, block = raw['accounts'], raw.get('block', {})
        mode, selection = 'SYNTHETIC_FIXTURE', 'predefined synthetic fixture (not NEAR data)'
    else:
        if not _endpoint_ok(a.endpoint):
            p.error('RPC endpoint must use HTTPS (plain HTTP is allowed only for localhost)')
        if a.sample_signers is not None and (a.sample_signers < 1 or a.window_blocks < 1):
            p.error('--sample-signers and --window-blocks must be positive')
        kw = {'retries': a.retries, 'api_key': os.environ.get('FASTNEAR_API_KEY') or None}
        try:
            network = network_info(a.endpoint, **kw)
            block = finalized_block(a.endpoint, **kw)
        except RPCError as exc:
            print('RPC failure: ' + str(exc), file=sys.stderr)
            return 2
        proto = block.get('latest_protocol_version') or network.get('protocol_version')
        if isinstance(proto, int) and proto < PQ_MIN_PROTOCOL:
            warnings.append('Protocol version %s is below %s: ML-DSA-65 keys cannot exist at this block' % (proto, PQ_MIN_PROTOCOL))
        if a.accounts:
            ids = [x.strip() for x in pathlib.Path(a.accounts).read_text().splitlines()
                   if x.strip() and not x.lstrip().startswith('#')]
            if not ids or len(ids) != len(set(ids)):
                p.error('account list must be nonempty with unique IDs')
            selection = 'user-provided account list (convenience sample; not representative of NEAR)'
            enrollments = []
        else:
            signers, enrollments, frame = window_frame(a.endpoint, block, a.window_blocks, a.delay, **kw)
            if not signers:
                print('No signers found in the block window; nothing to sample', file=sys.stderr)
                return 2
            ids = seeded_draw(signers, block['hash'], a.sample_signers)
            random_draw = len(ids) < len(signers)
            selection = ('seeded random draw of %d from %d distinct transaction signers in blocks %d-%d; '
                         'seed = pinned block hash' % (len(ids), len(signers), frame['lowest_height'], frame['head_height']))
            if not frame['complete']:
                warnings.append('Sampling frame incomplete: %d block and %d chunk read failures'
                                % (frame['block_failures'], frame['chunk_failures']))
        _, records = scan(a.endpoint, ids, a.delay, block=block, **kw)
        enrollers = sorted({e['account_id'] for e in enrollments if isinstance(e.get('account_id'), str)})
        if enrollers and not a.no_enrollers:
            _, er = scan(a.endpoint, enrollers, a.delay, block=block, **kw)
            ers = _classify(er)
            cohorts['pq_enrollers'] = {
                'definition': 'Accounts that received an ML-DSA-65 AddKey inside the sampling window, '
                              'read at the same pinned block',
                'events': enrollments, 'summary': summarize(ers), 'accounts': ers,
                'raw_observations_sha256': canonical_digest(er)}
        mode = 'LIVE_RPC'

    results = _classify(records)
    report = {
        'schema': 'residual.near.report.v2',
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'provenance': {'mode': mode, 'block': block, 'network': network, 'selection': selection,
                       'sampling_frame': frame, 'endpoint': a.endpoint if mode == 'LIVE_RPC' else None,
                       'account_list_sha256': canonical_digest([r['account_id'] for r in records]),
                       'raw_observations_sha256': canonical_digest(records)},
        'warnings': warnings,
        'summary': summarize(results, random_draw=random_draw),
        'accounts': results,
        'cohorts': cohorts,
    }
    report['report_sha256'] = canonical_digest(report)
    out = pathlib.Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'observations.json').write_text(json.dumps(records, indent=2) + '\n')
    (out / 'index.html').write_text(render(report))
    print(json.dumps({'report': str(out / 'report.json'), 'dashboard': str(out / 'index.html'),
                      'warnings': warnings, 'summary': report['summary']}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
