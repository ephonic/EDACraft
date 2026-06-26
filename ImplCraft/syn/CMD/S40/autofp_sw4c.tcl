########################################################################################
######  DCICC FLOW - Version 4.1.0 (2015-10-15), For T40
######  Owner : Anonymous , rc
########################################################################################
set autopg_start        [clock seconds]
echo "######\tAuto PG Start : [date]" > ./$icc_finalopt/report/autopg.log

derive_pg_connection -power_net VDD -ground_net VSS 
derive_pg_connection -power_net VDD -ground_net VSS -tie

#######################################
### Auto create power and ground straps
#######################################


## power ground parameter               {width  step    start	1st-row	2nd-row }
set var(power_param,M2)        {0.15  	1.68    0       VSS VDD}
set var(power_param,M3)        {0.4  	3.36    0       VDD VSS}
set var(power_param,M4)        {0.4  	3.36    0       VSS VDD}
set var(power_param,M5)        {0.4	3.36    0       VDD VSS}  
set var(power_param,M6)        {0.4	3.36    0       VSS VDD}
set var(power_param,M7)        {0.84	6.72    0       VDD VSS}  
set var(power_param,M8)        {0.84	6.72    0       VSS VDD}
set var(power_param,M9)       	{1.68	13.44   0 	VDD VSS}  
set var(power_param,M10)       {3.36	13.44   0	VSS VDD}  


set all_available_metals [dict get $lib_common metal_layers all]
set all_used_metals [lrange $all_available_metals [lsearch $all_available_metals M3] [lsearch $all_available_metals $var(top_layer)]]

set placement_area(vertical) [lindex [get_placement_area] 2]
set placement_area(horizontal) [lindex [get_placement_area] 3]

#set_pin_physical_constraints -depth [get_minimum_used_pin_depth $all_used_metals] [get_ports]

#if {[file isfile $var(autofp,pin_cons)]} { source -verbose -echo $var(autofp,pin_cons) }

remove_objects [get_terminals]

## set via rule to move via to center
set_preroute_advanced_via_rule
set_preroute_advanced_via_rule -contact_code via23 -move_via_to_center -rotation_mode off -size_by_via_area {0.40 0.15} -cut_spacings {0.07 0.07}
set_preroute_advanced_via_rule -contact_code via34 -move_via_to_center -rotation_mode off -size_by_via_area {0.40 0.40} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via45 -move_via_to_center -rotation_mode off -size_by_via_area {0.40 0.40} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via56 -move_via_to_center -rotation_mode off -size_by_via_area {0.40 0.40} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via67 -move_via_to_center -rotation_mode off -size_by_via_area {0.84 0.40} -cut_spacings {0.16 0.16}
set_preroute_advanced_via_rule -contact_code via78 -move_via_to_center -rotation_mode off -size_by_via_area {0.84 0.84} -cut_spacings {0.16 0.16}
set_preroute_advanced_via_rule -contact_code via89 -move_via_to_center -rotation_mode off -size_by_via_area {1.68 0.84} -cut_spacings {0.34 0.34}
set_preroute_advanced_via_rule -contact_code via910 -move_via_to_center -rotation_mode off -size_by_via_area {1.68 3.36} -cut_spacings {0.56 0.34}
set_preroute_advanced_via_rule -cut_layer RV -move_via_to_center -rotation_mode off

set pg_phase_start         [clock seconds]
set pg_phase_name          "Preroute M1 M2 Rail"
###	create route guide for macro keepout
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

preroute_standard_cells -nets  {VDD VSS}  \
	-route_pins_on_layer M2 \
	-connect horizontal  \
	-pin_width_by_most_extended_pin  \
	-fill_empty_rows  \
	-port_filter_mode off \
	-cell_master_filter_mode off \
	-cell_instance_filter_mode off \
	-voltage_area_filter_mode off \
	-route_type {P/G Std. Cell Pin Conn} \
	-skip_macro_pins -do_not_route_over_macros -ignore_cell_boundary

set pg_phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $pg_phase_name \
        [expr {[clock format [expr $pg_phase_end - $pg_phase_start] -format %j -gmt true]-1}] \
        [clock format [expr $pg_phase_end - $pg_phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log

set pg_phase_start         [clock seconds]
set pg_phase_name          "Compile Top PG Mesh"
## extand M2 PG
foreach_in_collection one_pg_strap [get_net_shapes -filter {route_type=~"P/G *" && layer==M2}] {
	lassign [join [get_attribute $one_pg_strap points]] m2_pg_x1 m2_pg_y1 m2_pg_x2 m2_pg_y2
	set_attribute $one_pg_strap points [list [list [expr {$m2_pg_x1-0.2}] $m2_pg_y1] [list [expr {$m2_pg_x2+0.2}] $m2_pg_y2]]
}

## create power straps ( M3 ~ Top layer ) 
foreach one_used_metal $all_used_metals {
	set down_one_used_metal [lindex $all_available_metals [expr {[lsearch $all_available_metals $one_used_metal]-1}]]
	set_preroute_drc_strategy -min_layer $down_one_used_metal -max_layer $one_used_metal
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
}

set all_used_metals [concat M2 $all_used_metals]
foreach one_used_metal $all_used_metals {
	foreach_in_collection one_shape [get_net_shapes -filter "route_type=~\"P/G*\" && layer==$one_used_metal"] {
		reshape_endpoints_baseone_vias $one_shape
	}
}
set pg_phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $pg_phase_name \
        [expr {[clock format [expr $pg_phase_end - $pg_phase_start] -format %j -gmt true]-1}] \
        [clock format [expr $pg_phase_end - $pg_phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log
set_preroute_drc_strategy -min_layer M1 -max_layer M10
set autopg_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" "Total AUTO PG FLOW" \
        [expr {[clock format [expr $autopg_end - $autopg_start] -format %j -gmt true]-1}] \
        [clock format [expr $autopg_end - $autopg_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log

### remove all PGs
#remove_route_by_type -pg_strap -pg_std_cell_pin_conn -nets {VDD VSS}

