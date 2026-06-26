########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
# plz open s02_place_opt , and modify clock.tcl, then source this file!
unset -nocomplain custom_mesh_trunk_setting
array unset clock
array unset clock_pin
source -echo -verbose ../CMD/clock.tcl
########################################################################################
###	s03 clockopt design
########################################################################################
set phase_start [clock seconds]
set phase_name  "t03_clock_try_mesh"
show_current_status $phase_name 1
update_nhp_clockdefine

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

if {$var(dc_clock_factor)!=1 && $var(clock_recover_phase)=="s03"} { recover_clock_period }
###	setting design variables
if {[file isfile $setting(design)]} {source -echo -verbose $setting(design)}
if {[file isfile $setting(route)]} {source -echo -verbose $setting(route)}

if {$designopt(autoweight)} { my_proc_auto_weights }
###	whether need to set dont touch network in mesh clock nets???
###	do MESH CLOCK DESIGN
set clocklist_mesh      [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_mesh}]]
set clocklist_cts       [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
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
        set compile_instance_name_prefix ICC_CLOCK_OPT
        if {[llength $clocklist_mesh]>0} { mark_clock_tree -clock_synthesized -clock_trees $clocklist_mesh }
        if {$designopt(ccdopt) && [llength $clocklist_mesh]==0} {
                puts "Script Info:: Performing Concurrent Clock and Data Optimization"
                source -echo -verbose ../CMD/ccdopt.tcl
        } else {
                set designopt(ccdopt)    false
                puts "Script Info:: Performing Traditional Clock Tree Synthesis"
                source -echo -verbose ../CMD/cts.tcl
        }
	set_propagated_clock [get_clocks $clocklist_cts]
        if {[llength $clocklist_mesh]>0} {
                set_ideal_network -no_propagate [get_nets -of_objects [get_attribute [get_clocks $clocklist_mesh] sources]]
        }
        set compile_instance_name_prefix U
}

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)
derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net) -tie

#report_all ./$icc_finalopt/report $phase_name

save_mw_cel -as $phase_name
set phase_end [clock seconds]

### then you can check whether this mesh structure meet your requirements.

