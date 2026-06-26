########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	common setup
########################################################################################
if {[string equal $var(mw_lib_name,icc) SYN]} {
	set source_mw_cel s04_route_opt
} else {
	set source_mw_cel $var(design_name)
}
open_mw_cel -readonly $source_mw_cel

set postfix_libs [get_attribute [current_mw_cel] library_strategy]_opt
array unset library_cur_used
foreach one $final_lib_list {
	set library_cur_used($one) 1
}
foreach one [split [get_attribute [current_mw_cel] library_last_used] _] {
	array unset library_cur_used $one
}
if {[array size library_cur_used]>0} {
	set postfix_libs ${postfix_libs}_[join [lsort [array name library_cur_used]] _]
}
set mw_finalopt         $var(mw_lib_name,icc)_$postfix_libs
regsub -- "$var(mw_lib_name,icc)" $mw_finalopt ICC icc_finalopt


close_mw_lib

###     create new ICC working directories
if {![file isdirectory $icc_finalopt]} {
        file mkdir $icc_finalopt
}       
if {![file isdirectory $icc_finalopt/report]} {
        file mkdir $icc_finalopt/report 
}       
if {![file isdirectory $icc_finalopt/out]} {
        file mkdir $icc_finalopt/out
}       
###     create or open new MW
if {![file isdirectory $mw_finalopt ]} {
	extend_mw_layers
        create_mw_lib -technology [dict get $nhp_predefine tf_file] -mw_reference_library [dict get $nhp_predefine ref_mw] $mw_finalopt
} else {
        set_mw_lib_reference $mw_finalopt -mw_reference_library [dict get $nhp_predefine ref_mw]
}       
puts [format "Script Info:: now copy mw cel(%s) from lib(%s) to lib(%s) as cel(%s)" $source_mw_cel $var(mw_lib_name,icc) $mw_finalopt $var(design_name)]
copy_mw_cel -from_library $var(mw_lib_name,icc) -from $source_mw_cel -to $var(design_name) -to_library $mw_finalopt -overwrite
        
open_mw_lib $mw_finalopt
set_tlu_plus_files -max_tluplus [dict get $nhp_predefine tlu_file] -tech2itf_map [dict get $nhp_predefine itfmap_file]
if {!$var(use_def_track)} {
                create_lib_track -dir [dict get $lib_common lib_track dir] \
                        -offset [dict get $lib_common lib_track offset]
}
open_mw_cel $var(design_name)

set_attribute [current_mw_cel] library_strategy $postfix_libs
set_attribute [current_mw_cel] library_last_used [join [lsort [array name all_lib_list]] _]

if {$var(insert,listdecap)} {
	set_lib_cell_spacing_label -names SP_CELL \
                                -left_lib_cells [dict get $nhp_predefine listdecap_cells] \
                                -right_lib_cells [dict get $nhp_predefine listdecap_cells]
        set_lib_cell_spacing_label -names ALL_CELL -left_lib_cells {*} -right_lib_cells {*}
        set listdecap_sites [expr {int([lindex [get_attribute [get_physical_lib_cells [dict get $lib_define $main_lib_name function_cell predecap]] bbox] 1 0]
                                /
                                [get_attribute [index_collection [get_site_rows] 0] site_space])}]
        set_spacing_label_rule -labels {SP_CELL ALL_CELL} "0 [expr {$listdecap_sites-1}]"
}

current_mw_cel

########################################################################################
###	s05 focalopt design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s05_focal_opt"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

echo [format "### %s" "s04_route_opt"] > ./$icc_finalopt/report/focal_opt.txt
echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {[llength $var(libs_finalopt)]>0} {
	if {[llength $var(libs)]==[llength $final_lib_list]} {
		puts "Script Info:: No New Libraries specified!! Skip appending libraries operations!!"
	} else {
		report_threshold_voltage_group > ./$icc_finalopt/report/$var(design_name).threshold_voltage_group.bf_final_opt
		report_power > ./$icc_finalopt/report/$var(design_name).power.bf_final_opt
		puts "Script Info:: Using new libraries for final focal timing && power optimization : $final_lib_list"
		set_app_var target_library      ""
		foreach mvt_one $final_lib_list {
			foreach each_corner [array name corner_used] {
				set_app_var target_library      [concat $target_library [dict get $lib_define $mvt_one db $each_corner]]
			}
		}
		puts [format "Script Info:: Additional Timing && Power Optimization using : %s" $target_library]
	}
}
###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

