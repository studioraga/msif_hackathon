import importlib.util, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',ROOT/'scripts/m72_tt_sta_audit.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestTTAudit(unittest.TestCase):
    def test_recorded_tt_evidence_not_signoff(self):
        run=ROOT/'build/m72/tt-research-run-c13b'
        if not run.is_dir():self.skipTest('archived TT logs not included')
        result=mod.audit(run)
        self.assertEqual(result['status'],'TT_LOGS_CONSISTENT_REVIEW_REQUIRED',result['issues'])
        self.assertEqual(result['signoff'],'NOT_VERIFIED')
        self.assertEqual(set(result['results']),set(mod.VARIANTS))
    def test_missing_logs_block(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'manifest.json').write_text(json.dumps({'results':{v:{} for v in mod.VARIANTS}}))
            self.assertEqual(mod.audit(d)['status'],'BLOCKED')
    def test_log_tamper_blocks(self):
        run=ROOT/'build/m72/tt-research-run-c13b'
        if not run.is_dir():self.skipTest('archived TT logs not included')
        import shutil
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for name in ['manifest.json']+[v+'.log' for v in mod.VARIANTS]:shutil.copy2(run/name,d/name)
            (d/'fixed.log').write_text((d/'fixed.log').read_text()+'\nTAMPER\n')
            self.assertEqual(mod.audit(d)['status'],'BLOCKED')
