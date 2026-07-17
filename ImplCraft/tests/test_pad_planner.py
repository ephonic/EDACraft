"""Tests for Pad Planner — I/O, PG pad, and bump planning interfaces."""
import pytest
from src.analysis.pad_planner import (
    PadPlanner,
    IOGroupingAgent,
    PGPadCalculator,
    BumpPlanner,
    PadPlacer,
    IOSignal,
    IOSignalType,
    IOGroup,
    GroupingStrategy,
    PGPadInfo,
    BumpArraySpec,
    PadPlacement,
)


class TestIOSignal:
    """Test IOSignal data class."""
    
    def test_signal_creation(self):
        """Test signal creation."""
        sig = IOSignal(
            name="uart_tx",
            signal_type=IOSignalType.DIGITAL_OUTPUT,
            width=1,
            function_group="uart",
        )
        
        assert sig.name == "uart_tx"
        assert sig.signal_type == IOSignalType.DIGITAL_OUTPUT
        assert sig.function_group == "uart"


class TestIOGroupingAgent:
    """Test IOGroupingAgent functionality."""
    
    @pytest.fixture
    def sample_signals(self):
        """Create sample I/O signals."""
        return [
            IOSignal(name="uart_tx", signal_type=IOSignalType.DIGITAL_OUTPUT,
                    function_group="uart"),
            IOSignal(name="uart_rx", signal_type=IOSignalType.DIGITAL_INPUT,
                    function_group="uart"),
            IOSignal(name="spi_clk", signal_type=IOSignalType.CLOCK,
                    function_group="spi"),
            IOSignal(name="spi_mosi", signal_type=IOSignalType.DIGITAL_OUTPUT,
                    function_group="spi"),
            IOSignal(name="spi_miso", signal_type=IOSignalType.DIGITAL_INPUT,
                    function_group="spi"),
            IOSignal(name="gpio_0", signal_type=IOSignalType.DIGITAL_BIDIR,
                    function_group="gpio"),
            IOSignal(name="gpio_1", signal_type=IOSignalType.DIGITAL_BIDIR,
                    function_group="gpio"),
        ]
    
    def test_group_by_function(self, sample_signals):
        """Test functional grouping."""
        agent = IOGroupingAgent()
        groups = agent.suggest_groups(sample_signals, GroupingStrategy.FUNCTIONAL)
        
        # Should have 3 groups: uart, spi, gpio
        assert len(groups) == 3
        
        group_names = {g.name for g in groups}
        assert "uart" in group_names
        assert "spi" in group_names
        assert "gpio" in group_names
    
    def test_group_by_signal_type(self, sample_signals):
        """Test signal type grouping."""
        agent = IOGroupingAgent()
        groups = agent.suggest_groups(sample_signals, GroupingStrategy.SIGNAL_TYPE)
        
        # Should group by signal type
        assert len(groups) > 0
    
    def test_group_max_size(self, sample_signals):
        """Test max group size."""
        agent = IOGroupingAgent()
        groups = agent.suggest_groups(
            sample_signals,
            GroupingStrategy.FUNCTIONAL,
            max_group_size=2,
        )
        
        # All groups should be <= 2
        for group in groups:
            assert group.signal_count <= 2


class TestPGPadCalculator:
    """Test PGPadCalculator functionality."""
    
    def test_calculate_single_domain(self):
        """Test calculation for single domain."""
        calculator = PGPadCalculator()
        
        domains = {
            "VDD_CORE": {"vdd_current_ma": 500, "vss_current_ma": 500}
        }
        
        results = calculator.calculate(domains, current_density_a_per_pad=0.05)
        
        assert len(results) == 1
        assert results[0].voltage_domain == "VDD_CORE"
        assert results[0].vdd_pad_count == 10  # 0.5A / 0.05A = 10
        assert results[0].vss_pad_count == 10
    
    def test_calculate_multiple_domains(self):
        """Test calculation for multiple domains."""
        calculator = PGPadCalculator()
        
        domains = {
            "VDD_CORE": {"vdd_current_ma": 500, "vss_current_ma": 500},
            "VDDIO": {"vdd_current_ma": 200, "vss_current_ma": 200},
        }
        
        results = calculator.calculate(domains)
        
        assert len(results) == 2
    
    def test_distribute_uniformly(self):
        """Test uniform distribution."""
        calculator = PGPadCalculator()
        
        pg_info = PGPadInfo(
            voltage_domain="VDD",
            vdd_current_ma=500,
            vss_current_ma=500,
        )
        pg_info.calculate()
        
        positions = calculator.distribute_uniformly(
            pg_info,
            die_perimeter_um=10000,
            io_pad_count=100,
        )
        
        # Should have positions for all PG pads
        assert len(positions) == pg_info.vdd_pad_count + pg_info.vss_pad_count
        
        # Should alternate VDD/VSS
        vdd_count = sum(1 for p in positions if p["type"] == "vdd")
        vss_count = sum(1 for p in positions if p["type"] == "vss")
        assert vdd_count == pg_info.vdd_pad_count
        assert vss_count == pg_info.vss_pad_count


