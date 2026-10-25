import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from m21_verify import RTL, TB, validate_simulation_output, validate_formal_output

class TestM21Generation(unittest.TestCase):
    def test_full_domain_loop(self):
        self.assertIn('wi=-8; wi<=7', TB)
        self.assertIn('xi=-128; xi<=127', TB)
        self.assertIn('count != 4096', TB)
    def test_formal_assertion(self):
        self.assertIn('assert(shift_add == mul_ref)', RTL)
        self.assertIn('sx <<< 3', RTL)

class TestM21FailClosed(unittest.TestCase):
    def test_assertions_only_in_formal_build(self):
        self.assertIn('`ifdef FORMAL', RTL)
        self.assertIn('`endif', RTL)
    def test_simulation_error_overrides_pass(self):
        with self.assertRaises(RuntimeError):
            validate_simulation_output('ERROR: assertion failed\nPASS M2.1 exhaustive RTL 4096 vectors\n')
    def test_simulation_pass_once(self):
        validate_simulation_output('PASS M2.1 exhaustive RTL 4096 vectors\n')
    def test_missing_pass_rejected(self):
        with self.assertRaises(RuntimeError):
            validate_simulation_output('simulation finished\n')
    def test_formal_failure_rejected(self):
        with self.assertRaises(RuntimeError):
            validate_formal_output('SAT proof finished - no model found: FAILURE!')
