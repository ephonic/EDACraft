####### restore

####### mcmm
#source -e /storeroom/course/icc2/mcu_synopsys/2_data_preparation/liblist/liblist.tcl
source -e /share/home/limuhan/TSMC28nm_icc2/icc_work/scripts/scripts/mcmm1.tcl



########################################################################
# Pre-CTS: remove propagated clocks
########################################################################

foreach_in_collection mode [all_modes] {
    current_mode $mode
    remove_propagated_clocks [all_clocks]
    remove_propagated_clocks [get_ports]
    remove_propagated_clocks [get_pins -hierarchical]
}


########################################################################
# Timing guardband / uncertainty
# Temporary TT-only derate.
# For final signoff, use true SS/FF libraries instead of large artificial derates.
########################################################################

set_timing_derate -late  1.10 -cell_delay -net_delay -corners wc
set_timing_derate -early 0.88 -cell_delay -net_delay -corners bc

# If you only want extra setup margin:
set_clock_uncertainty -setup 0.050 [get_clocks *clk*]

# Optional hold uncertainty, smaller value
set_clock_uncertainty -hold 0.020 [get_clocks *clk*]


########################################################################
# Utility: safely create PG port/net
########################################################################

proc ensure_pg_port_net {name type} {
    if {![sizeof_collection [get_ports -quiet $name]]} {
        create_port -direction inout $name
    }

    if {![sizeof_collection [get_nets -quiet $name]]} {
        if {$type == "power"} {
            create_net -power $name
        } elseif {$type == "ground"} {
            create_net -ground $name
        } else {
            create_net $name
        }
    }

    set_attribute [get_nets $name] net_type $type
}




####### pg

########################################################################
# Create supply ports/nets
#
# VDD      : 0.9V core/pre-driver
# VSS      : core/pre-driver ground
# VDDPST   : 1.8V digital IO post-driver supply
# VSSPST   : digital IO post-driver ground
# AVDD     : 1.8V analog supply for PLL VDDHV, from PVDD2ANA
# AVSS     : analog ground for PLL/PVSS2ANA, optional but recommended
########################################################################

ensure_pg_port_net VDD    power
ensure_pg_port_net VSS    ground
ensure_pg_port_net VDDPST power
ensure_pg_port_net VSSPST ground
ensure_pg_port_net AVDD   power
ensure_pg_port_net AVSS   ground


########################################################################
# Connect supply ports
########################################################################

connect_pg_net -net VDD    [get_ports VDD]
connect_pg_net -net VSS    [get_ports VSS]
connect_pg_net -net VDDPST [get_ports VDDPST]
connect_pg_net -net VSSPST [get_ports VSSPST]
connect_pg_net -net AVDD   [get_ports AVDD]
connect_pg_net -net AVSS   [get_ports AVSS]

########################################################################
# Connect digital/core PG pins
########################################################################

connect_pg_net -net VDD [get_pins -hierarchical -quiet */VDD]
connect_pg_net -net VSS [get_pins -hierarchical -quiet */VSS]

########################################################################
# Connect digital IO PG pins
########################################################################

connect_pg_net -net VDDPST [get_pins -hierarchical -quiet */VDDPST]
connect_pg_net -net VSSPST [get_pins -hierarchical -quiet */VSSPST]


########################################################################
# PLL power connection
#
# PLL datasheet:
#   VDDHV   = 1.8V analog supply       -> AVDD
#   VDDREF  = 0.9V reference supply    -> VDD, or clean PLL_VDD09
#   VDDPOST = 0.9V post-divider supply -> VDD, or clean PLL_VDD09
#   VSS     = ground/substrate         -> AVSS if using analog ground;
#                                          otherwise VSS.
########################################################################

# 0.9V PLL supplies
connect_pg_net -net VDD [get_pins -quiet PLLTS28HPMFRAC_inst/VDDREF]
connect_pg_net -net VDD [get_pins -quiet PLLTS28HPMFRAC_inst/VDDPOST]

# 1.8V PLL analog supply
connect_pg_net -net AVDD [get_pins -quiet PLLTS28HPMFRAC_inst/VDDHV]

# PLL ground:
# Recommended if you placed PVSS2ANA as analog ground:
connect_pg_net -net AVSS [get_pins -quiet PLLTS28HPMFRAC_inst/VSS]

# If you decide not to use separate AVSS, comment the AVSS line above
# and use this instead:
# connect_pg_net -net VSS [get_pins -quiet PLLTS28HPMFRAC_inst/VSS]


########################################################################
# Connect analog power/ground IO cells used for PLL
#
# Use the instance names from the IO script:
#   avddhv_pll_1 avddhv_pll_2 : PVDD2ANA_V_G
#   avss_pll_1   avss_pll_2   : PVSS2ANA_V_G
########################################################################

connect_pg_net -net AVDD [get_pins -hierarchical -quiet avddhv_pll_*/AVDD]
connect_pg_net -net AVSS [get_pins -hierarchical -quiet avss_pll_*/AVSS]

# Some analog IO cells may also expose VSS/global ESD bus pins.
# Keep global ESD VSS tied to chip VSS if such pins exist.
connect_pg_net -net VSS [get_pins -hierarchical -quiet avddhv_pll_*/VSS]
connect_pg_net -net VSS [get_pins -hierarchical -quiet avss_pll_*/VSS]




########################################################################
# Set voltage for all scenarios/corners
########################################################################

foreach c {wc bc} {
    set_voltage 0.9 -min 0.9 -corners $c -object_list [get_nets VDD]
    set_voltage 0.0 -min 0.0 -corners $c -object_list [get_nets VSS]

    set_voltage 1.8 -min 1.8 -corners $c -object_list [get_nets VDDPST]
    set_voltage 0.0 -min 0.0 -corners $c -object_list [get_nets VSSPST]

    set_voltage 1.8 -min 1.8 -corners $c -object_list [get_nets AVDD]
    set_voltage 0.0 -min 0.0 -corners $c -object_list [get_nets AVSS]
}

########################################################################
# Basic check reports
########################################################################

report_scenarios
report_corners
report_clocks

check_pg_connectivity