class TestBumpPlanner:
    """Test BumpPlanner functionality."""
    
    def test_calculate_array_size(self):
        """Test bump array size calculation."""
        planner = BumpPlanner()
        
        array = planner.calculate_array_size(
            total_signals=100,
            total_pg_pads=50,
            pitch_um=150,
            utilization=0.7,
        )
        
        assert array.rows > 0
        assert array.cols > 0
        assert array.total_bumps >= 150 / 0.7
    
    def test_assign_signals_to_bumps(self):
        """Test signal to bump assignment."""
        planner = BumpPlanner()
        
        signals = [
            IOSignal(name="clk", signal_type=IOSignalType.CLOCK),
            IOSignal(name="data", signal_type=IOSignalType.DIGITAL_OUTPUT, width=8),
        ]
        
        array = BumpArraySpec(rows=10, cols=10, pitch_um=150)
        
        assignments = planner.assign_signals_to_bumps(signals, array)
        
        assert len(assignments) == len(signals)
        assert "clk" in assignments
        assert "data" in assignments


class TestPadPlacer:
    """Test PadPlacer functionality."""
    
    @pytest.fixture
    def sample_groups(self):
        """Create sample I/O groups."""
        group1 = IOGroup(
            name="uart",
            signals=[
                IOSignal(name="tx", signal_type=IOSignalType.DIGITAL_OUTPUT),
                IOSignal(name="rx", signal_type=IOSignalType.DIGITAL_INPUT),
            ],
            side="top",
            start_position=0.1,
        )
        
        group2 = IOGroup(
            name="spi",
            signals=[
                IOSignal(name="clk", signal_type=IOSignalType.CLOCK),
                IOSignal(name="mosi", signal_type=IOSignalType.DIGITAL_OUTPUT),
            ],
            side="bottom",
            start_position=0.2,
        )
        
        return [group1, group2]
    
    def test_place_io_pads_top(self, sample_groups):
        """Test placing I/O pads on top."""
        placer = PadPlacer()
        
        placements = placer.place_io_pads(
            sample_groups[:1],  # Only first group (top)
            die_area=(0, 0, 2900, 1900),
        )
        
        assert len(placements) == 2
        for p in placements:
            assert p.pad_type == "io"
            assert p.y_um == 1900 - 80  # Top edge
    
    def test_place_io_pads_bottom(self, sample_groups):
        """Test placing I/O pads on bottom."""
        placer = PadPlacer()
        
        placements = placer.place_io_pads(
            sample_groups[1:],  # Only second group (bottom)
            die_area=(0, 0, 2900, 1900),
        )
        
        assert len(placements) == 2
        for p in placements:
            assert p.y_um == 0  # Bottom edge
    
    def test_place_pg_pads(self):
        """Test placing PG pads."""
        placer = PadPlacer()
        
        positions = [
            {"position_um": 100, "type": "vdd", "domain": "VDD"},
            {"position_um": 200, "type": "vss", "domain": "VDD"},
        ]
        
        placements = placer.place_pg_pads(
            positions,
            die_area=(0, 0, 2900, 1900),
        )
        
        assert len(placements) == 2
        assert placements[0].pad_type == "vdd"
        assert placements[1].pad_type == "vss"
    
    def test_place_bumps(self):
        """Test placing bumps."""
        placer = PadPlacer()
        
        array = BumpArraySpec(
            rows=5,
            cols=5,
            pitch_um=150,
            center_x_um=1450,
            center_y_um=950,
        )
        
        assignments = {
            "clk": (2, 2),
            "data": (2, 3),
        }
        
        placements = placer.place_bumps(array, assignments)
        
        assert len(placements) == 2
        for p in placements:
            assert p.pad_type == "bump"


