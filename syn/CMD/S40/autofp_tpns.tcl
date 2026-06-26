########################################################################################
######  DCICC FLOW - Version 4.1.0 (2015-10-15), For T40,
######  Owner : Anonymous , rc
########################################################################################
set autopg_start	[clock seconds]
echo "######\tAuto PG Start : [date]" > ./$icc_finalopt/report/autopg.log

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)

#######################################
### Define Parameters
#######################################
#set nhp_pgmesh_macro_region	5.0
#set nhp_pgmesh_notch_threshold	3.36
set nhp_power_plan_regions_exceptions { }
set nhp_custom_macro_metal_respect_keepout { }
###	var(autofp,metal_respect_keepout) is global variable, for all macros.
###	you can either define different layer constrarints for different macros, such as :
###     ----------------------------------------------------------------------------------
###	set nhp_custom_macro_metal_respect_keepout {
###		m_macro_inst1	{M1 M2 M3 M4}
###		m_macro_inst2	{M1 M2 M3 M4 M5}
###	}
###     ----------------------------------------------------------------------------------
set nhp_powerdefine {
	M3	{
		width		0.4
		spacing		3.36
		offset		0
		direction	vertical
		pg_pair		{VDD VSS}
	}
	M4	{
		width		0.4
		spacing		3.36
		offset		0
		direction	horizontal
		pg_pair		{VSS VDD}
	}
	M5	{
		width		0.4
		spacing		3.36
		offset		0
		direction	vertical
		pg_pair		{VDD VSS}
	}
	M6	{
		width		0.4
		spacing		3.36
		offset		0
		direction	horizontal
		pg_pair		{VSS VDD}
	}
	M7	{
		width		0.84
		spacing		6.72
		offset		0
		direction	vertical
		pg_pair		{VDD VSS}
	}
	M8	{
		width		0.84
		spacing		6.72
		offset		0
		direction	horizontal
		pg_pair		{VSS VDD}
	}
	M9	{
		width		1.68
		spacing		13.44
		offset		0
		direction	vertical
		pg_pair		{VDD VSS}
	}
	M10	{
		width		3.36
		spacing		13.44
		offset		0
		direction	horizontal
		pg_pair		{VSS VDD}
	}
}

#######################################
### create pg mesh
#######################################
set all_pgmesh_metals	[lrange [dict get $lib_common metal_layers all] \
                                [lsearch [dict get $lib_common metal_layers all] [dict get $lib_common metal_layers start]] \
                                [lsearch [dict get $lib_common metal_layers all] $var(top_layer)]]

remove_objects [get_terminals]

## set via rule to move via to center
set pns_ignore_cell_boundary true
set preroute_ContactSizeSelection 0
set_preroute_advanced_via_rule
set_preroute_advanced_via_rule -contact_code via23 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1} -cut_spacings {0.07 0.07}
set_preroute_advanced_via_rule -contact_code via34 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 3} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via45 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 3} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via56 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 3} -cut_spacings {0.09 0.09}
set_preroute_advanced_via_rule -contact_code via67 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 1} -cut_spacings {0.16 0.16}
set_preroute_advanced_via_rule -contact_code via78 -move_via_to_center -rotation_mode off -size_by_array_dimensions {3 3} -cut_spacings {0.16 0.16}
set_preroute_advanced_via_rule -contact_code via89 -move_via_to_center -rotation_mode off -size_by_array_dimensions {2 1} -cut_spacings {0.34 0.34}
set_preroute_advanced_via_rule -contact_code via910 -move_via_to_center -rotation_mode off -size_by_array_dimensions {2 5} -cut_spacings {0.56 0.34}
set_preroute_advanced_via_rule -cut_layer RV -move_via_to_center -rotation_mode off

foreach_in_collection one [all_macro_cells] {
	set cur_inst_name [get_attribute $one full_name]
	if {[dict exists $nhp_custom_macro_metal_respect_keepout $cur_inst_name]} {
		foreach one_layer [dict get $lib_common metal_layers all] {
			if {[lsearch -exact [dict get $nhp_custom_macro_metal_respect_keepout $cur_inst_name] $one_layer]>=0} {
				dict lappend nhp_power_plan_regions_exceptions $one_layer $cur_inst_name
			}
		}
	} else {
		foreach one_layer [dict get $lib_common metal_layers all] {
			if {[lsearch -exact $var(autofp,metal_respect_keepout) $one_layer]>=0} {
				dict lappend nhp_power_plan_regions_exceptions $one_layer $cur_inst_name
			}
		}
	}
}

