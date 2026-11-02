import tempfile
import unittest
from pathlib import Path
from m72_normalize import run, normalize
class TestM72Normalize(unittest.TestCase):
    def test_unsigned_structural_noop(self):
        source = "module x(input clk);\nwire s;\nendmodule\n"
        updated, changed = normalize(source)
        self.assertEqual(source, updated)
        self.assertEqual(changed, [])


    def test_declarations_only(self):
        x='module t;\n input signed [31:0] x;\n wire signed [31:0] x;\n sky130_fd_sc_hd__inv_1 u1 (.A(x[0]),.Y(y));\nendmodule\n'
        y,lines=normalize(x)
        self.assertEqual(lines,[2,3])
        self.assertIn('input  [31:0] x;',y)
        self.assertIn('u1 (.A(x[0]),.Y(y))',y)
    def test_bad_signed_expression_fails(self):
        with self.assertRaises(ValueError): normalize('assign x = $signed(y);\n')
    def test_non_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.v';q=Path(d)/'b.v'
            p.write_text('module t;\n input signed [7:0] x;\nendmodule\n')
            run(p,q)
            with self.assertRaises(ValueError): run(p,q)
if __name__=='__main__':unittest.main()
