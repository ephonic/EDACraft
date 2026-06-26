#################################################################################
# High Performance Core Script Setup
# Script: proc_auto_weights.tcl
# Version: G-2012.06-SP4 (January 31, 2013)
# Copyright (C) 2007-2013 Synopsys, Inc. All rights reserved.
#################################################################################

# Automatically assign path group weights based on WNS/TNS/NVP WNS and TNS are adjusted for clock period"

proc proc_sort_hash {args} {

  parse_proc_arguments -args ${args} opt

  upvar $opt(hash) myarr

  set given    "[info exists opt(-values)][info exists opt(-dict)][info exists opt(-reverse)]"

  set key_list  [array names myarr]

  switch $given {
    000 { return [lsort -real $key_list] }
    001 { return [lsort -real -decreasing $key_list] }
    010 { return [lsort -dictionary $key_list] }
    011 { return [lsort -dictionary -decreasing $key_list] }
  }
  
  foreach {a b} [array get myarr] { lappend full_list [list $a $b] }

  switch $given {
    100 { set sfull_list [lsort -real -index 1 $full_list] }
    101 { set sfull_list [lsort -real -index 1 -decreasing $full_list] }
    110 { set sfull_list [lsort -index 1 -dictionary $full_list] }
    111 { set sfull_list [lsort -index 1 -dictionary -decreasing $full_list] }

  }

  foreach i $sfull_list { lappend sorted_key_list [lindex $i 0] }
  return $sorted_key_list
}

define_proc_attributes proc_sort_hash -info "USER PROC:sorts a hash based on options and returns sorted keys list\nUSAGE: set sorted_keys \[proc_sort_hash hash_name_without_dollar\]" \
      -define_args { \
                  { -reverse 	"reverse sort"      			""              	boolean optional }
                  { -dict 	"dictionary sort, default numerical"	""              	boolean optional }
                  { -values 	"sort values, default keys"      	""              	boolean optional }
                  { hash   	"hash"         				"hash"            	list    required }
                  }

	
