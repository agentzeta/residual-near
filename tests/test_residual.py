import json,unittest
from unittest.mock import patch
from residual.core import classify_account,classify_key,summarize,canonical_digest
from residual.rpc import scan,RPCError
from residual.report import render

def key(prefix,permission='FullAccess'):
    # base58 '1' encodes a zero byte: 32 bytes for ed25519 and ML-DSA-65 handles, 64 for secp256k1.
    return {'public_key':prefix+'1'*(64 if prefix=='secp256k1:' else 32),'access_key':{'permission':permission}}
P='ml-dsa-65-hash:';E='ed25519:';S='secp256k1:'
class TestClassification(unittest.TestCase):
    def c(self,keys,status='OK'): return classify_account('test.near',keys,status)['state']
    def test_mixed(self): self.assertEqual(self.c([key(E),key(P)]),'INCOMPLETE_WEAKEST_LINK')
    def test_mixed_secp(self): self.assertEqual(self.c([key(S),key(P)]),'INCOMPLETE_WEAKEST_LINK')
    def test_classical(self): self.assertEqual(self.c([key(E)]),'CLASSICAL_ONLY')
    def test_complete(self): self.assertEqual(self.c([key(P)]),'COMPLETE')
    def test_pq_function_only(self): self.assertEqual(self.c([key(P,{'FunctionCall':{'receiver_id':'x','method_names':['a']}})]),'PQ_FUNCTION_ONLY')
    def test_classical_function_pq_full(self): self.assertEqual(self.c([key(E,{'FunctionCall':{'receiver_id':'x'}}),key(P)]),'COMPLETE')
    def test_empty(self): self.assertEqual(self.c([]),'UNDETERMINED')
    def test_failed_rpc(self): self.assertEqual(self.c(None,'RPC_ERROR'),'UNDETERMINED')
    def test_unknown_type(self): self.assertEqual(self.c([key(P),key('weird:')]),'UNDETERMINED')
    def test_malformed_pq(self): self.assertEqual(self.c([key(P),{'public_key':P+'0','access_key':{'permission':'FullAccess'}}]),'UNDETERMINED')
    def test_missing_permission(self): self.assertEqual(self.c([{'public_key':P+'111'}]),'UNDETERMINED')
    def test_no_false_safe(self): self.assertNotEqual(self.c([key(E),key(P)]),'COMPLETE')
    def test_counts(self):
        a=[classify_account('a',[key(P)]),classify_account('b',[key(E),key(P)]),classify_account('c',None,'RPC_ERROR')]
        s=summarize(a);self.assertEqual((s['requested'],s['resolved'],s['unresolved']), (3,2,1));self.assertEqual(s['complete_share_of_requested'],1/3)
    def test_digest_stable(self): self.assertEqual(canonical_digest({'b':1,'a':2}),canonical_digest({'a':2,'b':1}))
    def test_html_escaped(self):
        a=classify_account('<script>',[key(P)]);r={'summary':summarize([a]),'accounts':[a],'provenance':{'mode':'SYNTHETIC_FIXTURE','selection':'test','block':{}}};h=render(r)
        self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h)
    @patch('residual.rpc.rpc')
    def test_block_pinned(self,mock):
        mock.side_effect=[{'header':{'hash':'H','height':123}},{'block_hash':'H','keys':[key(P)]}]
        block,records=scan('https://example.org',['test.near']);self.assertEqual(block['hash'],'H');self.assertEqual(records[0]['status'],'OK')
        self.assertEqual(mock.call_args_list[1].args[2]['block_id'],'H')
    @patch('residual.rpc.rpc')
    def test_block_mismatch(self,mock):
        mock.side_effect=[{'header':{'hash':'H','height':123}},{'block_hash':'DIFFERENT','keys':[]}]
        _,records=scan('https://example.org',['test.near']);self.assertEqual(records[0]['status'],'RPC_ERROR')
    @patch('residual.rpc.rpc')
    def test_failed_one_keeps_denominator(self,mock):
        mock.side_effect=[{'header':{'hash':'H','height':123}},RPCError('timeout'),{'block_hash':'H','keys':[key(P)]}]
        _,records=scan('https://example.org',['a.near','b.near']);self.assertEqual(len(records),2)
        self.assertEqual(records[0]['status'],'RPC_ERROR');self.assertEqual(records[1]['status'],'OK')
if __name__=='__main__':unittest.main()