set_app_var compile_instance_name_prefix ICC_FOCAL_OPT
set_app_var timing_use_ceff_for_drc $var(use_ceff)

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        set_active_scenarios [dict get $nhp_predefine actived_scenarios]
        current_scenario $var(mcmm_default_view)
}

if {[file isfile $var(focal,constraints)]} {
	source -echo -verbose $var(focal,constraints)
}

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	foreach one_sc [all_active_scenarios] {
		report_constraint -significant_digits 3 -all_violators -nosplit \
				-scenarios $one_sc > ./$icc_finalopt/report/all_vio.s04.${one_sc}.cons
	}
} else {
	report_constraint -significant_digits 3 -all_violators -nosplit \
			 > ./$icc_finalopt/report/all_vio.s04.cons
}

if {$designopt(focal_opt) && $var(focal,xtalk)} {
	show_current_status "$phase_name : focal_opt -xtalk_reduction"
	set tmp_file_focal_opt [get_focal_opt_xtalk_cons $var(focal,xtalk)]
	if {[file size $tmp_file_focal_opt]>0} { focal_opt -xtalk_reduction_nets $tmp_file_focal_opt }
	echo [format "### %s" "focal_opt -xtalk_reduction_nets $tmp_file_focal_opt"] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
}

###	fix drc_nets violations
if {$designopt(focal_opt) && $var(focal,drc)} {
	show_current_status "$phase_name : focal_opt -drc_nets (1st)"
	focal_opt -drc_nets all
	echo [format "### %s" "focal_opt -drc_nets all"] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
}

if {$designopt(focal_opt) && [llength $final_lib_list]>1} {
	###	fix setup violations
	show_current_status "$phase_name : focal_opt -setup_endpoints"
	set CMD_FOCAL_OPT_SETUP "focal_opt -setup_endpoints"
	if {[string equal $var(focal,fix_setup_group) *]} {
		lappend CMD_FOCAL_OPT_SETUP all
	} else {
		set tmp_file_focal_opt [get_focal_opt_timing_cons max_delay $var(focal,fix_setup_group)]
		if {[file size $tmp_file_focal_opt]>0} { lappend CMD_FOCAL_OPT_SETUP $tmp_file_focal_opt }
	}
	eval $CMD_FOCAL_OPT_SETUP
	echo [format "### %s" $CMD_FOCAL_OPT_SETUP] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
	###	focal opt power
	show_current_status "$phase_name : focal_opt -power"
	set_app_var timing_remove_clock_reconvergence_pessimism false
	set_app_var focalopt_power_critical_range $var(focal,power_critical_range)
	focal_opt -power
	set_app_var timing_remove_clock_reconvergence_pessimism true
	echo [format "### %s" "focal_opt -power"] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt

	###	fix drc_pins violations
	if {$var(focal,drc)} {
		show_current_status "$phase_name : focal_opt -drc_nets (2nd)"
		focal_opt -drc_pins all
		echo [format "### %s" "focal_opt -drc_pins all"] >> ./$icc_finalopt/report/focal_opt.txt
		echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
	}
}
###	incremental fix hold violations
if {$designopt(focal_opt)} {
	show_current_status "$phase_name : focal_opt -hold_endpoints"
	set CMD_FOCAL_OPT_HOLD "focal_opt -hold_endpoints"
	if {[string equal $var(focal,fix_hold_group) *]} {
		lappend CMD_FOCAL_OPT_HOLD all
	} else {
		set tmp_file_focal_opt [get_focal_opt_timing_cons min_delay $var(focal,fix_hold_group)]
		if {[file size $tmp_file_focal_opt]>0} { lappend CMD_FOCAL_OPT_HOLD $tmp_file_focal_opt }
	}
	eval $CMD_FOCAL_OPT_HOLD
	echo [format "### %s" $CMD_FOCAL_OPT_HOLD] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
}

