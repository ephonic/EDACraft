########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######	COMMON CLOCKDESIGN SETTING
######  Owner : Anonymous , rc
########################################################################################
# Make sure that skew_opt does not accidentally revert to ideal_clocks
set_app_var skew_opt_skip_ideal_clocks true
# Set clock tree optimization to do more DRC fixing
set_app_var cto_enable_drc_fixing true
set_app_var cts_use_arnoldi_based_delays true
set_app_var cts_do_characterization true        ; # prints 

set_app_var cts_use_lib_max_fanout true
set_app_var cts_use_sdc_max_fanout true

# define CTS RULE if needed.
#if {[string equal [dict get $nhp_predefine process] T16FFP]}
if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
	if {![my_check_routing_rule CTS_RULE]} {
			#-driver_taper_distance 0
		define_routing_rule CTS_RULE \
        		-default_reference_rule \
        		-multiplier_spacing 2 \
        		-multiplier_width 2 -shield \
			-shield_spacings {M1 0.096 M2 0.096 M3 0.096 M4 0.12 M5 0.12 M6 0.12 M7 0.12 M8 0.186 M9 0.186 M10 1.35 M11 1.35} \
			-via_cuts {{VIA34_LONG_H_80W_NDR 1X1 NR} \
				{VIA34_LONG_H_120W_NDR 1X1 NR} \
				{VIA34_LONG_V_80W_NDR 1X1 NR} \
				{VIA34_LONG_V_120W_NDR 1X1 NR} \
				{VIA34_LONG_H_40W_NDR 1X1 NR} \
				{VIA34_LONG_V_40W_NDR 1X1 NR} \
				{VIA45_LONG_H_80W_120W_NDR 1X1	NR} \
				{VIA45_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA45_LONG_V_120W_80W_NDR 1X1	NR} \
				{VIA45_LONG_H_40W_120W_NDR 1X1	NR} \
				{VIA56_LONG_V_80W_120W_NDR 1X1	NR} \
				{VIA56_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA56_LONG_H_120W_80W_NDR 1X1	NR} \
				{VIA56_LONG_V_40W_120W_NDR 1X1	NR} \
				{VIA67_LONG_H_80W_120W_NDR 1X1	NR} \
				{VIA67_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA67_LONG_V_120W_80W_NDR 1X1	NR} \
				{VIA67_LONG_H_40W_120W_NDR 1X1	NR} \
				{VIA78_1cut_NDR 1X1	NR} }
		report_routing_rule CTS_RULE
	}
	if {![my_check_routing_rule CTS_RULE_LEAF]} {
			#-driver_taper_distance 0
			#-taper_distance 50
		define_routing_rule CTS_RULE_LEAF \
        		-default_reference_rule \
        		-multiplier_spacing 2 \
        		-multiplier_width 2 \
			-via_cuts {{VIA34_LONG_H_80W_NDR 1X1 NR} \
				{VIA34_LONG_H_120W_NDR 1X1 NR} \
				{VIA34_LONG_V_80W_NDR 1X1 NR} \
				{VIA34_LONG_V_120W_NDR 1X1 NR} \
				{VIA34_LONG_H_40W_NDR 1X1 NR} \
				{VIA34_LONG_V_40W_NDR 1X1 NR} \
				{VIA45_LONG_H_80W_120W_NDR 1X1	NR} \
				{VIA45_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA45_LONG_V_120W_80W_NDR 1X1	NR} \
				{VIA45_LONG_H_40W_120W_NDR 1X1	NR} \
				{VIA56_LONG_V_80W_120W_NDR 1X1	NR} \
				{VIA56_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA56_LONG_H_120W_80W_NDR 1X1	NR} \
				{VIA56_LONG_V_40W_120W_NDR 1X1	NR} \
				{VIA67_LONG_H_80W_120W_NDR 1X1	NR} \
				{VIA67_LONG_H_120W_120W_NDR 1X1	NR} \
				{VIA67_LONG_V_120W_80W_NDR 1X1	NR} \
				{VIA67_LONG_H_40W_120W_NDR 1X1	NR} \
				{VIA78_1cut_NDR 1X1	NR} }
		report_routing_rule CTS_RULE_LEAF
	}
} else {
	if {![my_check_routing_rule CTS_RULE]} {
		define_routing_rule CTS_RULE \
        		-default_reference_rule \
        		-multiplier_spacing 2 \
        		-multiplier_width 1 -shield
		report_routing_rule CTS_RULE
	}
}
# If there are OCV issues that are seen uncomment the following
# set_clock_tree_options -ocv_path_sharing true

