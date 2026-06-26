set_app_options -name plan.pgroute.disable_via_creation -value true

### remove all pg regions
remove_pg_regions -all
remove_routing_blockages *
### remove power settings
remove_pg_patterns -all
remove_pg_strategies -all
remove_pg_via_master_rules -all
remove_pg_strategy_via_rules -all

### remove all pg routes
remove_routes -net_types {power ground} -ring -stripe -macro_pin_connect -lib_cell_pin_connect


create_routing_blockage -layers {M6 M7 M8 M9 M10} -boundary {{2431.1550 180} {2720 570.2000}}

create_pg_mesh_pattern p_m9 -layers {{{horizontal_layer: M9} {width: 4} {spacing: 1.5} {pitch: 11} {offset: 2.5} {trim: false}}}
set_pg_strategy s_m9 -core -pattern {{name:p_m9} {nets:{VDD VSS}}}

create_pg_mesh_pattern p_m10 -layers {{{vertical_layer: M10} {width: 4} {spacing: 1.5} {pitch: 11} {offset: -1.5} {trim: false}}}
set_pg_strategy s_m10 -core -pattern {{name:p_m10} {nets:{VDD VSS}}}



compile_pg -strategies {s_m9 s_m10}


create_pg_mesh_pattern p_m7 -layers {{{horizontal_layer: M7} {width: 2} {spacing: 1.5} {pitch: 8} {offset: 0} {trim: false}}}
set_pg_strategy s_m7 -core -pattern {{name:p_m7} {nets:{VDD VSS}}}
create_pg_mesh_pattern p_m8 -layers {{{vertical_layer: M8} {width: 2} {spacing: 1.5} {pitch: 8} {offset: 0} {trim: false}}}
set_pg_strategy s_m8 -core -pattern {{name:p_m8} {nets:{VDD VSS}}}










compile_pg -strategies {s_m7 s_m8}



create_pg_mesh_pattern p_m6 -layers {{{vertical_layer: M6} {width: 2} {spacing: 1.5} {pitch: 8} {offset: 0} {trim: false}}}
set_pg_strategy s_m6 -core -pattern {{name:p_m6} {nets:{VSS VDD}}}





compile_pg -strategies {s_m6}

###PLL blockages{195.8750 195.3850} {501.8750 460.3850}
#create_routing_blockage -layers {M1} -boundary {{254.4300 1385.7850} {2669.9200 1648.4750}}
#create_routing_blockage -layers {M1} -boundary {{254.4300 1103.1150} {477.0550 1365.8050}}
#create_routing_blockage -layers {M1} -boundary {{254.4300 827.4650} {477.0550 1090.1550}}
#create_routing_blockage -layers {M1} -boundary {{254.4300 551.8150} {477.0550 814.5050}}

#create_routing_blockage -layers {M1} -boundary {{2436.1550 611.9700} {2669.9200 874.6600}}
#create_routing_blockage -layers {M1} -boundary {{2436.1550 1103.1150} {2669.9200 1365.8050}}

#create_routing_blockage -layers {M1} -boundary {{255.6300 250.0000} {2431.1550 512.6900}}

#create_routing_blockage -layers {M1} -boundary {{254.4950 230.0000} {2429.9550 489.5900}}
#create_routing_blockage -layers {M1} -boundary {{254.4350 567.0000} {476.9600 818.7000}}
#create_routing_blockage -layers {M1} -boundary {{254.4300 832.4650} {476.9550 1084.7000}}
#create_routing_blockage -layers {M1} -boundary {{254.4300 1108.6000} {476.9550 1360.8050}}


#create_routing_blockage -layers {M1} -boundary {{254.4300 1411.0850} {2658.6800 1670.0000}}

#create_routing_blockage -layers {M1} -boundary {{2436.1550 1107.9000} {2669.9200 1360.1200}}
#create_routing_blockage -layers {M1} -boundary {{2436.1550 617.1000} {2669.9200 871.2000}}




#create_pg_std_cell_conn_pattern p_std_conn -layer M2 -rail_width 0.15
create_pg_std_cell_conn_pattern p_std_conn1 -layer M1 -rail_width 0.15
#set_pg_strategy std_conn -pattern {{name:p_std_conn} {nets:{VDD VSS}}} -blockage {{nets: {VDD VSS}} {placement_blockages: all}} -core
#compile_pg -strategies {std_conn}
set_pg_strategy std_conn1 -pattern {{name:p_std_conn1} {nets:{VDD VSS}}} -blockage {{nets: {VDD VSS}} {placement_blockages: all}} -core
compile_pg -strategies {std_conn1}

#M6 copy


####### pg via
set die_box [get_attribute [current_block] boundary_bbox]
create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types lib_cell_pin_connect -from_layers M6 -to_layers M1 -mark_as strap -allow_parallel_objects
#create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M5 -to_layers M4 -mark_as strap -allow_parallel_objects
#create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M6 -to_layers M4 -mark_as strap -allow_parallel_objects
create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M7 -to_layers M6 -mark_as strap -allow_parallel_objects
create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M8 -to_layers M7  -mark_as strap -allow_parallel_objects
create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M9 -to_layers M8  -mark_as strap -allow_parallel_objects
create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers M10 -to_layers M9  -mark_as strap -allow_parallel_objects
#create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers TM2 -to_layers M8 -mark_as strap -allow_parallel_objects
#create_pg_vias -nets {VDD VSS} -within_bbox $die_box -from_types stripe -to_types stripe -from_layers TM2 -to_layers TM1 -mark_as strap -allow_parallel_objects
##macro pin M7-M4
##vss_core M7-M3
##DVSS M3-M2
create_pg_macro_conn_pattern scattered_pin_pattern -pin_conn_type scattered_pin -nets {VDD VSS} -layers {M4 M5} -width {0.3 0.3} -pin_layers {M4}
set_pg_strategy sram_macro -core -pattern {{name:scattered_pin_pattern} {nets:{VDD VSS}}} -blockage {{nets: {VDD VSS}} {placement_blockages: all}}
compile_pg -strategies {sram_macro}



########################################################################
# Core VDD/VSS ring
# 28um channel friendly:
#   M10 horizontal: width=4, spacing=1.5
#   M9  vertical  : width=4, spacing=1.5
########################################################################

create_pg_ring_pattern p_core_ring \
    -horizontal_layer M9 \
    -horizontal_width 4.0 \
    -horizontal_spacing 5 \
    -vertical_layer M10 \
    -vertical_width 4.0 \
    -vertical_spacing 5

set_pg_strategy s_core_ring \
    -core \
    -pattern {{name:p_core_ring} {nets:{VDD VSS}} {offset:{8 8}}}

compile_pg -strategies {s_core_ring}


#remove_routing_blockages *

#create_pg_ring_pattern pattern_core_ring_vdd -horizontal_layer M8 -horizontal_width {10} -vertical_layer M8 -vertical_width {10} -corner_bridge false
#set_pg_strategy strategy_core_ring_top_vdd  -core -pattern { {pattern: pattern_core_ring_vdd} {nets: {VDD}}  {offset: {40 40}} }
#compile_pg -strategies {strategy_core_ring_top_vdd}

#create_pg_ring_pattern pattern_core_ring_vss -horizontal_layer M7 -horizontal_width {10} -vertical_layer M7 -vertical_width {10} -corner_bridge false
#set_pg_strategy strategy_core_ring_top_vss  -core -pattern { {pattern: pattern_core_ring_vss} {nets: {VSS}}  {offset: {20 20}} }
#compile_pg -strategies {strategy_core_ring_top_vss}

