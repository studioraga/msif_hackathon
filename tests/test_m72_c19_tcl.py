import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / 'scripts/m72_c18_classified_area.tcl'

# Mock only OpenDB interface; the actual Tcl is sourced by tclsh.
MOCK = r'''
proc ord::get_db_block {} {return block}
proc block {method args} {
 switch -- $method {
  getDbUnitsPerMicron {return 1000}
  getCoreArea {return rect}
  getInsts {return {instA instB instC}}
  default {error "unknown block method $method"}
 }
}
proc rect {method args} {switch -- $method {xMax {return 100000} yMax {return 100000} xMin {return 0} yMin {return 0} default {error bad}}}
foreach {instance master} {instA masterA instB masterB instC masterC} {
 proc $instance {method args} [format {if {$method eq "getMaster"} {return %s}; error bad} $master]
}
proc masterA {method args} {switch -- $method {getName {return sky130_fd_sc_hd__nand2_1} getType {return CORE} getWidth {return 2000} getHeight {return 3000} default {error bad}}}
proc masterB {method args} {switch -- $method {getName {return sky130_fd_sc_hd__fill_1} getType {return CORE_SPACER} getWidth {return 1000} getHeight {return 3000} default {error bad}}}
proc masterC {method args} {switch -- $method {getName {return sky130_fd_sc_hd__clkbuf_8} getType {return CORE_CLOCK} getWidth {return 3000} getHeight {return 3000} default {error bad}}}
source $::env(MSIF_C19_TCL)
'''
class TclExecution(unittest.TestCase):
 def test_actual_tcl_with_mocked_db(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)
   env=dict(os.environ,MSIF_C19_TCL=str(TCL),MSIF_M72_AREA_OUT=str(out/'area.txt'),MSIF_M72_MASTERS_OUT=str(out/'masters.txt'))
   process=subprocess.run(['tclsh'],input='namespace eval ord {}\n'+MOCK,text=True,capture_output=True,env=env)
   self.assertEqual(process.returncode,0,process.stderr)
   self.assertNotIn('extra characters',process.stdout+process.stderr)
   a=(out/'area.txt').read_text()
   self.assertIn('category.functional_or_unresolved.area_um2=6.0',a)
   self.assertIn('category.filler.area_um2=3.0',a)
   self.assertIn('category.clock_tree_named.area_um2=9.0',a)
   self.assertIn('category.functional_or_unresolved.count=1',a)
   self.assertIn('classification=NAME_HEURISTIC_REVIEW_REQUIRED',a)
   self.assertIn('sky130_fd_sc_hd__nand2_1',(out/'masters.txt').read_text())
 def test_erroneous_expression_not_present(self):
  self.assertNotIn('0.0}+$area',TCL.read_text())