set pg_phase_start		[clock seconds]
set pg_phase_name		"Preroute M1 M2 Rail"
###	create route guide for macro keepout
if {[sizeof_collection [all_macro_cells]]>0 && [dict size $nhp_power_plan_regions_exceptions]>0} {
	my_create_preroute_route_guide_base_on_macro_keepout RG_MACRO_KEEPOUT_PREROUTE "M1 M2" [get_attribute [get_core_areas] tile_height]
	my_create_power_plan_regions_base_on_macro_keepout [all_macro_cells] [get_attribute [get_core_areas] tile_height]
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

remove_route_guide -name RG_MACRO_KEEPOUT_PREROUTE*

## extand M2 PG
foreach_in_collection one_pg_strap [get_net_shapes -filter {route_type=~"P/G *" && layer==M2}] {
	lassign [join [get_attribute $one_pg_strap points]] m2_pg_x1 m2_pg_y1 m2_pg_x2 m2_pg_y2
	set_attribute $one_pg_strap points [list [list [expr {$m2_pg_x1-0.3}] $m2_pg_y1] [list [expr {$m2_pg_x2+0.3}] $m2_pg_y2]]
}
set pg_phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $pg_phase_name \
        [expr {[clock format [expr $pg_phase_end - $pg_phase_start] -format %j -gmt true]-1}] \
        [clock format [expr $pg_phase_end - $pg_phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log

set pg_phase_start		[clock seconds]
set pg_phase_name		"Compile Top PG Mesh"
remove_power_plan_strategy -all
foreach one_used_metal $all_pgmesh_metals {
	set one_pg_nets		[dict get $nhp_powerdefine $one_used_metal pg_pair]
	set one_pg_direction	[dict get $nhp_powerdefine $one_used_metal direction]
	set one_pg_width	[dict get $nhp_powerdefine $one_used_metal width]
	set one_pg_spacing	[expr {[dict get $nhp_powerdefine $one_used_metal spacing]-[dict get $nhp_powerdefine $one_used_metal width]}]
	set one_pg_pitch	[expr {[dict get $nhp_powerdefine $one_used_metal spacing]*2}]
	set one_pg_offset	[dict get $nhp_powerdefine $one_used_metal offset]
	set CMD_PPS		"set_power_plan_strategy pg_mesh_$one_used_metal -core -nets {$one_pg_nets} \
		-template ../CMD/T40G/pg_template.tpl:sw4c_pg_mesh_${one_pg_direction}($one_used_metal,$one_pg_width,$one_pg_spacing,$one_pg_pitch,$one_pg_offset)"
	if {[dict exists $nhp_power_plan_regions_exceptions $one_used_metal]} {
		#if {[sizeof_collection [get_power_plan_regions -quiet -exact $nhp_power_plan_regions_exceptions]]} {
		#	set CMD_PPS	[concat $CMD_PPS "-blockage {power_plan_region:{[dict get $nhp_power_plan_regions_exceptions $one_used_metal]}}"]
		#}
                if {[sizeof_collection [get_power_plan_regions -quiet -exact [dict get $nhp_power_plan_regions_exceptions $one_used_metal]]]} {
                        unset -nocomplain regions_list
                        foreach one_power_plan_region [dict get $nhp_power_plan_regions_exceptions $one_used_metal] {
                                lappend regions_list "{power_plan_regions: $one_power_plan_region} {layers: $one_used_metal}"
                        }
                        set CMD_PPS     [concat $CMD_PPS "-blockage \{$regions_list\}"]
                }
	}
	if {[string equal $one_used_metal M3]} {
		set CMD_PPS	[concat $CMD_PPS "-extension {{nets: {$one_pg_nets}} {direction: TB} {stop: 0.225}}"]
	}
	if {[string equal $one_used_metal M6]} {
		set CMD_PPS	[concat $CMD_PPS "-extension {{nets: {$one_pg_nets}} {direction: LR} {stop: 0.42}}"]
	}
	eval $CMD_PPS
}
report_power_plan_strategy
compile_power_plan

set pg_phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $pg_phase_name \
        [expr {[clock format [expr $pg_phase_end - $pg_phase_start] -format %j -gmt true]-1}] \
        [clock format [expr $pg_phase_end - $pg_phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log

set pns_ignore_cell_boundary false
set nhp_power_plan_regions_exceptions { }
set nhp_custom_macro_metal_respect_keepout { }
set_preroute_advanced_via_rule
if {[sizeof_collection [all_macro_cells]]>0 && [get_power_plan_regions -quiet [get_object_name [all_macro_cells]]]>0} {
	remove_power_plan_regions [get_object_name [all_macro_cells]]
}

set autopg_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" "Total AUTO PG FLOW" \
        [expr {[clock format [expr $autopg_end - $autopg_start] -format %j -gmt true]-1}] \
        [clock format [expr $autopg_end - $autopg_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/report/autopg.log

### remove all PGs
#remove_route_by_type -pg_strap -pg_std_cell_pin_conn -nets {VDD VSS}
