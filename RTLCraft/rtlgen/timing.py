"""
rtlgen.timing — Block-based static timing analysis for mapped netlists.

Provides:
- NLDM 2D table lookup with bilinear interpolation
- Forward / backward traversal on a pin-level timing graph
- Slack calculation for gate sizing feedback
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rtlgen.liberty import LibertyLibrary, LibertyTable
from rtlgen.netlist import Netlist, NetlistNet
from rtlgen.synth import WireLoadModel


@dataclass
class TimingNode:
    """A pin-level timing node (cell_pin or primary port)."""

    full_name: str  # e.g. "g00:A" or "PI:\\a[0]" or "PO:\\y[0]"
    arrival: float = 0.0
    slew: float = 0.01  # input transition time (ns)
    required: float = float("inf")
    slack: float = float("inf")
    is_input: bool = False
    is_output: bool = False
    cell_name: Optional[str] = None
    pin_name: Optional[str] = None


def _avg_table(tbl_rise: Optional[LibertyTable], tbl_fall: Optional[LibertyTable],
               x: float, y: float) -> float:
    """Average rise/fall lookup."""
    v_rise = tbl_rise.lookup(x, y) if tbl_rise else 0.0
    v_fall = tbl_fall.lookup(x, y) if tbl_fall else 0.0
    return (v_rise + v_fall) * 0.5


class TimingAnalyzer:
    """Pin-level STA engine for a mapped netlist + Liberty library."""

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
        self.nodes: Dict[str, TimingNode] = {}
        self._build_graph()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def _build_graph(self):
        # Primary inputs
        for net_name, net in self.netlist.nets.items():
            if net.port_direction == "input":
                node = TimingNode(
                    full_name=f"PI:{net_name}",
                    slew=self.default_slew,
                    is_input=True,
                )
                self.nodes[node.full_name] = node
            elif net.port_direction == "output":
                node = TimingNode(
                    full_name=f"PO:{net_name}",
                    is_output=True,
                )
                self.nodes[node.full_name] = node

        # Cell pins
        for cell_name, cell in self.netlist.cells.items():
            lib_cell = self.liberty.cells.get(cell.cell_type)
            for pin_name in cell.pins:
                full = f"{cell_name}:{pin_name}"
                self.nodes[full] = TimingNode(
                    full_name=full,
                    cell_name=cell_name,
                    pin_name=pin_name,
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _net_capacitance(self, net: NetlistNet) -> float:
        """Total load capacitance on a net (sum of all load pin caps)."""
        total = 0.0
        for cell_name, pin_name in net.loads:
            cell = self.netlist.cells.get(cell_name)
            if cell is None:
                continue
            lib_cell = self.liberty.cells.get(cell.cell_type)
            if lib_cell is None:
                continue
            lib_pin = lib_cell.pins.get(pin_name)
            if lib_pin and lib_pin.capacitance:
                total += lib_pin.capacitance
        return total

    def _cell_output_pin(self, cell_name: str) -> Optional[str]:
        """Return the (first) output pin name of a cell instance."""
        cell = self.netlist.cells.get(cell_name)
        if cell is None:
            return None
        lib_cell = self.liberty.cells.get(cell.cell_type)
        if lib_cell is None:
            return None
        for pin_name in cell.pins:
            lib_pin = lib_cell.pins.get(pin_name)
            if lib_pin and lib_pin.direction == "output":
                return pin_name
        return None

    def _timing_arc(self, cell_type: str, out_pin: str, in_pin: str):
        """Return the LibertyTiming arc from in_pin to out_pin."""
        lib_cell = self.liberty.cells.get(cell_type)
        if lib_cell is None:
            return None
        out_lib = lib_cell.pins.get(out_pin)
        if out_lib is None:
            return None
        for t in out_lib.timings:
            if t.related_pin == in_pin:
                return t
        return None

    def _calc_arc_delay_slew(self, cell_type: str, out_pin: str, in_pin: str,
                             input_slew: float, load_cap: float) -> Tuple[float, float]:
        """Return (delay, output_slew) for a combinational arc."""
        arc = self._timing_arc(cell_type, out_pin, in_pin)
        if arc is None:
            return 0.0, input_slew
        delay = _avg_table(arc.cell_rise, arc.cell_fall, input_slew, load_cap)
        out_slew = _avg_table(arc.rise_transition, arc.fall_transition, input_slew, load_cap)
        return delay, out_slew

    # ------------------------------------------------------------------
    # Forward traversal
    # ------------------------------------------------------------------
    def forward(self):
        """Compute arrival times and slews from PIs to POs."""
        visited_cells: set = set()

        # Initialize PI arrivals
        for net_name, net in self.netlist.nets.items():
            if net.port_direction == "input":
                pi_node = self.nodes[f"PI:{net_name}"]
                pi_node.arrival = 0.0
                pi_node.slew = self.default_slew

        # Topological-like propagation: iterate until no change
        changed = True
        while changed:
            changed = False
            for cell_name, cell in self.netlist.cells.items():
                if cell_name in visited_cells:
                    continue
                lib_cell = self.liberty.cells.get(cell.cell_type)
                if lib_cell is None:
                    visited_cells.add(cell_name)
                    continue

                out_pin = self._cell_output_pin(cell_name)
                if out_pin is None:
                    visited_cells.add(cell_name)
                    continue

                # Check all input pins have known arrival/slew
                all_ready = True
                in_arrivals = []
                in_slews = []
                for pin_name, pin in cell.pins.items():
                    lib_pin = lib_cell.pins.get(pin_name)
                    if lib_pin and lib_pin.direction == "input":
                        net = self.netlist.nets.get(pin.net_name)
                        driver = net.driver if net else None
                        if driver:
                            driver_node = self.nodes.get(f"{driver[0]}:{driver[1]}")
                        else:
                            driver_node = self.nodes.get(f"PI:{pin.net_name}")
                        if driver_node is None:
                            all_ready = False
                            break
                        in_arrivals.append(driver_node.arrival)
                        in_slews.append(driver_node.slew)

                if not all_ready:
                    continue

                # Compute load cap on output net
                out_net_name = cell.pins[out_pin].net_name
                out_net = self.netlist.nets.get(out_net_name)
                load_cap = self._net_capacitance(out_net) if out_net else 0.0
                wire_delay = self.wlm.estimate_delay(len(out_net.loads)) if out_net else 0.0

                # Compute arc delay from latest input
                max_arrival = max(in_arrivals) if in_arrivals else 0.0
                max_slew = max(in_slews) if in_slews else self.default_slew

                # For simplicity, use the arc from the latest input to output
                # (In reality each input has its own arc; we pessimistically take max)
                arc_delay = 0.0
                out_slew = max_slew
                for pin_name, pin in cell.pins.items():
                    lib_pin = lib_cell.pins.get(pin_name)
                    if lib_pin and lib_pin.direction == "input":
                        d, s = self._calc_arc_delay_slew(
                            cell.cell_type, out_pin, pin_name, max_slew, load_cap
                        )
                        arc_delay = max(arc_delay, d)
                        out_slew = max(out_slew, s)

                out_node = self.nodes[f"{cell_name}:{out_pin}"]
                new_arrival = max_arrival + arc_delay + wire_delay
                if new_arrival > out_node.arrival:
                    out_node.arrival = new_arrival
                    out_node.slew = out_slew
                    changed = True
                    visited_cells.discard(cell_name)  # allow re-evaluation if downstream changes

                # Also assign arrival to input pins (same as their driver net arrival)
                for pin_name, pin in cell.pins.items():
                    lib_pin = lib_cell.pins.get(pin_name)
                    if lib_pin and lib_pin.direction == "input":
                        in_node = self.nodes[f"{cell_name}:{pin_name}"]
                        net = self.netlist.nets.get(pin.net_name)
                        driver = net.driver if net else None
                        if driver:
                            driver_node = self.nodes.get(f"{driver[0]}:{driver[1]}")
                        else:
                            driver_node = self.nodes.get(f"PI:{pin.net_name}")
                        if driver_node and driver_node.arrival > in_node.arrival:
                            in_node.arrival = driver_node.arrival
                            in_node.slew = driver_node.slew

                visited_cells.add(cell_name)

        # Propagate to POs
        for net_name, net in self.netlist.nets.items():
            if net.port_direction == "output":
                po_node = self.nodes[f"PO:{net_name}"]
                if net.driver:
                    driver_node = self.nodes.get(f"{net.driver[0]}:{net.driver[1]}")
                    if driver_node:
                        wire_delay = self.wlm.estimate_delay(len(net.loads))
                        po_node.arrival = driver_node.arrival + wire_delay
                        po_node.slew = driver_node.slew

    # ------------------------------------------------------------------
    # Backward traversal
    # ------------------------------------------------------------------
    def backward(self, target_delay: Optional[float] = None):
        """Compute required times and slacks from POs to PIs."""
        if target_delay is None:
            target_delay = max((n.arrival for n in self.nodes.values() if n.is_output), default=0.0)

        # Reset required times
        for node in self.nodes.values():
            node.required = float("inf")

        # Initialize PO required times
        for net_name, net in self.netlist.nets.items():
            if net.port_direction == "output":
                po_node = self.nodes[f"PO:{net_name}"]
                po_node.required = target_delay

        # Propagate from POs to cell output pins
        for net_name, net in self.netlist.nets.items():
            if net.port_direction == "output" and net.driver:
                cell_name, pin_name = net.driver
                out_node = self.nodes.get(f"{cell_name}:{pin_name}")
                if out_node:
                    wire_delay = self.wlm.estimate_delay(len(net.loads))
                    new_req = target_delay - wire_delay
                    if new_req < out_node.required:
                        out_node.required = new_req

        # Topological backward: iterate until stable
        changed = True
        while changed:
            changed = False
            for cell_name, cell in self.netlist.cells.items():
                lib_cell = self.liberty.cells.get(cell.cell_type)
                if lib_cell is None:
                    continue
                out_pin = self._cell_output_pin(cell_name)
                if out_pin is None:
                    continue

                out_net_name = cell.pins[out_pin].net_name
                out_net = self.netlist.nets.get(out_net_name)
                load_cap = self._net_capacitance(out_net) if out_net else 0.0
                out_node = self.nodes[f"{cell_name}:{out_pin}"]
                req_out = out_node.required
                if req_out == float("inf"):
                    continue

                # For each input pin, required = req_out - arc_delay
                for pin_name, pin in cell.pins.items():
                    lib_pin = lib_cell.pins.get(pin_name)
                    if lib_pin and lib_pin.direction == "input":
                        in_node = self.nodes[f"{cell_name}:{pin_name}"]
                        d, _ = self._calc_arc_delay_slew(
                            cell.cell_type, out_pin, pin_name, in_node.slew, load_cap
                        )
                        new_req = req_out - d
                        if new_req < in_node.required:
                            in_node.required = new_req
                            changed = True

                        # Propagate to driver of the input net
                        net = self.netlist.nets.get(pin.net_name)
                        if net and net.driver:
                            driver_node = self.nodes.get(f"{net.driver[0]}:{net.driver[1]}")
                            if driver_node and new_req < driver_node.required:
                                driver_node.required = new_req
                                changed = True
                        elif net and net.port_direction == "input":
                            pi_node = self.nodes.get(f"PI:{pin.net_name}")
                            if pi_node and new_req < pi_node.required:
                                pi_node.required = new_req
                                changed = True

        # Compute slack for all nodes
        for node in self.nodes.values():
            node.slack = node.required - node.arrival

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def worst_slack(self) -> float:
        return min((n.slack for n in self.nodes.values() if n.is_output), default=float("inf"))

    def critical_path(self) -> List[str]:
        """Return a list of node full_names from a PI to the worst-slack PO."""
        # Find worst PO
        worst_po = None
        worst_slack = float("inf")
        for node in self.nodes.values():
            if node.is_output and node.slack < worst_slack:
                worst_slack = node.slack
                worst_po = node
        if worst_po is None:
            return []

        path = [worst_po.full_name]
        current_net = worst_po.full_name[3:]  # strip "PO:"

        # Back-trace through drivers
        visited = set()
        while True:
            net = self.netlist.nets.get(current_net)
            if net is None or net.driver is None:
                break
            driver_cell, driver_pin = net.driver
            driver_node = self.nodes.get(f"{driver_cell}:{driver_pin}")
            if driver_node is None or driver_node.full_name in visited:
                break
            visited.add(driver_node.full_name)
            path.append(driver_node.full_name)

            # Move to the input pin of this cell with worst (smallest) slack
            cell = self.netlist.cells.get(driver_cell)
            if cell is None:
                break
            lib_cell = self.liberty.cells.get(cell.cell_type)
            if lib_cell is None:
                break
            worst_in = None
            worst_in_slack = float("inf")
            for pin_name, pin in cell.pins.items():
                lib_pin = lib_cell.pins.get(pin_name)
                if lib_pin and lib_pin.direction == "input":
                    in_node = self.nodes.get(f"{driver_cell}:{pin_name}")
                    if in_node and in_node.slack < worst_in_slack:
                        worst_in_slack = in_node.slack
                        worst_in = in_node
            if worst_in is None:
                break
            path.append(worst_in.full_name)
            # driver net for this input
            net2 = self.netlist.nets.get(
                cell.pins[worst_in.pin_name].net_name
            )
            if net2 is None:
                break
            if net2.port_direction == "input":
                path.append(f"PI:{net2.name}")
                break
            current_net = net2.name

        return list(reversed(path))
