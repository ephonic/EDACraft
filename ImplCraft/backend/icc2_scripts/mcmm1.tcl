
remove_scenarios -all
remove_corners -all
remove_modes -all 
####### func setup
create_mode func
create_corner wc
create_scenario -name func.tt0p9v.wc.cmax_25c.setup -mode func -corner wc
current_scenario func.tt0p9v.wc.cmax_25c.setup
source -e /share/home/limuhan/Projects/BP_TapeOut_WorkSpace/BP_TapeOut_syn/work/DC/out/top.sdc
read_parasitic_tech -tlup /share/home/limuhan/Libraries/TSMC28/cln28hpm_1p10m+ut-alrdl_7x2z_rcworst -layermap /share/home/limuhan/Libraries/TSMC28/star.map_9M -name cmax
set_parasitic_parameters -corners wc -early_spec cmax -late_spec cmax
set_scenario_status func.tt0p9v.wc.cmax_25c.setup -none
set_scenario_status func.tt0p9v.wc.cmax_25c.setup -setup true -max_transition true -max_capacitance true
set_temperature -corners wc 25
if {![sizeof [get_nets -q VDD]]} {create_net -power VDD}
set_voltage 0.9 -min 0.9 -corners wc -object_list [get_supply_nets VDD]
if {![sizeof [get_nets -q VSS]]} {create_net -ground VSS}
set_voltage 0.0 -min 0.0 -corners wc -object_list [get_supply_nets VSS]
#set_process_label -corners wc cmax

####### func hold
create_corner bc
create_scenario -name func.tt0p9v.bc.cmin_25c.hold -mode func -corner bc
current_scenario func.tt0p9v.bc.cmin_25c.hold
source -e /share/home/limuhan/Projects/BP_TapeOut_WorkSpace/BP_TapeOut_syn/work/DC/out/top.sdc
read_parasitic_tech -tlup /share/home/limuhan/Libraries/TSMC28/cln28hpm_1p10m+ut-alrdl_7x2z_cworst -layermap /share/home/limuhan/Libraries/TSMC28/star.map_9M -name cmin
set_parasitic_parameters -corners bc -early_spec cmin -late_spec cmin
set_scenario_status func.tt0p9v.bc.cmin_25c.hold -none
set_scenario_status func.tt0p9v.bc.cmin_25c.hold -hold true
set_temperature -corners bc 25 -min 25
if {![sizeof [get_nets -q VDD]]} {create_net -power VDD}
set_voltage 0.9 -min 0.9 -corners bc -object_list [get_supply_nets VDD]
if {![sizeof [get_nets -q VSS]]} {create_net -ground VSS}
set_voltage 0.0 -min 0.0 -corners bc -object_list [get_supply_nets VSS]
#set_process_label -corners bc cmin
####### scan setup
#create_mode scan
#create_corner wc
#create_scenario -name scan.ss0p99v.wc.cmax_125c.setup -mode scan -corner wc
#current_scenario scan.ss0p99v.wc.cmax_125c.setup
#source -e /storeroom/course/icc2/mcu_synopsys/2_data_preparation/sdc/mcu.scan.sdc
#read_parasitic_tech -tlup $CMAX_TLUP_PLUS_FILE -layermap $TLUPLUS_MAP -name cmax
#set_parasitic_parameters -corners wc -early_spec cmax -late_spec cmax
#set_scenario_status scan.ss0p99v.wc.cmax_125c.setup -none
#set_scenario_status scan.ss0p99v.wc.cmax_125c.setup -setup true -max_transition true -max_capacitance true
#set_temperature -corners wc 125 -min 125
#if {![sizeof [get_nets -q VDD]]} {create_net -power VDD}
#set_voltage 0.99 -min 0.99 -corners wc -object_list [get_supply_nets VDD]
#if {![sizeof [get_nets -q VSS]]} {create_net -power VSS}
#set_voltage 0.0 -min 0.0 -corners wc -object_list [get_supply_nets VSS]
#set_process_label -corners wc cmax

####### scan hold
#create_corner bc
#create_scenario -name scan.ff1p21v.bc.cmin_125c.hold -mode scan -corner bc
#current_scenario scan.ff1p21v.bc.cmin_125c.hold
#source -e /storeroom/course/icc2/mcu_synopsys/2_data_preparation/sdc/mcu.scan.sdc
#read_parasitic_tech -tlup $CMIN_TLUP_PLUS_FILE -layermap $TLUPLUS_MAP -name cmin
#set_parasitic_parameters -corners bc -early_spec cmin -late_spec cmin
#set_scenario_status scan.ff1p21v.bc.cmin_125c.hold -none
#set_scenario_status scan.ff1p21v.bc.cmin_125c.hold -hold true -max_transition true -max_capacitance true
#set_temperature -corners bc 125 -min 125
#if {![sizeof [get_nets -q VDD]]} {create_net -power VDD}
#set_voltage 1.21 -min 1.21 -corners wc -object_list [get_supply_nets VDD]
#if {![sizeof [get_nets -q VSS]]} {create_net -power VSS}
#set_voltage 0.0 -min 0.0 -corners wc -object_list [get_supply_nets VSS]
#set_process_label -corners bc cmin
