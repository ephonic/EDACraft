########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	COMMON DESIGN SETTING
######  Owner : Anonymous , rc
########################################################################################
###	common setting for DC && ICC
########################################################################################
if {[regexp -- {2015|2016} $product_version]} {
	set_app_var	timing_disable_recovery_removal_checks		false	; # default is true.
} else {
	set_app_var	enable_recovery_removal_arcs			true
}
set_app_var	timing_enable_multiple_clocks_per_reg		true		; # from K-2015.06, default is : true
set_app_var	timing_scgc_override_library_setup_hold		false
set_app_var	timing_separate_clock_gating_group		true
set_app_var	timing_use_enhanced_capacitance_modeling	true
set_app_var	timing_remove_clock_reconvergence_pessimism	true
#set timing_clock_reconvergence_pessimism same_transition
set_app_var	timing_crpr_threshold_ps			1.0
set_app_var	case_analysis_with_logic_constants		true
set_app_var	timing_library_derate_is_scenario_specific	false
###	remove high-fanout threshold
#set_app_var	high_fanout_net_threshold 0
set_app_var	dct_placement_ignore_scan			true
set_app_var	compile_no_new_cells_at_top_level		$var(top_no_new_cell)
if {[regexp -- {2015|2016} $product_version]} {
	set_app_var	timing_library_max_cap_from_lookup_table	true	; # name match PrimeTime
} else {
#	set_app_var	timing_enable_ccsn_waveform_analysis		true
}
###	optimize icg
if {[get_clock_gating_cell_nums]>0} {
	set_app_var	power_remove_redundant_clock_gates	false
	set_app_var	power_cg_flatten			true
	set_app_var	power_cg_physically_aware_cg		true
}
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
###	for 16nm
set_app_var	placer_enable_enhanced_router			true
#set		placer_detect_detours				true		; ###MDF: no such variable, but try.
#set		placer_zrt_deterministic_mode			false		; ###MDF: no such variable, but try.
#set		extract_enable_vr_sparse_handle			false		; ###MDF: no such variable, but try.
#set_app_var	placer_disable_auto_bound_for_gated_clock	false		; ###MDF: need try
#if {[string equal [dict get $nhp_predefine process] T16FFP]}
set_app_var	disable_auto_time_borrow			true
set_app_var	timing_early_launch_at_borrowing_latches	false
set_app_var	dont_bind_unused_pins_to_logic_constant		true
set_app_var	placer_gated_register_area_multiplier		5

### ICC OD Jog placement settings
set legalizer_consider_continuous_OD_spacing true
set legalizer_consider_PODE_spacing false
set legalizer_PODE_mode 0
set legalizer_min_OD_filler_size 2
### ICC VT Min. Area placement settings
set legalizer_consider_vth_spacing true
#set legalizer_vth_spacing_use_files false
set legalizer_support_min_vth_spacing true
set legalizer_advanced_tech_flow true
#set legalizer_min_VT_filler_size  1
set legalizer_min_VT_filler_size  2
#set legalizer_use_both_for_min_filler true

set legalizer_num_tracks_for_access_check 2
set placer_max_pins_per_square_micron 25
###	from synposys adv mu
set legalizer_skip_preroute_merge false
set legalizer_preroute_merge_num_tracks 2
}

if {$synopsys_program_name == "icc_shell" || $synopsys_program_name == "dc_shell" && [shell_is_in_topographical_mode]} {
set_app_var	physopt_enable_via_res_support			true
set_app_var	placer_enable_enhanced_soft_blockages		true
set_app_var	placer_max_cell_density_threshold		$var(placer_max_cell_density_threshold)
set_app_var	placer_gated_register_area_multiplier		6
set_app_var	preroute_opt_verbose				160
set_app_var	magnet_placement_stop_after_seq_cell		true
set_app_var	placer_congestion_effort			medium
set_app_var	placer_channel_detect_mode			auto
set_congestion_options -max_util        $var(cong_max_utli)
set		placer_target_routing_density			0.6		; # by AG.pdf, P78
}

set_cost_priority -delay
set_auto_disable_drc_nets -constant false -scan false
set_fix_multiple_port_nets -all -buffer_constants
# Disable register merging
set_register_merging [current_design] false

