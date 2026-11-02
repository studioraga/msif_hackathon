"""Regression for M7.2 closure9 memory and async-FF proof prerequisites."""
import unittest
from m72_formal_equiv import yosys_script

class Closure10Formal(unittest.TestCase):
    def test_memories_lowered_before_miter(self):
        s=yosys_script('rtl','mapped','lib','msif_programmable')
        self.assertLess(s.index('\nproc\n'), s.index('\nmemory_map\n'))
        self.assertLess(s.index('\nmemory_map\n'),s.index('\nequiv_make '))
    def test_async_sampling_is_explicit_not_full_async_proof(self):
        s=yosys_script('rtl','mapped','lib','msif_fixed')
        self.assertGreater(s.index('\nasync2sync\n'),s.index('\nflatten\n'))
        self.assertLess(s.index('\nasync2sync\n'),s.index('\nequiv_simple\n'))
        self.assertIn('equiv_status -assert',s)
    def test_no_discarded_tops(self):
        s=yosys_script('rtl','mapped','lib','msif_rom')
        before=s.split('equiv_make')[0]
        self.assertNotIn('hierarchy -top',before)
