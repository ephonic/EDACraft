"""
PG (Power/Ground) Network Advisor — provides pad placement recommendations
and calculation methodology for power delivery network design.

Capabilities:
- PG pad count calculation based on current requirements
- PG pad placement strategy (uniform, clustered, peripheral)
- I/O pad placement suggestions (timing, signal integrity)
- Bond pad placement strategy
- IR-drop estimation and mitigation
- Electromigration (EM) checking

This integrates with the floorplan advisor and partition system.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .module_graph import ModuleGraph, ModuleNode


class PadType(Enum):
    """Types of pads in IC design."""
    PG_PAD = "pg_pad"           # Power/Ground pad
    IO_PAD = "io_pad"           # Signal I/O pad
    BOND_PAD = "bond_pad"       # Wire bond pad
    FLIP_CHIP_BUMP = "fc_bump"  # Flip chip bump


class PlacementStrategy(Enum):
    """Pad placement strategies."""
    UNIFORM = "uniform"         # Uniformly distributed
    CLUSTERED = "clustered"     # Clustered in groups
    PERIPHERAL = "peripheral"   # Around chip periphery
    CORNER = "corner"           # At chip corners
    MIXED = "mixed"             # Mixed strategy


@dataclass
class PowerConfig:
    """Power configuration for the design."""
    vdd_voltage: float = 0.9            # Core supply voltage (V)
    vddq_voltage: float | None = None   # I/O supply voltage (V)
    total_power_w: float = 1.0          # Total power consumption (W)
    core_power_w: float = 0.7           # Core power consumption (W)
    io_power_w: float = 0.3             # I/O power consumption (W)
    max_current_per_pad_a: float = 0.1  # Max current per PG pad (A)
    current_density_limit_a_um: float = 0.001  # Current density limit (A/um)
    num_power_domains: int = 1          # Number of power domains
    power_domain_names: list[str] = field(default_factory=lambda: ["VDD"])


@dataclass
class PadSpec:
    """Specification for a pad type."""
    pad_type: PadType
    width_um: float = 80.0
    height_um: float = 80.0
    pitch_um: float = 100.0
    max_current_a: float = 0.1
    resistance_ohm: float = 0.01


@dataclass
class PadPlacement:
    """Placement information for a single pad."""
    pad_id: str
    pad_type: PadType
    x_um: float
    y_um: float
    width_um: float
    height_um: float
    net_name: str = ""
    domain: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class PGNetworkPlan:
    """Complete PG network plan."""
    design_name: str
    die_width_um: float
    die_height_um: float
    
    # Calculated requirements
    total_pg_pads_needed: int = 0
    vdd_pads_needed: int = 0
    vss_pads_needed: int = 0
    
    # Placement results
    pg_pad_placements: list[PadPlacement] = field(default_factory=list)
    io_pad_placements: list[PadPlacement] = field(default_factory=list)
    bond_pad_placements: list[PadPlacement] = field(default_factory=list)
    
    # Analysis results
    estimated_ir_drop_mv: float = 0.0
    max_current_density_a_um: float = 0.0
    em_violations: int = 0
    
    # Recommendations
    placement_strategy: PlacementStrategy = PlacementStrategy.UNIFORM
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    summary: str = ""


class PGNetworkAdvisor:
    """
    Advisor for PG network and pad placement planning.
    
    Usage:
        advisor = PGNetworkAdvisor()
        plan = advisor.plan_pg_network(
            power_config=power_config,
            pad_spec=pad_spec,
            die_width_um=2900,
            die_height_um=1900,
        )
        print(plan.summary)
    """
    
    def __init__(self):
        self.default_pad_spec = PadSpec(
            pad_type=PadType.PG_PAD,
            width_um=80.0,
            height_um=80.0,
            pitch_um=100.0,
            max_current_a=0.1,
        )
    
    def plan_pg_network(
        self,
        power_config: PowerConfig,
        pad_spec: PadSpec | None = None,
        die_width_um: float = 2900.0,
        die_height_um: float = 1900.0,
        num_io_pads: int = 100,
        num_bond_pads: int = 0,
        placement_strategy: PlacementStrategy = PlacementStrategy.UNIFORM,
    ) -> PGNetworkPlan:
        """
        Generate complete PG network plan.
        
        Args:
            power_config: Power configuration for the design
            pad_spec: Pad specifications (uses default if None)
            die_width_um: Die width in micrometers
            die_height_um: Die height in micrometers
            num_io_pads: Number of I/O pads
            num_bond_pads: Number of bond pads (0 = auto)
            placement_strategy: Strategy for pad placement
            
        Returns:
            PGNetworkPlan with all placement details
        """
        if pad_spec is None:
            pad_spec = self.default_pad_spec
        
        plan = PGNetworkPlan(
            design_name="design",
            die_width_um=die_width_um,
            die_height_um=die_height_um,
            placement_strategy=placement_strategy,
        )
        
        # Step 1: Calculate PG pad requirements
        self._calculate_pg_requirements(plan, power_config, pad_spec)
        
        # Step 2: Place PG pads
        self._place_pg_pads(plan, pad_spec, placement_strategy)
        
        # Step 3: Place I/O pads
        self._place_io_pads(plan, num_io_pads, pad_spec)
        
        # Step 4: Place bond pads (if any)
        if num_bond_pads > 0:
            self._place_bond_pads(plan, num_bond_pads, pad_spec)
        
        # Step 5: Analyze IR-drop and EM
        self._analyze_power_integrity(plan, power_config, pad_spec)
        
        # Step 6: Generate recommendations
        self._generate_recommendations(plan, power_config)
        
        # Step 7: Generate summary
        plan.summary = self._generate_summary(plan)
        
        return plan
    
    def _calculate_pg_requirements(
        self,
        plan: PGNetworkPlan,
        power_config: PowerConfig,
        pad_spec: PadSpec,
    ):
        """Calculate number of PG pads needed."""
        
        # Calculate total current
        total_current_a = power_config.total_power_w / power_config.vdd_voltage
        
        # Calculate pads needed per supply
        pads_per_supply = math.ceil(
            total_current_a / (2 * pad_spec.max_current_a)
        )
        
        # VDD and VSS need equal number of pads
        plan.vdd_pads_needed = pads_per_supply
        plan.vss_pads_needed = pads_per_supply
        plan.total_pg_pads_needed = plan.vdd_pads_needed + plan.vss_pads_needed
        
        # Add safety margin (20%)
        plan.total_pg_pads_needed = math.ceil(plan.total_pg_pads_needed * 1.2)
    
    def _place_pg_pads(
        self,
        plan: PGNetworkPlan,
        pad_spec: PadSpec,
        strategy: PlacementStrategy,
    ):
        """Place PG pads according to strategy."""
        
        if strategy == PlacementStrategy.UNIFORM:
            self._place_pg_uniform(plan, pad_spec)
        elif strategy == PlacementStrategy.CLUSTERED:
            self._place_pg_clustered(plan, pad_spec)
        elif strategy == PlacementStrategy.PERIPHERAL:
            self._place_pg_peripheral(plan, pad_spec)
        elif strategy == PlacementStrategy.CORNER:
            self._place_pg_corner(plan, pad_spec)
        else:
            self._place_pg_uniform(plan, pad_spec)
    
    def _place_pg_uniform(self, plan: PGNetworkPlan, pad_spec: PadSpec):
        """Uniformly distribute PG pads around periphery."""
        
        perimeter = 2 * (plan.die_width_um + plan.die_height_um)
        available_length = perimeter * 0.8  # 80% for PG pads
        
        # Calculate spacing
        num_pads = plan.total_pg_pads_needed
        spacing = available_length / num_pads
        
        # Place pads
        current_pos = 0.0
        pad_idx = 0
        
        for i in range(num_pads):
            # Determine which side
            if current_pos < plan.die_width_um:
                # Bottom side
                x = current_pos
                y = 0.0
            elif current_pos < plan.die_width_um + plan.die_height_um:
                # Right side
                x = plan.die_width_um
                y = current_pos - plan.die_width_um
            elif current_pos < 2 * plan.die_width_um + plan.die_height_um:
                # Top side
                x = plan.die_width_um - (current_pos - plan.die_width_um - plan.die_height_um)
                y = plan.die_height_um
            else:
                # Left side
                x = 0.0
                y = plan.die_height_um - (current_pos - 2 * plan.die_width_um - plan.die_height_um)
            
            # Alternate VDD/VSS
            net_name = "VDD" if i % 2 == 0 else "VSS"
            
            placement = PadPlacement(
                pad_id=f"PG_{pad_idx:03d}",
                pad_type=PadType.PG_PAD,
                x_um=x,
                y_um=y,
                width_um=pad_spec.width_um,
                height_um=pad_spec.height_um,
                net_name=net_name,
                domain="CORE",
            )
            plan.pg_pad_placements.append(placement)
            
            current_pos += spacing
            pad_idx += 1
    
    def _place_pg_clustered(self, plan: PGNetworkPlan, pad_spec: PadSpec):
        """Place PG pads in clusters (groups of 4-8)."""
        
        # Group pads into clusters of 4
        cluster_size = 4
        num_clusters = math.ceil(plan.total_pg_pads_needed / cluster_size)
        
        # Distribute clusters around periphery
        perimeter = 2 * (plan.die_width_um + plan.die_height_um)
        cluster_spacing = perimeter / num_clusters
        
        pad_idx = 0
        for cluster in range(num_clusters):
            # Cluster center position
            cluster_pos = cluster * cluster_spacing
            
            # Place pads in cluster
            for j in range(min(cluster_size, plan.total_pg_pads_needed - pad_idx)):
                offset = (j - cluster_size / 2) * pad_spec.pitch_um
                
                # Calculate position with offset
                pos = cluster_pos + offset
                
                # Determine coordinates
                if pos < plan.die_width_um:
                    x = pos
                    y = 0.0
                elif pos < plan.die_width_um + plan.die_height_um:
                    x = plan.die_width_um
                    y = pos - plan.die_width_um
                elif pos < 2 * plan.die_width_um + plan.die_height_um:
                    x = plan.die_width_um - (pos - plan.die_width_um - plan.die_height_um)
                    y = plan.die_height_um
                else:
                    x = 0.0
                    y = plan.die_height_um - (pos - 2 * plan.die_width_um - plan.die_height_um)
                
                net_name = "VDD" if j % 2 == 0 else "VSS"
                
                placement = PadPlacement(
                    pad_id=f"PG_{pad_idx:03d}",
                    pad_type=PadType.PG_PAD,
                    x_um=x,
                    y_um=y,
                    width_um=pad_spec.width_um,
                    height_um=pad_spec.height_um,
                    net_name=net_name,
                    domain="CORE",
                )
                plan.pg_pad_placements.append(placement)
                pad_idx += 1
    
    def _place_pg_peripheral(self, plan: PGNetworkPlan, pad_spec: PadSpec):
        """Place PG pads around entire periphery."""
        # Similar to uniform but uses more of periphery
        self._place_pg_uniform(plan, pad_spec)
    
    def _place_pg_corner(self, plan: PGNetworkPlan, pad_spec: PadSpec):
        """Place PG pads concentrated at corners."""
        
        # Divide pads among 4 corners
        pads_per_corner = plan.total_pg_pads_needed // 4
        corner_positions = [
            (0.0, 0.0),                                    # Bottom-left
            (plan.die_width_um, 0.0),                      # Bottom-right
            (plan.die_width_um, plan.die_height_um),       # Top-right
            (0.0, plan.die_height_um),                     # Top-left
        ]
        
        pad_idx = 0
        for corner_idx, (cx, cy) in enumerate(corner_positions):
            for j in range(pads_per_corner):
                # Arrange in L-shape around corner
                if j < pads_per_corner // 2:
                    # Horizontal line
                    offset = j * pad_spec.pitch_um
                    x = cx + offset if corner_idx < 2 else cx - offset
                    y = cy
                else:
                    # Vertical line
                    offset = (j - pads_per_corner // 2) * pad_spec.pitch_um
                    x = cx
                    y = cy + offset if corner_idx in [0, 3] else cy - offset
                
                net_name = "VDD" if j % 2 == 0 else "VSS"
                
                placement = PadPlacement(
                    pad_id=f"PG_{pad_idx:03d}",
                    pad_type=PadType.PG_PAD,
                    x_um=x,
                    y_um=y,
                    width_um=pad_spec.width_um,
                    height_um=pad_spec.height_um,
                    net_name=net_name,
                    domain="CORE",
                )
                plan.pg_pad_placements.append(placement)
                pad_idx += 1
    
    def _place_io_pads(
        self,
        plan: PGNetworkPlan,
        num_io_pads: int,
        pad_spec: PadSpec,
    ):
        """Place I/O pads between PG pads."""
        
        # I/O pads go between PG pads
        perimeter = 2 * (plan.die_width_um + plan.die_height_um)
        
        # Calculate available slots (between PG pads)
        pg_count = len(plan.pg_pad_placements)
        if pg_count == 0:
            spacing = perimeter / num_io_pads
        else:
            spacing = perimeter / (pg_count + num_io_pads)
        
        # Place I/O pads
        current_pos = spacing / 2  # Offset from PG pads
        for i in range(num_io_pads):
            if current_pos < plan.die_width_um:
                x = current_pos
                y = 0.0
            elif current_pos < plan.die_width_um + plan.die_height_um:
                x = plan.die_width_um
                y = current_pos - plan.die_width_um
            elif current_pos < 2 * plan.die_width_um + plan.die_height_um:
                x = plan.die_width_um - (current_pos - plan.die_width_um - plan.die_height_um)
                y = plan.die_height_um
            else:
                x = 0.0
                y = plan.die_height_um - (current_pos - 2 * plan.die_width_um - plan.die_height_um)
            
            placement = PadPlacement(
                pad_id=f"IO_{i:03d}",
                pad_type=PadType.IO_PAD,
                x_um=x,
                y_um=y,
                width_um=pad_spec.width_um * 0.8,  # I/O pads slightly smaller
                height_um=pad_spec.height_um * 0.8,
                net_name=f"IO_{i}",
                domain="IO",
            )
            plan.io_pad_placements.append(placement)
            
            current_pos += spacing
    
    def _place_bond_pads(
        self,
        plan: PGNetworkPlan,
        num_bond_pads: int,
        pad_spec: PadSpec,
    ):
        """Place bond pads (typically larger than I/O pads)."""
        
        # Bond pads are larger and need more spacing
        bond_pad_spec = PadSpec(
            pad_type=PadType.BOND_PAD,
            width_um=pad_spec.width_um * 1.5,
            height_um=pad_spec.height_um * 1.5,
            pitch_um=pad_spec.pitch_um * 1.5,
        )
        
        # Distribute around periphery
        perimeter = 2 * (plan.die_width_um + plan.die_height_um)
        spacing = perimeter / num_bond_pads
        
        current_pos = 0.0
        for i in range(num_bond_pads):
            if current_pos < plan.die_width_um:
                x = current_pos
                y = 0.0
            elif current_pos < plan.die_width_um + plan.die_height_um:
                x = plan.die_width_um
                y = current_pos - plan.die_width_um
            elif current_pos < 2 * plan.die_width_um + plan.die_height_um:
                x = plan.die_width_um - (current_pos - plan.die_width_um - plan.die_height_um)
                y = plan.die_height_um
            else:
                x = 0.0
                y = plan.die_height_um - (current_pos - 2 * plan.die_width_um - plan.die_height_um)
            
            placement = PadPlacement(
                pad_id=f"BOND_{i:03d}",
                pad_type=PadType.BOND_PAD,
                x_um=x,
                y_um=y,
                width_um=bond_pad_spec.width_um,
                height_um=bond_pad_spec.height_um,
                net_name=f"BOND_{i}",
                domain="IO",
            )
            plan.bond_pad_placements.append(placement)
            
            current_pos += spacing
    
    def _analyze_power_integrity(
        self,
        plan: PGNetworkPlan,
        power_config: PowerConfig,
        pad_spec: PadSpec,
    ):
        """Analyze IR-drop and electromigration."""
        
        if len(plan.pg_pad_placements) == 0:
            return
        
        # Estimate average distance from pad to core center
        center_x = plan.die_width_um / 2
        center_y = plan.die_height_um / 2
        
        total_distance = 0.0
        for pad in plan.pg_pad_placements:
            dx = pad.x_um - center_x
            dy = pad.y_um - center_y
            distance = math.sqrt(dx * dx + dy * dy)
            total_distance += distance
        
        avg_distance = total_distance / len(plan.pg_pad_placements)
        
        # Estimate IR-drop (simplified model)
        # IR = I * R, where R proportional to distance
        total_current = power_config.total_power_w / power_config.vdd_voltage
        current_per_pad = total_current / len(plan.pg_pad_placements)
        
        # Assume 10 mOhm per 100 um of strap resistance
        resistance_per_um = 0.0001  # Ohm/um
        estimated_resistance = avg_distance * resistance_per_um
        ir_drop_v = current_per_pad * estimated_resistance
        plan.estimated_ir_drop_mv = ir_drop_v * 1000
        
        # Check EM (simplified)
        max_current_density = current_per_pad / (pad_spec.width_um * 10)  # Assume 10um width strap
        plan.max_current_density_a_um = max_current_density
        
        if max_current_density > power_config.current_density_limit_a_um:
            plan.em_violations += 1
            plan.warnings.append(
                f"Potential EM violation: current density {max_current_density:.4f} A/um "
                f"exceeds limit {power_config.current_density_limit_a_um:.4f} A/um"
            )
    
    def _generate_recommendations(
        self,
        plan: PGNetworkPlan,
        power_config: PowerConfig,
    ):
        """Generate placement recommendations."""
        
        # IR-drop recommendations
        if plan.estimated_ir_drop_mv > 50:
            plan.recommendations.append(
                f"High IR-drop ({plan.estimated_ir_drop_mv:.1f} mV). "
                "Consider: (1) adding more PG pads, (2) using clustered placement, "
                "(3) increasing strap width"
            )
        elif plan.estimated_ir_drop_mv > 20:
            plan.recommendations.append(
                f"Moderate IR-drop ({plan.estimated_ir_drop_mv:.1f} mV). "
                "Monitor during detailed PDN analysis"
            )
        
        # EM recommendations
        if plan.em_violations > 0:
            plan.recommendations.append(
                f"{plan.em_violations} potential EM violations detected. "
                "Widen power straps or add more PG pads"
            )
        
        # Placement strategy recommendations
        if plan.placement_strategy == PlacementStrategy.UNIFORM:
            if plan.total_pg_pads_needed > 100:
                plan.recommendations.append(
                    "Large number of PG pads. Consider clustered placement "
                    "to reduce routing complexity"
                )
        
        # I/O pad recommendations
        if len(plan.io_pad_placements) > 200:
            plan.recommendations.append(
                "High I/O count. Consider staggered placement or multiple rows"
            )
        
        # Power domain recommendations
        if power_config.num_power_domains > 1:
            plan.recommendations.append(
                f"Multiple power domains ({power_config.num_power_domains}). "
                "Ensure proper isolation and level shifters"
            )
    
    def _generate_summary(self, plan: PGNetworkPlan) -> str:
        """Generate human-readable summary."""
        
        lines = [
            "=" * 70,
            f"PG NETWORK PLAN: {plan.design_name}",
            "=" * 70,
            "",
            "DESIGN PARAMETERS:",
            f"  Die size: {plan.die_width_um:.0f} x {plan.die_height_um:.0f} um",
            f"  Placement strategy: {plan.placement_strategy.value}",
            "",
            "PG PAD REQUIREMENTS:",
            f"  Total PG pads needed: {plan.total_pg_pads_needed}",
            f"    - VDD pads: {plan.vdd_pads_needed}",
            f"    - VSS pads: {plan.vss_pads_needed}",
            "",
            "PLACEMENT SUMMARY:",
            f"  PG pads placed: {len(plan.pg_pad_placements)}",
            f"  I/O pads placed: {len(plan.io_pad_placements)}",
            f"  Bond pads placed: {len(plan.bond_pad_placements)}",
            "",
            "POWER INTEGRITY ANALYSIS:",
            f"  Estimated IR-drop: {plan.estimated_ir_drop_mv:.2f} mV",
            f"  Max current density: {plan.max_current_density_a_um:.4f} A/um",
            f"  EM violations: {plan.em_violations}",
            "",
        ]
        
        if plan.recommendations:
            lines.extend([
                "RECOMMENDATIONS:",
            ])
            for i, rec in enumerate(plan.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")
        
        if plan.warnings:
            lines.extend([
                "WARNINGS:",
            ])
            for warning in plan.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_pg_script(
        self,
        plan: PGNetworkPlan,
        output_path: str,
        tool: str = "icc2",
    ):
        """Generate PG network creation script."""
        
        if tool == "icc2":
            self._generate_icc2_pg_script(plan, output_path)
        else:
            raise ValueError(f"Unsupported tool: {tool}")
    
    def _generate_icc2_pg_script(self, plan: PGNetworkPlan, output_path: str):
        """Generate ICC2 PG creation script."""
        
        lines = [
            "# PG Network Creation Script",
            f"# Design: {plan.design_name}",
            f"# Total PG pads: {plan.total_pg_pads_needed}",
            "",
            "# Create PG straps",
            "create_pg_ring_pattern PG_RING \\",
            "    -horizontal_layer M9 \\",
            "    -vertical_layer M8 \\",
            "    -horizontal_width 5 \\",
            "    -vertical_width 5 \\",
            "    -horizontal_pitch 20 \\",
            "    -vertical_pitch 20",
            "",
            "# Create PG mesh",
            "create_pg_mesh_pattern PG_MESH \\",
            "    -layers {M9 M8 M7} \\",
            "    -layer_directions {horizontal vertical horizontal} \\",
            "    -layer_widths {3 3 3} \\",
            "    -layer_pitches {20 20 20} \\",
            "    -layer_offsets {0 10 0} \\",
            "    -layer_spacings {2 2 2}",
            "",
            "# Compile PG",
            "compile_pg -patterns {PG_RING PG_MESH} \\",
            "    -voltage_areas {{{{0 0}} {{%.0f %.0f}}}}" % (plan.die_width_um, plan.die_height_um),
            "",
            "# Create PG pads",
        ]
        
        for pad in plan.pg_pad_placements:
            lines.append(
                f"create_pg_pad -net {pad.net_name} "
                f"-coordinate {{{pad.x_um:.2f} {pad.y_um:.2f}}} "
                f"-size {{{pad.width_um:.2f} {pad.height_um:.2f}}}"
            )
        
        lines.extend([
            "",
            "# Connect PG pads to straps",
            "compile_pg -connect_pads",
            "",
        ])
        
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
