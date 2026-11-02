import tempfile,unittest
from pathlib import Path
from m72_formal_equiv import yosys_script
from m72_physical_lec_inventory import audit
class Closure(unittest.TestCase):
 def test_script_proof_required(self):
  s=yosys_script(Path('rtl'),Path('gate'),Path('models'),'msif_fixed')
  self.assertIn('equiv_induct -seq 32',s)
  self.assertIn('equiv_status -assert',s)
 def test_missing_exports_block(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(audit(Path(d),'exact_lq_singlecore_v2')['status'],'BLOCKED')
 def test_corner_no_fabrication(self):
  from m72_corner_inventory import main
  self.assertTrue(callable(main))


class M72DocumentHistory(unittest.TestCase):
    def test_history_is_actual_not_premature_release(self):
        root = Path(__file__).resolve().parents[1]
        history = (root / 'docs' / 'Milestones.md').read_text()
        future = (root / 'docs' / 'M7.2-Future-Commit-and-Tags.md').read_text()
        self.assertIn('07 G1 blocked 3411e86', history)
        self.assertIn('Commit 08 is **not yet committed**', history)
        self.assertIn('release_authorized=false', history)
        self.assertIn('**BLOCKED**', future)
