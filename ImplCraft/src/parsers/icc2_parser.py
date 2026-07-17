"""
ICC2 Report Parser — extracts detailed metrics from ICC2 reports.

Supports: timing, congestion, utilization, QoR, route check reports.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ICC2StageResult:
    """Detailed results from an ICC2 sub-stage."""
    stage_name: str = ""

    # Timing
    wns: float | None = None
    tns: float | None = None
    num_violating_paths: int = 0
    num_endpoints: int = 0
    clock_skew: float | None = None

    # Placement
    utilization: float | None = None
    num_std_cells: int = 0
    num_macros: int = 0

    # Congestion
    congestion_h: float | None = None
    congestion_v: float | None = None
    congestion_overflow: int = 0

    # Routing
    drc_errors: int | None = None
    total_wirelength: float | None = None
    num_nets_routed: int = 0
    num_vias: int = 0

    # Power
    total_power: float | None = None
    leakage_power: float | None = None
    dynamic_power: float | None = None

    # Path group breakdown
    path_group_timing: dict[str, dict[str, float]] = field(default_factory=dict)


class ICC2ReportParser:
    """Parse ICC2 report files from physical implementation stages."""

    def __init__(self, report_dir: str | Path, stage_name: str = ""):
        self.report_dir = Path(report_dir)
        self.stage_name = stage_name

    def parse_all(self) -> ICC2StageResult:
        result = ICC2StageResult(stage_name=self.stage_name)

        for rpt_file in self.report_dir.glob("*.rpt"):
            content = rpt_file.read_text(errors="ignore")
            name = rpt_file.stem.lower()

            if "timing" in name:
                self.parse_timing(content, result)
            if "congestion" in name:
                self.parse_congestion(content, result)
            if "utilization" in name:
                self.parse_utilization(content, result)
            if "qor" in name:
                self.parse_qor_summary(content, result)
            if "route_check" in name or "check_route" in name:
                self.parse_route_check(content, result)
            if "report_design" in name:
                self.parse_design(content, result)

        return result

    def parse_timing(self, text: str, result: ICC2StageResult):
        """Parse ICC2 timing report."""
        slacks = []
        for m in re.finditer(r'slack\s+\((\w+)\)\s+([-.\d]+)', text):
            slacks.append(float(m.group(2)))

        if slacks:
            result.wns = min(slacks)
            neg = [s for s in slacks if s < 0]
            result.num_violating_paths = len(neg)
            result.tns = sum(neg) if neg else 0.0

        # Extract path group info
        for m in re.finditer(r'(?:Path Group|group):\s*(\S+).*?slack\s+\(\w+\)\s+([-.\d]+)', text, re.DOTALL):
            group_name = m.group(1)
            slack = float(m.group(2))
            if group_name not in result.path_group_timing:
                result.path_group_timing[group_name] = {}
            result.path_group_timing[group_name]["wns"] = slack

    def parse_congestion(self, text: str, result: ICC2StageResult):
        """Parse ICC2 congestion report."""
        m = re.search(r'(?:GRC\s+)?congestion.*?H\s*(?:=|:)\s*([-.\d]+).*?V\s*(?:=|:)\s*([-.\d]+)', text, re.DOTALL | re.IGNORECASE)
        if m:
            result.congestion_h = float(m.group(1))
            result.congestion_v = float(m.group(2))

        m = re.search(r'overflow\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.congestion_overflow = int(m.group(1))

    def parse_utilization(self, text: str, result: ICC2StageResult):
        """Parse ICC2 utilization report."""
        m = re.search(r'STD CELL utilization\s*[:=]\s*([-.\d]+)', text, re.IGNORECASE)
        if m:
            result.utilization = float(m.group(1))

        m = re.search(r'Total (?:number of|cells)\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.num_std_cells = int(m.group(1))

        # Macro count
        m = re.search(r'(?:Hard macro|Macro) (?:count|cells?)\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.num_macros = int(m.group(1))

    def parse_qor_summary(self, text: str, result: ICC2StageResult):
        """Parse ICC2 report_qor -summary."""
        m = re.search(r'timing\s+([-.\d]+)\s+([-.\d]+)', text)
        if m:
            result.wns = float(m.group(1))
            result.tns = float(m.group(2))

        m = re.search(r'leakage\s+power\s*[:=]\s*([-.\d]+)', text, re.IGNORECASE)
        if m:
            result.leakage_power = float(m.group(1))

        m = re.search(r'dynamic\s+power\s*[:=]\s*([-.\d]+)', text, re.IGNORECASE)
        if m:
            result.dynamic_power = float(m.group(1))

    def parse_route_check(self, text: str, result: ICC2StageResult):
        """Parse check_route output."""
        m = re.search(r'(?:Total )?(?:DRC )?(?:error|violation)s?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.drc_errors = int(m.group(1))

        m = re.search(r'(?:nets? (?:routed|completed))\s*[:=]\s*(\d+)', text, re.IGNORECASE)
        if m:
            result.num_nets_routed = int(m.group(1))

    def parse_design(self, text: str, result: ICC2StageResult):
        """Parse report_design output for power info."""
        m = re.search(r'Total\s+(?:power|leakage)\s*[:=]\s*([-.\d]+)', text, re.IGNORECASE)
        if m:
            result.total_power = float(m.group(1))
