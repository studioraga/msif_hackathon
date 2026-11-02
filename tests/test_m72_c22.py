import tempfile,unittest,json
from pathlib import Path
import m72_c22_tt_coverage as tt
import m72_c22_vcd_workload as pw
class C22(unittest.TestCase):
 def test_tt_missing_fails_closed(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);(t/'inv.json').write_text('{}');self.assertEqual(tt.run(t/'inv.json',t/'out'),2)
   m=json.loads((t/'out/manifest.json').read_text());self.assertEqual(m['signoff'],'NOT_VERIFIED');self.assertTrue(m['issues'])
 def test_tt_valid_synthetic_only_dry(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);lib=t/'tt.lib';lib.write_text('timing');data={'libraries':[{'name':'sky130_fd_sc_hd__tt_025C_1v80.lib','path':str(lib),'sha256':tt.sha(lib)}],'designs':{}}
   for v in tt.V:
    data['designs'][v]={}
    for key in ('odb','sdc','spef'):
     p=t/f'{v}.{key}';p.write_text(key);data['designs'][v][key]={'path':str(p),'sha256':tt.sha(p)}
   (t/'inv.json').write_text(json.dumps(data));self.assertEqual(tt.run(t/'inv.json',t/'out'),0);m=json.loads((t/'out/manifest.json').read_text());self.assertEqual(m['status'],'TT_INPUTS_VERIFIED_NOT_EXECUTED');self.assertEqual(m['signoff'],'NOT_VERIFIED')
 def test_vcd_transitions(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'x.vcd';p.write_text('$scope module tb $end\n$var wire 1 ! clk $end\n$var wire 4 " activations [3:0] $end\n$upscope $end\n$enddefinitions $end\n#0\n0!\nb0000 "\n#5\n1!\n#10\n0!\nb1101 "\n')
   r=pw.scan_vcd(p);self.assertEqual(r['clock_records'],3);self.assertEqual(r['inputs']['activations'][-1][1],'1101')
 def test_vcd_bad_previous_proof_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);(t/'gls').mkdir();(t/'gls/manifest.json').write_text('{"status":"NOT_VERIFIED"}');(t/'root/build/m71_liberty/m71_lq').mkdir(parents=True);(t/'root/build/m71_liberty/m71_lq/evidence.json').write_text('{}');self.assertEqual(pw.run(t/'root',t/'flow',t/'gls',t/'out'),2)
   self.assertEqual(json.loads((t/'out/manifest.json').read_text())['power'],'NOT_VERIFIED')
if __name__=='__main__':unittest.main()
