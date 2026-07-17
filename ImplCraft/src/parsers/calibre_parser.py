"""
Calibre Report Parser — extracts DRC/LVS results from Calibre reports.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DRCResult:
    """Detailed DRC results."""
    is_clean: bool = False
    total_errors: int = 0
    errors_by_rule: dict[str, int] = field(default_factory=dict)
    errors_by_layer: dict[str, int] = field(default_factory=dict)
    fixable_errors: int = 0
    non_fixable_errors: int = 0


@dataclass
class LVSResult:
    """Detailed LVS results."""
    is_clean: bool = False
    num_device_mismatches: int = 0
    num_net_mismatches: int = 0
    num_property_errors: int = 0
    num_erc_errors: int = 0
    layout_device_count: int = 0
    source_device_count: int = 0
    layout_net_count: int = 0
    source_net_count: int = 0


class CalibreReportParser:
    """Parse Calibre DRC/LVS report files."""

    def __init__(self, report_dir: str | Path):
        self.report_dir = Path(report_dir)

    def parse_drc(self) -> DRCResult:
        """Parse DRC summary report."""
        result = DRCResult()

        # Try summary report first
        summary_file = self.report_dir / "drc_summary.rpt"
        if not summary_file.exists():
            summary_file = self.report_dir / "drc.results"

        if summary_file.exists():
            text = summary_file.read_text(errors="ignore")

            # Total errors
            m = re.search(r'Total DRC Errors\.?\s*:\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.total_errors = int(m.group(1))

            # Parse rule-by-rule errors
            for m in re.finditer(r'(?:Rule|Check)\s+(\S+)\s*:\s*(\d+)', text, re.IGNORECASE):
                rule = m.group(1)
                count = int(m.group(2))
                result.errors_by_rule[rule] = count

            # Also try pattern: "M1.xxx : count"
            for m in re.finditer(r'(\w+\.\w+)\s+:\s+(\d+)', text):
                rule = m.group(1)
                count = int(m.group(2))
                result.errors_by_rule[rule] = count
                # Infer layer
                layer = rule.split(".")[0]
                result.errors_by_layer[layer] = result.errors_by_layer.get(layer, 0) + count

            result.is_clean = result.total_errors == 0

        return result

    def parse_lvs(self) -> LVSResult:
        """Parse LVS report."""
        result = LVSResult()

        report_file = self.report_dir / "lvs_report.rpt"
        if not report_file.exists():
            report_file = self.report_dir / "lvs.report"

        if report_file.exists():
            text = report_file.read_text(errors="ignore")

            # Clean check
            if re.search(r'\bCORRECT\b', text):
                result.is_clean = True
            elif re.search(r'\bINCORRECT\b', text):
                result.is_clean = False

            # Device counts
            m = re.search(r'Layout\s+device\s+count\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.layout_device_count = int(m.group(1))
            m = re.search(r'Source\s+device\s+count\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.source_device_count = int(m.group(1))

            # Net counts
            m = re.search(r'Layout\s+net\s+count\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.layout_net_count = int(m.group(1))
            m = re.search(r'Source\s+net\s+count\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.source_net_count = int(m.group(1))

            # Mismatches
            m = re.search(r'(?:Device|Net)\s+mismatch(?:es)?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.num_device_mismatches = int(m.group(1))

            # ERC errors
            m = re.search(r'(?:Total\s+)?ERC\s+(?:error|violations?)s?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.num_erc_errors = int(m.group(1))

            # Property errors
            m = re.search(r'Property\s+(?:error|mismatch)(?:es|s)?\s*[:=]\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.num_property_errors = int(m.group(1))

        return result
