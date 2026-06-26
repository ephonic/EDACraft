########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CUSTOM FULL DC CONSTRAINTS, plz change file name as <blockname>.sdc manually, if needed!!
########################################################################################
### Define Clocks
#create_clock -name $clock_name -period <period_value> [get_ports ***]
#set_dont_touch_network  [get_clocks $clock_name]
#set_ideal_network [all_fanout -flat -from [get_attribute [get_clocks $clocknames] sources]]
#set_drive       0       [get_ports $clock_name]
#set_clock_uncertainty -setup    <setup_value> [get_clocks $clock_name]
#set_clock_uncertainty -hold     <hold_value> [get_clocks $clock_name]
#set_clock_transition            <max_transition> [get_clocks $clock_name]

### Input and Output Delays
#set_input_delay -clock $clock_name      $var(default_input_delay)       [get_ports ***]
#set_input_transition 0.1                                                [get_ports ***]
#set_output_delay -clock $clock_name     $var(default_output_delay)      [get_ports ***]

### Set or Remove Dont Use 
#set_dont_use -power [get_lib_cells */$dont_cell]
#remove_attribute [get_lib_cells */$use_cell] dont_use
#remove_attribute [get_lib_cells */$use_cell] dont_touch

### Other Constraints
#set_max_area 34100
#set_driving_cell
#set_load
#group_path
#set_max_transition
#set_max_fanout
#set_max_capacitance
#set_max_delay
#set_min_delay
#set_disable_timing
#set_case_analysis

### False Paths
#set_false_path
#set_clock_groups -asynchronous -group clock_list

### Multicycle Paths
#set_multicycle_path