###	define timing derate
set_timing_derate $var(timing_derate_max) -late
set_timing_derate $var(timing_derate_min) -early

report_timing_derate

####    mvt percentage functional will release only if it is required.
if {[llength $var(libs_vth_cons)]>0} {
        set_multi_vth_constraint -type hard -cost area \
				-lvth_groups [lindex $var(libs_vth_cons) 0] \
                                -lvth_percentage [lindex $var(libs_vth_cons) 1] -include_blackboxes
}
########################################################################################
###	setting only for DC
########################################################################################
if {$synopsys_program_name == "dc_shell"} {
set_app_var	compile_delete_unloaded_sequential_cells false
set_app_var	compile_seqmap_propagate_constants	false
set_app_var	compile_enable_register_merging		false
set_app_var	spg_enable_via_resistance_support	true
#set_app_var	glo_more_opto				true
set_app_var	verilogout_no_tri			true
set_app_var	compile_register_replication		$designopt(register_replication)

if {[shell_is_in_topographical_mode]} {
	###     set ignored routing layers
	set_ignored_layers -min_routing_layer $var(bottom_layer)
	set_ignored_layers -max_routing_layer $var(top_layer)
	report_ignored_layers
}
}
########################################################################################
###	setting only for ICC
########################################################################################
if {$synopsys_program_name == "icc_shell"} {
set_app_var	icc_preroute_power_aware_optimization	true
set_app_var	routeopt_xtalk_reduction_cell_sizing	true
set_app_var	physopt_new_fix_constants		true
set_app_var	physopt_delete_unloaded_cells		false
set_app_var	placer_enable_high_effort_congestion	true
set_app_var	placer_show_zroutegr_output		true
set_app_var	timing_waveform_analysis_mode		full_design
set_app_var	psyn_onroute_size_seqcell		$var(sizing_seq_onroute)

#if {[string equal [dict get $nhp_predefine process] T16FFP]}
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
	if {$designopt(create_abut_rules)} {
		create_abut_rules -number_of_references $var(abut_rules,abut_rule) -output abut_rules.$var(abut_rules,abut_rule)
		create_abut_rules -number_of_references $var(abut_rules,soft_keepout) -soft_keepout -output keepout.$var(abut_rules,soft_keepout)
	}
	#check_finfet_grid
	if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_place_abut_rule] &&
       		[file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_place_abut_rule]]} {
       		source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_place_abut_rule]
	}
}

