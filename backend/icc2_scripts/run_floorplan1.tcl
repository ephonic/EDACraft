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
#initialize_floorplan -utilization 0.7 -aspect_ratio 1.0
#initialize_floorplan -control_type die -shape R -flip_first_row true -boundary {{0 0} {320 550}} -core_offset {0 0 0 0}
place_pins -self -ports [get_ports *]
initialize_floorplan -core_utilization 0.6
#yuanbenshi 180
#### place io
########################################################################
# Parameters
########################################################################

set DIE_W      2900
set DIE_H      1900
set IO_DEPTH   110
set PAD_PITCH  60

set H_SIDE_LEN [expr {$DIE_W - 2*$IO_DEPTH}]
set V_SIDE_LEN [expr {$DIE_H - 2*$IO_DEPTH}]

########################################################################
# User signal pads already exist in netlist:
# u_pad_clk u_pad_rst u_pad_sclk u_pad_mosi
# u_pad_cs u_pad_flag u_pad_miso u_pad_sel
########################################################################


########################################################################
# Digital IO P/G cells
# Use _V_G on top/bottom, _H_G on left/right.
# These are placement cells. Whether they are "bonded" depends on whether
# you later place PAD60GU/PAD60NU on them and connect package pins.
########################################################################


########################################################################
# Digital I/O power/ground cells
# One digital I/O domain:
#   PVDD1DGZ >= 3 bonded
#   PVDD2DGZ >= 2 bonded, one may be PVDD2POC if bonded
#   PVDD2POC = one and only one
#   PVSS1DGZ/PVSS3DGZ >= 1
#   PVSS2DGZ/PVSS3DGZ >= 1
########################################################################

# Top side PG
create_cell { \
    vddcore_top_1 vddcore_top_2 vddcore_top_3 \
    vddcore_top_4 vddcore_top_5 vddcore_top_6 \
} PVDD1DGZ_V_G

create_cell { \
    vsscore_top_1 vsscore_top_2 vsscore_top_3 vsscore_top_4 \
} PVSS1DGZ_V_G

create_cell { \
    vddio_top_1 vddio_top_2 vddio_top_3 vddio_top_4 \
} PVDD2DGZ_V_G

create_cell { \
    vssio_top_1 vssio_top_2 vssio_top_3 \
    vssio_top_4 vssio_top_5 vssio_top_6 \
} PVSS2DGZ_V_G


# Bottom side PG
create_cell { \
    vddcore_bottom_1 vddcore_bottom_2 vddcore_bottom_3 \
    vddcore_bottom_4 vddcore_bottom_5 vddcore_bottom_6 \
} PVDD1DGZ_V_G

create_cell { \
    vsscore_bottom_1 vsscore_bottom_2 vsscore_bottom_3 vsscore_bottom_4 \
} PVSS1DGZ_V_G

create_cell { \
    vddio_bottom_1 vddio_bottom_2 vddio_bottom_3 vddio_bottom_4 \
} PVDD2DGZ_V_G

create_cell { \
    vssio_bottom_1 vssio_bottom_2 vssio_bottom_3 \
    vssio_bottom_4 vssio_bottom_5 vssio_bottom_6 \
} PVSS2DGZ_V_G


# Left side PG
create_cell { \
    vddcore_left_1 vddcore_left_2 vddcore_left_3 vddcore_left_4 \
} PVDD1DGZ_H_G

create_cell { \
    vsscore_left_1 vsscore_left_2 vsscore_left_3 \
} PVSS1DGZ_H_G

create_cell { \
    vddio_left_1 vddio_left_2 vddio_left_3 \
} PVDD2DGZ_H_G

create_cell { \
    vssio_left_1 vssio_left_2 vssio_left_3 vssio_left_4 \
} PVSS2DGZ_H_G


# Right side PG
create_cell { \
    vddcore_right_1 vddcore_right_2 vddcore_right_3 vddcore_right_4 \
} PVDD1DGZ_H_G

create_cell { \
    vsscore_right_1 vsscore_right_2 vsscore_right_3 \
} PVSS1DGZ_H_G

