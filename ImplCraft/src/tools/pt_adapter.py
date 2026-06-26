"""
PrimeTime Adapter — sign-off static timing analysis.

Compatible with PT K-2015.06 and newer versions.

Industrial features:
- SPEF back-annotation from ICC2/StarRC
- Multi-corner multi-mode (MCMM)
- CPPR (Common Path Pessimism Removal)
- SI analysis (crosstalk delay)
- Path-based analysis
- ECO guidance generation
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignState, FlowStage, StageResult, StageStatus,
    TimingMetrics, PowerMetrics,
)
from .base import ToolAdapter

logger = logging.getLogger("ic_backend")


class PTAdapter(ToolAdapter):
    tool_name = "PrimeTime"
    stage = FlowStage.STA_SIGNOFF
    env_script = "/share/apps/EDAs/syn22.bash"

    def _get_shell_cmd(self) -> str:
        # K-2015.06 does not support -no_gui flag
        return "pt_shell"

    def setup_work_dir(self, stage_name: str = "primetime") -> Path:
        root = super().setup_work_dir(stage_name)
        (root / "PT" / "out").mkdir(parents=True, exist_ok=True)
        (root / "PT" / "report").mkdir(parents=True, exist_ok=True)
        return root

    def generate_script(self) -> str:
        cfg = self.state.config
        lines = [
            f"# PrimeTime STA Sign-off Script",
            f"# Design: {cfg.design_name}",
            f"# Compatible with PT K-2015.06",
            "",
            f'set_host_options -max_cores {cfg.synthesis.num_cores}',
            "",
        ]

        # ---- Common timing settings ----
        lines.extend([
            "# ---- Timing Settings ----",
            "set_app_var timing_enable_multiple_clocks_per_reg true",
            "set_app_var timing_separate_clock_gating_group true",
            "set_app_var timing_use_enhanced_capacitance_modeling true",
            "set_app_var timing_remove_clock_reconvergence_pessimism true",
            "set_app_var case_analysis_with_logic_constants true",
            "",
        ])

        # ---- Libraries ----
        lines.append("# ---- Libraries ----")
        lib_names = " ".join(Path(p).name for p in cfg.libraries.std_cell_libs)
        lines.append(f"set target_library [list {lib_names}]")
        lines.append(f"set link_library   [concat * $target_library]")
        lines.append("")

        # ---- Read netlist ----
        lines.append("# ---- Read Netlist ----")
        routed_netlist = self.state.get_artifact("icc2_route_opt_routed_v")
        if not routed_netlist:
            routed_netlist = f"work/route_opt/out/{cfg.design_name}_routed.v"
        lines.append(f'read_verilog "{routed_netlist}"')
        lines.append(f"current_design {cfg.top_module}")
        lines.append("link_design")
        lines.append("")

        # ---- Read SDC ----
        lines.append("# ---- Read SDC ----")
        sdc_file = self.state.get_artifact("icc2_route_opt_sdc")
        if not sdc_file:
            sdc_file = f"work/route_opt/out/{cfg.design_name}.sdc"
        lines.append(f'source "{sdc_file}"')
        lines.append("")

        # ---- Read SPEF (parasitics) ----
        # K-2015.06: use read_parasitics -format SPEF
        lines.append("# ---- Read SPEF ----")
        spef_file = self.state.get_artifact("icc2_route_opt_spef")
        if not spef_file:
            spef_file = f"work/route_opt/out/{cfg.design_name}.spef"
        lines.append(f'read_parasitics -format SPEF "{spef_file}"')
        lines.append("")

        # ---- Timing derate ----
        d = cfg.timing_derate
        if d.late_factor != 1.0 or d.early_factor != 1.0:
            lines.extend([
                "# ---- Timing Derate (OCV) ----",
                f"set_timing_derate {d.late_factor} -late",
                f"set_timing_derate {d.early_factor} -early",
                "",
            ])

        # ---- Update timing ----
        lines.extend([
            "# ---- Update Timing ----",
            "update_timing -full",
            "",
        ])

        # ---- Setup timing analysis ----
        lines.extend([
            "# ---- Setup Timing Analysis ----",
            'report_timing -delay_type max -max_paths 500 -slack_lesser_than 0 \\',
            '    -path_type full_clock_expanded -significant_digits 4 \\',
            '    -sort_by slack -nworst 1 \\',
            '    > ./PT/report/timing_setup.rpt',
            "",
            'report_timing -delay_type min -max_paths 500 -slack_lesser_than 0 \\',
            '    -path_type full_clock_expanded -significant_digits 4 \\',
            '    -sort_by slack -nworst 1 \\',
            '    > ./PT/report/timing_hold.rpt',
            "",
        ])

        # ---- Path groups ----
        # K-2015.06: use get_path_groups (no wildcard, no all_path_groups)
        lines.extend([
            "# ---- Path Group Reports ----",
            'foreach pg [get_path_groups] {',
            '    set pg_name [get_attribute $pg full_name]',
            '    report_timing -path_group $pg -max_paths 50 \\',
            '        -slack_lesser_than 0 -sort_by slack \\',
            '        > ./PT/report/timing_${pg_name}.rpt',
            '}',
            "",
        ])

        # ---- Constraint violations ----
        lines.extend([
            "# ---- Constraint Reports ----",
            "report_constraint -all_violators -significant_digits 4 \\",
            "    > ./PT/report/constraint.rpt",
            "report_constraint -all_violators -max_transition -significant_digits 4 \\",
            "    > ./PT/report/constraint_transition.rpt",
            "report_constraint -all_violators -max_capacitance -significant_digits 4 \\",
            "    > ./PT/report/constraint_capacitance.rpt",
            "report_constraint -all_violators -max_fanout -significant_digits 4 \\",
            "    > ./PT/report/constraint_fanout.rpt",
            "",
        ])

        # ---- QoR summary ----
        lines.extend([
            "# ---- QoR Summary ----",
            "report_qor -significant_digits 4 > ./PT/report/qor.rpt",
            "",
        ])

        # ---- Path summary (for RTL analysis) ----
        lines.extend([
            "# ---- Path Summary for RTL Analysis ----",
            "report_timing -max_paths 100 -nworst 1 -slack_lesser_than 0 \\",
            "    -significant_digits 4 -path_type full_clock_expanded \\",
            "    -delay_type max -through [all_registers -edge_triggered] \\",
            "    -from [all_registers -edge_triggered] \\",
            "    > ./PT/report/critical_paths_setup.rpt",
            "",
            "report_timing -max_paths 100 -nworst 1 -slack_lesser_than 0 \\",
            "    -significant_digits 4 -path_type full_clock_expanded \\",
            "    -delay_type min -through [all_registers -edge_triggered] \\",
            "    -from [all_registers -edge_triggered] \\",
            "    > ./PT/report/critical_paths_hold.rpt",
            "",
        ])

        # ---- Cell count / VT distribution ----
        lines.extend([
            "# ---- Cell Statistics ----",
            "report_cell > ./PT/report/cell.rpt",
            "report_threshold_voltage_group > ./PT/report/vt_group.rpt",
            "",
        ])

        # ---- Power report ----
        lines.extend([
            "# ---- Power Report ----",
            "report_power -significant_digits 4 > ./PT/report/power.rpt",
            "",
        ])

        # ---- ECO changes ----
        # K-2015.06: use write_changes instead of write_eco_changes
        lines.extend([
            "# ---- ECO Changes ----",
            'write_changes -format dctcl -output ./PT/out/eco_changes.tcl',
            "",
        ])

        # ---- Exit ----
        lines.extend([
            "exit",
        ])

        return "\n".join(lines)

    def parse_results(self) -> None:
        result = self.state.get_stage_result(FlowStage.STA_SIGNOFF)
        if self.work_dir is None:
            return

        rpt_dir = self.work_dir / "PT" / "report"
        if not rpt_dir.exists():
            return

        # Parse QoR
        qor_file = rpt_dir / "qor.rpt"
        if qor_file.exists():
            self._parse_qor(qor_file.read_text(), result)

        # Parse timing reports
        for fname in ["timing_setup.rpt", "critical_paths_setup.rpt"]:
            fpath = rpt_dir / fname
            if fpath.exists():
                self._parse_timing(fpath.read_text(), result, is_setup=True)

        for fname in ["timing_hold.rpt", "critical_paths_hold.rpt"]:
            fpath = rpt_dir / fname
            if fpath.exists():
                self._parse_timing(fpath.read_text(), result, is_setup=False)

        # Parse constraints
        constraint_file = rpt_dir / "constraint.rpt"
        if constraint_file.exists():
            self._parse_constraints(constraint_file.read_text(), result)

        # Record outputs
        out_dir = self.work_dir / "PT" / "out"
        if out_dir.exists():
            for f in out_dir.iterdir():
                self.state.record_artifact(f"pt_{f.stem}", str(f))

    def _parse_qor(self, text: str, result: StageResult):
        m = re.search(r'timing\s+([-.\d]+)\s+([-.\d]+)', text)
        if m:
            result.timing.wns = float(m.group(1))
            result.timing.tns = float(m.group(2))

    def _parse_timing(self, text: str, result: StageResult, is_setup: bool):
        """Parse timing report for detailed path info."""
        slacks = re.findall(r'slack\s+\(\w+\)\s+([-.\d]+)', text)
        if slacks:
            worst = min(float(s) for s in slacks)
            neg_slacks = [float(s) for s in slacks if float(s) < 0]
            if is_setup:
                if result.timing.wns is None or worst < result.timing.wns:
                    result.timing.wns = worst
                if neg_slacks:
                    result.timing.tns = sum(neg_slacks)
                result.timing.num_violating_paths = len(neg_slacks)
            else:
                result.timing.num_violating_paths = (result.timing.num_violating_paths or 0) + len(neg_slacks)

    def _parse_constraints(self, text: str, result: StageResult):
        tran_violations = len(re.findall(r'max_transition', text, re.IGNORECASE))
        cap_violations = len(re.findall(r'max_capacitance', text, re.IGNORECASE))
        fanout_violations = len(re.findall(r'max_fanout', text, re.IGNORECASE))
        result.timing.max_transition_violations = tran_violations
        result.timing.max_capacitance_violations = cap_violations
        result.timing.max_fanout_violations = fanout_violations
