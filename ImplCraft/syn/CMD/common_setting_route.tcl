########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	COMMON ROUTING SETTING
######  Owner : Anonymous , rc
########################################################################################
###	Zroute common options [DCT && ICC]
########################################################################################
				#-net_min_layer_mode allow_pin_connection \
				#-connect_within_pins {{M1 via_standard_cell_pins}} \
###	if need to fix the bridge rule, turn on all below
# Demote soft rules which are not true DRC issues
# set_route_zrt_common_options -global_max_layer_mode hard
set_route_zrt_common_options	-route_soft_rule_effort_level low \
				-post_detail_route_fix_soft_violations true \
				-post_eco_route_fix_soft_violations true \
				-post_group_route_fix_soft_violations true \
				-post_incremental_detail_route_fix_soft_violations true \
				-concurrent_redundant_via_mode off \
				-eco_route_concurrent_redundant_via_mode off \
				-concurrent_redundant_via_effort_level medium \
				-eco_route_concurrent_redundant_via_effort_level medium \
				-verbose_level 2
if {$designopt(optimize_vias)} { set_route_zrt_common_options -post_detail_route_redundant_via_insertion medium }
set_route_zrt_common_options	-read_user_metal_blockage_layer true
set_route_zrt_common_options	-connect_within_pins_by_layer_name {{M1 via_wire_standard_cell_pins}} \
				-global_min_layer_mode $var(global_min_layer_mode) \
				-global_max_layer_mode $var(global_max_layer_mode)

#if {[string equal [dict get $nhp_predefine process] T16FFP]}
				#-global_min_layer_mode hard
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
set_route_zrt_common_options	-route_top_boundary_mode stay_half_min_space_inside \
				-connect_within_pins_by_layer_name {{M1 via_wire_standard_cell_pins} {M2 off}} \
				-net_min_layer_mode allow_pin_connection \
				-extra_nonpreferred_direction_wire_cost_multiplier_by_layer_name {{M4 3} {M5 3} {M6 3} {M7 3}} \
				-report_local_double_pattern_odd_cycles true \
				-single_connection_to_pins standard_cell_pins \
				-fix_existing_internal_drc true
set_route_zrt_common_options	-via_array_mode rotate
set_route_zrt_common_options	-extra_preferred_direction_wire_cost_multiplier_by_layer_name {{M2 1}} \
				-extra_via_off_grid_cost_multiplier_by_layer_name {{M2 2}}	; # add by AG.pdf, P79
}

########################################################################################
###	Zroute global route specific options can be set by the following command [DCT && ICC]
########################################################################################
set_route_zrt_global_options	-crosstalk_driven true \
				-effort high \
				-timing_driven true \
				-timing_driven_effort_level high
set_route_zrt_global_options	-exclude_blocked_gcells_from_congestion_report true

#if {[string equal [dict get $nhp_predefine process] T16FFP]}
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
set_route_zrt_global_options -double_pattern_utilization_by_layer_name $var(dpt_utilization)
#set_route_zrt_global_options -pin_access_factor 9	; # test.
}

###	other variables
set_app_var	rc_noise_model_mode		advanced
set_app_var	physopt_area_critical_range	$var(physopt_area_critical_range)
set_app_var	physopt_power_critical_range	$var(physopt_power_critical_range)

if {$synopsys_program_name == "icc_shell"} {
########################################################################################
###	Zroute track assign specific options can be set by the following command [ICC]
########################################################################################
set_route_zrt_track_options -crosstalk_driven true -timing_driven true

########################################################################################
###	Zroute detail route specific options can be set by the following command [ICC]
########################################################################################
# Allow the use of off-grid routing to improve DRC fixing
set_route_zrt_detail_options -generate_extra_off_grid_pin_tracks true

# Improve DRC routing over macros
set_route_zrt_detail_options -repair_shorts_over_macros_effort_level high

# Fix Antenna
set_route_zrt_detail_options 	-antenna true \
				-timing_driven true \
				-insert_diodes_during_routing true \
				-diode_libcell_names "[dict get $nhp_predefine antenna_cell]" \
				-default_port_external_gate_size 0.000000001
# To Optimize wire length and via counts : 
set_route_zrt_detail_options	-optimize_wire_via_effort_level high \
				-optimize_tie_off_effort_level high

#if {[string equal [dict get $nhp_predefine process] T16FFP]}
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
				#-optimize_wire_via_effort_level medium
set_route_zrt_detail_options	-default_diode_protection 0.5 \
				-drc_convergence_effort_level high \
				-check_pin_min_area_min_length false \
				-check_port_min_area_min_length true \
				-repair_shorts_over_macros_effort_level high
}
#set_route_zrt_detail_options 	-eco_route_special_design_rule_fixing_stage none
# turn off the report of 'bridge rule' errors.
#set_route_zrt_detail_options	-report_ignore_drc {"Illegal Bridge" "Comb routing direct connection"}
########################################################################################
###	Zroute SI Options [ICC]
########################################################################################
set_si_options	-delta_delay true  \
		-route_xtalk_prevention true \
		-route_xtalk_prevention_threshold 0.25 \
	 	-static_noise true \
		-static_noise_threshold_above_low 0.35 \
		-static_noise_threshold_below_high 0.35 \
		-timing_window true \
		-analysis_effort medium \
		-reselect true
set_si_options	-min_delta_delay true

set_route_opt_zrt_crosstalk_options -effort_level high \
		-setup true -hold true \
		-static_noise true \
		-transition true \
                -setup_one_net_delta_delay_threshold $var(focal,xtalk) \
                -hold_one_net_delta_delay_threshold $var(focal,xtalk)
set_xtalk_route_options -groute_minimize_xtalk true -track_assign_minimize_xtalk true

set_route_opt_strategy -search_repair_loop 40 -eco_route_search_repair_loops 20 \
			-enable_port_punching true -xtalk_reduction_loops 5
}

dict set nhp_predefine sl_route 1
