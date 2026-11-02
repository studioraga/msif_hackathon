import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m72_c20_audit import audit
ROOT=Path(__file__).resolve().parents[1]
class C20(unittest.TestCase):
 def test_actual_area_receipts_without_external_sdc(self):
  r=audit(ROOT/'build/m72/c19-classified-v1',ROOT/'build/m72/corner-inventory-c11p1.json',ROOT/'build/m72/closure17-area-execute',False)
  self.assertEqual(r['status'],'AREA_RECONCILED_SDC_NOT_CHECKED',r['issues']);self.assertEqual(len(r['variants']),3)
  self.assertEqual(r['signoff'],'NOT_VERIFIED')
 def test_missing_receipts_block(self):
  r=audit(ROOT/'build/m72/does-not-exist',ROOT/'build/m72/corner-inventory-c11p1.json',None,False)
  self.assertEqual(r['status'],'BLOCKED')
 def test_sdc_fails_closed_if_external_missing(self):
  r=audit(ROOT/'build/m72/c19-classified-v1',ROOT/'build/m72/corner-inventory-c11p1.json',None,True)
  self.assertIn(r['status'],('BLOCKED','AREA_RECONCILED_SDC_REVIEW_REQUIRED'))
if __name__=='__main__':unittest.main()
