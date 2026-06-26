########################################################################################
######  DCICC FLOW - DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	common setup
########################################################################################
#set monitor_cpu_memory true
set hierarchy_separator                 /
set sh_source_uses_search_path          true
set report_default_significant_digits   3
set link_create_black_boxes             false
set timing_remove_clock_reconvergence_pessimism true
set timing_clock_reconvergence_pessimism same_transition
set timing_save_pin_arrival_and_slack   true
set timing_crpr_threshold_ps            1.0
set si_enable_analysis                  true
set model_validation_significant_digits 3
set power_enable_analysis               true
set power_clock_network_include_register_clock_pin_power false
set read_parasitics_load_locations      true
set delay_calc_waveform_analysis_mode   full_design

set si_xtalk_double_switching_mode clock_network
if {$var(use_aocvm)} {
set timing_aocvm_enable_analysis true
set timing_aocvm_analysis_mode	$var(aocvm_analysis_mode)
}

set eco_enable_more_scenarios_than_hosts true
file delete -force $var(pt,dmsa,path)
set multi_scenario_working_directory $var(pt,dmsa,path)
set multi_scenario_merged_error_log $var(pt,dmsa,path)/error_log.txt

if {![file isdirectory $var(pt,dmsa,path)]} {
	file mkdir $var(pt,dmsa,path)
}
if {![file isdirectory $var(pt,dmsa,path)/report]} {
	file mkdir $var(pt,dmsa,path)/report
}
if {![file isdirectory $var(pt,dmsa,path)/out]} {
	file mkdir $var(pt,dmsa,path)/out
}

set num_of_scenarios [dict size $lib_mcmm]
if {$num_of_scenarios>16} { set num_of_scenarios 16 }
set_host_options -num_processes $num_of_scenarios -max_cores $num_of_scenarios
report_host_usage -verbose

foreach each_scenario [dict get $nhp_predefine actived_scenarios] {
	create_scenario \
	-name $each_scenario \
	-specific_variables {each_scenario} \
	-specific_data "../CMD/pt_dmsa_mc.tcl"
}

# start processes on all remote machines
start_hosts

# set session focus to all scenarios
current_session -all

##################################################################
#    Save_Session Section                                        #
##################################################################
remote_execute {
	set timing_save_pin_arrival_and_slack true
	update_timing -full
	# Ensure design is properly constrained
	check_timing -verbose > $var(pt,report_path)/report/$var(design_name)_check_timing.report
	save_session $var(pt,report_path)/out/$var(design_name).session
}
##################################################################
#    Report_timing Section                                       #
##################################################################
report_global_timing > $var(pt,dmsa,path)/report/$var(design_name).global_timing
report_analysis_coverage > $var(pt,dmsa,path)/report/$var(design_name).analysis_coverage

