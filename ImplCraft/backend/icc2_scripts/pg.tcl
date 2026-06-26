
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






