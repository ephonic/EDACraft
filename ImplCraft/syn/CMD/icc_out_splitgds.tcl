########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  split gds
######  Owner : Anonymous , rc
########################################################################################
if {![info exists icc_finalopt]} {
        set icc_finalopt ICC
}
if {[info exists directory_for_splitgds]} {
	set icc_splitgds_out	"$directory_for_splitgds/splitedGDS"
} else {
	set icc_splitgds_out	./$icc_finalopt/out/splitedGDS
}

if {![file isdirectory $icc_splitgds_out]} {
	file mkdir $icc_splitgds_out
}

###	only output cell, keep current cel has already been opened!
#open_mw_cel $var(design_name)
save_mw_cel -as $var(design_name)_wire_via

### remove custom pg metal.
if {[sizeof_collection [get_user_shapes -quiet]]>0} {
        remove_objects [get_user_shapes -quiet]
}

remove_objects [get_net_shapes]
remove_objects [get_vias]

save_mw_cel -as $var(design_name)_cell
remove_cell -all >> /dev/null
if {[sizeof_collection [all_physical_only_cells]]>0} {
	remove_cell [all_physical_only_cells] >> /dev/null
}

set_write_stream_options -reset
set_write_stream_options -output_pin {text geometry} -max_name_length 64 \
                        -resize_text {0 0.1} -pin_name_mag 0.1 \
                        -rotate_pin_text_by_access_dir \
                        -output_geometry_property \
                        -output_net_name_as_property 100 \
                        -output_instance_name_as_property 102 \
			-keep_data_type \
                        -map_layer [dict get $nhp_predefine gdsmap_file]

write_stream -cells [get_object_name [current_mw_cel]] $icc_splitgds_out/$var(design_name).gds
close_mw_cel

set_write_stream_options -reset
set_write_stream_options -max_name_length 64 \
                        -resize_text {0 0.1} -pin_name_mag 0.1 \
                        -output_geometry_property \
                        -output_net_name_as_property 100 \
                        -output_instance_name_as_property 102 \
			-keep_data_type \
                        -map_layer [dict get $nhp_predefine gdsmap_file]

write_stream -cells $var(design_name)_cell $icc_splitgds_out/$var(design_name)_cell.gds
remove_mw_cel -all_view -all_version $var(design_name)_cell

###	only output Top Metal
open_mw_cel $var(design_name)_wire_via
remove_cell -all >> /dev/null
if {[sizeof_collection [all_physical_only_cells]]>0} {
	remove_cell [all_physical_only_cells] >> /dev/null
}
save_mw_cel
#save_mw_cel -as $var(design_name)_wire_via

set_write_stream_options -reset
set_write_stream_options -max_name_length 64 \
                        -resize_text {0 0.1} -pin_name_mag 0.1 \
                        -output_geometry_property \
                        -output_net_name_as_property 100 \
                        -output_instance_name_as_property 102 \
			-keep_data_type \
                        -map_layer [dict get $nhp_predefine gdsmap_file]

###	output each metal
#open_mw_cel $var(design_name)_wire_via
remove_objects [get_vias]

foreach_in_collection one_layer [get_layer -filter {is_routing_layer==true && layer_type!=via}] {
	set cur_layer_name	[get_attribute $one_layer name]
	set cur_layer_number	[get_attribute $one_layer layerNumber]
	if {[sizeof_collection [get_net_shapes -quiet -filter "layer==$cur_layer_name"]]>0} {
		show_current_status "Output Layer : $cur_layer_name"
		copy_mw_cel -from $var(design_name)_wire_via -to $var(design_name)_$cur_layer_name
		set_write_stream_options -output_by_layer $cur_layer_number
		write_stream -cells $var(design_name)_$cur_layer_name $icc_splitgds_out/$var(design_name)_${cur_layer_name}.gds
		remove_mw_cel -all_view -all_version $var(design_name)_$cur_layer_name
	}
}
close_mw_cel

###	output each vias
open_mw_cel $var(design_name)_wire_via
remove_objects [get_net_shapes]
save_mw_cel

set_write_stream_options -reset
set_write_stream_options -max_name_length 64 \
                        -resize_text {0 0.1} -pin_name_mag 0.1 \
                        -output_geometry_property \
                        -output_net_name_as_property 100 \
                        -output_instance_name_as_property 102 \
			-keep_data_type \
                        -map_layer [dict get $nhp_predefine gdsmap_file]

foreach_in_collection one_layer [get_layer -filter {is_routing_layer==true && layer_type==via}] {
	set cur_layer_name	[get_attribute $one_layer name]
	set cur_layer_number	[get_attribute $one_layer layerNumber]
	if {[sizeof_collection [get_vias -quiet -filter "via_layer==$cur_layer_name"]]>0} {
		show_current_status "Output Layer : $cur_layer_name"
		copy_mw_cel -from $var(design_name)_wire_via -to $var(design_name)_$cur_layer_name
		#set_write_stream_options -output_by_layer $cur_layer_number
		open_mw_cel $var(design_name)_$cur_layer_name
		## do something
		remove_via [get_vias -quiet -filter "via_layer!=$cur_layer_name"]
		close_mw_cel -save $var(design_name)_$cur_layer_name
		write_stream -cells $var(design_name)_$cur_layer_name $icc_splitgds_out/$var(design_name)_${cur_layer_name}.gds
		remove_mw_cel -all_view -all_version $var(design_name)_$cur_layer_name
		current_mw_cel $var(design_name)_wire_via
	}
}
close_mw_cel $var(design_name)_wire_via

set_write_stream_options -reset
