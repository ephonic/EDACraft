"""
rtlgen.sizing — Gate sizing engine for post-mapped netlists.

Provides:
- Slack-driven iterative cell up/down sizing
- Sensitivity-based candidate selection
- Re-emission of sized Verilog
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rtlgen.liberty import LibertyLibrary
from rtlgen.netlist import Netlist, NetlistCell, parse_mapped_verilog
from rtlgen.synth import WireLoadModel
from rtlgen.timing import TimingAnalyzer


@dataclass
class SizingResult:
    area: float
    delay: float
    worst_slack: float
    iterations: int
    sized_verilog: str
    report: str


class GateSizer:
    """Post-mapping gate sizing optimizer."""

    def __init__(
        self,
        netlist: Netlist,
        liberty: LibertyLibrary,
        wlm: Optional[WireLoadModel] = None,
        default_slew: float = 0.01,
    ):
        self.netlist = netlist
        self.liberty = liberty
        self.wlm = wlm or WireLoadModel()
        self.default_slew = default_slew
        self._function_groups = self._build_function_groups()

    def _build_function_groups(self) -> Dict[str, List[str]]:
        """Group cells by output pin function for sizing substitution."""
        groups: Dict[str, List[str]] = {}
        for cname, cell in self.liberty.cells.items():
            for pin in cell.pins.values():
                if pin.direction == "output" and pin.timings:
                    # key = function string if available, else cell name (no sizing possible)
                    func = getattr(pin, "function", None)
                    key = func if func else f"__unique__{cname}"
                    groups.setdefault(key, []).append(cname)
                    break
        return groups

    def _cell_group_key(self, cell_type: str) -> Optional[str]:
        lib_cell = self.liberty.cells.get(cell_type)
        if lib_cell is None:
            return None
        for pin in lib_cell.pins.values():
            if pin.direction == "output" and pin.timings:
                func = getattr(pin, "function", None)
                return func if func else f"__unique__{cell_type}"
        return None

    def _sizing_candidates(self, cell_type: str) -> List[str]:
        """Return other cell types in the same function group, sorted by area."""
        key = self._cell_group_key(cell_type)
        if key is None:
            return []
        group = self._function_groups.get(key, [])
        # Filter out self and sort by area
        others = [c for c in group if c != cell_type]
        others.sort(key=lambda c: self.liberty.cells[c].area)
        return others

    def _evaluate_swap(self, cell_name: str, new_type: str, target_delay: Optional[float]) -> Tuple[float, float]:
        """Evaluate (worst_slack, total_area) if we swap cell_name to new_type."""
        old_type = self.netlist.cells[cell_name].cell_type
        self.netlist.cells[cell_name].cell_type = new_type
        ta = TimingAnalyzer(self.netlist, self.liberty, self.wlm, self.default_slew)
        ta.forward()
        ta.backward(target_delay)
        slack = ta.worst_slack()
        area = self._total_area()
        # restore
        self.netlist.cells[cell_name].cell_type = old_type
        return slack, area

    def _total_area(self) -> float:
        area = 0.0
        for cell in self.netlist.cells.values():
            lib_cell = self.liberty.cells.get(cell.cell_type)
            if lib_cell:
                area += lib_cell.area
        return area

    def optimize(
        self,
        target_delay: Optional[float] = None,
        max_iterations: int = 20,
        area_budget: Optional[float] = None,
    ) -> SizingResult:
        """Run iterative slack-driven sizing."""
        initial_area = self._total_area()
        report_lines: List[str] = []
        report_lines.append(f"Initial area: {initial_area:.3f}")

        # Baseline timing
        ta = TimingAnalyzer(self.netlist, self.liberty, self.wlm, self.default_slew)
        ta.forward()
        ta.backward(target_delay)
        initial_delay = max((n.arrival for n in ta.nodes.values() if n.is_output), default=0.0)
        initial_slack = ta.worst_slack()
        report_lines.append(f"Initial delay: {initial_delay:.4f} ns")
        report_lines.append(f"Initial slack: {initial_slack:.4f} ns")

        # Check if any sizing candidates exist at all
        has_candidates = any(
            len(self._sizing_candidates(cell.cell_type)) > 0
            for cell in self.netlist.cells.values()
        )
        if not has_candidates:
            report_lines.append("No alternative drive-strength cells found in library; sizing skipped.")
            return SizingResult(
                area=initial_area,
                delay=initial_delay,
                worst_slack=initial_slack,
                iterations=0,
                sized_verilog=self._emit_verilog(),
                report="\n".join(report_lines),
            )

        for iteration in range(max_iterations):
            ta = TimingAnalyzer(self.netlist, self.liberty, self.wlm, self.default_slew)
            ta.forward()
            ta.backward(target_delay)
            slack = ta.worst_slack()

            if slack >= 0.0:
                report_lines.append(f"Iteration {iteration}: slack {slack:.4f} >= 0, done.")
                break

            # Identify negative-slack cells on critical path
            worst_po = min(
                (n for n in ta.nodes.values() if n.is_output),
                key=lambda n: n.slack,
                default=None,
            )
            if worst_po is None:
                break

            # Backtrace from worst PO to find best upsize candidate
            best_candidate: Optional[Tuple[str, str, float, float]] = None  # cell, new_type, slack_gain, area_cost
            current_net = worst_po.full_name[3:]

            visited_cells = set()
            while True:
                net = self.netlist.nets.get(current_net)
                if net is None or net.driver is None:
                    break
                cell_name, _ = net.driver
                if cell_name in visited_cells:
                    break
                visited_cells.add(cell_name)
                cell = self.netlist.cells[cell_name]
                candidates = self._sizing_candidates(cell.cell_type)
                for cand in candidates:
                    new_slack, new_area = self._evaluate_swap(cell_name, cand, target_delay)
                    old_area = self.liberty.cells[cell.cell_type].area
                    area_cost = new_area - self._total_area()  # since _evaluate_swap restores, this is 0 unless other logic changes
                    # Actually _total_area during evaluate_swap is based on the temporary change; let's compute manually
                    cand_area = self.liberty.cells[cand].area
                    area_cost = cand_area - old_area
                    slack_gain = new_slack - slack
                    # We want positive slack_gain with minimal area_cost
                    if slack_gain > 0:
                        if best_candidate is None or (slack_gain / max(area_cost, 1e-9)) > (best_candidate[2] / max(best_candidate[3], 1e-9)):
                            best_candidate = (cell_name, cand, slack_gain, area_cost)

                # Move upstream
                cell = self.netlist.cells.get(cell_name)
                if cell is None:
                    break
                lib_cell = self.liberty.cells.get(cell.cell_type)
                if lib_cell is None:
                    break
                # find input pin with worst slack
                worst_in = None
                worst_slack_val = float("inf")
                for pin_name in cell.pins:
                    lp = lib_cell.pins.get(pin_name)
                    if lp and lp.direction == "input":
                        in_node = ta.nodes.get(f"{cell_name}:{pin_name}")
                        if in_node and in_node.slack < worst_slack_val:
                            worst_slack_val = in_node.slack
                            worst_in = pin_name
                if worst_in is None:
                    break
                next_net = self.netlist.nets.get(cell.pins[worst_in].net_name)
                if next_net and next_net.port_direction == "input":
                    break
                current_net = next_net.name if next_net else None
                if current_net is None:
                    break

            if best_candidate is None:
                report_lines.append(f"Iteration {iteration}: no beneficial swap found.")
                break

            cell_name, new_type, slack_gain, area_cost = best_candidate
            if area_budget is not None and (self._total_area() + area_cost) > area_budget:
                report_lines.append(f"Iteration {iteration}: area budget would be exceeded.")
                break

            # Prevent oscillation: do not swap back to the type we just replaced in this iteration
            if getattr(self.netlist.cells[cell_name], '_last_type', None) == new_type:
                report_lines.append(f"Iteration {iteration}: swap to {new_type} would oscillate, stopping.")
                break
            self.netlist.cells[cell_name]._last_type = self.netlist.cells[cell_name].cell_type
            self.netlist.cells[cell_name].cell_type = new_type
            report_lines.append(
                f"Iteration {iteration}: upsized {cell_name} -> {new_type} "
                f"(slack_gain={slack_gain:.4f}, area_cost={area_cost:.3f})"
            )
        else:
            report_lines.append(f"Reached max_iterations ({max_iterations}).")

        # Final stats
        ta = TimingAnalyzer(self.netlist, self.liberty, self.wlm, self.default_slew)
        ta.forward()
        ta.backward(target_delay)
        final_area = self._total_area()
        final_delay = max((n.arrival for n in ta.nodes.values() if n.is_output), default=0.0)
        final_slack = ta.worst_slack()
        report_lines.append(f"Final area: {final_area:.3f}")
        report_lines.append(f"Final delay: {final_delay:.4f} ns")
        report_lines.append(f"Final slack: {final_slack:.4f} ns")

        return SizingResult(
            area=final_area,
            delay=final_delay,
            worst_slack=final_slack,
            iterations=iteration + 1,
            sized_verilog=self._emit_verilog(),
            report="\n".join(report_lines),
        )

    def _emit_verilog(self) -> str:
        """Re-emit the structural Verilog with sized cell types."""
        lines = []
        lines.append(f"module {self.netlist.module_name} (")
        port_decls = []
        for name, info in self.netlist.ports.items():
            if info["direction"] == "input":
                port_decls.append(f"    input {name}")
            else:
                port_decls.append(f"    output {name}")
        lines.append(",\n".join(port_decls))
        lines.append(");")

        # wires
        wire_names = [n for n, net in self.netlist.nets.items() if not net.is_port]
        if wire_names:
            for i in range(0, len(wire_names), 8):
                batch = wire_names[i:i+8]
                lines.append(f"  wire {', '.join(batch)};")

        # cells
        for cell in self.netlist.cells.values():
            pin_strs = [f".{pn}({p.net_name})" for pn, p in cell.pins.items()]
            lines.append(f"  {cell.cell_type:<12} {cell.name}({', '.join(pin_strs)});")

        lines.append("endmodule")
        return "\n".join(lines)
