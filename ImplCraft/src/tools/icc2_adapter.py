"""
ICC2 Adapter — physical implementation stages.

Industrial features:
- Multi-VT library with VT percentage constraints
- Cell insertion (endcap, welltap, pre/post decap, spare, ECO)
- Timing derate (OCV)
- Advanced placement options (VT spacing, OD spacing, legalizer)
- CTS with target_skew, target_early_delay, inter-clock balance
- Routing SI analysis (crosstalk prevention, static noise, timing window)
- Via optimization, antenna fixing, search-repair loops
- Congestion control with max_utilization
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignState, FlowStage, StageResult, StageStatus,
    TimingMetrics, AreaMetrics, RouteMetrics, PowerMetrics,
)
from .base import ToolAdapter

logger = logging.getLogger("ic_backend")


class ICC2Adapter(ToolAdapter):
    """
    ICC2 adapter supporting multiple physical implementation sub-stages.

    Sub-stages:
      - create_lib
      - floorplan
      - placement
      - cts (clock tree synthesis)
      - routing
      - route_opt
    """
    tool_name = "ICC2"
    stage = FlowStage.PLACEMENT
    env_script = "/share/apps/EDAs/syn22.bash"

    def __init__(self, state: DesignState, sub_stage: str = "placement"):
        super().__init__(state)
        self.sub_stage = sub_stage
        self._stage_map = {
            "create_lib": FlowStage.INIT,
            "floorplan": FlowStage.FLOORPLAN,
            "placement": FlowStage.PLACEMENT,
            "cts": FlowStage.CTS,
            "routing": FlowStage.ROUTING,
            "route_opt": FlowStage.ROUTE_OPT,
        }
        self.stage = self._stage_map.get(sub_stage, FlowStage.PLACEMENT)

    def _get_shell_cmd(self) -> str:
        return "icc2_shell -no_gui"

    def setup_work_dir(self, stage_name: str | None = None) -> Path:
        name = stage_name or f"icc2_{self.sub_stage}"
        return super().setup_work_dir(name)

    def generate_script(self) -> str:
        gen_map = {
            "create_lib": self._gen_create_lib,
            "floorplan": self._gen_floorplan,
            "placement": self._gen_placement,
            "cts": self._gen_cts,
            "routing": self._gen_routing,
            "route_opt": self._gen_route_opt,
        }
        gen_func = gen_map.get(self.sub_stage)
        if gen_func is None:
            raise ValueError(f"Unknown ICC2 sub-stage: {self.sub_stage}")
        return gen_func()

    def parse_results(self) -> None:
        result = self.state.get_stage_result(self.stage)
        if self.work_dir is None:
            return

        rpt_dir = self.work_dir / "rpt"
        log_dir = self.work_dir / "log"

        for fname in rpt_dir.glob("*.rpt"):
            content = fname.read_text(errors="ignore")
            if "timing" in fname.stem.lower() or "report_timing" in fname.stem.lower():
                self._parse_timing_report(content, result)
            elif "congestion" in fname.stem.lower():
                self._parse_congestion(content, result)
            elif "utilization" in fname.stem.lower():
                self._parse_utilization(content, result)
            elif "qor" in fname.stem.lower():
                self._parse_qor_summary(content, result)

        out_dir = self.work_dir / "out"
        if out_dir.exists():
            for f in out_dir.iterdir():
                self.state.record_artifact(
                    f"icc2_{self.sub_stage}_{f.stem}", str(f)
                )

    # ----------------------------------------------------------------
    # Tcl Script Generators
    # ----------------------------------------------------------------

    def _gen_common_app_vars(self) -> list[str]:
        """Generate common app_var settings for all ICC2 stages."""
        cfg = self.state.config
        lines = [
            "# ---- Common App Variables ----",
            "set_app_var timing_enable_multiple_clocks_per_reg true",
            "set_app_var timing_separate_clock_gating_group true",
            "set_app_var timing_use_enhanced_capacitance_modeling true",
            "set_app_var timing_remove_clock_reconvergence_pessimism true",
            "set_app_var timing_crpr_threshold_ps 1.0",
            "set_app_var case_analysis_with_logic_constants true",
            "set_app_var physopt_enable_via_res_support true",
            "set_app_var placer_enable_enhanced_soft_blockages true",
            "set_app_var preroute_opt_verbose 160",
            "set_app_var rc_noise_model_mode advanced",
            "",
        ]

        # Timing derate
        if cfg.timing_derate.late_factor != 1.0 or cfg.timing_derate.early_factor != 1.0:
            lines.append("# ---- Timing Derate (OCV) ----")
            lines.append(f"set_timing_derate {cfg.timing_derate.late_factor} -late")
            lines.append(f"set_timing_derate {cfg.timing_derate.early_factor} -early")
            if cfg.timing_derate.late_clock_factor is not None:
                lines.append(f"set_timing_derate {cfg.timing_derate.late_clock_factor} -late -clock -cell_delay")
                lines.append(f"set_timing_derate {cfg.timing_derate.early_clock_factor} -early -clock -cell_delay")
            lines.append("report_timing_derate")
            lines.append("")

        return lines

    def _gen_create_lib(self) -> str:
        cfg = self.state.config
        lines = [
            f"# ICC2 Library Creation Script",
            f"# Design: {cfg.design_name}",
            "",
            f'set_host_option -max_cores 64',
            f'set TOP_NAME "{cfg.top_module}"',
            f'set TECH_FILE "{cfg.pdk.tech_file}"',
            "",
            "# Reference NDM libraries",
        ]

        ndm_list = " \\\n    ".join(f'"{p}"' for p in cfg.libraries.ndm_libs)
        lines.append(f"set REF_LIBS [list \\\n    {ndm_list}\n]")
        lines.append("")

        lib_path = str(Path(self.state.work_root) / "work_lib" / f"{cfg.design_name}.nlib")
        lines.extend([
            f'create_lib -technology $TECH_FILE -ref_libs $REF_LIBS "{lib_path}"',
            f'open_lib "{lib_path}"',
            "",
            "# Read synthesized netlist",
        ])

        syn_verilog = self.state.get_artifact("syn_v") or ""
        if not syn_verilog:
            syn_verilog = f"synthesis/DC/out/{cfg.design_name}.v"
        lines.extend([
            f'read_verilog -top $TOP_NAME "{syn_verilog}"',
            f"current_block $TOP_NAME",
            "link_block",
            "",
            "# Derive PG connection",
            f"derive_pg_connection -power_net {cfg.placement.power_net} -ground_net {cfg.placement.ground_net}",
            "",
            "save_lib",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_floorplan(self) -> str:
        cfg = self.state.config
        w, h = cfg.die_width_um, cfg.die_height_um
        offsets = cfg.core_offset_um
        lines = [
            f"# ICC2 Floorplan Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_common_app_vars())
        lines.extend([
            f"set_host_option -max_cores 64",
            "",
            f"initialize_floorplan \\",
            f"    -control_type die -shape R \\",
            f"    -flip_first_row true \\",
            f"    -boundary {{{{0 0}} {{{w} {h}}}}} \\",
            f"    -core_offset {{{offsets[0]} {offsets[1]} {offsets[2]} {offsets[3]}}}",
            "",
        ])

        # Boundary cells
        left_cell = cfg.libraries.boundary_cells.get("left", "BOUNDARY_LEFTBWP30P140")
        right_cell = cfg.libraries.boundary_cells.get("right", "BOUNDARY_RIGHTBWP30P140")
        lines.extend([
            "# Create boundary cells",
            f"create_boundary_cells \\",
            f"    -left_boundary_cell {left_cell} \\",
            f"    -right_boundary_cell {right_cell} \\",
            f"    -bottom_boundary_cells {{FILL2BWP30P140UHVT FILL3BWP30P140UHVT}} \\",
            f"    -top_boundary_cells {{FILL2BWP30P140UHVT FILL3BWP30P140UHVT}} \\",
            f"    -no_1x",
            "",
        ])

        # Tap cells
        if cfg.placement.insert_welltap and cfg.libraries.tap_cell:
            lines.extend([
                "# Create tap cells",
                f"create_tap_cells -lib_cell {cfg.libraries.tap_cell} -distance {cfg.placement.tap_distance_um} -pattern stagger -skip_fixed_cells",
                "",
            ])

        # Macro placement
        if cfg.placement.auto_macro_placement:
            lines.extend([
                "# Macro placement",
                f"set_keepout_margin -type hard -outer {{{cfg.placement.macro_keepout_margin[0]} {cfg.placement.macro_keepout_margin[1]} {cfg.placement.macro_keepout_margin[2]} {cfg.placement.macro_keepout_margin[3]}}} -all_macros",
                "set_fp_placement_strategy -macros_on_edge auto -auto_grouping high -sliver_size 15 -congestion_effort high",
                "create_fp_placement -effort high -congestion_driven",
                "",
            ])

        # Pin constraints
        lines.extend([
            "# Pin constraints",
            f"set_fp_pin_constraints -block_level -corner_keepout_num_wiretracks 20 \\",
            f"    -allowed_layers [lrange [get_attribute [get_physical_lib_cells] metal_layers] [lsearch [get_attribute [get_physical_lib_cells] metal_layers] M3] [lsearch [get_attribute [get_physical_lib_cells] metal_layers] {cfg.pdk.max_routing_layer}]]",
            "",
            "# PG straps (auto-create)",
            f"derive_pg_connection -power_net {cfg.placement.power_net} -ground_net {cfg.placement.ground_net}",
            "",
            "save_block -as fp",
            "save_lib",
            "",
            "# Reports",
            "report_utilization > ./rpt/fp_utilization.rpt",
            "check_legality > ./rpt/fp_legality.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_placement(self) -> str:
        cfg = self.state.config
        lines = [
            f"# ICC2 Placement Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_common_app_vars())
        lines.extend([
            f"set_host_option -max_cores 64 -num_process 8",
            "",
            "# Scenario setup",
            f'set active_scenarios "{cfg.scenario}"',
            f"set_scenario_status -active false [get_scenarios -filter active]",
            f"set_scenario_status -active true $active_scenarios",
            f"current_scenario $active_scenarios",
            "",
            "# Cell list — enable all cells",
            "set_dont_touch [get_lib_cells */*] false",
            "set_attribute [get_lib_cells */*] dont_use false",
        ])

        if cfg.libraries.dont_use_cells:
            lines.append("")
            lines.append("# Dont-use cells")
            for cell in cfg.libraries.dont_use_cells:
                lines.append(f'set_lib_cell_purpose -exclude all [get_lib_cells {{*/{cell}}}]')

        # VT percentage constraints
        if cfg.libraries.vt_percentage_constraint:
            lines.append("")
            lines.append("# VT percentage constraints")
            for vt_name, percentage in cfg.libraries.vt_percentage_constraint.items():
                lines.append(f'set_multi_vth_constraint -type hard -cost area -lvth_groups [get_lib_cells */*{vt_name}*] -lvth_percentage {percentage} -include_blackboxes')

        # Advanced placement options
        lines.extend([
            "",
            "# ---- Advanced Placement Options ----",
            f"set_app_var placer_max_cell_density_threshold {cfg.placement.max_cell_density_threshold}",
            f"set_app_var placer_congestion_effort {cfg.placement.congestion_effort}",
            f"set placer_target_routing_density {cfg.placement.target_routing_density}",
            f"set_congestion_options -max_util {cfg.placement.target_utilization}",
            "",
            "# VT min area placement",
            f"set legalizer_consider_vth_spacing {str(cfg.placement.consider_vt_spacing).lower()}",
            f"set legalizer_min_VT_filler_size {cfg.placement.vt_min_filler_size}",
            f"set legalizer_support_min_vth_spacing true",
            f"set legalizer_advanced_tech_flow true",
            f"set legalizer_consider_continuous_OD_spacing {str(cfg.placement.consider_continuous_od_spacing).lower()}",
            f"set legalizer_consider_PODE_spacing {str(cfg.placement.consider_pode_spacing).lower()}",
            "",
        ])

        # Cell insertion
        if cfg.placement.insert_endcap and cfg.libraries.endcap_cell:
            lines.append(f"# Insert endcap cells")
            lines.append(f"set_endcap_cells -lib_cell {cfg.libraries.endcap_cell}")
            lines.append("")

        if cfg.placement.insert_predecap and cfg.libraries.decap_cells:
            lines.append(f"# Insert pre-decap cells")
            decap_list = " ".join(cfg.libraries.decap_cells)
            lines.append(f"insert_decap_cells -lib_cells [list {decap_list}]")
            lines.append("")

        # Path groups
        lines.extend([
            "# Path groups",
            "remove_path_group [get_object_name [get_path_groups * -filter {name!~*default*}]]",
            "remove_path_group [get_object_name [get_path_groups *]]",
            "set clock_ports [get_ports *clk*]",
            "set all_icgs [get_flat_cells -filter {is_integrated_clock_gating_cell==true}]",
            "set non_clk_inputs [remove_from_collection [all_inputs] $clock_ports]",
            "set all_regs [remove_from_collection [all_registers] $all_icgs]",
            "group_path -name input -from $non_clk_inputs",
            "group_path -name output -to [all_outputs]",
            "group_path -name reg2icg -from $all_regs -to $all_icgs",
            "group_path -name reg2reg -from $all_regs -to $all_regs",
            "",
            "# Routing layers",
            f'set_ignored_layers -min_routing_layer {cfg.pdk.min_routing_layer} -max_routing_layer {cfg.pdk.max_routing_layer}',
            "",
            "# Placement options",
            'set_app_options -name place.coarse.continue_on_missing_scandef -value true',
            'set_app_options -name place.coarse.max_density -value 0.1',
            'set_app_options -name place.coarse.enhanced_auto_density_control -value false',
            'set_app_options -name place.coarse.icg_auto_bound -value true',
            'set_app_options -name opt.power.mode -value leakage',
            'set_app_options -name opt.power.effort -value high',
            'set_app_options -name opt.timing.effort -value high',
            'set_app_options -name opt.common.max_fanout -value 30',
            f'set_app_options -name opt.common.max_net_length -value {cfg.placement.max_net_length_um}',
            "",
            "# Spacing rules",
            "remove_placement_spacing_rules -all",
            'set_placement_spacing_label -name X -side both -lib_cells [get_lib_cells */*]',
            "set_placement_spacing_rule -labels {X X} {0 1}",
            "",
            "# Place",
            "create_placement -congestion",
            "place_opt",
            "",
        ])

        # Standard-cell PG rails (required for LVS connectivity)
        lines.extend(self._gen_pg_rails())

        lines.extend([
            "# Save",
            'save_block -as place',
            "save_lib",
            "",
            "# Reports",
            "report_congestion > ./rpt/place_congestion.rpt",
            "report_utilization > ./rpt/place_utilization.rpt",
            "report_design -nosplit > ./rpt/place_report_design.rpt",
            "check_legality > ./rpt/check_legality.rpt",
            "report_qor -summary > ./rpt/report_qor.summary.rpt",
            "report_timing -nosplit -report_by scenario -transition_time -capacitance \\",
            "    -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute \\",
            "    -derate -voltage -delay_type max > ./rpt/place_timing.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_pg_rails(self) -> list[str]:
        """Generate ICC2 standard-cell power/ground rail commands."""
        cfg = self.state.config
        vdd = cfg.placement.power_net
        vss = cfg.placement.ground_net
        rail_layer = getattr(cfg.pdk, "std_cell_rail_layer", "M1")
        rail_width = getattr(cfg.pdk, "std_cell_rail_width", "0.15")
        return [
            "# ---- Standard-cell PG rail generation ----",
            "# Clean up any stale PG strategies/patterns from previous runs.",
            "catch {remove_pg_strategies -all}",
            "catch {remove_pg_patterns -all}",
            "catch {remove_pg_via_master_rules -all}",
            "catch {remove_pg_strategy_via_rules -all}",
            "catch {remove_routes -net_types {power ground} -ring -stripe -macro_pin_connect -lib_cell_pin_connect}",
            "",
            f"# Create the std-cell rail pattern on {rail_layer} so every row",
            f"# gets a {vdd}/{vss} follow-pin that overlaps the std-cell pins.",
            f'create_pg_std_cell_conn_pattern std_cell_rail_pattern -layer {rail_layer} -rail_width {rail_width}',
            "",
            f"# Apply the rail pattern to {vdd} and {vss}, extending to the",
            f"# design boundary and creating top-level pins for LVS.",
            f'set_pg_strategy std_cell_rails -core \\',
            f'    -pattern {{{{name: std_cell_rail_pattern}}{{nets: {{{vdd} {vss}}}}}}} \\',
            '    -extension {{stop: design_boundary_and_generate_pin}}',
            "",
            "compile_pg -strategies std_cell_rails",
            "",
            "check_pg_connectivity > ./rpt/pg_connectivity.rpt",
            "report_pg_strategies > ./rpt/pg_strategies.rpt",
            "",
        ]

    def _gen_cts(self) -> str:
        cfg = self.state.config
        lines = [
            f"# ICC2 CTS (Clock Tree Synthesis) Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_common_app_vars())
        lines.extend([
            f"set_host_option -max_cores 64 -num_process 8",
            "",
            f'set active_scenarios "{cfg.scenario}"',
            f"set_scenario_status -active false [get_scenarios -filter active]",
            f"set_scenario_status -active true $active_scenarios",
            f"current_scenario $active_scenarios",
            "",
            f"set_ignored_layers -min_routing_layer {cfg.pdk.min_routing_layer} -max_routing_layer {cfg.pdk.max_routing_layer}",
            "",
            "# ---- CTS Options ----",
            f"set_app_options -name opt.power.mode -value leakage",
            f"set_app_options -name opt.power.effort -value high",
            f"set_app_options -name opt.timing.effort -value high",
            f"set_app_options -name opt.common.max_fanout -value 24",
            f"set_app_options -name opt.common.max_net_length -value 150",
            f"set_app_options -name clock_opt.flow.enable_ccd -value false",
            "",
            "# ---- Clock Tree Options ----",
        ])

        # Clock tree options
        cts_opts = ["set_clock_tree_options"]
        cts_opts.append(f"    -target_skew {cfg.cts.target_skew_ns}")
        cts_opts.append(f"    -target_early_delay {cfg.cts.target_early_delay_ns}")
        if cfg.cts.max_transition_ns is not None:
            cts_opts.append(f"    -max_transition {cfg.cts.max_transition_ns}")
        if cfg.cts.max_fanout is not None:
            cts_opts.append(f"    -max_fanout {cfg.cts.max_fanout}")
        if cfg.cts.leaf_max_transition_ns is not None:
            cts_opts.append(f"    -leaf_max_transition {cfg.cts.leaf_max_transition_ns}")
        cts_opts.append(f"    -use_leaf_max_transition_on_macros {str(cfg.cts.use_leaf_max_transition_on_macros).lower()}")
        if cfg.cts.max_rc_delay_ns is not None:
            cts_opts.append(f"    -max_rc_delay_constraint {cfg.cts.max_rc_delay_ns}")
        cts_opts.append(f"    -ocv_clustering {str(cfg.cts.ocv_clustering).lower()}")
        cts_opts.append(f"    -ocv_path_sharing {str(cfg.cts.ocv_path_sharing).lower()}")
        cts_opts.append(f"    -logic_level_balance {str(cfg.cts.logic_level_balance).lower()}")
        if cfg.cts.routing_layers:
            cts_opts.append(f"    -layer_list {{ {' '.join(cfg.cts.routing_layers)} }}")
        lines.append(" \\\n".join(cts_opts))
        lines.append("")

        # Remove ideal network for CTS clocks
        if cfg.clocks:
            cts_clocks = [c for c in cfg.clocks if c.clock_type == "CTS"]
            if cts_clocks:
                clk_names = " ".join(c.name for c in cts_clocks)
                lines.append(f"# Remove ideal network for CTS clocks")
                lines.append(f"remove_ideal_network [all_fanout -flat -from [get_attribute [get_clocks {{ {clk_names} }}] sources]]")
                lines.append("")

        lines.extend([
            "# Build clock",
            "clock_opt -from build_clock -to build_clock",
            "clock_opt -from route_clock -to route_clock",
            "",
        ])

        # Guard final_opto: in GRE mode, running it twice errors out.
        # Use catch to make it non-fatal and only run once.
        if not getattr(cfg.cts, 'skip_redundant_final_opto', False):
            lines.extend([
                "# Final optimization (guarded — GRE mode disallows repeated iterations)",
                "if {[catch {clock_opt -from final_opto -to final_opto} err_msg]} {",
                '    puts "WARNING: final_opto skipped: $err_msg",',
                "}",
                "",
            ])

        lines.append("")

        # Inter-clock balance
        if cfg.cts.inter_clock_balance:
            lines.extend([
                "# Inter-clock balance",
                "balance_inter_clock_delay",
                "",
            ])

        # Fix hold
        lines.extend([
            "# Fix hold",
            "set_fix_hold [all_clocks]",
            "",
            'save_block -as cts',
            "save_lib",
            "",
            "# Reports",
            "report_congestion > ./rpt/cts_congestion.rpt",
            "report_utilization > ./rpt/cts_utilization.rpt",
            "report_clock > ./rpt/cts_clock.rpt",
            "report_clock_timing -type skew > ./rpt/cts_clock_skew.rpt",
            "report_timing -nosplit -report_by scenario -transition_time -capacitance \\",
            "    -physical -nets -input_pins -nworst 1 -max_paths 200 -attribute \\",
            "    -derate -voltage -delay_type max > ./rpt/cts_timing.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_routing(self) -> str:
        cfg = self.state.config
        lines = [
            f"# ICC2 Routing Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_common_app_vars())
        lines.extend([
            f"set_host_option -max_cores 64 -num_process 8",
            "",
            f'set active_scenarios "{cfg.scenario}"',
            f"set_scenario_status -active false [get_scenarios -filter active]",
            f"set_scenario_status -active true $active_scenarios",
            f"current_scenario $active_scenarios",
            "",
            f"set_ignored_layers -min_routing_layer {cfg.pdk.min_routing_layer} -max_routing_layer {cfg.pdk.max_routing_layer}",
            "",
            "# ---- Routing Common Options ----",
            f"set_route_zrt_common_options -route_soft_rule_effort_level low",
            f"set_route_zrt_common_options -post_detail_route_fix_soft_violations true",
            f"set_route_zrt_common_options -post_eco_route_fix_soft_violations true",
            f"set_route_zrt_common_options -concurrent_redundant_via_mode off",
            f"set_route_zrt_common_options -concurrent_redundant_via_effort_level {cfg.routing.redundant_via_insertion}",
            f"set_route_zrt_common_options -read_user_metal_blockage_layer true",
            f"set_route_zrt_common_options -global_min_layer_mode {cfg.pdk.min_layer_mode}",
            f"set_route_zrt_common_options -global_max_layer_mode {cfg.pdk.max_layer_mode}",
            "",
            "# ---- Global Route Options ----",
            f"set_route_zrt_global_options -crosstalk_driven {str(cfg.routing.crosstalk_driven).lower()}",
            f"set_route_zrt_global_options -effort {cfg.routing.timing_driven_effort}",
            f"set_route_zrt_global_options -timing_driven {str(cfg.routing.timing_driven).lower()}",
            f"set_route_zrt_global_options -timing_driven_effort_level {cfg.routing.timing_driven_effort}",
            f"set_route_zrt_global_options -exclude_blocked_gcells_from_congestion_report true",
            "",
            "# ---- Track Assign Options ----",
            f"set_route_zrt_track_options -crosstalk_driven {str(cfg.routing.track_crosstalk_driven).lower()}",
            f"set_route_zrt_track_options -timing_driven {str(cfg.routing.track_timing_driven).lower()}",
            "",
            "# ---- Detail Route Options ----",
            f"set_route_zrt_detail_options -generate_extra_off_grid_pin_tracks {str(cfg.routing.generate_off_grid_pin_tracks).lower()}",
            f"set_route_zrt_detail_options -repair_shorts_over_macros_effort_level {cfg.routing.repair_shorts_over_macros_effort}",
            f"set_route_zrt_detail_options -optimize_wire_via_effort_level {cfg.routing.optimize_wire_via_effort}",
            f"set_route_zrt_detail_options -optimize_tie_off_effort_level {cfg.routing.optimize_tie_off_effort}",
        ])

        # Antenna fixing
        if cfg.routing.antenna_fixing:
            lines.extend([
                f"set_route_zrt_detail_options -antenna {str(cfg.routing.insert_diodes_during_routing).lower()}",
                f"set_route_zrt_detail_options -insert_diodes_during_routing {str(cfg.routing.insert_diodes_during_routing).lower()}",
            ])
            if cfg.libraries.antenna_cell:
                lines.append(f'set_route_zrt_detail_options -diode_libcell_names "{cfg.libraries.antenna_cell}"')
        lines.append("")

        # SI options
        if cfg.routing.si_delta_delay or cfg.routing.si_static_noise:
            lines.extend([
                "# ---- SI Options ----",
                f"set_si_options -delta_delay {str(cfg.routing.si_delta_delay).lower()}",
                f"set_si_options -route_xtalk_prevention {str(cfg.routing.si_route_xtalk_prevention).lower()}",
                f"set_si_options -route_xtalk_prevention_threshold 0.25",
                f"set_si_options -static_noise {str(cfg.routing.si_static_noise).lower()}",
                f"set_si_options -static_noise_threshold_above_low 0.35",
                f"set_si_options -static_noise_threshold_below_high 0.35",
                f"set_si_options -timing_window {str(cfg.routing.si_timing_window).lower()}",
                f"set_si_options -analysis_effort {cfg.routing.si_analysis_effort}",
                f"set_si_options -reselect true",
                f"set_si_options -min_delta_delay true",
                "",
            ])

        # Search repair loops
        lines.extend([
            "# ---- Route Opt Strategy ----",
            f"set_route_opt_strategy -search_repair_loop {cfg.routing.search_repair_loop}",
            f"set_route_opt_strategy -eco_route_search_repair_loops {cfg.routing.eco_route_search_repair_loops}",
            f"set_route_opt_strategy -enable_port_punching true",
            f"set_route_opt_strategy -xtalk_reduction_loops {cfg.routing.xtalk_reduction_loops}",
            "",
            "# Route",
            "route_global",
            "route_track",
            "route_detail",
            "",
            "# Fix DRCs",
            "check_route",
            "route_detail -incremental true -initial_drc_from_input true",
            "check_route",
            "",
            "# Add redundant vias",
            "add_redundant_vias",
            "",
            'save_block -as route',
            "save_lib",
            "",
            "# Reports",
            "check_route > ./rpt/route_check.rpt",
            "report_timing -nosplit -significant_digits 3 -input_pins -nets \\",
            "    -max_paths 200 -slack_lesser_than 0 -groups reg2reg \\",
            "    > ./rpt/route_timing_reg2reg.rpt",
            "report_timing -nosplit -significant_digits 3 -input_pins -nets \\",
            "    -max_paths 200 -slack_lesser_than 0 -groups reg2icg \\",
            "    > ./rpt/route_timing_reg2icg.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_route_opt(self) -> str:
        cfg = self.state.config
        lines = [
            f"# ICC2 Route Optimization Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_common_app_vars())
        lines.extend([
            f"set_host_option -max_cores 64 -num_process 8",
            "",
            f'set active_scenarios "{cfg.scenario}"',
            f"set_scenario_status -active false [get_scenarios -filter active]",
            f"set_scenario_status -active true $active_scenarios",
            f"current_scenario $active_scenarios",
            "",
            f"set_ignored_layers -min_routing_layer {cfg.pdk.min_routing_layer} -max_routing_layer {cfg.pdk.max_routing_layer}",
            "",
            "# Route optimization",
            'set_app_options -name opt.power.mode -value leakage',
            'set_app_options -name opt.power.effort -value high',
            'set_app_options -name opt.timing.effort -value high',
            "",
            "route_opt -initial_route_opt",
            "route_opt",
            "",
            "# Final DRC check",
            "check_route",
            "route_detail -incremental true -initial_drc_from_input true",
            "check_route",
            "",
            "# Post-decap insertion",
        ])

        if cfg.placement.insert_postdecap and cfg.libraries.decap_cells:
            decap_list = " ".join(cfg.libraries.decap_cells)
            lines.append(f"insert_decap_cells -lib_cells [list {decap_list}]")
        lines.append("")

        lines.extend([
            "# Write outputs",
            'save_block -as route_opt',
            "save_lib",
            "",
            "# Write netlist for STA / PV",
            f"write_verilog -include_pwr_grd \\",
            f"    -exclude_cell_output unconnected \\",
            f"    ./out/{cfg.design_name}_routed.v",
            f"write_parasitics -format SPEF -output ./out/{cfg.design_name}.spef",
            "",
            "# Reports",
            "check_route > ./rpt/routeopt_check.rpt",
            "report_timing -nosplit -significant_digits 3 -input_pins -nets \\",
            "    -max_paths 9999 -slack_lesser_than 0 \\",
            "    > ./rpt/routeopt_timing_violations.rpt",
            "report_qor -summary > ./rpt/routeopt_qor.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Report Parsers
    # ----------------------------------------------------------------

    def _parse_timing_report(self, text: str, result: StageResult):
        wns_matches = re.findall(r'slack\s+\(\w+\)\s+([-.\d]+)', text)
        if wns_matches:
            slacks = [float(s) for s in wns_matches]
            worst = min(slacks)
            if result.timing.wns is None or worst < result.timing.wns:
                result.timing.wns = worst
            result.timing.num_violating_paths = sum(1 for s in slacks if s < 0)
            neg_slacks = [s for s in slacks if s < 0]
            if neg_slacks:
                result.timing.tns = sum(neg_slacks)

    def _parse_congestion(self, text: str, result: StageResult):
        m = re.search(r'GRC congestion.*?H\s*:\s*([-.\d]+).*?V\s*:\s*([-.\d]+)', text, re.DOTALL)
        if m:
            result.route.congestion_h = float(m.group(1))
            result.route.congestion_v = float(m.group(2))

    def _parse_utilization(self, text: str, result: StageResult):
        m = re.search(r'STD CELL utilization\s*:\s*([-.\d]+)', text)
        if m:
            result.area.utilization = float(m.group(1))
        m = re.search(r'Total (?:number of|cells)\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.area.num_std_cells = int(m.group(1))

    def _parse_qor_summary(self, text: str, result: StageResult):
        m = re.search(r'timing\s+([-.\d]+)\s+([-.\d]+)', text)
        if m:
            result.timing.wns = float(m.group(1))
            result.timing.tns = float(m.group(2))
