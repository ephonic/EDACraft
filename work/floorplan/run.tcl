# ICC2 Floorplan Script
# Design: FullSystem

# ---- Common App Variables ----
set_app_var timing_enable_multiple_clocks_per_reg true
set_app_var timing_separate_clock_gating_group true
set_app_var timing_use_enhanced_capacitance_modeling true
set_app_var timing_remove_clock_reconvergence_pessimism true
set_app_var timing_crpr_threshold_ps 1.0
set_app_var case_analysis_with_logic_constants true
set_app_var physopt_enable_via_res_support true
set_app_var placer_enable_enhanced_soft_blockages true
set_app_var preroute_opt_verbose 160
set_app_var rc_noise_model_mode advanced

set_host_option -max_cores 64

initialize_floorplan \
    -control_type die -shape R \
    -flip_first_row true \
    -boundary {{0 0} {2900.0 1900.0}} \
    -core_offset {180 180 180 180}

# Create boundary cells
create_boundary_cells \
    -left_boundary_cell BOUNDARY_LEFTBWP30P140 \
    -right_boundary_cell BOUNDARY_RIGHTBWP30P140 \
    -bottom_boundary_cells {FILL2BWP30P140UHVT FILL3BWP30P140UHVT} \
    -top_boundary_cells {FILL2BWP30P140UHVT FILL3BWP30P140UHVT} \
    -no_1x

# Macro placement
set_keepout_margin -type hard -outer {5.0 5.0 5.0 5.0} -all_macros
set_fp_placement_strategy -macros_on_edge auto -auto_grouping high -sliver_size 15 -congestion_effort high
create_fp_placement -effort high -congestion_driven

# Pin constraints
set_fp_pin_constraints -block_level -corner_keepout_num_wiretracks 20 \
    -allowed_layers [lrange [get_attribute [get_physical_lib_cells] metal_layers] [lsearch [get_attribute [get_physical_lib_cells] metal_layers] M3] [lsearch [get_attribute [get_physical_lib_cells] metal_layers] M9]]

# PG straps (auto-create)
derive_pg_connection -power_net VDD -ground_net VSS

save_block -as fp
save_lib

# Reports
report_utilization > ./rpt/fp_utilization.rpt
check_legality > ./rpt/fp_legality.rpt

exit