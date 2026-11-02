import unittest
from pathlib import Path
from m72_formal_equiv import yosys_script
class FormalV2(unittest.TestCase):
    def test_liberty_functional_not_blackbox(self):
        s = yosys_script(Path('rtl.sv'),Path('mapped.v'),Path('sky.lib'),'msif_fixed')
        self.assertIn('read_liberty -ignore_miss_func sky.lib', s)
        self.assertNotIn('read_liberty -lib', s)
        self.assertIn('equiv_make msif_gold msif_gate msif_equiv', s)
        self.assertIn('hierarchy -check -top msif_equiv', s)
        self.assertNotIn('hierarchy -check -top msif_gate', s)
        self.assertLess(s.index('equiv_make msif_gold msif_gate msif_equiv'), s.index('hierarchy -check -top msif_equiv'))
        self.assertNotIn('read_verilog -sv sky.lib', s)
    def test_fail_closed_status_and_no_undef_relaxation(self):
        s=yosys_script(Path('rtl'),Path('gate'),Path('model'),'msif_fixed')
        self.assertIn('equiv_status -assert',s)
        self.assertIn('check -assert',s)
        self.assertNotIn('equiv_simple -undef',s)
