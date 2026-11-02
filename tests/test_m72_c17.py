import json,tempfile,unittest
from pathlib import Path
from m72_c17_evidence import audit
from m72_exact_lq_area import main
ROOT=Path(__file__).resolve().parents[1]
class Closure17(unittest.TestCase):
 def test_existing_evidence_all_three(self):
  x=audit(ROOT/'build/m72/postroute-gls-run-c16',ROOT/'build/m72/tt-research-run-c13b')
  self.assertEqual(x['status'],'GLS_TT_EVIDENCE_CONSISTENT_NOT_SIGNOFF',x['issues'])
  self.assertEqual({v['routed_cell_types'] for v in x['variants'].values()},{43})
 def test_tamper_is_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   import shutil
   dst=Path(t)/'gls';shutil.copytree(ROOT/'build/m72/postroute-gls-run-c16',dst)
   (dst/'fixed.simulate.log').write_text('PASS fixed 260 vectors\n')
   result=audit(dst,ROOT/'build/m72/tt-research-run-c13b')
   self.assertEqual(result['status'],'BLOCKED')
 def test_area_missing_files_block_not_signoff(self):
  with tempfile.TemporaryDirectory() as t:
   inv=Path(t)/'inv.json';inv.write_text(json.dumps({'designs':{v:{'odb':{'path':'/nonexistent/6_final.odb','sha256':'x'}} for v in ('programmable','fixed','rom')}}))
   self.assertEqual(main(['--inventory',str(inv),'--out',str(Path(t)/'area')]),2)
