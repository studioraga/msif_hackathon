import json, tempfile, unittest
from pathlib import Path
from m72_postroute_gls import run
class PostrouteGLS(unittest.TestCase):
 def test_missing_external_files_fail_closed(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d)/'result'
   self.assertEqual(run(root,Path(d)/'absent_flow',dest,False),2)
   m=json.loads((dest/'manifest.json').read_text())
   self.assertEqual(set(m['variants']),{'programmable','fixed','rom'})
   self.assertEqual(m['functional_equivalence'],'NOT_VERIFIED')
 def test_never_uses_placeholder_paths(self):
  s=(Path(__file__).resolve().parents[1]/'scripts/m72_postroute_gls.py').read_text()
  self.assertIn("f'{top}_gate_tb.sv'",s)
  self.assertIn("'6_final.v'",s)
  self.assertNotIn('qualified_final_cell_models.v',s)