## The following route_opt command performs final overall optimization with -size_only option which is used
#  to avoid potential route and cell disturbances associated with buffer insertion.
#  Refer to SolvNet #034130 for more details about postroute design closre flow. 
if {$designopt(focal_opt) && $var(route_after_focal_opt)} {
	show_current_status "$phase_name : route_opt -incremental"
	save_mw_cel -as s05_focal_before_route
	route_opt -incremental -size_only
	echo [format "### %s" "route_opt -incremental -size_only"] >> ./$icc_finalopt/report/focal_opt.txt
	echo [get_qor_summary 3] >> ./$icc_finalopt/report/focal_opt.txt
}

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

set_app_var compile_instance_name_prefix U

report_all ./$icc_finalopt/report $phase_name

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	foreach one_sc [all_active_scenarios] {
		report_constraint -significant_digits 3 -all_violators -nosplit \
				-scenarios $one_sc > ./$icc_finalopt/report/all_vio.s05.${one_sc}.cons
	}
} else {
	report_constraint -significant_digits 3 -all_violators -nosplit \
			 > ./$icc_finalopt/report/all_vio.s05.cons
}

if {[dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} {
	echo [format "########## s05 : %s" $phase_name] >> ./$icc_finalopt/report/CTS_monitor.rpt
	report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
}

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary 3] >> ./$icc_finalopt/time.txt
########################################################################################
###	s06 finishchip design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s06_chip_finish"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

#if {$designopt(autoweight)} { my_proc_auto_weights }
##Turn of soft spacing for timing optimization during chip finishing
set_route_zrt_detail_options -eco_route_use_soft_spacing_for_timing_optimization false

###	incremental fixing antenna && drc
#set_route_zrt_detail_options -antenna true -antenna_on_iteration 3
#route_zrt_detail -max_number_iterations 3 -incremental true -initial_drc_from_input true

# insert filler and de-cap cells
show_current_status "$phase_name : insert_stdcell_filler"
if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_insert_fillcap] &&
        [file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_fillcap]]} {
	###	for 16nm
	set loop_for_insert_filler 1
	if {[sizeof_collection [all_physical_only_cells *CAP*IN*]]>0} {
		set loop_for_insert_filler [expr {$loop_for_insert_filler+[sizeof_collection [all_physical_only_cells *CAP*IN*]]}]
	}
	set loop_for_insert_filler_i 0
	while {$loop_for_insert_filler} {
		incr loop_for_insert_filler  -1
		incr loop_for_insert_filler_i 1
		set message_error_count [get_message_info -error_count]
		puts [format "Script Info:: Insert stdfiller in %s try! with error : %s" $loop_for_insert_filler_i $message_error_count]
       		source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_fillcap]
		if {$message_error_count==[get_message_info -error_count]} {
			puts [format "Script Info:: Insert stdfiller done at %s try! with error : %s" $loop_for_insert_filler_i $message_error_count]
			break
		}
	}
} else {
	###	for 28nm and 40nm
	source -echo -verbose ../CMD/insert_fill_decap.tcl
}

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie


if {!$designopt(fast_mode)} {
	show_current_status "$phase_name : spread && widen zrt wires"
	spread_zrt_wires -timing_preserve_setup_slack_threshold $var(timing_preserve_slack_setup) -timing_preserve_hold_slack_threshold $var(timing_preserve_slack_hold)
	widen_zrt_wires -timing_preserve_setup_slack_threshold $var(timing_preserve_slack_setup) -timing_preserve_hold_slack_threshold $var(timing_preserve_slack_hold)
}

###	delete floating shape && fixing open nets
show_current_status "$phase_name : verify && fix wires"
remove_zrt_redundant_shapes -remove_floating_shapes true \
	-remove_dangling_shapes true \
	-route_types {nonfixed_route} \
	-report_changed_nets true
verify_lvs -exclude_nets {VDD VSS} > ./$icc_finalopt/report/verify_lvs_ochk.rpt
open_mw_cel -not_as_current $var(design_name)_lvs.err
if {[sizeof_collection [get_drc_errors -quiet -error_view $var(design_name)_lvs.err -filter {type==Open}]]>0} {
	route_zrt_eco -open_net_driven true
}
close_mw_cel $var(design_name)_lvs.err

###	ECO Fixing DRC && LVS 1st
verify_zrt_route -report_all_open_nets true \
	-check_from_user_shapes true \
	-drc true > ./$icc_finalopt/report/verify_zroute_1st.rpt
