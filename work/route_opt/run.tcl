# ICC2 Route Optimization Script
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

# Route optimization
set_app_options -name opt.power.mode -value leakage
set_app_options -name opt.power.effort -value high
set_app_options -name opt.timing.effort -value high

route_opt -initial_route_opt
route_opt

# Final DRC check
check_route
route_detail -incremental true -initial_drc_from_input true
check_route

# Post-decap insertion

# Write outputs
save_block -as route_opt
save_lib

# Write netlist for STA / PV
write_verilog -include_pwr_grd \
    -exclude_cell_output unconnected \
    ./out/FullSystem_routed.v
write_parasitics -format SPEF -output ./out/FullSystem.spef

# Reports
check_route > ./rpt/routeopt_check.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets \
    -max_paths 9999 -slack_lesser_than 0 \
    > ./rpt/routeopt_timing_violations.rpt
report_qor -summary > ./rpt/routeopt_qor.rpt

exit