########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
######  CUSTOM ADDITIONAL ICC CONSTRAINTS
########################################################################################
### Input and Output Delays
#set_input_delay -clock $clock_name      $var(default_input_delay)       [get_ports ***]
#set_input_transition 0.1                                                [get_ports ***]
#set_output_delay -clock $clock_name     $var(default_output_delay)      [get_ports ***]

### Dont Use
#set_dont_use -power {ts45nkkhsst_ttdb0p9v25c/*}

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

### Custom Constraints add blow
#set_input_delay
#set_output_delay
