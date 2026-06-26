"""
Tempus Adapter — Cadence Tempus Timing Signoff (STA).

Industrial features:
- Multi-corner multi-mode (MCMM) analysis
- SI analysis (crosstalk delay, crosstalk glitch)
- CPPR (Common Path Pessimism Removal)
- Clock tree analysis (skew, waveform, latency)
- Signoff-quality timing reporting
- Power analysis integration
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


class TempusAdapter(ToolAdapter):
    """
    Cadence Tempus adapter for static timing signoff.
    """

    tool_name = "Tempus"
    stage = FlowStage.STA_SIGNOFF
    env_script = "/share/apps/EDAs/tempus.bash"
    tool_family = "tempus"

    def _get_shell_cmd(self) -> str:
        return "tempus -no_gui"

    def setup_work_dir(self, stage_name: str | None = None) -> Path:
        return super().setup_work_dir(stage_name or "tempus_sta")

    def generate_script(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Tempus STA Signoff Script",
            f"# Design: {cfg.design_name}",
            "",
            f"set_multi_cpu_usage -localCpu {cfg.synthesis.num_cores}",
            "",
        ]

        lines.extend(self._gen_design_import())
        lines.extend(self._gen_analysis_settings())
        lines.extend(self._gen_reporting())

        lines.extend(["", "exit"])
        return "\n".join(lines)

    def _gen_design_import(self) -> list[str]:
        cfg = self.state.config
        lines = ["# ---- Design Import ----"]

        routed_v = self.state.get_artifact("innovus_route_opt_routed_v") or \
                   self.state.get_artifact("routed_v") or \
                   f"./../innovus_route_opt/out/{cfg.design_name}_routed.v"
        spef = self.state.get_artifact("innovus_route_opt_spef") or \
               self.state.get_artifact("routed_spef") or \
               f"./../innovus_route_opt/out/{cfg.design_name}.spef"

        lines.extend([
            f'set_db design "{cfg.design_name}"',
            f'init_design -verilog "{routed_v}" -top {cfg.top_module}',
        ])

        if cfg.pdk.tech_file:
            lines.append(f'set_db init_lib_search_path "{cfg.pdk.tech_file}"')
        if cfg.pdk.lef_files:
            lef_list = " ".join(cfg.pdk.lef_files)
            lines.append(f'set_db lef_library "{lef_list}"')
        for vt_name, libs in cfg.libraries.vt_libs.items():
            for lib in libs:
                lines.append(f'set_db library "{lib}"')

        lines.append(f'read_parasitics -spef "{spef}"')

        if cfg.sdc_file:
            lines.append(f'read_sdc "{cfg.sdc_file}"')

        lines.append("")
        return lines

    def _gen_analysis_settings(self) -> list[str]:
        cfg = self.state.config
        lines = [
            "# ---- Analysis Settings ----",
            'set_db timing_analysis_type setup_hold',
        ]

        late = cfg.timing_derate.late_factor
        early = cfg.timing_derate.early_factor
        if late != 1.0 or early != 1.0:
            lines.append(f"set_timing_derate -late {late}")
            lines.append(f"set_timing_derate -early {early}")

        lines.extend([
            'set_db timing_analysis_cppr_mode true',
            'set_db timing_analysis_cppr_credit_threshold 0.01',
            "",
            "# ---- SI Analysis ----",
            'set_db si_enable_analysis true',
            'set_db si_analysis_type full',
            "",
        ])
        return lines

    def _gen_reporting(self) -> list[str]:
        cfg = self.state.config
        lines = [
            "# ---- Timing Analysis ----",
            'timeDesign -signoff -outDir rpt',
            'timeDesign -signoff -hold -outDir rpt',
            "",
            "# ---- Path Reports ----",
            f'report_timing -max_paths 100 -nworst 10 -slack_lesser_than 0 '
            f'-significant_digits 4 -path_type full_clock '
            f'> rpt/signoff_timing.rpt',
            "",
            f'report_timing -max_paths 50 -nworst 5 -slack_lesser_than 0 '
            f'-path_type full_clock_expanded '
            f'> rpt/signoff_timing_expanded.rpt',
            "",
            "# ---- QoR Summary ----",
            f'report_qor -summary > rpt/signoff_qor.rpt',
            "",
            "# ---- Clock Reports ----",
            f'report_clock_timing -type skew > rpt/signoff_clock_skew.rpt',
            f'report_clock_timing -type latency > rpt/signoff_clock_latency.rpt',
            "",
            "# ---- Power Report ----",
            f'report_power > rpt/signoff_power.rpt',
            "",
        ]
        return lines

    def parse_results(self) -> None:
        result = self.state.get_stage_result(self.stage)
        if self.work_dir is None:
            return

        rpt_dir = self.work_dir / "rpt"
        if rpt_dir.exists():
            for fname in rpt_dir.glob("*.rpt"):
                content = fname.read_text(errors="ignore")
                if "timing" in fname.stem.lower() or "qor" in fname.stem.lower():
                    self._parse_timing_report(content, result)
                elif "power" in fname.stem.lower():
                    self._parse_power_report(content, result)

    def _parse_timing_report(self, text: str, result: StageResult):
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

    def _parse_power_report(self, text: str, result: StageResult):
        total_match = re.search(r'total\s+(?:power|cell_power)\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if total_match:
            result.power.total_power_mw = float(total_match.group(1))

        dynamic_match = re.search(r'dynamic\s+power\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if dynamic_match:
            result.power.dynamic_power_mw = float(dynamic_match.group(1))

        leakage_match = re.search(r'leakage\s+power\s*[=:]\s*([-.\d]+)', text, re.IGNORECASE)
        if leakage_match:
            result.power.leakage_power_mw = float(leakage_match.group(1))
