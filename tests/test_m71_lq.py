import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m71_lq import inventory, digest, safe_path

class TestM71LQ(unittest.TestCase):
    def test_inventory_known_cells(self):
        d={'modules': {'top': {'cells': {'a': {'type':'sky_a'}, 'b': {'type':'sky_a'}}}}}
        lib={'modules': {'sky_a': {}}}
        r=inventory(d,lib,'top')
        self.assertEqual(r['total_cells'],2)
        self.assertEqual(r['check'],'PASS')
    def test_inventory_fail_closed_unknown(self):
        r=inventory({'modules':{'top':{'cells':{'a':{'type':'$_AND_'}}}}},{'modules':{'sky_a':{}}},'top')
        self.assertEqual(r['check'],'FAIL')
        self.assertEqual(r['unknown_cells'],['$_AND_'])
    def test_empty_or_missing_fails(self):
        for design,lib in [({},{}),({'modules':{'top':{'cells':{}}}},{'modules':{'sky_a':{}}})]:
            with self.assertRaises(ValueError): inventory(design,lib,'top')
    def test_path_restrictions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'no spaces.lib';p.write_text('abc')
            with self.assertRaises(ValueError): safe_path(p)
            self.assertEqual(len(digest(p)),64)
