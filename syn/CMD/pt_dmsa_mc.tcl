########################################################################################
######  DCICC FLOW - DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
set start_time [clock seconds]
if {![file isdirectory $var(pt,report_path)]} {
        file mkdir $var(pt,report_path)
}
if {![file isdirectory $var(pt,report_path)/report]} {
        file mkdir $var(pt,report_path)/report
}
if {![file isdirectory $var(pt,report_path)/out]} {
        file mkdir $var(pt,report_path)/out
}
echo "-----------------------------------------------------" > ./$var(pt,report_path)/time.txt
echo "######\tPT Start : [date]" >> ./$var(pt,report_path)/time.txt
echo "-----------------------------------------------------" >> ./$var(pt,report_path)/time.txt
########################################################################################
###	common setup
########################################################################################
puts [format "Script Info:: Running script \"runpt_dmsa_mc.tcl\" base on %s" $each_scenario]

set link_library	"* [dict get $nhp_corner_link [dict get $lib_mcmm $each_scenario corner]]"
puts [format "Script Info:: current link_library is   : %s" $link_library]

set hierarchy_separator                 /
set sh_source_uses_search_path          true
set report_default_significant_digits   3
set link_create_black_boxes             false
set timing_remove_clock_reconvergence_pessimism true
set timing_clock_reconvergence_pessimism same_transition
set timing_save_pin_arrival_and_slack	true
set timing_crpr_threshold_ps            1.0
set si_enable_analysis                  true
set model_validation_significant_digits 3
set power_enable_analysis               true
set power_clock_network_include_register_clock_pin_power false
set read_parasitics_load_locations      true
set delay_calc_waveform_analysis_mode	full_design

set si_xtalk_double_switching_mode	clock_network
if {$var(use_aocvm)} {
set timing_aocvm_enable_analysis true
set timing_aocvm_analysis_mode  $var(aocvm_analysis_mode)
}

set cur_tlu_file	[file tail [dict get $lib_common tlu [dict get $lib_mcmm $each_scenario rctype]]]
regexp -- {v(n?\d+)c} [dict get $lib_mcmm $each_scenario corner] match cur_temp
regsub -- {n} $cur_temp - cur_temp

set dmsa_local_file_verilog	../../$var(pt,dmsa,icc_path)/out/$var(design_name).v
set dmsa_local_file_sdc		../../$var(pt,dmsa,icc_path)/out/${var(design_name)}.${each_scenario}.sdc
set dmsa_local_file_spf		../../$var(pt,dmsa,icc_path)/out/${cur_tlu_file}_${cur_temp}.$var(design_name).spef

if {[file isfile [string trim $var(pt,dmsa,custom_verilog)]]} { set dmsa_local_file_verilog [string trim $var(pt,dmsa,custom_verilog)] } 
if {[dict exists $lib_mcmm $each_scenario pt_custom_sdc] && [file isfile [string trim [dict get $lib_mcmm $each_scenario pt_custom_sdc]]]} {
	set dmsa_local_file_sdc [string trim [dict get $lib_mcmm $each_scenario pt_custom_sdc]]
}
if {[dict exists $lib_mcmm $each_scenario pt_custom_spf] && [file isfile [string trim [dict get $lib_mcmm $each_scenario pt_custom_spf]]]} {
	set dmsa_local_file_spf		[string trim [dict get $lib_mcmm $each_scenario pt_custom_spf]]
}

puts [format "Script Info:: Load verilog file : %s" $dmsa_local_file_verilog]
read_verilog $dmsa_local_file_verilog
link_design $var(design_name)
###	define dont use
foreach mvt_one $final_lib_list {
	###	dont use 
	if {[dict exists $lib_define $mvt_one dontuse]} {
                puts "Script Info:: Set dontuse cells in lib ($mvt_one) for PrimeTime"
                source [dict get $lib_define $mvt_one dontuse icc_list]
		foreach dontuse_one [set [dict get $lib_define $mvt_one dontuse param_define]] {
                        append_to_collection -unique dont_use_cell_list [get_lib_cell -regexp "[dict get $lib_define $mvt_one lib_title]/[regsub -all -- {\*} $dontuse_one .*]"]
                }
        }
	if {$var(insert,eco) && [string equal $mvt_one $eco_ref_lib] && ![string equal $mvt_one $eco_lib_name]} {
		append_to_collection -unique dont_use_cell_list [get_lib_cell -regexp [dict get $lib_define $eco_lib_name lib_title]/.*]
	}
	###	mark threshold voltage group
	set_user_attribute [get_libs -regexp [dict get $lib_define $mvt_one lib_title]] \
			default_threshold_voltage_group $mvt_one
}
if {$var(insert,eco) && $eco_ref_lib ni $final_lib_list} {
	append_to_collection -unique dont_use_cell_list [get_lib_cell -regexp [dict get $lib_define $eco_ref_lib lib_title]/.*]
	append_to_collection -unique dont_use_cell_list [get_lib_cell -regexp [dict get $lib_define $eco_lib_name lib_title]/.*]
}
if {[llength $var(custom_set_dontuse)]>0} {
        foreach one_cus_dontuse $var(custom_set_dontuse) {
                puts [format "Script Info:: Set custom dontuse cell : %s" $one_cus_dontuse]
                append_to_collection -unique dont_use_cell_list [get_lib_cells */$one_cus_dontuse]
        }
}
if {[llength $var(custom_remove_dontuse)]>0} {
        foreach one_cus_release $var(custom_remove_dontuse) {
                puts [format "Script Info:: Remove dontuse attributes from specified cell : %s" $one_cus_release]
		set dont_use_cell_list [remove_from_collection $dont_use_cell_list [get_lib_cells */$one_cus_release]]
        }
}
set_dont_use $dont_use_cell_list

puts [format "Script Info:: Load SDC file : %s" $dmsa_local_file_sdc]
read_sdc $dmsa_local_file_sdc
report_clock
remove_capacitance [get_nets -hierarchical]
remove_resistance [get_nets -hierarchical]

set_timing_derate $var(timing_derate_max) -late
set_timing_derate $var(timing_derate_min) -early


if {[file isfile $dmsa_local_file_spf]} {
	set cur_spf_type [get_spf_type $dmsa_local_file_spf]
	puts [format "Script Info:: Load SPF(%s) file : %s" $cur_spf_type $dmsa_local_file_spf]
	read_parasitics -format $cur_spf_type -complete_with zero -keep_capacitive_coupling $dmsa_local_file_spf
}
if {$var(use_aocvm)} {
	set current_scenario_corner     [dict get $lib_mcmm $each_scenario corner]
	foreach mvt_one $final_lib_list {
        	if {[dict exists $lib_define $mvt_one aocv $current_scenario_corner]} {
                        read_aocvm [dict get $lib_define $mvt_one aocv $current_scenario_corner]
        	}
	}
}
check_timing
update_timing
if {[string equal $cur_spf_type dspf]} {
	pt_remove_cell_prefix_X
	write_changes -reset
}
