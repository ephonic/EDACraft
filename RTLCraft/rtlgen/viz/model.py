"""Data models for rtlgen visualizer."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class VizPort:
    """A port on a module instance."""
    name: str
    direction: str = "input"  # 'input', 'output', 'inout'
    width: int = 1
    port_type: str = "wire"   # 'wire', 'reg', 'clock', 'reset'


@dataclass
class VizModule:
    """A module instance in the visualization graph."""
    name: str = ""                    # Module type name (e.g. "SystolicArray")
    instance_name: str = ""           # Instance name (e.g. "systolic")
    ports: List[VizPort] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0
    width: float = 140.0
    height: float = 100.0


@dataclass
class VizSignal:
    """A signal/connection between two module ports."""
    name: str = ""
    src_module: str = ""      # Source instance name
    src_port: str = ""        # Source port name
    dst_module: str = ""      # Destination instance name
    dst_port: str = ""        # Destination port name
    width: int = 1
    signal_type: str = "wire"  # 'wire', 'reg', 'axi', 'clock', 'reset'


@dataclass
class VizGraph:
    """A visualization graph containing modules and signals."""
    name: str = ""
    modules: List[VizModule] = field(default_factory=list)
    signals: List[VizSignal] = field(default_factory=list)

    def get_module(self, instance_name: str) -> Optional[VizModule]:
        for m in self.modules:
            if m.instance_name == instance_name:
                return m
        return None
