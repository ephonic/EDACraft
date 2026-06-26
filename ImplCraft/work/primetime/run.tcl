# PrimeTime STA Sign-off Script
# Design: FullSystem

set_host_options -max_cores 64

# ---- Timing Settings ----
set_app_var timing_enable_multiple_clocks_per_reg true
set_app_var timing_separate_clock_gating_group true
set_app_var timing_use_enhanced_capacitance_modeling true
set_app_var timing_remove_clock_reconvergence_pessimism true
set_app_var timing_crpr_threshold_ps 1.0
set_app_var case_analysis_with_logic_constants true

# ---- Libraries ----
set target_library [list tcbn28hpcplusbwp30p140ffg0p88v0c.db tcbn28hpcplusbwp30p140uhvttt0p9v85c.db tcbn28hpcplusbwp30p140uhvttt0p9v25c.db]
set link_library   [concat * $target_library]

# ---- Read Netlist ----
read_verilog "work/route_opt/out/FullSystem_routed.v"
current_design FullSystem
link

# ---- Read SDC ----
source "work/route_opt/out/FullSystem.sdc"

# ---- Read SPEF ----
read_parasitics -format SPEF "work/route_opt/out/FullSystem.spef"

# ---- Update Timing ----
update_timing

# ---- Setup Timing Analysis ----
report_timing -delay_type max -max_paths 500 -slack_lesser_than 0 \    -path_type full_clock_expanded -significant_digits 4 \    -sort_by slack -nworst 1 \    > ./PT/report/timing_setup.rpt

report_timing -delay_type min -max_paths 500 -slack_lesser_than 0 \    -path_type full_clock_expanded -significant_digits 4 \    -sort_by slack -nworst 1 \    > ./PT/report/timing_hold.rpt

# ---- Path Group Reports ----
foreach pg [get_path_groups *] {
    report_timing -path_group $pg -max_paths 50 \        -slack_lesser_than 0 -sort_by slack \        > ./PT/report/timing_${pg}.rpt
}

# ---- Constraint Violations ----
report_constraint -all_violators -significant_digits 4 \
    > ./PT/report/constraint.rpt
report_constraint -all_violators -max_transition -significant_digits 4 \
    > ./PT/report/constraint_transition.rpt
report_constraint -all_violators -max_capacitance -significant_digits 4 \
    > ./PT/report/constraint_capacitance.rpt
report_constraint -all_violators -max_fanout -significant_digits 4 \
    > ./PT/report/constraint_fanout.rpt

# ---- QoR Summary ----
report_qor -significant_digits 4 > ./PT/report/qor.rpt

# ---- Path Summary for RTL Analysis ----
report_timing -max_paths 100 -nworst 1 -slack_lesser_than 0 \
    -significant_digits 4 -path_type full_clock_expanded \
    -delay_type max -through [all_registers -edge_triggered] \
    -from [all_registers -edge_triggered] \
    > ./PT/report/critical_paths_setup.rpt

report_timing -max_paths 100 -nworst 1 -slack_lesser_than 0 \
    -significant_digits 4 -path_type full_clock_expanded \
    -delay_type min -through [all_registers -edge_triggered] \
    -from [all_registers -edge_triggered] \
    > ./PT/report/critical_paths_hold.rpt

# ---- Cell Statistics ----
report_cell > ./PT/report/cell.rpt
report_threshold_voltage_group > ./PT/report/vt_group.rpt

# ---- ECO Guidance ----
write_eco_changes -format tcl ./PT/out/eco_script.tcl

exit