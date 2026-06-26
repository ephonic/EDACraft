"""Tests for DesignContext — persistent design analysis state."""
import pytest
import json
from pathlib import Path
from src.analysis.design_context import (
    DesignContext,
    ModuleAnalysis,
    ModuleRole,
    Interconnect,
    InterconnectType,
    SignalInfo,
    SignalFlowPath,
)


class TestDesignContext:
    """Test DesignContext functionality."""
    
    def test_create_empty_context(self):
        """Test creating empty context."""
        ctx = DesignContext(design_name="test_design", top_module="top")
        
        assert ctx.design_name == "test_design"
        assert ctx.top_module == "top"
        assert len(ctx.modules) == 0
        assert len(ctx.interconnects) == 0
    
    def test_add_module(self):
        """Test adding modules."""
        ctx = DesignContext()
        
        mod = ModuleAnalysis(name="cpu", role=ModuleRole.DATAPATH)
        ctx.add_module(mod)
        
        assert "cpu" in ctx.modules
        assert ctx.modules["cpu"].role == ModuleRole.DATAPATH
    
    def test_get_module(self):
        """Test getting modules."""
        ctx = DesignContext()
        
        mod = ModuleAnalysis(name="sram_ctrl", role=ModuleRole.MEMORY)
        ctx.add_module(mod)
        
        retrieved = ctx.get_module("sram_ctrl")
        assert retrieved is not None
        assert retrieved.name == "sram_ctrl"
        
        # Non-existent module
        assert ctx.get_module("nonexistent") is None
    
    def test_get_children(self):
        """Test getting child modules."""
        ctx = DesignContext()
        
        parent = ModuleAnalysis(name="top", children=["cpu", "mem", "io"])
        child1 = ModuleAnalysis(name="cpu")
        child2 = ModuleAnalysis(name="mem")
        child3 = ModuleAnalysis(name="io")
        
        ctx.add_module(parent)
        ctx.add_module(child1)
        ctx.add_module(child2)
        ctx.add_module(child3)
        
        children = ctx.get_children("top")
        assert len(children) == 3
        assert {c.name for c in children} == {"cpu", "mem", "io"}
    
    def test_get_interconnects(self):
        """Test getting interconnects."""
        ctx = DesignContext()
        
        ic1 = Interconnect(from_module="cpu", to_module="mem", signal_count=32)
        ic2 = Interconnect(from_module="cpu", to_module="io", signal_count=16)
        ic3 = Interconnect(from_module="dma", to_module="mem", signal_count=64)
        
        ctx.interconnects.extend([ic1, ic2, ic3])
        
        incoming, outgoing = ctx.get_interconnects("mem")
        assert len(incoming) == 2  # from cpu and dma
        assert len(outgoing) == 0
    
    def test_get_critical_path(self):
        """Test getting critical path."""
        ctx = DesignContext()
        
        path1 = SignalFlowPath(
            name="path1",
            modules=["cpu", "mem"],
            total_delay_ns=2.5,
            is_critical=True,
        )
        path2 = SignalFlowPath(
            name="path2",
            modules=["io", "dma"],
            total_delay_ns=1.8,
            is_critical=False,
        )
        
        ctx.signal_flow_paths.extend([path1, path2])
        
        critical = ctx.get_critical_path()
        assert critical is not None
        assert critical.name == "path1"
        assert critical.total_delay_ns == 2.5
    
    def test_get_modules_by_role(self):
        """Test getting modules by role."""
        ctx = DesignContext()
        
        ctx.add_module(ModuleAnalysis(name="sram1", role=ModuleRole.MEMORY))
        ctx.add_module(ModuleAnalysis(name="sram2", role=ModuleRole.MEMORY))
        ctx.add_module(ModuleAnalysis(name="cpu", role=ModuleRole.DATAPATH))
        ctx.add_module(ModuleAnalysis(name="pll", role=ModuleRole.CLOCK))
        
        memory_modules = ctx.get_modules_by_role(ModuleRole.MEMORY)
        assert len(memory_modules) == 2
        assert {m.name for m in memory_modules} == {"sram1", "sram2"}
    
    def test_get_harden_candidates(self):
        """Test getting harden candidates."""
        ctx = DesignContext()
        
        mod1 = ModuleAnalysis(name="cpu", should_harden=True, harden_reason="Large")
        mod2 = ModuleAnalysis(name="mem", should_harden=True, harden_reason="Memory")
        mod3 = ModuleAnalysis(name="ctrl", should_harden=False)
        
        ctx.add_module(mod1)
        ctx.add_module(mod2)
        ctx.add_module(mod3)
        
        candidates = ctx.get_harden_candidates()
        assert len(candidates) == 2
        assert {c.name for c in candidates} == {"cpu", "mem"}
    
    def test_save_and_load_json(self, tmp_path):
        """Test saving and loading JSON."""
        ctx = DesignContext(
            design_name="test",
            top_module="top",
            total_gates=1000000,
            total_area_um2=5000000,
        )
        
        mod = ModuleAnalysis(
            name="cpu",
            role=ModuleRole.DATAPATH,
            gate_count=500000,
            should_harden=True,
            harden_reason="Large module",
        )
        ctx.add_module(mod)
        
        ic = Interconnect(
            from_module="cpu",
            to_module="mem",
            signal_count=32,
            interconnect_type=InterconnectType.BUS,
        )
        ctx.interconnects.append(ic)
        
        # Save
        json_path = tmp_path / "context.json"
        ctx.save(json_path)
        assert json_path.exists()
        
        # Load
        loaded = DesignContext.load(json_path)
        assert loaded.design_name == "test"
        assert loaded.top_module == "top"
        assert loaded.total_gates == 1000000
        assert "cpu" in loaded.modules
        assert loaded.modules["cpu"].should_harden is True
        assert len(loaded.interconnects) == 1
        assert loaded.interconnects[0].interconnect_type == InterconnectType.BUS
    
    def test_save_and_load_yaml(self, tmp_path):
        """Test saving and loading YAML."""
        ctx = DesignContext(
            design_name="test",
            top_module="top",
        )
        
        mod = ModuleAnalysis(name="mem", role=ModuleRole.MEMORY)
        ctx.add_module(mod)
        
        # Save as YAML
        yaml_path = tmp_path / "context.yaml"
        ctx.save(yaml_path)
        assert yaml_path.exists()
        
        # Load
        loaded = DesignContext.load(yaml_path)
        assert loaded.design_name == "test"
        assert "mem" in loaded.modules
    
    def test_summary(self):
        """Test summary generation."""
        ctx = DesignContext(
            design_name="SoC",
            top_module="top",
            total_gates=2000000,
            total_area_um2=10000000,
        )
        
        ctx.add_module(ModuleAnalysis(name="cpu", role=ModuleRole.DATAPATH))
        ctx.add_module(ModuleAnalysis(name="mem", role=ModuleRole.MEMORY))
        ctx.add_module(ModuleAnalysis(
            name="io",
            role=ModuleRole.IO,
            should_harden=True,
            harden_reason="IO module",
        ))
        
        summary = ctx.summary()
        
        assert "SoC" in summary
        assert "2,000,000" in summary
        assert "datapath" in summary
        assert "memory" in summary
        assert "Harden candidates" in summary


