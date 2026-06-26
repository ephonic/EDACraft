########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	common setup
########################################################################################
echo "-----------------------------------------------------" > ./$icc_finalopt/time.txt
echo "######\tICC Start : [date]" >> ./$icc_finalopt/time.txt
echo [format "######\tVersion   : %s" $product_version] >> ./$icc_finalopt/time.txt
echo "-----------------------------------------------------" >> ./$icc_finalopt/time.txt
########################################################################################
###	s01 init design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s01_init_design"
show_current_status $phase_name

###	load dc database
source -echo -verbose ../CMD/icc_loaddcdata.tcl

if {$var(dc_clock_factor)!=1 && $var(clock_recover_phase)=="s01"} { recover_clock_period }

###	initialize or load floorplan
source -echo -verbose ../CMD/icc_floorplan.tcl

###     define clock region if needed
if {![expr {$var(dc2icc_datatype)==1 && $designopt(spg)}]} {
foreach one_clock [dict keys $nhp_clockdefine] {
	if {[llength [dict get $nhp_clockdefine $one_clock region]]>0} {
		create_bounds -name CLOCK_MOVE_REGION_$one_clock \
			-type hard \
			-coordinate [dict get $nhp_clockdefine $one_clock region] \
			[get_flat_cells -of_objects [get_nets -segments -of_objects [get_attribute [get_clocks $one_clock] sources]]]
	} else {
		if {$var(automesh_region)!=off && [dict get $nhp_clockdefine $one_clock is_mesh]} {
			create_bounds -name CLOCK_AUTOMESH_REGION_$one_clock \
				-effort $var(automesh_region) \
				[get_flat_cells -of_objects [get_nets -segments -of_objects [get_attribute [get_clocks $one_clock] sources]]]
		}
	}
}
}
###	create gater placement blockage if needed
if {[info exists clock_gater_area]} {
	set index_gater_area 0
        foreach each_area $clock_gater_area {
                if {[llength $each_area]==4} {
                        set CMD_GATER_AREA_PB "create_placement_blockage -bbox {$each_area} -type hard"
                        set CMD_GATER_AREA_RG "create_route_guide -name GATER_ROUTE_GUIDE_$index_gater_area \
				-coordinate {$each_area} -no_signal_layers {[dict get $lib_common metal_layers all]}"
                        echo $CMD_GATER_AREA_PB
                        echo $CMD_GATER_AREA_RG
                        eval $CMD_GATER_AREA_PB
                        eval $CMD_GATER_AREA_RG
			incr index_gater_area 1
                } elseif {[llength $each_area]==5} {
                        set cur_coor    [lrange $each_area 0 3]
                        set CMD_GATER_AREA_PB "create_placement_blockage -bbox {$cur_coor} -type hard"
                        echo $CMD_GATER_AREA_PB
                        eval $CMD_GATER_AREA_PB
                        foreach one_bdmetal [lindex $each_area 4] {
                                set CMD_GATER_AREA_RG "create_route_guide -name GATER_ROUTE_GUIDE_$index_gater_area -coordinate {$cur_coor}"
                                if {[llength $one_bdmetal]>1} {
					set CMD_GATER_AREA_RG [concat $CMD_GATER_AREA_RG "-track_utilization_layers {[lrange $one_bdmetal 0 end-1]}"]
                                        set CMD_GATER_AREA_RG [concat $CMD_GATER_AREA_RG "-horizontal_track_utilization [lindex $one_bdmetal end]"]
                                        set CMD_GATER_AREA_RG [concat $CMD_GATER_AREA_RG "-vertical_track_utilization [lindex $one_bdmetal end]"]
                                } else {
					set CMD_GATER_AREA_RG [concat $CMD_GATER_AREA_RG "-no_signal_layers [lindex $one_bdmetal 0]"]
				}
                                echo $CMD_GATER_AREA_RG
                                eval $CMD_GATER_AREA_RG
				incr index_gater_area 1
                        }
                } else {
                        puts [format "Script %s:: wrong clock_gater_area defined : %s, skip!" [string totitle error] $each_area]
                }
        }
}

###	create user-shapes for global obs!
if {[file isfile $var(obs)]} {
	source -echo -verbose $var(obs)
}

if {$designopt(power)} {
        #set_power_prediction    true
}

