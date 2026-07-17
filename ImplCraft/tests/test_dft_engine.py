"""Tests for DFT Engine — scan chain, BIST, repair, ATPG."""
import pytest
import json
from pathlib import Path
from src.analysis.dft_engine import (
    DFTEngine,
    DFTConfig,
    DFTTool,
    ScanChainConfig,
    ScanArchitecture,
    BISTConfig,
    BISTArchitecture,
    RepairConfig,
    RepairStrategy,
    ATPGConfig,
    SRAMSpec,
    ScanInsertionEngine,
    BISTInsertionEngine,
    RepairLogicEngine,
    ATPGEngine,
)


@pytest.fixture
def sample_srams():
    """Sample SRAM specifications."""
    return [
        SRAMSpec(name="sram_256x32", depth=256, width=32,
                 has_redundancy=True, spare_rows=2, spare_cols=1),
        SRAMSpec(name="sram_1024x64", depth=1024, width=64,
                 has_redundancy=True, spare_rows=4, spare_cols=2),
        SRAMSpec(name="sram_512x16", depth=512, width=16,
                 has_redundancy=False),
    ]


@pytest.fixture
def sample_config(sample_srams):
    """Sample DFT configuration."""
    return DFTConfig(
        tool=DFTTool.DFT_COMPILER,
        design_name="test_soc",
        srams=sample_srams,
        scan=ScanChainConfig(
            architecture=ScanArchitecture.FULL_SCAN,
            num_chains=4,
            clock_domain="clk",
            scan_enable_signal="scan_en",
        ),
        bist=BISTConfig(
            architecture=BISTArchitecture.MARCH,
            algorithm="march_c_plus",
            bist_controller_type="shared",
            max_srams_per_controller=8,
        ),
        repair=RepairConfig(
            strategy=RepairStrategy.ROW_COL,
            fuse_type="efuse",
        ),
        atpg=ATPGConfig(
            fault_model="stuck_at",
            coverage_target=0.99,
            max_patterns=50000,
        ),
    )


class TestSRAMSpec:
    """Test SRAMSpec."""
    
    def test_auto_address_width(self):
        """Test auto address width calculation."""
        sram = SRAMSpec(name="test", depth=256, width=32)
        assert sram.address_width == 8  # log2(256)
        assert sram.data_width == 32
    
    def test_explicit_address_width(self):
        """Test explicit address width."""
        sram = SRAMSpec(name="test", depth=256, width=32, address_width=10)
        assert sram.address_width == 10


class TestScanInsertionEngine:
    """Test scan insertion script generation."""
    
    def test_generate_dft_compiler_script(self, sample_config):
        """Test DFT Compiler scan script."""
        engine = ScanInsertionEngine(sample_config)
        script = engine.generate_script(DFTTool.DFT_COMPILER)
        
        assert "DFT Compiler" in script
        assert "insert_scan" in script
        assert "chain_count 4" in script
        assert "scan_en" in script
        assert "check_scan" in script
    
    def test_generate_tessent_script(self, sample_config):
        """Test Tessent scan script."""
        engine = ScanInsertionEngine(sample_config)
        script = engine.generate_script(DFTTool.TESSENT)
        
        assert "Tessent" in script
        assert "AddScanCells" in script
        assert "StitchScanChains" in script
    
    def test_generate_genus_script(self, sample_config):
        """Test Genus scan script."""
        engine = ScanInsertionEngine(sample_config)
        script = engine.generate_script(DFTTool.GENUS_DFT)
        
        assert "Genus DFT" in script
        assert "dft_scan_chains" in script


class TestBISTInsertionEngine:
    """Test BIST insertion script generation."""
    
    def test_generate_bist_script(self, sample_config):
        """Test BIST insertion script."""
        engine = BISTInsertionEngine(sample_config)
        script = engine.generate_script()
        
        assert "Memory BIST" in script
        assert "march_c_plus" in script
        assert "insert_bist" in script
        assert "check_bist" in script
        assert "sram_256x32" in script
    
    def test_shared_controller_grouping(self, sample_config):
        """Test shared controller groups SRAMs."""
        engine = BISTInsertionEngine(sample_config)
        script = engine.generate_script()
        
        assert "bist_ctrl_0" in script
    
    def test_tessent_bist(self, sample_config):
        """Test Tessent BIST script."""
        engine = BISTInsertionEngine(sample_config)
        script = engine.generate_script(DFTTool.TESSENT)
        
        assert "Tessent" in script
        assert "InsertMemoryBist" in script