class TestModuleAnalysis:
    """Test ModuleAnalysis data class."""
    
    def test_module_creation(self):
        """Test module creation."""
        mod = ModuleAnalysis(
            name="cpu_core",
            role=ModuleRole.DATAPATH,
            gate_count=1000000,
            area_um2=5000000,
        )
        
        assert mod.name == "cpu_core"
        assert mod.role == ModuleRole.DATAPATH
        assert mod.gate_count == 1000000
    
    def test_module_signals(self):
        """Test module signals."""
        mod = ModuleAnalysis(name="test")
        
        sig1 = SignalInfo(name="clk", width=1, direction="input", is_clock=True)
        sig2 = SignalInfo(name="data", width=32, direction="output")
        
        mod.input_signals.append(sig1)
        mod.output_signals.append(sig2)
        
        assert len(mod.input_signals) == 1
        assert len(mod.output_signals) == 1
        assert mod.input_signals[0].is_clock is True


class TestInterconnect:
    """Test Interconnect data class."""
    
    def test_interconnect_creation(self):
        """Test interconnect creation."""
        ic = Interconnect(
            from_module="cpu",
            to_module="mem",
            signal_count=64,
            signal_width=256,
            interconnect_type=InterconnectType.BUS,
            is_critical=True,
        )
        
        assert ic.from_module == "cpu"
        assert ic.to_module == "mem"
        assert ic.signal_count == 64
        assert ic.interconnect_type == InterconnectType.BUS
    
    def test_interconnect_serialization(self):
        """Test interconnect serialization."""
        ic = Interconnect(
            from_module="cpu",
            to_module="mem",
            signal_count=32,
            interconnect_type=InterconnectType.POINT_TO_POINT,
        )
        
        data = ic.to_dict()
        assert data["from_module"] == "cpu"
        assert data["interconnect_type"] == "p2p"
        
        loaded = Interconnect.from_dict(data)
        assert loaded.from_module == "cpu"
        assert loaded.interconnect_type == InterconnectType.POINT_TO_POINT


class TestSignalFlowPath:
    """Test SignalFlowPath data class."""
    
    def test_path_creation(self):
        """Test path creation."""
        path = SignalFlowPath(
            name="critical_path",
            modules=["cpu", "bus", "mem"],
            total_delay_ns=3.2,
            is_critical=True,
        )
        
        assert path.name == "critical_path"
        assert len(path.modules) == 3
        assert path.is_critical is True
    
    def test_path_serialization(self):
        """Test path serialization."""
        path = SignalFlowPath(
            name="test_path",
            modules=["a", "b", "c"],
            total_delay_ns=2.5,
        )
        
        data = path.to_dict()
        assert data["name"] == "test_path"
        assert data["modules"] == ["a", "b", "c"]
        
        loaded = SignalFlowPath.from_dict(data)
        assert loaded.name == "test_path"
        assert len(loaded.modules) == 3