verify_lvs -exclude_nets {VDD VSS} > ./$icc_finalopt/report/verify_lvs_1st.rpt
open_mw_cel -not_as_current $var(design_name)_lvs.err
## fix double-via & other drc errors
if {[sizeof_collection [get_drc_errors -quiet -filter {type != "Illegal Bridge"}]]>0 || [sizeof_collection [get_drc_errors -quiet -error_view $var(design_name)_lvs.err -filter {type==Open}]]>0} {
	set nets_need_eco [filter_collection [add_to_collection -unique [get_attribute [get_drc_errors -quiet -filter {type != "Illegal Bridge"}] nets] [get_attribute [get_drc_errors -quiet -error_view $var(design_name)_lvs.err -filter {type==Open}] nets]] {net_type!=Power && net_type!=Ground}]
	if {[sizeof_collection $nets_need_eco]>0} {
		route_zrt_eco -nets [add_to_collection -unique [get_attribute [get_drc_errors -quiet -filter {type != "Illegal Bridge"}] nets] [get_attribute [get_drc_errors -quiet -error_view $var(design_name)_lvs.err -filter {type==Open}] nets]]
		## verify_lvs_fixed
        	verify_lvs -exclude_nets {VDD VSS} > ./$icc_finalopt/report/verify_lvs_1st_fixed.rpt
        	## verify Zroute violation_fixed
        	verify_zrt_route -report_all_open_nets true \
			-check_from_user_shapes true \
			-drc true  > ./$icc_finalopt/report/verify_zroute_1st_fixed.rpt
	}
}
close_mw_cel $var(design_name)_lvs.err

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
verify_pg_nets -error_cell PG_CHECK_FINAL > ./$icc_finalopt/report/verify_pg_nets.final.rpt

report_all ./$icc_finalopt/report $phase_name

if {[dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} {
	echo [format "########## s06 : %s" $phase_name] >> ./$icc_finalopt/report/CTS_monitor.rpt
	report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
}

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary 3] >> ./$icc_finalopt/time.txt
########################################################################################
###	s07 output design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s07_output_design"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -create_ports top
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

###	create PG Label
create_pg_text_by_cell [index_collection [all_physical_only_cells *[lindex [dict get $nhp_predefine welltap_cell] 0]*] 0] \
			[lindex [dict get $nhp_predefine welltap_cell] 2] \
			[lindex [dict get $nhp_predefine welltap_cell] 3] \
			[lindex [dict get $nhp_predefine welltap_cell] 4]

###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

###	write verilog netlist
change_names -hierarchy -rule verilog
## refresh WM to keep the name of net and port consistent, otherwise the spef used for PT will be wrong
define_name_rules -remove_internal_net_bus -equal_ports_nets -inout_ports_equal_nets NAMERULE_NET_PORT_CONSISTENT
change_names -rules NAMERULE_NET_PORT_CONSISTENT

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	set_active_scenarios [dict get $nhp_predefine actived_scenarios]
}

###	save_mw_cel 

set pg_strip_m1 [get_net_shapes -quiet -filter {route_type=~"P/G*" && layer==M1 && width==0.130}]
if {[sizeof_collection $pg_strip_m1]>0} {
	remove_objects $pg_strip_m1
}

save_mw_cel -as $phase_name

save_mw_cel
current_mw_cel

show_current_status "$phase_name : signoff_drc" 
###	in-design signoff drc && auto fix.
if {$var(icv,signoff_drc) || $var(icv,signoff_autofix_drc)} {
	redirect -tee -file ./$icc_finalopt/report/signoff_drc.check.rpt {signoff_drc -ignore_child_cell_errors -read_cel_view -user_defined_options {-holding_cell}}
}

if {$var(icv,signoff_autofix_drc)} {
	redirect -tee -file ./$icc_finalopt/report/signoff_drc.autofix.rpt {signoff_autofix_drc -init_drc_error_db signoff_drc_run}
	save_mw_cel
}

