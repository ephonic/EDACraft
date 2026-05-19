"""
rtlgen.tech_library — Technology Node Characterization Library

Provides process node timing, area, and power models for PPA estimation.
Maps RTL constructs (gate types, logic depth, bit widths) to physical
metrics at a given process node (e.g., 28nm, 7nm, 5nm).

Usage:
    from rtlgen import TechNode

    node = TechNode("7nm")
    delay = node.gate_delay("nand2")           # ps per NAND2 gate
    depth_budget = node.max_logic_depth(target_freq=2.0e9)  # max gates in critical path
    area = node.std_cell_area("dff")           # um^2 per flip-flop
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Gate-Level Characterization Data
# ============================================================================

# Typical standard-cell library metrics per process node.
# Values are representative, not tied to any specific foundry PDK.
_TECH_NODES: Dict[str, Dict[str, Any]] = {
    "180nm": {
        "node_name": "180nm",
        "min_feature_nm": 180,
        "vdd_v": 1.8,
        "gate_delay_ps": {
            "inv": 35,       # Inverter
            "nand2": 45,     # 2-input NAND
            "nand3": 65,     # 3-input NAND
            "nor2": 55,      # 2-input NOR
            "nor3": 80,      # 3-input NOR
            "xor2": 110,     # 2-input XOR
            "aoi21": 60,     # AND-OR-INVERT 2-1
            "oai21": 60,     # OR-AND-INVERT 2-1
            "mux2": 80,      # 2:1 MUX
            "mux4": 150,     # 4:1 MUX
            "fa": 180,       # Full adder
            "dff": 120,      # D flip-flop (clk->q)
        },
        "std_cell_area_um2": {
            "inv": 3.0,
            "nand2": 4.0,
            "nand3": 5.5,
            "nor2": 5.0,
            "nor3": 7.0,
            "xor2": 10.0,
            "aoi21": 6.0,
            "oai21": 6.0,
            "mux2": 7.0,
            "mux4": 13.0,
            "fa": 16.0,
            "dff": 10.0,
        },
        "wire_delay_ps_per_um": 0.4,
        "wire_cap_ff_per_um": 0.2,
        "dff_setup_ps": 120,
        "dff_hold_ps": 50,
        "clock_buffer_delay_ps": 100,
        "routing_overhead": 3.0,    # routing area = 3x std cell area
        "leakage_nw_per_cell": 50,  # nW per cell (typical corner)
    },
    "65nm": {
        "node_name": "65nm",
        "min_feature_nm": 65,
        "vdd_v": 1.2,
        "gate_delay_ps": {
            "inv": 12,
            "nand2": 16,
            "nand3": 24,
            "nor2": 20,
            "nor3": 30,
            "xor2": 40,
            "aoi21": 22,
            "oai21": 22,
            "mux2": 30,
            "mux4": 55,
            "fa": 65,
            "dff": 45,
        },
        "std_cell_area_um2": {
            "inv": 1.0,
            "nand2": 1.4,
            "nand3": 2.0,
            "nor2": 1.8,
            "nor3": 2.5,
            "xor2": 3.5,
            "aoi21": 2.2,
            "oai21": 2.2,
            "mux2": 2.5,
            "mux4": 4.5,
            "fa": 5.5,
            "dff": 3.5,
        },
        "wire_delay_ps_per_um": 0.6,
        "wire_cap_ff_per_um": 0.25,
        "dff_setup_ps": 45,
        "dff_hold_ps": 20,
        "clock_buffer_delay_ps": 40,
        "routing_overhead": 2.5,
        "leakage_nw_per_cell": 15,
    },
    "28nm": {
        "node_name": "28nm",
        "min_feature_nm": 28,
        "vdd_v": 1.0,
        "gate_delay_ps": {
            "inv": 6,
            "nand2": 8,
            "nand3": 12,
            "nor2": 10,
            "nor3": 15,
            "xor2": 20,
            "aoi21": 11,
            "oai21": 11,
            "mux2": 15,
            "mux4": 28,
            "fa": 32,
            "dff": 22,
        },
        "std_cell_area_um2": {
            "inv": 0.4,
            "nand2": 0.55,
            "nand3": 0.8,
            "nor2": 0.7,
            "nor3": 1.0,
            "xor2": 1.4,
            "aoi21": 0.9,
            "oai21": 0.9,
            "mux2": 1.0,
            "mux4": 1.8,
            "fa": 2.2,
            "dff": 1.4,
        },
        "wire_delay_ps_per_um": 0.8,
        "wire_cap_ff_per_um": 0.3,
        "dff_setup_ps": 22,
        "dff_hold_ps": 10,
        "clock_buffer_delay_ps": 20,
        "routing_overhead": 2.0,
        "leakage_nw_per_cell": 8,
    },
    "16nm": {
        "node_name": "16nm (FinFET)",
        "min_feature_nm": 16,
        "vdd_v": 0.8,
        "gate_delay_ps": {
            "inv": 4,
            "nand2": 5,
            "nand3": 8,
            "nor2": 7,
            "nor3": 10,
            "xor2": 14,
            "aoi21": 7,
            "oai21": 7,
            "mux2": 10,
            "mux4": 19,
            "fa": 22,
            "dff": 15,
        },
        "std_cell_area_um2": {
            "inv": 0.2,
            "nand2": 0.28,
            "nand3": 0.4,
            "nor2": 0.35,
            "nor3": 0.5,
            "xor2": 0.7,
            "aoi21": 0.45,
            "oai21": 0.45,
            "mux2": 0.5,
            "mux4": 0.9,
            "fa": 1.1,
            "dff": 0.7,
        },
        "wire_delay_ps_per_um": 1.0,
        "wire_cap_ff_per_um": 0.35,
        "dff_setup_ps": 15,
        "dff_hold_ps": 7,
        "clock_buffer_delay_ps": 12,
        "routing_overhead": 2.0,
        "leakage_nw_per_cell": 5,
    },
    "7nm": {
        "node_name": "7nm (FinFET)",
        "min_feature_nm": 7,
        "vdd_v": 0.7,
        "gate_delay_ps": {
            "inv": 3,
            "nand2": 4,
            "nand3": 6,
            "nor2": 5,
            "nor3": 8,
            "xor2": 10,
            "aoi21": 5,
            "oai21": 5,
            "mux2": 7,
            "mux4": 14,
            "fa": 16,
            "dff": 11,
        },
        "std_cell_area_um2": {
            "inv": 0.09,
            "nand2": 0.13,
            "nand3": 0.18,
            "nor2": 0.15,
            "nor3": 0.22,
            "xor2": 0.32,
            "aoi21": 0.2,
            "oai21": 0.2,
            "mux2": 0.23,
            "mux4": 0.4,
            "fa": 0.5,
            "dff": 0.32,
        },
        "wire_delay_ps_per_um": 1.2,
        "wire_cap_ff_per_um": 0.4,
        "dff_setup_ps": 11,
        "dff_hold_ps": 5,
        "clock_buffer_delay_ps": 8,
        "routing_overhead": 2.0,
        "leakage_nw_per_cell": 3,
    },
    "5nm": {
        "node_name": "5nm (FinFET)",
        "min_feature_nm": 5,
        "vdd_v": 0.65,
        "gate_delay_ps": {
            "inv": 2.5,
            "nand2": 3.5,
            "nand3": 5,
            "nor2": 4.5,
            "nor3": 7,
            "xor2": 8,
            "aoi21": 4,
            "oai21": 4,
            "mux2": 6,
            "mux4": 11,
            "fa": 13,
            "dff": 9,
        },
        "std_cell_area_um2": {
            "inv": 0.05,
            "nand2": 0.07,
            "nand3": 0.1,
            "nor2": 0.08,
            "nor3": 0.12,
            "xor2": 0.18,
            "aoi21": 0.11,
            "oai21": 0.11,
            "mux2": 0.13,
            "mux4": 0.22,
            "fa": 0.28,
            "dff": 0.18,
        },
        "wire_delay_ps_per_um": 1.5,
        "wire_cap_ff_per_um": 0.45,
        "dff_setup_ps": 9,
        "dff_hold_ps": 4,
        "clock_buffer_delay_ps": 6,
        "routing_overhead": 2.0,
        "leakage_nw_per_cell": 2,
    },
}


# ============================================================================
# RTL Construct → Gate Mapping
# ============================================================================

# How many equivalent gates each RTL construct costs.
# Used to estimate logic depth and area from AST analysis.
RTL_TO_GATES: Dict[str, Dict[str, Any]] = {
    # Arithmetic
    "add":   {"gates": ["fa"], "depth": 4, "area_cells": 16},       # ripple carry FA chain
    "add_carry": {"gates": ["fa"], "depth": 4, "area_cells": 16},
    "sub":   {"gates": ["fa", "xor2"], "depth": 5, "area_cells": 20},
    "mul":   {"gates": ["nand2", "fa"], "depth": 12, "area_cells": 128},  # array multiplier
    "mul_booth": {"gates": ["nand2", "fa", "mux2"], "depth": 16, "area_cells": 64},  # booth recoding
    "div":   {"gates": ["fa", "mux2", "nor2"], "depth": 24, "area_cells": 256},  # restoring divider
    # Logic
    "and":   {"gates": ["nand2", "inv"], "depth": 1, "area_cells": 2},
    "or":    {"gates": ["nor2", "inv"], "depth": 1, "area_cells": 2},
    "xor":   {"gates": ["xor2"], "depth": 1, "area_cells": 1},
    "not":   {"gates": ["inv"], "depth": 1, "area_cells": 1},
    # Mux
    "mux2":  {"gates": ["mux2"], "depth": 1, "area_cells": 1},
    "mux4":  {"gates": ["mux4"], "depth": 2, "area_cells": 1},
    "mux_tree_8": {"gates": ["mux2"], "depth": 3, "area_cells": 7},
    "mux_tree_16": {"gates": ["mux2"], "depth": 4, "area_cells": 15},
    # Comparator
    "eq":    {"gates": ["xor2", "nor2"], "depth": 2, "area_cells": 2},
    "ne":    {"gates": ["xor2", "nor2"], "depth": 2, "area_cells": 2},
    "lt":    {"gates": ["nor3", "inv"], "depth": 3, "area_cells": 2},
    "gt":    {"gates": ["nor3", "inv"], "depth": 3, "area_cells": 2},
    "lte":   {"gates": ["nor3", "inv"], "depth": 3, "area_cells": 2},
    "gte":   {"gates": ["nor3", "inv"], "depth": 3, "area_cells": 2},
    # Shift
    "shift_left":  {"gates": ["mux2"], "depth": 3, "area_cells": 16},  # barrel shifter per bit
    "shift_right": {"gates": ["mux2"], "depth": 3, "area_cells": 16},
    "rotate":      {"gates": ["mux2"], "depth": 3, "area_cells": 16},
    # Priority encoder
    "priority_enc": {"gates": ["nor2", "nor3"], "depth": 4, "area_cells": 16},
    # Counter
    "counter": {"gates": ["fa", "dff"], "depth": 5, "area_cells": 20},
    # Register file
    "regfile_read":  {"gates": ["mux4"], "depth": 3, "area_cells": 4},  # per bit
    "regfile_write": {"gates": ["dff"], "depth": 1, "area_cells": 1},   # per bit
    # FIFO
    "fifo_read":  {"gates": ["mux2"], "depth": 2, "area_cells": 2},
    "fifo_write": {"gates": ["dff"], "depth": 1, "area_cells": 1},
    # CSR / decode
    "decode": {"gates": ["nor2"], "depth": 2, "area_cells": 4},
    "csr_read": {"gates": ["dff"], "depth": 1, "area_cells": 1},
}


@dataclass
class TimingConstraint:
    """Timing budget analysis for a critical path."""
    target_freq_ghz: float
    clock_period_ps: float = 0.0
    setup_budget_ps: float = 0.0
    clock_skew_ps: float = 0.0
    max_logic_delay_ps: float = 0.0

    def __post_init__(self):
        self.clock_period_ps = 1000.0 / self.target_freq_ghz
        self.setup_budget_ps = self.clock_period_ps * 0.1  # 10% margin
        self.clock_skew_ps = self.clock_period_ps * 0.05   # 5% skew budget
        self.max_logic_delay_ps = (
            self.clock_period_ps - self.setup_budget_ps - self.clock_skew_ps
        )

    @property
    def max_logic_gates(self) -> float:
        """Maximum equivalent NAND2 gates in critical path."""
        return self.max_logic_delay_ps / 10.0  # rough: NAND2 ≈ 10ps at advanced nodes


@dataclass
class AreaEstimate:
    """Area estimate for a module."""
    std_cell_count: float = 0.0
    dff_count: int = 0
    comb_cell_count: float = 0.0
    total_cell_area_um2: float = 0.0
    routing_area_um2: float = 0.0
    total_area_um2: float = 0.0
    utilization: float = 0.75  # typical place-and-route utilization

    @property
    def die_area_mm2(self) -> float:
        return self.total_area_um2 / 1e6


@dataclass
class PowerEstimate:
    """Power estimate for a module."""
    dynamic_mw: float = 0.0
    leakage_mw: float = 0.0
    total_mw: float = 0.0
    activity_factor: float = 0.15  # default toggle rate


# ============================================================================
# TechNode — Process Characterization
# ============================================================================

class TechNode:
    """Characterization data for a semiconductor process node.

    Provides gate delays, cell areas, wire models, and timing budgets
    used by PPAOptimizer to estimate RTL quality before synthesis.
    """

    def __init__(self, node_name: str = "28nm",
                 custom_data: Optional[Dict[str, Any]] = None):
        self._data = _TECH_NODES.get(node_name)
        if self._data is None:
            raise ValueError(
                f"Unknown process node '{node_name}'. "
                f"Available: {sorted(_TECH_NODES.keys())}"
            )
        if custom_data:
            self._data = {**self._data, **custom_data}

    @property
    def name(self) -> str:
        return self._data["node_name"]

    @property
    def min_feature_nm(self) -> int:
        return self._data["min_feature_nm"]

    @property
    def vdd_v(self) -> float:
        return self._data["vdd_v"]

    # ----------------------------------------------------------------
    # Gate Timing
    # ----------------------------------------------------------------

    def gate_delay(self, gate_type: str) -> float:
        """Gate delay in picoseconds at typical corner."""
        return self._data["gate_delay_ps"].get(gate_type, 0.0)

    def gate_area(self, gate_type: str) -> float:
        """Standard cell area in um^2."""
        return self._data["std_cell_area_um2"].get(gate_type, 0.0)

    def dff_clk_q_delay(self) -> float:
        return self._data["gate_delay_ps"]["dff"]

    def dff_setup_time(self) -> float:
        return self._data["dff_setup_ps"]

    def dff_hold_time(self) -> float:
        return self._data["dff_hold_ps"]

    # ----------------------------------------------------------------
    # Wire Model
    # ----------------------------------------------------------------

    def wire_delay(self, length_um: float) -> float:
        return self._data["wire_delay_ps_per_um"] * length_um

    def wire_capacitance(self, length_um: float) -> float:
        return self._data["wire_cap_ff_per_um"] * length_um

    # ----------------------------------------------------------------
    # Timing Budget Analysis
    # ----------------------------------------------------------------

    def timing_budget(self, freq_ghz: float) -> TimingConstraint:
        """Compute timing budget at target frequency."""
        tc = TimingConstraint(freq_ghz)
        return tc

    def max_logic_depth(self, target_freq_ghz: float,
                        gate_type: str = "nand2") -> int:
        """Maximum number of `gate_type` stages allowed in critical path.

        Returns a conservative integer that represents the maximum
        combinational logic depth before pipelining is required.
        """
        tc = self.timing_budget(target_freq_ghz)
        gate_d = self.gate_delay(gate_type)
        if gate_d <= 0:
            return 0
        return int(tc.max_logic_delay_ps / gate_d)

    def check_critical_path(self, path_delay_ps: float,
                            freq_ghz: float) -> Tuple[bool, float]:
        """Check if a critical path meets timing at target frequency.

        Returns:
            (meets_timing, slack_ps)
        """
        tc = self.timing_budget(freq_ghz)
        slack = tc.max_logic_delay_ps - path_delay_ps
        return (slack >= 0, slack)

    # ----------------------------------------------------------------
    # Area Estimation
    # ----------------------------------------------------------------

    def estimate_area(self, cell_counts: Dict[str, int]) -> AreaEstimate:
        """Estimate area from cell count map.

        Args:
            cell_counts: {gate_type: count}

        Returns:
            AreaEstimate with total area and routing overhead
        """
        total = 0.0
        for gate, count in cell_counts.items():
            total += count * self.gate_area(gate)
        est = AreaEstimate(
            std_cell_count=sum(cell_counts.values()),
            comb_cell_count=sum(
                c for g, c in cell_counts.items() if g != "dff"
            ),
            dff_count=cell_counts.get("dff", 0),
            total_cell_area_um2=total,
        )
        overhead = self._data["routing_overhead"]
        est.routing_area_um2 = total * (overhead - 1)
        est.total_area_um2 = total * overhead
        return est

    def estimate_area_from_rtl(self, rtl_constructs: Dict[str, int],
                               bit_widths: Optional[Dict[str, int]] = None) -> AreaEstimate:
        """Estimate area from RTL construct descriptions.

        Args:
            rtl_constructs: {construct_name: count}
            bit_widths: {construct_name: bit_width} — scales area linearly

        Returns:
            AreaEstimate
        """
        widths = bit_widths or {}
        cell_counts: Dict[str, int] = {}
        for construct, count in rtl_constructs.items():
            info = RTL_TO_GATES.get(construct)
            if info is None:
                continue
            width = widths.get(construct, 1)
            cells = info["area_cells"] * width * count
            for gate in info["gates"]:
                cell_counts[gate] = cell_counts.get(gate, 0) + int(cells / len(info["gates"]))
        return self.estimate_area(cell_counts)

    # ----------------------------------------------------------------
    # Power Estimation
    # ----------------------------------------------------------------

    def estimate_power(self, cell_counts: Dict[str, int],
                       activity: float = 0.15,
                       freq_ghz: float = 1.0) -> PowerEstimate:
        """Estimate dynamic and leakage power.

        Args:
            cell_counts: {gate_type: count}
            activity: toggle rate (0.0-1.0)
            freq_ghz: clock frequency

        Returns:
            PowerEstimate
        """
        vdd = self.vdd_v
        # Dynamic power: P = alpha * C * V^2 * f
        # Approximate: each std cell has ~0.5fF capacitance
        total_cells = sum(cell_counts.values())
        avg_cap_ff = 0.5
        dynamic_mw = activity * total_cells * avg_cap_ff * 1e-15 * vdd * vdd * freq_ghz * 1e9

        # Leakage: per-cell leakage
        leakage_per_cell_nw = self._data["leakage_nw_per_cell"]
        leakage_mw = total_cells * leakage_per_cell_nw * 1e-6

        est = PowerEstimate(
            dynamic_mw=dynamic_mw,
            leakage_mw=leakage_mw,
            activity_factor=activity,
        )
        est.total_mw = dynamic_mw + leakage_mw
        return est

    # ----------------------------------------------------------------
    # Logic Depth Estimation from RTL
    # ----------------------------------------------------------------

    def estimate_logic_depth(self, rtl_constructs: List[str],
                             bit_widths: Optional[Dict[str, int]] = None) -> int:
        """Estimate combinational logic depth from RTL construct list.

        Args:
            rtl_constructs: ordered list of construct names in critical path
            bit_widths: optional width scaling

        Returns:
            Estimated equivalent NAND2 gate depth
        """
        widths = bit_widths or {}
        total_depth = 0
        for construct in rtl_constructs:
            info = RTL_TO_GATES.get(construct)
            if info is None:
                total_depth += 1
                continue
            depth = info["depth"]
            width = widths.get(construct, 1)
            # Wide operations add depth (log2 for tree structures)
            if width > 32:
                depth += 2
            elif width > 8:
                depth += 1
            total_depth += depth
        return total_depth

    # ----------------------------------------------------------------
    # Pipeline Recommendation
    # ----------------------------------------------------------------

    def recommend_pipeline(self, current_depth: int,
                           target_freq_ghz: float) -> int:
        """Recommend minimum pipeline stages for target frequency.

        Args:
            current_depth: estimated logic depth (NAND2 equivalent)
            target_freq_ghz: target clock frequency

        Returns:
            Minimum pipeline stages needed. 1 = no pipelining needed.
        """
        max_depth = self.max_logic_depth(target_freq_ghz)
        if max_depth <= 0:
            return current_depth
        stages = (current_depth + max_depth - 1) // max_depth
        return max(1, stages)

    # ----------------------------------------------------------------
    # Convenience
    # ----------------------------------------------------------------

    @classmethod
    def available_nodes(cls) -> List[str]:
        return sorted(_TECH_NODES.keys())

    @classmethod
    def node_comparison(cls) -> str:
        """Print a comparison table of all process nodes."""
        lines = [
            f"{'Node':<18} {'VDD(V)':<8} {'NAND2(ps)':<12} "
            f"{'DFF(ps)':<10} {'NAND2(um2)':<12} {'DFF(um2)':<10} "
            f"{'Wire(ps/um)':<12}",
            "-" * 90,
        ]
        for node_name in cls.available_nodes():
            node = cls(node_name)
            lines.append(
                f"{node.name:<18} {node.vdd_v:<8.2f} "
                f"{node.gate_delay('nand2'):<12.1f} "
                f"{node.gate_delay('dff'):<10.1f} "
                f"{node.gate_area('nand2'):<12.3f} "
                f"{node.gate_area('dff'):<10.3f} "
                f"{node._data['wire_delay_ps_per_um']:<12.1f}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"TechNode('{self.name}')"