report_all ./$icc_finalopt/report $phase_name

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary] >> ./$icc_finalopt/time.txt
########################################################################################
###	s02 placeopt design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s02_place_opt"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {$var(dc_clock_factor)!=1 && $var(clock_recover_phase)=="s02"} { recover_clock_period }
###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
#if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

###	define antenna rule
#if {[file isfile [dict get $lib_common ant_rule]]} {
#	source -echo -verbose [dict get $lib_common ant_rule]
#}

###	add diode protection for all inputs (except clock pins)
for {set i 0} {$i<$var(input,diode)} {incr i 1} {
	insert_port_protection_diodes 	-ignore_dont_touch -diode_cell [get_lib_cells *[dict get $nhp_predefine default_corner]*/[dict get $nhp_predefine antenna_cell]] \
					-port [remove_from_collection [all_inputs] \
						[filter_collection [get_attribute [get_clocks] sources] object_class==port]]
	report_port_protection_diodes
}

###	add addtional icc constraints
if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	foreach each_active_scenario [all_active_scenarios] {
		if {[file isfile [dict get $lib_mcmm $each_active_scenario icc_sdc]]} {
			current_scenario $each_active_scenario
			source -echo -verbose [dict get $lib_mcmm $each_active_scenario icc_sdc]
		}
	}
        set_active_scenarios [dict get $nhp_predefine actived_scenarios]
        current_scenario $var(mcmm_default_view)
} else {
	if {[file isfile $var(sdc_icc)]} { source -echo -verbose $var(sdc_icc) }
}

