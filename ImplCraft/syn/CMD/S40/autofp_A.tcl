########################################################################################
######  DCICC FLOW - Version 4.1.0 (2015-10-15)
######  Owner : Anonymous , rc
########################################################################################

derive_pg_connection -power_net VDD -ground_net VSS -tie

#######################################
### Auto create power and ground straps
#######################################


## power ground parameter               {width  step    start	1st-row	2nd-row }
#set var(power_param,M2)		{0.14  	0.576   0       VDD VSS}
#set var(power_param,M3)		{0.320 	3.200	1.600   VDD VSS}
#set var(power_param,M4)		{0.330	2.304	0       VSS VDD}
set var(power_param,M5)         {0.520  5.040   0       VDD VSS}
set var(power_param,M6)         {0.520  5.040   0       VDD VSS}
set var(power_param,M7)         {0.520  5.040   0       VDD VSS}
set var(power_param,M8)         {0.806  7.938   0       VSS VDD}
set var(power_param,M9)         {0.806  7.938   0       VDD VSS}
set var(power_param,M10)        {1.638  15.876  0       VSS VDD}
set var(power_param,M11)        {1.638  15.876  0       VDD VSS}
set var(power_param,M12)        {4.680  45.360  0       VSS VDD}
set var(power_param,M13)        {5.850  56.700  0       VDD VSS}

#set var(power_param,M5)         {0.220  3.200   0       VDD VSS}
#set var(power_param,M6)         {0.220  3.200   0       VDD VSS}
#set var(power_param,M7)         {0.220  3.200   0       VDD VSS}
#set var(power_param,M8)         {0.270  5.040   0       VSS VDD}
#set var(power_param,M9)         {0.270  5.040   0       VDD VSS}
#set var(power_param,M10)        {0.750  10.080  0       VSS VDD}
#set var(power_param,M11)        {0.750  10.080  0       VDD VSS}
#set var(power_param,M12)        {3.100  36.000  0       VSS VDD}
#set var(power_param,M13)        {3.300  36.000  0       VDD VSS}


set all_available_metals [dict get $lib_common metal_layers all]
set all_used_metals [lrange $all_available_metals [lsearch $all_available_metals M5] [lsearch $all_available_metals $var(top_layer)]]

set placement_area(vertical) [lindex [get_placement_area] 2]
set placement_area(horizontal) [lindex [get_placement_area] 3]

set_pin_physical_constraints -depth [get_minimum_used_pin_depth $all_used_metals] [get_ports]

if {[file isfile $var(autofp,pin_cons)]} { source -verbose -echo $var(autofp,pin_cons) }

if {[sizeof_collection [get_terminals]]>0} { remove_objects [get_terminals] }

## set via rule to move via to center
set_preroute_advanced_via_rule
set preroute_ContactSizeSelection 0
set_preroute_advanced_via_rule -contact_code VIA12_LONG_H -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1}
set_preroute_advanced_via_rule -contact_code VIA23_LONG_H -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1}
set_preroute_advanced_via_rule -contact_code VIA34_LONG_H -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1}
set_preroute_advanced_via_rule -contact_code VIA45_LONG_H -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1}
set_preroute_advanced_via_rule -contact_code VIA56_LONG_V -move_via_to_center -rotation_mode off -size_by_array_dimensions {4 3}
set_preroute_advanced_via_rule -contact_code VIA67_LONG_V -move_via_to_center -rotation_mode off -size_by_array_dimensions {4 3}
#set_preroute_advanced_via_rule -contact_code -move_via_to_center -rotation_mode off -size_by_array_dimensions {}
#set_preroute_advanced_via_rule -contact_code -move_via_to_center -rotation_mode off -size_by_array_dimensions {}
#set_preroute_advanced_via_rule -contact_code -move_via_to_center -rotation_mode off -size_by_array_dimensions {}
#set_preroute_advanced_via_rule -contact_code -move_via_to_center -rotation_mode off -size_by_array_dimensions {}

