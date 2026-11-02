import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from m72_graph_compare import compare
class GraphContinuity(unittest.TestCase):
 def test_net_renaming_is_allowed(self):
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a';b=Path(td)/'b'
   a.write_text('CELL\tu\tNAND\nPIN\tu\tA\tx\nPIN\tu\tY\ty\nPIN\tu\tVPWR\t__UNCONNECTED__\nPORT\tin\tx\nPORT\tout\ty\n')
   b.write_text(a.read_text().replace('\tx','\tnet_1').replace('\ty','\tnet_2'))
   self.assertEqual(compare(a,b)[0],[])
 def test_connection_mutation_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a';b=Path(td)/'b'
   a.write_text('CELL\tu\tNAND\nPIN\tu\tA\tx\nPIN\tu\tY\ty\nPORT\tin\tx\nPORT\tout\ty\n')
   b.write_text(a.read_text().replace('PIN\tu\tY\ty','PIN\tu\tY\tx'))
   self.assertIn('net endpoint connectivity differs', compare(a,b)[0])
 def test_missing_pin_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a';b=Path(td)/'b'
   a.write_text('CELL\tu\tNAND\nPIN\tu\tA\tx\nPORT\tin\tx\n')
   b.write_text('CELL\tu\tNAND\nPORT\tin\tx\n')
   with self.assertRaisesRegex(ValueError,'instance missing ITerms'):
    compare(a,b)
if __name__=='__main__':unittest.main()
