########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  Owner : Anonymous , rc
########################################################################################
########################################################################################
## Check and Fix floorplan issues
# 1) site_rows, 2) tracks, 3) unfixed macro, 4)
########################################################################################
## check site_row and tracks
if {[sizeof_collection [get_site_rows -quiet]]>0} {
        ## for def have row
	## create default track
	if {!$var(use_def_track) || [sizeof_collection [get_tracks -quiet]]==0} {
		if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_create_track] &&
			[file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_create_track]]} {
			source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_create_track]
		}
	}
} else {
	## for def don't have row
	if {$var(autofp,flip)} {
		set CMD_CREATE_SITE_ROW "create_floorplan -control_type boundary -start_first_row -flip_first_row -keep_macro_place -keep_io_place"
	} else {
		set CMD_CREATE_SITE_ROW "create_floorplan -control_type boundary -start_first_row -keep_macro_place -keep_io_place"
	}
	puts "Script Info:: there is no site row information were defined in def file ,create them automatically.."
        puts "Script Info:: disable SPG mode automatically while no site_rows were provided!!\n";
        set designopt(spg)      false
	echo $CMD_CREATE_SITE_ROW
	eval $CMD_CREATE_SITE_ROW
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
## For auto create pg strap with pin def! (no stripe shapes exists in def)
if {$var(create_pg_strap_with_pin_def)} {
	if {[sizeof_collection [get_net_shapes -quiet -filter {route_type=~"P/G*"}]]==0} {
		puts [format "Script Info:: Create PG Strap with Pin DEF : %s" [dict get $nhp_predefine def_exists]]
		###	auto place unfixed macros
		if {![file isfile $var(dc_dp,flag)]} { check_physical_constraints }
		source -verbose [dict get $nhp_predefine autofp]
		read_def -incremental [dict get $nhp_predefine def_exists]
        } else {
		puts [format "Script Info:: Create PG Strap with Pin(only) DEF : There are already some metal stripe in def files,Skip!"]
        }
}

source /mnt/Data/Project/Cluster/DCICC/WORK_rc001_2/useful_tcl/auto_create_power.tcl

# check and place missing terminals
if {[sizeof_collection [get_terminals -quiet]]==0} {
        # no terminals, create all
        puts [format "Script Info:: Place Terminals : All"]
        place_fp_pins -block_level
} elseif {[sizeof_collection [filter_collection  [remove_from_collection [get_ports] [get_ports -of_objects [get_terminals ]]] {port_type!=power && port_type!=ground}]]>0} {
        # missing some terminals, fix them.
        set missing_terminals [filter_collection  [remove_from_collection [get_ports] [get_ports -of_objects [get_terminals ]]] {port_type!=power && port_type!=ground}]
        puts [format "Script Info:: Place Terminals : %d" [sizeof_collection $missing_terminals]]
        place_fp_pins -block_level $missing_terminals
} else {
}
set_object_fixed_edit [get_terminals] true

## change pg via attribute
if {[sizeof_collection [get_vias -filter {via_master=~*NHP_PG* && route_type!~"P/G Strap"}]]>0} {
	set_attribute [get_vias -filter {via_master=~*NHP_PG* && route_type!~"P/G*"}] route_type {P/G Strap}
}

## adjust track if flip rows, #if {$var(autofp,flip)}
if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_adjust_track] &&
	[file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_adjust_track]]} {
	source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_adjust_track]
}

###     insert endcap && welltap
if {$var(insert,endcap) && [sizeof_collection [all_physical_only_cells xoendcap*]]==0} {
	if {[dict exists $tech_structure process2file [dict get $nhp_predefine process] file_insert_boundary] &&
		[file isfile [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_boundary]]} {
		source -echo -verbose [dict get $tech_structure process2file [dict get $nhp_predefine process] file_insert_boundary]
	} else {
        	add_end_cap -mode both -respect_blockage -respect_keepout \
                        -lib_cell [dict get $nhp_predefine endcap_cell] -next_to_fixed
        	add_end_cap -mode both -respect_blockage -respect_keepout \
                        -lib_cell [dict get $nhp_predefine endcap_cell] -next_to_fixed
	}
}
if {$var(insert,welltap) && [sizeof_collection [all_physical_only_cells tapfiller*welltap*]]==0} {
        add_tap_cell_array -master_cell_name [lindex [dict get $nhp_predefine welltap_cell] 0] \
                -distance [lindex [dict get $nhp_predefine welltap_cell] 1] \
                -pattern stagger_every_other_row \
                -ignore_soft_blockage true -skip_fixed_cells true \
                -connect_power_name VDD -connect_ground_name VSS \
                -left_macro_blockage_extra_tap must_insert \
                -right_macro_blockage_extra_tap must_insert -respect_keepout -tap_cell_identifier welltap
}
if {$var(insert,predecap) && [sizeof_collection [all_physical_only_cells tapfiller*predecap*]]==0} {
        add_tap_cell_array -master_cell_name [dict get $nhp_predefine predecap_cell] \
                -distance [lindex [dict get $nhp_predefine welltap_cell] 1] \
                -pattern stagger_every_other_row \
                -ignore_soft_blockage true -skip_fixed_cells true \
                -connect_power_name VDD -connect_ground_name VSS \
                -left_macro_blockage_extra_tap no_insert \
                -right_macro_blockage_extra_tap no_insert -respect_keepout -tap_cell_identifier predecap
}

derive_pg_connection -power_net $var(power_net) -ground_net $var(ground_net)

set nhp_cell_prefixed [get_cells -quiet -filter {is_fixed==true}]
if {[sizeof_collection $nhp_cell_prefixed]>0} { set_attribute $nhp_cell_prefixed is_fixed false }
if {[sizeof_collection [all_macro_cells]]>0} { set_attribute [all_macro_cells] is_fixed true }
write_def -output ./$icc_finalopt/out/$var(design_name)_fp.def -all_vias -rows_tracks_gcells -regions_groups -pins -blockages -specialnets -components -fixed
if {[sizeof_collection $nhp_cell_prefixed]>0} { set_attribute $nhp_cell_prefixed is_fixed true }
