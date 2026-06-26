########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CTS script
######  Owner : Anonymous , rc
########################################################################################
if {[file isfile $var(cts,constraints)]} {source -echo -verbose $var(cts,constraints)}

#set cts_low_power false	; default is true ,which can impore power but increase the skew.
				# if the clock skew is higher priority over power, plz set this to 'false' before CTS
#set_app_var cts_use_debug_mode true		; # prints additional informations.
set_app_var cts_do_characterization true	; # prints 

report_clock_tree -settings > ./$icc_finalopt/report/clock_tree.setting

set clocklist_cts	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
remove_ideal_network [all_fanout -flat -from [get_attribute [get_clocks $clocklist_cts] sources]]
set CMD_CLOCK_1 "compile_clock_tree -clock_trees \"$clocklist_cts\""
show_current_status [format "s03 clock opt : s1 : %s" $CMD_CLOCK_1]
echo $CMD_CLOCK_1
eval $CMD_CLOCK_1
update_timing
echo [format "########## s03_1 : %s" $CMD_CLOCK_1] > ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

set CMD_CLOCK_2 "optimize_clock_tree -clock_trees \"$clocklist_cts\""
show_current_status [format "s03 clock opt : s2 : %s" $CMD_CLOCK_2]
echo $CMD_CLOCK_2
eval $CMD_CLOCK_2
update_timing
echo [format "########## s03_2 : %s" $CMD_CLOCK_2] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

if {$var(cts,inter_clock_balance)}	{
	set CMD_CLOCK_BALANCE "balance_inter_clock_delay"
	show_current_status [format "s03 clock opt : sb : %s" $CMD_CLOCK_BALANCE]
	echo $CMD_CLOCK_BALANCE
	eval $CMD_CLOCK_BALANCE
	update_timing
	echo [format "########## s03_b : %s" $CMD_CLOCK_BALANCE] >> ./$icc_finalopt/report/CTS_monitor.rpt
	report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
}

set CMD_CLOCK_3 {route_zrt_group -nets [get_nets -of_objects [all_fanout -flat -from [get_attribute [get_clocks $clocklist_cts] sources]]]}
show_current_status [format "s03 clock opt : s3 : %s" $CMD_CLOCK_3]
echo $CMD_CLOCK_3
eval $CMD_CLOCK_3
echo [format "########## s03_3 : %s" $CMD_CLOCK_3] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

#foreach one_clock $clocklist_cts {
	#set_net_routing_layer_constraints -min_layer_name M2 \
					#-max_layer_name [lindex $clock($one_clock) 4] \
					#[get_nets -of_objects [all_fanout -flat -from [get_ports $one_clock]]]
#}

extract_rc
update_timing
set CMD_CLOCK_4 "optimize_clock_tree -clock_trees \"$clocklist_cts\" -routed_clock_stage detail"
show_current_status [format "s03 clock opt : s4 : %s" $CMD_CLOCK_4]
echo $CMD_CLOCK_4
eval $CMD_CLOCK_4
echo [format "########## s03_4 : %s" $CMD_CLOCK_4] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
## Generate clock shielding wires
#  Note: if routing resource is a concern, consider to run these at chip_finish_icc step instead
#create_zrt_shield
#set_route_zrt_common_options -reshield_modified_nets reshield
#set_extraction_options -virtual_shield_extraction false

update_clock_latency
update_timing
set_fix_hold [all_clocks]
#if {$designopt(autoweight)} { my_proc_auto_weights }

#set CMD_CLOCK_5 "psynopt -area_recovery"
#if {$designopt(power)}	{ lappend CMD_CLOCK_5 -power }
#if {$designopt(cong)}	{ lappend CMD_CLOCK_5 -congestion}
#show_current_status [format "s03 clock opt : s5 : %s" $CMD_CLOCK_5]
#echo $CMD_CLOCK_5
#eval $CMD_CLOCK_5
#echo [format "########## s03_5 : %s" $CMD_CLOCK_5] >> ./$icc_finalopt/report/CTS_monitor.rpt
#report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
