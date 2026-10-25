import unittest
from msif.core import fixture
from msif.simulation import create_testbench,test_vectors

class TestSimulationHarness(unittest.TestCase):
    def test_expected_vectors(self):
        model=fixture(2,4)
        vec=test_vectors(model,4)
        self.assertEqual(vec[0],[0]*4)
        self.assertEqual(vec[1],[127]*4)
        self.assertEqual(vec[2],[-128]*4)
    def test_verilog_tb(self):
        model=fixture(2,4)
        src=create_testbench(model,test_vectors(model,1),'fixed')
        self.assertIn('msif_fixed dut',src)
        self.assertIn('$fatal(1)',src)
        self.assertIn('out_valid',src)
if __name__=='__main__': unittest.main()
