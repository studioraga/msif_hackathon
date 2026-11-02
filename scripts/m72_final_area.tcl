# Project-owned OpenDB area inspection. Must be sourced after read_db.
# Write via MSIF_M72_AREA_OUT; does not claim PPA signoff.
set block [ord::get_db_block]
if {$block eq "NULL"} { error "M7.2: missing OpenDB block" }
set dbu [$block getDbUnitsPerMicron]
set core [$block getCoreArea]
set xspan [expr {double([$core xMax]-[$core xMin])/$dbu}]
set yspan [expr {double([$core yMax]-[$core yMin])/$dbu}]
set core_area [expr {$xspan*$yspan}]
set classes [dict create]
set counts [dict create]
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set typ [$master getType]
  set name [$master getName]
  set category "other"
  if {[string match *fill* $name]} {set category "filler"}
  if {[string match *tap* $name]} {set category "tap"}
  if {[string match *decap* $name]} {set category "decap"}
  if {[string match *clkbuf* $name]} {set category "clock_buffer"}
  if {[string match *diode* $name]} {set category "antenna"}
  set area [expr {double([$master getWidth])*[$master getHeight]/($dbu*$dbu)}]
  dict incr counts $category 1
  if {[dict exists $classes $category]} {dict set classes $category [expr {[dict get $classes $category]+$area}]} else {dict set classes $category $area}
}
set f [open $::env(MSIF_M72_AREA_OUT) w]
puts $f "core_area_um2=$core_area"
puts $f "dbu_per_micron=$dbu"
foreach k [lsort [dict keys $classes]] {
  puts $f "category.$k.area_um2=[dict get $classes $k]"
  puts $f "category.$k.count=[dict get $counts $k]"
}
close $f
puts "M72_AREA_RESEARCH_ONLY $::env(MSIF_M72_AREA_OUT)"
