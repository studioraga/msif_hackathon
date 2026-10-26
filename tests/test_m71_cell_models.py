import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from m71_cell_models import assemble

class TestActualMappedCellModels(unittest.TestCase):
    def test_missing_top_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td);(src/'cells').mkdir();(src/'models').mkdir()
            with self.assertRaises(ValueError):
                assemble({'modules':{}}, 'top',src,src/'out.v')
    def test_missing_wrapper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td);(src/'cells').mkdir();(src/'models').mkdir()
            mapped={'modules':{'top':{'cells':{'x':{'type':'sky130_fd_sc_hd__nand2_1'}}}}}
            with self.assertRaises(FileNotFoundError):
                assemble(mapped,'top',src,src/'out.v')
    def test_unknown_cells_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td);(src/'cells').mkdir();(src/'models').mkdir()
            mapped={'modules':{'top':{'cells':{'x':{'type':'$_AND_'}}}}}
            with self.assertRaises(ValueError):
                assemble(mapped,'top',src,src/'out.v')
