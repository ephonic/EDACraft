"""
Area Planner — estimates die size and generates area budget breakdown.

Capabilities:
- Die size estimation from gate count + macro area + I/O count
- Aspect ratio optimization for routing efficiency
- Core offset calculation (I/O ring + seal ring)
- Multiple die size candidates with trade-offs
- Area budget breakdown (logic + macro + routing + I/O + power)

Methodology:
1. Calculate logic area = gate_count * avg_gate_area_um2
2. Add macro area (SRAM + analog IP)
3. Apply target utilization (0.6 - 0.8)
4. Add routing overhead factor (1.2 - 1.5x)
5. Calculate core area
6. Add I/O ring width (100-200um per side)
7. Add seal ring (10-20um per side)
8. Optimize aspect ratio (typically 1.0 - 1.5)

Usage:
    planner = AreaPlanner()
    plan = planner.estimate_die_size(
        gate_count=2_000_000,
        macro_area_um2=500_000,
        io_count=200,
    )
    print(plan.summary)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MacroSpec:
    """Specification for a hard macro."""
    name: str
    width_um: float
    height_um: float
    macro_type: str = "sram"  # sram, analog, digital_ip, custom
    power_domain: str = "VDD"
    keepout_um: float = 5.0  # Keepout around macro
    halo_um: float = 10.0    # Halo for routing


@dataclass
class AreaBudget:
    """Area budget breakdown."""
    logic_area_um2: float = 0.0
    macro_area_um2: float = 0.0
    routing_area_um2: float = 0.0
    io_area_um2: float = 0.0
    power_mesh_area_um2: float = 0.0
    margin_area_um2: float = 0.0
    total_core_area_um2: float = 0.0
    total_die_area_um2: float = 0.0

    @property
    def logic_percentage(self) -> float:
        if self.total_core_area_um2 == 0:
            return 0.0
        return 100.0 * self.logic_area_um2 / self.total_core_area_um2

    @property
    def macro_percentage(self) -> float:
        if self.total_core_area_um2 == 0:
            return 0.0
        return 100.0 * self.macro_area_um2 / self.total_core_area_um2

    @property
    def routing_percentage(self) -> float:
        if self.total_core_area_um2 == 0:
            return 0.0
        return 100.0 * self.routing_area_um2 / self.total_core_area_um2


@dataclass
class DieSizeCandidate:
    """Candidate die size with metrics."""
    width_um: float
    height_um: float
    core_width_um: float
    core_height_um: float
    area_um2: float
    utilization: float
    aspect_ratio: float
    score: float = 0.0  # Higher = better
    notes: list[str] = field(default_factory=list)

    @property
    def area_mm2(self) -> float:
        return self.area_um2 / 1_000_000.0


@dataclass
class AreaPlan:
    """Complete area planning result."""
    design_name: str
    gate_count: int
    macro_count: int
    io_count: int
    
    # Estimated areas
    budget: AreaBudget = field(default_factory=AreaBudget)
    
    # Die size candidates
    candidates: list[DieSizeCandidate] = field(default_factory=list)
    recommended: DieSizeCandidate | None = None
    
    # Configuration
    target_utilization: float = 0.7
    routing_overhead_factor: float = 1.3
    avg_gate_area_um2: float = 1.5  # Average gate area in um2
    
    # I/O ring
    io_ring_width_um: float = 150.0  # Width of I/O ring on each side
    seal_ring_width_um: float = 15.0  # Seal ring width
    
    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    summary: str = ""


class AreaPlanner:
    """
    Plans die size and area budget for IC designs.
    
    Usage:
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=2_000_000,
            macro_area_um2=500_000,
            io_count=200,
        )
        print(f"Recommended die: {plan.recommended.width_um} x {plan.recommended.height_um} um")
    """
    
    # Technology-dependent constants (can be overridden)
    DEFAULT_GATE_AREA_UM2 = 1.5  # Average gate area (28nm HPC+)
    DEFAULT_IO_RING_WIDTH_UM = 150.0  # Typical I/O ring width
    DEFAULT_SEAL_RING_WIDTH_UM = 15.0  # Seal ring width
    DEFAULT_ROUTING_OVERHEAD = 1.3  # Routing area multiplier
    
    # Aspect ratio constraints
    MIN_ASPECT_RATIO = 0.8  # Min height/width ratio
    MAX_ASPECT_RATIO = 1.5  # Max height/width ratio
    OPTIMAL_ASPECT_RATIO = 1.2  # Slightly taller than wide for routing
    
    def __init__(
        self,
        avg_gate_area_um2: float = DEFAULT_GATE_AREA_UM2,
        io_ring_width_um: float = DEFAULT_IO_RING_WIDTH_UM,
        seal_ring_width_um: float = DEFAULT_SEAL_RING_WIDTH_UM,
        routing_overhead: float = DEFAULT_ROUTING_OVERHEAD,
    ):
        self.avg_gate_area_um2 = avg_gate_area_um2
        self.io_ring_width_um = io_ring_width_um
        self.seal_ring_width_um = seal_ring_width_um
        self.routing_overhead = routing_overhead
    
    def estimate_die_size(
        self,
        gate_count: int,
        macro_area_um2: float = 0.0,
        macros: list[MacroSpec] | None = None,
        io_count: int = 100,
        target_utilization: float = 0.7,
        aspect_ratio: float = 1.2,
        design_name: str = "top",
    ) -> AreaPlan:
        """
        Estimate die size and generate area plan.
        
        Args:
            gate_count: Total gate count (standard cells)
            macro_area_um2: Total hard macro area in um2
            macros: List of macro specifications (optional, more detailed)
            io_count: Number of I/O pads
            target_utilization: Target core utilization (0.6 - 0.8)
            aspect_ratio: Target die aspect ratio (height/width)
            design_name: Design name for reporting
            
        Returns:
            AreaPlan with budget and die size candidates
        """
        plan = AreaPlan(
            design_name=design_name,
            gate_count=gate_count,
            macro_count=len(macros) if macros else 0,
            io_count=io_count,
            target_utilization=target_utilization,
            routing_overhead_factor=self.routing_overhead,
            avg_gate_area_um2=self.avg_gate_area_um2,
            io_ring_width_um=self.io_ring_width_um,
            seal_ring_width_um=self.seal_ring_width_um,
        )
        
        # Calculate area budget
        plan.budget = self._calculate_area_budget(
            gate_count, macro_area_um2, macros, io_count, target_utilization
        )
        
        # Generate die size candidates
        plan.candidates = self._generate_candidates(
            plan.budget, target_utilization, aspect_ratio
        )
        
        # Select recommended candidate
        plan.recommended = self._select_recommended(plan.candidates)
        
        # Generate recommendations
        plan.recommendations = self._generate_recommendations(plan)
        plan.warnings = self._generate_warnings(plan)
        
        # Generate summary
        plan.summary = self._generate_summary(plan)
        
        return plan
    
    def _calculate_area_budget(
        self,
        gate_count: int,
        macro_area_um2: float,
        macros: list[MacroSpec] | None,
        io_count: int,
        target_utilization: float,
    ) -> AreaBudget:
        """Calculate detailed area budget breakdown."""
        budget = AreaBudget()
        
        # Logic area
        budget.logic_area_um2 = gate_count * self.avg_gate_area_um2
        
        # Macro area (use detailed specs if available)
        if macros:
            total_macro_area = 0.0
            for m in macros:
                # Include keepout and halo
                effective_width = m.width_um + 2 * (m.keepout_um + m.halo_um)
                effective_height = m.height_um + 2 * (m.keepout_um + m.halo_um)
                total_macro_area += effective_width * effective_height
            budget.macro_area_um2 = total_macro_area
        else:
            budget.macro_area_um2 = macro_area_um2
        
        # Routing area (estimated as overhead on logic area)
        budget.routing_area_um2 = budget.logic_area_um2 * (self.routing_overhead - 1.0)
        
        # I/O area (estimated based on pad count and typical pad size)
        # Assume 80um x 80um pads with 100um pitch
        pad_area_um2 = 80.0 * 80.0
        budget.io_area_um2 = io_count * pad_area_um2 * 1.2  # 20% margin
        
        # Power mesh area (estimated as 5-10% of core area)
        core_area_without_power = (
            budget.logic_area_um2 + budget.macro_area_um2 + budget.routing_area_um2
        )
        budget.power_mesh_area_um2 = core_area_without_power * 0.08
        
        # Total core area (before utilization adjustment)
        raw_core_area = (
            budget.logic_area_um2
            + budget.macro_area_um2
            + budget.routing_area_um2
            + budget.power_mesh_area_um2
        )
        
        # Apply utilization factor
        budget.total_core_area_um2 = raw_core_area / target_utilization
        
        # Margin (10% of core area)
        budget.margin_area_um2 = budget.total_core_area_um2 * 0.10
        budget.total_core_area_um2 += budget.margin_area_um2
        
        # Total die area (core + I/O ring + seal ring)
        io_ring_area = self._calculate_io_ring_area(budget.total_core_area_um2, io_count)
        budget.total_die_area_um2 = budget.total_core_area_um2 + io_ring_area
        
        return budget
    
    def _calculate_io_ring_area(self, core_area_um2: float, io_count: int) -> float:
        """Calculate I/O ring area."""
        # Estimate core dimensions
        core_side_um = math.sqrt(core_area_um2)
        
        # I/O ring adds width on all 4 sides
        io_ring_width = self.io_ring_width_um
        seal_ring_width = self.seal_ring_width_um
        total_offset = io_ring_width + seal_ring_width
        
        # Die dimensions
        die_width = core_side_um + 2 * total_offset
        die_height = core_side_um + 2 * total_offset
        die_area = die_width * die_height
        
        return die_area - core_area_um2
    
    def _generate_candidates(
        self,
        budget: AreaBudget,
        target_utilization: float,
        base_aspect_ratio: float,
    ) -> list[DieSizeCandidate]:
        """Generate multiple die size candidates with different aspect ratios."""
        candidates = []
        
        # Calculate the "used" area (logic + macro only)
        used_area = budget.logic_area_um2 + budget.macro_area_um2
        
        # Calculate required core area to achieve target utilization
        required_core_area = used_area / target_utilization
        
        # Try different aspect ratios
        aspect_ratios = [0.9, 1.0, 1.2, 1.4]
        
        for ar in aspect_ratios:
            if ar < self.MIN_ASPECT_RATIO or ar > self.MAX_ASPECT_RATIO:
                continue
            
            # Calculate core dimensions from required core area
            core_width = math.sqrt(required_core_area / ar)
            core_height = required_core_area / core_width
            
            # Add I/O ring and seal ring
            total_offset = self.io_ring_width_um + self.seal_ring_width_um
            die_width = core_width + 2 * total_offset
            die_height = core_height + 2 * total_offset
            
            # Round to 10um grid
            die_width = math.ceil(die_width / 10.0) * 10.0
            die_height = math.ceil(die_height / 10.0) * 10.0
            
            # Recalculate core dimensions
            core_width = die_width - 2 * total_offset
            core_height = die_height - 2 * total_offset
            actual_core_area = core_width * core_height
            actual_die_area = die_width * die_height
            
            # Calculate actual utilization (used area / actual core area)
            actual_util = used_area / actual_core_area if actual_core_area > 0 else 0
            
            # Score this candidate
            score = self._score_candidate(
                actual_util, target_utilization, ar, base_aspect_ratio
            )
            
            notes = []
            if ar == base_aspect_ratio:
                notes.append("Target aspect ratio")
            if abs(actual_util - target_utilization) < 0.05:
                notes.append("Good utilization match")
            if 0.65 <= actual_util <= 0.75:
                notes.append("Optimal utilization range")
            
            candidates.append(DieSizeCandidate(
                width_um=die_width,
                height_um=die_height,
                core_width_um=core_width,
                core_height_um=core_height,
                area_um2=actual_die_area,
                utilization=actual_util,
                aspect_ratio=ar,
                score=score,
                notes=notes,
            ))
        
        # Sort by score (descending)
        candidates.sort(key=lambda c: c.score, reverse=True)
        
        return candidates
    
    def _score_candidate(
        self,
        actual_util: float,
        target_util: float,
        actual_ar: float,
        target_ar: float,
    ) -> float:
        """Score a die size candidate (higher = better)."""
        score = 100.0
        
        # Penalize deviation from target utilization
        util_error = abs(actual_util - target_util)
        score -= util_error * 50  # 50 points per 1.0 utilization error
        
        # Penalize deviation from target aspect ratio
        ar_error = abs(actual_ar - target_ar)
        score -= ar_error * 20  # 20 points per 1.0 AR error
        
        # Bonus for optimal utilization range (0.65 - 0.75)
        if 0.65 <= actual_util <= 0.75:
            score += 10
        
        # Bonus for reasonable aspect ratio (1.0 - 1.3)
        if 1.0 <= actual_ar <= 1.3:
            score += 5
        
        return max(score, 0.0)
    
    def _select_recommended(self, candidates: list[DieSizeCandidate]) -> DieSizeCandidate | None:
        """Select the recommended die size candidate."""
        if not candidates:
            return None
        return candidates[0]  # Highest score
    
    def _generate_recommendations(self, plan: AreaPlan) -> list[str]:
        """Generate recommendations based on area plan."""
        recs = []
        
        if plan.recommended:
            util = plan.recommended.utilization
            if util < 0.6:
                recs.append(
                    f"Low utilization ({util:.1%}). Consider reducing die size "
                    f"or adding more logic to improve area efficiency."
                )
            elif util > 0.8:
                recs.append(
                    f"High utilization ({util:.1%}). Consider increasing die size "
                    f"or optimizing logic to reduce congestion."
                )
            
            ar = plan.recommended.aspect_ratio
            if ar > 1.4:
                recs.append(
                    f"Tall aspect ratio ({ar:.2f}). May cause routing congestion "
                    f"on vertical layers. Consider more square die."
                )
            elif ar < 0.9:
                recs.append(
                    f"Wide aspect ratio ({ar:.2f}). May cause routing congestion "
                    f"on horizontal layers. Consider more square die."
                )
        
        if plan.budget.macro_percentage > 40:
            recs.append(
                f"High macro content ({plan.budget.macro_percentage:.1f}%). "
                f"Ensure adequate routing channels between macros."
            )
        
        if plan.io_count > 300:
            recs.append(
                f"High I/O count ({plan.io_count}). Consider flip-chip packaging "
                f"or multi-row I/O ring to reduce die perimeter."
            )
        
        return recs
    
    def _generate_warnings(self, plan: AreaPlan) -> list[str]:
        """Generate warnings for potential issues."""
        warnings = []
        
        if plan.gate_count > 10_000_000:
            warnings.append(
                f"Very large design ({plan.gate_count:,} gates). "
                f"Consider hierarchical partitioning for parallel P&R."
            )
        
        if plan.budget.macro_area_um2 > 1_000_000:
            warnings.append(
                f"Large macro area ({plan.budget.macro_area_um2/1e6:.2f} mm2). "
                f"Verify macro placement does not create routing bottlenecks."
            )
        
        if plan.recommended and plan.recommended.area_mm2 > 100:
            warnings.append(
                f"Large die area ({plan.recommended.area_mm2:.1f} mm2). "
                f"Yield may be impacted. Consider chiplet or multi-die approach."
            )
        
        return warnings
    
    def _generate_summary(self, plan: AreaPlan) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Area Plan for {plan.design_name}",
            "=" * 60,
            "",
            "Design Metrics:",
            f"  Gate count: {plan.gate_count:,}",
            f"  Macro count: {plan.macro_count}",
            f"  I/O count: {plan.io_count}",
            "",
            "Area Budget:",
            f"  Logic area: {plan.budget.logic_area_um2/1e6:.2f} mm2 ({plan.budget.logic_percentage:.1f}%)",
            f"  Macro area: {plan.budget.macro_area_um2/1e6:.2f} mm2 ({plan.budget.macro_percentage:.1f}%)",
            f"  Routing area: {plan.budget.routing_area_um2/1e6:.2f} mm2 ({plan.budget.routing_percentage:.1f}%)",
            f"  Total core: {plan.budget.total_core_area_um2/1e6:.2f} mm2",
            f"  Total die: {plan.budget.total_die_area_um2/1e6:.2f} mm2",
            "",
        ]
        
        if plan.candidates:
            lines.append("Die Size Candidates:")
            for i, c in enumerate(plan.candidates, 1):
                marker = " ★" if c == plan.recommended else ""
                lines.append(
                    f"  {i}. {c.width_um:.0f} x {c.height_um:.0f} um "
                    f"({c.area_mm2:.2f} mm2, util={c.utilization:.1%}, AR={c.aspect_ratio:.2f}){marker}"
                )
                if c.notes:
                    lines.append(f"     Notes: {', '.join(c.notes)}")
            lines.append("")
        
        if plan.recommended:
            lines.extend([
                "Recommended Die Size:",
                f"  Width: {plan.recommended.width_um:.0f} um",
                f"  Height: {plan.recommended.height_um:.0f} um",
                f"  Core: {plan.recommended.core_width_um:.0f} x {plan.recommended.core_height_um:.0f} um",
                f"  Area: {plan.recommended.area_mm2:.2f} mm2",
                f"  Utilization: {plan.recommended.utilization:.1%}",
                f"  Aspect ratio: {plan.recommended.aspect_ratio:.2f}",
                "",
            ])
        
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
