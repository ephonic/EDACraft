"""
DesignAnalyzer — RTL analysis engine producing DesignContext.

Analyzes RTL to extract:
- Module hierarchy and roles
- Signal flow patterns
- Interconnect relationships
- Data path information
- Macro placement constraints

Usage:
    analyzer = DesignAnalyzer()
    context = analyzer.analyze_rtl(rtl_files, top_module)
    context.save("design_context.json")
"""
from __future__ import annotations

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .design_context import (
    DesignContext,
    ModuleAnalysis,
    ModuleRole,
    Interconnect,
    InterconnectType,
    SignalInfo,
    SignalFlowPath,
)
from .verilog_hierarchy_parser import VerilogHierarchyParser, VerilogModule

logger = logging.getLogger("ic_backend")


class DesignAnalyzer:
    """
    RTL analysis engine that produces DesignContext.
    
    Usage:
        analyzer = DesignAnalyzer()
        context = analyzer.analyze_rtl(
            rtl_files=["top.v", "sub1.v", "sub2.v"],
            top_module="top"
        )
        context.save("design_context.json")
    """
    
    # Role detection patterns
    ROLE_PATTERNS = {
        ModuleRole.CONTROLLER: [
            r"fsm", r"arbiter", r"controller", r"ctrl", r"state",
            r"decode", r"dispatch", r"schedule"
        ],
        ModuleRole.DATAPATH: [
            r"alu", r"multiplier", r"adder", r"shifter", r"datapath",
            r"compute", r"process", r"filter", r"fft", r"dsp"
        ],
        ModuleRole.MEMORY: [
            r"sram", r"cache", r"memory", r"mem", r"rom", r"fifo",
            r"buffer", r"queue", r"store"
        ],
        ModuleRole.IO: [
            r"uart", r"spi", r"i2c", r"pcie", r"usb", r"ethernet",
            r"gpio", r"pad", r"phy", r"interface", r"if_"
        ],
        ModuleRole.CLOCK: [
            r"pll", r"clock", r"clk", r"divider", r"generator",
            r"oscillator"
        ],
        ModuleRole.POWER: [
            r"ldo", r"pmu", r"power", r"regulator", r"voltage",
            r"current", r"battery"
        ],
    }
    
    # Bus detection patterns
    BUS_PATTERNS = [
        r"axi_", r"ahb_", r"apb_", r"wishbone", r"avalon",
        r"pcie_", r"usb_", r"ethernet_"
    ]
    
    def __init__(self):
        self.parser = VerilogHierarchyParser()
    
    def analyze_rtl(
        self,
        rtl_files: list[str | Path],
        top_module: str,
        design_name: str = "",
    ) -> DesignContext:
        """
        Analyze RTL files and produce DesignContext.
        
        Args:
            rtl_files: List of Verilog files to analyze
            top_module: Name of the top-level module
            design_name: Design name (defaults to top_module)
            
        Returns:
            DesignContext with analysis results
        """
        # Parse RTL hierarchy
        hierarchy = self.parser.parse_files(rtl_files)
        
        # Create context
        context = DesignContext(
            design_name=design_name or top_module,
            top_module=top_module,
            analyzed_at=datetime.now().isoformat(),
        )
        
        # Analyze modules
        for module_name, verilog_module in hierarchy.modules.items():
            module_analysis = self._analyze_module(verilog_module, hierarchy)
            context.add_module(module_analysis)
        
        # Build interconnects
        context.interconnects = self._build_interconnects(context, hierarchy)
        
        # Detect signal flow paths
        context.signal_flow_paths = self._detect_signal_flow_paths(context)
        
        # Calculate totals
        self._calculate_totals(context)
        
        # Detect macros
        context.macros = self._detect_macros(context, hierarchy)
        
        # Add notes
        self._add_analysis_notes(context)
        
        return context
    
    def _analyze_module(
        self,
        verilog_module: VerilogModule,
        hierarchy: Any,
    ) -> ModuleAnalysis:
        """Analyze a single module."""
        module = ModuleAnalysis(name=verilog_module.name)
        
        # Detect role
        module.role = self._detect_role(verilog_module.name)
        
        # Basic metrics
        module.port_count = len(verilog_module.ports)
        module.instance_count = len(verilog_module.instances)
        
        # Extract signals
        for port in verilog_module.ports:
            sig = SignalInfo(
                name=port.name,
                width=port.bit_count,
                direction=port.direction,
                is_clock=self._is_clock(port.name),
                is_reset=self._is_reset(port.name),
                is_bus=self._is_bus(port.name),
                driver="",  # Will be filled later
                receivers=[],
            )
            
            if port.direction == "input":
                module.input_signals.append(sig)
            elif port.direction == "output":
                module.output_signals.append(sig)
        
        # Determine hierarchy
        module.children = [inst.module_name for inst in verilog_module.instances]
        
        # Placement hints based on role
        module.preferred_region = self._suggest_region(module.role)
        
        # Hardening decision
        module.should_harden, module.harden_reason = self._should_harden(module, verilog_module)
        
        return module
    
    def _detect_role(self, module_name: str) -> ModuleRole:
        """Detect module role from name."""
        name_lower = module_name.lower()
        
        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower):
                    return role
        
        return ModuleRole.UNKNOWN
    
    def _is_clock(self, signal_name: str) -> bool:
        """Check if signal is a clock."""
        return bool(re.search(r"clk|clock", signal_name, re.I))
    
    def _is_reset(self, signal_name: str) -> bool:
        """Check if signal is a reset."""
        return bool(re.search(r"rst|reset", signal_name, re.I))
    
    def _is_bus(self, signal_name: str) -> bool:
        """Check if signal is part of a bus."""
        return any(re.search(p, signal_name, re.I) for p in self.BUS_PATTERNS)
    
    def _suggest_region(self, role: ModuleRole) -> str:
        """Suggest placement region based on role."""
        if role == ModuleRole.IO:
            return "periphery"
        elif role == ModuleRole.CLOCK:
            return "periphery"
        elif role == ModuleRole.POWER:
            return "periphery"
        elif role == ModuleRole.MEMORY:
            return "center"
        elif role == ModuleRole.DATAPATH:
            return "center"
        elif role == ModuleRole.CONTROLLER:
            return "center"
        return ""
    
    def _should_harden(
        self,
        module: ModuleAnalysis,
        verilog_module: VerilogModule,
    ) -> tuple[bool, str]:
        """Determine if module should be hardened."""
        # Large modules
        if verilog_module.instance_count > 100:
            return True, f"Large module ({verilog_module.instance_count} instances)"
        
        # Memory controllers
        if module.role == ModuleRole.MEMORY:
            return True, "Memory interface"
        
        # Complex I/O
        if module.role == ModuleRole.IO and module.port_count > 50:
            return True, "Complex I/O interface"
        
        # Clock generation
        if module.role == ModuleRole.CLOCK:
            return True, "Clock generation"
        
        return False, ""
    
    def _build_interconnects(
        self,
        context: DesignContext,
        hierarchy: Any,
    ) -> list[Interconnect]:
        """Build interconnect list from hierarchy."""
        interconnects = []
        
        for parent_name, parent_module in hierarchy.modules.items():
            parent_analysis = context.get_module(parent_name)
            if not parent_analysis:
                continue
            
            for instance in parent_module.instances:
                child_name = instance.module_name
                child_analysis = context.get_module(child_name)
                
                if not child_analysis:
                    continue
                
                # Count signals
                signal_count = len(instance.port_connections)
                signal_width = sum(
                    self._get_signal_width(sig_name, parent_module, child_analysis)
                    for sig_name in instance.port_connections.values()
                )
                
                # Detect interconnect type
                ic_type = self._detect_interconnect_type(
                    instance.port_connections, parent_name, child_name
                )
                
                # Create interconnect
                ic = Interconnect(
                    from_module=parent_name,
                    to_module=child_name,
                    signal_count=signal_count,
                    signal_width=signal_width,
                    interconnect_type=ic_type,
                )
                
                # Update module analysis
                parent_analysis.outgoing.append(ic)
                child_analysis.incoming.append(ic)
                
                interconnects.append(ic)
        
        return interconnects
    
    def _get_signal_width(
        self,
        signal_name: str,
        parent_module: VerilogModule,
        child_analysis: ModuleAnalysis,
    ) -> int:
        """Get signal width from module ports."""
        # Check parent outputs
        for sig in parent_analysis.output_signals if (parent_analysis := child_analysis) else []:
            if sig.name == signal_name:
                return sig.width
        
        # Check child inputs
        for sig in child_analysis.input_signals:
            if sig.name == signal_name:
                return sig.width
        
        return 1  # Default
    
    def _detect_interconnect_type(
        self,
        connections: dict[str, str],
        parent_name: str,
        child_name: str,
    ) -> InterconnectType:
        """Detect interconnect type from connections."""
        # Check for bus signals
        for sig_name in connections.values():
            if self._is_bus(sig_name):
                return InterconnectType.BUS
        
        # Check for FIFO-like patterns
        for sig_name in connections.values():
            if re.search(r"fifo|queue|buffer", sig_name, re.I):
                return InterconnectType.FIFO
        
        # Check for register-like patterns
        for sig_name in connections.values():
            if re.search(r"reg|addr|data", sig_name, re.I):
                return InterconnectType.REGISTER
        
        # Check for clock
        for sig_name in connections.values():
            if self._is_clock(sig_name):
                return InterconnectType.CLOCK
        
        return InterconnectType.POINT_TO_POINT
    
    def _detect_signal_flow_paths(self, context: DesignContext) -> list[SignalFlowPath]:
        """Detect signal flow paths through the design."""
        paths = []
        
        # Find paths from inputs to outputs
        for module in context.modules.values():
            if not module.input_signals:
                continue
            
            # Trace forward through interconnects
            path = self._trace_forward_path(module.name, context, [])
            if len(path) > 1:
                flow_path = SignalFlowPath(
                    name=f"path_{module.name}",
                    modules=path,
                    total_delay_ns=len(path) * 0.5,  # Estimate
                    is_critical=len(path) > 3,
                )
                paths.append(flow_path)
        
        return paths
    
    def _trace_forward_path(
        self,
        start_module: str,
        context: DesignContext,
        visited: list[str],
    ) -> list[str]:
        """Trace forward signal flow path."""
        if start_module in visited:
            return visited
        
        visited.append(start_module)
        
        module = context.get_module(start_module)
        if not module:
            return visited
        
        # Follow outgoing interconnects
        for ic in module.outgoing:
            if ic.to_module not in visited:
                visited = self._trace_forward_path(ic.to_module, context, visited)
        
        return visited
    
    def _calculate_totals(self, context: DesignContext):
        """Calculate total design metrics."""
        context.total_gates = sum(m.gate_count for m in context.modules.values())
        context.total_area_um2 = sum(m.area_um2 for m in context.modules.values())
        context.total_power_mw = sum(m.dynamic_power_mw for m in context.modules.values())
    
    def _detect_macros(
        self,
        context: DesignContext,
        hierarchy: Any,
    ) -> list[dict[str, Any]]:
        """Detect hard macros in the design."""
        macros = []
        
        for module in context.modules.values():
            # Memory modules
            if module.role == ModuleRole.MEMORY:
                macros.append({
                    "name": module.name,
                    "type": "sram" if "sram" in module.name.lower() else "memory",
                    "gate_count": module.gate_count,
                    "area_um2": module.area_um2,
                })
            
            # Clock modules
            elif module.role == ModuleRole.CLOCK:
                macros.append({
                    "name": module.name,
                    "type": "pll",
                    "gate_count": module.gate_count,
                    "area_um2": module.area_um2,
                })
            
            # Power modules
            elif module.role == ModuleRole.POWER:
                macros.append({
                    "name": module.name,
                    "type": "ldo",
                    "gate_count": module.gate_count,
                    "area_um2": module.area_um2,
                })
        
        return macros
    
    def _add_analysis_notes(self, context: DesignContext):
        """Add analysis notes."""
        # Check for large modules
        large_modules = [m for m in context.modules.values() if m.gate_count > 100000]
        if large_modules:
            context.notes.append(
                f"Found {len(large_modules)} large modules (>100K gates)"
            )
        
        # Check for complex interconnects
        complex_ics = [ic for ic in context.interconnects if ic.signal_width > 100]
        if complex_ics:
            context.notes.append(
                f"Found {len(complex_ics)} high-bandwidth interconnects (>100 bits)"
            )
        
        # Check for critical paths
        critical_paths = [p for p in context.signal_flow_paths if p.is_critical]
        if critical_paths:
            context.notes.append(
                f"Found {len(critical_paths)} potentially critical signal flow paths"
            )
        
        # Check for harden candidates
        harden_candidates = context.get_harden_candidates()
        if harden_candidates:
            context.notes.append(
                f"Identified {len(harden_candidates)} harden candidates"
            )
