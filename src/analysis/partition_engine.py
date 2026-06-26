"""
Partition Engine — makes harden/flatten/split decisions for design modules.

Decision criteria:
1. Gate count vs tool capacity (primary)
2. Timing criticality (critical paths should stay flat for global optimization)
3. Connectivity (low cross-module signals = good harden candidate)
4. Module balance (even distribution of gates across blocks)

Algorithm:
1. Walk hierarchy bottom-up
2. For each module, check if it exceeds gate limit
3. If yes, try to split into sub-modules
4. If module is small enough, decide harden vs flatten based on:
   - Timing criticality (critical → flatten for global opt)
   - Cross-module signals (low → harden for parallel P&R)
   - Macro content (has macros → harden)
5. Generate partition report with recommendations
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .module_graph import (
    ModuleGraph, ModuleNode, ModuleMetrics,
    PartitionDecision, TimingCriticality,
)

logger = logging.getLogger("ic_backend")


@dataclass
class PartitionConfig:
    """Configuration for partition decisions."""
    gate_limit: int = 4_000_000          # Max gates per block
    min_harden_gates: int = 100_000      # Min gates to justify hardening
    critical_path_flatten: bool = True   # Flatten critical path modules
    max_cross_signals: int = 500         # Max cross-module signals for hardening
    prefer_harden_macros: bool = True    # Harden modules with hard macros
    balance_threshold: float = 0.3       # Max gate imbalance between blocks (30%)


@dataclass
class PartitionResult:
    """Result of partition analysis."""
    graph: ModuleGraph
    decisions: list[PartitionDecision] = field(default_factory=list)
    hardened_blocks: list[ModuleNode] = field(default_factory=list)
    split_modules: list[ModuleNode] = field(default_factory=list)
    flattened_modules: list[ModuleNode] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""


class PartitionEngine:
    """
    Make partition decisions for design hierarchy.

    Usage:
        engine = PartitionEngine(config)
        result = engine.partition(graph)
        print(result.summary)
    """

    def __init__(self, config: PartitionConfig | None = None):
        self.config = config or PartitionConfig()

    def partition(self, graph: ModuleGraph) -> PartitionResult:
        """
        Analyze module graph and make partition decisions.

        Returns PartitionResult with decisions for each module.
        """
        result = PartitionResult(graph=graph)

        if graph.root is None:
            result.summary = "No module hierarchy to partition."
            return result

        # Walk bottom-up (leaves first)
        self._partition_recursive(graph.root, result)

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def _partition_recursive(
        self, node: ModuleNode, result: PartitionResult
    ):
        """Recursively partition module tree (bottom-up)."""
        # First, partition children
        for child in node.children:
            self._partition_recursive(child, result)

        # Now decide for this node
        total_gates = node.total_gate_count()

        # Check if oversized
        if total_gates > self.config.gate_limit:
            # Needs splitting
            node.decision = PartitionDecision.SPLIT
            node.split_suggestions = self._suggest_splits(node)
            result.split_modules.append(node)
            logger.warning(
                f"Module {node.name} needs splitting: "
                f"{total_gates:,} gates > {self.config.gate_limit:,} limit"
            )
            return

        # Check if should harden
        if self._should_harden(node):
            node.decision = PartitionDecision.HARDEN
            node.harden_priority = self._compute_harden_priority(node)
            result.hardened_blocks.append(node)
            logger.info(
                f"Module {node.name} → HARDEN: "
                f"{total_gates:,} gates, priority={node.harden_priority}"
            )
            return

        # Check if should flatten
        if self._should_flatten(node):
            node.decision = PartitionDecision.FLATTEN
            result.flattened_modules.append(node)
            logger.info(f"Module {node.name} → FLATTEN (timing critical)")
            return

        # Default: keep as-is
        node.decision = PartitionDecision.KEEP

    def _should_harden(self, node: ModuleNode) -> bool:
        """Determine if a module should be hardened."""
        total_gates = node.total_gate_count()

        # Too small to justify hardening overhead
        if total_gates < self.config.min_harden_gates:
            return False

        # Critical path modules should stay flat for global optimization
        if (self.config.critical_path_flatten and
            node.metrics.timing_criticality == TimingCriticality.CRITICAL):
            return False

        # Modules with hard macros should be hardened
        if (self.config.prefer_harden_macros and
            node.metrics.num_macros > 0):
            return True

        # Low cross-module connectivity = good harden candidate
        if node.cross_module_signals < self.config.max_cross_signals:
            return True

        return False

    def _should_flatten(self, node: ModuleNode) -> bool:
        """Determine if a module should be flattened."""
        # Critical path modules should be flattened
        if (self.config.critical_path_flatten and
            node.metrics.timing_criticality == TimingCriticality.CRITICAL):
            return True

        # Very small modules (< 10k gates) should be flattened
        if node.total_gate_count() < 10_000:
            return True

        return False

    def _compute_harden_priority(self, node: ModuleNode) -> int:
        """Compute hardening priority (higher = harden first)."""
        priority = 0

        # Larger modules get higher priority
        priority += node.total_gate_count() // 100_000

        # Modules with macros get priority boost
        priority += node.metrics.num_macros * 10

        # Low connectivity gets priority boost
        if node.cross_module_signals < 100:
            priority += 5
        elif node.cross_module_signals < 300:
            priority += 2

        # Non-critical modules get priority (can be hardened in parallel)
        if node.metrics.timing_criticality != TimingCriticality.CRITICAL:
            priority += 3

        return priority

    def _suggest_splits(self, node: ModuleNode) -> list[str]:
        """Suggest how to split an oversized module."""
        suggestions = []
        total_gates = node.total_gate_count()
        num_splits = (total_gates + self.config.gate_limit - 1) // self.config.gate_limit

        suggestions.append(
            f"Split into ~{num_splits} sub-modules "
            f"(each < {self.config.gate_limit:,} gates)"
        )

        # Analyze children for natural split points
        if node.children:
            # Sort children by gate count
            sorted_children = sorted(
                node.children,
                key=lambda c: c.total_gate_count(),
                reverse=True
            )

            # Check if any child is close to gate limit
            for child in sorted_children:
                child_gates = child.total_gate_count()
                if child_gates > self.config.gate_limit * 0.8:
                    suggestions.append(
                        f"Child '{child.name}' ({child_gates:,} gates) "
                        f"is close to limit - consider further splitting"
                    )

            # Suggest grouping small children
            small_children = [
                c for c in sorted_children
                if c.total_gate_count() < self.config.gate_limit * 0.3
            ]
            if len(small_children) >= 3:
                suggestions.append(
                    f"Group {len(small_children)} small modules into "
                    f"{len(small_children) // 2} balanced blocks"
                )

        # Check for natural boundaries
        if node.metrics.clock_domains and len(node.metrics.clock_domains) > 1:
            suggestions.append(
                f"Split by clock domain: {', '.join(node.metrics.clock_domains)}"
            )

        return suggestions

    def _generate_summary(self, result: PartitionResult) -> str:
        """Generate human-readable partition summary."""
        lines = [
            f"Partition Analysis: {result.graph.design_name}",
            f"Total gates: {result.graph.total_gate_count():,}",
            f"Gate limit: {self.config.gate_limit:,}",
            "",
        ]

        if result.hardened_blocks:
            lines.append(f"Hardened Blocks ({len(result.hardened_blocks)}):")
            sorted_blocks = sorted(
                result.hardened_blocks,
                key=lambda n: n.harden_priority,
                reverse=True
            )
            for node in sorted_blocks[:10]:  # Top 10
                lines.append(
                    f"  [{node.harden_priority:2d}] {node.name}: "
                    f"{node.total_gate_count():,} gates"
                )
            lines.append("")

        if result.split_modules:
            lines.append(f"Modules Needing Split ({len(result.split_modules)}):")
            for node in result.split_modules:
                lines.append(f"  {node.name}: {node.total_gate_count():,} gates")
                for sug in node.split_suggestions[:3]:
                    lines.append(f"    → {sug}")
            lines.append("")

        if result.flattened_modules:
            lines.append(f"Flattened Modules ({len(result.flattened_modules)}):")
            for node in result.flattened_modules[:5]:
                lines.append(
                    f"  {node.name}: {node.total_gate_count():,} gates "
                    f"({node.metrics.timing_criticality.value})"
                )
            if len(result.flattened_modules) > 5:
                lines.append(f"  ... and {len(result.flattened_modules) - 5} more")
            lines.append("")

        if result.recommendations:
            lines.append("Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)

    def generate_partition_script(
        self, result: PartitionResult, output_path: str | Path
    ):
        """Generate Tcl script for DC hierarchical synthesis."""
        if result.graph.root is None:
            return

        lines = [
            "# Hierarchical Synthesis Script",
            f"# Design: {result.graph.design_name}",
            f"# Generated by Partition Engine",
            "",
        ]

        # Set compile directives for hardened blocks
        if result.hardened_blocks:
            lines.append("# Hardened blocks - compile separately")
            for node in result.hardened_blocks:
                lines.append(f"# {node.name}: {node.total_gate_count():,} gates")
                lines.append(
                    f"compile_ultra -from_design {node.instance_path}"
                )
                lines.append(
                    f"write -format verilog -hierarchy "
                    f"-output {node.name}_syn.v"
                )
                lines.append("")

        # Flatten directives
        if result.flattened_modules:
            lines.append("# Flattened blocks - ungroup")
            for node in result.flattened_modules:
                lines.append(f"ungroup {node.instance_path} -flatten")
            lines.append("")

        lines.append("# Compile top level")
        lines.append("compile_ultra")
        lines.append("")

        Path(output_path).write_text("\n".join(lines))
