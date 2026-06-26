"""
Pad Planner — provides interfaces for I/O, PG pad, and bump planning.

Design philosophy:
- Provide atomic operations and calculations
- Leave high-level decisions to AI agents
- Composable interfaces for flexible workflows

Key interfaces:
1. IOGroupingAgent — suggest I/O groupings (agent decides)
2. PGPadCalculator — calculate PG pad requirements
3. BumpPlanner — plan flip-chip bump arrays
4. PadPlacer — low-level placement operations

Usage:
    planner = PadPlanner()
    
    # Agent decides grouping strategy
    groups = planner.io_agent.suggest_groups(signals, strategy="functional")
    
    # Calculate PG requirements
    pg_info = planner.pg_calculator.calculate(current_density, voltage_domains)
    
    # Place pads
    placements = planner.placer.place_io_pads(groups, die_area)
    planner.placer.place_pg_pads(pg_info, die_area)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Dict, Optional
import math

logger = logging.getLogger("ic_backend")


class IOSignalType(Enum):
    """I/O signal types for grouping."""
    DIGITAL_INPUT = "digital_input"
    DIGITAL_OUTPUT = "digital_output"
    DIGITAL_BIDIR = "digital_bidir"
    ANALOG_INPUT = "analog_input"
    ANALOG_OUTPUT = "analog_output"
    DIFFERENTIAL = "differential"
    CLOCK = "clock"
    RESET = "reset"
    POWER = "power"
    GROUND = "ground"


class GroupingStrategy(Enum):
    """I/O grouping strategies."""
    FUNCTIONAL = "functional"      # Group by function (UART, SPI, etc.)
    SIGNAL_TYPE = "signal_type"    # Group by signal type
    TIMING = "timing"              # Group by timing domain
    PHYSICAL = "physical"          # Group by physical proximity
    MIXED = "mixed"                # Mixed strategy


@dataclass
class IOSignal:
    """I/O signal specification."""
    name: str
    signal_type: IOSignalType
    width: int = 1
    voltage_domain: str = "VDDIO"
    timing_group: str = ""
    function_group: str = ""
    
    # Placement hints (optional)
    preferred_side: str = ""  # top, bottom, left, right
    preferred_position: float = 0.0  # 0.0-1.0 along side


@dataclass
class IOGroup:
    """Group of related I/O signals."""
    name: str
    signals: List[IOSignal] = field(default_factory=list)
    voltage_domain: str = "VDDIO"
    
    # Placement
    side: str = ""  # top, bottom, left, right
    start_position: float = 0.0
    
    @property
    def total_width(self) -> int:
        return sum(s.width for s in self.signals)
    
    @property
    def signal_count(self) -> int:
        return len(self.signals)


@dataclass
class PadPlacement:
    """Single pad placement."""
    name: str
    x_um: float
    y_um: float
    width_um: float
    height_um: float
    pad_type: str  # io, power, ground, bump
    signal_name: str = ""
    voltage_domain: str = ""
    
    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x_um, self.y_um, 
                self.x_um + self.width_um, 
                self.y_um + self.height_um)


@dataclass
class PGPadInfo:
    """Power/Ground pad requirements."""
    voltage_domain: str
    vdd_current_ma: float
    vss_current_ma: float
    current_density_a_per_pad: float = 0.05  # 50mA per pad typical
    
    vdd_pad_count: int = 0
    vss_pad_count: int = 0
    
    def calculate(self):
        """Calculate required pad counts."""
        self.vdd_pad_count = math.ceil(
            self.vdd_current_ma / 1000.0 / self.current_density_a_per_pad
        )
        self.vss_pad_count = math.ceil(
            self.vss_current_ma / 1000.0 / self.current_density_a_per_pad
        )


@dataclass
class BumpArraySpec:
    """Flip-chip bump array specification."""
    rows: int
    cols: int
    pitch_um: float
    bump_diameter_um: float = 80.0
    
    # Array position
    center_x_um: float = 0.0
    center_y_um: float = 0.0
    
    @property
    def total_bumps(self) -> int:
        return self.rows * self.cols
    
    @property
    def array_width_um(self) -> float:
        return (self.cols - 1) * self.pitch_um if self.cols > 1 else 0
    
    @property
    def array_height_um(self) -> float:
        return (self.rows - 1) * self.pitch_um if self.rows > 1 else 0


class IOGroupingAgent:
    """
    I/O grouping agent — provides grouping suggestions.
    
    This is an interface for AI agents to call. The agent decides
    which strategy to use and how to apply suggestions.
    """
    
    def suggest_groups(
        self,
        signals: List[IOSignal],
        strategy: GroupingStrategy = GroupingStrategy.FUNCTIONAL,
        max_group_size: int = 16,
    ) -> List[IOGroup]:
        """
        Suggest I/O groupings based on strategy.
        
        Args:
            signals: List of I/O signals
            strategy: Grouping strategy to use
            max_group_size: Maximum signals per group
            
        Returns:
            List of suggested groups (agent can modify)
        """
        if strategy == GroupingStrategy.FUNCTIONAL:
            return self._group_by_function(signals, max_group_size)
        elif strategy == GroupingStrategy.SIGNAL_TYPE:
            return self._group_by_signal_type(signals, max_group_size)
        elif strategy == GroupingStrategy.TIMING:
            return self._group_by_timing(signals, max_group_size)
        else:
            return self._group_by_signal_type(signals, max_group_size)
    
    def _group_by_function(
        self,
        signals: List[IOSignal],
        max_size: int,
    ) -> List[IOGroup]:
        """Group signals by function."""
        groups_dict: Dict[str, List[IOSignal]] = {}
        
        for sig in signals:
            func = sig.function_group or "ungrouped"
            if func not in groups_dict:
                groups_dict[func] = []
            groups_dict[func].append(sig)
        
        groups = []
        for func_name, sigs in groups_dict.items():
            # Split if too large
            for i in range(0, len(sigs), max_size):
                chunk = sigs[i:i+max_size]
                group = IOGroup(
                    name=f"{func_name}_{i//max_size}" if i > 0 else func_name,
                    signals=chunk,
                    voltage_domain=chunk[0].voltage_domain if chunk else "VDDIO",
                )
                groups.append(group)
        
        return groups
    
    def _group_by_signal_type(
        self,
        signals: List[IOSignal],
        max_size: int,
    ) -> List[IOGroup]:
        """Group signals by type."""
        groups_dict: Dict[str, List[IOSignal]] = {}
        
        for sig in signals:
            stype = sig.signal_type.value
            if stype not in groups_dict:
                groups_dict[stype] = []
            groups_dict[stype].append(sig)
        
        groups = []
        for type_name, sigs in groups_dict.items():
            for i in range(0, len(sigs), max_size):
                chunk = sigs[i:i+max_size]
                group = IOGroup(
                    name=f"{type_name}_{i//max_size}" if i > 0 else type_name,
                    signals=chunk,
                )
                groups.append(group)
        
        return groups
    
    def _group_by_timing(
        self,
        signals: List[IOSignal],
        max_size: int,
    ) -> List[IOGroup]:
        """Group signals by timing domain."""
        groups_dict: Dict[str, List[IOSignal]] = {}
        
        for sig in signals:
            timing = sig.timing_group or "default"
            if timing not in groups_dict:
                groups_dict[timing] = []
            groups_dict[timing].append(sig)
        
        groups = []
        for timing_name, sigs in groups_dict.items():
            for i in range(0, len(sigs), max_size):
                chunk = sigs[i:i+max_size]
                group = IOGroup(
                    name=f"{timing_name}_{i//max_size}" if i > 0 else timing_name,
                    signals=chunk,
                )
                groups.append(group)
        
        return groups


class PGPadCalculator:
    """
    Calculate Power/Ground pad requirements.
    
    Provides calculations for agents to use in placement decisions.
    """
    
    def calculate(
        self,
        voltage_domains: Dict[str, Dict[str, float]],
        current_density_a_per_pad: float = 0.05,
    ) -> List[PGPadInfo]:
        """
        Calculate PG pad requirements for all voltage domains.
        
        Args:
            voltage_domains: Dict of {domain: {vdd_current_ma, vss_current_ma}}
            current_density_a_per_pad: Current capacity per pad
            
        Returns:
            List of PGPadInfo for each domain
        """
        results = []
        
        for domain, currents in voltage_domains.items():
            info = PGPadInfo(
                voltage_domain=domain,
                vdd_current_ma=currents.get("vdd_current_ma", 0),
                vss_current_ma=currents.get("vss_current_ma", 0),
                current_density_a_per_pad=current_density_a_per_pad,
            )
            info.calculate()
            results.append(info)
        
        return results
    
    def distribute_uniformly(
        self,
        pg_info: PGPadInfo,
        die_perimeter_um: float,
        io_pad_count: int,
    ) -> List[Dict[str, float]]:
        """
        Suggest uniform distribution of PG pads around die perimeter.
        
        Args:
            pg_info: PG pad requirements
            die_perimeter_um: Total die perimeter
            io_pad_count: Number of I/O pads
            
        Returns:
            List of suggested positions (agent can adjust)
        """
        total_pg = pg_info.vdd_pad_count + pg_info.vss_pad_count
        total_pads = total_pg + io_pad_count
        
        if total_pads == 0:
            return []
        
        spacing = die_perimeter_um / total_pads
        positions = []
        
        # Alternate VDD/VSS for better decoupling
        for i in range(total_pg):
            pos = (i * spacing + spacing / 2) % die_perimeter_um
            pad_type = "vdd" if i % 2 == 0 else "vss"
            positions.append({
                "position_um": pos,
                "type": pad_type,
                "domain": pg_info.voltage_domain,
            })
        
        return positions


class BumpPlanner:
    """
    Plan flip-chip bump arrays.
    
    Provides interfaces for agents to design bump layouts.
    """
    
    def calculate_array_size(
        self,
        total_signals: int,
        total_pg_pads: int,
        pitch_um: float = 150.0,
        utilization: float = 0.7,
    ) -> BumpArraySpec:
        """
        Calculate bump array dimensions.
        
        Args:
            total_signals: Total signal bumps needed
            total_pg_pads: Total power/ground bumps
            pitch_um: Bump pitch
            utilization: Target array utilization
            
        Returns:
            BumpArraySpec with suggested dimensions
        """
        total_bumps = total_signals + total_pg_pads
        target_bumps = total_bumps / utilization
        
        # Calculate square array
        side = math.ceil(math.sqrt(target_bumps))
        
        return BumpArraySpec(
            rows=side,
            cols=side,
            pitch_um=pitch_um,
        )
    
    def assign_signals_to_bumps(
        self,
        signals: List[IOSignal],
        array: BumpArraySpec,
        strategy: str = "center_out",
    ) -> Dict[str, tuple[int, int]]:
        """
        Assign signals to bump positions.
        
        Args:
            signals: List of signals to assign
            array: Bump array specification
            strategy: Assignment strategy (center_out, edge_in, etc.)
            
        Returns:
            Dict of {signal_name: (row, col)}
        """
        assignments = {}
        
        # Simple center-out strategy
        center_row = array.rows // 2
        center_col = array.cols // 2
        
        # Sort by priority (clock/reset first, then others)
        sorted_signals = sorted(
            signals,
            key=lambda s: (
                0 if s.signal_type in [IOSignalType.CLOCK, IOSignalType.RESET] else 1,
                s.name
            )
        )
        
        # Assign in spiral pattern from center
        positions = self._generate_spiral_positions(
            array.rows, array.cols, len(sorted_signals)
        )
        
        for sig, (row, col) in zip(sorted_signals, positions):
            assignments[sig.name] = (row, col)
        
        return assignments
    
    def _generate_spiral_positions(
        self,
        rows: int,
        cols: int,
        count: int,
    ) -> List[tuple[int, int]]:
        """Generate spiral positions from center."""
        center_r = rows // 2
        center_c = cols // 2
        
        positions = [(center_r, center_c)]
        
        # Spiral outward
        for radius in range(1, max(rows, cols)):
            # Top
            for c in range(center_c - radius, center_c + radius + 1):
                if 0 <= c < cols and len(positions) < count:
                    positions.append((center_r - radius, c))
            
            # Right
            for r in range(center_r - radius + 1, center_r + radius):
                if 0 <= r < rows and len(positions) < count:
                    positions.append((r, center_c + radius))
            
            # Bottom
            for c in range(center_c + radius, center_c - radius - 1, -1):
                if 0 <= c < cols and len(positions) < count:
                    positions.append((center_r + radius, c))
            
            # Left
            for r in range(center_r + radius - 1, center_r - radius, -1):
                if 0 <= r < rows and len(positions) < count:
                    positions.append((r, center_c - radius))
        
        return positions[:count]


class PadPlacer:
    """
    Low-level pad placement operations.
    
    Provides atomic operations for placing pads.
    """
    
    def place_io_pads(
        self,
        groups: List[IOGroup],
        die_area: tuple[float, float, float, float],
        pad_width_um: float = 80.0,
        pad_height_um: float = 80.0,
        spacing_um: float = 10.0,
    ) -> List[PadPlacement]:
        """
        Place I/O pad groups around die perimeter.
        
        Args:
            groups: I/O groups to place
            die_area: Die bounding box (x1, y1, x2, y2)
            pad_width_um: I/O pad width
            pad_height_um: I/O pad height
            spacing_um: Spacing between pads
            
        Returns:
            List of pad placements
        """
        placements = []
        x1, y1, x2, y2 = die_area
        
        # Distribute groups around perimeter
        for group in groups:
            side = group.side or "top"  # Default to top
            
            if side == "top":
                y = y2 - pad_height_um
                x_start = group.start_position * (x2 - x1) + x1
                
                for i, sig in enumerate(group.signals):
                    for j in range(sig.width):
                        x = x_start + i * (pad_width_um + spacing_um) + j * pad_width_um
                        placements.append(PadPlacement(
                            name=f"{sig.name}_{j}" if sig.width > 1 else sig.name,
                            x_um=x,
                            y_um=y,
                            width_um=pad_width_um,
                            height_um=pad_height_um,
                            pad_type="io",
                            signal_name=sig.name,
                            voltage_domain=sig.voltage_domain,
                        ))
            
            elif side == "bottom":
                y = y1
                x_start = group.start_position * (x2 - x1) + x1
                
                for i, sig in enumerate(group.signals):
                    for j in range(sig.width):
                        x = x_start + i * (pad_width_um + spacing_um) + j * pad_width_um
                        placements.append(PadPlacement(
                            name=f"{sig.name}_{j}" if sig.width > 1 else sig.name,
                            x_um=x,
                            y_um=y,
                            width_um=pad_width_um,
                            height_um=pad_height_um,
                            pad_type="io",
                            signal_name=sig.name,
                        ))
            
            elif side == "left":
                x = x1
                y_start = group.start_position * (y2 - y1) + y1
                
                for i, sig in enumerate(group.signals):
                    for j in range(sig.width):
                        y = y_start + i * (pad_height_um + spacing_um) + j * pad_height_um
                        placements.append(PadPlacement(
                            name=f"{sig.name}_{j}" if sig.width > 1 else sig.name,
                            x_um=x,
                            y_um=y,
                            width_um=pad_width_um,
                            height_um=pad_height_um,
                            pad_type="io",
                            signal_name=sig.name,
                        ))
            
            elif side == "right":
                x = x2 - pad_width_um
                y_start = group.start_position * (y2 - y1) + y1
                
                for i, sig in enumerate(group.signals):
                    for j in range(sig.width):
                        y = y_start + i * (pad_height_um + spacing_um) + j * pad_height_um
                        placements.append(PadPlacement(
                            name=f"{sig.name}_{j}" if sig.width > 1 else sig.name,
                            x_um=x,
                            y_um=y,
                            width_um=pad_width_um,
                            height_um=pad_height_um,
                            pad_type="io",
                            signal_name=sig.name,
                        ))
        
        return placements
    
    def place_pg_pads(
        self,
        positions: List[Dict[str, float]],
        die_area: tuple[float, float, float, float],
        pad_width_um: float = 80.0,
        pad_height_um: float = 80.0,
    ) -> List[PadPlacement]:
        """
        Place PG pads at specified positions.
        
        Args:
            positions: List of {position_um, type, domain}
            die_area: Die bounding box
            pad_width_um: PG pad width
            pad_height_um: PG pad height
            
        Returns:
            List of pad placements
        """
        placements = []
        x1, y1, x2, y2 = die_area
        
        perimeter = 2 * (x2 - x1 + y2 - y1)
        
        for i, pos_info in enumerate(positions):
            pos = pos_info["position_um"]
            pad_type = pos_info["type"]
            domain = pos_info.get("domain", "VDD")
            
            # Convert position to x,y
            if pos < (x2 - x1):  # Top
                x = x1 + pos
                y = y2 - pad_height_um
            elif pos < (x2 - x1) + (y2 - y1):  # Right
                x = x2 - pad_width_um
                y = y2 - (pos - (x2 - x1))
            elif pos < 2 * (x2 - x1) + (y2 - y1):  # Bottom
                x = x2 - (pos - (x2 - x1) - (y2 - y1))
                y = y1
            else:  # Left
                x = x1
                y = y1 + (pos - 2 * (x2 - x1) - (y2 - y1))
            
            placements.append(PadPlacement(
                name=f"{domain}_{pad_type}_{i}",
                x_um=x,
                y_um=y,
                width_um=pad_width_um,
                height_um=pad_height_um,
                pad_type=pad_type,
                voltage_domain=domain,
            ))
        
        return placements
    
    def place_bumps(
        self,
        array: BumpArraySpec,
        assignments: Dict[str, tuple[int, int]],
    ) -> List[PadPlacement]:
        """
        Place flip-chip bumps.
        
        Args:
            array: Bump array specification
            assignments: Signal to bump position mapping
            
        Returns:
            List of bump placements
        """
        placements = []
        
        # Calculate array origin
        origin_x = array.center_x_um - array.array_width_um / 2
        origin_y = array.center_y_um - array.array_height_um / 2
        
        for sig_name, (row, col) in assignments.items():
            x = origin_x + col * array.pitch_um
            y = origin_y + row * array.pitch_um
            
            placements.append(PadPlacement(
                name=sig_name,
                x_um=x,
                y_um=y,
                width_um=array.bump_diameter_um,
                height_um=array.bump_diameter_um,
                pad_type="bump",
                signal_name=sig_name,
            ))
        
        return placements


class PadPlanner:
    """
    Main Pad Planner interface.
    
    Provides composed access to all planning agents.
    """
    
    def __init__(self):
        self.io_agent = IOGroupingAgent()
        self.pg_calculator = PGPadCalculator()
        self.bump_planner = BumpPlanner()
        self.placer = PadPlacer()
    
    def get_summary(
        self,
        io_groups: List[IOGroup],
        pg_info: List[PGPadInfo],
        bump_array: Optional[BumpArraySpec] = None,
    ) -> str:
        """Generate planning summary."""
        lines = [
            "Pad Planning Summary",
            "=" * 60,
            "",
            "I/O Groups:",
        ]
        
        total_io = 0
        for group in io_groups:
            lines.append(f"  {group.name}: {group.signal_count} signals, {group.total_width} bits")
            total_io += group.total_width
        
        lines.append(f"  Total I/O bits: {total_io}")
        lines.append("")
        
        lines.append("Power/Ground Pads:")
        for info in pg_info:
            lines.append(f"  {info.voltage_domain}:")
            lines.append(f"    VDD: {info.vdd_pad_count} pads ({info.vdd_current_ma:.0f}mA)")
            lines.append(f"    VSS: {info.vss_pad_count} pads ({info.vss_current_ma:.0f}mA)")
        lines.append("")
        
        if bump_array:
            lines.append("Flip-Chip Bumps:")
            lines.append(f"  Array: {bump_array.rows} x {bump_array.cols}")
            lines.append(f"  Total bumps: {bump_array.total_bumps}")
            lines.append(f"  Pitch: {bump_array.pitch_um}um")
            lines.append("")
        
        return "\n".join(lines)
