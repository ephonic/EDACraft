########################################################################
# IO placement + staggered CUP bond pad placement
#
# Fixes:
#   1. Force IO physical order after place_io.
#   2. PG IO order uses vddcore/vsscore/vddio/vssio groups.
#   3. CUP bond pads alternate PAD60NU/PAD60GU in physical order.
#   4. Bond pad origin/orientation is exactly copied from corresponding IO cell.
#   5. Safe for second run: delete generated cells/guides first.
########################################################################


########################################################################
# Parameters
########################################################################

set DIE_W      2900
set DIE_H      1900
set IO_DEPTH   110

# CUP staggered pitch. If package requires PAD50, change PAD_PITCH=50
# and change PAD_INNER_CAND/PAD_OUTER_CAND below.
set PAD_PITCH  60

set H_SIDE_LEN [expr {$DIE_W - 2*$IO_DEPTH}]
set V_SIDE_LEN [expr {$DIE_H - 2*$IO_DEPTH}]

# Center IO list on each side instead of starting close to corner.
# Set to 0 if you want to start from guide start point directly.
set CENTER_IO_ON_SIDE 1

# Generated cell cleanup switch.
set CLEAN_PREVIOUS_RUN 1

# Delete corner cells whose ref_name matches this list.
# If your design already has manually created corner cells that should be kept,
# set DELETE_OLD_IO_CORNERS to 0.
set DELETE_OLD_IO_CORNERS 1
set CORNER_REF_LIST {PCORNER_G PCORNERR}


########################################################################
# Utility procs
########################################################################

proc delete_cells_by_patterns {patterns} {
    foreach pat $patterns {
        set objs [get_cells -quiet $pat]
        if {[sizeof_collection $objs] > 0} {
            echo "INFO: Remove existing cells matching $pat"
            catch {set_attribute $objs physical_status placed}
            catch {set_fixed_objects -unfix $objs}
            catch {remove_cells $objs}
        }
    }
}

proc delete_cells_by_ref_patterns {ref_patterns} {
    foreach rpat $ref_patterns {
        set objs ""
        catch {
            set objs [get_cells -quiet -hierarchical -filter "ref_name =~ $rpat"]
        }
        if {$objs != "" && [sizeof_collection $objs] > 0} {
            echo "INFO: Remove existing cells with ref_name =~ $rpat"
            catch {set_attribute $objs physical_status placed}
            catch {set_fixed_objects -unfix $objs}
            catch {remove_cells $objs}
        }
    }
}

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

proc place_cell_exact {cell_name xy orient {status fixed}} {
    set obj [get_cells -quiet $cell_name]

    if {[sizeof_collection $obj] == 0} {
        echo "WARN: place_cell_exact: cell $cell_name not found."
        return
    }

    if {$orient == ""} {
        set orient [get_attribute $obj orientation]
    }

    catch {set_attribute $obj physical_status placed}

    # Preferred ICC2 way.
    set rc [catch {
        set_cell_location -coordinates $xy -orientation $orient -status $status $obj
    } msg]

    # Fallback for environments where set_cell_location options differ.
    if {$rc != 0} {
        catch {set_attribute $obj orientation $orient}

        set old_origin ""
        catch {set old_origin [get_attribute $obj origin]}

        if {[llength $old_origin] == 2} {
            set dx [expr {[lindex $xy 0] - [lindex $old_origin 0]}]
            set dy [expr {[lindex $xy 1] - [lindex $old_origin 1]}]
            if {[catch {move_objects -delta [list $dx $dy] $obj} msg2]} {
                catch {move_objects -to $xy $obj}
                catch {set_attribute $obj origin $xy}
            }
        } else {
            catch {move_objects -to $xy $obj}
            catch {set_attribute $obj origin $xy}
        }

        catch {set_attribute $obj physical_status $status}
        catch {set_fixed_objects $obj}
    }
}