###     create route guide for macro keepout
if {[sizeof_collection [all_macro_cells]]>0 && [llength $var(autofp,metal_respect_keepout)]>0} {
        my_create_preroute_route_guide_base_on_macro_keepout RG_MACRO_KEEPOUT_PREROUTE $var(autofp,metal_respect_keepout)
}

###	preroute M1 && M2
preroute_standard_cells -nets  {VDD VSS}  \
	-route_pins_on_layer M1 \
	-connect horizontal  \
	-pin_width_by_most_extended_pin  \
	-fill_empty_rows  \
	-port_filter_mode off \
	-cell_master_filter_mode off \
	-cell_instance_filter_mode off \
	-voltage_area_filter_mode off \
	-route_type {P/G Std. Cell Pin Conn} \
	-skip_macro_pins -do_not_route_over_macros -ignore_cell_boundary

#foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Std. Cell Pin Conn" && layer==M1}] { extend_pg_strap $one 0.16 0.16 }

#preroute_standard_cells -nets  {VDD VSS}  \
#	-route_pins_on_layer M2 \
#	-connect horizontal  \
#	-pin_width_by_most_extended_pin  \
#	-fill_empty_rows  \
#	-port_filter_mode off \
#	-cell_master_filter_mode off \
#	-cell_instance_filter_mode off \
#	-voltage_area_filter_mode off \
#	-route_type {P/G Std. Cell Pin Conn} \
#	-skip_macro_pins -do_not_route_over_macros -ignore_cell_boundary
#
###	For TSMC Virage LIBRARY REV 5.00A (01/15/2014), For M1 VSS

#set_preroute_drc_strategy -min_layer M1 -max_layer M2 -honor_shapes_of_nets all
foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Std. Cell Pin Conn" && layer==M1}] { extend_pg_strap $one 0.16 0.16 }
#set all_m1_pg_vdd_shapes [get_net_shapes -filter {route_type=="P/G Std. Cell Pin Conn" && layer==M1 && owner_net==VDD}]
#if {[get_attribute [index_collection [sort_collection $all_m1_pg_vdd_shapes bbox_lly] 0] bbox_lly]>0} {
#	set var(power_param,M2)	[lreplace $var(power_param,M2) 3 4 VSS VDD]
#}
#set_preroute_drc_strategy -min_layer M1 -max_layer M2

#set one_used_metal M2

#create_power_straps     -nets [lindex $var(power_param,$one_used_metal) 3] -layer $one_used_metal \
#                        -width [lindex $var(power_param,$one_used_metal) 0] \
#                        -direction [get_attribute [get_layers $one_used_metal] preferred_direction] \
#                        -configure step_and_stop \
#                        -start_at [lindex $var(power_param,$one_used_metal) 2] \
#                        -step [expr {[lindex $var(power_param,$one_used_metal) 1]*2}] \
#                        -stop $placement_area([get_attribute [get_layers $one_used_metal] preferred_direction]) \
#                        -ignore_cell_boundary -keep_floating_wire_pieces
#create_power_straps     -nets [lindex $var(power_param,$one_used_metal) 4] -layer $one_used_metal \
#                        -width [lindex $var(power_param,$one_used_metal) 0] \
#                        -direction [get_attribute [get_layers $one_used_metal] preferred_direction] \
#                        -configure step_and_stop \
#                        -start_at [expr {[lindex $var(power_param,$one_used_metal) 2]+[lindex $var(power_param,$one_used_metal) 1]}] \
#                        -step [expr {[lindex $var(power_param,$one_used_metal) 1]*2}] \
#                        -stop $placement_area([get_attribute [get_layers $one_used_metal] preferred_direction]) \
#                        -ignore_cell_boundary -keep_floating_wire_pieces

#foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M2}] { extend_pg_strap $one 0.16 0.16 }

