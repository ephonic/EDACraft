########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Clock Mesh script
######  Owner : Anonymous , rc
########################################################################################
###	get die size
show_current_status "s03 mesh : create clock trunk"
if {![info exists var(mesh_spacing_scalar)]} {
	set var(mesh_spacing_scalar)            1
}
set die_size_bbox [get_attribute [get_die_areas] bbox]
set die_width	[expr {[lindex $die_size_bbox 1 0]-[lindex $die_size_bbox 0 0]}]
set die_height	[expr {[lindex $die_size_bbox 1 1]-[lindex $die_size_bbox 0 1]}]
###	move all gater route guide!
set move_gater_area_route_guides 0
if {[sizeof_collection [get_route_guides -quiet GATER_ROUTE_GUIDE_*]]>0} {
	set move_gater_area_route_guides 1
	set gater_route_guide_delta_x	[expr {$die_width*2}]
	foreach_in_collection one_guide [get_route_guides -quiet GATER_ROUTE_GUIDE_*] {
		move_objects -delta "$gater_route_guide_delta_x 0" $one_guide
	}
}
set_route_zrt_common_options -single_connection_to_pins all_pins
set finished_mesh_net 0
unset -nocomplain clock_mesh_net_list clock_mesh_net_route
set clock_shield_list {}
array unset clock_pin_name_map
array unset trunk_mesh_width
echo ----------------------------------------------------------------------- > ./mesh.rpt
set clocklist_mesh      [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
foreach one_clock $clocklist_mesh {
	foreach one_root [dict get $nhp_clockdefine $one_clock root] {
		lappend clock_mesh_net_list $one_root
		set clock_pin_name_map($one_root)	$one_clock
	}
}
foreach one_mesh $clock_mesh_net_list {
	set mesh_start [clock seconds]
	if {[sizeof_collection [get_cells -quiet -of_objects [get_nets -quiet -segments $one_mesh] -filter {is_hierarchical==false}]]==0} {
		incr finished_mesh_net 1
		set mesh_end [clock seconds]
		puts [format "Script Info:: Skip floating port: %s" $one_mesh]
		echo [format "\[%02d/%02d\] cost : [clock format [expr $mesh_end - $mesh_start] -format %H:%M:%S -gmt true], trunked : %-20s %s" \
			$finished_mesh_net [llength $clock_mesh_net_list] $one_mesh "Skip floating port"] >> ./mesh.rpt
		continue
	}
	unset -nocomplain cus_num_hori_vert
	set org_mesh	$one_mesh
	#lappend clock_mesh_net_route $one_mesh
	puts [format "Script Info:: now creating mesh trunk for : %s" $one_mesh]
	if {[info exists custom_mesh_trunk_setting($one_mesh)]} {
		set cur_mesh_trunk_multiple_pitch [lindex $custom_mesh_trunk_setting($one_mesh) 0]
		if {[llength $custom_mesh_trunk_setting($one_mesh)]>1} {
			set cus_num_hori_vert	[lindex $custom_mesh_trunk_setting($one_mesh) 1]
		}
	} else {
		set cur_mesh_trunk_multiple_pitch $var(mesh_trunk_multiple_pitch)
	}
	set cur_mesh_layer [dict get $nhp_clockdefine $clock_pin_name_map($org_mesh) metal]
	##	set mesh net layer constraints
	set_net_routing_layer_constraints -min_layer_name $var(bottom_layer) -max_layer_name $cur_mesh_layer [get_nets $one_mesh]
	if {[sizeof_collection [get_net_shapes -quiet -of_objects [get_nets $one_mesh]]]>0} {
		set_object_snap_type -enabled false
		set create_mesh_info "Reform existed Clk Strap!"
		set org_one_mesh_shapes [get_net_shapes -quiet -of_objects [get_nets $one_mesh]]
		foreach_in_collection one_shape $org_one_mesh_shapes {
			set one_points	[get_attribute $one_shape points]
			set one_width	[get_attribute $one_shape width]
			set one_layer	[get_attribute $one_shape layer]
			set CMD_CR_CK_WIRE "create_net_shape -type wire -layer $one_layer -net $one_mesh -route_type clk_strap -width $one_width"
			lassign [join $one_points] one_coor_x1 one_coor_y1 one_coor_x2 one_coor_y2
			if {$one_coor_y1==$one_coor_y2} {
				### create horizontal wire
				if {$one_coor_x1<$one_coor_x2} {
					set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -origin {$one_coor_x1 $one_coor_y1}"]
				} else {
					set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -origin {$one_coor_x2 $one_coor_y2}"]
				}
				set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -length [expr {abs($one_coor_x2-$one_coor_x1)}]"]
			} else {
				### create vertical wire
				if {$one_coor_y1<$one_coor_y2} {
					set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -origin {$one_coor_x1 $one_coor_y1}"]
				} else {
					set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -origin {$one_coor_x2 $one_coor_y2}"]
				}
				set CMD_CR_CK_WIRE [concat $CMD_CR_CK_WIRE " -length [expr {abs($one_coor_y2-$one_coor_y1)}] -vertical"]
			}
			echo $CMD_CR_CK_WIRE
			eval $CMD_CR_CK_WIRE
		}
		remove_objects $org_one_mesh_shapes
		set_object_snap_type -enabled true
	} else {
		lappend clock_shield_list $one_mesh
		set change_name_mark	0
		if {[regexp -- {[\[\]]} $one_mesh]} {
			set change_name_mark 1
			regsub -all -- {[\[\]]} $one_mesh _ one_mesh
			set_name -type net -name $one_mesh [get_nets $org_mesh]
		}
		set cur_mesh_lower [lindex [dict get $nhp_predefine full_metal_list] [expr {[lsearch [dict get $nhp_predefine full_metal_list] $cur_mesh_layer]-1}]]
		if {[lsearch [dict get $nhp_predefine horizontal_metal_list] $cur_mesh_layer]>0} {
			set mesh_hori	$cur_mesh_layer
			set mesh_vert	$cur_mesh_lower
		} else {
			set mesh_hori	$cur_mesh_lower
			set mesh_vert	$cur_mesh_layer
		}
		set width_hori	[expr {[get_layer_attribute -layer $mesh_hori defaultWidth]*$cur_mesh_trunk_multiple_pitch}]
		set width_vert	[expr {[get_layer_attribute -layer $mesh_vert defaultWidth]*$cur_mesh_trunk_multiple_pitch}]
		set cur_mesh_load [get_pins -leaf -of_objects [get_nets -segments $one_mesh]]
		set cur_mesh_load_cell [get_cells -of_objects [get_nets -segments $one_mesh] -filter {is_hierarchical==false}]
		if {[sizeof_collection [get_pins -quiet -of_objects [all_macro_cells]]]>0} {
			set cur_mesh_load [remove_from_collection $cur_mesh_load [get_pins -of_objects [all_macro_cells]]]
			set cur_mesh_load_cell [remove_from_collection $cur_mesh_load_cell [all_macro_cells]]
		}
		if {[sizeof_collection $cur_mesh_load_cell]==0} {
			incr finished_mesh_net 1
			set mesh_end [clock seconds]
			puts [format "Script Info:: Skip macro loading port: %s" $one_mesh]
			echo [format "\[%02d/%02d\] cost : [clock format [expr $mesh_end - $mesh_start] -format %H:%M:%S -gmt true], trunked : %-20s %s" \
				$finished_mesh_net [llength $clock_mesh_net_list] $one_mesh "Skip macro loading port"] >> ./mesh.rpt
			continue
		}
		#set eff_bbox_llx [lindex [lindex $die_size_bbox 1] 0]
		#set eff_bbox_lly [lindex [lindex $die_size_bbox 1] 1]
		#set eff_bbox_urx [lindex [lindex $die_size_bbox 0] 0]
		#set eff_bbox_ury [lindex [lindex $die_size_bbox 0] 1]
		lassign [join $die_size_bbox] eff_bbox_urx eff_bbox_ury eff_bbox_llx eff_bbox_lly
		set eff_width	0
		set eff_height	0
		foreach cur_pin_bbox [get_attribute $cur_mesh_load bbox] {
			lassign [join $cur_pin_bbox] cur_pin_bbox_llx cur_pin_bbox_lly cur_pin_bbox_urx cur_pin_bbox_ury
			if {$eff_bbox_llx>$cur_pin_bbox_llx} {set eff_bbox_llx $cur_pin_bbox_llx}
			if {$eff_bbox_lly>$cur_pin_bbox_lly} {set eff_bbox_lly $cur_pin_bbox_lly}
			if {$eff_bbox_urx<$cur_pin_bbox_urx} {set eff_bbox_urx $cur_pin_bbox_urx}
			if {$eff_bbox_ury<$cur_pin_bbox_ury} {set eff_bbox_ury $cur_pin_bbox_ury}
		}
		set eff_width	[expr {$eff_bbox_urx - $eff_bbox_llx}]
		set eff_height	[expr {$eff_bbox_ury - $eff_bbox_lly}]
		#set def_hori_spacing [lindex $var(mesh_trunk_spacing) 0]
		#set def_vert_spacing [lindex $var(mesh_trunk_spacing) 1]
		lassign $var(mesh_trunk_spacing) def_hori_spacing def_vert_spacing
		if {[sizeof_collection [all_macro_cells]]>0} {
			if {[info exists cus_num_hori_vert]} {
				##	create mesh trunk
				create_clock_mesh -net $one_mesh \
						-layers "$mesh_hori $mesh_vert" \
						-num_straps $cus_num_hori_vert \
						-widths "$width_hori $width_vert" \
						-load $cur_mesh_load -avoid [all_macro_cells]
			} else {
				if {$def_hori_spacing>$eff_height} {
					puts [format "Script Info:: default mesh spacing between horizontal metal is changed : %s => %s" $def_hori_spacing [expr {int($eff_height)}]]
					set def_hori_spacing [expr {int($eff_height)}]
				}
				if {$def_vert_spacing>$eff_width} {
					puts [format "Script Info:: default mesh spacing between vertical metal is changed : %s => %s" $def_vert_spacing [expr {int($eff_width)}]]
					set def_vert_spacing [expr {int($eff_width)}]
				}
				set cur_used_mesh_trunk_spacing [list $def_hori_spacing $def_vert_spacing]
				##	create mesh trunk
				create_clock_mesh -net $one_mesh \
						-layers "$mesh_hori $mesh_vert" \
						-widths "$width_hori $width_vert" \
						-pitches $cur_used_mesh_trunk_spacing \
						-load $cur_mesh_load -avoid [all_macro_cells]
			}
		} else {
			if {[info exists cus_num_hori_vert]} {
				##	create mesh trunk
				create_clock_mesh -net $one_mesh \
						-layers "$mesh_hori $mesh_vert" \
						-num_straps $cus_num_hori_vert \
						-widths "$width_hori $width_vert" \
						-load $cur_mesh_load
			} else {
				if {$def_hori_spacing>$eff_height} {
					puts [format "Script Info:: default mesh spacing between horizontal metal is changed : %s => %s" $def_hori_spacing [expr {int($eff_height)}]]
					set def_hori_spacing [expr {int($eff_height)}]
				}
				if {$def_vert_spacing>$eff_width} {
					puts [format "Script Info:: default mesh spacing between vertical metal is changed : %s => %s" $def_vert_spacing [expr {int($eff_width)}]]
					set def_vert_spacing [expr {int($eff_width)}]
				}
				set cur_used_mesh_trunk_spacing [list $def_hori_spacing $def_vert_spacing]
				##	create mesh trunk
				create_clock_mesh -net $one_mesh \
						-layers "$mesh_hori $mesh_vert" \
						-widths "$width_hori $width_vert" \
						-pitches $cur_used_mesh_trunk_spacing \
						-load $cur_mesh_load
			}
		}
		##	re-change name
		if {$change_name_mark} {
			set_name -type net -name $org_mesh [get_nets $one_mesh]
		}
		set create_mesh_info "Create new Clk Strap!"
		###	add reshape mesh structure
		set cur_mesh_clock_region	[dict get $nhp_clockdefine $clock_pin_name_map($org_mesh) region]
		if {[llength $cur_mesh_clock_region]>4} {
			append create_mesh_info " Polygon region, reshape mesh structure!"
			set all_mesh_vias [get_vias -of_object [get_nets -segments $org_mesh]]
			set all_mesh_vias_within [get_vias -of_object [get_nets -segments $org_mesh] \
				-within [get_attribute [get_attribute [index_collection [get_cells -of_objects [get_nets -segments $org_mesh] -filter {is_hierarchical==false}] 0] movebound] points]]
			set all_mesh_vias_outside [remove_from_collection $all_mesh_vias $all_mesh_vias_within]
			array unset mesh_via_spacing_x_array
			array unset mesh_via_spacing_y_array
			array unset point_spacing_up
			array unset point_spacing_down
			array unset point_spacing_left
			array unset point_spacing_right
			set mesh_via_spacing_x_value $die_width
			set mesh_via_spacing_y_value $die_height
			foreach via_xy [get_attribute $all_mesh_vias center] {
				set mesh_via_spacing_x_array([lindex $via_xy 0]) 1
				set mesh_via_spacing_y_array([lindex $via_xy 1]) 1
			}
			set mesh_via_x_list [lsort -real -incr [array name mesh_via_spacing_x_array]]
			set mesh_via_y_list [lsort -real -incr [array name mesh_via_spacing_y_array]]

			###################################
			if {[llength $mesh_via_x_list]>1} {
				for {set i 0} {$i<[llength $mesh_via_x_list]} {incr i 1} {
					if {$i==0} {
						set point_spacing_left([lindex $mesh_via_x_list $i]) [expr {[lindex $mesh_via_x_list $i]-$eff_bbox_llx+10}]
						set point_spacing_right([lindex $mesh_via_x_list $i]) [expr {([lindex $mesh_via_x_list [expr {$i+1}]]-[lindex $mesh_via_x_list $i])*$var(mesh_spacing_scalar)}]
					} elseif {$i==[expr {[llength $mesh_via_x_list]-1}]} {
						set point_spacing_left([lindex $mesh_via_x_list $i]) [expr {([lindex $mesh_via_x_list $i]-[lindex $mesh_via_x_list [expr {$i-1}]])*$var(mesh_spacing_scalar)}]
						set point_spacing_right([lindex $mesh_via_x_list $i]) [expr {$eff_bbox_urx-[lindex $mesh_via_x_list $i]+10}]
					} else {
						set point_spacing_left([lindex $mesh_via_x_list $i]) [expr {([lindex $mesh_via_x_list $i]-[lindex $mesh_via_x_list [expr {$i-1}]])*$var(mesh_spacing_scalar)}]
						set point_spacing_right([lindex $mesh_via_x_list $i]) [expr {([lindex $mesh_via_x_list [expr {$i+1}]]-[lindex $mesh_via_x_list $i])*$var(mesh_spacing_scalar)}]
					}
				}
			} else {
				set point_spacing_left($mesh_via_x_list) $die_width
				set point_spacing_right($mesh_via_x_list) $die_width
			}
			if {[llength $mesh_via_y_list]>1} {
				for {set i 0} {$i<[llength $mesh_via_y_list]} {incr i 1} {
					if {$i==0} {
						set point_spacing_down([lindex $mesh_via_y_list $i]) [expr {[lindex $mesh_via_y_list $i]-$eff_bbox_lly+10}]
						set point_spacing_up([lindex $mesh_via_y_list $i]) [expr {([lindex $mesh_via_y_list [expr {$i+1}]]-[lindex $mesh_via_y_list $i])*$var(mesh_spacing_scalar)}]
					} elseif {$i==[expr {[llength $mesh_via_y_list]-1}]} {
						set point_spacing_down([lindex $mesh_via_y_list $i]) [expr {([lindex $mesh_via_y_list $i]-[lindex $mesh_via_y_list [expr {$i-1}]])*$var(mesh_spacing_scalar)}]
						set point_spacing_up([lindex $mesh_via_y_list $i]) [expr {$eff_bbox_ury-[lindex $mesh_via_y_list $i]+10}]
					} else {
						set point_spacing_down([lindex $mesh_via_y_list $i]) [expr {([lindex $mesh_via_y_list $i]-[lindex $mesh_via_y_list [expr {$i-1}]])*$var(mesh_spacing_scalar)}]
						set point_spacing_up([lindex $mesh_via_y_list $i]) [expr {([lindex $mesh_via_y_list [expr {$i+1}]]-[lindex $mesh_via_y_list $i])*$var(mesh_spacing_scalar)}]
					}
				}
			} else {
				set point_spacing_down($mesh_via_y_list) $die_width
				set point_spacing_up($mesh_via_y_list) $die_width
			}
			foreach_in_collection each_mesh_via $all_mesh_vias_outside {
        			set cur_via_center [get_attribute $each_mesh_via center]
				#set cur_via_x [lindex $cur_via_center 0]
				#set cur_via_y [lindex $cur_via_center 1]
				lassign $cur_via_center cur_via_x cur_via_y
				set cur_match_bbox [list [list [expr {$cur_via_x-$point_spacing_left($cur_via_x)*$var(mesh_spacing_scalar)+$width_vert*2}] [expr {$cur_via_y-$point_spacing_down($cur_via_y)*$var(mesh_spacing_scalar)+$width_hori*2}]] \
							[list [expr {$cur_via_x+$point_spacing_right($cur_via_x)*$var(mesh_spacing_scalar)-$width_vert*2}] [expr {$cur_via_y+$point_spacing_up($cur_via_y)*$var(mesh_spacing_scalar)-$width_hori*2}]]]
        			if {[sizeof_collection [remove_from_collection -intersect [add_to_collection [get_cells -within $cur_match_bbox] [get_cells -intersect $cur_match_bbox]] $cur_mesh_load_cell]]==0} {
                			cut_objects -bbox $cur_match_bbox [get_nets -segments $org_mesh]
                			set cur_left_shapes [get_net_shapes -quiet -of_objects [get_nets -segments $org_mesh] -within $cur_match_bbox]
                			if {[sizeof_collection $cur_left_shapes]>0} { remove_object $cur_left_shapes }
               				remove_object $each_mesh_via
				} else {
				}
			}
		}
		##	auto re-place clock terminals
		set mesh_trunk_shapes [get_net_shapes -of_objects [get_net $org_mesh] -filter "layer==$cur_mesh_layer"]
		set mesh_trunk_medium [index_collection $mesh_trunk_shapes [expr {[sizeof_collection $mesh_trunk_shapes]/2}]]
		remove_terminal	[get_terminal $org_mesh]
		create_terminal -bbox [get_center_square [get_attribute $mesh_trunk_medium bbox]] -layer $cur_mesh_layer -port [get_port $org_mesh]
		##	extend trunk width
		foreach_in_collection each_net_shape [get_net_shapes -of_objects [get_nets -segments $org_mesh]] {
			set trunk_mesh_width([get_attribute $each_net_shape name]) [get_attribute $each_net_shape width]
			set_attribute $each_net_shape width [expr {[get_attribute $each_net_shape width]+[get_layer_attribute -layer $mesh_hori defaultWidth]*4}]
		}
	}
	###
	lappend clock_mesh_net_route $org_mesh
	incr finished_mesh_net 1
	set mesh_end [clock seconds]
	echo [format "\[%02d/%02d\] cost : [clock format [expr $mesh_end - $mesh_start] -format %H:%M:%S -gmt true], trunked : %-20s %s" \
			$finished_mesh_net [llength $clock_mesh_net_list] $one_mesh $create_mesh_info] >> ./mesh.rpt
	foreach_in_collection one_via [get_vias -of_objects [get_nets -segments $org_mesh] -filter {route_type=="Clk Strap"}] {
		echo [format "%s %s" [get_attribute $one_via center] [get_attribute $one_via upper_layer]] >> ./mesh.rpt
	}
	unset -nocomplain cus_num_hori cus_num_vert
}
echo ----------------------------------------------------------------------- >> ./mesh.rpt

set mesh_start [clock seconds]
set sizeof_reshield_net [llength $clock_shield_list]
if {$sizeof_reshield_net>0} {
	##	restore trunk width
	foreach_in_collection each_net_shape [get_net_shapes -of_objects [get_nets -segments $clock_shield_list]] {
		set_attribute $each_net_shape width $trunk_mesh_width([get_attribute $each_net_shape name])
	}
        create_zrt_shield -net [get_nets -segments $clock_shield_list] -preferred_direction_only true
        set_attribute [get_net_shapes -shield_of [get_nets -segments $clock_shield_list]] route_type "P/G Strap"
        set_attribute [get_vias -shield_of [get_nets -segments $clock_shield_list]] route_type "P/G Strap"
}
set mesh_end [clock seconds]
echo [format "create_trunk_shielding (%d) cost : [clock format [expr $mesh_end - $mesh_start] -format %H:%M:%S -gmt true]" $sizeof_reshield_net] >> ./mesh.rpt
echo ----------------------------------------------------------------------- >> ./mesh.rpt

###	move back all gater route guide!
if {$move_gater_area_route_guides>0} {
        foreach_in_collection one_guide [get_route_guides -quiet GATER_ROUTE_GUIDE_*] {
                move_objects -delta "[expr {0-$gater_route_guide_delta_x}] 0" $one_guide
        }
}

set_attribute [get_terminals $clock_mesh_net_list] is_fixed true

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
set nhp_cell_prefixed [get_cells -quiet -filter {is_fixed==true}]
if {[sizeof_collection $nhp_cell_prefixed]>0} { set_attribute $nhp_cell_prefixed is_fixed false }
if {[sizeof_collection [all_macro_cells]]>0} { set_attribute [all_macro_cells] is_fixed true }
write_def -output ./$icc_finalopt/out/$var(design_name)_mesh.def -all_vias -rows_tracks_gcells -regions_groups -pins -blockages -specialnets -components -fixed
if {[sizeof_collection $nhp_cell_prefixed]>0} { set_attribute $nhp_cell_prefixed is_fixed true }

save_mw_cel -as ${phase_name}_before_route_mesh_net

###	route mesh nets
show_current_status "s03 mesh : route mesh nets"
set route_mesh_start [clock seconds]
set_auto_disable_drc_nets -clock true
route_mesh_net -net $clock_mesh_net_route -mode fishbone -max_span 0
set route_mesh_end [clock seconds]
echo [format "route mesh cost : [clock format [expr $route_mesh_end - $route_mesh_start] -format %H:%M:%S -gmt true]"] >> ./mesh.rpt
echo ----------------------------------------------------------------------- >> ./mesh.rpt
set_route_zrt_common_options -single_connection_to_pins off
