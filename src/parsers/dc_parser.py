"""
Design Compiler Report Parser — extracts detailed metrics from DC reports.

Supports: QoR, timing, area, power, constraint, cell, VT group reports.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DCQoRResult:
    """Detailed QoR results from DC synthesis."""
    # Timing
    wns_setup: float | None = None
    wns_hold: float | None = None
    tns_setup: float | None = None
    tns_hold: float | None = None
    num_setup_violations: int = 0
    num_hold_violations: int = 0
    num_endpoints: int = 0

    # Area
    cell_area: float | None = None
    comb_area: float | None = None
    seq_area: float | None = None
    buf_area: float | None = None
    num_comb_cells: int = 0
    num_seq_cells: int = 0
    num_buf_cells: int = 0

    # Power
    total_power: float | None = None
    dynamic_power: float | None = None
    leakage_power: float | None = None

    # Design stats
    num_nets: int = 0
    num_ports: int = 0
    num_clocks: int = 0

    # VT distribution
    vt_distribution: dict[str, float] = field(default_factory=dict)

    # Constraint violations
    max_transition_violations: int = 0
    max_cap_violations: int = 0
    max_fanout_violations: int = 0


class DCReportParser:
    """Parse Design Compiler report files."""

    def __init__(self, report_dir: str | Path):
        self.report_dir = Path(report_dir)

    def parse_all(self) -> DCQoRResult:
        """Parse all available DC reports."""
        result = DCQoRResult()

        qor_file = self.report_dir / "qor.rpt"
        if qor_file.exists():
            self.parse_qor(qor_file.read_text(), result)

        timing_setup = self.report_dir / "timing_setup.rpt"
        if timing_setup.exists():
            self.parse_timing(timing_setup.read_text(), result, is_setup=True)

        timing_hold = self.report_dir / "timing_hold.rpt"
        if timing_hold.exists():
            self.parse_timing(timing_hold.read_text(), result, is_setup=False)

        area_file = self.report_dir / "area.rpt"
        if area_file.exists():
            self.parse_area(area_file.read_text(), result)

        power_file = self.report_dir / "power.rpt"
        if power_file.exists():
            self.parse_power(power_file.read_text(), result)

        constraint_file = self.report_dir / "constraint.rpt"
        if constraint_file.exists():
            self.parse_constraints(constraint_file.read_text(), result)

        vt_file = self.report_dir / "vt_group.rpt"
        if vt_file.exists():
            self.parse_vt_group(vt_file.read_text(), result)

        return result

    def parse_qor(self, text: str, result: DCQoRResult):
        """Parse report_qor output."""
        # Timing section
        m = re.search(r'timing\s+([-.\d]+)\s+([-.\d]+)', text)
        if m:
            result.wns_setup = float(m.group(1))
            result.tns_setup = float(m.group(2))

        # Area
        m = re.search(r'area\s+([-.\d]+)', text)
        if m:
            result.cell_area = float(m.group(1))

        # Count endpoints
        m = re.search(r'Number of endpoints\s*[:=]\s*(\d+)', text)
        if m:
            result.num_endpoints = int(m.group(1))

        # Violating paths
        m = re.search(r'Number of violating paths\s*[:=]\s*(\d+)', text)
        if m:
            result.num_setup_violations = int(m.group(1))

    def parse_timing(self, text: str, result: DCQoRResult, is_setup: bool = True):
        """Parse report_timing output."""
        slacks = []
        for m in re.finditer(r'slack\s+\((\w+)\)\s+([-.\d]+)', text):
            slacks.append(float(m.group(2)))

        if not slacks:
            return

        worst = min(slacks)
        violations = sum(1 for s in slacks if s < 0)
        tns = sum(s for s in slacks if s < 0)

        if is_setup:
            result.wns_setup = worst
            result.num_setup_violations = violations
            result.tns_setup = tns
        else:
            result.wns_hold = worst
            result.num_hold_violations = violations
            result.tns_hold = tns

    def parse_area(self, text: str, result: DCQoRResult):
        """Parse report_area output."""
        m = re.search(r'Total cell area:\s+([-.\d]+)', text)
        if m:
            result.cell_area = float(m.group(1))

        # Count by type
        for line in text.splitlines():
            if "Combinational cell count:" in line:
                nums = re.findall(r'(\d+)', line)
                if nums:
                    result.num_comb_cells = int(nums[0])
            elif "Noncombinational cell count:" in line or "Sequential cell count:" in line:
                nums = re.findall(r'(\d+)', line)
                if nums:
                    result.num_seq_cells = int(nums[0])
            elif "Buf/Inv cell count:" in line:
                nums = re.findall(r'(\d+)', line)
                if nums:
                    result.num_buf_cells = int(nums[0])

    def parse_power(self, text: str, result: DCQoRResult):
        """Parse report_power output."""
        # Look for the Total line
        for line in text.splitlines():
            if re.match(r'\s*Total\s+', line):
                nums = re.findall(r'([-.\d]+(?:[eE][-+]?\d+)?)', line)
                if len(nums) >= 4:
                    result.leakage_power = float(nums[0])
                    result.dynamic_power = float(nums[1])
                    result.total_power = float(nums[3])
                break

    def parse_constraints(self, text: str, result: DCQoRResult):
        """Parse report_constraint output."""
        result.max_transition_violations = len(
            re.findall(r'max_transition', text, re.IGNORECASE)
        )
        result.max_cap_violations = len(
            re.findall(r'max_capacitance', text, re.IGNORECASE)
        )
        result.max_fanout_violations = len(
            re.findall(r'max_fanout', text, re.IGNORECASE)
        )

    def parse_vt_group(self, text: str, result: DCQoRResult):
        """Parse report_threshold_voltage_group output."""
        for m in re.finditer(r'(\w+)\s+([\d.]+)%', text):
            vt_name = m.group(1)
            percentage = float(m.group(2))
            result.vt_distribution[vt_name] = percentage
