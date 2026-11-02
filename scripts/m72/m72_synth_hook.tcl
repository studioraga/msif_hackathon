# MSIF M7.2: call ONLY after pinned ORFS synth.tcl has written 1_2_yosys.v.
if {![info exists ::env(MSIF_M72_NORMALIZER)]} {
  error "MSIF_M72_NORMALIZER missing"
}
set out_dir $::env(RESULTS_DIR)
set raw_netlist $out_dir/1_2_yosys.v
set preserved $out_dir/1_2_yosys.raw.v
set staged $out_dir/1_2_yosys.compat.tmp.v
set receipt $out_dir/1_2_yosys.normalization.json
if {![file exists $raw_netlist]} {error "M7.2 synth output missing"}
if {[file exists $preserved] || [file exists $staged] || [file exists $receipt]} {
  error "M7.2 refuses to overwrite existing normalization artifacts; use new FLOW_VARIANT"
}
file copy $raw_netlist $preserved
if {[catch {exec python3 $::env(MSIF_M72_NORMALIZER) --input $preserved --output $staged --receipt $receipt} msg]} {
  error "M7.2 normalization rejected: $msg"
}
if {![file exists $staged] || ![file exists $receipt]} {
  error "M7.2 normalized output / receipt missing"
}
file rename -force -- $staged $raw_netlist
puts "MSIF_M72_NORMALIZED_EXPORT: $receipt"
