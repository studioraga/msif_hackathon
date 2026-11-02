import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'scripts/m72_tt_sta_research.py'
spec=importlib.util.spec_from_file_location('tt_study',SOURCE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class TTResearch(unittest.TestCase):
    def test_actual_archive_inventory_is_not_physical_signoff(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            rc=mod.main(['--inventory',str(root/'build/m72/corner-inventory-c11p1.json'),'--out',str(Path(td)/'out')])
            self.assertIn(rc, (0, 2))  # Depends on whether external ORFS results are mounted
            data=json.loads((Path(td)/'out/manifest.json').read_text())
            self.assertEqual(data['signoff'],'NOT_VERIFIED')
            self.assertEqual(data['status'], 'TT_INPUTS_VERIFIED_NOT_EXECUTED' if rc == 0 else 'BLOCKED')
            if rc == 0:
                self.assertEqual(set(data['results']), set(mod.VARIANTS))
                self.assertFalse(data['issues'])
                for variant in mod.VARIANTS:
                    self.assertEqual(data['results'][variant]['status'], 'INPUTS_HASH_VERIFIED_NOT_EXECUTED')
            else:
                self.assertTrue(data['issues'])
            self.assertEqual(data['multi_corner'],'NOT_VERIFIED')
    def test_missing_inventory_preserves_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'
            self.assertEqual(mod.main(['--inventory',str(Path(td)/'missing.json'),'--out',str(out)]),2)
            self.assertTrue((out/'manifest.json').is_file())
    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(SystemExit):
                mod.main(['--inventory','x','--out',td])
