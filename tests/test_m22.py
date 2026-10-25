import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m22_verify import formal_rtl, sequential_tb, require_clean
from msif.core import fixture
from msif.simulation import test_vectors

class TestM22(unittest.TestCase):
    def setUp(self): self.model=fixture(2,4,2026)
    def test_formal_shape(self):
        txt=formal_rtl(self.model)
        self.assertEqual(txt.count('assert ('),2)
        self.assertIn('ref_0',txt)
        self.assertIn('opt_1',txt)
    def test_formal_rejects_wrong_shape(self):
        with self.assertRaises(ValueError): formal_rtl(fixture(16,64,2026))
    def test_testbench_covers_reset_and_hold(self):
        txt=sequential_tb(self.model,'fixed',test_vectors(self.model,32))
        self.assertIn('async reset failed',txt)
        self.assertIn('rst_n=1, in_valid=0',txt)
        self.assertIn('#1; rst_n=0; #1;',txt)
        self.assertLess(txt.index('rst_n=0; #1;'), txt.index('async reset failed'))
        self.assertIn('invalid hold',txt)
        self.assertIn('mid-stream async reset',txt)
    def test_fail_closed_marker(self):
        marker='PASS M2.2 fixed sequential 2x4 36 vectors'
        with self.assertRaises(RuntimeError): require_clean('ERROR: failure\n'+marker,marker)
        with self.assertRaises(RuntimeError): require_clean(marker+'\n'+marker,marker)
        require_clean(marker,marker)
