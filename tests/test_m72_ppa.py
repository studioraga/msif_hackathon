import unittest,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/m72_ppa_compare.py'
spec=importlib.util.spec_from_file_location('m72_ppa_compare',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestPPA(unittest.TestCase):
 def test_missing_architecture_rejected(self):
  with self.assertRaises(ValueError):m.compare({'variants':{'programmable':{'status':'REPORTS_PRESENT_REVIEW_REQUIRED','artifacts':{}}}})
 def test_all_research_never_signoff(self):
  x={'variants':{v:{'status':'REPORTS_PRESENT_REVIEW_REQUIRED','artifacts':{'6_final.gds':'hash'},'timing_observations':{'worst_slack_max_ns':88.2}} for v in m.VARIANTS}}
  d=m.compare(x)
  self.assertEqual(d['status'],'RESEARCH_COMPARISON_NOT_SIGNOFF')
  self.assertIsNone(d['variants']['rom']['power_watts_qualified'])
  self.assertEqual(d['exact_lq_equivalence'],'NOT_VERIFIED')
