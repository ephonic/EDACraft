"""
Innovus Adapter — Cadence Digital Implementation (place and route).

Industrial features:
- Design import from synthesis (DEF/Verilog + LEF)
- Floorplan with utilization / die area control
- Power plan (rings + stripes)
- Timing-driven placement with congestion awareness
- CTS with target skew, useful skew, CCOPT
- NanoRoute with SI-driven routing, antenna fixing, redundant via
- Post-route optimization with ECO opt
- Report parsing for timing / congestion / utilization

Sub-stages:
  - create_lib
  - floorplan
  - placement
  - cts
  - routing
  - route_opt
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


class InnovusAdapter(ToolAdapter):
    """
    Cadence Innovus adapter for physical implementation.

    Sub-stages:
      - create_lib: Import design and initialize Innovus database
      - floorplan: Die/core area, pin assignment, power plan
      - placement: Timing-driven placement + pre/post place opt
      - cts: Clock tree synthesis + CCOPT optimization
      - routing: NanoRoute global + detail routing
      - route_opt: Post-route optimization + ECO opt
    """

    tool_name = "Innovus"
    stage = FlowStage.PLACEMENT
    env_script = "/share/apps/EDAs/innovus.bash"
    tool_family = "innovus"

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
        return "innovus -no_gui"

    def setup_work_dir(self, stage_name: str | None = None) -> Path:
        name = stage_name or f"innovus_{self.sub_stage}"
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
            raise ValueError(f"Unknown Innovus sub-stage: {self.sub_stage}")
        return gen_func()

    def parse_results(self) -> None:
        result = self.state.get_stage_result(self.stage)
        if self.work_dir is None:
            return

        rpt_dir = self.work_dir / "rpt"
        if rpt_dir.exists():
            for fname in rpt_dir.glob("*.rpt"):
                content = fname.read_text(errors="ignore")
                if "timing" in fname.stem.lower() or "timeDesign" in fname.stem:
                    self._parse_timing_report(content, result)
                elif "congestion" in fname.stem.lower():
                    self._parse_congestion(content, result)
                elif "utilization" in fname.stem.lower() or "place" in fname.stem.lower():
                    self._parse_utilization(content, result)

        log_dir = self.work_dir / "log"
        if log_dir.exists():
            for logfile in log_dir.glob("*.log"):
                content = logfile.read_text(errors="ignore")
                if "ERROR" in content:
                    errors = [
                        line for line in content.split("\n")
                        if line.strip().startswith("ERROR")
                    ]
                    result.messages.extend(errors[:20])

        out_dir = self.work_dir / "out"
        if out_dir.exists():
            for f in out_dir.iterdir():
                self.state.record_artifact(
                    f"innovus_{self.sub_stage}_{f.stem}", str(f)
                )

    # ----------------------------------------------------------------
    # Common Tcl Helpers
    # ----------------------------------------------------------------

    def _gen_multi_cpu(self) -> list[str]:
        """Generate multi-CPU setup."""
        num_cores = self.state.config.synthesis.num_cores
        return [
            f"setMultiCpuUsage -localCpu {num_cores}",
            f"set_db max_cpus_per_server {num_cores}",
            "",
        ]

    def _gen_design_import_libs(self) -> list[str]:
        """Generate library loading commands."""
        cfg = self.state.config
        lines = ["# ---- Library Setup ----"]

        if cfg.pdk.tech_file:
            lines.append(f'set_db init_lib_search_path "{cfg.pdk.tech_file}"')

        if cfg.pdk.lef_files:
            lef_list = " ".join(cfg.pdk.lef_files)
            lines.append(f'set_db lef_library "{lef_list}"')

        for vt_name, libs in cfg.libraries.vt_libs.items():
            for lib in libs:
                lines.append(f'set_db library "{lib}"')

        if cfg.libraries.dont_use_cells:
            dont_use = " ".join(cfg.libraries.dont_use_cells)
            lines.append(f'set_db dont_use_cell_list "{dont_use}"')

        lines.append("")
        return lines

    def _gen_sdc(self) -> list[str]:
        """Generate SDC loading."""
        cfg = self.state.config
        lines = []
        if cfg.sdc_file:
            lines.append(f'set_db timing_analysis_type setup_hold')
            lines.append(f'read_sdc "{cfg.sdc_file}"')
        return lines

    def _gen_timing_derate(self) -> list[str]:
        """Generate timing derate / OCV settings."""
        cfg = self.state.config
        lines = []
        late = cfg.timing_derate.late_factor
        early = cfg.timing_derate.early_factor
        if late != 1.0 or early != 1.0:
            lines.append("# ---- Timing Derate (OCV) ----")
            lines.append(f"set_timing_derate -late {late}")
            lines.append(f"set_timing_derate -early {early}")
            lines.append("")
        return lines

    def _gen_special_cells(self) -> list[str]:
        """Generate endcap, welltap, filler cell commands."""
        cfg = self.state.config
        lines = []

        if cfg.placement.insert_endcap and cfg.libraries.endcap_cell:
            lines.append(f"addEndCap -libCell {cfg.libraries.endcap_cell}")

        if cfg.placement.insert_welltap and cfg.libraries.tap_cell:
            lines.append(
                f"addWellTap -cell {cfg.libraries.tap_cell} "
                f"-maxDistance {cfg.placement.tap_distance_um}"
            )

        if cfg.placement.insert_predecap and cfg.libraries.decap_cells:
            cells = " ".join(cfg.libraries.decap_cells)
            lines.append(f"addDeCap -cellList [list {cells}]")

        return lines

    # ----------------------------------------------------------------
    # Script Generators
    # ----------------------------------------------------------------

    def _gen_create_lib(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Create Library Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_design_import_libs())
        lines.extend([
            "# ---- Design Import ----",
        ])

        synth_v = self.state.get_artifact("synth_v") or f"./../syn/out/{cfg.design_name}_syn.v"
        lines.append(f'set_db design "{cfg.design_name}"')
        lines.append(f'init_design -verilog "{synth_v}" -top {cfg.top_module}')
        lines.extend(self._gen_sdc())
        lines.extend(self._gen_timing_derate())
        lines.extend([
            "",
            "# ---- Process Settings ----",
            f'set_db route_early_global_layer {cfg.pdk.min_routing_layer}',
            f'set_db route_early_detail_layer {cfg.pdk.max_routing_layer}',
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_floorplan(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Floorplan Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend([
            "# ---- Floorplan ----",
        ])

        offset = cfg.core_offset_um
        if isinstance(offset, list) and len(offset) >= 4:
            lines.append(
                f"floorPlan -site core -r 1.0 "
                f"{offset[0]} {offset[1]} {offset[2]} {offset[3]}"
            )
        else:
            lines.append("floorPlan -site core -r 1.0 10.0 10.0 10.0 10.0")

        lines.extend([
            "",
            "# ---- Power Plan ----",
            f'createRing -nets "{cfg.placement.power_net} {cfg.placement.ground_net}" '
            f'-type core_rings -offset 0.8 -width 4.0 -spacing 2.0 '
            f'-layer top metal8 -layer bottom metal8 '
            f'-layer left metal9 -layer right metal9',
            "",
            f'createStripe -nets "{cfg.placement.power_net} {cfg.placement.ground_net}" '
            f'-layer metal8 -width 2.0 -spacing 10.0 -start_offset 100 '
            f'-set_to_set_distance 200 -xleft_offset 100 -merge_stripes_value 0.4 '
            f'-extend_to design_boundary',
            "",
            f'sroute -nets "{cfg.placement.power_net} {cfg.placement.ground_net}" '
            f'-connect corePin -padPin {cfg.placement.power_net} -useStraps false',
            "",
            "# ---- Special Cells ----",
        ])
        lines.extend(self._gen_special_cells())

        lines.extend([
            "",
            "# ---- Pin Assignment ----",
            "setPinAssignMode -pinEditInBatch true",
            "editPin -pinWidth 0.2 -pinDepth 0.6 -fixOverlap 1 -spacing 1.0 "
            "    -layer metal4 -spreadType direction -spreadDirection clockwise "
            "    -side left -start {0 0}",
            "legalizePin",
            "setPinAssignMode -pinEditInBatch false",
            "",
            "# Save design",
            f'saveDesign innovus_fp',
            "",
            "# Reports",
            f"reportNetStat > rpt/fp_netstat.rpt",
            f"report_power > rpt/fp_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_placement(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Placement Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend([
            "# ---- Placement Configuration ----",
            'setPlaceMode -place_detail_legalization_on true',
            f'set_db place_opt_effort high',
        ])

        if cfg.routing.timing_driven:
            lines.append('set_db place_opt_legalize true')

        if cfg.placement.congestion_effort == "high":
            lines.append('set_db place_opt_congestion_effort high')

        lines.extend([
            "",
            "# ---- Pre-Placement Optimization ----",
            "optDesign -prePlace",
            "",
            "# ---- Placement ----",
            "place_opt_design",
            "",
            "# ---- Post-Placement Optimization ----",
            "optDesign -postPlace",
            "",
            "# ---- Filler Cells ----",
        ])

        if cfg.libraries.filler_cells:
            filler_list = " ".join(cfg.libraries.filler_cells)
            lines.append(f"addFiller -cell [list {filler_list}] -prefix FILL")

        lines.extend([
            "",
            "# Save design",
            f'saveDesign innovus_placed',
            "",
            "# ---- Timing Reports ----",
            'timeDesign -preCTSTiming -outDir rpt',
            f"report_timing -max_paths 100 -nworst 10 -slack_lesser_than 0 > rpt/place_timing.rpt",
            f"report_qor > rpt/place_qor.rpt",
            f"reportNetStat > rpt/place_netstat.rpt",
            f"report_power > rpt/place_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_cts(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus CTS Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend([
            "# ---- CTS Configuration ----",
            f'set_db cts_target_skew {cfg.cts.target_skew_ns}',
        ])

        if cfg.cts.target_early_delay_ns > 0:
            lines.append('set_db cts_useful_skew true')
            lines.append(f'set_db cts_insertion_delay {cfg.cts.target_early_delay_ns}')

        if cfg.cts.inter_clock_balance:
            lines.append('set_db cts_inter_clock_balance true')

        lines.extend([
            "",
            "# ---- Clock Tree Synthesis ----",
            'setCTSMode -engineMode true',
            f'createClockTreeSpec -outputFile out/{cfg.design_name}.cts',
            f'clockOptDesign -from buildClock -to routeClock',
            "",
            "# ---- Post-CTS Optimization ----",
            'optDesign -postCTS -hold',
            'clockOptDesign -from routeClock',
            "",
            "# Save design",
            f'saveDesign innovus_cts',
            "",
            "# ---- Timing Reports ----",
            'timeDesign -postCTS -outDir rpt',
            'timeDesign -postCTS -hold -outDir rpt',
            f"report_timing -max_paths 100 -nworst 10 -slack_lesser_than 0 > rpt/cts_timing.rpt",
            f"report_qor > rpt/cts_qor.rpt",
            f"report_clock_timing -type skew > rpt/cts_skew.rpt",
            f"report_power > rpt/cts_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_routing(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus NanoRoute Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend([
            "# ---- Routing Configuration ----",
            f'set_db route_flow_effort {cfg.routing.timing_driven_effort}',
        ])

        if cfg.routing.si_delta_delay:
            lines.append('set_db route_enable_si_driven true')
            lines.append('set_db route_si_effort high')

        if cfg.routing.antenna_fixing:
            lines.append('set_db route_antenna_fix true')

        if cfg.routing.redundant_via_insertion:
            lines.append('set_db route_with_via_opt true')
            lines.append('set_db route_with_via_in_pin true')

        lines.extend([
            "",
            "# ---- NanoRoute ----",
            'setNanoRouteMode -drouteUseMultiCutViaEffort low',
            'setNanoRouteMode -drouteFixAntenna true',
            'setNanoRouteMode -drouteStartIteration 1',
            'setNanoRouteMode -routeTopRoutingLayer default',
            'setNanoRouteMode -routeBottomRoutingLayer default',
            "",
            'routeDesign',
            "",
            "# ---- Search and Repair ----",
        ])

        if cfg.routing.search_repair_loop > 0:
            lines.append('set_db route_design_with_timing_driven true')
            lines.append(
                f'optDesign -postRoute -hold -setup -drv '
                f'-num_iters {cfg.routing.search_repair_loop}'
            )

        lines.extend([
            "",
            "# Save design",
            f'saveDesign innovus_routed',
            "",
            "# ---- Reports ----",
            'timeDesign -postRoute -outDir rpt',
            'timeDesign -postRoute -hold -outDir rpt',
            f"verifyConnectivity > rpt/route_connectivity.rpt",
            f"report_timing -max_paths 200 -nworst 10 -slack_lesser_than 0 > rpt/route_timing.rpt",
            f"report_qor > rpt/route_qor.rpt",
            f"reportNetStat > rpt/route_netstat.rpt",
            f"report_power > rpt/route_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_route_opt(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Post-Route Optimization Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend([
            "# ---- Post-Route Optimization ----",
            'set_db route_flow_effort high',
            'set_db opt_setup_effort high',
            'set_db opt_hold_effort high',
            "",
            "optDesign -postRoute -setup -hold",
            "",
        ])

        lines.append("# ---- Post-Route Decap ----")
        if cfg.placement.insert_postdecap and cfg.libraries.decap_cells:
            cells = " ".join(cfg.libraries.decap_cells)
            lines.append(f"addDeCap -cellList [list {cells}]")
        lines.append("")

        lines.extend([
            "# ---- Write Outputs ----",
            f'saveDesign innovus_route_opt',
            f"defOut -floorplan -netlist -routing > out/{cfg.design_name}_routed.def",
            f"saveNetlist out/{cfg.design_name}_routed.v",
            f"extractRC > out/{cfg.design_name}.spef",
            "",
            "# ---- Reports ----",
            'timeDesign -postRoute -outDir rpt',
            'timeDesign -postRoute -hold -outDir rpt',
            f"verifyConnectivity > rpt/routeopt_connectivity.rpt",
            f"report_timing -max_paths 9999 -nworst 10 -slack_lesser_than 0 "
            f"> rpt/routeopt_timing_violations.rpt",
            f"report_qor > rpt/routeopt_qor.rpt",
            f"reportNetStat > rpt/routeopt_netstat.rpt",
            f"report_power > rpt/routeopt_power.rpt",
            f"report_clock_timing -type skew > rpt/routeopt_clock_skew.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Report Parsers
    # ----------------------------------------------------------------

    def _parse_timing_report(self, text: str, result: StageResult):
        """Parse Innovus timeDesign / report_timing output."""
        wns_matches = re.findall(r'(?:slack|wns)\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if wns_matches:
            slacks = [float(s) for s in wns_matches]
            worst = min(slacks)
            if result.timing.wns is None or worst < result.timing.wns:
                result.timing.wns = worst
            neg_slacks = [s for s in slacks if s < 0]
            result.timing.num_violating_paths = len(neg_slacks)
            if neg_slacks:
                result.timing.tns = sum(neg_slacks)

        tns_match = re.search(r'(?:tns|total negative slack)\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if tns_match:
            result.timing.tns = float(tns_match.group(1))

        endpoints_match = re.search(r'total\s+endpoints?\s*[=:]\s*(\d+)', text, re.IGNORECASE)
        if endpoints_match:
            result.timing.num_endpoints = int(endpoints_match.group(1))

    def _parse_congestion(self, text: str, result: StageResult):
        """Parse Innovus congestion report."""
        h_match = re.search(r'(?:horizontal|H)\s*congestion\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        v_match = re.search(r'(?:vertical|V)\s*congestion\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if h_match:
            result.route.congestion_h = float(h_match.group(1))
        if v_match:
            result.route.congestion_v = float(v_match.group(1))

    def _parse_utilization(self, text: str, result: StageResult):
        """Parse Innovus utilization / placement report."""
        util_match = re.search(
            r'(?:utilization|std\s*cell\s*utilization)\s*[=:]\s*([-.\d]+)',
            text, re.IGNORECASE
        )
        if util_match:
            result.area.utilization = float(util_match.group(1))

        cells_match = re.search(r'(?:total\s+cells?|instance\s+count)\s*[=:]\s*(\d+)', text, re.IGNORECASE)
        if cells_match:
            result.area.num_std_cells = int(cells_match.group(1))
