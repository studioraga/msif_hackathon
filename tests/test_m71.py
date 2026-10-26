import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m71_compare import ERROR, VARIANTS, digest

class TestM71(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(VARIANTS,('programmable','fixed','rom'))
    def test_error_detection(self):
        for line in ['ERROR: failed', 'FATAL: stopped', '%Warning-LATCH: hello', '%Error: parse', 'FAIL: bad']:
            self.assertIsNotNone(ERROR.search(line))
    def test_normal_output(self):
        self.assertIsNone(ERROR.search('Found and reported 0 problems.'))
    def test_hash_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_text('abc')
            self.assertEqual(digest(p),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