class TestRepairLogicEngine:
    """Test repair logic insertion."""
    
    def test_generate_repair_script(self, sample_config):
        """Test repair logic script."""
        engine = RepairLogicEngine(sample_config)
        script = engine.generate_script()
        
        assert "Memory Repair" in script
        assert "row_col" in script
        assert "efuse" in script
        assert "insert_repair_logic" in script
        assert "sram_256x32" in script
        assert "sram_1024x64" in script
    
    def test_repairable_only(self, sample_config):
        """Test only repairable SRAMs are included."""
        engine = RepairLogicEngine(sample_config)
        script = engine.generate_script()
        
        # sram_512x16 has no redundancy, should not be in repair script
        assert "sram_512x16" not in script
    
    def test_generate_verilog_wrapper(self, sample_config):
        """Test Verilog wrapper generation."""
        engine = RepairLogicEngine(sample_config)
        sram = sample_config.srams[0]
        
        wrapper = engine.generate_verilog_wrapper(sram)
        
        assert "module sram_256x32_repair_wrapper" in wrapper
        assert "repair_fuse" in wrapper
        assert "addr_remap" in wrapper
        assert "repair_pass" in wrapper


class TestATPGEngine:
    """Test ATPG pattern generation."""
    
    def test_generate_dft_compiler_atpg(self, sample_config):
        """Test DFT Compiler ATPG script."""
        engine = ATPGEngine(sample_config)
        script = engine.generate_script(DFTTool.DFT_COMPILER)
        
        assert "ATPG" in script
        assert "stuck_at" in script
        assert "0.99" in script
        assert "create_faults" in script
        assert "create_patterns" in script
    
    def test_generate_tessent_atpg(self, sample_config):
        """Test Tessent ATPG script."""
        engine = ATPGEngine(sample_config)
        script = engine.generate_script(DFTTool.TESSENT)
        
        assert "Tessent ATPG" in script
        assert "CreateFaults" in script
        assert "CreatePatterns" in script
    
    def test_generate_testbench(self, sample_config):
        """Test Verilog testbench generation."""
        engine = ATPGEngine(sample_config)
        tb = engine.generate_verilog_testbench()
        
        assert "module test_soc_atpg_tb" in tb
        assert "scan_en" in tb
        assert "scan_out" in tb


class TestDFTEngine:
    """Test main DFT engine."""
    
    def test_engine_initialization(self, sample_config):
        """Test engine initialization."""
        engine = DFTEngine(sample_config)
        
        assert engine.scan is not None
        assert engine.bist is not None
        assert engine.repair is not None
        assert engine.atpg is not None
    
    def test_write_all_scripts(self, sample_config, tmp_path):
        """Test writing all DFT scripts."""
        engine = DFTEngine(sample_config)
        scripts = engine.write_all_scripts(tmp_path)
        
        assert "scan" in scripts
        assert "bist" in scripts
        assert "repair" in scripts
        assert "atpg" in scripts
        assert "flow" in scripts
        
        # Check files exist
        for name, path in scripts.items():
            assert path.exists(), f"Script {name} not found at {path}"
    
    def test_get_summary(self, sample_config):
        """Test summary generation."""
        engine = DFTEngine(sample_config)
        summary = engine.get_summary()
        
        assert "DFT Configuration Summary" in summary
        assert "test_soc" in summary
        assert "sram_256x32" in summary
        assert "march_c_plus" in summary
        assert "stuck_at" in summary


class TestDFTConfig:
    """Test DFT configuration."""
    
    def test_save_and_load(self, sample_config, tmp_path):
        """Test config save and load."""
        config_path = tmp_path / "dft_config.json"
        sample_config.save(config_path)
        
        assert config_path.exists()
        
        # Load back
        loaded = DFTConfig.from_file(config_path)
        
        assert loaded.design_name == sample_config.design_name
        assert loaded.tool == sample_config.tool
        assert loaded.scan.num_chains == sample_config.scan.num_chains


class TestIntegration:
    """Integration tests for DFT engine."""
    
    def test_complete_dft_flow(self, sample_config, tmp_path):
        """Test complete DFT flow."""
        engine = DFTEngine(sample_config)
        
        # Generate all scripts
        scripts = engine.write_all_scripts(tmp_path)
        
        # Verify all stages
        assert len(scripts) >= 5
        
        # Verify scan script content
        scan_content = scripts["scan"].read_text()
        assert "insert_scan" in scan_content
        
        # Verify BIST script content
        bist_content = scripts["bist"].read_text()
        assert "insert_bist" in bist_content
        
        # Verify repair script content
        repair_content = scripts["repair"].read_text()
        assert "insert_repair_logic" in repair_content
        
        # Verify ATPG script content
        atpg_content = scripts["atpg"].read_text()
        assert "create_patterns" in atpg_content
        
        # Verify flow script
        flow_content = scripts["flow"].read_text()
        assert "scan_insertion.tcl" in flow_content
        assert "bist_insertion.tcl" in flow_content
        assert "repair_insertion.tcl" in flow_content
        assert "atpg_patterns.tcl" in flow_content
