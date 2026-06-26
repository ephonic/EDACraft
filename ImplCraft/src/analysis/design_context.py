"""
DesignContext — persistent design analysis state.

Captures RTL analysis results including:
- Module hierarchy with signal flow
- Interconnect relationships
- Data path information
- Macro placement constraints
- Timing criticality

Serializable to JSON/YAML for persistence across sessions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any
import yaml


class SignalFlowDirection(Enum):
    """Signal flow direction between modules."""
    FORWARD = "forward"      # A -> B
    BACKWARD = "backward"    # B -> A
    BIDIRECTIONAL = "bidirectional"
    UNKNOWN = "unknown"


class ModuleRole(Enum):
    """Role of a module in the design."""
    CONTROLLER = "controller"  # Control logic (FSM, arbiter)
    DATAPATH = "datapath"      # Data processing (ALU, multiplier)
    MEMORY = "memory"          # Memory interface (SRAM, cache)
    IO = "io"                  # I/O interface (UART, SPI, PCIe)
    CLOCK = "clock"            # Clock generation (PLL, divider)
    POWER = "power"            # Power management (LDO, PMU)
    MIXED = "mixed"            # Mixed function
    UNKNOWN = "unknown"


class InterconnectType(Enum):
    """Type of interconnect between modules."""
    BUS = "bus"              # Shared bus (AXI, AHB)
    POINT_TO_POINT = "p2p"   # Direct connection
    FIFO = "fifo"            # FIFO interface
    REGISTER = "register"    # Register interface
    INTERRUPT = "interrupt"  # Interrupt signal
    CLOCK = "clock"          # Clock distribution
    POWER = "power"          # Power domain boundary


@dataclass
class SignalInfo:
    """Signal information."""
    name: str
    width: int = 1
    direction: str = "input"  # input, output, inout
    is_clock: bool = False
    is_reset: bool = False
    is_bus: bool = False
    bus_name: str = ""
    driver: str = ""  # Module that drives this signal
    receivers: list[str] = field(default_factory=list)  # Modules that receive


@dataclass
class Interconnect:
    """Interconnect between two modules."""
    from_module: str
    to_module: str
    signal_count: int = 0
    signal_width: int = 0
    interconnect_type: InterconnectType = InterconnectType.POINT_TO_POINT
    is_critical: bool = False
    bandwidth_mbps: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "from_module": self.from_module,
            "to_module": self.to_module,
            "signal_count": self.signal_count,
            "signal_width": self.signal_width,
            "interconnect_type": self.interconnect_type.value,
            "is_critical": self.is_critical,
            "bandwidth_mbps": self.bandwidth_mbps,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Interconnect:
        return cls(
            from_module=data["from_module"],
            to_module=data["to_module"],
            signal_count=data.get("signal_count", 0),
            signal_width=data.get("signal_width", 0),
            interconnect_type=InterconnectType(data.get("interconnect_type", "p2p")),
            is_critical=data.get("is_critical", False),
            bandwidth_mbps=data.get("bandwidth_mbps", 0.0),
        )


@dataclass
class ModuleAnalysis:
    """Analysis result for a single module."""
    name: str
    role: ModuleRole = ModuleRole.UNKNOWN
    
    # Hierarchy
    parent: str = ""
    children: list[str] = field(default_factory=list)
    depth: int = 0
    
    # Metrics
    gate_count: int = 0
    area_um2: float = 0.0
    port_count: int = 0
    instance_count: int = 0
    
    # Signals
    input_signals: list[SignalInfo] = field(default_factory=list)
    output_signals: list[SignalInfo] = field(default_factory=list)
    
    # Interconnects
    incoming: list[Interconnect] = field(default_factory=list)
    outgoing: list[Interconnect] = field(default_factory=list)
    
    # Placement hints from RTL
    preferred_region: str = ""  # center, periphery, top, bottom, left, right
    should_harden: bool = False
    harden_reason: str = ""
    
    # Timing
    is_timing_critical: bool = False
    max_delay_ns: float = 0.0
    slack_ns: float = 0.0
    
    # Power
    power_domain: str = "VDD"
    dynamic_power_mw: float = 0.0
    leakage_power_mw: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role.value,
            "parent": self.parent,
            "children": self.children,
            "depth": self.depth,
            "gate_count": self.gate_count,
            "area_um2": self.area_um2,
            "port_count": self.port_count,
            "instance_count": self.instance_count,
            "input_signals": [asdict(s) for s in self.input_signals],
            "output_signals": [asdict(s) for s in self.output_signals],
            "incoming": [ic.to_dict() for ic in self.incoming],
            "outgoing": [ic.to_dict() for ic in self.outgoing],
            "preferred_region": self.preferred_region,
            "should_harden": self.should_harden,
            "harden_reason": self.harden_reason,
            "is_timing_critical": self.is_timing_critical,
            "max_delay_ns": self.max_delay_ns,
            "slack_ns": self.slack_ns,
            "power_domain": self.power_domain,
            "dynamic_power_mw": self.dynamic_power_mw,
            "leakage_power_mw": self.leakage_power_mw,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ModuleAnalysis:
        mod = cls(name=data["name"])
        mod.role = ModuleRole(data.get("role", "unknown"))
        mod.parent = data.get("parent", "")
        mod.children = data.get("children", [])
        mod.depth = data.get("depth", 0)
        mod.gate_count = data.get("gate_count", 0)
        mod.area_um2 = data.get("area_um2", 0.0)
        mod.port_count = data.get("port_count", 0)
        mod.instance_count = data.get("instance_count", 0)
        
        # Signals
        for sig_data in data.get("input_signals", []):
            mod.input_signals.append(SignalInfo(**sig_data))
        for sig_data in data.get("output_signals", []):
            mod.output_signals.append(SignalInfo(**sig_data))
        
        # Interconnects
        for ic_data in data.get("incoming", []):
            mod.incoming.append(Interconnect.from_dict(ic_data))
        for ic_data in data.get("outgoing", []):
            mod.outgoing.append(Interconnect.from_dict(ic_data))
        
        mod.preferred_region = data.get("preferred_region", "")
        mod.should_harden = data.get("should_harden", False)
        mod.harden_reason = data.get("harden_reason", "")
        mod.is_timing_critical = data.get("is_timing_critical", False)
        mod.max_delay_ns = data.get("max_delay_ns", 0.0)
        mod.slack_ns = data.get("slack_ns", 0.0)
        mod.power_domain = data.get("power_domain", "VDD")
        mod.dynamic_power_mw = data.get("dynamic_power_mw", 0.0)
        mod.leakage_power_mw = data.get("leakage_power_mw", 0.0)
        
        return mod


@dataclass
class SignalFlowPath:
    """Signal flow path through multiple modules."""
    name: str
    modules: list[str] = field(default_factory=list)
    total_delay_ns: float = 0.0
    is_critical: bool = False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "modules": self.modules,
            "total_delay_ns": self.total_delay_ns,
            "is_critical": self.is_critical,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> SignalFlowPath:
        return cls(
            name=data["name"],
            modules=data.get("modules", []),
            total_delay_ns=data.get("total_delay_ns", 0.0),
            is_critical=data.get("is_critical", False),
        )


@dataclass
class DesignContext:
    """
    Persistent design analysis context.
    
    Contains all analysis results needed for:
    - Macro placement (block-level and top-level)
    - Harden partitioning
    - Floorplan planning
    - Power mesh planning
    """
    design_name: str = ""
    top_module: str = ""
    
    # Analysis timestamp
    analyzed_at: str = ""
    
    # Module analysis
    modules: dict[str, ModuleAnalysis] = field(default_factory=dict)
    
    # Interconnects (flattened list)
    interconnects: list[Interconnect] = field(default_factory=list)
    
    # Signal flow paths
    signal_flow_paths: list[SignalFlowPath] = field(default_factory=list)
    
    # Design metrics
    total_gates: int = 0
    total_area_um2: float = 0.0
    total_power_mw: float = 0.0
    
    # Macro information
    macros: list[dict[str, Any]] = field(default_factory=list)
    
    # Placement constraints derived from analysis
    placement_constraints: dict[str, Any] = field(default_factory=dict)
    
    # Analysis notes
    notes: list[str] = field(default_factory=list)
    
    def add_module(self, module: ModuleAnalysis):
        """Add a module analysis result."""
        self.modules[module.name] = module
    
    def get_module(self, name: str) -> ModuleAnalysis | None:
        """Get module analysis by name."""
        return self.modules.get(name)
    
    def get_children(self, parent: str) -> list[ModuleAnalysis]:
        """Get all children of a parent module."""
        return [
            self.modules[name]
            for name in self.modules.get(parent, ModuleAnalysis(name=parent)).children
            if name in self.modules
        ]
    
    def get_interconnects(self, module_name: str) -> tuple[list[Interconnect], list[Interconnect]]:
        """Get incoming and outgoing interconnects for a module."""
        incoming = [ic for ic in self.interconnects if ic.to_module == module_name]
        outgoing = [ic for ic in self.interconnects if ic.from_module == module_name]
        return incoming, outgoing
    
    def get_critical_path(self) -> SignalFlowPath | None:
        """Get the most critical signal flow path."""
        if not self.signal_flow_paths:
            return None
        return max(self.signal_flow_paths, key=lambda p: p.total_delay_ns)
    
    def get_modules_by_role(self, role: ModuleRole) -> list[ModuleAnalysis]:
        """Get all modules with a specific role."""
        return [m for m in self.modules.values() if m.role == role]
    
    def get_harden_candidates(self) -> list[ModuleAnalysis]:
        """Get all modules marked for hardening."""
        return [m for m in self.modules.values() if m.should_harden]
    
    def save(self, path: str | Path):
        """Save design context to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "design_name": self.design_name,
            "top_module": self.top_module,
            "analyzed_at": self.analyzed_at,
            "modules": {name: mod.to_dict() for name, mod in self.modules.items()},
            "interconnects": [ic.to_dict() for ic in self.interconnects],
            "signal_flow_paths": [path.to_dict() for path in self.signal_flow_paths],
            "total_gates": self.total_gates,
            "total_area_um2": self.total_area_um2,
            "total_power_mw": self.total_power_mw,
            "macros": self.macros,
            "placement_constraints": self.placement_constraints,
            "notes": self.notes,
        }
        
        if path.suffix in [".yaml", ".yml"]:
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path: str | Path) -> DesignContext:
        """Load design context from JSON/YAML file."""
        path = Path(path)
        
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            with open(path) as f:
                data = json.load(f)
        
        ctx = cls(
            design_name=data.get("design_name", ""),
            top_module=data.get("top_module", ""),
            analyzed_at=data.get("analyzed_at", ""),
            total_gates=data.get("total_gates", 0),
            total_area_um2=data.get("total_area_um2", 0.0),
            total_power_mw=data.get("total_power_mw", 0.0),
            macros=data.get("macros", []),
            placement_constraints=data.get("placement_constraints", {}),
            notes=data.get("notes", []),
        )
        
        # Load modules
        for name, mod_data in data.get("modules", {}).items():
            ctx.modules[name] = ModuleAnalysis.from_dict(mod_data)
        
        # Load interconnects
        for ic_data in data.get("interconnects", []):
            ctx.interconnects.append(Interconnect.from_dict(ic_data))
        
        # Load signal flow paths
        for path_data in data.get("signal_flow_paths", []):
            ctx.signal_flow_paths.append(SignalFlowPath.from_dict(path_data))
        
        return ctx
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Design Context: {self.design_name}",
            f"Top module: {self.top_module}",
            f"Analyzed at: {self.analyzed_at}",
            "",
            "Metrics:",
            f"  Total gates: {self.total_gates:,}",
            f"  Total area: {self.total_area_um2:,.0f} um²",
            f"  Total power: {self.total_power_mw:.2f} mW",
            f"  Modules: {len(self.modules)}",
            f"  Interconnects: {len(self.interconnects)}",
            f"  Signal flow paths: {len(self.signal_flow_paths)}",
            "",
        ]
        
        # Module roles
        roles = {}
        for mod in self.modules.values():
            role = mod.role.value
            roles[role] = roles.get(role, 0) + 1
        
        if roles:
            lines.append("Module roles:")
            for role, count in sorted(roles.items()):
                lines.append(f"  {role}: {count}")
            lines.append("")
        
        # Harden candidates
        harden = self.get_harden_candidates()
        if harden:
            lines.append(f"Harden candidates ({len(harden)}):")
            for mod in harden[:10]:
                lines.append(f"  {mod.name}: {mod.gate_count:,} gates - {mod.harden_reason}")
            lines.append("")
        
        # Critical paths
        critical = [p for p in self.signal_flow_paths if p.is_critical]
        if critical:
            lines.append(f"Critical paths ({len(critical)}):")
            for path in critical[:5]:
                lines.append(f"  {path.name}: {path.total_delay_ns:.2f} ns")
                lines.append(f"    {' -> '.join(path.modules)}")
            lines.append("")
        
        if self.notes:
            lines.append("Notes:")
            for note in self.notes:
                lines.append(f"  • {note}")
        
        return "\n".join(lines)