proc force_io_order_on_side {side io_list die_w die_h io_depth pitch center_on_side} {
    set n [llength $io_list]
    if {$n == 0} {
        return
    }

    if {$side == "top" || $side == "bottom"} {
        set side_len [expr {$die_w - 2*$io_depth}]
    } else {
        set side_len [expr {$die_h - 2*$io_depth}]
    }

    set need_len [expr {($n - 1) * $pitch}]

    if {$center_on_side} {
        set offset [expr {($side_len - $need_len) / 2.0}]
        if {$offset < 0} {
            echo "WARN: $side side IO list is longer than available side length."
            set offset 0
        }
    } else {
        set offset 0
    }

    echo "INFO: Force IO order on $side side, n=$n, offset=$offset"

    set idx 0
    foreach io $io_list {
        set obj [get_cells -quiet $io]
        if {[sizeof_collection $obj] == 0} {
            echo "WARN: IO cell $io not found when forcing order."
            incr idx
            continue
        }

        # Keep the orientation generated by place_io.
        set orient [get_attribute $obj orientation]

        switch $side {
            top {
                set x [expr {$io_depth + $offset + $idx * $pitch}]
                set y $die_h
            }
            bottom {
                # Keep the same convention as the original bottom guide:
                # list order goes from right to left.
                set x [expr {$die_w - $io_depth - $offset - $idx * $pitch}]
                set y 0
            }
            left {
                set x 0
                set y [expr {$io_depth + $offset + $idx * $pitch}]
            }
            right {
                # Keep the same convention as the original right guide:
                # list order goes from top to bottom.
                set x $die_w
                set y [expr {$die_h - $io_depth - $offset - $idx * $pitch}]
            }
            default {
                echo "ERROR: Unknown side $side"
                return
            }
        }

        place_cell_exact $io [list $x $y] $orient fixed
        echo "INFO:   $side idx=$idx  $io  origin=[list $x $y] orient=$orient"
        incr idx
    }
}

proc create_cup_pad_on_io {io_inst pad_inst pad_ref} {
    set io_obj [get_cells -quiet $io_inst]

    if {[sizeof_collection $io_obj] == 0} {
        echo "WARN: IO cell $io_inst not found. Skip $pad_inst."
        return
    }

    set old_pad [get_cells -quiet $pad_inst]
    if {[sizeof_collection $old_pad] > 0} {
        echo "INFO: Bond pad $pad_inst already exists. Remove and recreate."
        catch {set_attribute $old_pad physical_status placed}
        catch {set_fixed_objects -unfix $old_pad}
        catch {remove_cells $old_pad}
    }

    create_cell $pad_inst $pad_ref

    set pad_obj [get_cells -quiet $pad_inst]
    if {[sizeof_collection $pad_obj] == 0} {
        echo "ERROR: Failed to create bond pad $pad_inst with ref $pad_ref"
        return
    }

    set io_origin [get_attribute $io_obj origin]
    set io_orient [get_attribute $io_obj orientation]

    # Important:
    # CUP bond pad and I/O driving buffer must have aligned origin/PR boundary.
    # Therefore copy orientation first, then force exact same origin.
    place_cell_exact $pad_inst $io_origin $io_orient fixed

    set pad_origin [get_attribute $pad_obj origin]
    set pad_orient [get_attribute $pad_obj orientation]

    echo "INFO: Place $pad_inst ref=$pad_ref on $io_inst origin=$io_origin orient=$io_orient"

    if {$pad_origin != $io_origin || $pad_orient != $io_orient} {
        echo "WARN: Origin/orient mismatch: IO=$io_inst origin=$io_origin orient=$io_orient ; PAD=$pad_inst origin=$pad_origin orient=$pad_orient"
    }
}

proc create_cup_pads_for_list {io_list prefix inner_ref outer_ref} {
    set idx 0

    foreach io $io_list {
        # Staggered sequence:
        #   even index: PAD60NU = inner pad, close to core
        #   odd  index: PAD60GU = outer pad, close to die edge
        #
        # The cell orientation is copied from the IO cell, so for each side
        # PAD60NU should extend toward core and PAD60GU toward die edge.
        if {[expr {$idx % 2}] == 0} {
            set pad_ref $inner_ref
            set pad_tag "NU"
        } else {
            set pad_ref $outer_ref
            set pad_tag "GU"
        }

        set pad_inst ${prefix}_${idx}_${pad_tag}_${io}
        create_cup_pad_on_io $io $pad_inst $pad_ref

        incr idx
    }
}


