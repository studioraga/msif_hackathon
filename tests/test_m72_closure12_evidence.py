import unittest
from pathlib import Path
from m72_closure12_evidence_audit import check

class Closure12Evidence(unittest.TestCase):
    def test_actual_cross_ledger_and_never_signoff(self):
        root=Path(__file__).resolve().parents[1]
        result=check(root)
        self.assertEqual(result['status'],'EVIDENCE_CONSISTENT_NOT_SIGNOFF')
        self.assertEqual(result['g1'],'NOT_VERIFIED')
        self.assertEqual(result['p4'],'NOT_VERIFIED')
        self.assertEqual(result['p5'],'NOT_VERIFIED')
        self.assertTrue(all(x['formal']=='TIMEOUT_INCONCLUSIVE' for x in result['variants'].values()))
        self.assertTrue(result['rcx_present'])