## create power straps ( M3 ~ Top layer ) 
foreach one_used_metal $all_used_metals {
	set down_one_used_metal [lindex $all_available_metals [expr {[lsearch $all_available_metals $one_used_metal]-1}]]
	if {[string equal $down_one_used_metal M4]} {
		set down_one_used_metal M1
	}
	set_preroute_drc_strategy -min_layer $down_one_used_metal -max_layer $one_used_metal
				#-ignore_cell_boundary -advanced_via_rule	; for create_power_straps
	create_power_straps	-nets [lindex $var(power_param,$one_used_metal) 3] -layer $one_used_metal \
				-width [lindex $var(power_param,$one_used_metal) 0] \
				-direction [get_attribute [get_layers $one_used_metal] preferred_direction] \
				-configure step_and_stop \
				-start_at [lindex $var(power_param,$one_used_metal) 2] \
				-step [expr {[lindex $var(power_param,$one_used_metal) 1]*2}] \
				-stop $placement_area([get_attribute [get_layers $one_used_metal] preferred_direction]) \
				-ignore_cell_boundary -advanced_via_rule
	create_power_straps	-nets [lindex $var(power_param,$one_used_metal) 4] -layer $one_used_metal \
				-width [lindex $var(power_param,$one_used_metal) 0] \
				-direction [get_attribute [get_layers $one_used_metal] preferred_direction] \
				-configure step_and_stop \
				-start_at [expr {[lindex $var(power_param,$one_used_metal) 2]+[lindex $var(power_param,$one_used_metal) 1]}] \
				-step [expr {[lindex $var(power_param,$one_used_metal) 1]*2}] \
				-stop $placement_area([get_attribute [get_layers $one_used_metal] preferred_direction]) \
				-ignore_cell_boundary -advanced_via_rule
        if {[sizeof_collection [get_route_guides -quiet RG_MACRO_KEEPOUT_PREROUTE_${one_used_metal}_*]]>0} {
                remove_route_guide [get_route_guides -quiet RG_MACRO_KEEPOUT_PREROUTE_${one_used_metal}_*]
        }
	if {[string equal $one_used_metal M3]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M3}] { extend_pg_strap $one 0.16 0.16 }
	}
	if {[string equal $one_used_metal M4]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M4}] { extend_pg_strap $one 0.16 0.16 }
	}
	if {[string equal $one_used_metal M5]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M5}] { extend_pg_strap $one 0.16 0.16 }
	}
	if {[string equal $one_used_metal M6]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M6}] { extend_pg_strap $one 0.16 0.16 }
	}
	if {[string equal $one_used_metal M7]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M7}] { extend_pg_strap $one 0.249 0.249 }
	}
	if {[string equal $one_used_metal M8]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M8}] { extend_pg_strap $one 0.249 0.249 }
	}
	if {[string equal $one_used_metal M9]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M9}] { extend_pg_strap $one 0.504 0.504 }
	}
	if {[string equal $one_used_metal M10]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M10}] { extend_pg_strap $one 0.504 0.504 }
	}
	if {[string equal $one_used_metal M11]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M11}] { extend_pg_strap $one 1.8 1.8 }
	}
	if {[string equal $one_used_metal M12]} {
		foreach_in_collection one [get_net_shapes -filter {route_type=="P/G Strap" && layer==M12}] { extend_pg_strap $one 1.8 1.8 }
	}
}

