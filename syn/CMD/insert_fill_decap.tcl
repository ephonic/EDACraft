########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
report_vt_filler_rule

set filler_with_metal		[dict get $lib_define $main_lib_name function_cell fill_metal]
set lib_listdecap_cell		[dict get $lib_define $main_lib_name function_cell predecap]
set vt_pair_list		""

set die_size_bbox [get_attribute [get_die_areas] bbox]
set delta_move   [expr {([lindex $die_size_bbox 1 0]-[lindex $die_size_bbox 0 0])*2}]
set delta_back   [expr {0-$delta_move}]
set pgcon_m1_vss [get_net_shapes -quiet -filter {route_type=~"P/G*" && layer=="M1" && owner_net=="VSS"}]
if {[sizeof_collection $pgcon_m1_vss]>0} {
	set_object_snap_type -enabled false
	move_objects -ignore_fixed -delta "$delta_move 0" $pgcon_m1_vss
	set_object_snap_type -enabled true
}

# insert with-metal fillers (or decaps)
if {$var(insert,listdecap)} {
	set_left_right_filler_rule -lib_cell [dict get $nhp_predefine listdecap_cells] \
		-left $lib_listdecap_cell -right $lib_listdecap_cell
}
if {$var(insert,postdecap)} {
	if {$var(insert,eco)} {
		insert_stdcell_filler -respect_keepout -cell_with_metal [dict get $lib_define $eco_lib_name function_cell_eco fill_metal]
	}
	if {$var(insert,listdecap)} { remove_all_spacing_rule }
	insert_stdcell_filler -respect_keepout -cell_with_metal $filler_with_metal
	insert_stdcell_filler -respect_keepout -cell_with_metal [lindex $filler_with_metal end]
}

# insert without-metal fillers, main lib
#insert_stdcell_filler -cell_without_metal [concat $ecolib_fillers_without_metal($main_lib_name) [lrange $lib_fillers_without_metal($main_lib_name) 0 end-1]]
insert_stdcell_filler -respect_keepout -cell_without_metal [concat \
			[dict get $lib_define $eco_lib_name function_cell_eco fill_no_metal] \
			[lrange [dict get $lib_define $main_lib_name function_cell fill_no_metal] 0 end-1] \
			]

# define vt-filler rules
set all_vt_lib_list $final_lib_list
if {$eco_ref_lib ni $all_vt_lib_list} {
	lappend all_vt_lib_list $eco_ref_lib
}
foreach mvt_one $all_vt_lib_list {
	set_cell_vt_type -library [dict get $lib_define $mvt_one mw] -vt_type $mvt_one
	if {$var(insert,eco) && [string equal $mvt_one $eco_ref_lib]} {
		set_cell_vt_type -library [dict get $lib_define $eco_lib_name mw] -vt_type $mvt_one
	}
	set_vt_filler_rule -threshold_voltage "$mvt_one $mvt_one" -lib_cell \
		[lindex [dict get $lib_define $mvt_one function_cell fill_no_metal] end]
	lappend vt_pair_list "$mvt_one $mvt_one"
	set_vt_filler_rule -threshold_voltage "$mvt_one" -lib_cell \
		[lindex [dict get $lib_define $mvt_one function_cell fill_no_metal] end]
	lappend vt_pair_list "$mvt_one"
}

for {set i 0} {$i<[llength $all_vt_lib_list]} {incr i 1} {
	set target_vt	[lindex $all_vt_lib_list $i]
	foreach one_vt_lib [lrange $all_vt_lib_list [expr {$i+1}] end] {
		set_vt_filler_rule -threshold_voltage "$one_vt_lib $target_vt" -lib_cell \
			[lindex [dict get $lib_define $target_vt function_cell fill_no_metal] end]
		lappend vt_pair_list "$one_vt_lib $target_vt"
	}
}
report_vt_filler_rule

# insert without-metal fillers, 1x filler
insert_stdcell_filler -respect_keepout

# remove previous defined vt filler rule
foreach one_vt_pair $vt_pair_list {
	remove_vt_filler_rule -threshold_voltage $one_vt_pair
}
if {$var(insert,listdecap)} {
	remove_left_right_filler_rule -lib_cell [dict get $nhp_predefine listdecap_cells]
}

if {[sizeof_collection $pgcon_m1_vss]>0} {
	set_object_snap_type -enabled false
	move_objects -ignore_fixed -delta "$delta_back 0" $pgcon_m1_vss
	set_object_snap_type -enabled true
	unset -nocomplain delta_move delta_back
}
unset -nocomplain die_size_bbox
