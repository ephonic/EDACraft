########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	auto split mesh network.
######  Owner : Anonymous , rc
########################################################################################
update_nhp_clockdefine
set mesh_split_flag [split_seperated_mesh_clock]
if {![info exists icc_finalopt]} {
	set icc_finalopt ICC
}
if {$mesh_split_flag>0} {
	## verify_lvs_mesh_split
        verify_lvs -exclude_nets {VDD VSS} > ./$icc_finalopt/report/verify_lvs_mesh_split.rpt
        ## verify Zroute violation_split
        verify_zrt_route -report_all_open_nets true \
		-check_from_user_shapes true \
		-drc true  > ./$icc_finalopt/report/verify_zroute_mesh_split.rpt
	if {![file isdirectory $icc_finalopt/out_mesh_split]} {
		file mkdir $icc_finalopt/out_mesh_split
	}

        derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
        derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

	save_mw_cel -as $var(design_name)_mesh_split

	if {!$var(output,splitgds)} {
		set_write_stream_options -output_pin {text geometry} -max_name_length 64 \
                        	-resize_text {0 0.1} -pin_name_mag 0.1 \
				-rotate_pin_text_by_access_dir \
                        	-output_geometry_property \
                        	-output_net_name_as_property 100 \
                        	-output_instance_name_as_property 102 \
				-keep_data_type \
                        	-map_layer [dict get $nhp_predefine gdsmap_file]
	
		if {[sizeof_collection [get_user_shapes -quiet]]} {
        		remove_objects [get_user_shapes -quiet]
		}
		## write gds && def
		if {[file isfile ../DEF/$var(design_name).def]} {
			write_stream -cells $var(design_name) ./$icc_finalopt/out_mesh_split/$var(design_name).gds
			write_def -output ./$icc_finalopt/out_mesh_split/$var(design_name).def -all_vias
			## delete power and ground net for icfb-->def flow
			remove_route_by_type -pg_strap -pg_std_cell_pin_conn -nets {VDD VSS}
			write_stream -cells $var(design_name) ./$icc_finalopt/out_mesh_split/$var(design_name)_nopg.gds
			write_def -output ./$icc_finalopt/out_mesh_split/$var(design_name)_nopg.def -all_vias
		} else {
			write_stream -cells $var(design_name) ./$icc_finalopt/out_mesh_split/$var(design_name).gds
			write_def -output ./$icc_finalopt/out_mesh_split/$var(design_name).def -all_vias
		}
		write_parasitics -out ./$icc_finalopt/out_mesh_split/$var(design_name).spef
	}

	## write verilog without ant diode
	write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
			-no_tap_cells -no_cover_cells -no_chip_cells \
			-no_corner_pad_cells -no_pad_filler_cells \
			-no_core_filler_cells -no_physical_only_cells \
			-no_unconnected_cells -unconnected_ports ./$icc_finalopt/out_mesh_split/$var(design_name).v
	## write ant diode in verilog file
	write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
			-no_tap_cells -no_cover_cells -no_chip_cells \
			-no_corner_pad_cells -no_pad_filler_cells \
			-no_core_filler_cells -no_physical_only_cells \
			-no_unconnected_cells -unconnected_ports -diode_ports ./$icc_finalopt/out_mesh_split/$var(design_name)_ant.v
	## write pg ports in verilog file, no diode
	write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells \
			-no_tap_cells -no_cover_cells -no_chip_cells \
			-no_corner_pad_cells -no_pad_filler_cells \
			-no_core_filler_cells -no_physical_only_cells \
			-no_unconnected_cells -unconnected_ports -pg ./$icc_finalopt/out_mesh_split/$var(design_name)_pg.v
	## write pg ports in verilog file, with all cells
	write_verilog   -keep_backslash_before_hiersep -no_io_pad_cells \
                	-no_tap_cells -no_cover_cells -no_chip_cells \
                	-no_corner_pad_cells -no_pad_filler_cells -no_core_filler_cells \
                	-unconnected_ports -pg -diode_ports ./$icc_finalopt/out_mesh_split/$var(design_name)_full.v
	## write verilog without ant diode, split bus
	write_verilog	-keep_backslash_before_hiersep -no_io_pad_cells -split_bus \
			-no_tap_cells -no_cover_cells -no_chip_cells \
			-no_corner_pad_cells -no_pad_filler_cells \
			-no_core_filler_cells -no_physical_only_cells \
			-no_unconnected_cells -unconnected_ports ./$icc_finalopt/out_mesh_split/$var(design_name)_splitbus.v

	if {$var(output,splitgds)} {
		set directory_for_splitgds ./$icc_finalopt/out_mesh_split
        	source -echo -verbose ../CMD/icc_out_splitgds.tcl
	} else {
		close_mw_cel
	}
}
