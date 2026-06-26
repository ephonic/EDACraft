########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
###	signoff metal fill generation
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

set var(icv,signoff_metal_fill) true

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

if {$var(icv,signoff_metal_fill) && [sizeof_collection [get_mw_cels -quiet $var(design_name).FILL]]>0} {
        echo "$var(design_name) $var(design_name)_metalfill_icv" > rename_metalfill.tcl
        set_write_stream_options -rename_cell rename_metalfill.tcl
        write_stream -cells $var(design_name).FILL ./$icc_finalopt/out/$var(design_name)_metalfill_icv.gds
        set_write_stream_options -rename_cell {}
}

set phase_end [clock seconds]
echo [format "### %-20s , cost : %d days, %s" $phase_name \
	[expr {[clock format [expr $phase_end - $phase_start] -format %j -gmt true]-1}] \
	[clock format [expr $phase_end - $phase_start] -format %H:%M:%S -gmt true]]
echo [format "Diagnostics summary: %d error, %d warnings, %d informations." \
		[get_message_info -error_count] \
		[get_message_info -warning_count] \
		[get_message_info -info_count] \
		]
##################################
###     Close && Quit        #####
##################################
close_mw_cel
close_mw_lib

print_message_info

check_show_messages Error

if {$var(quit)} {exit}
