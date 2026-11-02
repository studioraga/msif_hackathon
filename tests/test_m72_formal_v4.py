"""Regression for lost miter branch (closure8.1)."""
import unittest
from pathlib import Path
from m72_formal_equiv import yosys_script

class FormalHierarchy(unittest.TestCase):
    def test_both_tops_survive_until_equiv_make(self):
        script = yosys_script(Path('rtl.sv'), Path('mapped.v'), Path('lib.lib'), 'msif_fixed')
        before, after = script.split('equiv_make msif_gold msif_gate msif_equiv', 1)
        self.assertIn('msif_gold', before)
        self.assertIn('msif_gate', before)
        self.assertNotIn('hierarchy -check -top', before)
        self.assertIn('hierarchy -check -top msif_equiv', after)
        self.assertIn('equiv_status -assert', after)
        self.assertNotIn('equiv_simple -undef', script)
    def test_library_is_functional_import(self):
        script=yosys_script('rtl.sv','gate.v','lib.lib','msif_rom')
        self.assertIn('read_liberty -ignore_miss_func lib.lib',script)
        self.assertNotIn('read_liberty -lib',script)