create_cell { \
    vddio_right_1 vddio_right_2 vddio_right_3 \
} PVDD2DGZ_H_G

create_cell { \
    vssio_right_1 vssio_right_2 vssio_right_3 vssio_right_4 \
} PVSS2DGZ_H_G


########################################################################
# POC: one and only one in this digital IO domain
########################################################################

create_cell {poc_bottom} PVDD2POC_V_G


########################################################################
# PLL analog supply cells
# PLL VDDHV = 1.8V analog supply, so use PVDD2ANA/PVSS2ANA.
# If these cells are not found, run:
#   get_lib_cells *PVDD2ANA*
#   get_lib_cells *PVSS2ANA*
########################################################################

create_cell {avddhv_pll_1 avddhv_pll_2} PVDD2ANA_V_G
create_cell {avss_pll_1   avss_pll_2  } PVSS2ANA_V_G


########################################################################
# IO order
#
# Top: SPI group.
# Bottom: clk/rst/flag/sel + PLL analog supply, with clk close to PLL.
# Left/right: mostly PG cells, used to keep full IO ring continuous.
########################################################################

set top_ios {
    vssio_top_1
    vddcore_top_1
    vddio_top_1
    vsscore_top_1

    u_pad_mosi
    vssio_top_2
    u_pad_miso
    vddio_top_2
    u_pad_sclk
    vsscore_top_2
    u_pad_cs

    vssio_top_3
    vddcore_top_2
    vddio_top_3
    vddcore_top_3
    vsscore_top_3
    vssio_top_4

    vddcore_top_4
    vddio_top_4
    vsscore_top_4
    vddcore_top_5
    vssio_top_5
    vddcore_top_6
    vssio_top_6
}

set bottom_ios {
    vssio_bottom_1
    vddcore_bottom_1
    poc_bottom
    vddio_bottom_1
    vsscore_bottom_1

    u_pad_flag
    vssio_bottom_2
    u_pad_rst
    vddcore_bottom_2

    u_pad_clk
    avss_pll_1
    avddhv_pll_1
    avddhv_pll_2
    avss_pll_2
    u_pad_sel

    vddio_bottom_2
    vsscore_bottom_2
    vddcore_bottom_3
    vssio_bottom_3

    vddcore_bottom_4
    vddio_bottom_3
    vsscore_bottom_3
    vssio_bottom_4
    vddcore_bottom_5
    vddio_bottom_4
    vsscore_bottom_4
    vddcore_bottom_6
    vssio_bottom_5
    vssio_bottom_6
}

set left_ios {
    vssio_left_1
    vddcore_left_1
    vddio_left_1
    vsscore_left_1

    vssio_left_2
    vddcore_left_2
    vddio_left_2
    vsscore_left_2

    vssio_left_3
    vddcore_left_3
    vddio_left_3
    vsscore_left_3

    vddcore_left_4
    vssio_left_4
}

set right_ios {
    vssio_right_1
    vddcore_right_1
    vddio_right_1
    vsscore_right_1

    vssio_right_2
    vddcore_right_2
    vddio_right_2
    vsscore_right_2

    vssio_right_3
    vddcore_right_3
    vddio_right_3
    vsscore_right_3

    vddcore_right_4
    vssio_right_4
}


########################################################################
# Create IO guides
########################################################################

remove_io_guides -all

create_io_guide \
    -name left_guide \
    -side left \
    -pad_cells $left_ios \
    -line [list [list 0 $IO_DEPTH] $V_SIDE_LEN] \
    -min_pitch $PAD_PITCH

create_io_guide \
    -name top_guide \
    -side top \
    -pad_cells $top_ios \
    -line [list [list $IO_DEPTH $DIE_H] $H_SIDE_LEN] \
    -min_pitch $PAD_PITCH

create_io_guide \
    -name right_guide \
    -side right \
    -pad_cells $right_ios \
    -line [list [list $DIE_W [expr {$DIE_H - $IO_DEPTH}]] $V_SIDE_LEN] \
    -min_pitch $PAD_PITCH

