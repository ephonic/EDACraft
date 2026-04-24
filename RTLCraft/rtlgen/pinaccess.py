"""
rtlgen.pinaccess — Pin access optimization with cell-level and module-level DP.

Flow:
1. Cell-level DP: for each cell instance, generate multiple access candidates per pin,
   enumerate schemes (one candidate per pin), score by intra-cell compactness,
   and keep top-K schemes.
2. Module-level DP: process cells in placement order (x-major). For each cell,
   pick the best scheme among its top-K by minimizing transition cost
   (wirelength to previously processed neighbor cells on shared nets).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from rtlgen.lef import LefLibrary
from rtlgen.netlist import Netlist
from rtlgen.placement import PlacementResult


@dataclass
class PinAccessCandidate:
    x: float
    y: float
    cost: float


class PinAccessOptimizer:
    def __init__(
        self,
        netlist: Netlist,
        placement: PlacementResult,
        lef: LefLibrary,
        track_pitch: float = 1.0,
        max_candidates_per_pin: int = 3,
        top_k_schemes: int = 3,
    ):
        self.netlist = netlist
        self.placement = placement
        self.lef = lef
        self.track_pitch = track_pitch
        self.max_cand = max(2, max_candidates_per_pin)
        self.top_k = max(2, top_k_schemes)

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------

    def _candidates_for_pin(self, cell_name: str, pin_name: str) -> List[PinAccessCandidate]:
        cell_type = self.netlist.cells[cell_name].cell_type
        macro = self.lef.macros.get(cell_type)
        if macro is None or pin_name not in macro.pins or not macro.pins[pin_name].shapes:
            # fallback: cell center
            x, y = self.placement.positions[cell_name]
            return [PinAccessCandidate(x + 0.5, y + 0.5, 0.0)]

        cell_x, cell_y = self.placement.positions[cell_name]
        cell_w, cell_h = macro.size

        rect = macro.pins[pin_name].shapes[0]
        pcx = cell_x + (rect.x1 + rect.x2) / 2.0
        pcy = cell_y + (rect.y1 + rect.y2) / 2.0
        pitch = self.track_pitch

        raw = [
            (pcx, pcy, 0.0),                                    # center
            (pcx, round(pcy / pitch) * pitch, 0.05),            # snap H
            (round(pcx / pitch) * pitch, pcy, 0.05),            # snap V
            (cell_x, pcy, 0.2),                                 # left edge
            (cell_x + cell_w, pcy, 0.2),                        # right edge
            (pcx, cell_y, 0.2),                                 # bottom edge
            (pcx, cell_y + cell_h, 0.2),                        # top edge
        ]

        # deduplicate and filter out-of-die
        seen = set()
        candidates = []
        for x, y, c in raw:
            key = (round(x, 6), round(y, 6))
            if key in seen:
                continue
            seen.add(key)
            if x < -0.01 or y < -0.01:
                continue
            if x > self.placement.width + 0.01 or y > self.placement.height + 0.01:
                continue
            candidates.append(PinAccessCandidate(x, y, c))

        if not candidates:
            candidates.append(PinAccessCandidate(pcx, pcy, 0.0))

        candidates.sort(key=lambda cand: cand.cost)
        return candidates[: self.max_cand]

    # ------------------------------------------------------------------
    # Cell-level DP: enumerate schemes, keep top-K
    # ------------------------------------------------------------------

    def _cell_dp(self, cell_name: str) -> List[Tuple[float, Dict[str, Tuple[float, float]]]]:
        cell_type = self.netlist.cells[cell_name].cell_type
        macro = self.lef.macros.get(cell_type)
        pin_names = list(macro.pins.keys()) if macro else []
        if not pin_names:
            return [(0.0, {})]

        cand_lists = [self._candidates_for_pin(cell_name, p) for p in pin_names]
        schemes: List[Tuple[float, Dict[str, Tuple[float, float]]]] = []

        for combo in itertools.product(*cand_lists):
            pts = [(c.x, c.y) for c in combo]
            costs = [c.cost for c in combo]
            intra = sum(costs)
            if len(pts) > 1:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                intra += 0.03 * (max(xs) - min(xs) + max(ys) - min(ys))
            pin_dict = {pin_names[i]: pts[i] for i in range(len(pin_names))}
            schemes.append((intra, pin_dict))

        schemes.sort(key=lambda t: t[0])
        return schemes[: self.top_k]

    # ------------------------------------------------------------------
    # Module-level DP: sequence DP over placement order
    # ------------------------------------------------------------------

    def _build_pair_nets(self) -> Dict[Tuple[str, str], List[Tuple[List[str], List[str]]]]:
        """Precompute shared nets and pin lists for every cell pair."""
        pair_nets: Dict[Tuple[str, str], List[Tuple[List[str], List[str]]]] = {}
        for net_name, net in self.netlist.nets.items():
            pin_map: Dict[str, List[str]] = {}
            if net.driver and net.driver[0] in self.placement.positions:
                pin_map.setdefault(net.driver[0], []).append(net.driver[1])
            for lc, lp in net.loads:
                if lc in self.placement.positions:
                    pin_map.setdefault(lc, []).append(lp)
            cells = list(pin_map.keys())
            if len(cells) < 2:
                continue
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    c1, c2 = cells[i], cells[j]
                    pair_nets.setdefault((c1, c2), []).append((pin_map[c1], pin_map[c2]))
                    pair_nets.setdefault((c2, c1), []).append((pin_map[c2], pin_map[c1]))
        return pair_nets

    def optimize(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Run cell-level + module-level DP and return chosen access point per pin."""
        # Placement order: left-to-right, top-to-bottom
        cells = sorted(
            self.placement.positions.keys(),
            key=lambda c: (self.placement.positions[c][0], self.placement.positions[c][1]),
        )

        # Cell-level schemes
        cell_schemes: Dict[str, List[Tuple[float, Dict[str, Tuple[float, float]]]]] = {
            c: self._cell_dp(c) for c in cells
        }

        pair_nets = self._build_pair_nets()

        K = self.top_k
        dp = [dict() for _ in range(len(cells))]
        choice = [dict() for _ in range(len(cells))]

        for idx, c in enumerate(cells):
            schemes = cell_schemes[c]
            if idx == 0:
                for s_i, (intra, _) in enumerate(schemes):
                    dp[idx][s_i] = intra
                continue

            prev = cells[idx - 1]
            prev_schemes = cell_schemes[prev]
            shared = pair_nets.get((prev, c), [])

            for s_i, (intra, pin_dict) in enumerate(schemes):
                best_cost = float("inf")
                best_prev_s = 0
                for ps_i, (p_intra, p_pin_dict) in enumerate(prev_schemes):
                    trans = 0.0
                    for c_pins, p_pins in shared:
                        min_d = float("inf")
                        for cp in c_pins:
                            cx, cy = pin_dict.get(cp, self.placement.positions[c])
                            for pp in p_pins:
                                px, py = p_pin_dict.get(pp, self.placement.positions[prev])
                                d = abs(cx - px) + abs(cy - py)
                                if d < min_d:
                                    min_d = d
                        if min_d < float("inf"):
                            trans += min_d
                    total = dp[idx - 1][ps_i] + intra + trans
                    if total < best_cost:
                        best_cost = total
                        best_prev_s = ps_i
                dp[idx][s_i] = best_cost
                choice[idx][s_i] = best_prev_s

        # Backtrack
        chosen_s: Dict[str, int] = {}
        last_s = min(dp[-1], key=dp[-1].get)
        chosen_s[cells[-1]] = last_s
        for idx in range(len(cells) - 2, -1, -1):
            chosen_s[cells[idx]] = choice[idx + 1][chosen_s[cells[idx + 1]]]

        result: Dict[str, Dict[str, Tuple[float, float]]] = {}
        for c in cells:
            s_i = chosen_s[c]
            _, pin_dict = cell_schemes[c][s_i]
            result[c] = pin_dict
        return result
