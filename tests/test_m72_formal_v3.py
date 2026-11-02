import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import m72_formal_equiv as f
class FormalV3(unittest.TestCase):
    def test_unsupported_unused_cells_can_be_skipped(self):
        x=f.yosys_script("rtl.sv","mapped.v","lib.lib","msif_programmable")
        self.assertIn("read_liberty -ignore_miss_func lib.lib",x)
        self.assertNotIn("hierarchy -check -top msif_gate",x)
        self.assertNotIn("hierarchy -check -top msif_gold",x)
        self.assertLess(x.index("equiv_make "),x.index("hierarchy -check -top msif_equiv"))
        self.assertIn("equiv_status -assert",x)
        self.assertNotIn("-lib ",x)
        self.assertNotIn("equiv_simple -undef",x)
    def test_necessary_induction(self):
        self.assertIn("equiv_induct -seq 32",f.yosys_script("a","b","c","d"))