###	resize via arrays
#define_user_attribute -class {via} -type string pg_strap_via_h
#define_user_attribute -class {via} -type string pg_strap_via_v
#
#set_attribute [get_vias -filter {route_type=="P/G Strap"}] pg_strap_via_v false
#set_attribute [get_vias -filter {route_type=="P/G Strap"}] pg_strap_via_h false
#
#foreach_in_collection one_pg_strap [get_net_shapes -filter {route_type=~"P/G *"}] {
#	set cur_pg_layer [get_attribute $one_pg_strap layer_name]
#	set cur_pg_width [get_attribute $one_pg_strap width]
#        unset -nocomplain cur_pg_con_vias
#	if {[string equal $cur_pg_layer M1]} { continue }
#	if {$cur_pg_width!=[lindex $var(power_param,$cur_pg_layer) 0]} { continue }
#        append_to_collection -unique cur_pg_con_vias [filter_collection [get_vias -quiet -filter {route_type=="P/G Strap"} -within [get_attribute $one_pg_strap bbox]] "upper_layer==$cur_pg_layer"]
#        append_to_collection -unique cur_pg_con_vias [filter_collection [get_vias -quiet -filter {route_type=="P/G Strap"} -within [get_attribute $one_pg_strap bbox]] "lower_layer==$cur_pg_layer"]
#        append_to_collection -unique cur_pg_con_vias [filter_collection [get_vias -quiet -filter {route_type=="P/G Strap"} -intersect [get_attribute $one_pg_strap bbox]] "upper_layer==$cur_pg_layer"]
#        append_to_collection -unique cur_pg_con_vias [filter_collection [get_vias -quiet -filter {route_type=="P/G Strap"} -intersect [get_attribute $one_pg_strap bbox]] "lower_layer==$cur_pg_layer"]
#	if {[sizeof_collection $cur_pg_con_vias]>0} {
#		if {[string equal $cur_pg_layer M3] || [string equal $cur_pg_layer M5] || 
#			[string equal $cur_pg_layer M7] || [string equal $cur_pg_layer M9]} {
#			set_attribute $cur_pg_con_vias pg_strap_via_v true
#		} else {
#			set_attribute $cur_pg_con_vias pg_strap_via_h true
#		}
#	}
#}
#
#set pg_via_VIA2 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA2 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA2]>0} {
#	set_via_array_size -array_size {1 2} $pg_via_VIA2
#}
#set pg_via_VIA3 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA3 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA3]>0} {
#	set_via_array_size -array_size {2 3} $pg_via_VIA3
#}
#set pg_via_VIA4 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA4 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA4]>0} {
#	set_via_array_size -array_size {2 3} $pg_via_VIA4
#}
#set pg_via_VIA5 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA5 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA5]>0} {
#	set_via_array_size -array_size {2 3} $pg_via_VIA5
#}
#set pg_via_VIA6 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA6 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA6]>0} {
#	set_via_array_size -array_size {2 3} $pg_via_VIA6
#	set_attribute $pg_via_VIA6 x_pitch 0.23
#	set_attribute $pg_via_VIA6 y_pitch 0.23
#}
#set pg_via_VIA7 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA7 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA7]>0} {
#	set_via_array_size -array_size {3 3} $pg_via_VIA7
#	set_attribute $pg_via_VIA7 x_pitch 0.23
#	set_attribute $pg_via_VIA7 y_pitch 0.23
#}
#set pg_via_VIA8 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA8 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA8]>0} {
#	set_via_array_size -array_size {1 2} $pg_via_VIA8
#}
#set pg_via_VIA9 [get_vias -quiet -filter {route_type=="P/G Strap" && via_layer==VIA9 && pg_strap_via_h==true && pg_strap_via_v==true}]
#if {[sizeof_collection $pg_via_VIA9]>0} {
#	set_via_array_size -array_size {4 1} $pg_via_VIA9
#	set_attribute $pg_via_VIA9 y_pitch 0.7
#}
#
#set all_used_metals [concat M2 $all_used_metals]
#foreach one_used_metal $all_used_metals {
#	foreach_in_collection one_shape [get_net_shapes -filter "route_type=~\"P/G*\" && layer==$one_used_metal"] {
#		reshape_endpoints_baseone_vias $one_shape
#	}
#}

set_preroute_drc_strategy -min_layer M1 -max_layer M13
### remove all PGs
#remove_route_by_type -pg_strap -pg_std_cell_pin_conn -nets {VDD VSS}
