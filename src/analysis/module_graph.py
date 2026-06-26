"""
Module Graph — hierarchical representation of design modules.

Each node represents a module (or instance) in the design hierarchy.
Stores:
- Gate count (from DC area report)
- Area (um^2)
- Timing criticality (from timing reports)
- Connectivity (port count, cross-module signals)
- Partition decision (harden / flatten / split)

This is the central data structure for partition analysis.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Iterator


class PartitionDecision(Enum):
    HARDEN = "harden"       # Synthesize and P&R as a separate block
    FLATTEN = "flatten"     # Flatten into parent
    SPLIT = "split"         # Needs further sub-partitioning
    KEEP = "keep"           # Keep as-is (already sized correctly)
    MACRO = "macro"         # Treat as hard macro


class TimingCriticality(Enum):
    CRITICAL = "critical"   # On critical path
    MODERATE = "moderate"   # Some timing margin
    RELAXED = "relaxed"     # Plenty of margin


@dataclass
class ModuleMetrics:
    """Metrics for a single module."""
    gate_count: int = 0           # Equivalent gate count
    area_um2: float = 0.0         # Cell area in um^2
    num_ports: int = 0            # Number of module ports
    num_nets: int = 0             # Internal net count
    num_seq_cells: int = 0        # Sequential cell count
    num_comb_cells: int = 0       # Combinational cell count
    num_macros: int = 0           # Hard macro count
    wns_ns: float | None = None   # Worst negative slack
    tns_ns: float | None = None   # Total negative slack
    timing_criticality: TimingCriticality = TimingCriticality.MODERATE
    clock_domains: list[str] = field(default_factory=list)


@dataclass
class ModuleNode:
    """A node in the module hierarchy tree."""
    name: str
    instance_path: str = ""
    metrics: ModuleMetrics = field(default_factory=ModuleMetrics)
    children: list[ModuleNode] = field(default_factory=list)
    parent: ModuleNode | None = field(default=None, repr=False)
    decision: PartitionDecision = PartitionDecision.KEEP
    split_suggestions: list[str] = field(default_factory=list)
    harden_priority: int = 0      # Higher = should harden first
    notes: list[str] = field(default_factory=list)

    # Cross-module connectivity
    cross_module_signals: int = 0  # Number of signals crossing to siblings
    fanout_to_siblings: int = 0    # Number of fanout connections to siblings

    def add_child(self, child: ModuleNode):
        child.parent = self
        self.children.append(child)

    def total_gate_count(self) -> int:
        """Sum gate count of self and all descendants."""
        total = self.metrics.gate_count
        for child in self.children:
            total += child.total_gate_count()
        return total

    def total_area(self) -> float:
        """Sum area of self and all descendants."""
        total = self.metrics.area_um2
        for child in self.children:
            total += child.total_area()
        return total

    def depth(self) -> int:
        """Depth of this node in the tree."""
        d = 0
        node = self.parent
        while node is not None:
            d += 1
            node = node.parent
        return d

    def walk(self) -> Iterator[ModuleNode]:
        """Iterate over all nodes in the tree (DFS)."""
        yield self
        for child in self.children:
            yield from child.walk()

    def leaf_modules(self) -> list[ModuleNode]:
        """Get all leaf modules (no children)."""
        return [n for n in self.walk() if not n.children]

    def find(self, name: str) -> ModuleNode | None:
        """Find a module by name."""
        for node in self.walk():
            if node.name == name:
                return node
        return None

    def is_oversized(self, gate_limit: int = 4_000_000) -> bool:
        """Check if this module exceeds tool capacity."""
        return self.total_gate_count() > gate_limit

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON output."""
        return {
            "name": self.name,
            "instance_path": self.instance_path,
            "gate_count": self.metrics.gate_count,
            "total_gate_count": self.total_gate_count(),
            "area_um2": round(self.metrics.area_um2, 2),
            "total_area_um2": round(self.total_area(), 2),
            "num_ports": self.metrics.num_ports,
            "num_nets": self.metrics.num_nets,
            "num_seq_cells": self.metrics.num_seq_cells,
            "num_comb_cells": self.metrics.num_comb_cells,
            "num_macros": self.metrics.num_macros,
            "wns_ns": self.metrics.wns_ns,
            "timing_criticality": self.metrics.timing_criticality.value,
            "decision": self.decision.value,
            "harden_priority": self.harden_priority,
            "cross_module_signals": self.cross_module_signals,
            "split_suggestions": self.split_suggestions,
            "notes": self.notes,
            "children": [c.to_dict() for c in self.children],
        }


class ModuleGraph:
    """
    Complete module hierarchy graph for a design.

    Usage:
        graph = ModuleGraph(design_name="top")
        graph.root = root_node
        print(graph.summary())
    """

    def __init__(self, design_name: str = "top"):
        self.design_name = design_name
        self.root: ModuleNode | None = None
        self.gate_limit: int = 4_000_000  # Default tool capacity
        self.area_limit_um2: float = 0.0  # 0 = no limit

    def total_gate_count(self) -> int:
        if self.root is None:
            return 0
        return self.root.total_gate_count()

    def total_area(self) -> float:
        if self.root is None:
            return 0.0
        return self.root.total_area()

    def needs_partition(self) -> bool:
        """Check if the design exceeds tool capacity."""
        if self.root is None:
            return False
        if self.total_gate_count() > self.gate_limit:
            return True
        if self.area_limit_um2 > 0 and self.total_area() > self.area_limit_um2:
            return True
        return False

    def oversized_modules(self) -> list[ModuleNode]:
        """Find all modules that exceed gate limit."""
        if self.root is None:
            return []
        return [n for n in self.root.walk() if n.is_oversized(self.gate_limit)]

    def summary(self) -> str:
        """Generate a text summary of the module graph."""
        if self.root is None:
            return "No module hierarchy loaded."

        lines = [
            f"Module Hierarchy: {self.design_name}",
            f"Total gates: {self.total_gate_count():,}",
            f"Total area: {self.total_area():,.0f} um^2",
            f"Gate limit: {self.gate_limit:,}",
            f"Needs partition: {self.needs_partition()}",
            "",
            "Hierarchy:",
        ]

        for node in self.root.walk():
            indent = "  " * node.depth()
            decision_tag = f" [{node.decision.value}]" if node.decision != PartitionDecision.KEEP else ""
            lines.append(
                f"{indent}{node.name}: {node.metrics.gate_count:,} gates "
                f"({node.metrics.area_um2:,.0f} um^2){decision_tag}"
            )

        return "\n".join(lines)

    def save(self, path: str | Path):
        """Save module graph to JSON."""
        if self.root is None:
            return
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "design_name": self.design_name,
            "gate_limit": self.gate_limit,
            "total_gates": self.total_gate_count(),
            "total_area": self.total_area(),
            "needs_partition": self.needs_partition(),
            "hierarchy": self.root.to_dict(),
        }
        path.write_text(json.dumps(data, indent=2))

    def print_tree(self):
        """Print module tree to stdout."""
        print(self.summary())
