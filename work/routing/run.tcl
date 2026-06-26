# ICC2 Routing Script
# Design: FullSystem

# ---- Common App Variables ----
set_app_var timing_enable_multiple_clocks_per_reg true
set_app_var timing_separate_clock_gating_group true
set_app_var timing_use_enhanced_capacitance_modeling true
set_app_var timing_remove_clock_reconvergence_pessimism true
set_app_var timing_crpr_threshold_ps 1.0
set_app_var case_analysis_with_logic_constants true
set_app_var physopt_enable_via_res_support true
set_app_var placer_enable_enhanced_soft_blockages true
set_app_var preroute_opt_verbose 160
set_app_var rc_noise_model_mode advanced

set_host_option -max_cores 64 -num_process 8

set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario $active_scenarios

set_ignored_layers -min_routing_layer M2 -max_routing_layer M9

# ---- Routing Common Options ----
set_route_zrt_common_options -route_soft_rule_effort_level low
set_route_zrt_common_options -post_detail_route_fix_soft_violations true
set_route_zrt_common_options -post_eco_route_fix_soft_violations true
set_route_zrt_common_options -concurrent_redundant_via_mode off
set_route_zrt_common_options -concurrent_redundant_via_effort_level medium
set_route_zrt_common_options -read_user_metal_blockage_layer true
set_route_zrt_common_options -global_min_layer_mode allow_pin_connection
set_route_zrt_common_options -global_max_layer_mode hard

# ---- Global Route Options ----
set_route_zrt_global_options -crosstalk_driven true
set_route_zrt_global_options -effort high
set_route_zrt_global_options -timing_driven true
set_route_zrt_global_options -timing_driven_effort_level high
set_route_zrt_global_options -exclude_blocked_gcells_from_congestion_report true

# ---- Track Assign Options ----
set_route_zrt_track_options -crosstalk_driven true
set_route_zrt_track_options -timing_driven true

# ---- Detail Route Options ----
set_route_zrt_detail_options -generate_extra_off_grid_pin_tracks true
set_route_zrt_detail_options -repair_shorts_over_macros_effort_level high
set_route_zrt_detail_options -optimize_wire_via_effort_level high
set_route_zrt_detail_options -optimize_tie_off_effort_level high
set_route_zrt_detail_options -antenna true
set_route_zrt_detail_options -insert_diodes_during_routing true

# ---- SI Options ----
set_si_options -delta_delay true
set_si_options -route_xtalk_prevention true
set_si_options -route_xtalk_prevention_threshold 0.25
set_si_options -static_noise true
set_si_options -static_noise_threshold_above_low 0.35
set_si_options -static_noise_threshold_below_high 0.35
set_si_options -timing_window true
set_si_options -analysis_effort medium
set_si_options -reselect true
set_si_options -min_delta_delay true

# ---- Route Opt Strategy ----
set_route_opt_strategy -search_repair_loop 40
set_route_opt_strategy -eco_route_search_repair_loops 20
set_route_opt_strategy -enable_port_punching true
set_route_opt_strategy -xtalk_reduction_loops 5

# Route
route_global
route_track
route_detail

# Fix DRCs
check_route
route_detail -incremental true -initial_drc_from_input true
check_route

# Add redundant vias
add_redundant_vias

save_block -as route
save_lib

# Reports
check_route > ./rpt/route_check.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets \
    -max_paths 200 -slack_lesser_than 0 -groups reg2reg \
    > ./rpt/route_timing_reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets \
    -max_paths 200 -slack_lesser_than 0 -groups reg2icg \
    > ./rpt/route_timing_reg2icg.rpt

exit