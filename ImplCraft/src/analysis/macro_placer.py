"""
MacroPlacer — dual-mode macro placement engine.

Two placement modes:
1. Block-level: Place macros on periphery, reserve center for std cells
2. Top-level: Arrange blocks by signal flow, reserve routing channels

Usage:
    placer = MacroPlacer(mode="block")
    placements = placer.place(context, floorplan)
    
    placer = MacroPlacer(mode="top")
    placements = placer.place(context, floorplan)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .design_context import DesignContext, ModuleAnalysis, ModuleRole

logger = logging.getLogger("ic_backend")


class PlacementMode(Enum):
    BLOCK = "block"  # Block-level: macros on periphery
    TOP = "top"      # Top-level: arrange by signal flow


@dataclass
class Macro:
    """Macro specification."""
    name: str
    width_um: float
    height_um: float
    role: ModuleRole = ModuleRole.UNKNOWN
    module_name: str = ""  # Associated module name
    
    @property
    def area_um2(self) -> float:
        return self.width_um * self.height_um


@dataclass
class MacroPlacement:
    """Placed macro."""
    macro: Macro
    x_um: float
    y_um: float
    rotation: str = "R0"  # R0, R90, R180, R270, MX, MY
    
    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Bounding box (x1, y1, x2, y2)."""
        return (
            self.x_um,
            self.y_um,
            self.x_um + self.macro.width_um,
            self.y_um + self.macro.height_um,
        )


@dataclass
class PlacementResult:
    """Placement result."""
    placements: list[MacroPlacement] = field(default_factory=list)
    routing_channels: list[dict[str, Any]] = field(default_factory=list)
    std_cell_area: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            "Macro Placement Summary:",
            f"  Placed macros: {len(self.placements)}",
            f"  Routing channels: {len(self.routing_channels)}",
            f"  Warnings: {len(self.warnings)}",
            "",
        ]
        
        for placement in self.placements:
            lines.append(
                f"  {placement.macro.name}: ({placement.x_um:.0f}, {placement.y_um:.0f}) "
                f"{placement.macro.width_um:.0f}x{placement.macro.height_um:.0f}um "
                f"{placement.rotation}"
            )
        
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
        
        return "\n".join(lines)