###	insert spare if needed
if {$var(insert,spare)} {
	#source -echo -verbose ../CMD/add_spare.tcl
	set total_cell_nums [sizeof_collection [get_cells -hierarchical -filter {is_hierarchical==false}]]

	###	insert all spare cells
	foreach one_spare [dict get $lib_define $main_lib_name spare] {
		lassign $one_spare cur_spare_cell cur_spare_ratio cur_spare_multiple cur_spare_tie_net($cur_spare_cell)
		set cur_ins_num		[expr {int($total_cell_nums*$cur_spare_ratio*$cur_spare_multiple)}]
		insert_spare_cells -lib_cell $cur_spare_cell -num_instances $cur_ins_num -cell_name spare_$cur_spare_cell -skip_legal
	}

	###	tie input pins
	foreach_in_collection one [get_pins spare_*/* -filter {direction == in}] {
		disconnect_net [get_nets -of_object $one] $one
		connect_net $cur_spare_tie_net([get_attribute [get_cells -of_object $one] ref_name]) $one
	}
}

###	
if {!$designopt(spg) && [llength $var(insert_port_buffer)]>0} {
        foreach one_port_buffer_pair $var(insert_port_buffer) {
                if {[llength $one_port_buffer_pair]>=2} {
                        puts [format "Script Info:: mark port %s as dont_touch" [lindex $one_port_buffer_pair 0]]
			if {[string equal [lindex $one_port_buffer_pair 0] ALL_INPUTS]} {
				set all_inputs_without_clk      [remove_from_collection [all_inputs] \
                                                               	[filter_collection [get_attribute [get_clocks] sources] object_class==port] \
                                                               	]
                        	set_dont_touch $all_inputs_without_clk
			} elseif {[string equal [lindex $one_port_buffer_pair 0] ALL_OUTPUTS]} {
                        	set_dont_touch [all_outputs]
			} else {
                        	set_dont_touch [get_ports [subst [lindex $one_port_buffer_pair 0]]]
			}
                } else {
                        puts [format "Script %s:: syntax error(insert_port_buffer), skip : %s" [string totitle error] $one_port_buffer_pair]
                }
        }
        foreach one_port_buffer_pair $var(insert_port_buffer) {
		if {[string equal [lindex $one_port_buffer_pair 0] ALL_INPUTS]} {
			set magneted_ports $all_inputs_without_clk
		} elseif {[string equal [lindex $one_port_buffer_pair 0] ALL_OUTPUTS]} {
			set magneted_ports [all_outputs]
		} else {
			set magneted_ports [get_ports [subst [lindex $one_port_buffer_pair 0]]]
		}
                if {[llength $one_port_buffer_pair]>2} {
			if {$var(mark_magnet_fixed)} {
				magnet_placement -mark_fixed -move_fixed \
					-logical_level [lindex $one_port_buffer_pair 2] \
					-stop_by_sequential_cells $magneted_ports
			} else {
				magnet_placement -move_fixed \
					-logical_level [lindex $one_port_buffer_pair 2] \
					-stop_by_sequential_cells $magneted_ports
			}
                }
        }
}
if {[file isfile $var(netNDR,constraints)]} {
        source -echo -verbose $var(netNDR,constraints)
}
set_app_var compile_instance_name_prefix ICC_PLACE_OPT
###	do pre-place opt	################################################
if {$designopt(spg)} {
	#remove_bounds -all
	set_app_var spg_enable_ascii_flow true
} else {
	show_current_status "$phase_name : create_placement"
	# Do an initial placement of the design first
	set CMD_PRE_PLACE "create_placement"
	if {$designopt(cong)} { lappend CMD_PRE_PLACE -congestion }
	echo $CMD_PRE_PLACE
	eval $CMD_PRE_PLACE
	legalize_placement

	# Place the design first
	set CMD_PRE_PLACE "create_placement -direct_timing -effort high"
	#set CMD_PRE_PLACE "create_placement -timing_driven -effort high"

	if {$designopt(cong)} { lappend CMD_PRE_PLACE -congestion }
	echo $CMD_PRE_PLACE
	eval $CMD_PRE_PLACE
	legalize_placement
	create_buffer_tree
}
###	do place opt	########################################################
show_current_status "$phase_name : place_opt"
set CMD_PLACE_OPT	"place_opt -area_recovery -effort high"
if {$designopt(spg)}	{ 
	lappend CMD_PLACE_OPT	-spg 
	if {!$designopt(cong)}	{ lappend CMD_PLACE_OPT -congestion }
} else {
	lappend CMD_PLACE_OPT	-skip_initial_placement
}
if {$designopt(power)}	{ lappend CMD_PLACE_OPT -power }
if {$designopt(cong)}	{ lappend CMD_PLACE_OPT -congestion }
#if {$designopt(timing)}	{ lappend CMD_PLACE_OPT "-effort high" }
echo $CMD_PLACE_OPT
eval $CMD_PLACE_OPT

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
	report_power -scenarios [all_active_scenarios ]
} else {
	report_power
}

if {$var(insert,spare)} {
	connect_tie_cells -objects [get_pins * -filter "net_name == VDD || net_name == VSS"] -obj_type port_inst \
			-tie_high_lib_cell [dict get $lib_define $main_lib_name function_cell tie1] \
			-tie_low_lib_cell [dict get $lib_define $main_lib_name function_cell tie0]
}
###	do post-place opt	################################################
#if {$designopt(spg)} {
	#if {$designopt(autobound)} {remove_bounds AUTO_BOUND*}
	#remove_bounds -all
#}
if {!$designopt(fast_mode)} {
	save_mw_cel -as tmp_running
	check_placement_legality ./$icc_finalopt/report/${phase_name}.legality
	extract_rc
	update_timing
	echo [get_qor_summary 2] >> ./$icc_finalopt/report/place_opt.txt
	if {$designopt(autoweight)} { my_proc_auto_weights }
	show_current_status "$phase_name : preroute_focal_opt"
	set_preroute_focal_opt_strategy -min_layer_name $var(bottom_layer) -max_layer_name $var(top_layer) -congestion_effort medium
	report_preroute_focal_opt_strategy
	if {$designopt(auto_ndr_rule)} {
		set_preroute_focal_opt_strategy -congestion_effort high
		preroute_focal_opt -auto_routing_rule
	}
	preroute_focal_opt -layer_optimization
	#preroute_focal_opt -size_only_mode in_place -setup_endpoints all -effort $var(preroute_focal_opt)
	#preroute_focal_opt -size_only_mode in_place -hold_endpoints all -effort $var(preroute_focal_opt)
	#set_fix_hold [get_clocks] 
	extract_rc
	update_timing
	set_app_var compile_instance_name_prefix ICC_PSYNOPT
	show_current_status "$phase_name : psynopt"
	set CMD_PSYNOPT "psynopt -area_recovery -refine_critical_paths 10000"
	if {$designopt(power)}	{ lappend CMD_PSYNOPT -power }
	if {$designopt(cong)}	{ lappend CMD_PSYNOPT -congestion }
	echo $CMD_PSYNOPT
	eval $CMD_PSYNOPT
	if {$designopt(autoweight)} { my_proc_auto_weights }
}

extract_rc
update_timing
report_placement_utilization 

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

set_app_var compile_instance_name_prefix U

verify_pg_nets -error_cell PG_CHECK_S02 > ./$icc_finalopt/report/verify_pg_nets.s02.rpt
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
	check_finfet_grid > ./$icc_finalopt/report/check_finfet_grid.s02.rpt
}

report_all ./$icc_finalopt/report $phase_name

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)

report_congestion -grc_based -by_layer -routing_stage global
report_congestion -grc_based -by_layer -routing_stage global -from_saved_congestion_map > ./$icc_finalopt/report/${phase_name}.congestion
check_zrt_routability -check_out_of_boundary false > ./$icc_finalopt/report/${phase_name}.routability

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary 2] >> ./$icc_finalopt/time.txt
########################################################################################
###	s03 clockopt design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s03_clock_opt"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {$var(dc_clock_factor)!=1 && $var(clock_recover_phase)=="s03"} { recover_clock_period }
###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        set_active_scenarios [dict get $nhp_predefine actived_scenarios]
        current_scenario $var(mcmm_default_view)
}

if {$designopt(autoweight)} { my_proc_auto_weights }
###	do MESH CLOCK DESIGN
set clocklist_mesh	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
set clocklist_cts	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
if {[llength $clocklist_mesh]>0} {
	puts "Script Info:: Performing NHP Mesh Clock Synthesis"
	set_ideal_network -no_propagate [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]]
        source -echo -verbose ../CMD/mesh.tcl

	#remove_ideal_network -all
	#set_extraction_options -fan_out_threshold 100000
	#extract_rc -coupling_cap
	#report_net -verbose -physical [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]] > ./$icc_finalopt/report/$var(design_name).mesh_info
	#report_net_physical [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]] > ./$icc_finalopt/report/$var(design_name).mesh_phsical
	#set_extraction_options -fan_out_threshold 1000
}

###	do CTS CLOCK DESIGN
if {[llength $clocklist_cts]>0} {
	# update IO clock latency
	if {[info exists clocklist_cts]} {
		if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        		foreach each_active_scenario [all_active_scenarios] {
        			current_scenario $each_active_scenario
                		foreach one_clock $clocklist_cts {
                        		if {[sizeof_collection [get_clocks -quiet $one_clock]]>0 && [sizeof_collection [get_clocks -quiet ref_$one_clock]]>0} {
						set_latency_adjustment_options -from_clock ${one_clock} -to_clock ref_$one_clock
                        		}
                		}
        		}
        		current_scenario $var(mcmm_default_view)
		} else {
                	foreach one_clock $clocklist_cts {
                       		if {[sizeof_collection [get_clocks -quiet $one_clock]]>0 && [sizeof_collection [get_clocks -quiet ref_$one_clock]]>0} {
					set_latency_adjustment_options -from_clock ${one_clock} -to_clock ref_$one_clock
                       		}
                	}
		}
	}
	if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} {
		source -echo -verbose $setting(clock)
	}
	if {$designopt(icg_replication) && [get_clock_gating_cell_nums]>0} {
		split_clock_net -objects [get_flat_cells -filter {clock_gating_logic==true}] -gate_sizing -gate_relocation -split_intermediate_level_clock_gates
	}
	set_app_var compile_instance_name_prefix ICC_CLOCK_OPT
	if {[llength $clocklist_mesh]>0} { mark_clock_tree -clock_synthesized -clock_trees $clocklist_mesh }
	if {$designopt(ccdopt) && [llength $clocklist_mesh]==0} {
		puts "Script Info:: Performing Concurrent Clock and Data Optimization"
        	source -echo -verbose ../CMD/ccdopt.tcl
	} else {
		set designopt(ccdopt)	false
		puts "Script Info:: Performing Traditional Clock Tree Synthesis"
        	source -echo -verbose ../CMD/cts.tcl
	}
	set_propagated_clock [get_clocks $clocklist_cts]
	if {[llength $clocklist_mesh]>0} {
		set_ideal_network -no_propagate [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]]
	}
	set_app_var compile_instance_name_prefix U
}

set_fix_hold [all_clocks]

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

report_all ./$icc_finalopt/report $phase_name

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary 2] >> ./$icc_finalopt/time.txt
check_placement_legality ./$icc_finalopt/report/${phase_name}.legality
########################################################################################
###	s04 routeopt design
########################################################################################
set phase_start [clock seconds]
set phase_name	"s04_route_opt"
show_current_status $phase_name
check_change_current_cel $var(design_name)
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {$var(dc_clock_factor)!=1 && $var(clock_recover_phase)=="s04"} { recover_clock_period }
###	setting design variables
if {[check_load_setting $setting(design) sl_design]} {source -echo -verbose $setting(design)}
if {[check_load_setting $setting(clock) sl_clock] && [dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} { source -echo -verbose $setting(clock) }
if {[check_load_setting $setting(route) sl_route]} {source -echo -verbose $setting(route)}

if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]] && $designopt(high_resistance)} {
	puts [format "Script Info:: High Resistance Optimization : %s" $designopt(high_resistance)]
	set_optimization_strategy -high_resistance true
}

set_app_var compile_instance_name_prefix ICC_ROUTE_OPT

if {$var(use_mcmm_flow) && [all_scenarios]!={}} {
        set_active_scenarios [dict get $nhp_predefine actived_scenarios]
        current_scenario $var(mcmm_default_view)
}

if {$designopt(autoweight)} { my_proc_auto_weights }
if {[file isfile $var(route,constraints)]} {
	source -echo -verbose $var(route,constraints)
}
report_preferred_routing_direction
###	To enable concurrent redundant via insertion for 1st initial route
if {$designopt(optimize_vias)} {
	set_route_zrt_common_options -concurrent_redundant_via_mode reserve_space
	set_route_zrt_common_options -eco_route_concurrent_redundant_via_mode reserve_space
}
###	route critical nets
if {$designopt(zrt_crt_prior)} {
	set zrt_timing_paths [get_timing_paths -slack_lesser_than $var(zrt_crt_slack) -nworst 5 -max_paths 10000000]
	if {[sizeof_collection $zrt_timing_paths]>0} {
		show_current_status "$phase_name : route_zrt_group zrt nets"
		puts "Script Info:: Route critical nets first!"
		route_zrt_group -nets [get_nets -of_objects [get_attribute [get_attribute $zrt_timing_paths points] object]]
	}
}
###	Route first the design 
show_current_status "$phase_name : route_opt -initial_route_only"
route_opt -initial_route_only
###	double vias
if {$designopt(optimize_vias)} {
	show_current_status "$phase_name : insert_zrt_redundant_vias"
	if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_insert_dfmvia] &&
		[file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_dfmvia]]} {
		source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_dfmvia]
	} else {
		insert_zrt_redundant_vias
	}
	set_route_zrt_common_options -concurrent_redundant_via_mode off
	set_route_zrt_common_options -eco_route_concurrent_redundant_via_mode off
}

update_clock_latency
###	optimize clock trees
set clocklist_mesh	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
set clocklist_cts	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
if {[llength $clocklist_cts]>0 && !$designopt(ccdopt)} {
	show_current_status "$phase_name : optimize_clock_tree (1st)"
	optimize_clock_tree -clock_trees $clocklist_cts -routed_clock_stage detail_with_signal_routes
	if {[llength $clocklist_mesh]>0} {
		set_ideal_network -no_propagate [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]]
	}
}

update_timing

###	route_opt core command
#show_current_status "$phase_name : route_opt -skip_initial_route"				; # changed by 15.06
#set CMD_ROUTE_OPT_1	"route_opt -skip_initial_route -effort high -xtalk_reduction"		; # changed by 15.06
show_current_status "$phase_name : route_opt -incremental"
set CMD_ROUTE_OPT_1	"route_opt -incremental -effort medium -area_recovery"
if {$designopt(power)}	{ lappend CMD_ROUTE_OPT_1 -power }
echo $CMD_ROUTE_OPT_1
eval $CMD_ROUTE_OPT_1

save_mw_cel -as tmp_running

## Generate shieldign wires for clocks (if not done in clock_opt_route_icc step) or selected signal nets
if {[llength $clocklist_cts]>0} {
	set_route_zrt_common_options -reshield_modified_nets reshield
	show_current_status "$phase_name : create_zrt_shield"
	if {[llength $clocklist_mesh]>0} {
        	create_zrt_shield -preferred_direction_only true -with_ground $var(ground_net) \
                	-nets [get_nets -filter "var_route_rule!=default" -segments -of_objects [all_fanout -flat -from [get_attribute [get_clocks $clocklist_cts] sources]]]
	} else {
        	create_zrt_shield -preferred_direction_only true -with_ground $var(ground_net)
	}
	set_extraction_options -virtual_shield_extraction false
}

if {$designopt(autoweight)} { my_proc_auto_weights }

show_current_status "$phase_name : route_opt -incremental (1st)"
set_app_var routeopt_enable_aggressive_optimization true
set CMD_ROUTE_OPT_INCR	"route_opt -incremental -xtalk_reduction"
if {$designopt(ccdopt) && [llength $clocklist_mesh]==0} {
	lappend CMD_ROUTE_OPT_INCR -concurrent_clock_and_data
}
## Improving QoR after the default route_opt run : 
if {$designopt(power)} {
	# First turn on power-aware optimization
	#set_route_opt_strategy -power_aware_optimization true		; # changed by 15.06
	# Then run route_opt in incremental mode, optimize power
	#lappend CMD_ROUTE_OPT_INCR -power				; # changed by 15.06
}
echo $CMD_ROUTE_OPT_INCR
eval $CMD_ROUTE_OPT_INCR

# Then run route_opt in incremental mode, optimize xtalk
#show_current_status "$phase_name : route_opt -incremental(2nd)"		; # changed by 15.06
#if {!$designopt(fast_mode)} {route_opt -incremental -only_xtalk_reduction }	; # changed by 15.06

update_clock_latency
###	re-optimize clock tree
set clocklist_mesh	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
set clocklist_cts	[dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
if {[llength $clocklist_cts]>0 && !$designopt(ccdopt)} {
	show_current_status "$phase_name : optimize_clock_tree (2nd)"
	optimize_clock_tree -clock_trees $clocklist_cts -routed_clock_stage detail_with_signal_routes
	if {[llength $clocklist_mesh]>0} {
		set_ideal_network -no_propagate [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]]
	}
}
if {$designopt(autoweight)} { my_proc_auto_weights }

if {!$designopt(fast_mode)} {
	###	final incremental opt
	set_app_var routeopt_restrict_tns_to_size_only true
	set_app_var routeopt_allow_min_buffer_with_size_only true
	#set CMD_ROUTE_OPT_2 "route_opt -incremental -size_only -effort high -area -power"
	set CMD_ROUTE_OPT_2 "route_opt -incremental"				; # changed by 15.06
	echo $CMD_ROUTE_OPT_2
	#show_current_status "$phase_name : route_opt -incremental (3rd)"	; # changed by 15.06
	show_current_status "$phase_name : route_opt -incremental (2nd)"
	eval $CMD_ROUTE_OPT_2
	#show_current_status "$phase_name : route_opt -incremental (4th)"	; # changed by 15.06
	#eval $CMD_ROUTE_OPT_2							; # changed by 15.06
}

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

set_app_var compile_instance_name_prefix U

report_all ./$icc_finalopt/report $phase_name

if {[dict size [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]>0} {
	echo [format "########## s04 : %s" $phase_name] >> ./$icc_finalopt/report/CTS_monitor.rpt
	report_clock_tree_summary_to_file ./$icc_finalopt/report/CTS_monitor.rpt
}

set library_strategy [join [lsort $var(libs)] _]
if {[llength $var(libs_finalopt)]>0} {
        set library_strategy ${library_strategy}_opt_[join [lsort $var(libs_finalopt)] _]
}
set library_last_used [join [lsort [array name all_lib_list]] _]

define_user_attribute -class {mw_cel} -type string library_strategy
define_user_attribute -class {mw_cel} -type string library_last_used

set_attribute [current_mw_cel] library_strategy $library_strategy
set_attribute [current_mw_cel] library_last_used $library_last_used

report_attributes -app [current_mw_cel]

save_mw_cel -as $phase_name
save_mw_cel

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]] >> ./$icc_finalopt/time.txt
echo [get_qor_summary 3] >> ./$icc_finalopt/time.txt
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
