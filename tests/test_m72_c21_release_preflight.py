import tempfile
import unittest
from pathlib import Path
from m72_c21_release_preflight import inspect
class ReleasePreflight(unittest.TestCase):
    def test_actual_repo_never_approves_release(self):
        root=Path(__file__).resolve().parents[1]
        result=inspect(root)
        self.assertFalse(result['release_authorized'])
        self.assertEqual(result['gates']['p4_ss_ff_rc'],'NOT_VERIFIED')
        self.assertEqual(result['gates']['p5_activity_power'],'NOT_VERIFIED')
        self.assertEqual(result['gates']['g1_independent_approval'],'NOT_VERIFIED')
        self.assertEqual(set(result['variants']),set(('programmable','fixed','rom')))
        self.assertEqual(result['issues'],[])
    def test_missing_evidence_reports_blockers(self):
        with tempfile.TemporaryDirectory() as td:
            result=inspect(td)
            self.assertFalse(result['release_authorized'])
            self.assertTrue(result['issues'])
    def test_tampered_gls_fails(self):
        from unittest.mock import patch
        from m72_c21_release_preflight import sha
        root=Path(__file__).resolve().parents[1]
        with patch('m72_c21_release_preflight.sha',side_effect=lambda path: '0'*64):
            result=inspect(root)
        self.assertTrue(any('mismatch' in issue for issue in result['issues']))
if __name__=='__main__':unittest.main()