proc proc_auto_weights {args} {

  parse_proc_arguments -args $args results
  set wns_flag [info exists results(-wns)]
  set tns_flag [info exists results(-tns)]
  set nvp_flag [info exists results(-nvp)]
  set reset_flag [info exists results(-reset)]
  set d_flag   [info exists results(-dont_apply)]
  set verbose   [info exists results(-verbose)]
  set o_flag   [info exists results(-output)]
  set g_flag   [info exists results(-exclude_groups)]

  if {$reset_flag} {
    echo -n "Resetting all path group weights to 1 ...."
    foreach_in_collection g [get_path_groups] { group_path -name [get_object_name $g] -weight 1 }
    echo " Done"
    return
  }

  #if no wns tns or nvp switches are given then set tns and nvp, this is the default
  if {!$wns_flag&&!$tns_flag&&!$nvp_flag} { 
    set wns_flag 0
    set tns_flag 1
    set nvp_flag 1
    append line "Clock Period Adjusted TNS and NVP will be used as criteria for path group weights"
  } else {
    append line "Clock Period Adjusted "
    if {$wns_flag} { append line "WNS " }
    if {$tns_flag} { append line "TNS " }
    if {$nvp_flag} { append line "NVP " }
    append line "will be used as criteria for path group weights"
  }

  if {$o_flag} { set file $results(-output) } else { set file "auto_weights.tcl" }
  if {$g_flag} { set given_g $results(-exclude_groups) }

  if {$g_flag} { 
    set exclude [get_attr -quiet [get_path_group -quiet $given_g] full_name]
    if {[llength $exclude]<1} { puts "ERROR!! Unable to find given path group $given_g with \"get_path_group $given_g\"\nExiting...\n"; return }
    foreach e $exclude { set EXCLUDE($e) 1 }
  }

  #get report_qor file
  echo -n "\nRunning report_qor -nosplit .... "
  redirect -var x { report_qor -nosplit -sig 3}
  echo "Done\n"

  echo "$line\n"

  #process report_qor file
  set i 0
  set flag 0
  foreach line [split $x "\n"] {
    incr i
    #modify group name if it is already processed in another scenario
    if {[regexp {^\s*Timing Path Group\s+\'(\S+)\'} $line match group]} {
      #echo -n "$group\t"
    } elseif {[regexp {^\s*Critical Path Slack\s*:\s*(\S+)} $line match wns]} {
      #echo -n "$wns\t"
    } elseif {[regexp {^\s*Critical Path Clk Period\s*:\s*(\S+)} $line match per]} {
      #echo -n "$per\t"
      if { $per == "n/a"} { set per 0 }
    } elseif {[regexp {^\s*Total Negative Slack\s*:\s*(\S+)} $line match tns]} {
      #echo -n "$tns\t"
    } elseif {[regexp {^\s*No\. of Violating Paths\s*:\s*(\S+)} $line match nvp]} {
      #echo "$nvp"
      #nvp reached, now process group
      if {$nvp>0&&$per>0&&$wns<0} {
        #modified i.e. period adjusted wns=wns/per and tns=tns/period
        set m_wns [expr {double($wns)/$per}]
        set m_tns [expr {double($tns)/$per}]
        #save group data if the group does not exist and is not excluded or if it exists and the current modified tns is greater than prior saved data
        if {(![info exists GROUPS($group)]&&![info exists EXCLUDE($group)])||([info exists GROUPS($group)]&&$m_tns>$GROUP_M_TNS($group))} {
          set flag 1
          set GROUPS($group) 1
          set GROUP_WNS($group) $wns
          set GROUP_PER($group) $per
          set GROUP_TNS($group) $tns
          set GROUP_NVP($group) $nvp
          set GROUP_M_WNS($group) $m_wns
          set GROUP_M_TNS($group) $m_tns
          set GROUP_M_NVP($group) $nvp
        }
      }
    }
  }

  #return if no failing groups
  if {!$flag} { return "No failing path groups, No weighting applied, Exiting ....\n" }

  set out [open $file w]

  #find worst modified wns, tns and nvp
  set w_wns $GROUP_M_WNS([lindex [proc_sort_hash -values GROUP_M_WNS] 0])
  set w_tns $GROUP_M_TNS([lindex [proc_sort_hash -values GROUP_M_TNS] 0])
  set w_nvp $GROUP_M_NVP([lindex [proc_sort_hash -values -reverse GROUP_M_NVP] 0])
  
  #now create weighted wns, tns and nvp weighted = value/worstvalue
  foreach g [array names GROUPS] { set GROUP_W_WNS($g) [expr {$GROUP_M_WNS($g)/$w_wns}] }
  foreach g [array names GROUPS] { set GROUP_W_TNS($g) [expr {$GROUP_M_TNS($g)/$w_tns}] }
  foreach g [array names GROUPS] { set GROUP_W_NVP($g) [expr {$GROUP_M_NVP($g)/$w_nvp}] }

  #initialy net_weights to 0 for all groups
  foreach g [array names GROUPS] { set GROUP_NET_WEIGHT($g) 0.0 }

  #consider wns in net weight
  if {$wns_flag} { foreach g [array names GROUPS] { set GROUP_NET_WEIGHT($g) [expr {$GROUP_NET_WEIGHT($g)+$GROUP_W_WNS($g)}] } }

  #consider tns in net weight
  if {$tns_flag} { foreach g [array names GROUPS] { set GROUP_NET_WEIGHT($g) [expr {$GROUP_NET_WEIGHT($g)+$GROUP_W_TNS($g)}] } }

  #consider nvp in net weight
  if {$nvp_flag} { foreach g [array names GROUPS] { set GROUP_NET_WEIGHT($g) [expr {$GROUP_NET_WEIGHT($g)+$GROUP_W_NVP($g)}] } }

  #sort the groups based on net weights
  set sorted_groups [proc_sort_hash -values -reverse GROUP_NET_WEIGHT]

  #weights go from 2-20 with intervals of 2 for failing groups, if too many faling groups cap at 20
  set max_weight [expr [llength $sorted_groups]*2]
  if {$max_weight>20} { set max_weight 20 }

  #write out to file
  #reset all path group weights to 1 first
  puts $out {echo "Resetting ALL Path Group Weights to 1 ...."}
  puts $out {foreach_in_collection g [get_path_groups] { group_path -name [get_object_name $g] -weight 1 }}
  puts $out ""

  puts $out {echo "Applying new weights for failing groups ...."}
  set weight $max_weight
  if {$verbose} {

    echo "ADJUSTED_WNS = WNS/PERIOD"
    echo "ADJUSTED_TNS = TNS/PERIOD"
    echo "WNS_CRITERIA = ADJUSTED_WNS/Worst_ADJUSTED_WNS"
    echo "TNS_CRITERIA = ADJUSTED_TNS/Worst_ADJUSTED_TNS"
    echo "NVP_CRITERIA = NVP/Worst_NVP"
    echo "CRITERIA = WNS_CRITERIA+TNS_CRITERIA+NVP_CRITERIA (default)\n"

    echo "[format "%-30s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s" "" "" "" "" "" ADJUSTED ADJUSTED "BY WNS" "BY TNS" "BY NVP" NET GROUP]"
    echo "[format "%-30s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s" GROUP PERIOD WNS TNS NVP WNS TNS CRITERIA CRIERIA CRITERIA CRITERIA WEIGHT]"
    echo "-------------------------------------------------------------------------------------------------------------------------------------------------------";
  } else {
    echo "[format "%-30s %10s %10s %10s %10s %10s %10s" GROUP PERIOD WNS TNS NVP CRITERIA WEIGHT]"
    echo "------------------------------------------------------------------------------------------------";
  }
  foreach g $sorted_groups {
    if {$verbose} {
      echo "[format "%-30s %10s %10s %10s %10.0f %10.3f %10.3f %10.1f %10.1f %10.1f %10.2f %10s" $g $GROUP_PER($g) $GROUP_WNS($g) $GROUP_TNS($g) $GROUP_M_NVP($g) $GROUP_M_WNS($g) $GROUP_M_TNS($g) $GROUP_W_WNS($g) $GROUP_W_TNS($g) $GROUP_W_NVP($g) $GROUP_NET_WEIGHT($g) $weight]"
    } else {
      echo "[format "%-30s %10s %10s %10s %10.0f %10.2f %10s" $g $GROUP_PER($g) $GROUP_WNS($g) $GROUP_TNS($g) $GROUP_M_NVP($g) $GROUP_NET_WEIGHT($g) $weight]"
    }
    puts $out "group_path -name $g -weight $weight"
    set weight [expr $weight-2]
    #since all sorted_groups are failing the minimum weight they get is 2
    if {$weight<2} { set weight 2 }
  }

  if {$verbose} {
    echo "-------------------------------------------------------------------------------------------------------------------------------------------------------";
  } else {
    echo "------------------------------------------------------------------------------------------------";
  }
  close $out
  echo "Created path group weights script $file"
  if {!$d_flag} {
    echo "Sourcing path group weights script $file ...."
    source -e $file
  }
echo ""
}
define_proc_attributes proc_auto_weights -info "USER PROC: creates and sources a path group weights file with weights from 2-20 with intervals of 2 for failing path groups based on wns/tns/nvp" \
          -define_args {
          {-wns     "Optional - include wns as a criteria in sorting path groups, default is -tns -nvp" "" boolean optional}
          {-tns     "Optional - include tns as a criteria in sorting path groups, default is -tns -nvp" "" boolean optional}
          {-nvp     "Optional - include nvp as a criteria in sorting path groups, default is -tns -nvp" "" boolean optional}
          {-reset   "Optional - resets all path group weights to 1 and exits" "" boolean optional}
          {-verbose "Optional - displays formulas and intermediate results on how weights are calculated" "" boolean optional}
          {-dont_apply     "Optional - dont apply path group weights just create the output file, default group weights file is sourced" "" boolean optional}
          {-output "Optional - Output file name, default is auto_weights.tcl" "<file>" string optional}
          {-exclude_groups "Optional - list of path groups to exclude such as any ios, default none" "<pathgroups list>" string  optional}
          }

echo "\tproc_auto_weights"

