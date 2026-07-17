"""Tests for MacroPlacer — dual-mode placement engine."""
import pytest
from src.analysis.macro_placer import (
    MacroPlacer,
    Macro,
    MacroPlacement,
    PlacementResult,
    PlacementMode,
)
from src.analysis.design_context import (
    DesignContext,
    ModuleAnalysis,
    ModuleRole,
    Interconnect,
    InterconnectType,
)


class TestMacroPlacer:
    """Test MacroPlacer functionality."""
    
    @pytest.fixture
    def sample_context(self):
        """Create sample design context."""
        ctx = DesignContext(design_name="SoC", top_module="top")
        
        # Add modules
        ctx.add_module(ModuleAnalysis(
            name="sram_ctrl",
            role=ModuleRole.MEMORY,
            gate_count=200000,
            area_um2=1000000,
        ))
        ctx.add_module(ModuleAnalysis(
            name="pll",
            role=ModuleRole.CLOCK,
            gate_count=50000,
            area_um2=250000,
        ))
        ctx.add_module(ModuleAnalysis(
            name="uart",
            role=ModuleRole.IO,
            gate_count=80000,
            area_um2=400000,
        ))
        ctx.add_module(ModuleAnalysis(
            name="cpu",
            role=ModuleRole.DATAPATH,
            gate_count=500000,
            area_um2=2500000,
        ))
        
        # Add interconnects
        ctx.interconnects.append(Interconnect(
            from_module="cpu",
            to_module="sram_ctrl",
            signal_count=64,
            interconnect_type=InterconnectType.BUS,
        ))
        ctx.interconnects.append(Interconnect(
            from_module="uart",
            to_module="cpu",
            signal_count=8,
        ))
        
        # Add macros
        ctx.macros = [
            {"name": "sram_ctrl", "type": "sram", "area_um2": 1000000},
            {"name": "pll", "type": "pll", "area_um2": 250000},
            {"name": "uart", "type": "io", "area_um2": 400000},
        ]
        
        return ctx
    
    @pytest.fixture
    def sample_macros(self):
        """Create sample macros."""
        return [
            Macro(name="sram_ctrl", width_um=1000, height_um=1000, role=ModuleRole.MEMORY),
            Macro(name="pll", width_um=500, height_um=500, role=ModuleRole.CLOCK),
            Macro(name="uart", width_um=600, height_um=700, role=ModuleRole.IO),
            Macro(name="cpu", width_um=1500, height_um=1700, role=ModuleRole.DATAPATH),
        ]
    
    def test_block_mode_initialization(self):
        """Test block mode initialization."""
        placer = MacroPlacer(mode="block")
        assert placer.mode == PlacementMode.BLOCK
    
    def test_top_mode_initialization(self):
        """Test top mode initialization."""
        placer = MacroPlacer(mode=PlacementMode.TOP)
        assert placer.mode == PlacementMode.TOP
    
    def test_block_level_placement(self, sample_context, sample_macros):
        """Test block-level placement."""
        placer = MacroPlacer(mode="block")
        
        floorplan = {
            "core_area": (0, 0, 5000, 5000),
        }
        
        result = placer.place(sample_context, floorplan, sample_macros)
        
        # Should have placements
        assert len(result.placements) > 0
        
        # Should have routing channels
        assert len(result.routing_channels) > 0
        
        # Should reserve std cell area
        assert "core" in result.std_cell_area
        assert result.std_cell_area["core"] > 0
    
    def test_top_level_placement(self, sample_context, sample_macros):
        """Test top-level placement."""
        placer = MacroPlacer(mode="top")
        
        floorplan = {
            "core_area": (0, 0, 8000, 8000),
        }
        
        result = placer.place(sample_context, floorplan, sample_macros)
        
        # Should have placements
        assert len(result.placements) > 0
        
        # Should have routing channels (grid)
        assert len(result.routing_channels) > 0
        
        # Should reserve top-level std cell area
        assert "top_level" in result.std_cell_area
    
    def test_empty_macros(self, sample_context):
        """Test placement with no macros."""
        placer = MacroPlacer(mode="block")
        
        floorplan = {"core_area": (0, 0, 5000, 5000)}
        
        result = placer.place(sample_context, floorplan, [])
        
        assert len(result.placements) == 0
    
    def test_extract_macros_from_context(self, sample_context):
        """Test extracting macros from context."""
        placer = MacroPlacer(mode="block")
        
        macros = placer._extract_macros(sample_context)
        
        # Should extract macros from context.macros
        assert len(macros) == 3
        assert {m.name for m in macros} == {"sram_ctrl", "pll", "uart"}
    
    def test_group_macros_by_role(self, sample_macros):
        """Test grouping macros by role."""
        placer = MacroPlacer(mode="block")
        
        groups = placer._group_macros_by_role(sample_macros)
        
        assert ModuleRole.MEMORY in groups
        assert len(groups[ModuleRole.MEMORY]) == 1
        assert groups[ModuleRole.MEMORY][0].name == "sram_ctrl"
        
        assert ModuleRole.CLOCK in groups
        assert ModuleRole.IO in groups
        assert ModuleRole.DATAPATH in groups
    
    def test_signal_flow_order(self, sample_context, sample_macros):
        """Test signal flow ordering."""
        placer = MacroPlacer(mode="top")
        
        order = placer._get_signal_flow_order(sample_context, sample_macros)
        
        # Should return all macro names
        assert len(order) == 4
        assert set(order) == {"sram_ctrl", "pll", "uart", "cpu"}
    
    def test_routing_channels_block_mode(self, sample_context, sample_macros):
        """Test routing channels in block mode."""
        placer = MacroPlacer(mode="block")
        
        floorplan = {"core_area": (0, 0, 5000, 5000)}
        result = placer.place(sample_context, floorplan, sample_macros)
        
        # Should have center channels
        channel_names = [ch["name"] for ch in result.routing_channels]
        assert "h_channel_center" in channel_names
        assert "v_channel_center" in channel_names
    
    def test_routing_channels_top_mode(self, sample_context, sample_macros):
        """Test routing channels in top mode."""
        placer = MacroPlacer(mode="top")
        
        floorplan = {"core_area": (0, 0, 8000, 8000)}
        result = placer.place(sample_context, floorplan, sample_macros)
        
        # Should have grid channels
        assert len(result.routing_channels) > 0
        
        # Check for horizontal and vertical channels
        h_channels = [ch for ch in result.routing_channels if ch["direction"] == "horizontal"]
        v_channels = [ch for ch in result.routing_channels if ch["direction"] == "vertical"]
        
        assert len(h_channels) > 0
        assert len(v_channels) > 0
    
    def test_placement_result_summary(self, sample_context, sample_macros):
        """Test placement result summary."""
        placer = MacroPlacer(mode="block")
        
        floorplan = {"core_area": (0, 0, 5000, 5000)}
        result = placer.place(sample_context, floorplan, sample_macros)
        
        summary = result.summary()
        
        assert "Macro Placement Summary" in summary
        assert f"Placed macros: {len(result.placements)}" in summary


