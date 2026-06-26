
clock_opt -from build_clock -to build_clock
clock_opt -from route_clock -to route_clock


source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl
set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario func.tt0p9v.wc.cmax_25c.setup

####### set cell list
#set_lib_cell_purpose -exclude all [get_lib_cells -quiet */*X0*]
set_lib_cell_purpose -exclude all [get_lib_cells {*/*BUFFD0BWP30P140UHVT* */*INVD0BWP30P140UHVT*}]

####### fix all io nets
set all_io_nets [get_object_name [get_nets -of [get_ports * -filter "full_name != VDD && full_name != VSS"]]]
set_dont_touch [get_nets $all_io_nets]

####### ccd
set_app_options -name clock_opt.flow.enable_ccd -value false

####### pre setting
set_ignored_layers -min_routing_layer M2 -max_routing_layer M9

set_app_options -name opt.power.mode -value leakage
set_app_options -name opt.power.effort -value high
set_app_options -name opt.timing.effort -value high
set_app_options -name opt.common.max_fanout -value 24
set_app_options -name opt.common.max_net_length -value 150

set_max_transition -data_path 0.150 [get_clocks ] -scenario [all_scenario]
set_max_transition -clock_path 0.100 [get_clocks ] -scenario [all_scenario]
set_host_option -max_cores 64 -num_process 8
####### clock opt
clock_opt -from final_opto -to final_opto

####### connect pg
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl

####### save
save_lib
save_block
save_block -as 8_clock_opt

####### report
report_congestion > ./rpt/clock_opt_congestion.rpt
report_utilization > ./rpt/clock_opt_utilization.rpt
report_design -nosplit > ./rpt/clock_opt_report_design.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute -derate -voltage -delay_type max > ./rpt/cts_opt_report_timing.rpt

report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg > ./rpt/report_timing_func_max_reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg > ./rpt/report_timing_func_max_reg2icg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg > ./rpt/report_timing_func_max_in2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2out > ./rpt/report_timing_func_max_reg2out.rpt


