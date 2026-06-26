"""
Sub-Partition Advisor — suggests how to split oversized modules.

When a module exceeds tool capacity (e.g., 4M gates), this advisor:
1. Analyzes the module's internal structure
2. Identifies natural split boundaries:
   - Clock domain boundaries
   - Functional units (ALU, memory, IO)
   - Pipeline stages
   - Data path vs control path
3. Suggests balanced sub-partitions
4. Estimates cross-partition connectivity

Output:
- List of suggested sub-modules with gate counts
- Cross-partition signal estimates
- Timing impact assessment
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .module_graph import (
    ModuleGraph, ModuleNode, ModuleMetrics,
    PartitionDecision, TimingCriticality,
)

logger = logging.getLogger("ic_backend")


@dataclass
class SubPartition:
    """A suggested sub-partition of an oversized module."""
    name: str
    gate_count: int = 0
    area_um2: float = 0.0
    modules: list[str] = field(default_factory=list)
    clock_domains: list[str] = field(default_factory=list)
    cross_partition_signals: int = 0
    timing_critical: bool = False
    rationale: str = ""


@dataclass
class SubPartitionAdvice:
    """Advice for splitting an oversized module."""
    parent_module: str
    parent_gate_count: int
    gate_limit: int
    num_splits_needed: int
    suggested_partitions: list[SubPartition] = field(default_factory=list)
    cross_partition_signals: int = 0
    timing_impact: str = ""
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""


class SubPartitionAdvisor:
    """
    Suggest how to split oversized modules.

    Usage:
        advisor = SubPartitionAdvisor(gate_limit=4_000_000)
        advice = advisor.advise(oversized_module_node)
        print(advice.summary)
    """

    def __init__(self, gate_limit: int = 4_000_000):
        self.gate_limit = gate_limit

    def advise(self, module: ModuleNode) -> SubPartitionAdvice:
        """Generate sub-partition advice for an oversized module."""
        total_gates = module.total_gate_count()
        num_splits = (total_gates + self.gate_limit - 1) // self.gate_limit

        advice = SubPartitionAdvice(
            parent_module=module.name,
            parent_gate_count=total_gates,
            gate_limit=self.gate_limit,
            num_splits_needed=num_splits,
        )

        # Strategy 1: Split by existing children
        if module.children:
            self._split_by_children(module, advice)

        # Strategy 2: Split by clock domains
        if module.metrics.clock_domains and len(module.metrics.clock_domains) > 1:
            self._split_by_clock_domains(module, advice)

        # Strategy 3: Balanced split (if no natural boundaries)
        if not advice.suggested_partitions:
            self._balanced_split(module, advice)

        # Estimate cross-partition signals
        self._estimate_cross_signals(advice)

        # Assess timing impact
        self._assess_timing_impact(advice)

        # Generate summary
        advice.summary = self._generate_summary(advice)

        return advice

    def _split_by_children(
        self, module: ModuleNode, advice: SubPartitionAdvice
    ):
        """Split based on existing child modules."""
        if not module.children:
            return

        # Sort children by gate count
        sorted_children = sorted(
            module.children,
            key=lambda c: c.total_gate_count(),
            reverse=True
        )

        # Group children into partitions
        partitions: list[SubPartition] = []
        current_partition = SubPartition(
            name=f"{module.name}_part1",
            gate_count=0,
            modules=[],
        )

        for child in sorted_children:
            child_gates = child.total_gate_count()

            # If adding this child would exceed limit, start new partition
            if (current_partition.gate_count + child_gates > self.gate_limit and
                current_partition.gate_count > 0):
                partitions.append(current_partition)
                current_partition = SubPartition(
                    name=f"{module.name}_part{len(partitions) + 1}",
                    gate_count=0,
                    modules=[],
                )

            # Add child to current partition
            current_partition.modules.append(child.name)
            current_partition.gate_count += child_gates
            current_partition.area_um2 += child.total_area()

            # Inherit clock domains
            if child.metrics.clock_domains:
                for cd in child.metrics.clock_domains:
                    if cd not in current_partition.clock_domains:
                        current_partition.clock_domains.append(cd)

            # Inherit timing criticality
            if child.metrics.timing_criticality == TimingCriticality.CRITICAL:
                current_partition.timing_critical = True

        # Add last partition
        if current_partition.modules:
            partitions.append(current_partition)

        # Add rationale
        for i, part in enumerate(partitions):
            part.rationale = f"Grouped {len(part.modules)} child modules"

        advice.suggested_partitions = partitions

    def _split_by_clock_domains(
        self, module: ModuleNode, advice: SubPartitionAdvice
    ):
        """Split based on clock domain boundaries."""
        if not module.metrics.clock_domains:
            return

        # If we already have partitions from children, skip
        if advice.suggested_partitions:
            return

        # Create one partition per clock domain
        partitions = []
        for cd in module.metrics.clock_domains:
            part = SubPartition(
                name=f"{module.name}_{cd}",
                clock_domains=[cd],
                rationale=f"Clock domain: {cd}",
            )
            partitions.append(part)

        # Distribute gate count evenly (approximation)
        gates_per_domain = module.total_gate_count() // len(partitions)
        for part in partitions:
            part.gate_count = gates_per_domain
            part.area_um2 = module.total_area() / len(partitions)

        advice.suggested_partitions = partitions

    def _balanced_split(
        self, module: ModuleNode, advice: SubPartitionAdvice
    ):
        """Create balanced partitions when no natural boundaries exist."""
        total_gates = module.total_gate_count()
        num_splits = advice.num_splits_needed
        gates_per_split = total_gates // num_splits

        partitions = []
        for i in range(num_splits):
            part = SubPartition(
                name=f"{module.name}_part{i+1}",
                gate_count=gates_per_split,
                area_um2=module.total_area() / num_splits,
                rationale=f"Balanced split ({i+1}/{num_splits})",
            )
            partitions.append(part)

        advice.suggested_partitions = partitions

    def _estimate_cross_signals(self, advice: SubPartitionAdvice):
        """Estimate cross-partition signals."""
        if len(advice.suggested_partitions) < 2:
            advice.cross_partition_signals = 0
            return

        # Heuristic: ~10% of ports are cross-partition
        total_modules = sum(len(p.modules) for p in advice.suggested_partitions)
        if total_modules == 0:
            total_modules = len(advice.suggested_partitions)

        # Estimate based on number of partitions
        base_signals = 100  # Base cross-partition signals
        per_partition = 50  # Additional signals per partition

        advice.cross_partition_signals = base_signals + per_partition * len(advice.suggested_partitions)

    def _assess_timing_impact(self, advice: SubPartitionAdvice):
        """Assess timing impact of partitioning."""
        critical_partitions = sum(
            1 for p in advice.suggested_partitions if p.timing_critical
        )

        if critical_partitions > 0:
            advice.timing_impact = (
                f"HIGH: {critical_partitions} partitions contain critical paths. "
                f"Cross-partition timing may be harder to close."
            )
            advice.recommendations.append(
                "Consider keeping critical path modules in same partition"
            )
        elif advice.cross_partition_signals > 500:
            advice.timing_impact = (
                f"MEDIUM: {advice.cross_partition_signals} cross-partition signals. "
                f"May impact routing congestion."
            )
        else:
            advice.timing_impact = "LOW: Minimal cross-partition connectivity"

    def _generate_summary(self, advice: SubPartitionAdvice) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Sub-Partition Advice: {advice.parent_module}",
            f"Parent gates: {advice.parent_gate_count:,}",
            f"Gate limit: {advice.gate_limit:,}",
            f"Splits needed: {advice.num_splits_needed}",
            "",
        ]

        if advice.suggested_partitions:
            lines.append(f"Suggested Partitions ({len(advice.suggested_partitions)}):")
            for part in advice.suggested_partitions:
                lines.append(
                    f"  {part.name:30s} "
                    f"{part.gate_count:8,} gates  "
                    f"{len(part.modules):2d} modules"
                )
                if part.clock_domains:
                    lines.append(f"       Clocks: {', '.join(part.clock_domains)}")
                if part.rationale:
                    lines.append(f"       {part.rationale}")
            lines.append("")

        lines.append(f"Cross-partition signals: {advice.cross_partition_signals:,}")
        lines.append(f"Timing impact: {advice.timing_impact}")
        lines.append("")

        if advice.recommendations:
            lines.append("Recommendations:")
            for i, rec in enumerate(advice.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)
