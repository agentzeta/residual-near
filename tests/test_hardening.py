"""Tests for key-length validation, reason codes, RPC retries, sampling and intervals."""
import io, json, unittest, urllib.error
from unittest.mock import patch
from residual.core import b58decode, b58encode, classify_account, inspect_key, summarize, wilson
from residual.rpc import RPCError, rpc, scan
from residual.sample import pq_enrollments, seeded_draw, window_frame


def k(prefix, size, permission='FullAccess'):
    raw = bytes(i % 255 + 1 for i in range(size))
    return {'public_key': prefix + b58encode(raw), 'access_key': {'permission': permission}}


FC = {'FunctionCall': {'receiver_id': 'app.near', 'method_names': []}}
ED, SECP, PQH = 'ed25519:', 'secp256k1:', 'ml-dsa-65-hash:'


class TestKeyValidation(unittest.TestCase):
    def test_b58_roundtrip(self):
        for raw in (b'\0\0abc', bytes(32), bytes(range(64))):
            self.assertEqual(b58decode(b58encode(raw)), raw)

    def test_valid_lengths(self):
        self.assertEqual(inspect_key(k(ED, 32)), ('CLASSICAL_FULL', None))
        self.assertEqual(inspect_key(k(SECP, 64)), ('CLASSICAL_FULL', None))
        self.assertEqual(inspect_key(k(PQH, 32, FC)), ('PQ_FUNCTION', None))

    def test_wrong_lengths_rejected(self):
        self.assertEqual(inspect_key(k(ED, 31)), ('UNKNOWN', 'WRONG_KEY_LENGTH'))
        self.assertEqual(inspect_key(k(SECP, 32)), ('UNKNOWN', 'WRONG_KEY_LENGTH'))
        self.assertEqual(inspect_key(k(PQH, 1952)), ('UNKNOWN', 'WRONG_KEY_LENGTH'))
        self.assertEqual(inspect_key({'public_key': 'ed25519:1', 'access_key': {'permission': 'FullAccess'}}),
                         ('UNKNOWN', 'WRONG_KEY_LENGTH'))

    def test_full_pq_key_in_list_is_anomalous(self):
        a = classify_account('x.near', [k('ml-dsa-65:', 1952), k(ED, 32)])
        self.assertEqual(a['state'], 'UNDETERMINED')
        self.assertIn('UNEXPECTED_FULL_PQ_KEY', a['notes'])
        self.assertIn('CLASSICAL_FULL_ACCESS_OBSERVED', a['notes'])


class TestReasons(unittest.TestCase):
    def test_locked_account(self):
        self.assertEqual(classify_account('l.near', [])['reason_code'], 'NO_ACCESS_KEYS')

    def test_classical_function_only(self):
        a = classify_account('f.near', [k(ED, 32, FC)])
        self.assertEqual((a['state'], a['reason_code']), ('UNDETERMINED', 'CLASSICAL_FUNCTION_ONLY'))

    def test_complete_flags_residual_function_keys(self):
        a = classify_account('c.near', [k(PQH, 32), k(ED, 32, FC)])
        self.assertEqual(a['state'], 'COMPLETE')
        self.assertIn('RESIDUAL_CLASSICAL_FUNCTION_KEYS', a['notes'])

    def test_unresolved_reasons_are_counted(self):
        accts = [classify_account('a', None, 'ACCOUNT_NOT_FOUND'), classify_account('b', None, 'RPC_ERROR'),
                 classify_account('c', [k(ED, 32), k(PQH, 32)])]
        s = summarize(accts)
        self.assertEqual(s['unresolved_by_reason'], {'ACCOUNT_NOT_FOUND': 1, 'RPC_ERROR': 1})
        self.assertEqual(s['complete_share_of_pq_full_access'], 0.0)


class TestIntervals(unittest.TestCase):
    def test_wilson_matches_known_values(self):
        lo, hi = wilson(10, 10)
        self.assertAlmostEqual(lo, 0.7225, places=3)
        self.assertAlmostEqual(hi, 1.0)
        lo, hi = wilson(4, 10)
        self.assertAlmostEqual(lo, 0.1682, places=3)
        self.assertAlmostEqual(hi, 0.6873, places=3)
        self.assertIsNone(wilson(0, 0))

    def test_interval_only_for_random_draw(self):
        accts = [classify_account('a', [k(ED, 32)])]
        self.assertNotIn('interval_95', summarize(accts))
        self.assertIn('interval_95', summarize(accts, random_draw=True))


