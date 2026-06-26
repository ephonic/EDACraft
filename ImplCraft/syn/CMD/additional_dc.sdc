########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CUSTOM ADDITIONAL DC CONSTRAINTS
########################################################################################
### Generated Clock
#create_generated_clock [get_pins cg/r_1to2cnt_reg/Q] -name GClk_div2 -source [get_ports GClk] -divide_by 2
#create_generated_clock [get_pins cg/r_1to4cnt_reg[1]/Q] -name GClk_div4 -source [get_ports GClk] -divide_by 4

### Input and Output Delays
#set_input_delay -clock <clock_name>	-max [lindex $var(default_input_delay) 0]	[get_ports ***]
#set_input_delay -clock <clock_name>	-min [lindex $var(default_input_delay) 1]	[get_ports ***]
#set_input_transition 0.1                                                [get_ports ***]
#set_output_delay -clock <clock_name>	-max [lindex $var(default_output_delay) 0]	[get_ports ***]
#set_output_delay -clock <clock_name>	-min [lindex $var(default_output_delay) 1]	[get_ports ***]

### Dont Use
#set_dont_use -power {ts45nkkhsst_ttdb0p9v25c/*}
#set_ideal_network [all_fanout -flat -from [get_attribute [get_clocks $clocknames] sources]]

### Multicycle Paths
#set_multicycle_path

### False Paths
#set_false_path
#set_clock_groups -asynchronous -group clock_list

### Setting Case Logic
#set_case_analysis

### Other Constraints
#set_max_area 34100

### Specify Combinational Path Delay
#set_max_delay
#set_min_delay

#set_disable_timing
#set_max_fanout
#set_max_capacitance
#group_path -name <name> -critical_range 0.2
#group_path -name <name> -weight 50
#group_path -name <name> -priority 2

### Custom Constraints add blow
#set_input_delay
#set_output_delay

