########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	signoff drc && autofix
########################################################################################
open_mw_cel $var(design_name)
set phase_start [clock seconds]
set phase_name  "try_signoff_drc"
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -create_ports top
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

###     setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

current_mw_cel

set var(icv,signoff_autofix_drc) true

###     in-design signoff drc && auto fix.
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
