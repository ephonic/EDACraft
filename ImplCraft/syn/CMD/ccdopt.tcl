########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CTS script
######  Owner : Anonymous , rc
########################################################################################
if {[file isfile $var(cts,constraints)]} {source -echo -verbose $var(cts,constraints)}

report_concurrent_clock_and_data_strategy

report_clock_tree -settings > ./$icc_finalopt/report/clock_tree.setting

set clocklist_cts       [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
remove_ideal_network [all_fanout -flat -from [get_attribute [get_clocks $clocklist_cts] sources]]
set CMD_CLOCK_1 "clock_opt -concurrent_clock_and_data -only_cts -area_recovery"
if {$var(cts,inter_clock_balance)}	{ lappend CMD_CLOCK_1 -inter_clock_balance }
if {$designopt(cong) || $designopt(spg)} { lappend CMD_CLOCK_1 -congestion }
show_current_status [format "s03 clock opt : s1 : %s" $CMD_CLOCK_1]
echo $CMD_CLOCK_1
eval $CMD_CLOCK_1
update_timing
echo [format "########## s03_1 : %s" $CMD_CLOCK_1] > ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

set CMD_CLOCK_2 "clock_opt -concurrent_clock_and_data -only_psyn -area_recovery"
if {$designopt(power)} { lappend CMD_CLOCK_2 -power }
show_current_status [format "s03 clock opt : s2 : %s" $CMD_CLOCK_2]
echo $CMD_CLOCK_2
eval $CMD_CLOCK_2
echo [format "########## s03_2 : %s" $CMD_CLOCK_2] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

set CMD_CLOCK_3 "clock_opt -incremental_concurrent_clock_and_data"
show_current_status [format "s03 clock opt : s3 : %s" $CMD_CLOCK_3]
echo $CMD_CLOCK_3
eval $CMD_CLOCK_3
echo [format "########## s03_3 : %s" $CMD_CLOCK_3] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

set CMD_CLOCK_4 "route_zrt_group -all_clock_nets -reuse_existing_global_route true"
show_current_status [format "s03 clock opt : s4 : %s" $CMD_CLOCK_4]
echo $CMD_CLOCK_4
eval $CMD_CLOCK_4
echo [format "########## s03_4 : %s" $CMD_CLOCK_4] >> ./$icc_finalopt/report/CTS_monitor.rpt
report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt

update_clock_latency
