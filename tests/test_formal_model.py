"""Cross-check: the Python classifier agrees with the Lean model (formal/Residual.lean) on every
one of the 32 key-type combinations x 4 read statuses. The Lean file proves properties of the
model; this test ties the model to the code that actually runs."""
import json, pathlib, unittest
from residual.core import b58encode, classify_account

TABLE = pathlib.Path(__file__).resolve().parent.parent / 'formal' / 'truth_table.json'
FC = {'FunctionCall': {'receiver_id': 'app.near', 'method_names': []}}
SAMPLE = {
    'PQ_FULL': {'public_key': 'ml-dsa-65-hash:' + b58encode(bytes(range(1, 33))), 'access_key': {'permission': 'FullAccess'}},
    'PQ_FUNCTION': {'public_key': 'ml-dsa-65-hash:' + b58encode(bytes(range(2, 34))), 'access_key': {'permission': FC}},
    'CLASSICAL_FULL': {'public_key': 'ed25519:' + b58encode(bytes(range(3, 35))), 'access_key': {'permission': 'FullAccess'}},
    'CLASSICAL_FUNCTION': {'public_key': 'secp256k1:' + b58encode(bytes(range(4, 68))), 'access_key': {'permission': FC}},
    'UNKNOWN': {'public_key': 'bls12-381:abc', 'access_key': {'permission': 'FullAccess'}},
}


class TestMatchesLeanModel(unittest.TestCase):
    def test_every_row(self):
        rows = json.loads(TABLE.read_text())
        self.assertEqual(len(rows), 128)
        for r in rows:
            entries = [SAMPLE[t] for t in r['key_types']]
            if r['status'] == 'MALFORMED':
                got = classify_account('x.near', None, 'OK')
            elif r['status'] == 'OK':
                got = classify_account('x.near', entries, 'OK')
            else:
                got = classify_account('x.near', None, r['status'])
            with self.subTest(status=r['status'], key_types=r['key_types']):
                self.assertEqual(got['state'], r['state'])

    def test_sample_keys_classify_as_labelled(self):
        for label, entry in SAMPLE.items():
            got = classify_account('x.near', [entry])['key_types']
            self.assertEqual(got, [label])


if __name__ == '__main__':
    unittest.main()
