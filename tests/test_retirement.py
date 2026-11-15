"""Post-submission tests: temporal evidence is stricter than PQ-key presence."""
import unittest
from residual.core import b58encode
from residual.retirement import compare_retirement

ED = 'ed25519:' + b58encode(bytes(range(1, 33)))
ED2 = 'ed25519:' + b58encode(bytes(range(2, 34)))
PQ = 'ml-dsa-65-hash:' + b58encode(bytes(range(3, 35)))


def snap(height, keys, chain='mainnet', status='OK', acct='alice.near'):
    return {'provenance': {'network': {'chain_id': chain}, 'block': {'hash': 'H' + str(height), 'height': height}},
            'observations': [{'account_id': acct, 'status': status,
                              'keys': [{'public_key': x, 'access_key': {'permission': 'FullAccess'}} for x in keys]}]}


class TestRetirement(unittest.TestCase):
    def test_observed_retirement(self):
        s = compare_retirement(snap(1, [ED, PQ]), snap(2, [PQ]), 'alice.near')
        self.assertEqual(s['verdict'], 'RETIREMENT_OBSERVED_BETWEEN_SNAPSHOTS')
        self.assertFalse(s['cryptographic_proof'])

    def test_addition_does_not_retire(self):
        self.assertEqual(compare_retirement(snap(1, [ED]), snap(2, [ED, PQ]), 'alice.near')['verdict'], 'NOT_RETIRED')

    def test_different_old_key_remains(self):
        self.assertEqual(compare_retirement(snap(1, [ED, ED2, PQ]), snap(2, [ED2, PQ]), 'alice.near')['verdict'], 'NOT_RETIRED')

    def test_new_classical_key_blocks_migration(self):
        self.assertEqual(compare_retirement(snap(1, [ED, PQ]), snap(2, [ED2, PQ]), 'alice.near')['verdict'], 'NOT_RETIRED')

    def test_pq_only_without_prior_observation(self):
        self.assertEqual(compare_retirement(snap(1, [PQ]), snap(2, [PQ]), 'alice.near')['verdict'], 'CURRENT_ABSENCE_ONLY')

    def test_wrong_order(self):
        self.assertEqual(compare_retirement(snap(3, [ED, PQ]), snap(2, [PQ]), 'alice.near')['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_cross_chain(self):
        self.assertEqual(compare_retirement(snap(1, [ED, PQ]), snap(2, [PQ], chain='testnet'), 'alice.near')['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_failed_read(self):
        self.assertEqual(compare_retirement(snap(1, [ED, PQ]), snap(2, [], status='RPC_ERROR'), 'alice.near')['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_malformed_key(self):
        self.assertEqual(compare_retirement(snap(1, [ED, PQ]), snap(2, ['ed25519:BAD', PQ]), 'alice.near')['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_missing_raw_observations(self):
        self.assertEqual(compare_retirement({'provenance': {}}, snap(2, [PQ]), 'alice.near')['verdict'], 'INSUFFICIENT_EVIDENCE')

    def test_no_pq_after(self):
        self.assertEqual(compare_retirement(snap(1, [ED]), snap(2, []), 'alice.near')['verdict'], 'NOT_ESTABLISHED')


if __name__ == '__main__':
    unittest.main()
