import unittest, tempfile
from pathlib import Path
from m72_postroute_gls import routed_cell_types, check_source

class RoutedModels(unittest.TestCase):
 def test_extract_types_without_guessing(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'6_final.v'
   f.write_text('module msif_fixed;\nsky130_fd_sc_hd__buf_4 _abc_ (.A(a),.X(x));\nsky130_fd_sc_hd__dlygate4sd3_1 \\hold1 (.A(a),.X(x));\nendmodule\n')
   self.assertEqual(routed_cell_types(f),['sky130_fd_sc_hd__buf_4','sky130_fd_sc_hd__dlygate4sd3_1'])
 def test_unrecognized_netlist_fails(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'empty.v';f.write_text('module top; endmodule')
   with self.assertRaises(ValueError):routed_cell_types(f)
 def test_source_requires_wrapper_tree(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):check_source(Path(d))