create_io_guide \
    -name bottom_guide \
    -side bottom \
    -pad_cells $bottom_ios \
    -line [list [list [expr {$DIE_W - $IO_DEPTH}] 0] $H_SIDE_LEN] \
    -min_pitch $PAD_PITCH


########################################################################
# Corner cells
#
# General IO document uses PCORNER_G.
# If your library reference is actually PCORNERR, replace PCORNER_G below.
# The document also requires bonded PVSS2DGZ/PVSS3DGZ near corner sides.
########################################################################

create_io_corner_cell -reference_cell PCORNER_G {left_guide  top_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide top_guide}
create_io_corner_cell -reference_cell PCORNER_G {left_guide  bottom_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide bottom_guide}


########################################################################
# Place IO
########################################################################

place_io




########################################################################
# CUP bond pad placement
# Put this block after "place_io" and before "create_io_filler_cells".
#
# Available bond pad cells in your library:
#   PAD50GU / PAD50NU
#   PAD60GU / PAD60NU
#
# This script uses PAD60GU / PAD60NU.
# CUP pad must be placed at the same coordinate as the corresponding IO.
########################################################################

########################################################################
# Pick bond pad reference cells
# Some Milkyway/ICC display may show PAD60GU:2 / PAD60NU:2.
# This proc tries normal names first, then :2 names.
########################################################################

proc pick_lib_ref {candidate_list} {
    foreach ref $candidate_list {
        set c0 [get_lib_cells -quiet */$ref]
        if {[sizeof_collection $c0] > 0} {
            return [get_object_name [index_collection $c0 0]]
        }

        set c1 [get_lib_cells -quiet $ref]
        if {[sizeof_collection $c1] > 0} {
            return [get_object_name [index_collection $c1 0]]
        }
    }

    echo "ERROR: Cannot find any lib cell from: $candidate_list"
    return ""
}

set PAD60GU_REF [pick_lib_ref {PAD60GU PAD60GU:2}]
set PAD60NU_REF [pick_lib_ref {PAD60NU PAD60NU:2}]

if {$PAD60GU_REF == "" || $PAD60NU_REF == ""} {
    echo "ERROR: PAD60GU/PAD60NU reference cells are not found. Please check get_lib_cells *PAD60*"
    return
}

echo "INFO: PAD60GU_REF = $PAD60GU_REF"
echo "INFO: PAD60NU_REF = $PAD60NU_REF"


########################################################################
# Utility: create one CUP bond pad on one IO cell
########################################################################

proc create_cup_pad_on_io {io_inst pad_inst pad_ref} {
    set io_obj [get_cells -quiet $io_inst]

    if {[sizeof_collection $io_obj] == 0} {
        echo "WARN: IO cell $io_inst not found. Skip $pad_inst."
        return
    }

    set old_pad [get_cells -quiet $pad_inst]
    if {[sizeof_collection $old_pad] > 0} {
        echo "INFO: Bond pad $pad_inst already exists. Skip create."
        return
    }

    create_cell $pad_inst $pad_ref

    set pad_obj [get_cells $pad_inst]

    # Copy location from IO cell.
    set io_origin [get_attribute $io_obj origin]
    set io_orient [get_attribute $io_obj orientation]

    # ICC2 usually supports move_objects -to.
    move_objects -to $io_origin $pad_obj

    # Copy orientation if the attribute exists.
    catch {set_attribute $pad_obj orientation $io_orient}

    # Fix the bond pad.
    catch {set_attribute $pad_obj physical_status fixed}
    catch {set_fixed_objects $pad_obj}

    echo "INFO: Place $pad_inst $pad_ref on $io_inst at $io_origin orient=$io_orient"
}


########################################################################
# Utility: create CUP pads for a list of IO cells, alternating GU/NU
########################################################################

proc create_cup_pads_for_list {io_list prefix first_ref second_ref} {
    set idx 0

    foreach io $io_list {
        if {[expr {$idx % 2}] == 0} {
            set pad_ref $first_ref
        } else {
            set pad_ref $second_ref
        }

        set pad_inst ${prefix}_${io}
        create_cup_pad_on_io $io $pad_inst $pad_ref

        incr idx
    }
}


