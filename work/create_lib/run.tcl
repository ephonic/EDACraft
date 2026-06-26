# ICC2 Library Creation Script
# Design: FullSystem

set_host_option -max_cores 64
set TOP_NAME "FullSystem"
set TECH_FILE "/share/home/yangfan/backend_scripts/backend/tf/tsmcn28_10lm7X2ZUTRDL_HVH.tf"

# Reference NDM libraries
set REF_LIBS [list \
    "/share/home/yangfan/backend_scripts/backend/ndm/STDCELL.ndm" \
    "/share/home/yangfan/backend_scripts/backend/ndm/PLL.ndm" \
    "/share/home/yangfan/backend_scripts/backend/ndm/RAMNEW.ndm" \
    "/share/home/yangfan/backend_scripts/backend/ndm/PORT.ndm"
]

create_lib -technology $TECH_FILE -ref_libs $REF_LIBS "work/work_lib/FullSystem.nlib"
open_lib "work/work_lib/FullSystem.nlib"

# Read synthesized netlist
read_verilog -top $TOP_NAME "synthesis/DC/out/FullSystem.v"
current_block $TOP_NAME
link_block

# Derive PG connection
derive_pg_connection -power_net VDD -ground_net VSS

save_lib
exit