if {$var(icv,signoff_metal_fill) && [dict exists $lib_common icv FILL_RUNSET]} {
        set_extraction_options -real_metalfill_extraction none
	set CMD_SIGNOFF_METAL_FILL      "signoff_metal_fill"
	if {$var(icv,signoff_metal_fill,flat)} { append CMD_SIGNOFF_METAL_FILL " -mode flat" }
        if {![string equal $var(icv,signoff_metal_fill,setup_slack_threshold) off]} {
                append CMD_SIGNOFF_METAL_FILL " -timing_preserve_setup_slack_threshold $var(icv,signoff_metal_fill,setup_slack_threshold)"
        }
        if {[llength $var(icv,signoff_metal_fill,selected_layers)]>0} {
                append CMD_SIGNOFF_METAL_FILL " -select_layers {$var(icv,signoff_metal_fill,selected_layers)}"
        }
        echo $CMD_SIGNOFF_METAL_FILL
        eval $CMD_SIGNOFF_METAL_FILL
        set_extraction_options -real_metalfill_extraction floating
        #save_mw_cel
}

##################################
###	final report files   #####
##################################
# timing
show_current_status "$phase_name : report && output"
set final_qor_summary [get_qor_summary 3]

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	foreach one_sc [all_active_scenarios] {
		foreach one_group [get_attribute [get_path_groups] name] {
			regsub -all -- {\*} $one_group "" one_group_name
			regsub -all -- {/} $one_group_name _ one_group_name
			regsub -all -- {>} $one_group_name 2= one_group_name
			report_timing -delay max -transition_time -input_pins -capacitance -physical \
			-nets -significant_digits 3 -sort_by slack -max_paths 100 -derate -crosstalk_delta \
			-group $one_group -scenarios $one_sc > ./$icc_finalopt/report/$one_group_name\_max.${one_sc}.tim
		}
		foreach one_group [get_attribute [get_path_groups] name] {
			regsub -all -- {\*} $one_group "" one_group_name
			regsub -all -- {/} $one_group_name _ one_group_name
			regsub -all -- {>} $one_group_name 2= one_group_name
			report_timing -delay min -transition_time -input_pins -capacitance -physical \
			-nets -significant_digits 3 -sort_by slack -max_paths 100 -derate -crosstalk_delta \
			-group $one_group -scenarios $one_sc > ./$icc_finalopt/report/$one_group_name\_min.${one_sc}.tim
		}
		# slope
		report_constraint -significant_digits 3 -all_violators -nosplit \
				-max_transition -scenarios $one_sc > ./$icc_finalopt/report/$var(design_name).${one_sc}.slope
		# all_vios
		report_constraint -significant_digits 3 -all_violators -nosplit \
				-scenarios $one_sc > ./$icc_finalopt/report/$var(design_name).${one_sc}.all_vios
	}
} else {
	foreach one_group [get_attribute [get_path_groups] name] {
		regsub -all -- {\*} $one_group "" one_group_name
		regsub -all -- {/} $one_group_name _ one_group_name
		regsub -all -- {>} $one_group_name 2= one_group_name
		report_timing -delay max -transition_time -input_pins -capacitance -physical \
		-nets -significant_digits 3 -sort_by slack -max_paths 100 -derate -crosstalk_delta \
		-group $one_group > ./$icc_finalopt/report/$one_group_name\_max.tim
	}
	foreach one_group [get_attribute [get_path_groups] name] {
		regsub -all -- {\*} $one_group "" one_group_name
		regsub -all -- {/} $one_group_name _ one_group_name
		regsub -all -- {>} $one_group_name 2= one_group_name
		report_timing -delay min -transition_time -input_pins -capacitance -physical \
		-nets -significant_digits 3 -sort_by slack -max_paths 100 -derate -crosstalk_delta \
		-group $one_group > ./$icc_finalopt/report/$one_group_name\_min.tim
	}
	# slope
	report_constraint -significant_digits 3 -all_violators -nosplit \
			-max_transition > ./$icc_finalopt/report/$var(design_name).slope
	# all_vios
	report_constraint -significant_digits 3 -all_violators -nosplit \
			 > ./$icc_finalopt/report/$var(design_name).all_vios
}
# clock (if CTS)
if {[dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} {
	report_clock_tree -summary -structure -settings     > ./$icc_finalopt/report/$var(design_name).clock_tree
	if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
		report_clock_timing -type skew -significant_digits 3 -verbose -scenarios [all_active_scenarios] > ./$icc_finalopt/report/$var(design_name).clock_timing
	} else {
		report_clock_timing -type skew -significant_digits 3 -verbose   > ./$icc_finalopt/report/$var(design_name).clock_timing
	}
}
# qor
report_qor -physical -sig 3 > ./$icc_finalopt/report/$var(design_name).qor
report_qor -sig 3	>> ./$icc_finalopt/report/$var(design_name).qor
# xtalk
report_net_delta_delay -histogram > ./$icc_finalopt/report/$var(design_name).delta
if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	# power
	report_power -scenarios [all_active_scenarios] > ./$icc_finalopt/report/$var(design_name).power
} else {
	# power
	report_power > ./$icc_finalopt/report/$var(design_name).power
}
# routing information
report_design_physical -all -verbose > ./$icc_finalopt/report/$var(design_name).sum
# PR summary
report_design   -physical > ./$icc_finalopt/report/$var(design_name).pr_summary
# Shielding
#report_zrt_shield -per_layer true -output ICC/report/$var(design_name).shield
# threshold voltage group
report_threshold_voltage_group > ./$icc_finalopt/report/$var(design_name).threshold_voltage_group
# clock gating
report_clock_gating -style > ./$icc_finalopt/report/clock_gating.rpt
# spef file
write_parasitics -out ./$icc_finalopt/out/$var(design_name).spef
# wire summary
if {[llength $clocklist_mesh]==0} {
	report_wire_caps ./$icc_finalopt/report/$var(design_name).wire_sum 1
}
# check_finfet_grid
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
	check_finfet_grid > ./$icc_finalopt/report/check_finfet_grid.s07.rpt
}

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	current_scenario $var(mcmm_default_view)
}
##################################
###   write constraints      #####
##################################
#set_app_var write_sdc_output_lumped_net_capacitance false
#set_app_var write_sdc_output_net_resistance false
if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        foreach each [all_active_scenarios] {
                current_scenario $each
                write_sdc -nosplit ./$icc_finalopt/out/$var(design_name).$each.sdc
        }
        current_scenario $var(mcmm_default_view)
} else {
        write_sdc -nosplit ./$icc_finalopt/out/$var(design_name).sdc
}
write_saif -output ./$icc_finalopt/out/$var(design_name).saif -propagated
# Shielding
report_zrt_shield -per_layer true -output ICC/report/$var(design_name).shield
#extract_rc -coupling_cap
#write_parasitics  -format SPEF -output $var(result_path_icc)/$var(design_name).spef
#write_parasitics  -format SBPF -output $var(result_path_icc)/$var(design_name).sbpf
##################################
###     write GDSII&&DEF     #####
##################################
### set write GDSII option
set_write_stream_options -output_pin {text geometry} -max_name_length 64 \
			-resize_text {0 0.1} -pin_name_mag 0.1 \
			-rotate_pin_text_by_access_dir \
			-output_geometry_property \
			-output_net_name_as_property 100 \
			-output_instance_name_as_property 102 \
			-keep_data_type \
			-map_layer [dict get $nhp_predefine gdsmap_file]

