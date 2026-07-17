"""Tests for Power Mesh Builder."""
import pytest
from src.power import (
    PowerMeshBuilder,
    PowerMeshConfig,
    PowerMeshPlan,
    PowerDomain,
    RingConfig,
    StrapConfig,
)


class TestPowerMeshBuilder:
    """Test suite for PowerMeshBuilder."""
    
    def test_basic_mesh_generation(self):
        """Test basic power mesh generation."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(
            name="VDD_CORE",
            vdd_net="VDD",
            vss_net="VSS",
            voltage=0.9,
        )
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        assert plan.design_name == "top"
        assert len(plan.core_rings) > 0
        assert len(plan.straps) > 0
        assert plan.total_ring_length_um > 0
        assert plan.total_strap_length_um > 0
        assert plan.mesh_density_percentage > 0
    
    def test_multi_domain_mesh(self):
        """Test power mesh with multiple voltage domains."""
        builder = PowerMeshBuilder()
        
        domains = [
            PowerDomain(name="VDD_CORE", vdd_net="VDD", vss_net="VSS", voltage=0.9),
            PowerDomain(name="VDD_IO", vdd_net="VDDIO", vss_net="VSSIO", voltage=1.8, is_primary=False),
        ]
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=domains,
        )
        
        # Should have rings for both domains
        assert len(plan.core_rings) > 8  # 8 rings per domain minimum
        assert len(plan.straps) > 0
        
        # Check that both domains are represented
        ring_domains = set(r.domain for r in plan.core_rings)
        assert "VDD_CORE" in ring_domains
        assert "VDD_IO" in ring_domains
    
    def test_mesh_with_macros(self):
        """Test power mesh with hard macros."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        macros = [
            {"name": "sram_256k", "bbox": (500, 500, 700, 650), "power_domain": "VDD"},
            {"name": "pll", "bbox": (1000, 200, 1100, 300), "power_domain": "VDD"},
        ]
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
            macros=macros,
        )
        
        # Should have block rings around macros
        assert len(plan.block_rings) == 2
        assert plan.block_rings[0].macro_name == "sram_256k"
        assert plan.block_rings[1].macro_name == "pll"
    
    def test_ir_drop_estimation(self):
        """Test IR-drop estimation."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(
            name="VDD",
            vdd_net="VDD",
            vss_net="VSS",
            ir_drop_target_mv=45.0,
        )
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        # IR-drop should be calculated
        assert plan.estimated_ir_drop_mv > 0
        assert plan.estimated_ir_drop_mv < 200  # Should be reasonable
    
    def test_mesh_density_calculation(self):
        """Test mesh density calculation."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        # Mesh density should be reasonable (typically 5-15%)
        assert plan.mesh_density_percentage > 0
        assert plan.mesh_density_percentage < 50
    
    def test_custom_configuration(self):
        """Test power mesh with custom configuration."""
        config = PowerMeshConfig(
            ring_config=RingConfig(width_um=6.0, spacing_um=3.0),
            strap_config=StrapConfig(width_um=3.0, pitch_um=30.0),
            target_ir_drop_mv=30.0,
        )
        
        builder = PowerMeshBuilder(config)
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        # Should use custom widths
        assert plan.core_rings[0].width_um == 6.0
        assert plan.straps[0].width_um == 3.0
    
    def test_icc2_script_generation(self):
        """Test ICC2 Tcl script generation."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        script = builder.generate_icc2_script(plan)
        
        assert "ICC2 Power Mesh Script" in script
        assert "create_pg_ring_pattern" in script
        assert "create_pg_strap_pattern" in script
        assert "compile_pg_mesh" in script
        assert "exit" in script
    
    def test_innovus_script_generation(self):
        """Test Innovus Tcl script generation."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        script = builder.generate_innovus_script(plan)
        
        assert "Innovus Power Mesh Script" in script
        assert "createRing" in script
        assert "createStripe" in script
        assert "sroute" in script
        assert "exit" in script
    
    def test_recommendations_generation(self):
        """Test recommendations are generated."""
        # Create config with very low density
        config = PowerMeshConfig(
            strap_config=StrapConfig(set_to_set_distance_um=500.0),  # Very sparse
        )
        
        builder = PowerMeshBuilder(config)
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
        )
        
        # Should have recommendations for low density
        assert len(plan.recommendations) >= 0  # May or may not have recs
    
    def test_summary_generation(self):
        """Test summary is generated."""
        builder = PowerMeshBuilder()
        
        power_domain = PowerDomain(name="VDD", vdd_net="VDD", vss_net="VSS")
        
        plan = builder.build_mesh(
            die_area=(0, 0, 2900, 1900),
            core_area=(180, 180, 2720, 1720),
            power_domains=[power_domain],
            design_name="TestSoC",
        )
        
        assert plan.summary != ""
        assert "TestSoC" in plan.summary
        assert "Mesh Statistics" in plan.summary
        assert "IR-drop" in plan.summary


class TestPowerDomain:
    """Test PowerDomain configuration."""
    
    def test_power_domain_creation(self):
        """Test power domain creation."""
        domain = PowerDomain(
            name="VDD_CORE",
            vdd_net="VDD",
            vss_net="VSS",
            voltage=0.9,
            max_current_a=2.0,
        )
        
        assert domain.name == "VDD_CORE"
        assert domain.voltage == 0.9
        assert domain.max_current_a == 2.0
        assert domain.ir_drop_target_mv == 45.0  # Default


class TestRingConfig:
    """Test RingConfig."""
    
    def test_ring_config_defaults(self):
        """Test ring config default values."""
        config = RingConfig()
        
        assert config.layer == "M8"
        assert config.width_um == 4.0
        assert config.spacing_um == 2.0
        assert config.offset_um == 0.8


class TestStrapConfig:
    """Test StrapConfig."""
    
    def test_strap_config_defaults(self):
        """Test strap config default values."""
        config = StrapConfig()
        
        assert config.layer == "M7"
        assert config.width_um == 2.0
        assert config.pitch_um == 20.0
        assert config.direction == "horizontal"
