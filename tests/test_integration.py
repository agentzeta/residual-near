"""End-to-end CLI run against a local mock of the NEAR JSON-RPC API (no network access needed)."""
import json, pathlib, tempfile, threading, unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from residual.cli import main
from residual.core import b58encode

ED = 'ed25519:' + b58encode(bytes(range(1, 33)))
PQH = 'ml-dsa-65-hash:' + b58encode(bytes(range(2, 34)))
FULL = {'permission': 'FullAccess'}
KEYS = {
    'alice.near': [{'public_key': ED, 'access_key': FULL}],
    'bob.near': [{'public_key': ED, 'access_key': FULL}, {'public_key': PQH, 'access_key': FULL}],
    'relayer.near': [{'public_key': ED, 'access_key': FULL}],
    'pq-adopter.near': [{'public_key': ED, 'access_key': FULL}, {'public_key': PQH, 'access_key': FULL}],
}
BLOCKS = {
    'H3': {'header': {'hash': 'H3', 'height': 103, 'prev_hash': 'H2', 'latest_protocol_version': 85},
           'chunks': [{'chunk_hash': 'C3', 'height_included': 103}]},
    'H2': {'header': {'hash': 'H2', 'height': 102, 'prev_hash': 'H1', 'latest_protocol_version': 85},
           'chunks': [{'chunk_hash': 'C2', 'height_included': 102}]},
}
CHUNKS = {
    'C3': {'transactions': [{'hash': 'T1', 'signer_id': 'alice.near', 'receiver_id': 'x.near', 'actions': ['CreateAccount']},
                            {'hash': 'T2', 'signer_id': 'bob.near', 'receiver_id': 'x.near', 'actions': []}]},
    'C2': {'transactions': [{'hash': 'T3', 'signer_id': 'relayer.near', 'receiver_id': 'pq-adopter.near', 'actions': [
        {'Delegate': {'delegate_action': {'sender_id': 'pq-adopter.near', 'receiver_id': 'pq-adopter.near',
                                          'actions': [{'AddKey': {'public_key': 'ml-dsa-65:' + b58encode(bytes(1952)),
                                                                  'access_key': FULL}}]}}}]}]},
}


class MockNear(BaseHTTPRequestHandler):
    calls = []
    rate_limited_once = False

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        method, params = body['method'], body['params']
        MockNear.calls.append((method, params))
        if method == 'status' and not MockNear.rate_limited_once:
            MockNear.rate_limited_once = True
            self.send_response(429)
            self.end_headers()
            return
        if method == 'status':
            out = {'result': {'chain_id': 'mainnet', 'protocol_version': 85, 'version': {'version': '2.13.0'}}}
        elif method == 'block':
            out = {'result': BLOCKS['H3' if params.get('finality') == 'final' else params['block_id']]}
        elif method == 'chunk':
            out = {'result': CHUNKS[params['chunk_id']]}
        elif params.get('block_id') != 'H3':
            out = {'error': {'name': 'HANDLER_ERROR', 'cause': {'name': 'UNPINNED_READ'}}}
        elif params['account_id'] in KEYS:
            out = {'result': {'block_hash': 'H3', 'block_height': 103, 'keys': KEYS[params['account_id']]}}
        else:
            out = {'error': {'name': 'HANDLER_ERROR', 'cause': {'name': 'UNKNOWN_ACCOUNT'}}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), MockNear)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:%d' % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_cli(self, *args):
        out = tempfile.mkdtemp()
        with redirect_stdout(StringIO()):
            code = main(list(args) + ['--endpoint', self.url, '--output', out, '--delay', '0'])
        self.assertEqual(code, 0)
        return json.loads((pathlib.Path(out) / 'report.json').read_text()), pathlib.Path(out)

    def test_signer_sample_with_enrollers(self):
        report, out = self.run_cli('--sample-signers', '2', '--window-blocks', '2')
        prov = report['provenance']
        self.assertEqual(prov['network']['chain_id'], 'mainnet')
        self.assertEqual(prov['block']['hash'], 'H3')
        self.assertEqual(prov['sampling_frame']['distinct_signers'], 3)
        self.assertTrue(prov['sampling_frame']['complete'])
        self.assertEqual(report['summary']['requested'], 2)
        self.assertIn('interval_95', report['summary'])
        enr = report['cohorts']['pq_enrollers']
        self.assertEqual([a['account_id'] for a in enr['accounts']], ['pq-adopter.near'])
        self.assertEqual(enr['accounts'][0]['state'], 'INCOMPLETE_WEAKEST_LINK')
        self.assertEqual(enr['summary']['classical_full_access_present'], 1)
        reads = [p for m, p in MockNear.calls if m == 'query']
        self.assertTrue(reads and all(p['block_id'] == 'H3' for p in reads))
        self.assertIn('Accounts that enrolled an ML-DSA-65 key', (out / 'index.html').read_text())
        self.assertTrue((out / 'observations.json').exists())

    def test_account_list_keeps_missing_in_denominator(self):
        accounts = pathlib.Path(tempfile.mkdtemp()) / 'accounts.txt'
        accounts.write_text('# convenience sample\nalice.near\nghost.near\nbob.near\n')
        report, _ = self.run_cli('--accounts', str(accounts))
        s = report['summary']
        self.assertEqual((s['requested'], s['resolved'], s['unresolved']), (3, 2, 1))
        self.assertEqual(s['unresolved_by_reason'], {'ACCOUNT_NOT_FOUND': 1})
        self.assertNotIn('interval_95', s)
        self.assertEqual(report['cohorts'], {})


if __name__ == '__main__':
    unittest.main()