########################################################################
# Cleanup for second run
########################################################################

if {$CLEAN_PREVIOUS_RUN} {
    echo "INFO: Cleanup previous IO guides/fillers/generated cells."

    catch {remove_io_filler_cells -all}
    catch {remove_io_guides -all}

    delete_cells_by_patterns {
        bp_*

        vddcore_top_*    vsscore_top_*    vddio_top_*    vssio_top_*
        vddcore_bottom_* vsscore_bottom_* vddio_bottom_* vssio_bottom_*
        vddcore_left_*   vsscore_left_*   vddio_left_*   vssio_left_*
        vddcore_right_*  vsscore_right_*  vddio_right_*  vssio_right_*

        poc_bottom
        avddhv_pll_* avss_pll_*
    }

    if {$DELETE_OLD_IO_CORNERS} {
        delete_cells_by_ref_patterns $CORNER_REF_LIST
    }
}


########################################################################
# User signal pads already exist in netlist:
#   u_pad_clk u_pad_rst u_pad_sclk u_pad_mosi
#   u_pad_cs u_pad_flag u_pad_miso u_pad_sel
########################################################################


########################################################################
# Create digital IO P/G cells
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
########################################################################

create_cell {avddhv_pll_1 avddhv_pll_2} PVDD2ANA_V_G
create_cell {avss_pll_1   avss_pll_2  } PVSS2ANA_V_G


########################################################################
# IO order
#
# PG cells are arranged as much as possible in this repeated group:
#   vddcore, vsscore, vddio, vssio
#
# POC belongs to the IO VDD domain, so it is used as one vddio-domain slot.
########################################################################

set top_ios {
    vddcore_top_1
    vsscore_top_1
    vddio_top_1
    vssio_top_1

    u_pad_mosi

    vddcore_top_2
    vsscore_top_2
    vddio_top_2
    vssio_top_2

    u_pad_miso
    u_pad_sclk
    u_pad_cs

    vddcore_top_3
    vsscore_top_3
    vddio_top_3
    vssio_top_3

    vddcore_top_4
    vsscore_top_4
    vddio_top_4
    vssio_top_4

    vddcore_top_5
    vssio_top_5

    vddcore_top_6
    vssio_top_6
}

set bottom_ios {
    vddcore_bottom_1
    vsscore_bottom_1
    poc_bottom
    vssio_bottom_1

    u_pad_flag

    vddcore_bottom_2
    vsscore_bottom_2
    vddio_bottom_1
    vssio_bottom_2

    u_pad_rst

    vddcore_bottom_3
    vsscore_bottom_3
    vddio_bottom_2
    vssio_bottom_3

    u_pad_clk

    avss_pll_1
    avddhv_pll_1
    avddhv_pll_2
    avss_pll_2

    u_pad_sel

    vddcore_bottom_4
    vsscore_bottom_4
    vddio_bottom_3
    vssio_bottom_4

    vddcore_bottom_5
    vddio_bottom_4
    vssio_bottom_5

    vddcore_bottom_6
    vssio_bottom_6
}

set left_ios {
    vddcore_left_1
    vsscore_left_1
    vddio_left_1
    vssio_left_1

    vddcore_left_2
    vsscore_left_2
    vddio_left_2
    vssio_left_2

    vddcore_left_3
    vsscore_left_3
    vddio_left_3
    vssio_left_3

    vddcore_left_4
    vssio_left_4
}

