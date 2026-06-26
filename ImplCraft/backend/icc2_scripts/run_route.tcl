


set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario func.tt0p9v.wc.cmax_25c.setup

####### pre setting
set_ignored_layers -min_routing_layer M2 -max_routing_layer M9
set_app_options -name route.global.timing_driven -value true
set_app_options -name route.track.timing_driven -value true
set_app_options -name route.detail.timing_driven -value true
set_app_options -name route.global.crosstalk_driven -value true
set_app_options -name route.track.crosstalk_driven -value true
set_app_options -name time.si_enable_analysis -value true
set_host_option -max_cores 64 -num_process 8
####### route
#set_app_options -name clock_opt.flow.enable_global_route_opt -value tru
#clock_opt -from global_route_opt

route_global


route_track

route_detail




check_route
route_detail -incremental true -initial_drc_from_input true


check_route
####### detail
add_redundant_vias

####### connect pg
####### connect pg
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl
####### save
save_lib
save_block
save_block -as 9_route

####### report
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg > ./rpt/report_timing_func_max_reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg > ./rpt/report_timing_func_max_reg2icg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg > ./rpt/report_timing_func_max_in2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2out > ./rpt/report_timing_func_max_reg2out.rpt



check_route > ./rpt/check_route.rpt
