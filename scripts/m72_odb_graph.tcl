# Read-db after Liberty/LEF available; generate canonical source-referred graph.
set b [ord::get_db_block]
if {$b eq "NULL"} {error "missing block"}
set f [open $::env(MSIF_GRAPH_OUT) w]
foreach inst [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} [$b getInsts]] {
    set n [$inst getName]
    set typ [[$inst getMaster] getName]
    puts $f "CELL\t$n\t$typ"
    foreach it [lsort -command {apply {{a b} {string compare [[$a getMTerm] getName] [[$b getMTerm] getName]}}} [$inst getITerms]] {
        set net [$it getNet]
        set netname "__UNCONNECTED__"
        if {$net ne "NULL"} {set netname [$net getName]}
        puts $f "PIN\t$n\t[[$it getMTerm] getName]\t$netname"
    }
}
foreach bt [$b getBTerms] {
    set net [$bt getNet]
    set netname "__UNCONNECTED__"
    if {$net ne "NULL"} {set netname [$net getName]}
    puts $f "PORT\t[$bt getName]\t$netname"
}
close $f
