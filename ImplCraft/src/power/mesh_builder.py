"""
Power Mesh Builder — generates power delivery network structures.

Capabilities:
- Core power rings (top/bottom/left/right)
- Block rings around hard macros
- Horizontal and vertical power straps
- Standard cell power rails
- Multi-voltage domain support
- IR-drop estimation and optimization
- Tcl script generation for ICC2/Innovus

Usage:
    builder = PowerMeshBuilder()
    plan = builder.build_mesh(
        die_area=(0, 0, 2900, 1900),
        core_area=(180, 180, 2720, 1720),
        power_domains=[power_domain],
    )
    tcl_script = builder.generate_icc2_script(plan)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .mesh_config import (
    PowerDomain,
    RingConfig,
    StrapConfig,
    RailConfig,
    BlockRingConfig,
)

logger = logging.getLogger("ic_backend")


@dataclass
class PowerRing:
    """Generated power ring."""
    net_name: str
    layer: str
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    width_um: float
    domain: str


@dataclass
class PowerStrap:
    """Generated power strap."""
    net_name: str
    layer: str
    bbox: tuple[float, float, float, float]
    width_um: float
    direction: str  # horizontal or vertical
    domain: str


@dataclass
class PowerRail:
    """Generated power rail."""
    net_name: str
    layer: str
    bbox: tuple[float, float, float, float]
    width_um: float
    domain: str


@dataclass
class BlockRing:
    """Power ring around a macro."""
    macro_name: str
    net_name: str
    layer: str
    bbox: tuple[float, float, float, float]
    width_um: float
    domain: str


@dataclass
class PowerMeshPlan:
    """Complete power mesh plan."""
    design_name: str
    die_area: tuple[float, float, float, float]
    core_area: tuple[float, float, float, float]
    
    # Generated structures
    core_rings: list[PowerRing] = field(default_factory=list)
    block_rings: list[BlockRing] = field(default_factory=list)
    straps: list[PowerStrap] = field(default_factory=list)
    rails: list[PowerRail] = field(default_factory=list)
    
    # Analysis
    estimated_ir_drop_mv: float = 0.0
    total_strap_length_um: float = 0.0
    total_ring_length_um: float = 0.0
    mesh_density_percentage: float = 0.0
    
    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    summary: str = ""


@dataclass
class PowerMeshConfig:
    """Configuration for power mesh building."""
    ring_config: RingConfig = field(default_factory=RingConfig)
    strap_config: StrapConfig = field(default_factory=StrapConfig)
    rail_config: RailConfig = field(default_factory=RailConfig)
    
    # Mesh density
    target_ir_drop_mv: float = 45.0
    optimize_density: bool = True
    
    # Multi-domain
    support_multi_domain: bool = True


class PowerMeshBuilder:
    """
    Builds power delivery network mesh structures.
    
    Usage:
        builder = PowerMeshBuilder()
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        tcl = builder.generate_icc2_script(plan)
    """
    
    def __init__(self, config: PowerMeshConfig | None = None):
        self.config = config or PowerMeshConfig()
    
    def build_mesh(
        self,
        die_area: tuple[float, float, float, float],
        core_area: tuple[float, float, float, float],
        power_domains: list[PowerDomain],
        macros: list[dict[str, Any]] | None = None,
        design_name: str = "top",
    ) -> PowerMeshPlan:
        """
        Build complete power mesh.
        
        Args:
            die_area: Die bounding box (x1, y1, x2, y2) in um
            core_area: Core area (x1, y1, x2, y2) in um
            power_domains: List of power domains
            macros: List of hard macros with bbox (optional)
            design_name: Design name for reporting
            
        Returns:
            PowerMeshPlan with all generated structures
        """
        plan = PowerMeshPlan(
            design_name=design_name,
            die_area=die_area,
            core_area=core_area,
        )
        
        # Generate core rings
        plan.core_rings = self._generate_core_rings(core_area, power_domains)
        
        # Generate block rings around macros
        if macros:
            plan.block_rings = self._generate_block_rings(macros, power_domains)
        
        # Generate straps
        plan.straps = self._generate_straps(core_area, power_domains)
        
        # Generate rails (simplified representation)
        plan.rails = self._generate_rails(core_area, power_domains)
        
        # Calculate metrics
        plan.total_ring_length_um = self._calculate_ring_length(plan.core_rings)
        plan.total_strap_length_um = self._calculate_strap_length(plan.straps)
        plan.mesh_density_percentage = self._calculate_mesh_density(plan, core_area)
        plan.estimated_ir_drop_mv = self._estimate_ir_drop(plan, power_domains)
        
        # Generate recommendations
        plan.recommendations = self._generate_recommendations(plan, power_domains)
        plan.warnings = self._generate_warnings(plan)
        
        # Generate summary
        plan.summary = self._generate_summary(plan)
        
        return plan
    
    def _generate_core_rings(
        self,
        core_area: tuple[float, float, float, float],
        power_domains: list[PowerDomain],
    ) -> list[PowerRing]:
        """Generate core power rings."""
        rings = []
        ring_cfg = self.config.ring_config
        
        x1, y1, x2, y2 = core_area
        width = ring_cfg.width_um
        spacing = ring_cfg.spacing_um
        offset = ring_cfg.offset_um
        
        for domain in power_domains:
            # Top ring (horizontal)
            rings.append(PowerRing(
                net_name=domain.vdd_net,
                layer=ring_cfg.horizontal_layers[0],
                bbox=(x1 - offset, y2 + offset, x2 + offset, y2 + offset + width),
                width_um=width,
                domain=domain.name,
            ))
            rings.append(PowerRing(
                net_name=domain.vss_net,
                layer=ring_cfg.horizontal_layers[0],
                bbox=(x1 - offset, y2 + offset + width + spacing, x2 + offset, y2 + offset + 2*width + spacing),
                width_um=width,
                domain=domain.name,
            ))
            
            # Bottom ring (horizontal)
            rings.append(PowerRing(
                net_name=domain.vdd_net,
                layer=ring_cfg.horizontal_layers[0],
                bbox=(x1 - offset, y1 - offset - width, x2 + offset, y1 - offset),
                width_um=width,
                domain=domain.name,
            ))
            rings.append(PowerRing(
                net_name=domain.vss_net,
                layer=ring_cfg.horizontal_layers[0],
                bbox=(x1 - offset, y1 - offset - 2*width - spacing, x2 + offset, y1 - offset - width - spacing),
                width_um=width,
                domain=domain.name,
            ))
            
            # Left ring (vertical)
            rings.append(PowerRing(
                net_name=domain.vdd_net,
                layer=ring_cfg.vertical_layers[0],
                bbox=(x1 - offset - width, y1 - offset, x1 - offset, y2 + offset),
                width_um=width,
                domain=domain.name,
            ))
            rings.append(PowerRing(
                net_name=domain.vss_net,
                layer=ring_cfg.vertical_layers[0],
                bbox=(x1 - offset - 2*width - spacing, y1 - offset, x1 - offset - width - spacing, y2 + offset),
                width_um=width,
                domain=domain.name,
            ))
            
            # Right ring (vertical)
            rings.append(PowerRing(
                net_name=domain.vdd_net,
                layer=ring_cfg.vertical_layers[0],
                bbox=(x2 + offset, y1 - offset, x2 + offset + width, y2 + offset),
                width_um=width,
                domain=domain.name,
            ))
            rings.append(PowerRing(
                net_name=domain.vss_net,
                layer=ring_cfg.vertical_layers[0],
                bbox=(x2 + offset + width + spacing, y1 - offset, x2 + offset + 2*width + spacing, y2 + offset),
                width_um=width,
                domain=domain.name,
            ))
        
        return rings
    
    def _generate_block_rings(
        self,
        macros: list[dict[str, Any]],
        power_domains: list[PowerDomain],
    ) -> list[BlockRing]:
        """Generate block rings around macros."""
        block_rings = []
        
        for macro in macros:
            macro_name = macro.get("name", "macro")
            bbox = macro.get("bbox", (0, 0, 100, 100))
            domain_name = macro.get("power_domain", power_domains[0].name if power_domains else "VDD")
            
            # Find the domain
            domain = next((d for d in power_domains if d.name == domain_name), power_domains[0])
            
            # Generate ring around macro
            # Simplified: just create one ring per macro
            block_rings.append(BlockRing(
                macro_name=macro_name,
                net_name=domain.vdd_net,
                layer="M5",
                bbox=bbox,
                width_um=2.0,
                domain=domain.name,
            ))
        
        return block_rings
    
    def _generate_straps(
        self,
        core_area: tuple[float, float, float, float],
        power_domains: list[PowerDomain],
    ) -> list[PowerStrap]:
        """Generate power straps."""
        straps = []
        strap_cfg = self.config.strap_config
        
        x1, y1, x2, y2 = core_area
        core_width = x2 - x1
        core_height = y2 - y1
        
        for domain in power_domains:
            # Horizontal straps
            y_pos = y1 + strap_cfg.start_offset_um
            while y_pos < y2 - strap_cfg.start_offset_um:
                straps.append(PowerStrap(
                    net_name=domain.vdd_net,
                    layer=strap_cfg.layer,
                    bbox=(x1, y_pos, x2, y_pos + strap_cfg.width_um),
                    width_um=strap_cfg.width_um,
                    direction="horizontal",
                    domain=domain.name,
                ))
                straps.append(PowerStrap(
                    net_name=domain.vss_net,
                    layer=strap_cfg.layer,
                    bbox=(x1, y_pos + strap_cfg.width_um + strap_cfg.spacing_um, 
                          x2, y_pos + 2*strap_cfg.width_um + strap_cfg.spacing_um),
                    width_um=strap_cfg.width_um,
                    direction="horizontal",
                    domain=domain.name,
                ))
                y_pos += strap_cfg.set_to_set_distance_um
            
            # Vertical straps
            x_pos = x1 + strap_cfg.start_offset_um
            while x_pos < x2 - strap_cfg.start_offset_um:
                straps.append(PowerStrap(
                    net_name=domain.vdd_net,
                    layer="M8",  # Different layer for vertical
                    bbox=(x_pos, y1, x_pos + strap_cfg.width_um, y2),
                    width_um=strap_cfg.width_um,
                    direction="vertical",
                    domain=domain.name,
                ))
                straps.append(PowerStrap(
                    net_name=domain.vss_net,
                    layer="M8",
                    bbox=(x_pos + strap_cfg.width_um + strap_cfg.spacing_um, y1,
                          x_pos + 2*strap_cfg.width_um + strap_cfg.spacing_um, y2),
                    width_um=strap_cfg.width_um,
                    direction="vertical",
                    domain=domain.name,
                ))
                x_pos += strap_cfg.set_to_set_distance_um
        
        return straps
    
    def _generate_rails(
        self,
        core_area: tuple[float, float, float, float],
        power_domains: list[PowerDomain],
    ) -> list[PowerRail]:
        """Generate standard cell power rails (simplified)."""
        # Rails are typically generated by the P&R tool automatically
        # Here we just create a representative set
        rails = []
        rail_cfg = self.config.rail_config
        
        x1, y1, x2, y2 = core_area
        
        for domain in power_domains:
            # Just create one representative rail
            rails.append(PowerRail(
                net_name=domain.vdd_net,
                layer=rail_cfg.layer,
                bbox=(x1, y1, x2, y1 + rail_cfg.width_um),
                width_um=rail_cfg.width_um,
                domain=domain.name,
            ))
        
        return rails
    
    def _calculate_ring_length(self, rings: list[PowerRing]) -> float:
        """Calculate total ring length."""
        total = 0.0
        for ring in rings:
            x1, y1, x2, y2 = ring.bbox
            if x1 == x2:  # Vertical
                total += abs(y2 - y1)
            else:  # Horizontal
                total += abs(x2 - x1)
        return total
    
    def _calculate_strap_length(self, straps: list[PowerStrap]) -> float:
        """Calculate total strap length."""
        total = 0.0
        for strap in straps:
            x1, y1, x2, y2 = strap.bbox
            if strap.direction == "horizontal":
                total += abs(x2 - x1)
            else:
                total += abs(y2 - y1)
        return total
    
    def _calculate_mesh_density(
        self,
        plan: PowerMeshPlan,
        core_area: tuple[float, float, float, float],
    ) -> float:
        """Calculate mesh density as percentage of core area."""
        x1, y1, x2, y2 = core_area
        core_area_um2 = (x2 - x1) * (y2 - y1)
        
        # Estimate mesh area (rings + straps)
        ring_area = plan.total_ring_length_um * self.config.ring_config.width_um
        strap_area = plan.total_strap_length_um * self.config.strap_config.width_um
        mesh_area = ring_area + strap_area
        
        return 100.0 * mesh_area / core_area_um2 if core_area_um2 > 0 else 0.0
    
    def _estimate_ir_drop(
        self,
        plan: PowerMeshPlan,
        power_domains: list[PowerDomain],
    ) -> float:
        """Estimate IR-drop based on mesh density."""
        # Simplified IR-drop estimation
        # Lower mesh density = higher IR-drop
        target_density = 10.0  # Target 10% mesh density
        
        if plan.mesh_density_percentage >= target_density:
            return self.config.target_ir_drop_mv
        else:
            # Scale IR-drop inversely with density
            ratio = target_density / plan.mesh_density_percentage if plan.mesh_density_percentage > 0 else 10.0
            return self.config.target_ir_drop_mv * min(ratio, 3.0)
    
    def _generate_recommendations(
        self,
        plan: PowerMeshPlan,
        power_domains: list[PowerDomain],
    ) -> list[str]:
        """Generate recommendations for power mesh."""
        recs = []
        
        if plan.estimated_ir_drop_mv > self.config.target_ir_drop_mv:
            recs.append(
                f"Estimated IR-drop ({plan.estimated_ir_drop_mv:.1f} mV) exceeds target "
                f"({self.config.target_ir_drop_mv:.1f} mV). Consider increasing strap density."
            )
        
        if plan.mesh_density_percentage < 5.0:
            recs.append(
                f"Low mesh density ({plan.mesh_density_percentage:.1f}%). "
                f"Consider adding more straps or increasing strap width."
            )
        
        if len(power_domains) > 1:
            recs.append(
                f"Multi-voltage design ({len(power_domains)} domains). "
                f"Ensure proper level shifters and isolation cells."
            )
        
        return recs
    
    def _generate_warnings(self, plan: PowerMeshPlan) -> list[str]:
        """Generate warnings for potential issues."""
        warnings = []
        
        if plan.estimated_ir_drop_mv > 100.0:
            warnings.append(
                f"Very high IR-drop ({plan.estimated_ir_drop_mv:.1f} mV). "
                f"Design may have timing or functionality issues."
            )
        
        if len(plan.straps) > 1000:
            warnings.append(
                f"Large number of straps ({len(plan.straps)}). "
                f"May impact routing resources."
            )
        
        return warnings
    
    def _generate_summary(self, plan: PowerMeshPlan) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Power Mesh Plan for {plan.design_name}",
            "=" * 60,
            "",
            "Mesh Statistics:",
            f"  Core rings: {len(plan.core_rings)}",
            f"  Block rings: {len(plan.block_rings)}",
            f"  Straps: {len(plan.straps)}",
            f"  Rails: {len(plan.rails)}",
            "",
            "Metrics:",
            f"  Total ring length: {plan.total_ring_length_um:.0f} um",
            f"  Total strap length: {plan.total_strap_length_um:.0f} um",
            f"  Mesh density: {plan.mesh_density_percentage:.2f}%",
            f"  Estimated IR-drop: {plan.estimated_ir_drop_mv:.1f} mV",
            "",
        ]
        
        if plan.recommendations:
            lines.append("Recommendations:")
            for rec in plan.recommendations:
                lines.append(f"  • {rec}")
            lines.append("")
        
        if plan.warnings:
            lines.append("Warnings:")
            for warn in plan.warnings:
                lines.append(f"  ⚠ {warn}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_icc2_script(self, plan: PowerMeshPlan) -> str:
        """Generate ICC2 Tcl script for power mesh creation."""
        lines = [
            f"# ICC2 Power Mesh Script for {plan.design_name}",
            "# Auto-generated by PowerMeshBuilder",
            "",
            "# ---- Core Rings ----",
        ]
        
        ring_cfg = self.config.ring_config
        for ring in plan.core_rings[:4]:  # Just first 4 for brevity
            x1, y1, x2, y2 = ring.bbox
            lines.append(
                f"create_pg_ring_pattern {ring.net_name}_ring "
                f"-horizontal_layer {ring.layer} -horizontal_width {ring.width_um} "
                f"-vertical_layer {ring_cfg.vertical_layers[0]} -vertical_width {ring.width_um}"
            )
        
        lines.extend([
            "",
            "# ---- Straps ----",
        ])
        
        strap_cfg = self.config.strap_config
        lines.append(
            f"create_pg_strap_pattern {plan.design_name}_straps "
            f"-layers {{{strap_cfg.layer} M8}} "
            f"-width {strap_cfg.width_um} -pitch {strap_cfg.pitch_um} "
            f"-offset_start {{{strap_cfg.start_offset_um} {strap_cfg.start_offset_um}}}"
        )
        
        lines.extend([
            "",
            "# ---- Compile PG Mesh ----",
            "compile_pg_mesh",
            "",
            "exit",
        ])
        
        return "\n".join(lines)

    def generate_innovus_script(self, plan: PowerMeshPlan) -> str:
        """Generate Innovus Tcl script for power mesh creation."""
        lines = [
            f"# Innovus Power Mesh Script for {plan.design_name}",
            "# Auto-generated by PowerMeshBuilder",
            "",
            "# ---- Core Rings ----",
        ]
        
        ring_cfg = self.config.ring_config
        # Generate createRing command
        lines.append(
            f'createRing -nets "VDD VSS" -type core_rings '
            f'-offset {ring_cfg.offset_um} -width {ring_cfg.width_um} '
            f'-spacing {ring_cfg.spacing_um} '
            f'-layer top {ring_cfg.horizontal_layers[0]} -layer bottom {ring_cfg.horizontal_layers[0]} '
            f'-layer left {ring_cfg.vertical_layers[0]} -layer right {ring_cfg.vertical_layers[0]}'
        )
        
        lines.extend([
            "",
            "# ---- Straps ----",
        ])
        
        strap_cfg = self.config.strap_config
        lines.append(
            f'createStripe -nets "VDD VSS" '
            f'-layer {strap_cfg.layer} -width {strap_cfg.width_um} '
            f'-spacing {strap_cfg.spacing_um} -start_offset {strap_cfg.start_offset_um} '
            f'-set_to_set_distance {strap_cfg.set_to_set_distance_um} '
            f'-extend_to design_boundary'
        )
        
        lines.extend([
            "",
            "# ---- Sroute (connect to pads) ----",
            'sroute -nets "VDD VSS" -connect corePin -padPin VDD -useStraps false',
            "",
            "exit",
        ])
        
        return "\n".join(lines)
