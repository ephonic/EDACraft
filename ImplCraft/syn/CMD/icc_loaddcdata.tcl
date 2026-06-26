########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
######	load DC database, support : DDC, Verilog/SDC/DEF, Milkyway
########################################################################################
if {$var(netlist2gds_flow)} {
	set var(dc2icc_datatype) 1
	set var(use_mcmm_flow)	false
}
###	import in design
if {$var(dc2icc_datatype)==0} {
	### load ddc
        puts [format "Script Info:: Loading Datatype : DDC : %s" $var(icc_load_dc_ddc)]
	read_ddc $var(icc_load_dc_ddc)
	#if {$designopt(spg) && [file isfile ./DC/out/$var(design_name).def]} {
	#	dict lappend nhp_predefine def_exists ./DC/out/$var(design_name).def
	#}
} elseif {$var(dc2icc_datatype)==1} {
	### load verilog/sdc/def
        puts [format "Script Info:: Loading Datatype : Verilog/SDC/DEF from ./DC/out"]
        read_verilog -bus_direction_for_undefined_cell connection \
			-cell $var(design_name) ./DC/out/$var(design_name).v
	remove_sdc
	if {$var(use_mcmm_flow)} {
		foreach each_mcmm_view [dict keys $lib_mcmm] {
			puts [format "Script Info:: Create scenario : %s" $each_mcmm_view]
			create_scenario $each_mcmm_view
                	set_operating_conditions [dict get $lib_common operating_conditions [dict get $lib_mcmm $each_mcmm_view corner]] \
                                	-analysis_type [dict get $lib_mcmm $each_mcmm_view analysis_type]
                	set_tlu_plus_files -max_tluplus [dict get $lib_common tlu [dict get $lib_mcmm $each_mcmm_view rctype]] \
					-tech2itf_map [dict get $nhp_predefine itfmap_file]
                	set_scenario_options -scenarios $each_mcmm_view \
                                	-setup [dict get $lib_mcmm $each_mcmm_view setup] \
                                	-hold [dict get $lib_mcmm $each_mcmm_view hold]
                	if {$designopt(power)} {
                        	set_scenario_options -scenarios $each_mcmm_view \
                                	-leakage_power [dict get $lib_mcmm $each_mcmm_view leakage_power] \
                                	-dynamic_power [dict get $lib_mcmm $each_mcmm_view dynamic_power]
                	}
        		read_sdc -echo ./DC/out/$var(design_name).$each_mcmm_view.sdc
		}
	} else {
		if {$var(netlist2gds_flow)} {
			if {[file isfile ./DC/out/$var(design_name).sdc]} {
				source -echo -verbose ./DC/out/$var(design_name).sdc
			} else {
		###	define default virtual clock
				set default_virtual_clock [lindex $var(ref_clock) 0]
				create_clock -name $default_virtual_clock -period [expr {[lindex $var(ref_clock) 1]*$var(dc_clock_factor)}]
		###	define real clock
                		if {[llength [dict keys $nhp_clockdefine]]>0} {
                        		foreach clock_name [dict keys $nhp_clockdefine] {
                                		set clock_port  [dict get $nhp_clockdefine $clock_name root]
						if {[sizeof_collection [get_ports -quiet $clock_port]]>0} {
							create_clock -name $clock_name -period [expr {[dict get $nhp_clockdefine $clock_name period]*$var(dc_clock_factor)}] [get_ports $clock_port]
							set_drive	0	[get_ports $clock_port]
						} elseif {[sizeof_collection [get_pins -quiet $clock_port]]>0} {
							create_clock -name $clock_name -period [expr {[dict get $nhp_clockdefine $clock_name period]*$var(dc_clock_factor)}] [get_pins $clock_port]
							set_drive	0	[get_pins $clock_port]
						} else {
							puts [format "Script %s:: clock root : %s is neither port nor pin, plz check it!" [string totitle error] $clock_port]
							exit
						}
                                		set_dont_touch_network          [get_clocks $clock_name]
                                		#set_ideal_network              [get_clocks $clock_name]
                                		set_clock_uncertainty -setup    [dict get $nhp_clockdefine $clock_name setup]   [get_clocks $clock_name]
                                		set_clock_uncertainty -hold     [dict get $nhp_clockdefine $clock_name hold]    [get_clocks $clock_name]
                                		set_clock_transition            [dict get $nhp_clockdefine $clock_name skew]    [get_clocks $clock_name]
					}
				}
		###	define input && output delay
				set all_inputs_without_clk	[remove_from_collection [all_inputs] \
									[filter_collection [get_attribute [get_clocks] sources] object_class==port] \
								]
				set_input_delay	-clock $default_virtual_clock -max [lindex $var(default_input_delay) 0]	$all_inputs_without_clk
				set_input_delay	-clock $default_virtual_clock -min [lindex $var(default_input_delay) 1]	$all_inputs_without_clk
				set_input_transition 0.1 $all_inputs_without_clk
				set_output_delay -clock $default_virtual_clock -max [lindex $var(default_output_delay) 0] [all_outputs]
				set_output_delay -clock $default_virtual_clock -min [lindex $var(default_output_delay) 1] [all_outputs]
		###	Defining the Driver Cell
				set local_driving_cell	[dict get $lib_define $main_lib_name function_cell driver_inv]
				set_driving_cell -no_design_rule -lib_cell [lindex $local_driving_cell 0] \
						-pin [lindex $local_driving_cell 2] $all_inputs_without_clk
		###	Defining the Load Attribute
				set_load [expr [load_of [get_lib_pins */[lindex $local_driving_cell 0]/[lindex $local_driving_cell 1]]] * 20]	[all_outputs]
		###	Defining ideal network
				if {[llength $var(ideal_sources)]>0} {
					set_ideal_network [get_ports $var(ideal_sources)]
				}
		###	set isolate ports
				set_isolate_ports [remove_from_collection [all_outputs] [all_inputs]]
				report_isolate_ports
		
		###	default path groups	
				group_path -name C-O -to [all_outputs]
				group_path -name D-L -from $all_inputs_without_clk
				group_path -name D-O -from $all_inputs_without_clk -to [all_outputs]
		###	define max transition && fanout	
				set_max_transition $var(max_tran_dc) [current_design]
				set_max_fanout $var(max_fanout)	[current_design]
				if {$var(critical_range)>0} {
					set_critical_range $var(critical_range) [current_design]
				}
			}
			if {!$var(netlist2gds_opt)} {
				set_dont_touch [get_nets]
				set_dont_touch [get_cells]
			}
		} else {
			if {[file isfile ./DC/out/$var(design_name).sdc]} {
				read_sdc ./DC/out/$var(design_name).sdc
			}
		}
		update_nhp_clockdefine
		#if {$designopt(spg) && [file isfile ./DC/out/$var(design_name).def]} {
		#	dict lappend nhp_predefine def_exists ./DC/out/$var(design_name).def
		#} else {
		#	set designopt(spg) false
		#}
	}
} elseif {$var(dc2icc_datatype)==2} {
	###	load milkyway
        puts [format "Script Info:: Loading Datatype : Milkway : cel(%s)" $var(icc_load_dc_mw)]
	copy_mw_cel -from_library $var(mw_lib_name,dc) -from $var(icc_load_dc_mw) \
			-to_library $var(mw_lib_name,icc) -to $var(icc_load_dc_mw) -overwrite
	open_mw_cel $var(icc_load_dc_mw)
	#if {$designopt(spg) && [file isfile ./DC/out/$var(design_name).def]} {
		#dict lappend nhp_predefine def_exists ./DC/out/$var(design_name).def
	#}
} else {
	puts [format "Script %s:: variable 'var(dc2icc_datatype)' must be one of [0, 1, 2], your setting : %s is wrong!" [string totitle error] $var(dc2icc_datatype)]
	exit
}

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	current_scenario $var(mcmm_default_view)
	foreach each_mcmm_view [dict keys $lib_mcmm] {
        	set_scenario_options -scenarios $each_mcmm_view \
                               	-setup [dict get $lib_mcmm $each_mcmm_view setup] \
                               	-hold [dict get $lib_mcmm $each_mcmm_view hold] \
				-cts_mode [dict get $lib_mcmm $each_mcmm_view cts]
		if {[dict get $lib_mcmm $each_mcmm_view cts]} {
			set_cts_scenario $each_mcmm_view
		}
                if {$designopt(power)} {
                       	set_scenario_options -scenarios $each_mcmm_view \
                               	-leakage_power [dict get $lib_mcmm $each_mcmm_view leakage_power] \
                               	-dynamic_power [dict get $lib_mcmm $each_mcmm_view dynamic_power]
                }
		if {$var(extend,groups)} { create_path_groups_between_clocks [get_clocks -quiet] }
	}
	
	set_active_scenarios [dict get $nhp_predefine actived_scenarios]
	
	report_scenario_options
	#set_preferred_scenario $var(mcmm_default_view)
	
	check_scenarios -output $icc_finalopt/report
	
	report_scenarios

	current_design $var(design_name)

	foreach each_active_scenario [all_active_scenarios] {
		if {![file isfile [dict get $lib_mcmm $each_active_scenario full_sdc]]} {
			current_scenario $each_active_scenario
			set_max_transition $var(max_tran_icc) [current_design]
		}
	}
	current_scenario $var(mcmm_default_view)
} else {
	if {![file isfile $var(sdc_full)]} { set_max_transition $var(max_tran_icc) [current_design] }
}	
	
current_design $var(design_name)

save_mw_cel -as $var(design_name)
close_mw_cel
open_mw_cel $var(design_name)
current_mw_cel
