####### load design


source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/mcmm1.tcl
#######
set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario func.tt0p9v.wc.cmax_25c.setup

####### set cell list
set_dont_touch [get_lib_cells */*] false
set_attribute [get_lib_cells */*] dont_use false
#set_lib_cell_purpose -include optimization [get_lib_cells {*/*BUFHDV* */*INHDV*}]
#set_app_options -name opt.tie_cell.max_fanout -value 8
#set_lib_cell_purpose -exclude all [get_lib_cells {*/*BUFFD0BWP30P140UHVT* */*INVD0BWP30P140UHVT*}]

####### fix all io nets
set all_io_nets [get_object_name [get_nets -of [get_ports * -filter "full_name != VDD && full_name != VSS"]]]
set_dont_touch [get_nets $all_io_nets]

####### path group
remove_path_group [get_object_name [get_path_groups * -filter "name!~*default*"]]
remove_path_group [get_object_name [get_path_groups *]]
set clock_ports [get_ports *clk*]
set macro_cells [get_cells -hierarchical -filter "is_hard_macro==true"]
set all_icgs [get_flat_cells -filter "is_integrated_clock_gating_cell==true"]
set non_clk_inputs [remove_from_collection [all_inputs] $clock_ports]
set all_regs [remove_from_collection [all_registers] $all_icgs]

group_path -name input -from $non_clk_inputs
group_path -name output -to [all_outputs]
group_path -name reg2icg -from $all_regs -to $all_icgs
group_path -name reg2reg -from $all_regs -to $all_regs

#set_ignored_layers -min_routing_layer M2 -max_routing_layer M8
set_host_option -max_cores 64 -num_process 8

### auto density control
set_app_options -name opt.common.enable_rde -value false
set_app_options -name place.coarse.enhanced_auto_density_control -value fasle

####### ccd
set_app_options -name place_opt.flow.enable_ccd -value false
set_app_options -name place.coarse.icg_auto_bound -value true
set_app_options -name place.coarse.auto_timing_control -value false

####### pre setting
set_ignored_layers -min_routing_layer M2 -max_routing_layer M9

set_app_options -name place_opt.place.congestion_effort -value high
set_app_options -name compile.place.congestion_effort -value high
#set_app_options -name place_opt.final_place.effort -value high

set_app_options -name opt.power.mode -value leakage
set_app_options -name opt.power.effort -value high
set_app_options -name opt.timing.effort -value high
set_app_options -name opt.common.max_fanout -value 30
set_app_options -name opt.common.max_net_length -value 400

set_max_transition -data_path 0.150 clk -scenario [all_scenario]
set_max_transition -clock_path 0.100 clk -scenario [all_scenario]

####### place opt
#set_host_option -max_cores 4
set_app_options -name place.coarse.continue_on_missing_scandef -value true
set_app_options -name place.coarse.max_density -value 0.1




##########################################################################
remove_placement_spacing_rules -all

set_placement_spacing_label -name X -side both -lib_cells [get_lib_cells */*]
set_placement_spacing_rule -labels {X X} {0 1}

report_placement_spacing_rule > ./rpt/spacing_rule.rpt


create_placement -congestion
place_opt

#place_opt -from initial_place -to initial_place
#place_opt

source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl


save_lib
save_block
save_block -as 5_place

####### report
report_congestion > ./rpt/place_congestion.rpt
report_utilization > ./rpt/place_utilization.rpt
report_design -nosplit > ./rpt/place_report_design.rpt

check_legality > ./rpt/check_legality.rpt
check_mv_design > ./rpt/check_mv_design.rpt
report_qor -summary > ./rpt/report_qor.summary.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute -derate -voltage -delay_type max > ./rpt/place_report_timing.rpt

report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg >./reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg >./reg2icg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg >./in2reg.rpt
