# ICC2 CTS (Clock Tree Synthesis) Script
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

# ---- CTS Options ----
set_app_options -name opt.power.mode -value leakage
set_app_options -name opt.power.effort -value high
set_app_options -name opt.timing.effort -value high
set_app_options -name opt.common.max_fanout -value 24
set_app_options -name opt.common.max_net_length -value 150
set_app_options -name clock_opt.flow.enable_ccd -value false

# ---- Clock Tree Options ----
set_clock_tree_options \
    -target_skew 0.1 \
    -target_early_delay 0.0 \
    -use_leaf_max_transition_on_macros false \
    -ocv_clustering true \
    -ocv_path_sharing true \
    -logic_level_balance false

# Remove ideal network for CTS clocks
remove_ideal_network [all_fanout -flat -from [get_attribute [get_clocks { clk }] sources]]

# Build clock
clock_opt -from build_clock -to build_clock
clock_opt -from route_clock -to route_clock

# Final optimization
clock_opt -from final_opto -to final_opto

# Fix hold
set_fix_hold [all_clocks]

save_block -as cts
save_lib

# Reports
report_congestion > ./rpt/cts_congestion.rpt
report_utilization > ./rpt/cts_utilization.rpt
report_clock > ./rpt/cts_clock.rpt
report_clock_timing -type skew > ./rpt/cts_clock_skew.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance \
    -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute \
    -derate -voltage -delay_type max > ./rpt/cts_timing.rpt

exit