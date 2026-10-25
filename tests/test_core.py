import json,random,tempfile,unittest
from pathlib import Path
from msif.core import fixture,inference,write_build,generate,check
from msif.governance import validate_manifest
class TestMSIF(unittest.TestCase):
 def test_exhaustive_int4_int8(self):
  for w in range(-8,8):
   model=fixture(1,1);model['weights']=[[w]];model['bias']=[0]
   for x in range(-128,128):self.assertEqual(inference(model,[x]),[w*x])
 def test_full_shape(self):
  model=fixture(); x=[-128 if i%2 else 127 for i in range(64)]
  self.assertEqual(len(inference(model,x)),16)
 def test_deterministic(self):self.assertEqual(fixture(),fixture())
 def test_manifest_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   write_build(fixture(2,4),d);self.assertTrue(validate_manifest(d))
   with (Path(d)/'msif_fixed.sv').open('a') as f:f.write('//tampered\n')
   with self.assertRaises(ValueError):validate_manifest(d)
 def test_variants_present(self):
  model=fixture(1,4)
  for v in ('fixed','programmable','rom'):self.assertIn('endmodule',generate(model,v))
if __name__=='__main__':unittest.main()
