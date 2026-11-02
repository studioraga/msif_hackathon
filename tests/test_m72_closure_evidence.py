import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m72_closure_evidence import route_status,extract_area
class TestClosureEvidence(unittest.TestCase):
 def test_missing_route_is_not_pass(self):
  self.assertEqual(route_status({})['status'],'NOT_VERIFIED')
 def test_zero_drc_not_foundry_signoff(self):
  d=route_status({'detailedroute__route__drc_errors':0,'detailedroute__antenna__violating__nets':0,'detailedroute__antenna__violating__pins':0})
  self.assertIn('NOT_FOUNDRY_SIGNOFF',d['status'])
 def test_nonzero_blocks(self):
  self.assertEqual(route_status({'detailedroute__route__drc_errors':3,'detailedroute__antenna__violating__nets':0,'detailedroute__antenna__violating__pins':0})['status'],'BLOCKED_ROUTER_VIOLATIONS')
 def test_area_not_fake_signoff(self):
  d=extract_area({'finish__design__instance__area':12.5},'Design area 20 um^2 25% utilization.')
  self.assertEqual(d['reported_design_area_um2'],20)
  self.assertIn('REQUIRES',d['classification'])
if __name__=='__main__':unittest.main()
