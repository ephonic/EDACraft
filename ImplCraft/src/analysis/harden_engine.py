"""
HardenEngine — signal-flow-aware module hardening engine.

Consumes DesignContext to make intelligent hardening decisions:
- Identify harden candidates based on signal flow
- Generate block interfaces
- Create P&R scripts for hardened blocks
- Optimize for signal flow and routing

Usage:
    engine = HardenEngine()
    plan = engine.create_harden_plan(context)
    engine.generate_scripts(plan, output_dir)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .design_context import DesignContext, ModuleAnalysis, ModuleRole, Interconnect

logger = logging.getLogger("ic_backend")


@dataclass
class BlockInterface:
    """Block interface specification."""
    module_name: str
    input_ports: list[dict[str, Any]] = field(default_factory=list)
    output_ports: list[dict[str, Any]] = field(default_factory=list)
    clock_ports: list[str] = field(default_factory=list)
    reset_ports: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            f"Block Interface: {self.module_name}",
            f"  Input ports: {len(self.input_ports)}",
            f"  Output ports: {len(self.output_ports)}",
            f"  Clock ports: {len(self.clock_ports)}",
            f"  Reset ports: {len(self.reset_ports)}",
        ]
        return "\n".join(lines)


@dataclass
class HardenedBlock:
    """Hardened block specification."""
    name: str
    module_name: str
    role: ModuleRole
    interface: BlockInterface
    
    # Metrics
    gate_count: int = 0
    area_um2: float = 0.0
    port_count: int = 0
    
    # Placement hints
    preferred_region: str = ""
    
    # Dependencies
    depends_on: list[str] = field(default_factory=list)
    depended_by: list[str] = field(default_factory=list)
    
    # Scripts
    synth_script: str = ""
    pr_script: str = ""
    
    def summary(self) -> str:
        lines = [
            f"Hardened Block: {self.name}",
            f"  Module: {self.module_name}",
            f"  Role: {self.role.value}",
            f"  Gates: {self.gate_count:,}",
            f"  Area: {self.area_um2:,.0f} um²",
            f"  Ports: {self.port_count}",
            f"  Depends on: {', '.join(self.depends_on) if self.depends_on else 'none'}",
            f"  Depended by: {', '.join(self.depended_by) if self.depended_by else 'none'}",
            f"  Preferred region: {self.preferred_region or 'any'}",
        ]
        return "\n".join(lines)


@dataclass
class HardenPlan:
    """Hardening plan."""
    blocks: list[HardenedBlock] = field(default_factory=list)
    flow_order: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            "Harden Plan Summary:",
            f"  Hardened blocks: {len(self.blocks)}",
            f"  Flow order: {' -> '.join(self.flow_order)}",
            f"  Recommendations: {len(self.recommendations)}",
            f"  Warnings: {len(self.warnings)}",
            "",
        ]
        
        for block in self.blocks:
            lines.append(block.summary())
            lines.append("")
        
        if self.recommendations:
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")
            lines.append("")
        
        if self.warnings:
            lines.append("Warnings:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
        
        return "\n".join(lines)


class HardenEngine:
    """
    Signal-flow-aware module hardening engine.
    
    Consumes DesignContext to:
    - Identify harden candidates
    - Determine hardening order based on signal flow
    - Generate block interfaces
    - Create P&R scripts
    """
    
    def __init__(self):
        # Hardening thresholds
        self.min_gate_count = 50000  # Minimum gates to consider hardening
        self.max_gate_count = 2000000  # Maximum gates for single block
        self.prefer_memory = True  # Always harden memory modules
        self.prefer_io = True  # Always harden IO modules
        self.prefer_clock = True  # Always harden clock modules
    
    def create_harden_plan(self, context: DesignContext) -> HardenPlan:
        """
        Create hardening plan from design context.
        
        Args:
            context: Design analysis context
            
        Returns:
            HardenPlan with hardened blocks
        """
        plan = HardenPlan()
        
        # Identify harden candidates
        candidates = self._identify_candidates(context)
        
        # Create hardened blocks
        for module in candidates:
            block = self._create_hardened_block(module, context)
            plan.blocks.append(block)
        
        # Determine flow order
        plan.flow_order = self._determine_flow_order(context, plan.blocks)
        
        # Generate recommendations
        plan.recommendations = self._generate_recommendations(context, plan)
        
        # Generate warnings
        plan.warnings = self._generate_warnings(context, plan)
        
        return plan
    
    def generate_scripts(
        self,
        plan: HardenPlan,
        output_dir: str | Path,
        tool: str = "icc2",
    ):
        """
        Generate synthesis and P&R scripts for hardened blocks.
        
        Args:
            plan: Hardening plan
            output_dir: Output directory
            tool: Target tool (icc2, innovus)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for block in plan.blocks:
            block_dir = output_dir / block.name
            block_dir.mkdir(exist_ok=True)
            
            # Generate synthesis script
            synth_script = self._generate_synth_script(block, tool)
            synth_path = block_dir / "synth.tcl"
            synth_path.write_text(synth_script)
            block.synth_script = str(synth_path)
            
            # Generate P&R script
            pr_script = self._generate_pr_script(block, tool)
            pr_path = block_dir / "pr.tcl"
            pr_path.write_text(pr_script)
            block.pr_script = str(pr_path)
            
            # Generate block interface file
            interface_path = block_dir / "interface.txt"
            interface_path.write_text(block.interface.summary())
        
        # Generate flow order script
        flow_script = self._generate_flow_script(plan)
        flow_path = output_dir / "flow_order.tcl"
        flow_path.write_text(flow_script)
        
        logger.info(f"Generated scripts for {len(plan.blocks)} blocks in {output_dir}")
    
    def _identify_candidates(self, context: DesignContext) -> list[ModuleAnalysis]:
        """Identify modules that should be hardened."""
        candidates = []
        
        for module in context.modules.values():
            should_harden = False
            reason = ""
            
            # Memory modules
            if self.prefer_memory and module.role == ModuleRole.MEMORY:
                should_harden = True
                reason = "Memory module"
            
            # IO modules
            elif self.prefer_io and module.role == ModuleRole.IO:
                should_harden = True
                reason = "IO module"
            
            # Clock modules
            elif self.prefer_clock and module.role == ModuleRole.CLOCK:
                should_harden = True
                reason = "Clock module"
            
            # Large modules
            elif module.gate_count >= self.min_gate_count:
                should_harden = True
                reason = f"Large module ({module.gate_count:,} gates)"
            
            # Modules marked for hardening
            elif module.should_harden:
                should_harden = True
                reason = module.harden_reason
            
            if should_harden:
                candidates.append(module)
                logger.debug(f"Hardening {module.name}: {reason}")
        
        return candidates
    
    def _create_hardened_block(
        self,
        module: ModuleAnalysis,
        context: DesignContext,
    ) -> HardenedBlock:
        """Create hardened block from module analysis."""
        # Create interface
        interface = self._create_interface(module)
        
        # Get dependencies from context interconnects
        depends_on = [
            ic.from_module for ic in context.interconnects
            if ic.to_module == module.name
        ]
        depended_by = [
            ic.to_module for ic in context.interconnects
            if ic.from_module == module.name
        ]
        
        block = HardenedBlock(
            name=f"{module.name}_block",
            module_name=module.name,
            role=module.role,
            interface=interface,
            gate_count=module.gate_count,
            area_um2=module.area_um2,
            port_count=module.port_count,
            preferred_region=module.preferred_region,
            depends_on=depends_on,
            depended_by=depended_by,
        )
        
        return block
    
    def _create_interface(self, module: ModuleAnalysis) -> BlockInterface:
        """Create block interface from module analysis."""
        interface = BlockInterface(module_name=module.name)
        
        # Input ports
        for sig in module.input_signals:
            port = {
                "name": sig.name,
                "width": sig.width,
                "direction": "input",
                "is_clock": sig.is_clock,
                "is_reset": sig.is_reset,
            }
            interface.input_ports.append(port)
            
            if sig.is_clock:
                interface.clock_ports.append(sig.name)
            elif sig.is_reset:
                interface.reset_ports.append(sig.name)
        
        # Output ports
        for sig in module.output_signals:
            port = {
                "name": sig.name,
                "width": sig.width,
                "direction": "output",
                "is_clock": sig.is_clock,
                "is_reset": sig.is_reset,
            }
            interface.output_ports.append(port)
        
        return interface
    
    def _determine_flow_order(
        self,
        context: DesignContext,
        blocks: list[HardenedBlock],
    ) -> list[str]:
        """Determine hardening order based on signal flow."""
        # Topological sort based on dependencies
        # Blocks with no dependencies first, then blocks that depend on them
        
        block_map = {b.module_name: b for b in blocks}
        ordered = []
        visited = set()
        in_stack = set()  # Track nodes in current DFS path to detect cycles
        
        def visit(name: str):
            if name in visited or name not in block_map:
                return
            if name in in_stack:
                # Cycle detected, skip this dependency
                return
            
            in_stack.add(name)
            block = block_map[name]
            
            # Visit dependencies first
            for dep in block.depends_on:
                visit(dep)
            
            in_stack.discard(name)
            visited.add(name)
            ordered.append(name)
        
        # Visit all blocks
        for block in blocks:
            visit(block.module_name)
        
        return ordered
    
    def _generate_recommendations(
        self,
        context: DesignContext,
        plan: HardenPlan,
    ) -> list[str]:
        """Generate hardening recommendations."""
        recommendations = []
        
        # Check for very large blocks
        large_blocks = [b for b in plan.blocks if b.gate_count > self.max_gate_count]
        if large_blocks:
            for block in large_blocks:
                recommendations.append(
                    f"Block {block.name} is very large ({block.gate_count:,} gates). "
                    f"Consider splitting into smaller blocks."
                )
        
        # Check for high interconnect density
        for block in plan.blocks:
            total_connections = len(block.depends_on) + len(block.depended_by)
            if total_connections > 20:
                recommendations.append(
                    f"Block {block.name} has high interconnect density ({total_connections} connections). "
                    f"Consider optimizing interfaces."
                )
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan):
            recommendations.append(
                "Circular dependencies detected in hardening flow. "
                "Consider restructuring module hierarchy."
            )
        
        return recommendations
    
    def _generate_warnings(
        self,
        context: DesignContext,
        plan: HardenPlan,
    ) -> list[str]:
        """Generate hardening warnings."""
        warnings = []
        
        # Check for blocks with no connections
        isolated_blocks = [
            b for b in plan.blocks
            if not b.depends_on and not b.depended_by
        ]
        if isolated_blocks:
            for block in isolated_blocks:
                warnings.append(
                    f"Block {block.name} has no connections. "
                    f"Verify this is intentional."
                )
        
        # Check for timing-critical paths crossing block boundaries
        for path in context.signal_flow_paths:
            if path.is_critical:
                # Check if path crosses multiple hardened blocks
                blocks_in_path = [
                    b for b in plan.blocks
                    if b.module_name in path.modules
                ]
                if len(blocks_in_path) > 1:
                    warnings.append(
                        f"Critical path {path.name} crosses {len(blocks_in_path)} hardened blocks. "
                        f"Consider timing budget allocation."
                    )
        
        return warnings
    
    def _has_circular_dependencies(self, plan: HardenPlan) -> bool:
        """Check for circular dependencies."""
        # Simple cycle detection using DFS
        block_map = {b.module_name: b for b in plan.blocks}
        visited = set()
        rec_stack = set()
        
        def has_cycle(name: str) -> bool:
            visited.add(name)
            rec_stack.add(name)
            
            if name in block_map:
                block = block_map[name]
                for dep in block.depended_by:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(name)
            return False
        
        for block in plan.blocks:
            if block.module_name not in visited:
                if has_cycle(block.module_name):
                    return True
        
        return False
    
    def _generate_synth_script(self, block: HardenedBlock, tool: str) -> str:
        """Generate synthesis script for block."""
        lines = [
            f"# Synthesis script for {block.name}",
            f"# Generated by HardenEngine",
            "",
        ]
        
        if tool == "icc2":
            lines.extend([
                "# Read design",
                f"read_verilog {block.module_name}.v",
                f"current_design {block.module_name}",
                "",
                "# Constraints",
                f"source {block.module_name}.sdc",
                "",
                "# Compile",
                "compile_ultra",
                "",
                "# Reports",
                "report_timing > timing.rpt",
                "report_area > area.rpt",
                "report_power > power.rpt",
                "",
                "# Write outputs",
                f"write -format verilog -output {block.module_name}_netlist.v",
                f"write -format db -output {block.module_name}.db",
            ])
        else:  # innovus
            lines.extend([
                "# Read design",
                f"read_verilog {block.module_name}.v",
                "",
                "# Constraints",
                f"source {block.module_name}.sdc",
                "",
                "# Synthesis",
                "syn_generic",
                "syn_map",
                "syn_opt",
                "",
                "# Reports",
                "report_timing > timing.rpt",
                "report_area > area.rpt",
                "report_power > power.rpt",
                "",
                "# Write outputs",
                f"write_hdl > {block.module_name}_netlist.v",
            ])
        
        return "\n".join(lines)
    
    def _generate_pr_script(self, block: HardenedBlock, tool: str) -> str:
        """Generate P&R script for block."""
        lines = [
            f"# P&R script for {block.name}",
            f"# Generated by HardenEngine",
            "",
        ]
        
        if tool == "icc2":
            lines.extend([
                "# Read design",
                f"read_lib {block.module_name}.lib",
                f"read_verilog {block.module_name}_netlist.v",
                "",
                "# Floorplan",
                "create_floorplan -core_utilization 0.7",
                "",
                "# Placement",
                "place_opt",
                "",
                "# CTS",
                "clock_opt",
                "",
                "# Routing",
                "route_opt",
                "",
                "# Write outputs",
                f"write_gds {block.module_name}.gds",
                f"write_verilog -include pg {block.module_name}_pr.v",
            ])
        else:  # innovus
            lines.extend([
                "# Read design",
                f"read_lib {block.module_name}.lib",
                f"read_verilog {block.module_name}_netlist.v",
                "",
                "# Floorplan",
                "floorPlan -coreUtilization 0.7",
                "",
                "# Placement",
                "place_opt_design",
                "",
                "# CTS",
                "clockOptDesign",
                "",
                "# Routing",
                "routeDesign",
                "",
                "# Write outputs",
                f"streamOut {block.module_name}.gds",
                f"saveNetlist {block.module_name}_pr.v",
            ])
        
        return "\n".join(lines)
    
    def _generate_flow_script(self, plan: HardenPlan) -> str:
        """Generate flow order script."""
        lines = [
            "# Hardening flow order",
            "# Generated by HardenEngine",
            "",
            "# Execute blocks in this order:",
        ]
        
        for i, module_name in enumerate(plan.flow_order, 1):
            lines.append(f"# {i}. {module_name}")
        
        lines.extend([
            "",
            "# Run synthesis for each block:",
        ])
        
        for module_name in plan.flow_order:
            lines.append(f"# cd {module_name}_block && dc_shell -f synth.tcl")
        
        lines.extend([
            "",
            "# Run P&R for each block:",
        ])
        
        for module_name in plan.flow_order:
            lines.append(f"# cd {module_name}_block && icc2_shell -f pr.tcl")
        
        return "\n".join(lines)
