import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m72_p2b_checkpoint import audit
class TestP2bCheckpoint(unittest.TestCase):
 def test_no_fake_equivalence(self):
  from unittest.mock import patch
  with patch('m72_p2b_checkpoint.Path.is_file',return_value=True),patch('m72_p2b_checkpoint.digest',return_value='x'):
   d=audit({'variants':{'programmable':{'input':'x','accepted_sha256':'x','run':'FLOW_COMPLETE_NOT_EQUIVALENCE','final_odb_sha256':'a'}}})
  self.assertEqual(d['p2b_formal_equivalence'],'NOT_VERIFIED')
 def test_partial_is_not_complete(self):
  from unittest.mock import patch
  with patch('m72_p2b_checkpoint.Path.is_file',return_value=True),patch('m72_p2b_checkpoint.digest',return_value='x'):
   d=audit({'variants':{'rom':{'input':'x','accepted_sha256':'x','run':'BLOCKED'}}})
  self.assertFalse(d['route_all_complete'])
