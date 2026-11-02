import unittest,importlib.util,tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/m72_report_review.py'
spec=importlib.util.spec_from_file_location('m72_report_review',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TestCollector(unittest.TestCase):
 def test_drc_filename_optional_but_unverified(self):
  with tempfile.TemporaryDirectory() as t:
   flow=Path(t)
   for v in m.V:
    rel=Path('sky130hd')/f'msif_{v}'/f'msif_m72_{v}_normalized_v2'
    res=flow/'results'/rel;rep=flow/'reports'/rel;res.mkdir(parents=True);rep.mkdir(parents=True)
    for suffix in ('odb','gds','spef','sdc'):(res/f'6_final.{suffix}').write_text('artifact')
    (rep/'6_finish.rpt').write_text('wns max 0.00\nsetup violation count 0\n')
   d=m.collect(flow,'normalized_v2')
   self.assertEqual(d['status'],'REPORTS_COLLECTED_NOT_SIGNOFF')
   self.assertEqual(d['variants']['fixed']['route_drc_report']['status'],'NOT_EMITTED_BY_PINNED_FLOW')