########################################################################
# Bonded IO list
#
# This version puts bond pads on:
#   1. All 8 digital signal IOs
#   2. Digital VDD/VSS IO power/ground cells in the previous IO guide
#   3. PLL VDDHV analog supply cells avddhv_pll_* / avss_pll_*
#
# If you later decide some PG cells are dummy only, remove them from these
# lists so they will not get bond pads/package pins.
########################################################################

set top_bond_ios {
    vssio_top_1
    vddcore_top_1
    vddio_top_1
    vsscore_top_1

    u_pad_mosi
    vssio_top_2
    u_pad_miso
    vddio_top_2
    u_pad_sclk
    vsscore_top_2
    u_pad_cs

    vssio_top_3
    vddcore_top_2
    vddio_top_3
    vddcore_top_3
    vsscore_top_3
    vssio_top_4

    vddcore_top_4
    vddio_top_4
    vsscore_top_4
    vddcore_top_5
    vssio_top_5
    vddcore_top_6
    vssio_top_6
}

set bottom_bond_ios {
    vssio_bottom_1
    vddcore_bottom_1
    poc_bottom
    vddio_bottom_1
    vsscore_bottom_1

    u_pad_flag
    vssio_bottom_2
    u_pad_rst
    vddcore_bottom_2

    u_pad_clk
    avss_pll_1
    avddhv_pll_1
    avddhv_pll_2
    avss_pll_2
    u_pad_sel

    vddio_bottom_2
    vsscore_bottom_2
    vddcore_bottom_3
    vssio_bottom_3

    vddcore_bottom_4
    vddio_bottom_3
    vsscore_bottom_3
    vssio_bottom_4
    vddcore_bottom_5
    vddio_bottom_4
    vsscore_bottom_4
    vddcore_bottom_6
    vssio_bottom_5
    vssio_bottom_6
}

set left_bond_ios {
    vssio_left_1
    vddcore_left_1
    vddio_left_1
    vsscore_left_1

    vssio_left_2
    vddcore_left_2
    vddio_left_2
    vsscore_left_2

    vssio_left_3
    vddcore_left_3
    vddio_left_3
    vsscore_left_3

    vddcore_left_4
    vssio_left_4
}

set right_bond_ios {
    vssio_right_1
    vddcore_right_1
    vddio_right_1
    vsscore_right_1

    vssio_right_2
    vddcore_right_2
    vddio_right_2
    vsscore_right_2

    vssio_right_3
    vddcore_right_3
    vddio_right_3
    vsscore_right_3

    vddcore_right_4
    vssio_right_4
}


########################################################################
# Create CUP bond pads
#
# For top/bottom/left/right, alternate GU/NU to form staggered CUP pads.
# You can swap the first/second ref if package bonding diagram requires.
########################################################################

create_cup_pads_for_list $top_bond_ios    bp_top    $PAD60GU_REF $PAD60NU_REF
create_cup_pads_for_list $bottom_bond_ios bp_bottom $PAD60GU_REF $PAD60NU_REF
create_cup_pads_for_list $left_bond_ios   bp_left   $PAD60GU_REF $PAD60NU_REF
create_cup_pads_for_list $right_bond_ios  bp_right  $PAD60GU_REF $PAD60NU_REF


########################################################################
# Optional reports/checks
########################################################################

echo "INFO: Total CUP bond pads created:"
set bp_cells [get_cells -quiet bp_*]
echo [sizeof_collection $bp_cells]

echo "INFO: Check PAD60 instances:"
get_cells -quiet bp_*

########################################################################
# IO filler insertion
# Wide filler first, then narrow filler.
########################################################################

create_io_filler_cells \
    -reference_cell {PFILLER20_G PFILLER10_G PFILLER5_G PFILLER1_G PFILLER05_G PFILLER0005_G}
#read_def ./script/all_io.def

#create_io_filler_cells -reference_cell {PFILLER20_G PFILLER10_G PFILLER5_G PFILLER1_G PFILLER05_G PFILLER0005_G}

