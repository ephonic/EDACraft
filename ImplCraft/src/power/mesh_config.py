"""
Power Mesh Configuration — data structures for power delivery network.

Defines:
- PowerDomain: voltage domain with power/ground nets
- RingConfig: power ring specifications
- StrapConfig: power strap specifications
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PowerDomain:
    """Power domain specification."""
    name: str
    vdd_net: str = "VDD"
    vss_net: str = "VSS"
    voltage: float = 0.9  # Volts
    is_primary: bool = True
    
    # Area allocation
    area_percentage: float = 100.0  # Percentage of chip area for this domain
    
    # Current requirements
    max_current_a: float = 1.0  # Maximum current in Amperes
    dynamic_current_a: float = 0.7  # Dynamic current component
    static_current_a: float = 0.3  # Static/leakage current component
    
    # IR-drop targets
    ir_drop_target_mv: float = 45.0  # Target IR-drop in millivolts (5% of 0.9V)
    ir_drop_percentage: float = 5.0  # IR-drop as percentage of voltage


@dataclass
class RingConfig:
    """Power ring configuration."""
    layer: str = "M8"  # Metal layer
    width_um: float = 4.0  # Ring width in micrometers
    spacing_um: float = 2.0  # Spacing between VDD and VSS rings
    offset_um: float = 0.8  # Offset from core boundary
    
    # Direction-specific settings
    horizontal_layers: list[str] = field(default_factory=lambda: ["M8"])
    vertical_layers: list[str] = field(default_factory=lambda: ["M9"])
    
    # Connection settings
    connect_to_pads: bool = True
    connect_to_straps: bool = True


@dataclass
class StrapConfig:
    """Power strap configuration."""
    layer: str = "M7"  # Metal layer
    width_um: float = 2.0  # Strap width in micrometers
    pitch_um: float = 20.0  # Pitch between straps (center-to-center)
    spacing_um: float = 2.0  # Spacing between VDD and VSS straps
    
    # Direction
    direction: str = "horizontal"  # horizontal or vertical
    
    # Coverage
    start_offset_um: float = 100.0  # Offset from core boundary
    set_to_set_distance_um: float = 200.0  # Distance between strap sets
    
    # Optimization
    optimize_for_ir_drop: bool = True
    max_current_density_a_um: float = 0.001  # A/um


@dataclass
class RailConfig:
    """Standard cell power rail configuration."""
    vdd_rail: str = "VDD"
    vss_rail: str = "VSS"
    layer: str = "M1"  # Typically M1 for standard cells
    width_um: float = 0.1  # Rail width (technology dependent)
    
    # Connection
    connect_to_straps: bool = True
    use_followpins: bool = True


@dataclass
class BlockRingConfig:
    """Power ring around hard macro/block."""
    macro_name: str
    layer: str = "M5"
    width_um: float = 2.0
    spacing_um: float = 1.5
    offset_um: float = 0.5
    
    # Connection to main mesh
    connect_to_core_rings: bool = True
    num_connections: int = 4  # Number of connection points per side