class TestPadPlanner:
    """Test PadPlanner main interface."""
    
    def test_planner_initialization(self):
        """Test planner initialization."""
        planner = PadPlanner()
        
        assert planner.io_agent is not None
        assert planner.pg_calculator is not None
        assert planner.bump_planner is not None
        assert planner.placer is not None
    
    def test_get_summary(self):
        """Test summary generation."""
        planner = PadPlanner()
        
        groups = [
            IOGroup(name="uart", signals=[
                IOSignal(name="tx", signal_type=IOSignalType.DIGITAL_OUTPUT),
            ]),
        ]
        
        pg_info = [
            PGPadInfo(
                voltage_domain="VDD",
                vdd_current_ma=500,
                vss_current_ma=500,
                vdd_pad_count=10,
                vss_pad_count=10,
            )
        ]
        
        bump_array = BumpArraySpec(rows=10, cols=10, pitch_um=150)
        
        summary = planner.get_summary(groups, pg_info, bump_array)
        
        assert "Pad Planning Summary" in summary
        assert "uart" in summary
        assert "VDD" in summary
        assert "Flip-Chip Bumps" in summary


class TestIntegration:
    """Integration tests for Pad Planner."""
    
    def test_complete_io_flow(self):
        """Test complete I/O planning flow."""
        planner = PadPlanner()
        
        # Create signals
        signals = [
            IOSignal(name="uart_tx", signal_type=IOSignalType.DIGITAL_OUTPUT,
                    function_group="uart"),
            IOSignal(name="uart_rx", signal_type=IOSignalType.DIGITAL_INPUT,
                    function_group="uart"),
            IOSignal(name="spi_clk", signal_type=IOSignalType.CLOCK,
                    function_group="spi"),
        ]
        
        # Group signals
        groups = planner.io_agent.suggest_groups(signals, GroupingStrategy.FUNCTIONAL)
        assert len(groups) == 2
        
        # Assign sides
        groups[0].side = "top"
        groups[0].start_position = 0.1
        groups[1].side = "left"
        groups[1].start_position = 0.2
        
        # Place pads
        placements = planner.placer.place_io_pads(
            groups,
            die_area=(0, 0, 2900, 1900),
        )
        
        assert len(placements) == 3
    
    def test_complete_pg_flow(self):
        """Test complete PG planning flow."""
        planner = PadPlanner()
        
        # Calculate requirements
        domains = {
            "VDD_CORE": {"vdd_current_ma": 1000, "vss_current_ma": 1000}
        }
        
        pg_info = planner.pg_calculator.calculate(domains)
        assert len(pg_info) == 1
        
        # Distribute
        positions = planner.pg_calculator.distribute_uniformly(
            pg_info[0],
            die_perimeter_um=9600,
            io_pad_count=100,
        )
        
        # Place
        placements = planner.placer.place_pg_pads(
            positions,
            die_area=(0, 0, 2900, 1900),
        )
        
        assert len(placements) == pg_info[0].vdd_pad_count + pg_info[0].vss_pad_count
    
    def test_complete_bump_flow(self):
        """Test complete bump planning flow."""
        planner = PadPlanner()
        
        # Calculate array size
        array = planner.bump_planner.calculate_array_size(
            total_signals=50,
            total_pg_pads=20,
            pitch_um=150,
        )
        
        # Create signals
        signals = [
            IOSignal(name=f"sig_{i}", signal_type=IOSignalType.DIGITAL_OUTPUT)
            for i in range(50)
        ]
        
        # Assign to bumps
        assignments = planner.bump_planner.assign_signals_to_bumps(signals, array)
        
        # Place bumps
        placements = planner.placer.place_bumps(array, assignments)
        
        assert len(placements) == 50