set fixed_objects [get_cells * -filter "ref_name =~ *P*G"]
set fixed_objects [get_flat_cells * -filter "ref_name =~ *P*G"]

#### place macro
#change_selection [get_flat_cells * -filter is_hard_macro==true]
#write_floorplan -object [get_selection ] -force
#read_def ./script/all_macro.def

# »ñÈ¡Ñ¡ÖÐµÄºêµ¥Ôª
set selected_macros [get_selection]
# °´Ãû³ÆÊ××ÖÄ¸ÅÅÐò£¨ºöÂÔ´óÐ¡Ð´£©
set sorted_macros [lsort -dictionary -increasing $selected_macros]

align_objects -objects $sorted_macros -alignment vertical -pitch 10

set macros {
DTCM/RAM_BANK_0__inst_mem
DTCM/RAM_BANK_1__inst_mem

ITCM/RAM_BANK_0__inst_mem
ITCM/RAM_BANK_1__inst_mem

ahb_simd_instance/simd_inst/feature_sram/RAM_BANK_0__mem
ahb_simd_instance/simd_inst/feature_sram/RAM_BANK_1__mem

ahb_simd_instance/simd_inst/weight_sram/RAM_BANK_0__mem
ahb_simd_instance/simd_inst/weight_sram/RAM_BANK_1__mem

ahb_simd_instance/simd_inst/output_sram/RAM_BANK_0__mem
ahb_simd_instance/simd_inst/output_sram/RAM_BANK_1__mem

}
foreach macro $selected_macros {
    set bbox [get_attribute [get_cells $macro] bbox]
    set x0 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 0] 0] - 5]
    set y0 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 0] 1] - 5]
    set x1 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 1] 0] + 5]
    set y1 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 1] 1] + 5]
    create_placement_blockage -type hard -boundary "{{$x0 $y0} {$x1 $y1}}"
}
foreach macro $selected_macros {
    set bbox [get_attribute [get_cells $macro] bbox]
    set point0 [lindex $bbox 0]
    set point1 [lindex $bbox 1]
    set x0_raw [lindex $point0 0]
    set y0_raw [lindex $point0 1]
    set x1_raw [lindex $point1 0]
    set y1_raw [lindex $point1 1]
    set x0 [expr {[string trim $x0_raw] - 5}]
    set y0 [expr {[string trim $y0_raw] - 5}]
    set x1 [expr {[string trim $x1_raw] + 5}]
    set y1 [expr {[string trim $y1_raw] + 5}]
    create_placement_blockage -type hard -boundary [list [list $x0 $y0] [list $x1 $y1]]
}

set macros {
PLLTS28HPMFRAC_inst
}

foreach macro $macros {
    set bbox [get_attribute [get_cells $macro] bbox]
    set x0 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 0] 0] - 20]
    set y0 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 0] 1] - 20]
    set x1 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 1] 0] + 20]
    set y1 [expr [lindex [lindex [get_attr [get_cells $macro] bbox] 1] 1] + 20]
    create_placement_blockage -type hard -boundary "{{$x0 $y0} {$x1 $y1}}"
}
#create_placement_blockage -type hard -boundary {{209.9050 1436.0850} {2614.1550 1688.4750}}
#create_placement_blockage -type hard -boundary {{209.9050 1108.6000} {432.4300 1360.8050}}
#create_placement_blockage -type hard -boundary {{209.9050 832.4650} {432.4300 1084.7000}}
#create_placement_blockage -type hard -boundary {{209.9050 545.1000} {432.4300 796.8000}}


#create_placement_blockage -type hard -boundary {{209.9050 197.8000} {2391.5300 450.0400}}

#create_placement_blockage -type hard -boundary {{2436.1550 838.6000} {2658.6800 1090.8200}}
#create_placement_blockage -type hard -boundary {{2436.1550 566.9700} {2658.6800 819.1000}}

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

#### read scan def
#read_def /storeroom/course/icc2/mcu_synopsys/2_data_preparation/scan_def/mcu_top.scan.def

#### save
save_lib
save_block
save_block -as 3_floorplan1