set right_ios {pu
    vddcore_right_1
    vsscore_right_1
    vddio_right_1
    vssio_right_1

    vddcore_right_2
    vsscore_right_2
    vddio_right_2
    vssio_right_2

    vddcore_right_3
    vsscore_right_3
    vddio_right_3
    vssio_right_3

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
########################################################################

create_io_corner_cell -reference_cell PCORNER_G {left_guide  top_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide top_guide}
create_io_corner_cell -reference_cell PCORNER_G {left_guide  bottom_guide}
create_io_corner_cell -reference_cell PCORNER_G {right_guide bottom_guide}


########################################################################
# Initial place_io
########################################################################

place_io


########################################################################
# Force IO physical order after place_io
#
# This is the key fix for:
#   "set IO list order is not respected by actual placement"
########################################################################

force_io_order_on_side top    $top_ios    $DIE_W $DIE_H $IO_DEPTH $PAD_PITCH $CENTER_IO_ON_SIDE
force_io_order_on_side bottom $bottom_ios $DIE_W $DIE_H $IO_DEPTH $PAD_PITCH $CENTER_IO_ON_SIDE
force_io_order_on_side left   $left_ios   $DIE_W $DIE_H $IO_DEPTH $PAD_PITCH $CENTER_IO_ON_SIDE
force_io_order_on_side right  $right_ios  $DIE_W $DIE_H $IO_DEPTH $PAD_PITCH $CENTER_IO_ON_SIDE


########################################################################
# Pick CUP bond pad reference cells
#
# PAD60NU = inner pad, close to core.
# PAD60GU = outer pad, close to die edge.
########################################################################

set PAD_INNER_CAND {PAD60NU PAD60NU:2}
set PAD_OUTER_CAND {PAD60GU PAD60GU:2}

set PAD60NU_REF [pick_lib_ref $PAD_INNER_CAND]
set PAD60GU_REF [pick_lib_ref $PAD_OUTER_CAND]

if {$PAD60NU_REF == "" || $PAD60GU_REF == ""} {
    echo "ERROR: PAD60NU/PAD60GU reference cells are not found. Please check:"
    echo "       get_lib_cells *PAD60*"
    error "Missing CUP bond pad lib cells."
}

echo "INFO: PAD60NU_REF = $PAD60NU_REF"
echo "INFO: PAD60GU_REF = $PAD60GU_REF"


########################################################################
# Bonded IO lists
#
# Use the same physical-order list as IO placement.
# Because IO locations have been forced above, this list order equals
# physical order on the side.
########################################################################

set top_bond_ios    $top_ios
set bottom_bond_ios $bottom_ios
set left_bond_ios   $left_ios
set right_bond_ios  $right_ios


########################################################################
# Create staggered CUP bond pads
#
# Sequence:
#   PAD60NU, PAD60GU, PAD60NU, PAD60GU, ...
#
# For your bottom side:
#   top    = core
#   bottom = die edge
#
# Therefore:
#   PAD60NU is the larger/inner pad extending toward core.
#   PAD60GU is the shorter/outer pad closer to die edge.
########################################################################

create_cup_pads_for_list $top_bond_ios    bp_top    $PAD60NU_REF $PAD60GU_REF
create_cup_pads_for_list $bottom_bond_ios bp_bottom $PAD60NU_REF $PAD60GU_REF
create_cup_pads_for_list $left_bond_ios   bp_left   $PAD60NU_REF $PAD60GU_REF
create_cup_pads_for_list $right_bond_ios  bp_right  $PAD60NU_REF $PAD60GU_REF


########################################################################
# Reports/checks
########################################################################

echo "INFO: Total CUP bond pads created:"
set bp_cells [get_cells -quiet bp_*]
echo [sizeof_collection $bp_cells]

echo "INFO: PAD60 bond pad instances:"
get_cells -quiet bp_*

echo "INFO: Check IO origins:"
foreach side {top bottom left right} {
    set list_var ${side}_bond_ios
    set idx 0
    foreach io [set $list_var] {
        set io_obj [get_cells -quiet $io]
        if {[sizeof_collection $io_obj] > 0} {
            echo "INFO: $side idx=$idx IO=$io origin=[get_attribute $io_obj origin] orient=[get_attribute $io_obj orientation]"
        }
        incr idx
    }
}

echo "INFO: IO placement and staggered CUP bond pad placement completed."