if {[sizeof_collection [get_user_shapes -quiet]]>0} {
        remove_objects [get_user_shapes -quiet]
}

if {[file isfile ../DEF/$var(design_name).def]} {
	write_stream -cells $var(design_name) ./$icc_finalopt/out/$var(design_name).gds
	write_def -output ./$icc_finalopt/out/$var(design_name).def -all_vias
	## delete power and ground net for icfb-->def flow
	remove_route_by_type -pg_strap -pg_std_cell_pin_conn -nets {VDD VSS}
	write_stream -cells $var(design_name) ./$icc_finalopt/out/$var(design_name)_nopg.gds
	write_def -output ./$icc_finalopt/out/$var(design_name)_nopg.def -all_vias
} else {
	write_stream -cells $var(design_name) ./$icc_finalopt/out/$var(design_name).gds
	write_def -output ./$icc_finalopt/out/$var(design_name).def -all_vias
}
if {$var(icv,signoff_metal_fill) && [sizeof_collection [get_mw_cels -quiet $var(design_name).FILL]]>0} {
        echo "$var(design_name) $var(design_name)_metalfill_icv" > rename_metalfill.tcl
        set_write_stream_options -rename_cell rename_metalfill.tcl
        write_stream -cells $var(design_name).FILL ./$icc_finalopt/out/$var(design_name)_metalfill_icv.gds
        set_write_stream_options -rename_cell {}
}

