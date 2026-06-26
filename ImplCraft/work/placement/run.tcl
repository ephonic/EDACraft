# ICC2 Placement Script
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

# Scenario setup
set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario $active_scenarios

# Cell list — enable all cells
set_dont_touch [get_lib_cells */*] false
set_attribute [get_lib_cells */*] dont_use false

# ---- Advanced Placement Options ----
set_app_var placer_max_cell_density_threshold -1.0
set_app_var placer_congestion_effort medium
set placer_target_routing_density 0.6
set_congestion_options -max_util 0.7

# VT min area placement
set legalizer_consider_vth_spacing true
set legalizer_min_VT_filler_size 2
set legalizer_support_min_vth_spacing true
set legalizer_advanced_tech_flow true
set legalizer_consider_continuous_OD_spacing true
set legalizer_consider_PODE_spacing false

# Path groups
remove_path_group [get_object_name [get_path_groups * -filter {name!~*default*}]]
remove_path_group [get_object_name [get_path_groups *]]
set clock_ports [get_ports *clk*]
set all_icgs [get_flat_cells -filter {is_integrated_clock_gating_cell==true}]
set non_clk_inputs [remove_from_collection [all_inputs] $clock_ports]
set all_regs [remove_from_collection [all_registers] $all_icgs]
group_path -name input -from $non_clk_inputs
group_path -name output -to [all_outputs]
group_path -name reg2icg -from $all_regs -to $all_icgs
group_path -name reg2reg -from $all_regs -to $all_regs

# Routing layers
set_ignored_layers -min_routing_layer M2 -max_routing_layer M9

# Placement options
set_app_options -name place.coarse.continue_on_missing_scandef -value true
set_app_options -name place.coarse.max_density -value 0.1
set_app_options -name place.coarse.enhanced_auto_density_control -value false
set_app_options -name place.coarse.icg_auto_bound -value true
set_app_options -name opt.power.mode -value leakage
set_app_options -name opt.power.effort -value high
set_app_options -name opt.timing.effort -value high
set_app_options -name opt.common.max_fanout -value 30
set_app_options -name opt.common.max_net_length -value 250.0

# Spacing rules
remove_placement_spacing_rules -all
set_placement_spacing_label -name X -side both -lib_cells [get_lib_cells */*]
set_placement_spacing_rule -labels {X X} {0 1}

# Place
create_placement -congestion
place_opt

# Save
save_block -as place
save_lib

# Reports
report_congestion > ./rpt/place_congestion.rpt
report_utilization > ./rpt/place_utilization.rpt
report_design -nosplit > ./rpt/place_report_design.rpt
check_legality > ./rpt/check_legality.rpt
report_qor -summary > ./rpt/report_qor.summary.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance \
    -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute \
    -derate -voltage -delay_type max > ./rpt/place_timing.rpt

exit