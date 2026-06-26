########################################################################################
######  DC FLOW - Version 4.6.1 (2016-11-04)
######  support ICC2 2015.06
######  Owner : Anonymous , rc
######  Create default constraints for current scenario
########################################################################################
set nhp_realclock_list [dict keys $nhp_clockdefine]
if {[llength $nhp_realclock_list]==0} {
	# define default virtual clock
	set cur_virtual_clock [lindex $var(ref_clock) 0]
	create_clock -name $cur_virtual_clock -period [lindex $var(ref_clock) 1]
	# define input && output delay
	set_input_delay	-clock $cur_virtual_clock -max [lindex $var(default_input_delay) 0]	[all_inputs]
	set_input_delay	-clock $cur_virtual_clock -min [lindex $var(default_input_delay) 1]	[all_inputs]
	set_input_transition 0.1 [all_inputs]
	set_output_delay -clock $cur_virtual_clock -max [lindex $var(default_output_delay) 0] [all_outputs]
	set_output_delay -clock $cur_virtual_clock -min [lindex $var(default_output_delay) 1] [all_outputs]
	# Defining the Driver Cell
	set local_driving_cell	[dict get $lib_define $main_lib_name function_cell driver_inv]
	set_driving_cell -no_design_rule -lib_cell [lindex $local_driving_cell 0] \
			-pin [lindex $local_driving_cell 2] [all_inputs]
	# Defining the Load Attribute
	set_load [expr [load_of [get_lib_pins */[lindex $local_driving_cell 0]/[lindex $local_driving_cell 1]]] * 20]	[all_outputs]
        ###     default path groups     
        group_path -name D-O -from [all_inputs] -to [all_outputs]
} else { ; # design have real clock.
	###	define real clock
	if {[llength [dict keys $nhp_clockdefine]]>0} {
		unset -nocomplain nhp_faster_clock nhp_faster_period
		foreach clock_name [dict keys $nhp_clockdefine] {
			set cur_clock_period [dict get $nhp_clockdefine $clock_name period]
			# create current virtual clock
			set cur_virtual_clock ref_$clock_name
			create_clock -name $cur_virtual_clock -period $cur_clock_period
			# create current real clock
			set clock_port	[dict get $nhp_clockdefine $clock_name root]
			if {[sizeof_collection [get_ports -quiet $clock_port]]>0} {
				create_clock -name $clock_name -period $cur_clock_period [get_ports $clock_port]
				set_drive	0	[get_ports $clock_port]
			} elseif {[sizeof_collection [get_pins -quiet $clock_port]]>0} {
				create_clock -name $clock_name -period $cur_clock_period [get_pins $clock_port]
				set_drive	0	[get_pins $clock_port]
			} else {
				puts [format "Script %s:: clock root : %s is neither port nor pin, plz check it!" [string totitle error] $clock_port]
				exit
			}
			set_ideal_network		[all_fanout -flat -from [get_attribute [get_clocks $clock_name] sources]]
			set_clock_uncertainty -setup	[dict get $nhp_clockdefine $clock_name setup]	[get_clocks $clock_name]
			set_clock_uncertainty -hold	[dict get $nhp_clockdefine $clock_name hold]	[get_clocks $clock_name]
			set_clock_transition		[dict get $nhp_clockdefine $clock_name skew]	[get_clocks $clock_name]
			if {[info exists nhp_faster_period]} {
				if {$cur_clock_period<$nhp_faster_period} {
					set nhp_faster_clock $cur_virtual_clock
					set nhp_faster_period $cur_clock_period
				}
			} else {
				set nhp_faster_clock $cur_virtual_clock
				set nhp_faster_period $cur_clock_period
			}
		}
	}
	###	define input && output delay
	set all_inputs_without_clk	[remove_from_collection [all_inputs] \
						[filter_collection [get_attribute [get_clocks] sources] object_class==port] \
					]
	set_input_delay	-clock $nhp_faster_clock -max [lindex $var(default_input_delay) 0]	$all_inputs_without_clk
	set_input_delay	-clock $nhp_faster_clock -min [lindex $var(default_input_delay) 1]	$all_inputs_without_clk
	set_input_transition 0.1 $all_inputs_without_clk
	set_output_delay -clock $nhp_faster_clock -max [lindex $var(default_output_delay) 0] [all_outputs]
	set_output_delay -clock $nhp_faster_clock -min [lindex $var(default_output_delay) 1] [all_outputs]
	###	Defining the Driver Cell
	set local_driving_cell	[dict get $lib_define $main_lib_name function_cell driver_inv]
	set_driving_cell -no_design_rule -lib_cell [lindex $local_driving_cell 0] \
			-pin [lindex $local_driving_cell 2] $all_inputs_without_clk
	###	Defining the Load Attribute
	set_load [expr [load_of [get_lib_pins */[lindex $local_driving_cell 0]/[lindex $local_driving_cell 1]]] * 20]	[all_outputs]
	###	default path groups	
	group_path -name C-O -to [all_outputs]
	group_path -name D-L -from $all_inputs_without_clk
	group_path -name D-O -from $all_inputs_without_clk -to [all_outputs]
	update_nhp_clockdefine
	if {$var(extend,groups)} { create_path_groups_between_clocks [get_clocks -quiet] }
}
###	Defining ideal network
if {[llength $var(ideal_sources)]>0} {
	set_ideal_network [get_ports $var(ideal_sources)]
}
###	set isolate ports
set_isolate_ports [remove_from_collection [all_outputs] [all_inputs]]
report_isolate_ports
###	define max transition && fanout	
set_max_transition $var(max_tran_dc) [current_design]
set_max_fanout $var(max_fanout) [current_design]
if {$var(critical_range)>0} {
	set_critical_range $var(critical_range) [current_design]
}
###	source addtional sdc file
if {[file isfile $var(sdc_dc)]} {
	source -echo -verbose $var(sdc_dc)
}
