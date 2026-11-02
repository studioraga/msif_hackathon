import json, tempfile, unittest, copy
from pathlib import Path
from m72_c18_area_audit import check
ROOT=Path(__file__).resolve().parents[1]
class Audit(unittest.TestCase):
 def test_real_receipts(self):
  p=ROOT/'build/m72/closure17-area-execute'; inv=ROOT/'build/m72/corner-inventory-c11p1.json'
  r=check(p,inv)
  self.assertEqual(r['status'],'AREA_RECEIPTS_INTACT_CLASSIFICATION_PENDING',r['issues'])
  self.assertEqual(len(r['architectures']),3)
  self.assertTrue(all(x['raw_other_not_functional_area'] for x in r['architectures'].values()))
 def test_missing_receipts(self):
  with tempfile.TemporaryDirectory() as d:
   r=check(Path(d),ROOT/'build/m72/corner-inventory-c11p1.json')
   self.assertEqual(r['status'],'BLOCKED')
 def test_tamper_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   import shutil
   src=ROOT/'build/m72/closure17-area-execute';dst=Path(d)
   for f in src.iterdir():
    if f.is_file():shutil.copy2(f,dst/f.name)
   m=json.loads((dst/'manifest.json').read_text());m['variants']['fixed']['odb_sha256']='0'*64;(dst/'manifest.json').write_text(json.dumps(m))
   self.assertEqual(check(dst,ROOT/'build/m72/corner-inventory-c11p1.json')['status'],'BLOCKED')

class Collector(unittest.TestCase):
 def test_missing_odb(self):
  from m72_c18_classified_run import main
  with tempfile.TemporaryDirectory() as d:
   inv=Path(d)/'inventory.json'
   inv.write_text(json.dumps({'designs':{v:{'odb':{'path':'/nonexistent/6_final.odb','sha256':'x'}} for v in ('programmable','fixed','rom')}}))
   self.assertEqual(main(['--inventory',str(inv),'--out',str(Path(d)/'out')]),2)