class TestMacroPlacement:
    """Test MacroPlacement data class."""
    
    def test_placement_bbox(self):
        """Test placement bounding box."""
        macro = Macro(name="test", width_um=1000, height_um=800)
        placement = MacroPlacement(macro=macro, x_um=100, y_um=200)
        
        bbox = placement.bbox
        assert bbox == (100, 200, 1100, 1000)


class TestPlacementModes:
    """Test different placement modes."""
    
    def test_block_mode_periphery_placement(self):
        """Test block mode places macros on periphery."""
        ctx = DesignContext()
        ctx.macros = [
            {"name": "io1", "type": "io", "area_um2": 100000},
            {"name": "io2", "type": "io", "area_um2": 100000},
        ]
        
        ctx.add_module(ModuleAnalysis(name="io1", role=ModuleRole.IO))
        ctx.add_module(ModuleAnalysis(name="io2", role=ModuleRole.IO))
        
        macros = [
            Macro(name="io1", width_um=300, height_um=300, role=ModuleRole.IO),
            Macro(name="io2", width_um=300, height_um=300, role=ModuleRole.IO),
        ]
        
        placer = MacroPlacer(mode="block")
        floorplan = {"core_area": (0, 0, 3000, 3000)}
        
        result = placer.place(ctx, floorplan, macros)
        
        # All placements should be near edges
        for placement in result.placements:
            x, y = placement.x_um, placement.y_um
            # Should be near top/bottom/left/right edge
            assert (
                x < 500 or x > 2500 or  # Left or right
                y < 500 or y > 2500     # Top or bottom
            )
    
    def test_top_mode_flow_placement(self):
        """Test top mode arranges by signal flow."""
        ctx = DesignContext()
        
        # Create flow: A -> B -> C
        ctx.add_module(ModuleAnalysis(name="A", role=ModuleRole.DATAPATH))
        ctx.add_module(ModuleAnalysis(name="B", role=ModuleRole.DATAPATH))
        ctx.add_module(ModuleAnalysis(name="C", role=ModuleRole.DATAPATH))
        
        ctx.interconnects.append(Interconnect(from_module="A", to_module="B"))
        ctx.interconnects.append(Interconnect(from_module="B", to_module="C"))
        
        macros = [
            Macro(name="A", width_um=1000, height_um=1000, role=ModuleRole.DATAPATH),
            Macro(name="B", width_um=1000, height_um=1000, role=ModuleRole.DATAPATH),
            Macro(name="C", width_um=1000, height_um=1000, role=ModuleRole.DATAPATH),
        ]
        
        placer = MacroPlacer(mode="top")
        floorplan = {"core_area": (0, 0, 5000, 5000)}
        
        result = placer.place(ctx, floorplan, macros)
        
        # Should have all 3 placements
        assert len(result.placements) == 3
        
        # Should be arranged in grid
        positions = [(p.x_um, p.y_um) for p in result.placements]
        assert len(set(positions)) == 3  # All different positions
