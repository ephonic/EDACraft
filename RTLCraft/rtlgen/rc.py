"""
rtlgen.rc — Fast geometry-driven RC extraction for placed netlists.

Provides:
- Per-net resistance/capacitance based on Manhattan wirelength
- Elmore delay estimation
- Simplified SPEF-like output
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rtlgen.lef import LefLibrary
from rtlgen.netlist import Netlist
from rtlgen.placement import PlacementResult


@dataclass
class NetRC:
    net_name: str
    resistance: float  # Ohms
    capacitance: float  # pF
    elmore_delay: float  # ns
    pin_delays: Dict[str, float] = field(default_factory=dict)  # pin_full_name -> delay


@dataclass
class RCExtractionResult:
    nets: Dict[str, NetRC]
    total_cap: float
    total_res: float


class FastRCExtractor:
    """Geometry-driven fast RC extractor.

    Uses simplified layer parameters:
    - R_sheet (ohm/square) derived from typical values
    - C_area (fF/um^2) and C_fringe (fF/um) for each metal layer
    """

    def __init__(
        self,
        netlist: Netlist,
        lef: LefLibrary,
        placement: PlacementResult,
        r_sheet: float = 0.1,  # ohm per square
        c_area: float = 0.03,  # fF per um^2
        c_fringe: float = 0.04,  # fF per um
        via_r: float = 1.0,  # ohm
        via_c: float = 0.1,  # fF
    ):
        self.netlist = netlist
        self.lef = lef
        self.placement = placement
        self.r_sheet = r_sheet
        self.c_area = c_area
        self.c_fringe = c_fringe
        self.via_r = via_r
        self.via_c = via_c

    def _pin_location(self, cell_name: str, pin_name: str) -> Optional[tuple]:
        """Approximate pin location = cell position + pin shape center."""
        cell = self.netlist.cells.get(cell_name)
        if cell is None:
            return None
        pos = self.placement.positions.get(cell_name)
        if pos is None:
            return None
        macro = self.lef.macros.get(cell.cell_type)
        if macro is None:
            return pos
        pin = macro.pins.get(pin_name)
        if not pin or not pin.shapes:
            return pos
        shape = pin.shapes[0]
        cx = (shape.x1 + shape.x2) * 0.5
        cy = (shape.y1 + shape.y2) * 0.5
        return (pos[0] + cx, pos[1] + cy)

    def _wirelength(self, net_name: str) -> float:
        """Estimate wirelength as half-perimeter of bounding box of all pins."""
        net = self.netlist.nets.get(net_name)
        if net is None:
            return 0.0
        pts = []
        if net.driver:
            loc = self._pin_location(net.driver[0], net.driver[1])
            if loc:
                pts.append(loc)
        for cell_name, pin_name in net.loads:
            loc = self._pin_location(cell_name, pin_name)
            if loc:
                pts.append(loc)
        if len(pts) < 2:
            return 0.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    def extract(self) -> RCExtractionResult:
        nets_rc: Dict[str, NetRC] = {}
        total_cap = 0.0
        total_res = 0.0

        # Pick a default layer for wire width
        layer = next(iter(self.lef.layers.values()))
        width = layer.width

        for net_name, net in self.netlist.nets.items():
            wl = self._wirelength(net_name)
            if wl <= 0.0:
                continue

            # Approximate wire as a single straight segment of length = wl, width = layer.width
            # R = r_sheet * (L / W)
            r = self.r_sheet * (wl / width)
            # C = c_area * L * W + c_fringe * L
            c = self.c_area * wl * width + self.c_fringe * wl
            # Elmore delay = 0.5 * R * C (distributed RC approximation)
            elmore = 0.5 * r * c * 1e-3  # convert fF*ohm -> ps -> ns (scale factor approx)

            # Actually fF * ohm = 1e-15 * 1 = 1e-15 s = 1e-6 ps, so multiply by 1e-6 to get ps, then 1e-3 to get ns
            # Wait: r is in ohm, c is in fF (1e-15 F). r*c = 1e-15 seconds = 1 femtosecond.
            # So r*c is already in femtoseconds. 1 ns = 1e6 ps = 1e9 fs.
            # So elmore in ns = 0.5 * r * c / 1e9
            elmore = 0.5 * r * c / 1e9

            nrc = NetRC(
                net_name=net_name,
                resistance=r,
                capacitance=c,
                elmore_delay=elmore,
            )

            # Assign elmore delay to each load pin
            if net.driver:
                for cell_name, pin_name in net.loads:
                    nrc.pin_delays[f"{cell_name}:{pin_name}"] = elmore

            nets_rc[net_name] = nrc
            total_cap += c
            total_res += r

        return RCExtractionResult(
            nets=nets_rc,
            total_cap=total_cap,
            total_res=total_res,
        )
