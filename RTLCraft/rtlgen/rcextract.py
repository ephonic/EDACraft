"""
rtlgen.rcextract — RC extraction from global / detailed routing results
with RTL-level optimization feedback.

Supports:
1. Global-routing-based RC extraction (fast, coarse)
2. Detailed-routing-based RC extraction (more accurate)
3. Feedback generation for RTL / logic synthesis optimization
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rtlgen.netlist import Netlist
from rtlgen.placement import PlacementResult
from rtlgen.routing import RoutingResult


@dataclass
class NetRC:
    net_name: str
    wirelength: float  # um
    resistance: float  # ohm
    capacitance: float  # fF
    elmore_delay: float  # ps
    fanout: int
    pin_delays: Dict[str, float] = field(default_factory=dict)  # pin -> delay (ps)


@dataclass
class RCExtractionResult:
    nets: Dict[str, NetRC]
    total_wirelength: float
    total_res: float
    total_cap: float


@dataclass
class RTLFeedbackItem:
    net_name: str
    severity: str  # "critical", "warning", "info"
    wirelength: float
    elmore_ps: float
    fanout: int
    suggestion: str


@dataclass
class RTLFeedbackReport:
    items: List[RTLFeedbackItem]
    summary: str


class _BaseRCExtractor:
    """Shared RC physics."""

    def __init__(
        self,
        netlist: Netlist,
        r_sheet: float = 0.08,      # ohm/sq (metal2 typical)
        c_area: float = 0.03,       # fF/um^2
        c_fringe: float = 0.04,     # fF/um
        wire_width: float = 0.14,   # um
    ):
        self.netlist = netlist
        self.r_sheet = r_sheet
        self.c_area = c_area
        self.c_fringe = c_fringe
        self.wire_width = wire_width

    def _calc_rc(self, wl: float) -> Tuple[float, float, float]:
        """Return (R_ohm, C_fF, elmore_ps) for a given wirelength."""
        if wl <= 0.0:
            return 0.0, 0.0, 0.0
        r = self.r_sheet * (wl / self.wire_width)
        c = self.c_area * wl * self.wire_width + self.c_fringe * wl
        # Elmore for distributed RC: 0.5 * R * C
        # R(ohm) * C(fF) = 1e-15 s = 1 fs
        elmore = 0.5 * r * c  # in femtoseconds
        elmore_ps = elmore / 1e3  # 1 ps = 1e3 fs
        return r, c, elmore_ps


class GlobalRCExtractor(_BaseRCExtractor):
    """Extract RC from global routing paths."""

    def __init__(
        self,
        netlist: Netlist,
        routing_result: RoutingResult,
        placement: PlacementResult,
        **kwargs,
    ):
        super().__init__(netlist, **kwargs)
        self.routing = routing_result
        self.placement = placement

        grid_cols = max(1, routing_result.global_h_use.shape[1] + 1)
        grid_rows = max(1, routing_result.global_v_use.shape[0])
        self.grid_w = placement.width / grid_cols
        self.grid_h = placement.height / grid_rows

    def _path_length(self, path: List[Tuple[int, int]]) -> float:
        """Physical wirelength of a global grid path."""
        total = 0.0
        for i in range(len(path) - 1):
            dx = abs(path[i + 1][0] - path[i][0])
            dy = abs(path[i + 1][1] - path[i][1])
            total += dx * self.grid_w + dy * self.grid_h
        return total

    def extract(self) -> RCExtractionResult:
        nets_rc: Dict[str, NetRC] = {}
        total_wl = 0.0
        total_r = 0.0
        total_c = 0.0

        for net_name, segments in self.routing.global_routes.items():
            if not segments:
                continue
            wl = sum(self._path_length(seg) for seg in segments)
            if wl <= 0.0:
                continue
            r, c, elmore = self._calc_rc(wl)
            net = self.netlist.nets.get(net_name)
            fanout = len(net.loads) if net else 0
            nrc = NetRC(
                net_name=net_name,
                wirelength=wl,
                resistance=r,
                capacitance=c,
                elmore_delay=elmore,
                fanout=fanout,
                pin_delays={},
            )
            if net:
                for cell_name, pin_name in net.loads:
                    nrc.pin_delays[f"{cell_name}:{pin_name}"] = elmore
            nets_rc[net_name] = nrc
            total_wl += wl
            total_r += r
            total_c += c

        return RCExtractionResult(
            nets=nets_rc,
            total_wirelength=total_wl,
            total_res=total_r,
            total_cap=total_c,
        )


class DetailedRCExtractor(_BaseRCExtractor):
    """Extract RC from detailed routing physical paths."""

    def __init__(
        self,
        netlist: Netlist,
        routing_result: RoutingResult,
        **kwargs,
    ):
        super().__init__(netlist, **kwargs)
        self.routing = routing_result

    @staticmethod
    def _path_length(phys_path: List[Tuple[float, float]]) -> float:
        total = 0.0
        for i in range(len(phys_path) - 1):
            total += abs(phys_path[i + 1][0] - phys_path[i][0]) + abs(phys_path[i + 1][1] - phys_path[i][1])
        return total

    def extract(self) -> RCExtractionResult:
        nets_rc: Dict[str, NetRC] = {}
        total_wl = 0.0
        total_r = 0.0
        total_c = 0.0

        for net_name, segments in self.routing.detailed_routes.items():
            if not segments:
                continue
            wl = sum(self._path_length(seg) for seg in segments)
            if wl <= 0.0:
                continue
            r, c, elmore = self._calc_rc(wl)
            net = self.netlist.nets.get(net_name)
            fanout = len(net.loads) if net else 0
            nrc = NetRC(
                net_name=net_name,
                wirelength=wl,
                resistance=r,
                capacitance=c,
                elmore_delay=elmore,
                fanout=fanout,
                pin_delays={},
            )
            if net:
                for cell_name, pin_name in net.loads:
                    nrc.pin_delays[f"{cell_name}:{pin_name}"] = elmore
            nets_rc[net_name] = nrc
            total_wl += wl
            total_r += r
            total_c += c

        return RCExtractionResult(
            nets=nets_rc,
            total_wirelength=total_wl,
            total_res=total_r,
            total_cap=total_c,
        )


class RTLFeedbackEngine:
    """Generate RTL / synthesis optimization hints from RC extraction."""

    def __init__(
        self,
        netlist: Netlist,
        rc_result: RCExtractionResult,
        elmore_critical_ps: float = 50.0,
        long_wire_um: float = 100.0,
        high_fanout: int = 8,
    ):
        self.netlist = netlist
        self.rc = rc_result
        self.elmore_critical = elmore_critical_ps
        self.long_wire = long_wire_um
        self.high_fanout = high_fanout

    def analyze(self) -> RTLFeedbackReport:
        items: List[RTLFeedbackItem] = []
        sorted_nets = sorted(
            self.rc.nets.values(),
            key=lambda n: n.elmore_delay,
            reverse=True,
        )

        for nrc in sorted_nets:
            # Determine severity and suggestion
            if nrc.elmore_delay >= self.elmore_critical and nrc.fanout >= self.high_fanout:
                severity = "critical"
                suggestion = (
                    f"High RC ({nrc.elmore_delay:.1f} ps) + high fanout ({nrc.fanout}). "
                    "Suggestion: RTL-level pipeline insertion near this net, or fanout splitting / buffer tree."
                )
            elif nrc.elmore_delay >= self.elmore_critical:
                severity = "warning"
                suggestion = (
                    f"Long wire ({nrc.wirelength:.1f} um) causes {nrc.elmore_delay:.1f} ps delay. "
                    "Suggestion: Add a pipeline stage or constrain cells closer in placement."
                )
            elif nrc.wirelength >= self.long_wire and nrc.fanout >= self.high_fanout:
                severity = "warning"
                suggestion = (
                    f"Long wire ({nrc.wirelength:.1f} um) with fanout {nrc.fanout}. "
                    "Suggestion: Duplicate driver in RTL or insert buffer tree post-synthesis."
                )
            else:
                continue

            items.append(
                RTLFeedbackItem(
                    net_name=nrc.net_name,
                    severity=severity,
                    wirelength=nrc.wirelength,
                    elmore_ps=nrc.elmore_delay,
                    fanout=nrc.fanout,
                    suggestion=suggestion,
                )
            )

            if len(items) >= 50:
                break

        critical_count = sum(1 for it in items if it.severity == "critical")
        warning_count = sum(1 for it in items if it.severity == "warning")

        summary = (
            f"Analyzed {len(self.rc.nets)} routed nets. "
            f"Total wirelength = {self.rc.total_wirelength:.1f} um, "
            f"Total R = {self.rc.total_res:.1f} ohm, Total C = {self.rc.total_cap:.1f} fF. "
            f"Feedback: {critical_count} critical, {warning_count} warnings."
        )

        return RTLFeedbackReport(items=items, summary=summary)

    def report_text(self) -> str:
        report = self.analyze()
        lines = ["=" * 60, "RTL Feedback Report", "=" * 60, report.summary, ""]
        for it in report.items:
            lines.append(f"[{it.severity.upper()}] {it.net_name}")
            lines.append(f"  Wirelength: {it.wirelength:.1f} um  Elmore: {it.elmore_ps:.1f} ps  Fanout: {it.fanout}")
            lines.append(f"  -> {it.suggestion}")
            lines.append("")
        return "\n".join(lines)
