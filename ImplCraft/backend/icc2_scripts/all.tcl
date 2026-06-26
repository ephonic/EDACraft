set netlist "/share/home/limuhan/Projects/BP_TapeOut_WorkSpace/BP_TapeOut_syn/work/DC/out/top.v"
set top_name "top"

set TECH_FILE "/share/home/limuhan/Libraries/TSMC28/tsmcn28_10lm7X2ZUTRDL_HVH.tf"

####### NDM
set NDM_PLL "/share/home/limuhan/TSMC28nm_icc2/icc_work/ndm/PLL.ndm"
set NDM_STD "\
/share/home/limuhan/TSMC28nm_icc2/icc_work/ndm/STDCELL.ndm \
/share/home/limuhan/TSMC28nm_icc2/icc_work/ndm/PORT.ndm \
/share/home/limuhan/Downloads/PORT/icc2_frame/ndm/PORT_merge_db_physical_only.ndm \
"
set NDM_MEM "/share/home/limuhan/Projects/BP_TapeOut_WorkSpace/RAMNEW.ndm"

#/share/home/limuhan/TSMC28nm_icc2/icc_work/ndm/STDCELL.ndm \

#source /storeroom/course/icc2/mcu_synopsys/2_data_preparation/liblist/liblist.tcl

set_host_option -max_cores 64

set ndm_pll "[eval "glob -nocomplain $NDM_PLL"]"
set ndm_std "[eval "glob -nocomplain $NDM_STD"]"
set ndm_mem "[eval "glob -nocomplain $NDM_MEM"]"
#set reference_library [concat $ndm_pll]
set reference_library [concat $ndm_std $ndm_pll $ndm_mem]
create_lib -technology $TECH_FILE -ref_libs $reference_library /share/home/limuhan/TSMC28nm_icc2/icc_work/work_0429/${top_name}.nlib
open_lib /share/home/limuhan/TSMC28nm_icc2/icc_work/work_0429/${top_name}.nlib

read_verilog -top top $netlist
current_block top
link_block
redirect -file ./uniquify.rpt {uniquify}

save_lib

#### init fp
initialize_floorplan -control_type die -shape R -flip_first_row true -boundary {{0 0} {2900 1900}} -core_offset {180 180 180 180}


source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/place_io.tcl

read_def /share/home/limuhan/TSMC28nm_icc2/icc_work/work_0420/IO_place1.def
#manual

create_io_filler_cells \
    -reference_cell {PFILLER20_G PFILLER10_G PFILLER5_G PFILLER1_G PFILLER05_G PFILLER0005_G}
#read_def ./script/all_io.def

#create_io_filler_cells -reference_cell {PFILLER20_G PFILLER10_G PFILLER5_G PFILLER1_G PFILLER05_G PFILLER0005_G}

set fixed_objects [get_cells * -filter "ref_name =~ *P*G"]
set fixed_objects [get_flat_cells * -filter "ref_name =~ *P*G"]


####################macro
read_def /share/home/limuhan/TSMC28nm_icc2/icc_work/work_0420/macro_place1.def

create_placement_blockage -type hard -boundary {{254.4300 1385.7850} {2669.9200 1648.4750}}
create_placement_blockage -type hard -boundary {{254.4300 1103.1150} {477.0550 1365.8050}}
create_placement_blockage -type hard -boundary {{254.4300 827.4650} {477.0550 1090.1550}}
create_placement_blockage -type hard -boundary {{254.4300 551.8150} {477.0550 814.5050}}


create_placement_blockage -type hard -boundary {{2431.1550 180} {2720 570.2000}}

create_placement_blockage -type hard -boundary {{2436.1550 611.9700} {2669.9200 874.6600}}
create_placement_blockage -type hard -boundary {{2436.1550 1103.1150} {2669.9200 1365.8050}}

create_placement_blockage -type hard -boundary {{255.6300 250.0000} {2431.1550 512.6900}}

#### create boundary cell
create_boundary_cells -left_boundary_cell BOUNDARY_LEFTBWP30P140 -right_boundary_cell BOUNDARY_RIGHTBWP30P140 -bottom_boundary_cells {FILL2BWP30P140UHVT FILL3BWP30P140UHVT} -top_boundary_cells {FILL2BWP30P140UHVT FILL3BWP30P140UHVT} -bottom_left_outside_corner_cell {FILL3BWP30P140UHVT} -bottom_right_outside_corner_cell {FILL3BWP30P140UHVT} -top_left_outside_corner_cell {FILL3BWP30P140UHVT} -top_right_outside_corner_cell {FILL3BWP30P140UHVT} -bottom_left_inside_corner_cell {FILL3BWP30P140UHVT} -bottom_right_inside_corner_cell {FILL3BWP30P140UHVT} -top_left_inside_corner_cell {FILL3BWP30P140UHVT} -top_right_inside_corner_cell {FILL3BWP30P140UHVT}  -no_1x

#### create tap cell
create_tap_cells -lib_cell TAPCELLBWP30P140 -distance 40 -pattern stagger -skip_fixed_cells

save_block -as fp

source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/run_floorplan2.tcl


source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/gen_power_mesh_1.tcl
remove_routing_blockages *



####### save
save_lib
save_block
save_block -as 4_floorplan2

check_legality

source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/pg.tcl

source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/run_place.tcl
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/run_clock2.tcl

source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/run_clock_opt.tcl
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/run_route.tcl




