"""Lightweight synthesis/implementation report parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


@dataclass(frozen=True)
class TimingReportSummary:
    wns_ns: Optional[float] = None
    tns_ns: Optional[float] = None
    clock_period_ns: Optional[float] = None
    fmax_mhz: Optional[float] = None

    @property
    def critical_path_ns(self) -> Optional[float]:
        if self.clock_period_ns is None:
            return None
        if self.wns_ns is None:
            return self.clock_period_ns
        return self.clock_period_ns - self.wns_ns


@dataclass(frozen=True)
class AreaReportSummary:
    total_area: Optional[float] = None
    combinational_area: Optional[float] = None
    sequential_area: Optional[float] = None


@dataclass(frozen=True)
class PowerReportSummary:
    dynamic_mw: Optional[float] = None
    leakage_mw: Optional[float] = None
    total_mw: Optional[float] = None


@dataclass(frozen=True)
class ImplementationReportBundle:
    timing: TimingReportSummary
    area: AreaReportSummary
    power: PowerReportSummary
    sources: Tuple[str, ...]


def parse_timing_report(text: str) -> TimingReportSummary:
    clock_period_ns = _match_float(
        text,
        [
            r"Clock(?:\s+Period)?\s*[:=]\s*([-+]?\d+(?:\.\d+)?)",
            r"target\s+period\s*[:=]\s*([-+]?\d+(?:\.\d+)?)\s*ns",
        ],
    )
    fmax_mhz = _match_float(
        text,
        [
            r"\bFmax\b\s*[:=]\s*([-+]?\d+(?:\.\d+)?)",
            r"Frequency\s*[:=]\s*([-+]?\d+(?:\.\d+)?)\s*MHz",
        ],
    )
    if clock_period_ns is None and fmax_mhz not in (None, 0):
        clock_period_ns = 1000.0 / fmax_mhz
    if fmax_mhz is None and clock_period_ns not in (None, 0):
        fmax_mhz = 1000.0 / clock_period_ns
    return TimingReportSummary(
        wns_ns=_match_float(text, [r"\bWNS\b\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"worst slack\s*=\s*([-+]?\d+(?:\.\d+)?)"]),
        tns_ns=_match_float(text, [r"\bTNS\b\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"Total Negative Slack\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"]),
        clock_period_ns=clock_period_ns,
        fmax_mhz=fmax_mhz,
    )


def parse_area_report(text: str) -> AreaReportSummary:
    return AreaReportSummary(
        total_area=_match_float(text, [r"Total area\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"cell area\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"]),
        combinational_area=_match_float(text, [r"Combinational area\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"]),
        sequential_area=_match_float(text, [r"Sequential area\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"]),
    )


def parse_power_report(text: str) -> PowerReportSummary:
    dynamic = _match_float(text, [r"dynamic power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"Dynamic Power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"])
    leakage = _match_float(text, [r"leakage power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"Leakage Power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"])
    total = _match_float(text, [r"total power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", r"Total Power\s*[:=]\s*([-+]?\d+(?:\.\d+)?)"])
    if total is None and dynamic is not None and leakage is not None:
        total = round(dynamic + leakage, 12)
    return PowerReportSummary(dynamic_mw=dynamic, leakage_mw=leakage, total_mw=total)


def load_implementation_report_bundle(paths: Sequence[Path | str]) -> ImplementationReportBundle:
    timing = TimingReportSummary()
    area = AreaReportSummary()
    power = PowerReportSummary()
    sources = []
    for path_like in paths:
        path = Path(path_like)
        text = path.read_text(encoding="utf-8")
        sources.append(str(path))
        t = parse_timing_report(text)
        a = parse_area_report(text)
        p = parse_power_report(text)
        timing = TimingReportSummary(
            wns_ns=t.wns_ns if t.wns_ns is not None else timing.wns_ns,
            tns_ns=t.tns_ns if t.tns_ns is not None else timing.tns_ns,
            clock_period_ns=(
                t.clock_period_ns if t.clock_period_ns is not None else timing.clock_period_ns
            ),
            fmax_mhz=t.fmax_mhz if t.fmax_mhz is not None else timing.fmax_mhz,
        )
        area = AreaReportSummary(
            total_area=a.total_area if a.total_area is not None else area.total_area,
            combinational_area=a.combinational_area if a.combinational_area is not None else area.combinational_area,
            sequential_area=a.sequential_area if a.sequential_area is not None else area.sequential_area,
        )
        power = PowerReportSummary(
            dynamic_mw=p.dynamic_mw if p.dynamic_mw is not None else power.dynamic_mw,
            leakage_mw=p.leakage_mw if p.leakage_mw is not None else power.leakage_mw,
            total_mw=p.total_mw if p.total_mw is not None else power.total_mw,
        )
    return ImplementationReportBundle(timing=timing, area=area, power=power, sources=tuple(sources))


def _match_float(text: str, patterns: Iterable[str]) -> Optional[float]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None
