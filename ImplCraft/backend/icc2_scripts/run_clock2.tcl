

####### select scenario
set active_scenarios "func.tt0p9v.wc.cmax_25c.setup"
set_scenario_status -active false [get_scenarios -filter active]
set_scenario_status -active true $active_scenarios
current_scenario func.tt0p9v.wc.cmax_25c.setup

####### ndr
create_routing_rule clock_trunk -default_reference_rule \
    -widths {M2 0.1 M3 0.1 M4 0.1 M5 0.2 M6 0.2 M7 0.2 M8 0.2} \
    -spacings {M2 0.1 M3 0.1 M4 0.1 M5 0.1 M6 0.1 M7 0.1 M8 0.1} \
    -spacing_length_thresholds {M2 0.4 M3 0.4 M4 0.4 M5 0.4 M6 0.4 M7 0.4 M8 0.4}
create_routing_rule clock_leaf -default_reference_rule \
    -widths {M2 0.1 M3 0.1 M4 0.1 M5 0.1 M6 0.1 M7 0.1 M8 0.1} \
    -spacings {M2 0.1 M3 0.1 M4 0.1 M5 0.1 M6 0.1 M7 0.1 M8 0.1} \
    -spacing_length_thresholds {M2 0.4 M3 0.4 M4 0.4 M5 0.4 M6 0.4 M7 0.4 M8 0.4}
set_clock_routing_rules -net_type root -rules clock_trunk -min_routing_layer M2 -max_routing_layer M8
set_clock_routing_rules -net_type internal -rules clock_trunk -min_routing_layer M2 -max_routing_layer M8
set_clock_routing_rules -net_type sink -rules clock_leaf -min_routing_layer M2 -max_routing_layer M8


####### select clock cell
set cts_cell_list [list \
*/INVD2BWP30P140UHVT \
*/INVD32BWP30P140UHVT \
*/INVD24BWP30P140UHVT \
*/INVD21BWP30P140UHVT \
*/INVD20BWP30P140UHVT \
*/INVD18BWP30P140UHVT \
*/INVD16BWP30P140UHVT \
*/INVD15BWP30P140UHVT \
*/INVD12BWP30P140UHVT \
*/INVD9BWP30P140UHVT \
*/INVD8BWP30P140UHVT \
*/INVD6BWP30P140UHVT \
*/INVD4BWP30P140UHVT \
]
set_lib_cell_purpose -exclude cts [get_lib_cells -quiet */*]
set_lib_cell_purpose -include cts [get_lib_cells -quiet $cts_cell_list]

####### pre setting
set_app_options -list {cts.common.verbose 1}
set_app_options -list {cts.common.max_fanout 10}
set_app_options -list {cts.common.max_net_length 200}
set_clock_tree_options -target_skew 0.30 -clocks [get_clocks *clk*] -corners wc
set_host_option -max_cores 64 -num_process 8
#set non_macro_pins [get_flat_pins -of_objects [get_flat_cells -filter "design_type!=macro" ] -filter "layer_name=~*M1*"]
#set_attribute -objects [get_terminals -of_objects $non_macro_pins ] -name port.connect_within_pin -value via_wire
#set_app_options -name route.common.derive_connect_within_pin_via_region -value true
####### cts
clock_opt -from build_clock -to build_clock
clock_opt -from route_clock -to route_clock


source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl

####### save
save_lib
save_block
save_block -as 7_clock2

####### report
report_clock_qor -type latency -nosplit -significant_digits 3 > ./rpt/clock_qor.rpt
report_timing -nosplit -report_by scenario -transition_time -capacitance -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute -derate -voltage -delay_type max > ./rpt/cts_report_timing.rpt

report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2reg > ./rpt/report_timing_func_max_reg2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2icg > ./rpt/report_timing_func_max_reg2icg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups in2reg > ./rpt/report_timing_func_max_in2reg.rpt
report_timing -nosplit -significant_digits 3 -input_pins -nets -max_paths 9999 -slack_lesser_than 0 -groups reg2out > ./rpt/report_timing_func_max_reg2out.rpt
