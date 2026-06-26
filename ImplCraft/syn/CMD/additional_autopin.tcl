########################################################################################
######  DCICC FLOW - Version 4.6.0 (2016-10-19)
########################################################################################
#       "set_pin_physical_constraints"  =>      set constraints on individual pins or nets.
#       "set_fp_pin_constraints"        =>      set global constraints for a block.
#       "write_pin_pad_physical_constraints" => save the current pin and pad constraints for current design.
#       "read_pin_pad_physical_constraints" =>  reload the exists pin/pad constraints.(can use "-append" option, default is overwrite)
#       "report_pin_pad_physical_constraints"   display current constraints.
#       "remove_pin_pad_physical_constraints"   remove all constraints previously set by two "set_*" command written above.
#set_pin_physical_constraints -layer {M7} -side 2 [get_ports GClk*]
#set_pin_physical_constraints -layer {M6} -side 1 [get_ports {i_col0* i_col1* i_col2* i_col3*}]
#set_pin_physical_constraints -layer {M6} -side 3 [get_ports {i_col4* i_col5* i_col6* i_col7*}]
#set_pin_physical_constraints -layer {M5} -side 2 [get_ports {i_mt* i_ram* i_s* *reset* rst_n gc_bist gc_miss*}]
#set_pin_physical_constraints -layer {M5} -side 4 [remove_from_collection [get_ports {pamu2gc* tc2gc* gc2pamu* gc2tc* o_*}] [get_ports {o_mt* o_ram*}]]
#set_pin_physical_constraints -layer {M7} -side 2 [get_ports {o_mt* o_ram*}]
#set_pin_physical_constraints -layers {M2 M3} [get_ports]