remote_execute {
	report_analysis_coverage > ./$var(pt,report_path)/report/$var(design_name).analysis_coverage
	redirect -variable default_avn_rpt {report_analysis_vio_nums}
	echo $default_avn_rpt > ./$var(pt,report_path)/report/analysis_vio_nums.rpt
	echo $default_avn_rpt
	echo $default_avn_rpt >> ./$var(pt,report_path)/time.txt
	foreach_in_collection one_group [get_path_groups] {
        	regsub -all -- {\*} [get_attribute $one_group full_name] "" cur_group_name
        	regsub -all -- {\/} $cur_group_name _ cur_group_name
		regsub -all -- {>} $cur_group_name 2= cur_group_name
        	puts [format "Now creating timing rpt : %s" $cur_group_name]
        	if {[sizeof_collection [get_timing_paths -group $one_group]]>0} {
                	set vio_num_max [sizeof_collection [get_timing_paths -delay_type max -group $one_group -slack_lesser_than 0 -max_paths 2000000]]
                	set vio_num_min [sizeof_collection [get_timing_paths -delay_type min -group $one_group -slack_lesser_than 0 -max_paths 2000000]]
                	if {$vio_num_max>=1000} {
                        	set vio_num_max [expr {$vio_num_max+1}]
                        	report_timing -delay_type max -transition_time -net -capacitance \
                                	-group $one_group -crosstalk_delta -slack_lesser_than 1000 -derate \
                                	-max_paths $vio_num_max -path_type full > ./$var(pt,report_path)/report/${cur_group_name}_max.tim
                	} else {
                        	report_timing -delay_type max -transition_time -net -capacitance \
                                	-group $one_group -crosstalk_delta -slack_lesser_than 1000 -derate \
                                	-max_paths 1000 -path_type full > ./$var(pt,report_path)/report/${cur_group_name}_max.tim
                	}
                	if {$vio_num_min>=1000} {
                        	set vio_num_min [expr {$vio_num_min+1}]
                        	report_timing -delay_type min -transition_time -net -capacitance \
                                	-group $one_group -crosstalk_delta -slack_lesser_than 1000 -derate \
                                	-max_paths $vio_num_min -path_type full > ./$var(pt,report_path)/report/${cur_group_name}_min.tim
                	} else {
                        	report_timing -delay_type min -transition_time -net -capacitance \
                                	-group $one_group -crosstalk_delta -slack_lesser_than 1000 -derate \
                                	-max_paths 1000 -path_type full > ./$var(pt,report_path)/report/${cur_group_name}_min.tim
                	}
        	}
	}
	if {[llength $var(pt,vcd_file)]>0} {
		set power_analysis_mode                 $var(pt,power_mode)
        	if {[llength $var(pt,vcd_time)]>0} {
                	read_vcd -strip_path [lindex $var(pt,vcd_file) 0] [lindex $var(pt,vcd_file) 1] -time $var(pt,vcd_time)
        	} else {
                	read_vcd -strip_path [lindex $var(pt,vcd_file) 0] [lindex $var(pt,vcd_file) 1]
        	}
	} else {
		read_saif -strip_path $var(design_name) $var(pt,saif)
	}
	report_power -verbose > ./$var(pt,report_path)/report/$var(design_name).power
	report_switching_activity > ./$var(pt,report_path)/report/switching_activity.rpt
	report_switching_activity -list_not_annotated > ./$var(pt,report_path)/report/switching_activity_not_annotated.rpt
	report_annotated_parasitics -check -list_not_annotated -max_nets 1000 > ./$var(pt,report_path)/report/parasitics_not_annotated.rpt
	report_constraint -all_violators > ./$var(pt,report_path)/report/vios.rpt
	report_threshold_voltage_group > ./$var(pt,report_path)/report/threshold_voltage_group.rpt
	report_clock_timing -type summary > ./$var(pt,report_path)/report/clock_timing_summary.rpt
	if {$var(pt,mkmodel)} {
        	set_input_transition 0.3 [all_inputs]
        	extract_model -output ./$var(pt,report_path)/out/$var(design_name) -library_cell
        	extract_model -output ./$var(pt,report_path)/out/$var(design_name) -library_cell -format lib
	}
}

save_session $var(pt,dmsa,path)/out/${var(design_name)}.session

