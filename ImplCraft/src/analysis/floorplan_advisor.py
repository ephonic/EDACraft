"""
Floorplan Advisor — generates placement strategy for hardened blocks.

For each hardened block, determines:
- Approximate placement region (quadrant / strip)
- Aspect ratio
- Pin placement strategy
- Macro placement order
- Block-to-block connectivity (bus routing)

Strategy:
1. Sort hardened blocks by priority
2. Place critical path blocks first (center)
3. Place macro-heavy blocks near edges
4. Place IO-heavy blocks near IO ring
5. Generate floorplan constraints
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
from .partition_engine import PartitionResult, PartitionConfig

logger = logging.getLogger("ic_backend")


@dataclass
class BlockPlacement:
    """Placement suggestion for a hardened block."""
    module_name: str
    region: str = ""            # "center", "north", "south", "east", "west"
    x_offset_pct: float = 0.0  # % from left
    y_offset_pct: float = 0.0  # % from bottom
    width_pct: float = 0.0     # % of die width
    height_pct: float = 0.0    # % of die height
    aspect_ratio: float = 1.0  # width/height
    priority: int = 0          # Placement order priority
    pin_strategy: str = "distributed"  # "distributed", "concentrated", "bus"
    notes: list[str] = field(default_factory=list)


@dataclass
class FloorplanAdvice:
    """Complete floorplan advice for a design."""
    design_name: str
    die_width_um: float = 0.0
    die_height_um: float = 0.0
    block_placements: list[BlockPlacement] = field(default_factory=list)
    macro_placement_order: list[str] = field(default_factory=list)
    io_ring_strategy: str = ""
    bus_routing: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""


class FloorplanAdvisor:
    """
    Generate floorplan advice for hardened blocks.

    Usage:
        advisor = FloorplanAdvisor()
        advice = advisor.advise(partition_result, die_width=2900, die_height=1900)
        print(advice.summary)
    """

    def advise(
        self,
        partition_result: PartitionResult,
        die_width_um: float = 2900.0,
        die_height_um: float = 1900.0,
        target_utilization: float = 0.7,
    ) -> FloorplanAdvice:
        """Generate floorplan advice based on partition result."""
        advice = FloorplanAdvice(
            design_name=partition_result.graph.design_name,
            die_width_um=die_width_um,
            die_height_um=die_height_um,
        )

        if not partition_result.hardened_blocks:
            advice.summary = "No hardened blocks to place."
            return advice

        # Sort blocks by priority
        sorted_blocks = sorted(
            partition_result.hardened_blocks,
            key=lambda n: n.harden_priority,
            reverse=True
        )

        # Calculate total area needed
        total_area = sum(b.total_area() for b in sorted_blocks)
        core_area = die_width_um * die_height_um * target_utilization

        # Assign regions
        self._assign_regions(sorted_blocks, advice, core_area)

        # Determine macro placement order
        self._determine_macro_order(sorted_blocks, advice)

        # Generate bus routing suggestions
        self._suggest_bus_routing(sorted_blocks, advice)

        # Generate summary
        advice.summary = self._generate_summary(advice)

        return advice

    def _assign_regions(
        self,
        blocks: list[ModuleNode],
        advice: FloorplanAdvice,
        core_area: float,
    ):
        """Assign placement regions to blocks."""
        if not blocks:
            return

        # Calculate ideal block sizes
        total_gates = sum(b.total_gate_count() for b in blocks)
        if total_gates == 0:
            total_gates = 1

        # Available regions (simplified grid)
        regions = [
            ("center", 0.25, 0.25, 0.5, 0.5),    # center
            ("north", 0.0, 0.6, 1.0, 0.4),        # top strip
            ("south", 0.0, 0.0, 1.0, 0.4),        # bottom strip
            ("east", 0.6, 0.0, 0.4, 1.0),         # right strip
            ("west", 0.0, 0.0, 0.4, 1.0),         # left strip
        ]

        region_idx = 0
        for block in blocks:
            if region_idx >= len(regions):
                region_idx = 0  # Wrap around

            region_name, x_off, y_off, w_pct, h_pct = regions[region_idx]

            # Adjust size based on gate count
            gate_ratio = block.total_gate_count() / total_gates
            scale = gate_ratio * len(blocks)  # Scale factor

            placement = BlockPlacement(
                module_name=block.name,
                region=region_name,
                x_offset_pct=x_off * 100,
                y_offset_pct=y_off * 100,
                width_pct=w_pct * scale * 100,
                height_pct=h_pct * scale * 100,
                aspect_ratio=block.metrics.area_um2 ** 0.5 / 100 if block.metrics.area_um2 > 0 else 1.0,
                priority=block.harden_priority,
            )

            # Timing critical blocks go to center
            if block.metrics.timing_criticality == TimingCriticality.CRITICAL:
                placement.region = "center"
                placement.x_offset_pct = 30
                placement.y_offset_pct = 30
                placement.notes.append("Critical path - placed in center")

            # Macro-heavy blocks go to edges
            if block.metrics.num_macros > 5:
                if region_name == "center":
                    placement.region = "east"
                    placement.x_offset_pct = 60
                    placement.notes.append("Macro-heavy - moved to edge")

            # IO-heavy blocks (many ports) go to periphery
            if block.metrics.num_ports > 100:
                placement.pin_strategy = "distributed"
                placement.notes.append("High port count - distributed pins")
            elif block.metrics.num_ports < 20:
                placement.pin_strategy = "concentrated"
                placement.notes.append("Low port count - concentrated pins")

            advice.block_placements.append(placement)
            region_idx += 1

    def _determine_macro_order(
        self, blocks: list[ModuleNode], advice: FloorplanAdvice
    ):
        """Determine macro placement order."""
        # Place largest macros first
        macro_blocks = [
            b for b in blocks if b.metrics.num_macros > 0
        ]
        sorted_macros = sorted(
            macro_blocks,
            key=lambda b: b.metrics.num_macros,
            reverse=True
        )
        advice.macro_placement_order = [b.name for b in sorted_macros]

    def _suggest_bus_routing(
        self, blocks: list[ModuleNode], advice: FloorplanAdvice
    ):
        """Suggest bus routing between blocks."""
        # Find blocks with high cross-module signals
        high_connectivity = [
            b for b in blocks if b.cross_module_signals > 200
        ]

        if len(high_connectivity) >= 2:
            # Suggest bus between top 2 connected blocks
            advice.bus_routing.append(
                f"High-speed bus between {high_connectivity[0].name} "
                f"and {high_connectivity[1].name} "
                f"({high_connectivity[0].cross_module_signals} signals)"
            )

    def _generate_summary(self, advice: FloorplanAdvice) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Floorplan Advice: {advice.design_name}",
            f"Die: {advice.die_width_um:.0f} x {advice.die_height_um:.0f} um",
            "",
        ]

        if advice.block_placements:
            lines.append(f"Block Placements ({len(advice.block_placements)}):")
            for bp in sorted(advice.block_placements, key=lambda b: b.priority, reverse=True):
                lines.append(
                    f"  [{bp.priority:2d}] {bp.module_name:30s} "
                    f"region={bp.region:8s} "
                    f"pos=({bp.x_offset_pct:5.1f}%, {bp.y_offset_pct:5.1f}%) "
                    f"size=({bp.width_pct:5.1f}% x {bp.height_pct:5.1f}%)"
                )
                for note in bp.notes[:2]:
                    lines.append(f"       → {note}")
            lines.append("")

        if advice.macro_placement_order:
            lines.append("Macro Placement Order:")
            for i, name in enumerate(advice.macro_placement_order, 1):
                lines.append(f"  {i}. {name}")
            lines.append("")

        if advice.bus_routing:
            lines.append("Bus Routing:")
            for bus in advice.bus_routing:
                lines.append(f"  • {bus}")
            lines.append("")

        if advice.recommendations:
            lines.append("Recommendations:")
            for i, rec in enumerate(advice.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)

    def generate_floorplan_script(
        self, advice: FloorplanAdvice, output_path: str | Path
    ):
        """Generate ICC2 floorplan constraints script."""
        lines = [
            "# Floorplan Constraints Script",
            f"# Design: {advice.design_name}",
            "",
            f"initialize_floorplan \\",
            f"    -control_type die -shape R \\",
            f"    -boundary {{{{0 0}} {{{advice.die_width_um} {advice.die_height_um}}}}}",
            "",
        ]

        # Block placement regions
        if advice.block_placements:
            lines.append("# Block placement regions")
            for bp in advice.block_placements:
                x1 = bp.x_offset_pct / 100 * advice.die_width_um
                y1 = bp.y_offset_pct / 100 * advice.die_height_um
                x2 = x1 + bp.width_pct / 100 * advice.die_width_um
                y2 = y1 + bp.height_pct / 100 * advice.die_height_um

                lines.append(
                    f"create_placement_blockage -coordinate "
                    f"{{{{{x1:.0f} {y1:.0f}}} {{{x2:.0f} {y2:.0f}}}}} "
                    f"-name {bp.module_name}_region -type hard"
                )
            lines.append("")

        # Macro placement order
        if advice.macro_placement_order:
            lines.append("# Macro placement constraints")
            for i, name in enumerate(advice.macro_placement_order):
                lines.append(f"# Place {name} first (priority {i+1})")
            lines.append("")

        Path(output_path).write_text("\n".join(lines))
