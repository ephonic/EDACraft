##################################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	internal procedure files
######	Owner : Anonymous , YaoXin
##################################################################################################
##################################################################################################
###	open file
##################################################################################################
proc open_f {file {access r} {permission 0666}} {
        if [catch {open $file $access $permission} fileId] {
                error $fileId
        } else {
                return $fileId
        }
}
##################################################################################################
###	auto detect spf format.
##################################################################################################
proc get_spf_type {file} {
	set fileId [open_f [string trim $file] r]
	set loop_flag 0
	set return_type unrecognized
	while {[gets $fileId line]} {
		if {[regexp -nocase -- {spef} $line]} {
			set return_type spef
			break
		}
		if {[regexp -nocase -- {dspf} $line]} {
			set return_type dspf
			break
		}
		incr loop_flag 1
		if {$loop_flag>10} { break }
	}
	close $fileId
	return $return_type
}
##################################################################################################
###	change cell name from : Xinstance => instance ...
##################################################################################################
proc pt_remove_cell_prefix_X {} {
	foreach one [get_object_name [get_cells -hierarchical]] {
		regsub -- {^X} $one "" new_name
		rename_cell $one $new_name
	}
}
##################################################################################################
###	get file content from file
##################################################################################################
proc read_from_file {file} {
	set fileId [open_f [string trim $file] r]
	set list_content [read $fileId]
	close $fileId
	return $list_content
}
##################################################################################################
###	update clock definition
##################################################################################################
proc update_nhp_clockdefine {{rebuild 0}} {
	upvar #0 nhp_clockdefine clockdefine
	upvar #0 var		l_var
	upvar #0 clock		l_clock
	upvar #0 clock_pin	l_clock_pin
	upvar #0 synopsys_program_name	p_name
	if {$rebuild>0} {
		unset -nocomplain clockdefine
	}
	if {![info exists clockdefine]} {
		set clockdefine {}
	}
	foreach one_clock [array name l_clock] {
		if {![dict exists $clockdefine $one_clock root]} {
			if {[info exists l_clock_pin($one_clock)]} {
				dict set clockdefine $one_clock root	$l_clock_pin($one_clock)
			} else {
				dict set clockdefine $one_clock root	$one_clock
			}
		}
		if {![dict exists $clockdefine $one_clock period]} {
			dict set clockdefine $one_clock period	[lindex $l_clock($one_clock) 0]
		}
		if {![dict exists $clockdefine $one_clock setup]} {
			dict set clockdefine $one_clock setup	[lindex $l_clock($one_clock) 1]
		}
		if {![dict exists $clockdefine $one_clock hold]} {
			dict set clockdefine $one_clock hold	[lindex $l_clock($one_clock) 2]
		}
		if {![dict exists $clockdefine $one_clock skew]} {
			dict set clockdefine $one_clock skew	[lindex $l_clock($one_clock) 3]
		}
		if {![dict exists $clockdefine $one_clock metal]} {
			dict set clockdefine $one_clock metal	[lindex $l_clock($one_clock) 4]
		}
		if {![dict exists $clockdefine $one_clock type]} {
			dict set clockdefine $one_clock type	[lindex $l_clock($one_clock) 5]
		}
		if {[string equal -nocase [lindex $l_clock($one_clock) 5] MESH]} {
			dict set clockdefine $one_clock is_mesh 1
			dict set clockdefine $one_clock is_cts  0
		} elseif {[string equal -nocase [lindex $l_clock($one_clock) 5] CTS]} {
			dict set clockdefine $one_clock is_mesh 0
			dict set clockdefine $one_clock is_cts  1
		} else {
			puts [format "Script %s:: clock type : not support %s, only support MESH or CTS" [string totitle error] [lindex $l_clock($one_clock) 5]]
			exit;
		}
		if {![dict exists $clockdefine $one_clock region]} {
			dict set clockdefine $one_clock region	[lindex $l_clock($one_clock) 6]
		}
	}
	if {![info exists clockdefine]} {
		set clockdefine {}
	}
	foreach_in_collection one_clocked [get_clocks -quiet] {
		if {[sizeof_collection [get_attribute -quiet $one_clocked sources]]>0} {
			set cur_clocked_name	[get_attribute $one_clocked name]
			if {![dict exists $clockdefine $cur_clocked_name]} {
				dict set clockdefine $cur_clocked_name type CTS
				puts [format "Script Info:: Auto update clock info(%s) : type : %s" $cur_clocked_name CTS]
			}
			if {![dict exists $clockdefine $cur_clocked_name root]} {
				dict set clockdefine $cur_clocked_name root	[get_attribute [get_attribute $one_clocked sources] full_name]
				puts [format "Script Info:: Auto update clock info(%s) : root 1 : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name root]]
			} else {
				if {![string equal [dict get $clockdefine $cur_clocked_name root] [get_attribute [get_attribute $one_clocked sources] full_name]]} {
					dict set clockdefine $cur_clocked_name root	[get_attribute [get_attribute $one_clocked sources] full_name]
					puts [format "Script Info:: Auto update clock info(%s) : root 2 : %s" $cur_clocked_name \
						[dict get $clockdefine $cur_clocked_name root]]
				}
			}
			if {![dict exists $clockdefine $cur_clocked_name period] || [dict get $clockdefine $cur_clocked_name period]!=[get_attribute $one_clocked period]} {
				dict set clockdefine $cur_clocked_name period [get_attribute -quiet $one_clocked period]
				puts [format "Script Info:: Auto update clock info(%s) : period : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name period]]
			}
			if {![dict exists $clockdefine $cur_clocked_name setup] || [dict get $clockdefine $cur_clocked_name setup]!=[get_attribute -quiet $one_clocked setup_uncertainty]} {
				dict set clockdefine $cur_clocked_name setup [get_attribute -quiet $one_clocked setup_uncertainty]
				puts [format "Script Info:: Auto update clock info(%s) : setup : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name setup]]
			}
			if {![dict exists $clockdefine $cur_clocked_name hold] || [dict get $clockdefine $cur_clocked_name hold]!=[get_attribute -quiet $one_clocked hold_uncertainty]} {
				dict set clockdefine $cur_clocked_name hold [get_attribute -quiet $one_clocked hold_uncertainty]
				puts [format "Script Info:: Auto update clock info(%s) : hold : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name hold]]
			}
			set key_attribute_clock_transition clock_transition_rise_max
			if {$p_name=="dc_shell"} {
				set key_attribute_clock_transition clock_rise_transition
			}
			if {![dict exists $clockdefine $cur_clocked_name skew] || [dict get $clockdefine $cur_clocked_name skew]!=[get_attribute -quiet $one_clocked $key_attribute_clock_transition]} {
				dict set clockdefine $cur_clocked_name skew [get_attribute -quiet $one_clocked $key_attribute_clock_transition]
				puts [format "Script Info:: Auto update clock info(%s) : skew : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name skew]]
			}
			if {![dict exists $clockdefine $cur_clocked_name metal]} {
				dict set clockdefine $cur_clocked_name metal $l_var(top_layer)
				puts [format "Script Info:: Auto update clock info(%s) : metal : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name metal]]
			}
			if {![dict exists $clockdefine $cur_clocked_name type]} {
				dict set clockdefine $cur_clocked_name type CTS
				puts [format "Script Info:: Auto update clock info(%s) : type : %s" $cur_clocked_name CTS]
			}
			if {![dict exists $clockdefine $cur_clocked_name is_mesh]} {
				dict set clockdefine $cur_clocked_name is_mesh	0
			}
			if {![dict exists $clockdefine $cur_clocked_name is_cts]} {
				dict set clockdefine $cur_clocked_name is_cts	1
			}
			if {![dict exists $clockdefine $cur_clocked_name region]} {
				dict set clockdefine $cur_clocked_name region {}
				puts [format "Script Info:: Auto update clock info(%s) : region : %s" $cur_clocked_name \
					[dict get $clockdefine $cur_clocked_name region]]
			}
			dict set clockdefine $cur_clocked_name is_generated [get_attribute -quiet $one_clocked is_generated]
		}
	}
}
proc report_nhp_clockdefine {} {
	upvar 1 nhp_clockdefine clockdefine
	foreach each [dict keys $clockdefine] {
		puts [format "%-30s =>" $each]
		foreach key [dict keys [dict get $clockdefine $each]] {
			puts [format "%40s { %-10s => %s }" " " $key [dict get $clockdefine $each $key]]
		}
	}
}
##################################################################################################
###	Generate setp report files
##################################################################################################
proc report_all {dir_name step_name} {                  
        report_qor -sig 3                       			> ${dir_name}/${step_name}.qor
        report_design_physical -all -verbose    			> ${dir_name}/${step_name}.sum
        report_threshold_voltage_group          			> ${dir_name}/${step_name}.threshold_voltage_group
        report_net_fanout -threshold 50         			> ${dir_name}/${step_name}.net_fanout
        report_clock_tree -summary              			> ${dir_name}/${step_name}.clock_tree
	if {[all_scenarios]!={}} {
        	report_constraints -sig 3 -scenarios [all_active_scenarios]	> ${dir_name}/${step_name}.con
        	report_clock_timing -type skew -scenarios [all_active_scenarios ]	> ${dir_name}/${step_name}.clock_timing
		foreach each_scenario [all_active_scenarios] {
        		rpt_max -scenarios $each_scenario	> ${dir_name}/${step_name}.$each_scenario.max.tim
        		rpt_min -scenarios $each_scenario	> ${dir_name}/${step_name}.$each_scenario.min.tim
		}
		report_power -scenarios [all_active_scenarios]			> ${dir_name}/${step_name}.power
		report_scenarios						> ${dir_name}/${step_name}.scenarios
	} else {
        	report_constraints -sig 3 	> ${dir_name}/${step_name}.con
        	report_clock_timing -type skew 	> ${dir_name}/${step_name}.clock_timing
        	rpt_max 			> ${dir_name}/${step_name}.max.tim
        	rpt_min 			> ${dir_name}/${step_name}.min.tim
		report_power 			> ${dir_name}/${step_name}.power
	}
}
##################################################################################################
###	check one-2-multi connect nets. only check for top level. (for DC)
##################################################################################################
proc report_multi_load {{cell_name *}} {
	set count 0
	foreach_in_collection one [get_nets -of_object [get_cells $cell_name]] {
		set pin_num [expr {[sizeof_collection [get_pins -quiet -of_object $one]]+[sizeof_collection [get_ports -quiet -of_object $one]]}]
		if {$pin_num>2} {
			#report_net -noflat -connection $one
			puts "[get_object_name $one]   ------   [get_object_name [get_cells -quiet -of_objects $one]]"
			incr count
		}
	}
	puts "#######################################################################"
	puts "Total : $count multi_load top-level nets."
	puts "#######################################################################"
}
##################################################################################################
###	highlight un-matched pin/port pair.
##################################################################################################
proc highlight_unmatched_pin_port {{cell_name *}} {
	set result_nets {}
	foreach_in_collection one_net [get_nets -of_object [get_cells $cell_name]] {
		puts [get_object_name $one_net]
		set object_list [get_ports -quiet -of_object $one_net]
		append_to_collection object_list [get_pins -quiet -of_object $one_net]
		if {[sizeof_collection $object_list]>2} {
			append_to_collection result_nets $one_net
		}
		if {[sizeof_collection $object_list]==2} {
			set p1	[index_collection $object_list 0]
			set p2	[index_collection $object_list 1]
			set p1_bbox	[get_attribute $p1 bbox]
			set p2_bbox	[get_attribute $p2 bbox]
			set center_cmp([expr {[lindex $p1_bbox 0 0]+[lindex $p1_bbox 1 0]}])	1
			set center_cmp([expr {[lindex $p1_bbox 0 1]+[lindex $p1_bbox 1 1]}])	1
			set center_cmp([expr {[lindex $p2_bbox 0 0]+[lindex $p2_bbox 1 0]}])	1
			set center_cmp([expr {[lindex $p2_bbox 0 1]+[lindex $p2_bbox 1 1]}])	1
			if {[array size center_cmp]==4} {
				append_to_collection result_nets $one_net
			}
			array unset center_cmp
		}
	}
	if {[sizeof_collection $result_nets]>0} {
		puts [format "There are %d un-matched position nets. please see the highlight show!" [sizeof_collection $result_nets]]
		gui_change_highlight -collection $result_nets
	}
}
##################################################################################################
###	check top-level connection summary.
##################################################################################################
proc report_connection_summary {} {
	set repeat_time	120
	puts [string repeat = $repeat_time]
	puts [format "| %-30s | %8s | %8s | %8s | %-50s |" "Cell Name" "All Nets" "To Ports" "Internal" "Notes"]
	puts [string repeat = $repeat_time]
	foreach_in_collection one_cell [get_cells] {
		array unset cellConMap
		set ref_all_nets [get_nets -quiet -of_object $one_cell]
		set ref_ports	[get_ports -quiet -of_object $ref_all_nets]
		set ref_internal_nets [remove_from_collection $ref_all_nets [get_nets -quiet -of_objects $ref_ports]]
		foreach_in_collection one_inter_net $ref_internal_nets {
			foreach_in_collection one_inter_connected_cell [get_cells -quiet -of_objects $one_inter_net -filter "name != [get_object_name $one_cell]"] {
				if {[info exists cellConMap([get_object_name $one_inter_connected_cell])]} {
					incr cellConMap([get_object_name $one_inter_connected_cell])
				} else {
					set cellConMap([get_object_name $one_inter_connected_cell]) 1
				}
			}
		}
		set first_line true
		foreach {key value} [array get cellConMap] {
			if {$first_line} {
				set first_line false
				set cur_cell_name	[get_object_name $one_cell]
				set cur_nets_num	[sizeof_collection $ref_all_nets]
				set cur_ports_num	[sizeof_collection $ref_ports]
				set cur_inter_net_num	[sizeof_collection $ref_internal_nets]
			} else {
				set cur_cell_name	{}
				set cur_nets_num	{}
				set cur_ports_num	{}
				set cur_inter_net_num	{}
			}
			puts [format "| %-30s | %8s | %8s | %8s | %-50s |" $cur_cell_name $cur_nets_num $cur_ports_num $cur_inter_net_num "$key ($value)"]
				#puts [format "| %-30s | %8s | %8s | %8s | %-50s |" \
					#[get_object_name $one_cell] \
					#[sizeof_collection $ref_all_nets] \
					#[sizeof_collection $ref_ports] \
					#[sizeof_collection $ref_internal_nets] \
					#[array get cellConMap]]
		}
		puts [string repeat - $repeat_time]
	}
}

##################################################################################################
###	Show current status in icc_shell
##################################################################################################
proc show_current_status {message {show_design_info 0}} {
        set esc "\x1b"
        set bel "\x7"
        global env
        set design_info {}
	set timing_group {}
        if {$show_design_info>0} {
                #set group_list [get_object_name [get_attribute [get_timing_paths -delay max] path_group]]
                foreach_in_collection one_max_path [get_timing_paths -delay max] {
                        set max_path_slack([get_object_name [get_attribute $one_max_path path_group]]) [format "%.3f" [get_attribute $one_max_path slack]]
                }
                foreach_in_collection one_min_path [get_timing_paths -delay min] {
                        set min_path_slack([get_object_name [get_attribute $one_min_path path_group]]) [format "%.3f" [get_attribute $one_min_path slack]]
                }
                foreach group [array name max_path_slack] {
                        #append design_info "--\[${group}:$max_path_slack($group)/$min_path_slack($group)\]"
			#lappend timing_group "$group $max_path_slack($group) $min_path_slack($group)"
			if {[info exists max_path_slack($group)]} {
				set cur_max_slack $max_path_slack($group)
			} else {
				set cur_max_slack N/A
			}
			if {[info exists min_path_slack($group)]} {
				set cur_min_slack $min_path_slack($group)
			} else {
				set cur_min_slack N/A
			}
			lappend timing_group "$group $cur_max_slack $cur_min_slack"
                }
		foreach pair [lsort -real -increasing -index 1 $timing_group] {
			append design_info [format "--\[%s:%s/%s\]" [lindex $pair 0] [lindex $pair 1] [lindex $pair 2]]
		}
        }
	set message_error_count	[get_message_info -error_count]
	if {$message_error_count>0} {
       # 	puts "${esc}];$env(HOST):$env(PWD)--\[${message}\]--\[$message_error_count\]${design_info}$bel"
	} else {
       # 	puts "${esc}];$env(HOST):$env(PWD)--\[${message}\]${design_info}$bel"
	}
}
##################################################################################################
###	generate macro placement commands
##################################################################################################
proc get_macros_placement {} {
	foreach_in_collection one_macro [all_macro_cells] {
		set local_name		[get_attribute $one_macro full_name]
		set local_orientation	[get_attribute $one_macro orientation]
		set local_origin 	[get_attribute $one_macro origin]
		puts "set_attribute \[get_cells $local_name\] orientation $local_orientation"
		puts "set_attribute \[get_cells $local_name\] origin {$local_origin}"
		puts ""
	}
}

##################################################################################################
###	report placement region
##################################################################################################
proc report_user_placement_region {} {
	foreach_in_collection one [get_placement_blockages] {
		set name [get_attribute $one name]
		set bbox [get_attribute $one bbox]
		echo [format "%-50s {%-s}" $name [join $bbox]]
	}
}
##################################################################################################
###	generate user shape commands
##################################################################################################
proc get_user_shape_cmd {} {
	foreach_in_collection one_shape [get_user_shapes] {
		if {[string equal [get_attribute $one_shape object_type] POLYGON]} {
			puts "create_user_shape -layer [get_attribute $one_shape layer] -boundary {[get_attribute $one_shape points]} -type poly"
		} else {
			puts "create_user_shape -layer [get_attribute $one_shape layer] -bbox {[get_attribute $one_shape bbox]} -type rect -route_type shield"
		}
	}
}
##################################################################################################
###     create macro power plan regions
##################################################################################################
proc my_create_PPRPRG_base_on_macro_keepout {macro_collection head_prefix default_size_row} {
	upvar nhp_custom_macro_metal_respect_keepout	keepout_metal_custom_dict
	upvar var(autofp,metal_respect_keepout)		keepout_metal_default_var
        unset -nocomplain cur_inst cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top
        redirect -variable rpt_macro_keepout_margin {report_keepout_margin -type hard $macro_collection}
        foreach one_line [split $rpt_macro_keepout_margin "\n"] {
                if {[regexp -- {Cell Name:\s+(\S+)} $one_line match cell_name]} {
                        set cur_inst $cell_name
                }
                if {[regexp -- {Hard Keepout\s+-\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)} \
                        $one_line match cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top]} {
                        if {[info exists cur_inst]} {
				lassign [join [join [convert_from_polygon \
                                                        [resize_polygon [get_attribute [get_cells $cur_inst] boundary] \
                                                        -size_left $cur_keepout_left \
                                                        -size_bottom $cur_keepout_bottom \
                                                        -size_right $cur_keepout_right \
                                                        -size_top $cur_keepout_top] \
                                                        -format rectangle]]] local_llx local_lly local_urx local_ury
                                set local_lly [expr {int($local_lly/$default_size_row)*$default_size_row+$default_size_row/2}]
                                if {[expr {$local_ury/$default_size_row}]==[expr {int($local_ury/$default_size_row)}]} {
                                        set local_ury [expr {(int($local_ury/$default_size_row)-1)*$default_size_row+$default_size_row/2}]
                                } else {
                                        set local_ury [expr {int($local_ury/$default_size_row)*$default_size_row+$default_size_row/2}]
                                }
                                create_power_plan_regions $cur_inst \
                                        -polygon [list [list $local_llx $local_lly] \
							[list $local_urx $local_lly] \
							[list $local_urx $local_ury] \
							[list $local_llx $local_ury]]
				set metal_list_route_guide	$keepout_metal_default_var
				if {[dict exists $keepout_metal_custom_dict $cur_inst]} {
					set metal_list_route_guide	[dict get $keepout_metal_custom_dict $cur_inst]
				}
				foreach one_layer $metal_list_route_guide {
					create_route_guide -name ${head_prefix}_${cur_inst}_$one_layer \
							-coordinate [list $local_llx $local_lly $local_urx $local_ury] -no_preroute_layers $one_layer
				}
                        }
                        unset -nocomplain cur_inst
                }
        }
}
proc my_create_power_plan_regions_base_on_macro_keepout {macro_collection default_size_row} {
        unset -nocomplain cur_inst cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top
        redirect -variable rpt_macro_keepout_margin {report_keepout_margin -type hard $macro_collection}
        foreach one_line [split $rpt_macro_keepout_margin "\n"] {
                if {[regexp -- {Cell Name:\s+(\S+)} $one_line match cell_name]} {
                        set cur_inst $cell_name
                }
                if {[regexp -- {Hard Keepout\s+-\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)} \
                        $one_line match cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top]} {
                        if {[info exists cur_inst]} {
				lassign [join [join [convert_from_polygon \
                                                        [resize_polygon [get_attribute [get_cells $cur_inst] boundary] \
                                                        -size_left $cur_keepout_left \
                                                        -size_bottom $cur_keepout_bottom \
                                                        -size_right $cur_keepout_right \
                                                        -size_top $cur_keepout_top] \
                                                        -format rectangle]]] local_llx local_lly local_urx local_ury
                                set local_lly [expr {int($local_lly/$default_size_row)*$default_size_row+$default_size_row/2}]
                                if {[expr {$local_ury/$default_size_row}]==[expr {int($local_ury/$default_size_row)}]} {
                                        set local_ury [expr {(int($local_ury/$default_size_row)-1)*$default_size_row+$default_size_row/2}]
                                } else {
                                        set local_ury [expr {int($local_ury/$default_size_row)*$default_size_row+$default_size_row/2}]
                                }
                                create_power_plan_regions $cur_inst \
                                        -polygon [list [list $local_llx $local_lly] \
							[list $local_urx $local_lly] \
							[list $local_urx $local_ury] \
							[list $local_llx $local_ury]]
                        }
                        unset -nocomplain cur_inst
                }
        }
}
##################################################################################################
###	create route guides base on macro's keepout margin.
##################################################################################################
proc my_create_preroute_route_guide_base_on_macro_keepout {route_guide_head_prefix metal_list default_size_row} {
	#array unset macro_keepout_map
	set index_macro_keepout_rg	0
	#lassign [get_default_site_row] default_size_site default_size_row
	unset -nocomplain cur_inst cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top
	redirect -variable rpt_macro_keepout_margin {report_keepout_margin -type hard [all_macro_cells]}
	foreach one_line [split $rpt_macro_keepout_margin "\n"] {
		if {[regexp -- {Cell Name:\s+(\S+)} $one_line match cell_name]} {
			set cur_inst $cell_name
		}
		if {[regexp -- {Hard Keepout\s+-\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)} \
			$one_line match cur_keepout_left cur_keepout_bottom cur_keepout_right cur_keepout_top]} {
			if {[info exists cur_inst]} {
				set cur_bbox_polygon	[get_attribute [get_cells $cur_inst] boundary]
				set cur_new_rg_rect	[join [convert_from_polygon [resize_polygon $cur_bbox_polygon \
								-size_left $cur_keepout_left \
								-size_bottom $cur_keepout_bottom \
								-size_right $cur_keepout_right \
								-size_top $cur_keepout_top] \
							-format rectangle]]
				lassign [join $cur_new_rg_rect] local_llx local_lly local_urx local_ury
				set local_lly [expr {int($local_lly/$default_size_row)*$default_size_row+$default_size_row/2}]
				if {[expr {$local_ury/$default_size_row}]==[expr {int($local_ury/$default_size_row)}]} {
					set local_ury [expr {(int($local_ury/$default_size_row)-1)*$default_size_row+$default_size_row/2}]
				} else {
					set local_ury [expr {int($local_ury/$default_size_row)*$default_size_row+$default_size_row/2}]
				}
				foreach one_layer $metal_list {
					create_route_guide -name ${route_guide_head_prefix}_${one_layer}_$index_macro_keepout_rg \
							-coordinate [list $local_llx $local_lly $local_urx $local_ury] -no_preroute_layers $one_layer
				}
				incr index_macro_keepout_rg 1
			}
			unset -nocomplain cur_inst
		}
	}
}
##################################################################################################
###	get center square
##################################################################################################
proc get_center_square {bbox} {
	lassign [join $bbox] llx lly urx ury
	set height	[expr {$ury-$lly}]
	set width	[expr {$urx-$llx}]
	if {$height>$width} {
		set t_llx $llx
		set t_lly [expr {$lly+($height-$width)/2}]
		set t_urx $urx
		set t_ury [expr {$lly+($height+$width)/2}]
	} elseif {$height<$width} {
		set t_llx [expr {$llx+($width-$height)/2}]
		set t_lly $lly
		set t_urx [expr {$llx+($width+$height)/2}]
		set t_ury $ury
	} else {
		return $bbox
	}
	return [list [list $t_llx $t_lly] [list $t_urx $t_ury]]
}
##################################################################################################
###	report clock tree summary to file
##################################################################################################
proc report_clock_tree_summary_to_file {file} {
	#upvar 1 clocklist_cts ctslist
	upvar 1 nhp_clockdefine clockdefine
	set ctslist [dict keys [dict filter $clockdefine script {key value} {dict get $clockdefine $key is_cts}]]
	redirect -variable summary_rpt {report_clock_tree -clock_trees [get_clocks $ctslist] -summary}
	regexp -lineanchor {^=+ Clock Tree Summary =+\s*\n(.+)^[10]\s*\n} $summary_rpt match detail
	echo $detail >> $file
}
##################################################################################################
###	Recover Clock period (for ICC)
##################################################################################################
proc recover_clock_period {} {
	upvar 1 clock		clock_array
	upvar 1 clock_pin	clock_array_pin
	#upvar 1 mcmm_clock_file mcmm_clock_file_array
	upvar 1 lib_mcmm	lib_mcmm_dict
	upvar 1 var(ref_clock)	ref_clock
	if {[all_scenarios]!={}} {
                set cur_scenario                [current_scenario]
                set all_active_scenarios        [all_active_scenarios]
                set all_setup_scenarios [get_scenarios -setup true]
                foreach scenario $all_active_scenarios {
			current_scenario $scenario
                ###     load clock definition
                        source -echo -verbose [dict get $lib_mcmm_dict $scenario clock_file]
                ###     define default virtual clock
                        set default_virtual_clock [lindex $ref_clock 0]
                        create_clock -name $default_virtual_clock -period [lindex $ref_clock 1]
                ###     define real clock
                        if {[llength [array name clock_array]]>0} {
                                foreach clock_name [array name clock_array] {
                                        if {[info exists clock_array_pin($clock_name)]} {
                                                set clock_port  $clock_array_pin($clock_name)
                                        } else  {
                                                set clock_port  $clock_name
                                        }
					if {[sizeof_collection [get_ports -quiet $clock_port]]>0} {
                                        	create_clock -name $clock_name -period [lindex $clock_array($clock_name) 0] [get_ports $clock_port]
					} elseif {[sizeof_collection [get_pins -quiet $clock_port]]>0} {
                                        	create_clock -name $clock_name -period [lindex $clock_array($clock_name) 0] [get_pins $clock_port]
					} else {
						puts [format "Script %s:: clock root : %s is neither port nor pin, plz check it!" [string totitle error] $clock_port]
						exit
					}
                                        set_dont_touch_network  [get_clocks $clock_name]
                                        #set_ideal_network      [get_clocks $clock_name]
                                        set_drive       0       [get_ports $clock_name]
                                        set_clock_uncertainty -setup    [lindex $clock_array($clock_name) 1] [get_clocks $clock_name]
                                        set_clock_uncertainty -hold     [lindex $clock_array($clock_name) 2] [get_clocks $clock_name]
                                        set_clock_transition            [lindex $clock_array($clock_name) 3] [get_clocks $clock_name]
                                }
                        }
                }
                set_active_scenario $all_active_scenarios
                current_scenario $cur_scenario
		report_clock
	} else {
        ###     define default virtual clock
                set default_virtual_clock [lindex $ref_clock 0]
                create_clock -name $default_virtual_clock -period [lindex $ref_clock 1]
        ###     define real clock
                if {[llength [array name clock_array]]>0} {
                        foreach clock_name [array name clock_array] {
                                if {[info exists clock_array_pin($clock_name)]} {
                                        set clock_port  $clock_array_pin($clock_name)
                                } else {
                                        set clock_port  $clock_name
                                }
				if {[sizeof_collection [get_ports -quiet $clock_port]]>0} {
                                	create_clock -name $clock_name -period [lindex $clock_array($clock_name) 0] [get_ports $clock_port]
				} elseif {[sizeof_collection [get_pins -quiet $clock_port]]>0} {
                                	create_clock -name $clock_name -period [lindex $clock_array($clock_name) 0] [get_pins $clock_port]
				} else {
					puts [format "Script %s:: clock root : %s is neither port nor pin, plz check it!" [string totitle error] $clock_port]
					exit
				}
                                set_dont_touch_network  [get_clocks $clock_name]
                                #set_ideal_network      [get_clocks $clock_name]
                                set_drive       0       [get_ports $clock_name]
                                set_clock_uncertainty -setup    [lindex $clock_array($clock_name) 1] [get_clocks $clock_name]
                                set_clock_uncertainty -hold     [lindex $clock_array($clock_name) 2] [get_clocks $clock_name]
                                set_clock_transition            [lindex $clock_array($clock_name) 3] [get_clocks $clock_name]
                        }
                }
                report_clock
        }
}
##################################################################################################
###	Get QoR summary to a variable (for ICC)
##################################################################################################
proc get_qor_summary {{level 1}} {
	upvar synopsys_program_name program_name
	redirect -variable qor_rpt {report_qor -sig 3}
	if {$level>=2} {
		if {$program_name == "dc_shell"} {
			redirect -variable qor_phy {report_area -physical}
			if {$level>2} { set level 2 }
		}
		if {$program_name == "icc_shell"} {
			#redirect -variable qor_phy {report_qor -physical}
			redirect -variable qor_phy {report_design -physical}
		}
		redirect -variable qor_pwr {report_power}
		redirect -variable qor_mvt {report_threshold_voltage_group}
		if {$level>=3} {
			redirect -variable qor_xtalk {report_net_delta_delay}
			redirect -variable qor_slope {report_constraint -significant_digits 3 -all_violators -nosplit -max_transition}
		}
	}
	array unset pathgroup
	array unset total_ns
	set grouplist ""
	set group_wns_pair ""
	set scenario_list ""
	set scenario_name default_one
	set cur_scenario	""
	set mark_pathgroup 0
	set length_name		5
	set length_period	6
	set length_max_wns	6
	set length_max_tns	6
	set length_min_wns	6
	set length_min_tns	6
	set rpt	""
	if {[all_scenarios]!={}} {
		set mcmm_flow	true
		set cur_scenario	[current_scenario]
	} else {
		set mcmm_flow	false
		lappend scenario_list $scenario_name
	}

	foreach one_line [split $qor_rpt "\n"] {
		if {$mcmm_flow && [regexp -- {Scenario\s+'(\S+?)'} $one_line match scenario_name]} {
			if {![info exists scenario_array($scenario_name)]} {
				set scenario_array($scenario_name) 1
				lappend scenario_list $scenario_name
			}
		}
		if {[regexp -- {Timing Path Group\s+'(.+?)'} $one_line match group_name]} {
			set mark_pathgroup 1
			if {![info exists group_array($group_name)]} {
				set group_array($group_name) 1
				lappend grouplist $group_name
				if {[string length $group_name]>$length_name} {set length_name [string length $group_name]}
			}
		}
		if {$mark_pathgroup && [regexp -- {^\s*$} $one_line]} {
			set mark_pathgroup 0
			unset -nocomplain group_name
			if {$mcmm_flow} { unset -nocomplain scenario_name }
		}
		if {$mark_pathgroup && [info exists group_name]} {
			if {[regexp -- {Critical Path Slack:\s+(\S+)} $one_line match value]} {
				set pathgroup($scenario_name,$group_name,max_wns) $value
				if {[string length $value]>$length_max_wns} {set length_max_wns [string length $value]}
			}
			if {[regexp -- {Total Negative Slack:\s+(\S+)} $one_line match value]} {
				set pathgroup($scenario_name,$group_name,max_tns) $value
				if {[string length $value]>$length_max_tns} {set length_max_tns [string length $value]}
			}
			if {[regexp -- {Worst Hold Violation:\s+(\S+)} $one_line match value]} {
				set pathgroup($scenario_name,$group_name,min_wns) $value
				if {[string length $value]>$length_min_wns} {set length_min_wns [string length $value]}
			}
			if {[regexp -- {Total Hold Violation:\s+(\S+)} $one_line match value]} {
				set pathgroup($scenario_name,$group_name,min_tns) $value
				if {[string length $value]>$length_min_tns} {set length_min_tns [string length $value]}
			}
		}
		if {[regexp -- {Design\s+WNS:\s*(\S+)\s*TNS:\s*(\S+)\s*Number of Violating Paths:\s*(\S+)} $one_line match wns_value tns_value num_value]} {
			set total_ns(total,max_wns)	[format "%.3f" [expr {0-$wns_value}]]
			set total_ns(total,max_tns)	[format "%.3f" [expr {0-$tns_value}]]
			set total_ns(total,max_vio)	$num_value
			if {[string length $total_ns(total,max_wns)]>$length_max_wns} {set length_max_wns [string length $total_ns(total,max_wns)]}
			if {[string length $total_ns(total,max_tns)]>$length_max_tns} {set length_max_tns [string length $total_ns(total,max_tns)]}
		}
		if {[regexp -- {Design\s+\(Hold\)\s+WNS:\s*(\S+)\s*TNS:\s*(\S+)\s*Number of Violating Paths:\s*(\S+)} $one_line match wns_value tns_value num_value]} {
			set total_ns(total,min_wns)	[format "%.3f" [expr {0-$wns_value}]]
			set total_ns(total,min_tns)	[format "%.3f" [expr {0-$tns_value}]]
			set total_ns(total,min_vio)	$num_value
			if {[string length $total_ns(total,min_wns)]>$length_min_wns} {set length_min_wns [string length $total_ns(total,min_wns)]}
			if {[string length $total_ns(total,min_tns)]>$length_min_tns} {set length_min_tns [string length $total_ns(total,min_tns)]}
		}
	}
	foreach current_scenario $scenario_list {
		foreach one $grouplist {
			if {[get_attribute -quiet [get_clocks -quiet $one] period]>0} {
				set cur_period [format "%.3f" [get_attribute [get_clocks -quiet $one] period]]
				if {[string length $cur_period]>$length_period} {
					set length_period [string length $cur_period]
				}
			}
		}
	}
	set length_line [expr {$length_name+$length_period+$length_max_wns+$length_max_tns+$length_min_wns+$length_min_tns+5*2+1+8}]
	set scenario_title_line [expr {$length_line-14}]
	set scenario_loop_print 0
	append rpt "[string repeat = $length_line]\n"
	foreach current_scenario $scenario_list {
		unset -nocomplain group_wns_pair
		if {$scenario_loop_print>0} { append rpt "\n" }
		if {$mcmm_flow} {
			append rpt [format "| Scenario: %-${scenario_title_line}s |\n" $current_scenario]
			append rpt "[string repeat = $length_line]\n"
			current_scenario $current_scenario
		}
		append rpt [format "| %-${length_name}s | %${length_period}s | %${length_max_wns}s   %${length_max_tns}s | %${length_min_wns}s   %${length_min_tns}s |\n" \
				Path "Clock " MAX TIMING MIN TIMING]
		append rpt [format "| %-${length_name}s | %${length_period}s | %${length_max_wns}s | %${length_max_tns}s | %${length_min_wns}s | %${length_min_tns}s |\n" \
				Group Period WNS TNS WNS TNS]
		append rpt "[string repeat - $length_line]\n"
                foreach one $grouplist {
			if {[info exists pathgroup($current_scenario,$one,max_wns)]} {
                        	lappend group_wns_pair "$one $pathgroup($current_scenario,$one,max_wns)"
			} else {
                        	lappend group_wns_pair "$one 0.0"
			}
                }
		set group_wns_pair [lsort -index 1 -real $group_wns_pair]
		foreach one_pair $group_wns_pair {
			set one [lindex $one_pair 0]
			set cur_scenario_clock_max_wns	"N/A"
			set cur_scenario_clock_max_tns	"N/A"
			set cur_scenario_clock_min_wns	"N/A"
			set cur_scenario_clock_min_tns	"N/A"
			if {[info exists pathgroup($current_scenario,$one,max_wns)]} {
				set cur_scenario_clock_max_wns $pathgroup($current_scenario,$one,max_wns)
			}
			if {[info exists pathgroup($current_scenario,$one,max_tns)]} {
				set cur_scenario_clock_max_tns $pathgroup($current_scenario,$one,max_tns)
			}
			if {[info exists pathgroup($current_scenario,$one,min_wns)]} {
				set cur_scenario_clock_min_wns $pathgroup($current_scenario,$one,min_wns)
			}
			if {[info exists pathgroup($current_scenario,$one,min_tns)]} {
				set cur_scenario_clock_min_tns $pathgroup($current_scenario,$one,min_tns)
			}
			if {[sizeof_collection [get_clocks -quiet $one]]>0} {
				append rpt [format "| %-${length_name}s | %${length_period}.3f | %${length_max_wns}s | %${length_max_tns}s | %${length_min_wns}s | %${length_min_tns}s |\n" \
					$one [get_attribute [get_clocks -quiet $one] period] \
					$cur_scenario_clock_max_wns $cur_scenario_clock_max_tns \
					$cur_scenario_clock_min_wns $cur_scenario_clock_min_tns]
			} else {
				append rpt [format "| %-${length_name}s | %${length_period}s | %${length_max_wns}s | %${length_max_tns}s | %${length_min_wns}s | %${length_min_tns}s |\n" \
					$one " " \
					$cur_scenario_clock_max_wns $cur_scenario_clock_max_tns \
					$cur_scenario_clock_min_wns $cur_scenario_clock_min_tns]
			}
		}
		append rpt "[string repeat = $length_line]"
		incr scenario_loop_print 1
	}
	append rpt [format "\n| %-${length_name}s | %${length_period}s | %${length_max_wns}s | %${length_max_tns}s | %${length_min_wns}s | %${length_min_tns}s |\n" \
					Total " " \
					$total_ns(total,max_wns) $total_ns(total,max_tns) \
					$total_ns(total,min_wns) $total_ns(total,min_tns)]
	append rpt "[string repeat = $length_line]"
	if {$mcmm_flow} {
		current_scenario $cur_scenario
	}
	if {$level>=2} {
		append rpt "\n"
		set slength_name 14 
		set slength_value [expr {$length_line-$slength_name-5-2}]
		set phy_area 0
		set phy_util ""
		set pwr_dynmaic 0
		set pwr_leakage 0
		set pwr_total	0
		foreach one_line [split $qor_phy "\n"] {
			if {$program_name == "dc_shell"} {
				if {[regexp -- {^Total cell area:\s+(\S+)} $one_line match phy_area]} {
					append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Cell area" $phy_area]
				}
				if {[regexp -- {^Utilization Ratio:\s+(\S+)} $one_line match phy_util]} {
					append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Utilization" $phy_util]
				}
			}
			if {$program_name == "icc_shell"} {
				if {[regexp -- {^\s+Total Std Cell Area:\s+(\S+)} $one_line match phy_area]} {
					append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Cell area" $phy_area]
				}
				if {[regexp -- {^\s+Std cells utilization:\s+(\S+)} $one_line match phy_util]} {
					append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Utilization" $phy_util]
				}
				if {$level>=3 && [regexp -- {^\s+The optimized via conversion rate.+=\s+(\S+)} $one_line match phy_via_opt_rate]} {
					append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Optimized via" $phy_via_opt_rate]
				}
			}
		}
		append rpt "[string repeat - $length_line]\n"
		foreach one_line [split $qor_pwr "\n"] {
			if {[regexp -- {^Total Dynamic Power\s+=\s+(\S+\s+\S[Ww])} $one_line match pwr_dynamic]} {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Dynamic Power" $pwr_dynamic]
			}
			if {[regexp -- {^Cell Leakage Power\s+=\s+(\S+\s+\S[Ww])} $one_line match pwr_leakage]} {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Leakage Power" $pwr_leakage]
			}
			if {$program_name == "icc_shell" && [regexp -- {^Total\s+.+?(\S+\s+\S[Ww])\s*$} $one_line match pwr_total]} {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Total Power" $pwr_total]
			}
		}
		append rpt "[string repeat - $length_line]\n"
		if {$level>=3} {
			set slope_index 0
			set worst_slope 0
			foreach one_line [split $qor_slope \n] {
				if {[regexp -- {max_transition} $one_line match]} { set slope_index 1 }
				if {$slope_index==1 && [regexp -- {^\s*-+\s*$} $one_line match]} { set slope_index 2 }
				if {$slope_index==2 && [regexp -- {^\s*\S+\s+\S+\s+(\S+)} $one_line match slope]} {
					set worst_slope $slope
					set slope_index 3
				}
			}
			if { $worst_slope==0 } {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Worst Slope" {< default}]
			} else {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Worst Slope" [format "%.3f" $worst_slope]]
			}
			set worst_delta_delay_max 0
			set worst_delta_delay_min 0
        		foreach one_line [split $qor_xtalk \n] {
                		if {[regexp -- {Net:(\S+).+?max\s+(\S+)\s+min\s+(\S+)} $one_line match net max min]} {
					if {$max>$worst_delta_delay_max} {set worst_delta_delay_max $max}
					if {$min<$worst_delta_delay_min} {set worst_delta_delay_min $min}
                		}
        		}
			append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Max DeltaDelay" [format "%.3f" $worst_delta_delay_max]]
			append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Min DeltaDelay" [format "%.3f" $worst_delta_delay_min]]
			append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "Route Errors" [sizeof_collection [get_drc_errors -quiet]]]
			append rpt "[string repeat - $length_line]\n"
		}
		set mvt_index 0
		set mvt_per ""
		foreach one_line [split $qor_mvt "\n"] {
			if {[regexp -- {^\s*Threshold Voltage Group Report} $one_line]} { set mvt_index 1 }
			if {$mvt_index>0} { if {[regexp -- {^\*+\s*$} $one_line]} { incr mvt_index 1 } }
			if {$mvt_index==4 && [regexp -- {^(\S+).+\((.+?)\)} $one_line match mvt_lib mvt_per]} {
				append rpt [format "| %-${slength_name}s : %${slength_value}s |\n" "$mvt_lib" $mvt_per]
			}
		}
		append rpt "[string repeat = $length_line]"
	}
	return $rpt
}
##################################################################################################
###	report routing quality
##################################################################################################
proc report_final_routing_quality {} {
	set mark_length 70
	set final_quality {}
	set design_name [get_attribute [current_design] full_name]
	if {[sizeof_collection [get_mw_cels -quiet ${design_name}_lvs.err]]>0} {
		open_mw_cel -not_as_current ${design_name}_lvs.err
		update_one_type_quality final_quality [get_drc_errors -quiet -error_view ${design_name}_lvs.err] LVS
		close_mw_cel ${design_name}_lvs.err
	}
	if {[sizeof_collection [get_drc_errors -quiet]]>0} {
		update_one_type_quality final_quality [get_drc_errors -quiet] Routing
	}
	if {[sizeof_collection [get_mw_cels -quiet ${design_name}_ADR_sdrc.err]]>0} {
		open_mw_cel -not_as_current ${design_name}_ADR_sdrc.err
		update_one_type_quality final_quality [get_drc_errors -quiet -error_view ${design_name}_ADR_sdrc.err] Signoff-DRC
		close_mw_cel ${design_name}_ADR_sdrc.err
	} elseif {[sizeof_collection [get_mw_cels -quiet ${design_name}_sdrc.err]]>0} {
		open_mw_cel -not_as_current ${design_name}_sdrc.err
		update_one_type_quality final_quality [get_drc_errors -quiet -error_view ${design_name}_sdrc.err] Signoff-DRC
		close_mw_cel ${design_name}_sdrc.err
	} else {
		### no signoff-drc database
	}
	set rpt ""
	append rpt [format "%s %s %s\n" [string repeat "=" 23] "Final Routing Quality" [string repeat "=" 24]]
	if {[dict size $final_quality]>0} {
		append rpt [format "%-12s | %-40s | %-10s |\n" "Class" "Type" "Violations"]
		append rpt "[string repeat "-" $mark_length]\n"
		foreach one_err_type [dict keys $final_quality] {
			foreach one_err_detail [dict keys [dict get $final_quality $one_err_type]] {
				if {[string length $one_err_detail]>40} {
					set one_show_detail "[string range $one_err_detail 0 35] ..."
				} else {
					set one_show_detail $one_err_detail
				}
				append rpt [format "%-12s | %-40s | %10d |\n" $one_err_type $one_show_detail [dict get $final_quality $one_err_type $one_err_detail]]
			}
		}
	} else {
		append rpt "It's EXCELLENT, GOOD JOBS!^_^!\n"
	}
	append rpt "[string repeat "=" $mark_length]"
	return $rpt
}
proc update_one_type_quality {dict_name error_collection type} {
	upvar 1 $dict_name dict_quality
	foreach_in_collection one_err $error_collection {
		set err_type [get_attribute $one_err type]
		if {[dict exists $dict_quality $type $err_type]} {
			dict with dict_quality {
				dict incr $type $err_type 1
			}
		} else {
			dict set dict_quality $type $err_type 1
		}
	}
}
##################################################################################################
###	report routing quality
##################################################################################################
proc reshape_endpoints_baseone_vias {one_shape} {
	lassign [get_attribute $one_shape points] cur_points_0 cur_points_1
	set one_used_metal	[get_attribute $one_shape layer_name]
        set cur_direction       [get_attribute [get_layers $one_used_metal] preferred_direction]
        set col_vias_0  [get_vias -quiet -intersect [list $cur_points_0 $cur_points_0] -filter "upper_layer==$one_used_metal"]
        append_to_collection col_vias_0 [get_vias -quiet -intersect [list $cur_points_0 $cur_points_0] -filter "lower_layer==$one_used_metal"]
        set col_vias_1  [get_vias -quiet -intersect [list $cur_points_1 $cur_points_1] -filter "upper_layer==$one_used_metal"]
        append_to_collection col_vias_1 [get_vias -quiet -intersect [list $cur_points_1 $cur_points_1] -filter "lower_layer==$one_used_metal"]
        if {[string equal $cur_direction horizontal]} {
                set cur_state_point [lindex $cur_points_0 1]
                if {[lindex $cur_points_0 0]<[lindex $cur_points_1 0]} {
                        set cur_left_side 	[lindex $cur_points_0 0]
                        set cur_right_side 	[lindex $cur_points_1 0]
                        foreach_in_collection one $col_vias_0 {
                                if {[get_attribute $one bbox_llx]<$cur_left_side} {
                                        set cur_left_side [get_attribute $one bbox_llx]
                                }
                        }
                        foreach_in_collection one $col_vias_1 {
                                if {[get_attribute $one bbox_urx]>$cur_right_side} {
                                        set cur_right_side [get_attribute $one bbox_urx]
                                }
                        }
                } else {
                        set cur_left_side  	[lindex $cur_points_1 0]
                        set cur_right_side 	[lindex $cur_points_0 0]
                        foreach_in_collection one $col_vias_1 {
                                if {[get_attribute $one bbox_llx]<$cur_left_side} {
                                        set cur_left_side [get_attribute $one bbox_llx]
                                }
                        }
                        foreach_in_collection one $col_vias_0 {
                                if {[get_attribute $one bbox_urx]>$cur_right_side} {
                                        set cur_right_side [get_attribute $one bbox_urx]
                                }
                        }
                }
                set cur_new_points [list [list $cur_left_side $cur_state_point] [list $cur_right_side $cur_state_point]]
        } else {
                set cur_state_point [lindex $cur_points_0 0]
                if {[lindex $cur_points_0 1]<[lindex $cur_points_1 1]} {
                        set cur_bottom_side [lindex $cur_points_0 1]
                        set cur_top_side [lindex $cur_points_1 1]
                        foreach_in_collection one $col_vias_0 {
                                if {[get_attribute $one bbox_lly]<$cur_bottom_side} {
                                        set cur_bottom_side [get_attribute $one bbox_lly]
                                }
                        }
                        foreach_in_collection one $col_vias_1 {
                                if {[get_attribute $one bbox_ury]>$cur_top_side} {
                                        set cur_top_side [get_attribute $one bbox_ury]
                                }
                        }
                } else {
                        set cur_bottom_side [lindex $cur_points_1 1]
                        set cur_top_side [lindex $cur_points_0 1]
                        foreach_in_collection one $col_vias_1 {
                                if {[get_attribute $one bbox_lly]<$cur_bottom_side} {
                                        set cur_bottom_side [get_attribute $one bbox_lly]
                                }
                        }
                        foreach_in_collection one $col_vias_0 {
                                if {[get_attribute $one bbox_ury]>$cur_top_side} {
                                        set cur_top_side [get_attribute $one bbox_ury]
                                }
                        }
                }
                set cur_new_points [list [list $cur_state_point $cur_bottom_side] [list $cur_state_point $cur_top_side]]
        }
        set_attribute $one_shape points $cur_new_points
}
##################################################################################################
###	show current regs regions,
##################################################################################################
proc report_clock_regions {{flag 0} {scalar 1}} {
	#upvar 1 clock clock_array
	#upvar 1 clocklist_mesh clock_mesh
	upvar 1 nhp_clockdefine clockdefine
	set clock_mesh [dict keys [dict filter $clockdefine script {key value} {dict get $clockdefine $key is_mesh}]]
	set die_size_bbox [get_attribute [get_die_areas] bbox]
	foreach one_mesh $clock_mesh {
                set cur_mesh_load [get_pins -leaf -of_objects [get_nets -segments [dict get $clockdefine $one_mesh root]]]
                set cur_mesh_load_cell [get_cells -of_objects [get_nets -segments [dict get $clockdefine $one_mesh root]] -filter {is_hierarchical==false}]
                if {[sizeof_collection [get_pins -quiet -of_objects [all_macro_cells]]]>0} {
                        set cur_mesh_load [remove_from_collection $cur_mesh_load [get_pins -of_objects [all_macro_cells]]]
                        set cur_mesh_load_cell [remove_from_collection $cur_mesh_load_cell [all_macro_cells]]
                }
		lassign [join $die_size_bbox] eff_bbox_urx eff_bbox_ury eff_bbox_llx eff_bbox_lly
                set eff_width   0
                set eff_height  0
                foreach cur_pin_bbox [get_attribute $cur_mesh_load bbox] {
			lassign [join $cur_pin_bbox] cur_pin_bbox_llx cur_pin_bbox_lly cur_pin_bbox_urx cur_pin_bbox_ury
                        if {$eff_bbox_llx>$cur_pin_bbox_llx} {set eff_bbox_llx $cur_pin_bbox_llx}
                        if {$eff_bbox_lly>$cur_pin_bbox_lly} {set eff_bbox_lly $cur_pin_bbox_lly}
                        if {$eff_bbox_urx<$cur_pin_bbox_urx} {set eff_bbox_urx $cur_pin_bbox_urx}
                        if {$eff_bbox_ury<$cur_pin_bbox_ury} {set eff_bbox_ury $cur_pin_bbox_ury}
                }
		set eff_width [expr {$eff_bbox_urx-$eff_bbox_llx}]
		set eff_height [expr {$eff_bbox_ury-$eff_bbox_lly}]
		set ext_width [expr {$eff_width*($scalar-1)}]
		set ext_height [expr {$eff_height*($scalar-1)}]
		set eff_bbox_llx [expr {$eff_bbox_llx-$ext_width/2}]
		set eff_bbox_lly [expr {$eff_bbox_lly-$ext_height/2}]
		set eff_bbox_urx [expr {$eff_bbox_urx+$ext_width/2}]
		set eff_bbox_ury [expr {$eff_bbox_ury+$ext_height/2}]
		if {$flag} {
			puts [format "set clock(%s)\t{%s %s %s %s %s %s {%s %s %s %s}}" $one_mesh \
				[dict get $clockdefine $one_mesh period] \
				[dict get $clockdefine $one_mesh setup] \
				[dict get $clockdefine $one_mesh hold] \
				[dict get $clockdefine $one_mesh skew] \
				[dict get $clockdefine $one_mesh metal] \
				[dict get $clockdefine $one_mesh type] \
				$eff_bbox_llx $eff_bbox_lly $eff_bbox_urx $eff_bbox_ury]
		} else {
			puts [format "%-30s {%s %s %s %s}" $one_mesh $eff_bbox_llx $eff_bbox_lly $eff_bbox_urx $eff_bbox_ury]
		}
		unset -nocomplain cur_mesh_load cur_mesh_load_cell
	}
}
##################################################################################################
###	color highlight all clock mesh network
##################################################################################################
proc color_show_icc_clockline {{cus {}}} {
	gui_change_highlight -remove -all_colors
	upvar #0 nhp_clockdefine clockdefine
	set color_cycle [list red yellow orange green blue purple light_orange light_red light_green light_blue light_purple]
	set color_index 0
	if {[llength $cus]==0} {
		update_nhp_clockdefine
		set cus [dict keys $clockdefine]
	}
	foreach Clock $cus {
		if {$color_index==[llength $color_cycle]} {
			set color_index 0
		}
		set cur_color [lindex $color_cycle $color_index]
		puts [format "Clock : %-20s , color is : %s" $Clock $cur_color]
		gui_change_highlight -collection [get_nets -segments -of_objects [all_fanout -flat -from [get_attribute [get_clocks $Clock] sources]]] -color $cur_color
		incr color_index 1
	}
}
proc color_show_icc_clockline_one_by_one {{nums 1}} {
	gui_change_highlight -remove -all_colors
	upvar #0 nhp_clockdefine clockdefine
	upvar 1 myvalue_color_clock_cache clock_cache
	if {![info exists clock_cache]} {
		update_nhp_clockdefine
		foreach one [dict keys $clockdefine] {
			set clock_cache($one)	1
		}
	}
	set color_cycle [list red yellow orange green blue purple light_orange light_red light_green light_blue light_purple]
	set color_index 0
	set flag_i 0
	gui_change_highlight -remove -all_colors
	for {set i 0} {$i<$nums} {incr i 1} {
		if {[array size clock_cache]>0} {
			set cur_clock [lindex [array name clock_cache] 0]
			if {$color_index==[llength $color_cycle]} {
				set color_index 0
			}
			set cur_color [lindex $color_cycle $color_index]
			puts [format "Clock : %-20s , color is : %s" $cur_clock $cur_color]
			gui_change_highlight -collection [get_nets -segments -of_objects [all_fanout -flat -from [get_attribute [get_clocks $cur_clock] sources]]] -color $cur_color
			incr color_index 1
			array unset clock_cache $cur_clock
		} else {
			puts "one cycle is done!"
			array unset clock_cache
		}
	}
}
##################################################################################################
###	color highlight all regs
##################################################################################################
proc color_show_all_regs {{cus {}}} {
	gui_change_highlight -remove -all_colors
	upvar #0 nhp_clockdefine clockdefine
	set color_cycle [list red yellow orange green blue purple light_orange light_red light_green light_blue light_purple]
	set color_index 0
	if {[llength $cus]==0} {
		update_nhp_clockdefine
		set cus [dict keys $clockdefine]
	}
	foreach Clock $cus {
		if {$color_index==[llength $color_cycle]} {
			set color_index 0
		}
		set cur_color [lindex $color_cycle $color_index]
		puts [format "Clock : %-20s , color is : %s" $Clock $cur_color]
		gui_change_highlight -collection [get_flat_cells -of_objects [all_fanout -flat -endpoints_only -from [get_attribute [get_clocks $Clock] sources]]] -color $cur_color
		incr color_index 1
	}
}
proc color_show_cells_by_nets {cus} {
	gui_change_highlight -remove -all_colors
	set color_cycle [list red yellow orange green blue purple light_orange light_red light_green light_blue light_purple]
	set color_index 0
	foreach cur_net $cus {
		if {$color_index==[llength $color_cycle]} {
			set color_index 0
		}
		set cur_color [lindex $color_cycle $color_index]
		puts [format "Nets : %-20s , color is : %s" $cur_net $cur_color]
		gui_change_highlight -collection [get_flat_cells -of_objects [all_fanout -flat -endpoints_only -from [get_nets $cur_net]]] -color $cur_color
		incr color_index 1
	}
}
##################################################################################################
###	color highlight all regs
##################################################################################################
proc color_show_hier_cells {} {
	set color_cycle [list yellow orange red green blue purple light_orange light_red light_green light_blue light_purple]
	set color_index 0
	foreach_in_collection cell [get_cells -filter {is_hierarchical==true}] {
		if {$color_index==[llength $color_cycle]} {
			set color_index 0
		}
		set cur_color [lindex $color_cycle $color_index]
		puts [format "%-20s %-20s , color is : %s" [get_attribute $cell name] ([get_attribute $cell ref_name]) $cur_color]
		gui_change_highlight -collection [get_cells -of_objects $cell] -color $cur_color
		incr color_index 1
	}
}
##################################################################################################
###	split seperated mesh clocks
##################################################################################################
proc split_seperated_mesh_clock {{cus_list {}}} {
	upvar #0 nhp_clockdefine clockdefine
	array unset meshnet
	set clock_mesh [dict keys [dict filter $clockdefine script {key value} {dict get $clockdefine $key is_mesh}]]
	if {[llength $cus_list]>0} { set clock_mesh $cus_list }
	foreach one_mesh $clock_mesh {
		foreach one_root [dict get $clockdefine $one_mesh root] {
			set meshnet($one_root)	[dict get $clockdefine $one_mesh metal]
		}
	}

	redirect -variable verify_lvs_open {verify_lvs -exclude_nets {VDD VSS}}
	set err_flag 0
	set total_changed_mesh 0
	array unset mesh_seperated_areas
	foreach one_line [split $verify_lvs_open "\n"] {
		if {[regexp -- {^\*\*} $one_line]} {
			set err_flag 0
			set clock_name ""
		}
                if {[regexp -- {^ERROR : Logical Net (\S+) is open} $one_line match clock_name]} {
			if {[info exists meshnet($clock_name)]} {
				set err_flag 1
			} else {
				set err_flag 0
			}
                }
		if {$err_flag && [regexp -- {Node \d+ is in the region \(\((-?\d+),(-?\d+)\),\((-?\d+),(-?\d+)\)\)} $one_line match cn_llx cn_lly cn_urx cn_ury]} {
			lappend mesh_seperated_areas($clock_name) [list [expr {$cn_llx-1}] [expr {$cn_lly-1}] [expr {$cn_urx+1}] [expr {$cn_ury+1}]]
		}
	}
	foreach one_clock [array name mesh_seperated_areas] {
		set name_index 1
		set new_name_prefix $one_clock
		set cur_clock_llx [get_attribute [get_terminals $one_clock] bbox_llx]
		set cur_clock_lly [get_attribute [get_terminals $one_clock] bbox_lly]
		set cur_clock_urx [get_attribute [get_terminals $one_clock] bbox_urx]
		set cur_clock_ury [get_attribute [get_terminals $one_clock] bbox_ury]
		if {[regexp -- {[\[\]]} $one_clock]} {
			regsub -all -- {[\[\]]} $one_clock _ new_name_prefix
		}
		foreach each_clock_area $mesh_seperated_areas($one_clock) {
			if {$cur_clock_llx>=[lindex $each_clock_area 0] && $cur_clock_lly>=[lindex $each_clock_area 1] &&
				$cur_clock_urx<=[lindex $each_clock_area 2] && $cur_clock_ury<=[lindex $each_clock_area 3]} {
				continue
			} else {
				set new_clock_name ${new_name_prefix}_$name_index
				append script_message [format "Script Info:: change clock net from %s => %s in {%s} ...\n" $one_clock $new_clock_name $each_clock_area]
				#lappend meshnet_list $new_clock_name
				set meshnet($new_clock_name)	$meshnet($one_clock)
				set all_mesh_shapes [get_net_shapes -of_objects [get_nets -segments $one_clock] -within $each_clock_area]
				set all_via_shapes  [get_vias -of_objects [get_nets -segments $one_clock] -within $each_clock_area]
				create_port -direction [get_attribute [get_ports $one_clock] direction] $new_clock_name
				### create new clock
				create_clock -name $new_clock_name -period [get_attribute [get_clocks $one_clock] period] [get_ports $new_clock_name]
				set_dont_touch_network  [get_clocks $new_clock_name]
                        	set_clock_uncertainty -setup    [get_attribute [get_clocks $one_clock] setup_uncertainty] [get_clocks $new_clock_name]
                        	set_clock_uncertainty -hold     [get_attribute [get_clocks $one_clock] hold_uncertainty]  [get_clocks $new_clock_name]
                        	set_clock_transition            [get_attribute [get_clocks $one_clock] clock_transition_rise_max] [get_clocks $new_clock_name]
				create_net $new_clock_name
				connect_net [get_nets $new_clock_name] [get_ports $new_clock_name]
				set_attribute $all_mesh_shapes owner_net [get_nets $new_clock_name]
				set_attribute $all_via_shapes owner_net [get_nets $new_clock_name]
				set all_clock_regs [get_cells -of_objects [get_nets -segments $one_clock] -filter {is_hierarchical==false}]
				set efficient_regs [remove_from_collection -intersect \
					[add_to_collection [get_cells -within $each_clock_area] [get_cells -intersect $each_clock_area]] \
					$all_clock_regs]
				set efficient_clock_pins [remove_from_collection -intersect [get_pins -of_objects $efficient_regs] [get_pins -of_objects [get_nets -segments $one_clock]]]
				#change_connection -net [get_nets $new_clock_name] $efficient_clock_pins
                                foreach_in_collection one_eff_pin $efficient_clock_pins {
                                        disconnect_net [get_nets -of_object $one_eff_pin] $one_eff_pin
                                        connect_pin -from $one_eff_pin -to [get_port $new_clock_name] -port_name $new_clock_name
                                }
				#set one_clock_top_layer [lindex $clock_list($one_clock) 4]
				set one_clock_top_layer $meshnet($new_clock_name)
				#set mesh_trunk_shapes [get_net_shapes -of_objects [get_nets -segments $new_clock_name] -filter "route_type==\"Clk Strap\" && layer==$one_clock_top_layer"]
				set mesh_trunk_shapes [get_net_shapes -of_objects [get_nets -segments $new_clock_name] \
							-filter [subst {route_type=="Clk Strap" && layer==$one_clock_top_layer}]]
				set mesh_trunk_medium [index_collection $mesh_trunk_shapes [expr {[sizeof_collection $mesh_trunk_shapes]/2}]]
                                if {[sizeof_collection [get_terminals -quiet -within $each_clock_area "$one_clock\\ *"]]>0} {
                                        foreach_in_collection one_org_term [get_terminals -quiet -within $each_clock_area "$one_clock\\ *"] {
						set new_clock_bbox 	[get_attribute $one_org_term bbox]
						set new_clock_layer	[get_attribute $one_org_term layer]
                                                #set_attribute $one_org_term name $new_clock_name
                                                #set_attribute $one_org_term owner_port $new_clock_name
						#set_port_location -coordinate $new_clock_center \
								#-layer_name [get_attribute [get_terminals $new_clock_name] layer] \
								#-layer_area [join [get_attribute [get_terminals $new_clock_name] bbox]] \
								#$new_clock_name
						remove_terminal $one_org_term
						create_terminal -bbox $new_clock_bbox -layer $new_clock_layer -port [get_port $new_clock_name]
                                        }
					#set_port_location -coordinate [get_attribute [get_ports $new_clock_name] center] -append $new_clock_name
                                } else {
                                        create_terminal -bbox [get_center_square [get_attribute $mesh_trunk_medium bbox]] -layer $one_clock_top_layer -port [get_port $new_clock_name]
                                }
				mark_clock_tree -clock_trees $new_clock_name -clock_synthesized
				set_ideal_network [get_ports $new_clock_name]
				### clean variables
				incr name_index 1
				incr total_changed_mesh 1
				unset -nocomplain new_clock_name all_mesh_shapes all_via_shapes \
						all_clock_regs efficient_regs efficient_clock_pins \
						one_clock_top_layer mesh_trunk_shapes mesh_trunk_medium
			}
		}
	}
	if {[info exists script_message]} {
		echo $script_message
		echo $script_message > mesh_split_net.rpt
	}
	extract_rc
	update_nhp_clockdefine
	return $total_changed_mesh
}
##################################################################################################
###	PT: report analysis vio nums
##################################################################################################
proc report_analysis_vio_nums {} {
	foreach_in_collection one_group [get_path_groups] {
	        regsub -all -- {\*} [get_attribute $one_group full_name] "" cur_group_name
	        regsub -all -- {\/} $cur_group_name _ cur_group_name
	        if {[sizeof_collection [get_timing_paths -group $one_group]]>0} {
	                set vio_paths($cur_group_name)   [list \
	                                                [get_attribute [get_timing_paths -group $one_group -delay_type max -slack_lesser_than 1000000 -max_paths 1] slack] \
	                                                [sizeof_collection [get_timing_paths -group $one_group -delay_type max -slack_lesser_than 0 -max_paths 1000000]] \
	                                                [get_attribute [get_timing_paths -group $one_group -delay_type min -slack_lesser_than 1000000 -max_paths 1] slack] \
	                                                [sizeof_collection [get_timing_paths -group $one_group -delay_type min -slack_lesser_than 0 -max_paths 1000000]]]
	        } else {
	                set vio_paths($cur_group_name)   -----
	        }
	}
        set max_name_length 0
        foreach key [array name vio_paths] {
                if {[string length $key]>$max_name_length} {
                        set max_name_length [string length $key]
                }
        }
        puts [string repeat = [expr {$max_name_length+52}]]
        puts [format "| %-${max_name_length}s |%13s|%9s|%13s|%9s|" "Path Group" "WorstMaxSlack" "MaxVioNum" "WorstMinSlack" "MinVioNum"]
        puts [string repeat = [expr {$max_name_length+52}]]
        foreach key [lsort [array name vio_paths]] {
                set value $vio_paths($key)
                set cmd_print {}
                if {[llength $value]==4} {
			if {[string equal [lindex $value 0] {}]} {
                        	set cmd_print "puts \[format \"| \%-${max_name_length}s | \%11s | \%7d | \%11.3f | \%7d |\" \$key \[lindex \$value 0\] \[lindex \$value 1\] \[lindex \$value 2\] \[lindex \$value 3\]\]"
			} elseif {[string equal [lindex $value 2] {}]} {
                        	set cmd_print "puts \[format \"| \%-${max_name_length}s | \%11.3f | \%7d | \%11s | \%7d |\" \$key \[lindex \$value 0\] \[lindex \$value 1\] \[lindex \$value 2\] \[lindex \$value 3\]\]"
			} else {
                        	set cmd_print "puts \[format \"| \%-${max_name_length}s | \%11.3f | \%7d | \%11.3f | \%7d |\" \$key \[lindex \$value 0\] \[lindex \$value 1\] \[lindex \$value 2\] \[lindex \$value 3\]\]"
			}
                } else {
                        set cmd_print "puts \[format \"| \%-${max_name_length}s | \%11s | \%7s | \%11s | \%7s |\" \$key \$value \$value \$value \$value\]"
                }
                eval $cmd_print
                puts [string repeat - [expr {$max_name_length+52}]]
        }
}
##################################################################################################
###	check_change_current_cel
##################################################################################################
proc check_change_current_cel {design_name} {
	set current_cel_name [get_attribute [current_mw_cel] name]
	if {![string equal $current_cel_name $design_name]} {
		puts [format "Script Info:: Now save&&change cel from %s => %s .." $current_cel_name $design_name]
		save_mw_cel -as $design_name
		close_mw_cel
		open_mw_cel $design_name
		current_mw_cel
	}
}
##################################################################################################
###	MCMM AUTO WEIGHTS
##################################################################################################
proc my_proc_auto_weights {} {
	if {[all_scenarios]!={}} {
		set cur_scenario		[current_scenario]
		set all_active_scenarios	[all_active_scenarios]
		set all_setup_scenarios [get_scenarios -setup true]
		foreach scenario $all_active_scenarios {
			if { [lsearch -ascii $all_setup_scenarios $scenario] >= 0 } {
				set_active_scenario $scenario
				#current_scenario $scenario
				proc_auto_weights -wns
			}
		}
		set_active_scenario $all_active_scenarios
		current_scenario $cur_scenario
	} else {
		proc_auto_weights -wns
	}
}
##################################################################################################
###	auto size cell from ** to **, base on slack **
###	example : auto_cmd_resize_cel STL STN 0.020
##################################################################################################
proc auto_cmd_resize_cell_by_paths {from_title to_title {slack 0.020} {eval 0}} {
	array unset inst_to_change
	array unset inst_map
	set timing_paths [get_timing_paths -slack_greater_than $slack -nworst 100 -max_paths 10000]
	puts "get_timing_paths done!"
	set found [filter_collection [get_attribute [get_attribute $timing_paths points] object] ref_name=~${from_title}*]
	if {[sizeof_collection $found]>0} {
		puts [format "found : %d" [sizeof_collection $found]]
		foreach_in_collection one $found {
			set cur_cell	[get_attribute $one full_name]
			set cur_ref	[get_attribute $one ref_name]
			regsub -- "^$from_title" $cur_ref $to_title new_ref
			set cur_slack [lindex [lsort -real [get_attribute [get_timing_paths  -through [get_pins -of_objects [get_cells $one]]] slack]] 0]
			set cmd [format "size_cell %s\t%s\t; #org : %s, slack : %s" $cur_cell $new_ref $cur_ref $cur_slack]
			echo $cmd
			if {$eval} {
				eval $cmd
			}
		}
	} else {
		puts [format "nothing found : ^_^"]
	}
}
proc auto_cmd_resize_cell_one_by_one {from_title to_title {slack 0.020} {eval 0}} {
	array unset inst_to_change
	array unset inst_map
	set instances [get_cells -filter "ref_name=~${from_title}*"]
	set total_num [sizeof_collection $instances]
	set flag_i	0 
	set flag_f	0
	foreach_in_collection one $instances {
		incr flag_i 1
		set cur_cell	[get_attribute $one full_name]
		set cur_ref	[get_attribute $one ref_name]
		regsub -- "^$from_title" $cur_ref $to_title new_ref
		set cur_slack [lindex [lsort -real [get_attribute [get_timing_paths  -through [get_pins -of_objects [get_cells $one]]] slack]] 0]
		if {$cur_slack > $slack} {
			set inst_to_change($cur_cell)	$cur_slack
			set inst_map($cur_cell,org)	$cur_ref
			set inst_map($cur_cell,new)	$new_ref
			incr flag_f 1
		}
		echo [format "%10d:%-10d .. %10d" $total_num $flag_i $flag_f]
	}
	foreach each [array name inst_to_change] {
		set cmd [format "size_cell %s\t%s\t; #org : %s, slack : %s" $each $inst_map($each,new) $inst_map($each,org) $inst_to_change($each)]
		echo $cmd
		if {$eval} {
			eval $cmd
		}
	}
}
##################################################################################################
###	create size_cell command, only for current scenario
###	example : title_list : {{STM STN} {STP STN} {STN STL}}
##################################################################################################
proc auto_cmd_size_cell {type group slack title_list {eval 0} {spec_paths {}}} {
	array unset inst_name_map
	array unset inst_name_list
	upvar 1 synopsys_program_name cur_shell_name
	if {[sizeof_collection $spec_paths]>0} {
		set timing_paths $spec_paths
	} else {
		set timing_paths [get_timing_paths -delay_type $type -group $group -slack_lesser_than $slack -nworst 100 -max_paths 10000]
	}
	foreach_in_collection tp $timing_paths {
		set find_sub 0
		foreach one_pair $title_list {
			set tp_i 0
			lassign $one_pair pair_from pair_to
			set path_list {}
			if {$cur_shell_name == "icc_shell"} {
				set path_list [get_attribute [filter_collection [get_attribute [get_attribute $tp points] object] pin_direction==out] cell_name]
				if {[regexp -- {_reg} [lindex $path_list 0]]} {
					set path_list [lrange $path_list 1 end]
				}
			} elseif {$cur_shell_name == "pt_shell"} {
				set path_list [get_attribute [get_cells -of_objects [filter_collection [get_attribute [get_attribute $tp points] object] pin_direction==out]] full_name]
				if {[regexp -- {_reg} [lindex $path_list 0]]} {
					set path_list [lrange $path_list 1 end]
				}
			} else {
				puts "this command only support 'icc_shell' and 'pt_shell'."
				return
			}
			if {[string equal $type max]} {
				set cell_inst_list [my_lreverse $path_list]
			} elseif {[string equal $type min]} {
				set cell_inst_list $path_list
			} else {
				puts "type only support 'max' or 'min'"
				return
			}
			foreach cell_inst_name $cell_inst_list {
				if {$tp_i>0} {
					set cell_ref_org	[get_attribute [get_cells $cell_inst_name] ref_name]
					set cell_sub  $cell_ref_org
					if {[regsub -- "^$pair_from" $cell_sub $pair_to cell_new]} {
						if {![info exists inst_name_list($cell_inst_name)]} {
							set inst_name_list($cell_inst_name)	1
							set inst_name_map($cell_inst_name,org)	$cell_ref_org
							set inst_name_map($cell_inst_name,new)	$cell_new
						}
						set find_sub 1
						break
					}
				}
				incr tp_i 1
			}
			if {$find_sub>0} { break }
		}
	}
	foreach inst [lsort [array name inst_name_list]] {
		set cmd [format "size_cell %-40s %-20s\t\t; # org : %s" $inst $inst_name_map($inst,new) $inst_name_map($inst,org)]
		echo $cmd
		if {$eval} { eval $cmd }
	}
	if {$eval} {
		if {$cur_shell_name == "icc_shell"} {
			echo [get_qor_summary]
		}
		if {$cur_shell_name == "pt_shell"} {
			report_analysis_vio_nums
		}
	}
}

proc my_lreverse {ll} {
	set re {}
	while {[llength $ll]>0} {
		lappend re [lindex $ll end]
		set ll [lrange $ll 0 end-1]
	}
	return $re
}
##################################################################################################
###	auto apply non-default routing rule
##################################################################################################
proc auto_widen_critical_nets {rule_name width_list spacing_list apply_all {timing_slack 0}} {
	puts [format "Script Info:: Create Non-default routing rule: %s" $rule_name]
	set CMD_DEFINE_NDR "define_routing_rule -default_reference_rule"
	set defined_ndr	0
	if {[llength $width_list]>0} {
		lappend CMD_DEFINE_NDR "-widths"
		lappend CMD_DEFINE_NDR "$width_list"
		incr defined_ndr 1
	}
	if {[llength $spacing_list]>0} {
		lappend CMD_DEFINE_NDR "-spacings"
		lappend CMD_DEFINE_NDR "$spacing_list"
		incr defined_ndr 1
	}
	if {$defined_ndr>0} {
		lappend CMD_DEFINE_NDR $rule_name
	} else {
		puts [format "Script Info:: Must define \"var(widen_cr_nets,width)\" or \"var(widen_cr_nets,spacing)\"! No NDR is created,skip!"]
		return
	}
	echo $CMD_DEFINE_NDR
	eval $CMD_DEFINE_NDR
	report_routing_rules
	if {$apply_all} {
		set_net_routing_rule -rule $rule_name [get_nets -segments]
		puts [format "Script Info:: Apply Non-default routing rule(%s) for all nets!" $rule_name]
	} else {
		if {[all_scenario]!={}} {
			set timing_paths [get_timing_paths -slack_lesser_than $timing_slack -nworst 5 -max_paths 10000000 -scenarios [all_active_scenarios]]
		} else {
			set timing_paths [get_timing_paths -slack_lesser_than $timing_slack -nworst 5 -max_paths 10000000]
		}
		set used_nets [get_nets -of_objects [get_attribute [get_attribute $timing_paths points] object]]
		set_net_routing_rule -rule $rule_name $used_nets
		puts [format "Script Info:: Apply Non-default routing rule(%s) for %d/%d selected nets!" $rule_name [sizeof_collection $used_nets] [sizeof_collection [get_nets -segments]]]
	}
}
##################################################################################################
###	get minimum pin depth
##################################################################################################
proc get_minimum_used_pin_depth {metal_list} {
	set minimum_value 0
	puts [format "Script Info:: %-6s %-s" Layer min-depth]
	puts [string repeat - 35]
	foreach one $metal_list {
		set cur_min_area	[get_attribute [get_layers $one] minArea]
		set cur_min_width	[get_attribute [get_layers $one] defaultWidth]
		set cur_pitch		[get_attribute [get_layers $one] pitch]
		set cur_depth		[expr {(int($cur_min_area/($cur_pitch*$cur_min_width))+1)*$cur_pitch}]
		puts [format "Script Info:: %-6s %-2.3f" $one $cur_depth]
		if {$minimum_value<$cur_depth} { set minimum_value $cur_depth }
	}
	puts [string repeat - 35]
	puts [format "Script Info:: use %-2.3f as pin min-depth." $minimum_value]
	return $minimum_value
}
##################################################################################################
###	get endpoints for focalopt, base on define path_groups
##################################################################################################
proc get_focal_opt_timing_cons {type group} {
        # type must be 'max_delay' or 'min_delay'
	array unset selected_group
	foreach one_group [get_object_name [get_path_groups -quiet $group]] {
		set selected_group($one_group) 1
	}
	set cur_copy 0
	set cur_cont 0
        redirect -variable cur_cons {report_constraint -$type -all_violators -significant_digits 3 -nosplit}
	set file_name "focal_opt.${type}.endpoints.[clock seconds]"

	set fileId [open_f $file_name w]
	foreach one_line [split $cur_cons \n] {
		if {[regexp -- {\('(\S+?)'\s+group\)} $one_line match matched_group]} {
			if {[info exists selected_group($matched_group)]} {
				set cur_copy 1
			}
			continue
		}
		if {$cur_copy==1 && [regexp -- {^\s*-+\s*$} $one_line match]} {
			set cur_copy 2
			continue
		}
		if {$cur_copy==2 && [regexp -- {VIOLATED} $one_line match]} {
			puts $fileId $one_line
			incr cur_cont 1
			continue
		}
		if {$cur_copy==2 && [regexp -- {^\s*$} $one_line match]} {
			set cur_copy 0
		}
	}
	close $fileId
	if {$cur_cont==0} {
		return all
	} else {
		puts [format "Script Info:: create file : %s , for focal_opt : %s , base on group : \"%s\"" $file_name $type $group]
		return $file_name
	}
}
##################################################################################################
###	get file for focalopt, base on report_net_delta_delay
##################################################################################################
proc get_focal_opt_xtalk_cons {margin} {
	redirect -variable rpt_delta_delay {report_net_delta_delay}
	set file_name "focal_opt.xtalk.[clock seconds]"
	set fileId [open_f $file_name w]
	foreach one_line [split $rpt_delta_delay \n] {
		if {[regexp -- {Net:(\S+).+?max\s+(\S+)\s+min\s+(\S+)} $one_line match net max min]} {
			if {[expr {abs($max)}]>$margin || [expr {abs($min)}]>$margin} {
				#echo [format "%s\t%f\t%f" $net $max $min]
				puts $fileId [format "%s\t%f\t%f" $net $max $min]
			}
		}
	}
	close $fileId
	return $file_name
}

##################################################################################################
###	check size_cell file
##################################################################################################
proc my_check_size_cell_file {file} {
	set fileId [open_f $file r]
	set diff_num 0
	set total_num 0
	foreach one_line [split [read $fileId] \n] {
		if {[regexp -- {size_cell\s+\{(\S+?)\}\s+\{(\S+?)\}} $one_line match inst new_name]} {
			set org_name [get_attribute [get_cells $inst] ref_name]
			if {![string equal [string range $org_name 4 end] [string range $new_name 4 end]]} {
				puts [format "%-30s\t%-15s => %-15s" $inst $org_name $new_name]
				incr diff_num 1
			}
			incr total_num 1
		}
	}
	close $fileId
	puts [string repeat = 80]
	puts [format "\[%d/%d\]" $diff_num $total_num]
}
##################################################################################################
###	report && check each timing points
##################################################################################################
proc report_timing_detail {param} {
	set report_cmd	[concat {report_timing -transition_time -input_pins} $param ]
	set get_cmd	[concat get_timing_paths $param]
	eval $report_cmd
	set p_c	[eval $get_cmd]
	foreach_in_collection one $p_c {
		set max_point_length 0
		set max_cell_length 0
		foreach_in_collection point [filter_collection [get_attribute [get_attribute $one points] object] pin_direction==out] {
			set cur_length [string length [get_attribute $point full_name]]
			set cur_cell [string length [get_attribute [get_cells [get_attribute $point cell_name]] ref_name]]
			if {$cur_length > $max_point_length} { set max_point_length $cur_length }
			if {$cur_cell > $max_cell_length} { set max_cell_length $cur_cell }
		}
		set max_split_length [expr {$max_point_length+$max_cell_length+33}]
		puts [string repeat = $max_split_length]
		puts [format "From  : \t%s" [get_attribute [get_attribute $one startpoint] full_name]]
		puts [format "To    : \t%s" [get_attribute [get_attribute $one endpoint] full_name]]
		puts [format "Slack : \t%.3f" [get_attribute $one slack]]
		puts [string repeat - $max_split_length]
		puts [format "| %-${max_point_length}s | %-${max_cell_length}s | %10s | %10s |" Instance Cell MAX_SLACK MIN_SLACK]
		puts [string repeat - $max_split_length]
		foreach_in_collection point [filter_collection [get_attribute [get_attribute $one points] object] pin_direction==out] {
			puts [format "| %-${max_point_length}s | %-${max_cell_length}s | %10.3f | %10.3f |" [get_attribute $point full_name] \
					[get_attribute [get_cells [get_attribute $point cell_name]] ref_name] \
					[lindex [lsort -real [get_attribute [get_timing_paths -through $point -delay_type max] slack]] 0] \
					[lindex [lsort -real [get_attribute [get_timing_paths -through $point -delay_type min] slack]] 0]]
		}
		puts [string repeat - $max_split_length]
	}
}
##################################################################################################
###	get site row information
##################################################################################################
proc get_default_site_row {} {
	return [lindex [join [convert_from_polygon -format rectangle [get_attribute [get_mw_cels unitTile] pr_boundary]]] end]
}
##################################################################################################
###	check routing rule
##################################################################################################
proc my_check_routing_rules {rule} {
        redirect -variable rpt_routing_rule {report_routing_rules $rule}
	return [regexp -line -- "$rule" $rpt_routing_rule]
}
##################################################################################################
###	get_lcm : Get Least Common Multiple, all elements must be positive number.
##################################################################################################
proc get_commons { list1 list2 } {
	set rvalue 1
	set list1 [lsort -real $list1]
	set list2 [lsort -real $list2]
	foreach each1 $list1 {
		if { $each1 in $list2 } {
			set cur_i [lsearch -exact $list2 $each1]
			set list2 [lreplace $list2 $cur_i $cur_i X]
			set rvalue [expr {$rvalue*$each1}]
		}
	}
	return $rvalue
}

### step must start from 2 :
proc get_divisor { value step } {
	set rlist { }
	if {$step>$value} {
		if {[llength $rlist]==0} { lappend rlist 1 }
		return $rlist
	}
	if {[expr {$value%$step}]} {
		incr step 1
		set rlist [concat $rlist [get_divisor $value $step]]
	} else {
		lappend rlist $step
		set rlist [concat $rlist [get_divisor [expr {$value/$step}] $step]]
	}
	return $rlist
}
### Get Least Common Multiple, all elements must be positive number.
proc get_lcm { value_list } {
	set m_factor 1.0
	foreach one $value_list {
		scan [expr $one*1.0] %d.%d var_integer var_decimal
		set cur_mf [expr pow(10,[string length [string trimright $var_decimal 0]])]
		if {$cur_mf > $m_factor} { set m_factor $cur_mf }
	}
	set all_list { }
	foreach one $value_list { lappend all_list [expr int($one*$m_factor)] }
	set ele_used	[lindex $all_list 0]
	foreach ele_each [lrange $all_list 1 end] {
		set ele_used [expr {$ele_used*$ele_each/[get_commons [get_divisor $ele_used 2] [get_divisor $ele_each 2]]}]
	}
	return [expr {$ele_used/$m_factor}]
}
##################################################################################################
###	create inter-clock path groups
##################################################################################################
proc create_path_groups_between_clocks {collections} {
	set flag_start        [clock seconds]
	set local_objs	{}
	set CMD_GROUPS	{}
	foreach_in_collection one $collections {
		if {[sizeof_collection [get_attribute -quiet $one sources]]>0} {
			append_to_collection local_objs $one
		}
	}
	foreach_in_collection clock_from $local_objs {
		set name_from	[get_object_name $clock_from]
		foreach_in_collection clock_to $local_objs {
			set name_to	[get_object_name $clock_to]
			if {[string equal $name_from $name_to]} {
				continue
			} else {
				if {[sizeof_collection [get_path_groups -quiet ${name_from}=>$name_to]]==0} {
					if {[sizeof_collection [get_timing_paths -from $clock_from -to $clock_to]]>0} {
						#group_path -name ${name_from}=>$name_to -from $clock_from -to $clock_to
						lappend CMD_GROUPS "group_path -name ${name_from}=>$name_to -from \[get_clocks $name_from\] -to \[get_clocks $name_to\]"
					}
				}
			}
		}
	}
	foreach one_cmd $CMD_GROUPS {
		eval $one_cmd
	}
	set flag_stop        [clock seconds]
	puts [format "Script Info:: Auto create path groups between clocks, cost : %s" \
		[clock format [expr $flag_stop - $flag_start] -format %H:%M:%S -gmt true]]
}
##################################################################################################
###	create VDD/VSS text label
##################################################################################################
proc create_pg_text_by_cell {cell_obj label_list metal_layer text_layer} {
	foreach_in_collection one [get_pin_shapes -of_objects $cell_obj -filter "layer==$metal_layer"] {
		set cur_name	[get_attribute $one name]
		set cur_point	[get_attribute $one bbox_ll]
		if {$cur_name in $label_list && [sizeof_collection [get_text -quiet -filter "text==$cur_name"]]==0} {
			create_text -origin $cur_point -layer $text_layer $cur_name
		}
	}
}
##################################################################################################
###	check whether have clock gating cells
##################################################################################################
proc get_clock_gating_cell_nums {} {
        redirect -variable rpt_clock_gating {report_clock_gating}
	set number_of_cg_cell 0
        foreach one_line [split $rpt_clock_gating "\n"] {
                if {[regexp -- {\|\s*Number of Clock gating elements\s*\|\s*(\d+)\s*\|} $one_line match nums]} {
			set number_of_cg_cell $nums
                }
	}
	return $number_of_cg_cell
}
##################################################################################################
###	check whether common setting files have been loaded.
##################################################################################################
proc check_load_setting {file key} {
	upvar #0 nhp_predefine predefine
	set value_return 0
	if {![dict exists $predefine $key]} {
		puts [format "Script %s:: common setting key '%s' error, not support!" [string totitle error] $key]
	}
	if {[file isfile $file] && ![dict get $predefine $key]} {
		set value_return 1
	}
	return $value_return
}
##################################################################################################
###     extend P/G net shapes
##################################################################################################
proc extend_pg_strap {path_obj {fd_dla 0} {bd_dla 0} {debug 0}} {
        set cur_points [get_attribute $path_obj points]
        if {[llength $cur_points]!=2} {
                puts [format "Script %s:: 'extend_pg_strap' for '%s' on layer '%s' at point '%s' doesn't support ,skip!" \
                        [string totitle error] [get_attribute $path_obj owner_net] \
                        [get_attribute $path_obj layer] [get_attribute $path_obj points]]
                return
        }
        lassign [join $cur_points] fd_x fd_y bd_x bd_y
        if {$fd_x==$bd_x} {
        ### vertical direction
                set new_points [list [list $fd_x [expr {$fd_y-$fd_dla}]] [list $bd_x [expr {$bd_y+$bd_dla}]]]
        } elseif {$fd_y==$bd_y} {
        ### horizontal direction
                set new_points [list [list [expr {$fd_x-$fd_dla}] $fd_y] [list [expr {$bd_x+$bd_dla}] $bd_y]]
        } else {
                puts [format "Script %s:: 'extend_pg_strap' for '%s' on layer '%s' at point '%s', format Error!!" \
                        [string totitle error] [get_attribute $path_obj owner_net] \
                        [get_attribute $path_obj layer] [get_attribute $path_obj points]]
                return
        }
        if {$debug>0} {
                echo "set_attribute $path_obj points {$new_points}"
        } else {
                set_attribute $path_obj points $new_points
        }
}
##################################################################################################
###     show error messages
##################################################################################################
proc check_show_messages {key} {
	redirect -variable ms_info {print_message_info}
	unset -nocomplain ms_dict
	set split_n 80
	#set color_head "\033\[0m"
	#set color_tail "\033\[0m"
	if {[string equal $key Error]} {
		set color_head "\033\[31m"
	}
	foreach one_line [split $ms_info \n] {
		if {[regexp -- "(\\S+)\\s+$key\\s+(\\d+)\\s+(\\d+)" $one_line match ms_id ms_l ms_o]} {
			dict set ms_dict $ms_id Limit $ms_l
			dict set ms_dict $ms_id Occurrences $ms_o
		}
	}
	if {[info exists ms_dict] && [dict size $ms_dict]>0} {
		echo [string repeat - $split_n]
		puts [format "%-10s %-10s %-10s %-12s : %s" Id Severity Limit Occurrences implication]
		echo [string repeat - $split_n]
		foreach each_ids [lsort [dict keys $ms_dict]] {
			puts [format "%-10s %-10s %-10s %-12s : %s" $each_ids $key \
				[dict get $ms_dict $each_ids Limit] \
				[dict get $ms_dict $each_ids Occurrences] \
				[regsub -- {\n} [lindex [regexp -inline -- {\{(.+?)\}} [get_message_info -id $each_ids]] 1] ""]]
		}
		echo [string repeat - $split_n]
	}
}

##################################################################################################
###     check placement legality.
##################################################################################################
proc check_placement_legality {rpt_file} {
	check_legality -verbose > $rpt_file
	if {[lindex [regexp -inline -- {occurrences\s+(\d+)} [get_message_info -id PSYN-215]] 1]>0} {
        	puts [format "Script %s:: Fail in placement! Detail plz see : %s" [string totitle error] $rpt_file]
        	exit
	}
}
##################################################################################################
###     set max transition for clock trees
##################################################################################################
proc set_clock_tree_transition {name period f_trunk f_leaf tran_region} {
	set value_trunk	[expr {$period*$f_trunk}]
	set value_leaf	[expr {$period*$f_leaf}]
	if {$value_trunk<[lindex $tran_region 1] && $value_trunk>=[lindex $tran_region 0]} {
        	set_clock_tree_options -clock_trees $name -max_transition $value_trunk
	} elseif {$value_trunk<[lindex $tran_region 0]} {
        	set_clock_tree_options -clock_trees $name -max_transition [lindex $tran_region 0]
	} else {
		### use default value.
	}
	if {$value_leaf<[lindex $tran_region 1] && $value_leaf>=[lindex $tran_region 0]} {
        	set_clock_tree_options -clock_trees $name -leaf_max_transition $value_leaf
	} elseif {$value_leaf<[lindex $tran_region 0]} {
        	set_clock_tree_options -clock_trees $name -leaf_max_transition [lindex $tran_region 0]
	} else {
		### use default value.
	}
}
##################################################################################################
###     create wire cap/fanout report
###	usage : report_wire_caps [limit_report(integer)] [threshold_cap(pf)]
###	example:
###		report_wire_caps	; # equal to : report_wire_caps 0 0
###		report_wire_caps 100 0.050
##################################################################################################
proc report_wire_caps {report_file {zip_file 0}} {
	set phase_start [clock seconds]
	set dict_wire_tree {}
	set dict_wire_attr {}
	lassign [list 0 0 0 0 0 0] max_wire_cap max_wire_length max_out max_in max_inout max_unknow
	set name_maximum_cap {}
	set name_maximum_length {}
	set name_maximum_out {}
	set name_maximum_in {}
	set name_maximum_inout {}
	set name_maximum_unknow {}
	set all_flat_nets [get_flat_nets]
	set total_nets	[sizeof_collection $all_flat_nets]
	set loop_flag	0
	set cur_per	0
	set last_per	0
	set limit_mark	0
	unset -nocomplain metal_map
	# extract layer map
	foreach_in_collection one_layer [get_layers -filter {is_routing_layer==true && mask_name=~metal*}] {
		if {[regexp -- {metal(\d+)} [get_attribute $one_layer mask_name] match index]} {
			set metal_map([get_attribute $one_layer name]) $index
		}
	}
	#foreach_in_collection one [get_flat_nets -filter "wire_capacitance_max>=$threshold_cap"]
	foreach_in_collection one [get_flat_nets] {
		incr loop_flag 1
		set cur_per [expr {int($loop_flag*10/$total_nets)}]
		if {$cur_per!=$last_per} {
			set last_per $cur_per
			puts -nonewline .
			flush stdout
		}
		lassign [list 0 0 0 0] num_out num_in num_inout num_unknow
		set cur_wire_name	[get_attribute $one full_name]
		set cur_wire_cap	[get_attribute -quiet $one wire_capacitance_max]
		set cur_wire_length	[join [get_attribute -quiet $one route_length]]
		set cur_wire_layers	{}
		set cur_name_layers	{}
		set cur_wire_totallength 0
		if {$cur_wire_length!=0 && [llength $cur_wire_length]>0} {
			foreach one_ll $cur_wire_length {
				lappend cur_wire_layers [list [lindex $one_ll 0] $metal_map([lindex $one_ll 0])]
				set cur_wire_totallength [expr {$cur_wire_totallength+[lindex $one_ll 1]}]
			}
			set cur_wire_layers [lsort -integer -index 1 $cur_wire_layers]
			set cur_wire_1st_layer	[lindex [lindex $cur_wire_layers 0] 0]
			set cur_wire_loop_index	[lindex [lindex $cur_wire_layers 0] 1]
			set cur_wire_one_last	$cur_wire_1st_layer
			set cur_wire_end_layer	$cur_wire_1st_layer
			set cur_wire_zip	$cur_wire_1st_layer
			foreach one_ll [lrange $cur_wire_layers 1 end] {
				set cur_loop_name [lindex $one_ll 0]
				set cur_loop_idx  [lindex $one_ll 1]
				if {$cur_loop_idx!=$cur_wire_loop_index+1} {
					if {[string equal $cur_wire_1st_layer $cur_wire_end_layer]} {
						append cur_wire_zip ",$cur_loop_name"
						set cur_wire_1st_layer $cur_loop_name
					} else {
						append cur_wire_zip "~$cur_wire_end_layer,$cur_loop_name"
					}
					set cur_wire_one_last $cur_loop_name
				}
				set cur_wire_loop_index $cur_loop_idx
				set cur_wire_end_layer	$cur_loop_name
			}
			if {![string equal $cur_wire_one_last $cur_wire_end_layer]} {
					append cur_wire_zip "~$cur_wire_end_layer"
			}
			dict set dict_wire_attr $cur_wire_name	route_length	$cur_wire_totallength
			dict set dict_wire_attr $cur_wire_name	route_layers	$cur_wire_zip
			if {$max_wire_length<$cur_wire_totallength} {
				set max_wire_length $cur_wire_totallength
				set name_maximum_length $cur_wire_name
			}
		} else {
			dict set dict_wire_attr $cur_wire_name	route_length	0
			dict set dict_wire_attr $cur_wire_name	route_layers	""
		}
		if {[llength $cur_wire_cap]==0} { set cur_wire_cap 0 }
		set cur_pin_directions	[get_attribute -quiet [get_flat_pins -of_objects $one] direction]
		set num_out		[llength [lsearch -inline -all $cur_pin_directions out]]
		set num_in		[llength [lsearch -inline -all $cur_pin_directions in]]
		set num_inout		[llength [lsearch -inline -all $cur_pin_directions inout]]
		set num_unknow		[llength [lsearch -inline -all $cur_pin_directions unknow]]
		if {$num_out>$max_out} { set max_out $num_out ; set name_maximum_out $cur_wire_name}
		if {$num_in>$max_in} { set max_in $num_in ; set name_maximum_in $cur_wire_name}
		if {$num_inout>$max_inout} { set max_inout $num_inout ; set name_maximum_inout $cur_wire_name}
		if {$num_unknow>$max_unknow} { set max_unknow $num_unknow ; set name_maximum_unknow $cur_wire_name}
		if {$cur_wire_cap>$max_wire_cap} { set max_wire_cap $cur_wire_cap ; set name_maximum_cap $cur_wire_name}
		#dict set dict_wire_tree $num_out $num_inout $num_unknow $cur_wire_name [list load $num_in wire_cap $cur_wire_cap]
		if {$num_out==0} {
			dict set dict_wire_tree input $num_out $num_inout $num_unknow $cur_wire_name [list load $num_in wire_cap $cur_wire_cap]
		} elseif {$num_in==0} {
			dict set dict_wire_tree output $num_out $num_inout $num_unknow $cur_wire_name [list load $num_in wire_cap $cur_wire_cap]
		} else {
			dict set dict_wire_tree internal $num_out $num_inout $num_unknow $cur_wire_name [list load $num_in wire_cap $cur_wire_cap]
		}
	}
	set fileId [open_f [string trim $report_file] w]
	puts ""
	puts $fileId [string repeat - 100]
	puts $fileId "Report: Maximum ..."
	puts $fileId [format "\t%-30s : %-20.6f %s" "Wire capacitance" $max_wire_cap $name_maximum_cap]
	puts $fileId [format "\t%-30s : %-20.6f %s" "Wire length" $max_wire_length $name_maximum_length]
	puts $fileId [format "\t%-30s : %-20d %s" "Num. of driver pins" $max_out $name_maximum_out]
	puts $fileId [format "\t%-30s : %-20d %s" "Num. of load pins" $max_in $name_maximum_in]
	puts $fileId [format "\t%-30s : %-20d %s" "Num. of bidirectional pins" $max_inout $name_maximum_inout]
	puts $fileId [format "\t%-30s : %-20d %s" "Num. of unknow pins" $max_unknow $name_maximum_unknow]
	puts $fileId "\n"
	foreach net_type [lsort [dict keys $dict_wire_tree]] {
		puts $fileId "[string repeat - 45][format "  %-9s" $net_type][string repeat - 44]"
		puts $fileId [format "%-10s %-10s %-10s %-10s %-10s %-15s %-15s %-10s" "driver" "bidirect" "unknow" "cap(pf)" "load" "route_length" "route_layers" "nets"]
		puts $fileId [string repeat - 100]
		foreach cur_out [lsort -real -decreasing [dict keys [dict get $dict_wire_tree $net_type]]] {
			foreach cur_inout [lsort -real -decreasing [dict keys [dict get $dict_wire_tree $net_type $cur_out]]] {
				foreach cur_unknow [lsort -real -decreasing [dict keys [dict get $dict_wire_tree $net_type $cur_out $cur_inout]]] {
					unset -nocomplain wire_pairs
					dict for {key value} [dict get $dict_wire_tree $net_type $cur_out $cur_inout $cur_unknow] {
						lappend wire_pairs [join [list $key $value]]
					}
					foreach one_pair [lsort -real -decreasing -index 4 $wire_pairs] {
						#puts $fileId [format "%-10d %-10d %-10d %-10.6f %-10d %s  %s" $cur_out $cur_inout $cur_unknow \
						#	[lindex $one_pair 4] [lindex $one_pair 2] [lindex $one_pair 0] \
						#	[dict get $dict_wire_attr [lindex $one_pair 0]]]
						puts $fileId [format "%-10d %-10d %-10d %-10.6f %-10d %-15s %-15s %s" $cur_out $cur_inout $cur_unknow \
							[lindex $one_pair 4] [lindex $one_pair 2] \
							[dict get $dict_wire_attr [lindex $one_pair 0]  route_length] \
							[dict get $dict_wire_attr [lindex $one_pair 0]  route_layers] \
							[lindex $one_pair 0]]
					}
				}
			}
		}
	}
	puts $fileId [string repeat - 100]
	set phase_end [clock seconds]
	puts $fileId [format "### cost : %d days, %s" \
        	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
        	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]]
	close $fileId
	if {$zip_file} {
		exec gzip -f $report_file
	}
}
proc count_wire_length_and_layers {wire_route_length} {
	set list_layer {}
	set total_length 0
	foreach one [join $wire_route_length] {
		lappend list_layer [lindex $one 0]
		set total_length [expr {$total_length+[lindex $one 1]}]
	}
	return [list $total_length [lsort $list_layer]]
}
#{{limit_report 0} {threshold_cap 0}}
##################################################################################################
###     create used metal spacing list.
###	<type> only support : 'spacing' or 'multiple'.
##################################################################################################
proc get_used_metal_spacing_list {{multiple 1} {type spacing}} {
	upvar #0 lib_common common
        redirect -variable rpt_ignored_layers {report_ignored_layers}
	regexp -- {Min_routing_layer:\s+(\S+).*Max_routing_layer:\s+(\S+)} $rpt_ignored_layers match layer_min layer_max
	set all_available_metals [dict get $common metal_layers all]
	set all_used_metals [lrange $all_available_metals [lsearch $all_available_metals $layer_min] [lsearch $all_available_metals $layer_max]]
	set final_rpt {}
	foreach one $all_used_metals {
		lappend final_rpt $one
		if {[string equal $type spacing]} {
			lappend final_rpt [expr {[get_attribute [get_layers $one] minSpacing]*$multiple}]
		} elseif {[string equal $type multiple]} {
			lappend final_rpt $multiple
		} else {
			puts "Error : type only support : 'spacing' or 'multiple', not $type"
			exit
		}
	}
	return $final_rpt
}
##################################################################################################
###     For DCT, check DEF information
##################################################################################################
proc check_missing_from_def {} {
        upvar #0 var(insert,endcap) insert_endcap
        upvar #0 var(insert,welltap) insert_welltap
        set value 0
        # 1 site_row
        if {[sizeof_collection [get_site_rows -quiet]]==0} { incr value}
        # 2 tracks
        if {[sizeof_collection [get_tracks -quiet]]==0} { incr value}
        # 3 unfixed macro
        set nhp_all_macros [get_flat_cells -quiet -filter {design_type==macro}]
        if {[sizeof_collection $nhp_all_macros]>0 && [sizeof_collection [filter_collection $nhp_all_macros is_fixed==false]]>0} { incr value }
        # 4 missing pg stripe
        #if {[sizeof_collection [get_shapes -quiet -filter {shape_use==stripe}]]==0} { incr value }
        # 5 missing terminals
        if {[sizeof_collection [get_terminals]]!=[sizeof_collection [get_ports]]} { incr value }
        # 6 missing boundary cell
        if {$insert_endcap && [sizeof_collection [all_physical_only_cells xoendcap*]]==0} { incr value }
        # 7 missing tapfiller welltap
        if {$insert_welltap && [sizeof_collection [all_physical_only_cells tapfiller*welltap*]]==0} { incr value }
        # 8 missing tapfiller predecap
        if {$insert_welltap && [sizeof_collection [all_physical_only_cells tapfiller*predecap*]]==0} { incr value }
        # return
        if {$value>0} {
                return 1
        } else {
                return 0
        }
}
