import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('m72audit',Path(__file__).resolve().parents[1]/'scripts/m72_physical_audit.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestM72PhysicalAudit(unittest.TestCase):
    def test_missing_runs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            for v in mod.VARIANTS:
                self.assertEqual(mod.audit_variant(temp,v,'msif_m72_'+v+'_normalized_v2')['status'],'BLOCKED')
    def test_no_signoff_from_artifact_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            r=mod.audit_variant(temp,'programmable','one')
            self.assertEqual(r['exact_lq_mapped_import'],'NOT_VERIFIED')
            self.assertEqual(r['power_activity'],'NOT_VERIFIED')
