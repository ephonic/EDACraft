########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
###     read_in floorplan
derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
#derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {[file isfile $var(dc_dp,flag)]} {
	remove_placement -object_type standard_cell
        create_lib_track -dir [dict get $lib_common lib_track dir] \
                -offset [dict get $lib_common lib_track offset]
}
set_fp_pin_constraints -block_level -corner_keepout_num_wiretracks 20 \
		-allowed_layers [lrange [dict get $lib_common metal_layers all] \
				[lsearch [dict get $lib_common metal_layers all] [dict get $lib_common metal_layers start]] \
				[lsearch [dict get $lib_common metal_layers all] $var(top_layer)]]

set all_available_metals [dict get $lib_common metal_layers all]
set all_used_metals [lrange $all_available_metals [lsearch $all_available_metals M3] [lsearch $all_available_metals $var(top_layer)]]
set autopin_metals [dict get $lib_common metal_layers autopin]
if {[lsearch $all_available_metals $var(top_layer)]<[lsearch $all_available_metals [lindex $autopin_metals end]]} {
	set cur_top_metal_index [lsearch $all_available_metals $var(top_layer)]
	set autopin_metals [lrange $all_available_metals [expr {$cur_top_metal_index-1}] $cur_top_metal_index]
}

set_pin_physical_constraints -layers $autopin_metals -depth [get_minimum_used_pin_depth $autopin_metals] [get_ports]

if {[file isfile $var(autofp,pin_cons)]} { source -verbose -echo $var(autofp,pin_cons) }

if {[file exists $var(floorplan)]} {
        ## For floorplan file input
        puts "Script Info:: Apply Physical Constrains from $var(floorplan)"
        read_floorplan $var(floorplan)
} elseif {[llength [dict get $nhp_predefine def_exists]]>0} {
        ## For DEF floorplan input
        puts [format "Script Info:: Apply Physical Constrains from %s" [dict get $nhp_predefine def_exists]]
	read_def [dict get $nhp_predefine def_exists]
	###	set custom placement constraints
	if {[file isfile $var(place,constraints)]} {
        	source -echo -verbose $var(place,constraints)
	}
} else {
        ## For Auto floorplan input
        puts "Script Info:: Auto Floorplan"
	if {[llength $var(autofp,width,height)]>0} {
		if {$var(autofp,flip)} {
			create_floorplan -control_type width_and_height \
				-core_width [lindex $var(autofp,width,height) 0] \
				-core_height [lindex $var(autofp,width,height) 1] \
				-start_first_row -flip_first_row
		} else {
			create_floorplan -control_type width_and_height \
				-core_width [lindex $var(autofp,width,height) 0] \
				-core_height [lindex $var(autofp,width,height) 1] \
				-start_first_row
		}
	} elseif {[llength $var(autofp,ratio,util)]>0} {
		set cur_used_utilization [lindex $var(autofp,ratio,util) 1]
		if {[file isfile $var(dc_dp,flag)]} {
			set cur_used_utilization [expr {$cur_used_utilization*0.9}]
		}
		if {$var(autofp,flip)} {
			create_floorplan -control_type aspect_ratio \
				-core_aspect_ratio [lindex $var(autofp,ratio,util) 0] \
				-core_utilization $cur_used_utilization \
				-start_first_row -flip_first_row
		} else {
			create_floorplan -control_type aspect_ratio \
				-core_aspect_ratio [lindex $var(autofp,ratio,util) 0] \
				-core_utilization $cur_used_utilization \
				-start_first_row
		}
	} else {
		puts [format "Script %s:: auto-floorplan mode need at least one value of var(autofp,width,height) or var(autofp,ratio,util)." [string totitle error]]
		exit
	}
	###	set custom placement constraints
	if {[file isfile $var(place,constraints)]} {
        	source -echo -verbose $var(place,constraints)
	}
	# auto place unfixed macros
	if {[sizeof_collection [all_macro_cells]]>0 && [sizeof_collection [filter_collection [all_macro_cells] is_fixed==false]]>0} {
        	set_keepout_margin -type hard -outer {5 5 5 5} -all_macros
        	set_fp_placement_strategy -macros_on_edge auto -auto_grouping high -sliver_size 15 -congestion_effort high
        	if {[file isfile $var(place,constraints)]} { source -echo -verbose $var(place,constraints) }
        	create_fp_placement -effort high -congestion_driven
        	set_object_fixed_edit [all_macro_cells] true
        	remove_placement -object_type standard_cell
	}
        # auto create pg straps, 1st
        source -verbose [dict get $nhp_predefine autofp]
}
# check and fix def issue.
source -echo -verbose ../CMD/icc_checkfix_def.tcl

define_name_rules -remove_internal_net_bus -equal_ports_nets -inout_ports_equal_nets NAMERULE_NET_PORT_CONSISTENT
change_names -rules NAMERULE_NET_PORT_CONSISTENT

if {[file isfile $var(dc_dp,flag)]} {
	if {[file isfile ./$icc_finalopt/out/$var(design_name)_fp.def]} { file copy ./$icc_finalopt/out/$var(design_name)_fp.def DC/out }
        #update_dc_floorplan
        exit
}