def _http_error(code):
    return urllib.error.HTTPError('https://x', code, 'err', {}, io.BytesIO(b''))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestRPC(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_retries_rate_limit_then_succeeds(self, urlopen):
        urlopen.side_effect = [_http_error(429), _http_error(503), _Resp(b'{"result": {"ok": 1}}')]
        slept = []
        self.assertEqual(rpc('https://x', 'status', [], sleep=slept.append), {'ok': 1})
        self.assertEqual(slept, [1.0, 2.0])

    @patch('urllib.request.urlopen')
    def test_gives_up_after_retries(self, urlopen):
        urlopen.side_effect = [_http_error(429)] * 3
        with self.assertRaises(RPCError):
            rpc('https://x', 'status', [], retries=2, sleep=lambda s: None)
        self.assertEqual(urlopen.call_count, 3)

    @patch('urllib.request.urlopen')
    def test_client_error_not_retried(self, urlopen):
        urlopen.side_effect = [_http_error(400)]
        with self.assertRaises(RPCError):
            rpc('https://x', 'status', [], sleep=lambda s: None)
        self.assertEqual(urlopen.call_count, 1)

    @patch('urllib.request.urlopen')
    def test_unknown_account_codes(self, urlopen):
        err = {'error': {'name': 'HANDLER_ERROR', 'cause': {'name': 'UNKNOWN_ACCOUNT'}}}
        urlopen.side_effect = [_Resp(json.dumps(err).encode())]
        with self.assertRaises(RPCError) as ctx:
            rpc('https://x', 'query', {})
        self.assertEqual(ctx.exception.code, 'ACCOUNT_NOT_FOUND')
        old = {'result': {'error': 'account ghost.near does not exist while viewing', 'logs': []}}
        urlopen.side_effect = [_Resp(json.dumps(old).encode())]
        with self.assertRaises(RPCError) as ctx:
            rpc('https://x', 'query', {})
        self.assertEqual(ctx.exception.code, 'ACCOUNT_NOT_FOUND')

    @patch('residual.rpc.rpc')
    def test_scan_marks_missing_account(self, mock):
        mock.side_effect = [RPCError('gone', 'ACCOUNT_NOT_FOUND')]
        _, records = scan('https://x', ['ghost.near'], block={'hash': 'H', 'height': 1})
        self.assertEqual(records[0]['status'], 'ACCOUNT_NOT_FOUND')


class TestSampling(unittest.TestCase):
    def test_seeded_draw_is_deterministic(self):
        ids = ['a.near', 'b.near', 'c.near', 'd.near']
        self.assertEqual(seeded_draw(ids, 'H', 2), seeded_draw(list(reversed(ids)), 'H', 2))
        self.assertEqual(len(seeded_draw(ids, 'H', 10)), 4)
        draws = {tuple(seeded_draw(ids, seed, 2)) for seed in ('H1', 'H2', 'H3', 'H4', 'H5', 'H6')}
        self.assertGreater(len(draws), 1)

    def test_enrollment_inside_delegate(self):
        tx = {'hash': 'T', 'signer_id': 'relayer.near', 'receiver_id': 'user.near', 'actions': [
            {'Delegate': {'delegate_action': {'sender_id': 'user.near', 'receiver_id': 'user.near',
                                              'actions': [{'AddKey': {'public_key': 'ml-dsa-65:abc'}}]}}}]}
        self.assertEqual(pq_enrollments(tx, 7),
                         [{'account_id': 'user.near', 'signer_id': 'user.near', 'tx_hash': 'T', 'block_height': 7}])
        self.assertEqual(pq_enrollments({'actions': ['CreateAccount', {'AddKey': {'public_key': 'ed25519:x'}}]}, 1), [])

    @patch('residual.sample.rpc')
    def test_window_skips_carried_chunks_and_counts_failures(self, mock):
        blocks = {
            'H2': {'header': {'hash': 'H2', 'height': 2, 'prev_hash': 'H1'},
                   'chunks': [{'chunk_hash': 'C2', 'height_included': 2}, {'chunk_hash': 'OLD', 'height_included': 1}]},
            'H1': {'header': {'hash': 'H1', 'height': 1, 'prev_hash': None},
                   'chunks': [{'chunk_hash': 'BAD', 'height_included': 1}]},
        }

        def fake(endpoint, method, params, **kw):
            if method == 'block':
                return blocks[params['block_id']]
            if params['chunk_id'] == 'BAD':
                raise RPCError('timeout')
            return {'transactions': [{'signer_id': 'b.near'}, {'signer_id': 'a.near'}, {'signer_id': 'a.near'}]}
        mock.side_effect = fake
        signers, enrollments, frame = window_frame('https://x', {'hash': 'H2', 'height': 2}, 5)
        self.assertEqual(signers, ['a.near', 'b.near'])
        self.assertEqual((frame['chunks_read'], frame['chunk_failures'], frame['blocks_read']), (1, 1, 2))
        self.assertEqual(frame['transactions'], 3)
        self.assertFalse(frame['complete'])
        self.assertNotIn('OLD', [c.args[2].get('chunk_id') for c in mock.call_args_list])


if __name__ == '__main__':
    unittest.main()
