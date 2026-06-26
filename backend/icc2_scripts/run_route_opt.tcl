####### load design
open_lib./db_in/mcu_top.nlib
open_block mcu_top
gui_sta

#######
set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario func.tt0p9v.wc.cmax_25c.setup

####### set hold cell list
set hold_cell_list [list \
*/DEL025D1BWP30P140UHVT \
*/DEL050D1BWP30P140UHVT \
*/DEL075D1BWP30P140UHVT \
*/DEL150D1BWP30P140UHVT \
*/DEL200D1BWP30P140UHVT \
*/DEL250D1BWP30P140UHVT \
]
set_dont_touch [get_lib_cells -quiet $hold_cell_list] false
set_lib_cell_purpose -exclude hold [get_lib_cells -quiet */*]
set_lib_cell_purpose -include hold [get_lib_cells -quiet $hold_cell_list]

####### pre setting
set_app_option -name route_opt.flow.enable_cto -value false
set_app_option -name route_opt.flow.enable_ccd_clock_drc_fixing -value always_off
set_app_option -name route_opt.flow.enable_clock_power_recovery -value none
set_app_option -name route_opt.flow.enable_ccd -value false

set_app_option -name time.use_pt_delay -value true
set_app_option -name time.enable_si_timing_windows -value true

set_app_option -name opt.power.mode -value leakage
set_app_option -name opt.power.effort -value high
set_app_option -name route_opt.flow.enable_power -value false

#set_false_path -from [all_inputs]
#set_false_path -to [all_outputs]
set_host_option -max_cores 64 -num_process 8
####### route opt
route_opt
route_eco
####### connect pg
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl

report_timing
check_routes
check_lvs -max_errors 99999
check_legality

####### save
save_lib
save_block
save_block -as 10_route_opt
####### report
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg > ./rpt/report_timing_func_max_reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg > ./rpt/report_timing_func_max_reg2icg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg > ./rpt/report_timing_func_max_in2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2out > ./rpt/report_timing_func_max_reg2out.rpt

set active_scenarios "func.ff1p1v.bc.cmin_85c.hold"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
report_timing -scenario func.ff1p1v.bc.cmin_85c.hold -delay_type min -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg > ./rpt/report_timing_func_min_reg2reg.rpt
report_timing -scenario func.ff1p1v.bc.cmin_85c.hold -delay_type min -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg > ./rpt/report_timing_func_min_reg2icg.rpt
report_timing -scenario func.ff1p1v.bc.cmin_85c.hold -delay_type min -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg > ./rpt/report_timing_func_min_in2reg.rpt
report_timing -scenario func.ff1p1v.bc.cmin_85c.hold -delay_type min -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2out > ./rpt/report_timing_func_min_reg2out.rpt

check_route > ./rpt/check_route.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute -derate -voltage -delay_type max > ./rpt/route_opt_report_timing.rpt

set errors [get_drc_errors -error_data zroute.err -filter {type_name == "Short"}]
set pins ""
foreach_in_collection error $errors {
set net [get_attribute $error objects]
set pin [get_pins -q -all -of_objects [get_nets -q -all $net]]
set pins [add_to_collection -uniq $pins $pin]
}
remove_shape [get_shapes -of_objects [get_nets -of_objects $pins]]
remove_via   [get_vias   -of_objects [get_nets -of_objects $pins]]
route_eco -reroute modified_nets_first_then_others
route_detail -incremental true
check_routes

###
set errors [get_drc_errors -error_data zroute.err -filter {type_name == "Less than NDR width"}]
set pins ""
foreach_in_collection error $errors {
 set net [get_attribute $error objects]
 set pin [get_pins -q -all -of_objects [get_nets -q -all $net]]
 set pins [add_to_collection -uniq $pins $pin]
}
remove_shape [get_shapes -of_objects [get_nets -of_objects $pins]]
remove_via   [get_vias   -of_objects [get_nets -of_objects $pins]]
route_eco -reroute modified_nets_first_then_others
route_detail -incremental true
check_routes
###
set errors [get_drc_errors -error_data zroute.err -filter {type_name == "Short"}]
set pins ""
foreach_in_collection error $errors {
 set net [get_attribute $error objects]
 set pin [get_pins -q -all -of_objects [get_nets -q -all $net]]
 set pins [add_to_collection -uniq $pins $pin]
}
remove_shape [get_shapes -of_objects [get_nets -of_objects $pins]]
remove_via   [get_vias   -of_objects [get_nets -of_objects $pins]]
route_eco -reroute modified_nets_first_then_others
route_detail -incremental true