###	set cts prefix style
set_app_var cts_instance_name_prefix CTS_
set_app_var cts_net_name_prefix CTS_

# Specify that the tool considers float pin delays when updating the ideal clock latencies
set_app_var update_clock_latency_consider_float_pin_delays true

# Set STOP pin on macro clock pins
if { $var(cts,stop_pin_on_macro) && ( [sizeof_collection [all_macro_cells]] > 0 ) } {
	update_timing
	set_clock_tree_exceptions -stop_pins [get_pins -of [all_macro_cells] -filter "pin_on_clock_network==true && direction==in"]
}
## Enabling CRPR - CRPR is usually used with timing derate (bc_wc) and with OCV
set_app_var timing_remove_clock_reconvergence_pessimism true
###	set clock tree references

set CTSBUF	" \
	CLKBUFV10_12TL40 \
	CLKBUFV12_12TL40 \
	CLKBUFV16_12TL40 \
	CLKBUFV20_12TL40 \
	CLKBUFV8_12TL40 "

set CTSINV 	" \
	CLKINV10_12TL40 \
	CLKINV12_12TL40 \
	CLKINV16_12TL40 \
	CLKINV20_12TL40 \
	CLKINV8_12TL40 "
set CTSBUF_B "CLKBUFV20_12TL40"
set_clock_tree_references -references "$CTSINV"
set_clock_tree_references -references "$CTSINV"  -sizing_only
set_clock_tree_references -references "$CTSINV"  -delay_insertion_only
set_clock_tree_references -references "$CTSBUF_B" -boundary_cell_only
set balance_clock_group	false
set clocklist_cts       [dict keys [dict filter $nhp_clockdefine script {key value} {dict get $nhp_clockdefine $key is_cts}]]
foreach one_clock $clocklist_cts {
	set cur_cts_lower [lindex [dict get $nhp_predefine full_metal_list] \
			[expr {[lsearch [dict get $nhp_predefine full_metal_list] [dict get $nhp_clockdefine $one_clock metal]]-1}]]
	set cur_clock_tree_layer_list [list $cur_cts_lower [dict get $nhp_clockdefine $one_clock metal]]
	if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
		set cur_clock_tree_layer_list [lrange [dict get $lib_common metal_layers all] \
				[lsearch [dict get $lib_common metal_layers all] M4] \
				[lsearch [dict get $lib_common metal_layers all] [dict get $nhp_clockdefine $one_clock metal]] \
				]
	}
	set_clock_tree_options \
		-clock_trees $one_clock \
		-layer_list $cur_clock_tree_layer_list \
		-routing_rule CTS_RULE \
		-use_default_routing_for_sinks 1 \
		-advanced_drc_fixing true \
		-target_early_delay $var(cts,target_early_delay) \
		-insert_boundary_cell true
	if {[regexp -- {^T16FFP} [dict get $nhp_predefine process]]} {
		set_clock_tree_options -routing_rule_for_sinks CTS_RULE_LEAF -use_default_routing_for_sinks 0
	}
	if {!$var(cts,inter_clock_balance) && [llength [dict get $nhp_clockdefine $one_clock root]]>1} {
		puts [format "Script Info:: create clock balance_group base on mutil clock sources : %s => %s" $one_clock [dict get $nhp_clockdefine $one_clock root]]
		set_inter_clock_delay_options -balance_group [get_clocks $one_clock] -balance_group_name $one_clock
		set balance_clock_group true
	}
	# cmd clockname period factor_tran factor_leaf_tran {minimum maximum}
}
if {$balance_clock_group} {
	set var(cts,inter_clock_balance) true
	if {$designopt(ccdopt)} { set skew_opt_skip_clock_balancing true }
}
set balance_clock_group	false

if {$designopt(ccdopt)} {
	set_app_var update_clock_latency_consider_float_pin_delays true
	set_app_var skew_opt_optimize_clock_gates true
        set_concurrent_clock_and_data_strategy -effort medium \
		-ignore_path_groups $var(ccdopt,ignored_groups) \
		-adjust_boundary_registers false
}

if {$designopt(icg_replication)} {
	identify_clock_gating
}

#set_clock_cell_spacing -x_spacing 10 -y_spacing 10

#report_clock_cell_spacing

dict set nhp_predefine sl_clock 1