if {$var(pt,enable_eco)} {
	set eco_allow_filler_cells_as_open_sites true
	set eco_report_unfixed_reason_max_endpoints 50
	if {![file isdirectory $var(pt,dmsa,path)/eco]} {
		file mkdir $var(pt,dmsa,path)/eco
	}
	remote_execute {
		if {![file isdirectory $var(pt,report_path)/eco]} {
        		file mkdir $var(pt,report_path)/eco
		}
		# set eco options
		set_eco_options	-physical_lib_path $lef_library \
			-physical_design_path $var(pt,final_def) \
			-log_file $var(pt,report_path)/report/pt_eco_physical.log
		report_eco_options
	}
	# fix power
	if {$var(pt,fix_stage_power)} {
		fix_eco_power -verbose
	}
	remote_execute {
		echo [get_attribute [remove_from_collection [get_lib_cells $var(pt,fix_drc_buf_list)] $dont_use_cell_list] base_name] > ../eco/pt_fix_drc_buf_list.txt
		echo [get_attribute [remove_from_collection [get_lib_cells $var(pt,fix_hold_buf_list)] $dont_use_cell_list] base_name] > ../eco/pt_fix_hold_buf_list.txt
	}
	# fix transition
	if {$var(pt,fix_stage_drc)} {
		fix_eco_drc -type max_transition -verbose -methods {size_cell insert_buffer} \
			-buffer_list [read_from_file $var(pt,dmsa,path)/eco/pt_fix_drc_buf_list.txt] \
			-physical_mode $var(pt,eco_physical_mode) -verbose
	}
	# fix setup && hold
	if {$var(pt,fix_stage_timing,setup)} {
		fix_eco_timing -type setup -methods {size_cell} -group $var(pt,fix_setup_group) -ignore_drc \
			-setup_margin $var(pt,setup_opt_margin) -hold_margin $var(pt,hold_opt_margin) \
			-slack_lesser_than $var(pt,setup_opt_slack) -physical_mode $var(pt,eco_physical_mode) -verbose
	}
	if {$var(pt,fix_stage_timing,hold)} {
                fix_eco_timing -type hold -methods {size_cell insert_buffer_at_load_pins} -group $var(pt,fix_hold_group) \
                        -buffer_list [read_from_file $var(pt,dmsa,path)/eco/pt_fix_hold_buf_list.txt] \
			-setup_margin $var(pt,setup_opt_margin) -hold_margin $var(pt,hold_opt_margin) \
			-slack_lesser_than $var(pt,hold_opt_slack) -physical_mode $var(pt,eco_physical_mode) -verbose
	}
	# fix leakage
	if {$var(pt,fix_stage_power) && [llength $final_lib_list]>1} {
		#puts "do leakage optimization .."
		#fix_eco_power -verbose -pattern_priority {STH STN STL} -setup_margin $var(pt,power_opt_margin)
		fix_eco_power -verbose -pattern_priority [dict get $lib_common pt eco_power_priority] -setup_margin $var(pt,power_opt_margin)
	}
	# report eco timing
	report_analysis_coverage > $var(pt,dmsa,path)/eco/$var(design_name).analysis_coverage
	remote_execute {
		redirect -variable eco_avn_rpt {report_analysis_vio_nums}
		echo $eco_avn_rpt
		echo "######\tAfter ECO Fixing ..." >> $var(pt,report_path)/time.txt
		echo $eco_avn_rpt >> $var(pt,report_path)/time.txt
		report_threshold_voltage_group > $var(pt,report_path)/eco/threshold_voltage_group.rpt.eco
	}
	report_constraint -all_violators > $var(pt,dmsa,path)/eco/vios.rpt
	# write scripts
	if {[file isfile $var(eco_scripts)]} {
		file copy -force $var(eco_scripts) ${var(eco_scripts)}_bak
	}
	remote_execute {
		write_changes -format icctcl -output $var(eco_scripts)
	}

	# write eco session
	save_session $var(pt,dmsa,path)/out/${var(design_name)}_eco.session
}

remote_execute {
	set finish_time [clock seconds]
	echo "-----------------------------------------------------" >> ./$var(pt,report_path)/time.txt
	echo [format "PT Total Run     :\t%d days, %s" [expr {[clock format [expr $finish_time - $start_time] -format %j -gmt true]-1}] \
         	[clock format [expr $finish_time - $start_time] -format %H:%M:%S -gmt true]] >> ./$var(pt,report_path)/time.txt
	echo "-----------------------------------------------------" >> ./$var(pt,report_path)/time.txt
	echo "######\tPT Ends   : [date]" >> ./$var(pt,report_path)/time.txt
	echo "-----------------------------------------------------" >> ./$var(pt,report_path)/time.txt
	print_message_info
}

exit
