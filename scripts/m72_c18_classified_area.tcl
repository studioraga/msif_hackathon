# Read-only OpenDB master classification. Research evidence, NOT signoff.
set block [ord::get_db_block]
if {$block eq "NULL"} {error "Missing OpenDB block"}
set dbu [$block getDbUnitsPerMicron]
if {$dbu <= 0} {error "Invalid OpenDB units"}
set core [$block getCoreArea]
set corearea [expr {double([$core xMax]-[$core xMin])*([$core yMax]-[$core yMin])/($dbu*$dbu)}]
if {$corearea <= 0} {error "Invalid core area"}
set counts [dict create]
set areas [dict create]
set masters [dict create]
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set name [$m getName]
  set typ [$m getType]
  set n [string tolower $name]
  set cat "functional_or_unresolved"
  if {[string match *fill* $n]} {set cat "filler"} elseif {[string match *tap* $n]} {set cat "tap"} elseif {[string match *decap* $n]} {set cat "decap"} elseif {[string match *diode* $n]} {set cat "antenna"} elseif {[regexp {clkbuf|clkdly|clkinv|clkinvlp} $n]} {set cat "clock_tree_named"} elseif {[regexp {dlygate} $n]} {set cat "delay_gate_named"} elseif {[regexp {tiehi|tielo|conb} $n]} {set cat "tie_named"} elseif {[regexp {^sky130_fd_sc_hd__buf_|^sky130_fd_sc_hd__inv_} $n]} {set cat "buffer_inverter_named"}
  set area [expr {double([$m getWidth])*[$m getHeight]/($dbu*$dbu)}]
  dict incr counts $cat
  set previous_area 0.0
  if {[dict exists $areas $cat]} {set previous_area [dict get $areas $cat]}
  dict set areas $cat [expr {$previous_area + $area}]
  dict incr masters "$cat/$name/$typ"
}
set f [open $::env(MSIF_M72_AREA_OUT) w]
puts $f "core_area_um2=$corearea"
puts $f "dbu_per_micron=$dbu"
puts $f "classification=NAME_HEURISTIC_REVIEW_REQUIRED"
foreach k [lsort [dict keys $counts]] {
 puts $f "category.$k.count=[dict get $counts $k]"
 puts $f "category.$k.area_um2=[dict get $areas $k]"
}
close $f
set mf [open $::env(MSIF_M72_MASTERS_OUT) w]
foreach k [lsort [dict keys $masters]] {puts $mf "$k=[dict get $masters $k]"}
close $mf
puts "M72_C18_AREA_CLASSIFIED_REVIEW_REQUIRED"