class MacroPlacer:
    """
    Dual-mode macro placement engine.
    
    Block-level mode:
    - Place macros on periphery (top/bottom/left/right)
    - Group similar macros together
    - Reserve center for standard cells
    - Add routing channels between groups
    
    Top-level mode:
    - Arrange blocks by signal flow
    - Reserve routing channels between blocks
    - Reserve space for top-level standard cells
    """
    
    def __init__(self, mode: str | PlacementMode = PlacementMode.BLOCK):
        if isinstance(mode, str):
            mode = PlacementMode(mode)
        self.mode = mode
        
        # Placement parameters
        self.macro_spacing_um = 10.0  # Spacing between macros
        self.channel_width_um = 20.0  # Routing channel width
        self.periphery_margin_um = 50.0  # Margin from die edge
        self.std_cell_reserve_ratio = 0.6  # Reserve 60% for std cells in block mode
    
    def place(
        self,
        context: DesignContext,
        floorplan: dict[str, Any],
        macros: list[Macro] | None = None,
    ) -> PlacementResult:
        """
        Place macros based on mode.
        
        Args:
            context: Design analysis context
            floorplan: Floorplan specification (die_area, core_area, etc.)
            macros: Optional list of macros (extracted from context if not provided)
            
        Returns:
            PlacementResult with placements
        """
        # Extract macros from context if not provided
        if macros is None:
            macros = self._extract_macros(context)
        
        if self.mode == PlacementMode.BLOCK:
            return self._place_block_level(context, floorplan, macros)
        else:
            return self._place_top_level(context, floorplan, macros)
    
    def _extract_macros(self, context: DesignContext) -> list[Macro]:
        """Extract macros from design context."""
        macros = []
        
        for macro_data in context.macros:
            module = context.get_module(macro_data["name"])
            if not module:
                continue
            
            # Estimate dimensions from area (assume square for now)
            area = macro_data.get("area_um2", 10000)
            side = area ** 0.5
            
            macro = Macro(
                name=macro_data["name"],
                width_um=side,
                height_um=side,
                role=module.role,
                module_name=macro_data["name"],
            )
            macros.append(macro)
        
        return macros
    
    def _place_block_level(
        self,
        context: DesignContext,
        floorplan: dict[str, Any],
        macros: list[Macro],
    ) -> PlacementResult:
        """
        Block-level placement:
        - Group macros by role
        - Place groups on periphery
        - Reserve center for std cells
        """
        result = PlacementResult()
        
        if not macros:
            return result
        
        # Get floorplan dimensions
        core_area = floorplan.get("core_area", (0, 0, 1000, 1000))
        x1, y1, x2, y2 = core_area
        core_width = x2 - x1
        core_height = y2 - y1
        
        # Group macros by role
        groups = self._group_macros_by_role(macros)
        
        # Reserve center area for std cells
        reserve_width = core_width * self.std_cell_reserve_ratio
        reserve_height = core_height * self.std_cell_reserve_ratio
        reserve_x1 = x1 + (core_width - reserve_width) / 2
        reserve_y1 = y1 + (core_height - reserve_height) / 2
        reserve_x2 = reserve_x1 + reserve_width
        reserve_y2 = reserve_y1 + reserve_height
        
        # Place groups on periphery
        current_x = x1 + self.periphery_margin_um
        current_y = y1 + self.periphery_margin_um
        
        # Top edge: IO and Clock macros
        top_groups = [groups.get(ModuleRole.IO, []), groups.get(ModuleRole.CLOCK, [])]
        current_x = self._place_group_on_edge(
            top_groups, result, "top",
            x1 + self.periphery_margin_um, y1 + self.periphery_margin_um,
            x2 - self.periphery_margin_um, y1 + self.periphery_margin_um + 200,
            "horizontal"
        )
        
        # Bottom edge: Power macros
        bottom_groups = [groups.get(ModuleRole.POWER, [])]
        current_x = self._place_group_on_edge(
            bottom_groups, result, "bottom",
            x1 + self.periphery_margin_um, y2 - self.periphery_margin_um - 200,
            x2 - self.periphery_margin_um, y2 - self.periphery_margin_um,
            "horizontal"
        )
        
        # Left edge: Memory macros
        left_groups = [groups.get(ModuleRole.MEMORY, [])]
        current_y = self._place_group_on_edge(
            left_groups, result, "left",
            x1 + self.periphery_margin_um, reserve_y1,
            x1 + self.periphery_margin_um + 200, reserve_y2,
            "vertical"
        )
        
        # Right edge: Datapath macros
        right_groups = [groups.get(ModuleRole.DATAPATH, [])]
        current_y = self._place_group_on_edge(
            right_groups, result, "right",
            x2 - self.periphery_margin_um - 200, reserve_y1,
            x2 - self.periphery_margin_um, reserve_y2,
            "vertical"
        )
        
        # Place remaining macros in corners
        remaining = []
        for role, group in groups.items():
            if role not in [ModuleRole.IO, ModuleRole.CLOCK, ModuleRole.POWER, 
                           ModuleRole.MEMORY, ModuleRole.DATAPATH]:
                remaining.extend(group)
        
        if remaining:
            self._place_in_corners(remaining, result, core_area)
        
        # Add routing channels between groups
        self._add_routing_channels(result, core_area)
        
        # Define std cell area
        result.std_cell_area["core"] = reserve_width * reserve_height
        
        return result
    
    def _place_top_level(
        self,
        context: DesignContext,
        floorplan: dict[str, Any],
        macros: list[Macro],
    ) -> PlacementResult:
        """
        Top-level placement:
        - Arrange by signal flow
        - Reserve routing channels
        - Reserve space for top-level std cells
        """
        result = PlacementResult()
        
        if not macros:
            return result
        
        # Get floorplan dimensions
        core_area = floorplan.get("core_area", (0, 0, 2000, 2000))
        x1, y1, x2, y2 = core_area
        core_width = x2 - x1
        core_height = y2 - y1
        
        # Get signal flow order from context
        flow_order = self._get_signal_flow_order(context, macros)
        
        # Sort macros by flow order
        macro_map = {m.name: m for m in macros}
        ordered_macros = [macro_map[name] for name in flow_order if name in macro_map]
        
        # Add any macros not in flow order
        placed_names = set(m.name for m in ordered_macros)
        for macro in macros:
            if macro.name not in placed_names:
                ordered_macros.append(macro)
        
        # Arrange in grid pattern following flow order
        num_macros = len(ordered_macros)
        cols = int(num_macros ** 0.5) + 1
        rows = (num_macros + cols - 1) // cols
        
        cell_width = core_width / cols
        cell_height = core_height / rows
        
        current_x = x1 + self.channel_width_um
        current_y = y1 + self.channel_width_um
        
        for i, macro in enumerate(ordered_macros):
            row = i // cols
            col = i % cols
            
            # Place macro in cell
            macro_x = x1 + col * cell_width + self.channel_width_um
            macro_y = y1 + row * cell_height + self.channel_width_um
            
            # Center macro in cell
            macro_x += (cell_width - macro.width_um - 2 * self.channel_width_um) / 2
            macro_y += (cell_height - macro.height_um - 2 * self.channel_width_um) / 2
            
            placement = MacroPlacement(
                macro=macro,
                x_um=macro_x,
                y_um=macro_y,
                rotation="R0",
            )
            result.placements.append(placement)
        
        # Add routing channels
        self._add_routing_channels_grid(result, core_area, cols, rows, cell_width, cell_height)
        
        # Reserve space for top-level std cells (around the grid)
        result.std_cell_area["top_level"] = (
            core_width * core_height - sum(m.area_um2 for m in macros)
        )
        
        return result
    
    def _group_macros_by_role(self, macros: list[Macro]) -> dict[ModuleRole, list[Macro]]:
        """Group macros by role."""
        groups = {}
        for macro in macros:
            if macro.role not in groups:
                groups[macro.role] = []
            groups[macro.role].append(macro)
        return groups
    
    def _place_group_on_edge(
        self,
        groups: list[list[Macro]],
        result: PlacementResult,
        edge: str,
        x1: float, y1: float, x2: float, y2: float,
        direction: str,
    ) -> float:
        """Place a group of macros on an edge."""
        all_macros = []
        for group in groups:
            all_macros.extend(group)
        
        if not all_macros:
            return x1 if direction == "horizontal" else y1
        
        # Sort by size (largest first)
        all_macros.sort(key=lambda m: m.area_um2, reverse=True)
        
        current_pos = x1 if direction == "horizontal" else y1
        
        for macro in all_macros:
            if direction == "horizontal":
                # Place horizontally
                if current_pos + macro.width_um > x2:
                    break
                
                macro_x = current_pos
                macro_y = y1 if edge == "top" else y2 - macro.height_um
                
                placement = MacroPlacement(
                    macro=macro,
                    x_um=macro_x,
                    y_um=macro_y,
                    rotation="R0",
                )
                result.placements.append(placement)
                
                current_pos += macro.width_um + self.macro_spacing_um
            else:
                # Place vertically
                if current_pos + macro.height_um > y2:
                    break
                
                macro_x = x1 if edge == "left" else x2 - macro.width_um
                macro_y = current_pos
                
                placement = MacroPlacement(
                    macro=macro,
                    x_um=macro_x,
                    y_um=macro_y,
                    rotation="R0",
                )
                result.placements.append(placement)
                
                current_pos += macro.height_um + self.macro_spacing_um
        
        return current_pos
    
    def _place_in_corners(
        self,
        macros: list[Macro],
        result: PlacementResult,
        core_area: tuple[float, float, float, float],
    ):
        """Place macros in corners."""
        x1, y1, x2, y2 = core_area
        margin = self.periphery_margin_um
        
        corners = [
            (x1 + margin, y1 + margin),  # Bottom-left
            (x2 - margin - 200, y1 + margin),  # Bottom-right
            (x1 + margin, y2 - margin - 200),  # Top-left
            (x2 - margin - 200, y2 - margin - 200),  # Top-right
        ]
        
        for i, macro in enumerate(macros):
            if i >= len(corners):
                result.warnings.append(f"Not enough space for macro {macro.name}")
                break
            
            cx, cy = corners[i]
            placement = MacroPlacement(
                macro=macro,
                x_um=cx,
                y_um=cy,
                rotation="R0",
            )
            result.placements.append(placement)
    
    def _get_signal_flow_order(
        self,
        context: DesignContext,
        macros: list[Macro],
    ) -> list[str]:
        """Get macro order based on signal flow."""
        # Start with modules that have no incoming interconnects (sources)
        # Then follow the flow
        
        # Build adjacency
        incoming_count = {m.name: 0 for m in macros}
        for ic in context.interconnects:
            if ic.to_module in incoming_count:
                incoming_count[ic.to_module] += 1
        
        # Sort by incoming count (sources first)
        ordered = sorted(macros, key=lambda m: incoming_count.get(m.name, 0))
        
        return [m.name for m in ordered]
    
    def _add_routing_channels(
        self,
        result: PlacementResult,
        core_area: tuple[float, float, float, float],
    ):
        """Add routing channels between macro groups."""
        x1, y1, x2, y2 = core_area
        
        # Horizontal channel in middle
        mid_y = (y1 + y2) / 2
        result.routing_channels.append({
            "name": "h_channel_center",
            "bbox": (x1, mid_y - self.channel_width_um / 2,
                    x2, mid_y + self.channel_width_um / 2),
            "direction": "horizontal",
        })
        
        # Vertical channel in middle
        mid_x = (x1 + x2) / 2
        result.routing_channels.append({
            "name": "v_channel_center",
            "bbox": (mid_x - self.channel_width_um / 2, y1,
                    mid_x + self.channel_width_um / 2, y2),
            "direction": "vertical",
        })
    
    def _add_routing_channels_grid(
        self,
        result: PlacementResult,
        core_area: tuple[float, float, float, float],
        cols: int,
        rows: int,
        cell_width: float,
        cell_height: float,
    ):
        """Add routing channels for grid layout."""
        x1, y1, x2, y2 = core_area
        
        # Horizontal channels between rows
        for row in range(rows):
            channel_y = y1 + row * cell_height
            result.routing_channels.append({
                "name": f"h_channel_{row}",
                "bbox": (x1, channel_y - self.channel_width_um / 2,
                        x2, channel_y + self.channel_width_um / 2),
                "direction": "horizontal",
            })
        
        # Vertical channels between columns
        for col in range(cols):
            channel_x = x1 + col * cell_width
            result.routing_channels.append({
                "name": f"v_channel_{col}",
                "bbox": (channel_x - self.channel_width_um / 2, y1,
                        channel_x + self.channel_width_um / 2, y2),
                "direction": "vertical",
            })