###     set max net length, max fanout
if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        foreach each [all_active_scenarios] {
        	current_scenario $each
                if { $var(max_net_length) > 0 } { set_max_net_length $var(max_net_length) [current_design] }
		set_max_fanout $var(max_fanout) [current_design]
        }
        current_scenario $var(mcmm_default_view)
} else {
        if { $var(max_net_length) > 0 } { set_max_net_length $var(max_net_length) [current_design] }
	set_max_fanout $var(max_fanout) [current_design]
} 
###	fix hold
if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	### enable aocv analysis
	if {$var(use_aocvm)} {
		set timing_aocvm_enable_analysis		true
		set timing_aocvm_analysis_mode 			$var(aocvm_analysis_mode)
		set timing_aocvm_enable_distance_analysis	true
		#set timing_aocvm_ideal_clock_mode		true
		#set timing_aocvm_ideal_clock_depth		<number>
	}
        foreach each_active_scenario [all_active_scenarios] {
		if {$var(use_aocvm)} {
			set current_scenario_corner	[dict get $lib_mcmm $each_active_scenario corner]
			set current_scenario_setup	[dict get $lib_mcmm $each_active_scenario setup]
			set current_scenario_hold	[dict get $lib_mcmm $each_active_scenario hold]
			foreach mvt_one $final_lib_list {
				if {[dict exists $lib_define $mvt_one aocv $current_scenario_corner]} {
					if {$current_scenario_setup} {
						read_aocvm -max [dict get $lib_define $mvt_one aocv $current_scenario_corner]
					}
					if {$current_scenario_hold} {
						read_aocvm -min [dict get $lib_define $mvt_one aocv $current_scenario_corner]
					}
				}
			}
		}
                current_scenario $each_active_scenario
                set_fix_hold [all_clocks]
        }
        current_scenario $var(mcmm_default_view)
} else {
        set_fix_hold [all_clocks]

	set clocklist_mesh      [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
	set clocklist_cts       [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
	if {[llength $clocklist_cts]>0} {
###MDF:	change these values if use SBOCV settings.
		set_timing_derate -early 0.98 -clock -cell_delay
		set_timing_derate -early 0.95 -clock -net_delay
		set_timing_derate -late 1.02 -clock -cell_delay
		set_timing_derate -late 1.05 -clock -net_delay
	}
}
#set_prefer -min [get_lib_cells -quiet *[dict get $nhp_predefine default_corner]*/[dict get $nhp_predefine delay_cell]]
#set_fix_hold_options -preferred_buffer
# Set up delay calculation to use most accurate models
set_delay_calculation_options	-preroute awe \
				-awe_effort $var(delay,awe_effort) \
				-postroute arnoldi \
				-routed_clock arnoldi \
				-arnoldi_effort $var(delay,arnoldi_effort)
set_fix_hold_options -effort high -prioritize_tns
set_buffer_opt_strategy -effort high
###     set ignored routing layers
set_ignored_layers -min_routing_layer $var(bottom_layer)
set_ignored_layers -max_routing_layer $var(top_layer)
report_ignored_layers
set_separate_process_options -placement false
## Enable Power-Optimization
if {$designopt(power)} {
	set_total_power_strategy -effort high
	report_total_power_strategy
        set_optimize_pre_cts_power_options -low_power_placement true
}
###	layer optimization
set_place_opt_strategy -layer_optimization_effort high
###	set icv environment
set env(PATH) [dict get $lib_common icv EXE_PATH]:$env(PATH)
set env(ICV_HOME_DIR) [dict get $lib_common icv HOME_DIR]
set_stream_layer_map_file -map_file [dict get $lib_common mapfile gdsmap] -format out
#set_physical_signoff_options -exec_cmd icv -mapfile [dict get $lib_common mapfile gdsmap] -drc_runset [dict get $lib_common icv DRC_RUNSET]
set_physical_signoff_options -exec_cmd icv -drc_runset [dict get $lib_common icv DRC_RUNSET]
if {[dict exists $lib_common icv FILL_RUNSET]} { set_physical_signoff_options -fill_runset [dict get $lib_common icv FILL_RUNSET] }
###	define left/right spacing label rule for list-decap.
if {$var(insert,listdecap)} {
        set all_std_cells [remove_from_collection [get_physical_lib_cells] [get_physical_lib_cells -quiet -of_objects [all_macro_cells]]]
        set_lib_cell_spacing_label -names SP_CELL \
                                -left_lib_cells [dict get $nhp_predefine listdecap_cells] \
                                -right_lib_cells [dict get $nhp_predefine listdecap_cells]
        #set_lib_cell_spacing_label -names ALL_CELL -left_lib_cells {*} -right_lib_cells {*}
        set_lib_cell_spacing_label -names ALL_CELL -left_lib_cells $all_std_cells -right_lib_cells $all_std_cells
        set listdecap_sites [expr {int([lindex [get_attribute [get_physical_lib_cells [dict get $lib_define $main_lib_name function_cell predecap]] bbox] 1 0]
                                /
                                [get_attribute [index_collection [get_site_rows] 0] site_space])}]
        if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
                set CMD_SPACING_RULE "set_spacing_label_rule -labels {SP_CELL ALL_CELL} {0 [expr {$listdecap_sites+1}]}"
        } else {
                set CMD_SPACING_RULE "set_spacing_label_rule -labels {SP_CELL ALL_CELL} {0 [expr {$listdecap_sites-1}]}"
        }
        echo $CMD_SPACING_RULE
        eval $CMD_SPACING_RULE
}
###     define antenna rule
if {[file isfile [dict get $lib_common ant_rule]]} {
        source -echo -verbose [dict get $lib_common ant_rule]
}
}

dict set nhp_predefine sl_design 1
