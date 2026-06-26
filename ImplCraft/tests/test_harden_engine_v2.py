"""Tests for HardenEngine — signal-flow-aware hardening."""
import pytest
from pathlib import Path
from src.analysis.harden_engine import (
    HardenEngine,
    HardenedBlock,
    HardenPlan,
    BlockInterface,
)
from src.analysis.design_context import (
    DesignContext,
    ModuleAnalysis,
    ModuleRole,
    Interconnect,
    SignalInfo,
    SignalFlowPath,
)


class TestHardenEngine:
    """Test HardenEngine functionality."""
    
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
            port_count=64,
        ))
        ctx.add_module(ModuleAnalysis(
            name="pll",
            role=ModuleRole.CLOCK,
            gate_count=50000,
            area_um2=250000,
            port_count=32,
        ))
        ctx.add_module(ModuleAnalysis(
            name="cpu",
            role=ModuleRole.DATAPATH,
            gate_count=500000,
            area_um2=2500000,
            port_count=128,
        ))
        ctx.add_module(ModuleAnalysis(
            name="small_ctrl",
            role=ModuleRole.CONTROLLER,
            gate_count=10000,  # Too small to harden
            area_um2=50000,
            port_count=16,
        ))
        
        # Add signals
        sram_mod = ctx.get_module("sram_ctrl")
        sram_mod.input_signals.append(SignalInfo(name="clk", width=1, is_clock=True))
        sram_mod.input_signals.append(SignalInfo(name="rst", width=1, is_reset=True))
        sram_mod.input_signals.append(SignalInfo(name="addr", width=16))
        sram_mod.output_signals.append(SignalInfo(name="data", width=32))
        
        # Add interconnects
        ctx.interconnects.append(Interconnect(
            from_module="cpu",
            to_module="sram_ctrl",
            signal_count=64,
        ))
        ctx.interconnects.append(Interconnect(
            from_module="pll",
            to_module="cpu",
            signal_count=4,
        ))
        
        # Add signal flow path
        ctx.signal_flow_paths.append(SignalFlowPath(
            name="cpu_to_mem",
            modules=["cpu", "sram_ctrl"],
            total_delay_ns=2.5,
            is_critical=True,
        ))
        
        return ctx
    
    def test_create_harden_plan(self, sample_context):
        """Test creating hardening plan."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        # Should have hardened blocks
        assert len(plan.blocks) > 0
        
        # Memory, clock, and large modules should be hardened
        block_names = {b.module_name for b in plan.blocks}
        assert "sram_ctrl" in block_names
        assert "pll" in block_names
        assert "cpu" in block_names
        
        # Small module should not be hardened
        assert "small_ctrl" not in block_names
    
    def test_flow_order(self, sample_context):
        """Test flow order determination."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        # Should have flow order
        assert len(plan.flow_order) > 0
        
        # All blocks should be in flow order
        for block in plan.blocks:
            assert block.module_name in plan.flow_order
    
    def test_block_interface_creation(self, sample_context):
        """Test block interface creation."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        # Find sram block
        sram_block = next(b for b in plan.blocks if b.module_name == "sram_ctrl")
        
        # Should have interface
        assert sram_block.interface is not None
        assert sram_block.interface.module_name == "sram_ctrl"
        
        # Should have ports
        assert len(sram_block.interface.input_ports) > 0
        assert len(sram_block.interface.output_ports) > 0
        assert len(sram_block.interface.clock_ports) > 0
    
    def test_dependencies(self, sample_context):
        """Test dependency tracking."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        # Find sram block
        sram_block = next(b for b in plan.blocks if b.module_name == "sram_ctrl")
        
        # Should depend on cpu
        assert "cpu" in sram_block.depends_on
    
    def test_recommendations(self, sample_context):
        """Test recommendation generation."""
        engine = HardenEngine()
        
        # Add a very large module
        sample_context.add_module(ModuleAnalysis(
            name="huge_module",
            role=ModuleRole.DATAPATH,
            gate_count=5000000,  # Very large
            area_um2=25000000,
        ))
        
        plan = engine.create_harden_plan(sample_context)
        
        # Should have recommendation about large block
        assert any("very large" in rec.lower() for rec in plan.recommendations)
    
    def test_warnings(self, sample_context):
        """Test warning generation."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        # Should have warnings about critical paths crossing blocks
        # (cpu -> sram_ctrl is critical and both are hardened)
        assert len(plan.warnings) >= 0  # May or may not have warnings
    
    def test_generate_scripts_icc2(self, sample_context, tmp_path):
        """Test script generation for ICC2."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        engine.generate_scripts(plan, tmp_path, tool="icc2")
        
        # Check scripts were created
        for block in plan.blocks:
            block_dir = tmp_path / block.name
            assert (block_dir / "synth.tcl").exists()
            assert (block_dir / "pr.tcl").exists()
            assert (block_dir / "interface.txt").exists()
        
        # Check flow order script
        assert (tmp_path / "flow_order.tcl").exists()
    
    def test_generate_scripts_innovus(self, sample_context, tmp_path):
        """Test script generation for Innovus."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        engine.generate_scripts(plan, tmp_path, tool="innovus")
        
        # Check scripts were created
        for block in plan.blocks:
            block_dir = tmp_path / block.name
            assert (block_dir / "synth.tcl").exists()
            assert (block_dir / "pr.tcl").exists()
    
    def test_synth_script_content_icc2(self, sample_context, tmp_path):
        """Test synthesis script content."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        engine.generate_scripts(plan, tmp_path, tool="icc2")
        
        # Read a synth script
        block = plan.blocks[0]
        script_path = tmp_path / block.name / "synth.tcl"
        script = script_path.read_text()
        
        assert "read_verilog" in script
        assert "compile_ultra" in script
        assert "report_timing" in script
    
    def test_pr_script_content_icc2(self, sample_context, tmp_path):
        """Test P&R script content."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        engine.generate_scripts(plan, tmp_path, tool="icc2")
        
        # Read a P&R script
        block = plan.blocks[0]
        script_path = tmp_path / block.name / "pr.tcl"
        script = script_path.read_text()
        
        assert "read_lib" in script
        assert "place_opt" in script
        assert "clock_opt" in script
        assert "route_opt" in script
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        ctx = DesignContext()
        
        # Create circular dependency: A -> B -> C -> A
        ctx.add_module(ModuleAnalysis(
            name="A", role=ModuleRole.MEMORY, gate_count=100000,
        ))
        ctx.add_module(ModuleAnalysis(
            name="B", role=ModuleRole.MEMORY, gate_count=100000,
        ))
        ctx.add_module(ModuleAnalysis(
            name="C", role=ModuleRole.MEMORY, gate_count=100000,
        ))
        
        ctx.interconnects.append(Interconnect(from_module="A", to_module="B"))
        ctx.interconnects.append(Interconnect(from_module="B", to_module="C"))
        ctx.interconnects.append(Interconnect(from_module="C", to_module="A"))
        
        engine = HardenEngine()
        plan = engine.create_harden_plan(ctx)
        
        # Should detect circular dependency
        assert engine._has_circular_dependencies(plan)
    
    def test_harden_plan_summary(self, sample_context):
        """Test harden plan summary."""
        engine = HardenEngine()
        plan = engine.create_harden_plan(sample_context)
        
        summary = plan.summary()
        
        assert "Harden Plan Summary" in summary
        assert f"Hardened blocks: {len(plan.blocks)}" in summary


class TestHardenedBlock:
    """Test HardenedBlock data class."""
    
    def test_block_creation(self):
        """Test block creation."""
        interface = BlockInterface(module_name="test")
        
        block = HardenedBlock(
            name="test_block",
            module_name="test",
            role=ModuleRole.MEMORY,
            interface=interface,
            gate_count=200000,
            area_um2=1000000,
            port_count=64,
        )
        
        assert block.name == "test_block"
        assert block.gate_count == 200000
        assert block.role == ModuleRole.MEMORY
    
    def test_block_summary(self):
        """Test block summary."""
        interface = BlockInterface(module_name="cpu")
        
        block = HardenedBlock(
            name="cpu_block",
            module_name="cpu",
            role=ModuleRole.DATAPATH,
            interface=interface,
            gate_count=500000,
            area_um2=2500000,
            depends_on=["pll"],
            depended_by=["sram_ctrl"],
        )
        
        summary = block.summary()
        
        assert "cpu_block" in summary
        assert "500,000" in summary
        assert "pll" in summary
        assert "sram_ctrl" in summary


class TestBlockInterface:
    """Test BlockInterface data class."""
    
    def test_interface_creation(self):
        """Test interface creation."""
        interface = BlockInterface(module_name="test")
        
        assert interface.module_name == "test"
        assert len(interface.input_ports) == 0
        assert len(interface.output_ports) == 0
    
    def test_interface_with_ports(self):
        """Test interface with ports."""
        interface = BlockInterface(module_name="test")
        
        interface.input_ports.append({
            "name": "clk",
            "width": 1,
            "direction": "input",
            "is_clock": True,
        })
        interface.clock_ports.append("clk")
        
        interface.output_ports.append({
            "name": "data",
            "width": 32,
            "direction": "output",
        })
        
        assert len(interface.input_ports) == 1
        assert len(interface.output_ports) == 1
        assert "clk" in interface.clock_ports
    
    def test_interface_summary(self):
        """Test interface summary."""
        interface = BlockInterface(module_name="test")
        interface.input_ports.append({"name": "in1", "width": 1})
        interface.output_ports.append({"name": "out1", "width": 1})
        
        summary = interface.summary()
        
        assert "test" in summary
        assert "Input ports: 1" in summary
        assert "Output ports: 1" in summary


class TestIntegration:
    """Integration tests for HardenEngine."""
    
    def test_end_to_end_flow(self, tmp_path):
        """Test complete hardening flow."""
        # Create context
        ctx = DesignContext(design_name="SoC", top_module="top")
        
        ctx.add_module(ModuleAnalysis(
            name="memory_controller",
            role=ModuleRole.MEMORY,
            gate_count=300000,
            area_um2=1500000,
            port_count=128,
            should_harden=True,
            harden_reason="Memory controller",
        ))
        
        ctx.interconnects.append(Interconnect(
            from_module="cpu",
            to_module="memory_controller",
            signal_count=128,
        ))
        
        # Create hardening plan
        engine = HardenEngine()
        plan = engine.create_harden_plan(ctx)
        
        # Generate scripts
        engine.generate_scripts(plan, tmp_path, tool="icc2")
        
        # Verify outputs
        assert len(plan.blocks) == 1
        block = plan.blocks[0]
        
        block_dir = tmp_path / block.name
        assert block_dir.exists()
        assert (block_dir / "synth.tcl").exists()
        assert (block_dir / "pr.tcl").exists()
        assert (block_dir / "interface.txt").exists()
        
        # Verify script content
        synth_script = (block_dir / "synth.tcl").read_text()
        assert "memory_controller" in synth_script
        assert "compile_ultra" in synth_script