##################################
###  write verilog netlist   #####
##################################
## write verilog without ant diode
write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
		-no_tap_cells -no_cover_cells -no_chip_cells \
		-no_corner_pad_cells -no_pad_filler_cells \
		-no_core_filler_cells -no_physical_only_cells \
		-no_unconnected_cells -unconnected_ports ./$icc_finalopt/out/$var(design_name).v
## write ant diode in verilog file
write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
		-no_tap_cells -no_cover_cells -no_chip_cells \
		-no_corner_pad_cells -no_pad_filler_cells \
		-no_core_filler_cells -no_physical_only_cells \
		-no_unconnected_cells -unconnected_ports -diode_ports ./$icc_finalopt/out/$var(design_name)_ant.v
## write pg ports in verilog file, no diode
write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
		-no_tap_cells -no_cover_cells -no_chip_cells \
		-no_corner_pad_cells -no_pad_filler_cells \
		-no_core_filler_cells -no_physical_only_cells \
		-no_unconnected_cells -unconnected_ports -pg ./$icc_finalopt/out/$var(design_name)_pg.v
## write pg ports in verilog file, with all cells
write_verilog   -keep_backslash_before_hiersep -no_io_pad_cells \
                -no_tap_cells -no_cover_cells -no_chip_cells \
                -no_corner_pad_cells -no_pad_filler_cells -no_core_filler_cells \
                -unconnected_ports -pg -diode_ports ./$icc_finalopt/out/$var(design_name)_full.v
## write verilog without ant diode, split bus
write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells -split_bus \
		-no_tap_cells -no_cover_cells -no_chip_cells \
		-no_corner_pad_cells -no_pad_filler_cells \
		-no_core_filler_cells -no_physical_only_cells \
		-no_unconnected_cells -unconnected_ports ./$icc_finalopt/out/$var(design_name)_splitbus.v
close_mw_cel

if {$var(output,splitgds)} {
###	split output gds file
	show_current_status "$phase_name : splitgds"
	open_mw_cel $var(design_name)
	set directory_for_splitgds ./$icc_finalopt/out
	source -echo -verbose ../CMD/icc_out_splitgds.tcl
}

##################################
###     Show Final Results   #####
##################################
open_mw_cel $var(design_name)
set final_routing_quality  [report_final_routing_quality]

set clocklist_mesh	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
if {[llength $clocklist_mesh]>0} {
	show_current_status "$phase_name : check && split mesh clocks"
	set mesh_split_flag	0
	if {$designopt(split_mesh)} { source -echo -verbose ../CMD/split_mesh.tcl }
	if {$mesh_split_flag>0} { open_mw_cel $var(design_name)_mesh_split }
	remove_ideal_network -all
	set_extraction_options -fan_out_threshold 100000
	extract_rc -coupling_cap
	report_net -verbose -physical [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]] > ./$icc_finalopt/report/$var(design_name).mesh_info
	report_net_physical [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]] > ./$icc_finalopt/report/$var(design_name).mesh_phsical
	set_extraction_options -fan_out_threshold 1000
	report_wire_caps ./$icc_finalopt/report/$var(design_name).wire_sum 1
}

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo $final_qor_summary >> ./$icc_finalopt/time.txt
echo $final_routing_quality >> ./$icc_finalopt/time.txt
echo [format "Diagnostics summary: %d error, %d warnings, %d informations." \
		[get_message_info -error_count] \
		[get_message_info -warning_count] \
		[get_message_info -info_count] \
		] >> ./$icc_finalopt/time.txt
echo $final_qor_summary
echo $final_routing_quality
##################################
###     Close && Quit        #####
##################################
close_mw_cel
close_mw_lib

set finish_time [clock seconds]
echo "-----------------------------------------------------" >> ./$icc_finalopt/time.txt
echo [format "ICC Total Run     :\t%d days, %s" [expr {[clock format [expr $finish_time - $start_time] -format %j -gmt true]-1}] \
	 [clock format [expr $finish_time - $start_time] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo "-----------------------------------------------------" >> ./$icc_finalopt/time.txt
echo "######\tICC Ends   : [date]" >> ./$icc_finalopt/time.txt
echo "-----------------------------------------------------" >> ./$icc_finalopt/time.txt

print_message_info

check_show_messages Error

if {$var(quit)} {exit}
