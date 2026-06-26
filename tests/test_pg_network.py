"""Tests for PG network advisor."""
import pytest
import math
from pathlib import Path

from src.analysis.pg_network_advisor import (
    PGNetworkAdvisor,
    PGNetworkPlan,
    PowerConfig,
    PadSpec,
    PadType,
    PlacementStrategy,
)


def test_pg_pad_count_calculation():
    """Test PG pad count calculation based on power requirements."""
    advisor = PGNetworkAdvisor()
    
    # 1W design at 0.9V = 1.11A total current
    # With 0.1A per pad limit, need ~6 pads per supply (VDD/VSS)
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        max_current_a=0.1,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        pad_spec=pad_spec,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )
    
    # Expected: 1.11A / (2 * 0.1A) = 5.55 -> 6 pads per supply
    # With 20% safety margin: 12 * 1.2 = 14.4 -> 15 total
    assert plan.vdd_pads_needed == 6
    assert plan.vss_pads_needed == 6
    assert plan.total_pg_pads_needed >= 12


def test_pg_pad_uniform_placement():
    """Test uniform PG pad placement."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        placement_strategy=PlacementStrategy.UNIFORM,
        num_io_pads=50,
    )
    
    # Check pads are placed
    assert len(plan.pg_pad_placements) > 0
    
    # Check alternating VDD/VSS
    vdd_count = sum(1 for p in plan.pg_pad_placements if p.net_name == "VDD")
    vss_count = sum(1 for p in plan.pg_pad_placements if p.net_name == "VSS")
    assert vdd_count > 0
    assert vss_count > 0
    assert abs(vdd_count - vss_count) <= 1  # Should be roughly equal


def test_pg_pad_clustered_placement():
    """Test clustered PG pad placement."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=2.0,  # Higher power = more pads
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        placement_strategy=PlacementStrategy.CLUSTERED,
        num_io_pads=50,
    )
    
    # Check pads are placed in clusters
    assert len(plan.pg_pad_placements) > 0
    
    # Clustered placement should group pads
    # Check that some pads are close together (within cluster)
    if len(plan.pg_pad_placements) >= 4:
        distances = []
        for i in range(len(plan.pg_pad_placements) - 1):
            pad1 = plan.pg_pad_placements[i]
            pad2 = plan.pg_pad_placements[i + 1]
            dist = math.sqrt((pad1.x_um - pad2.x_um)**2 + (pad1.y_um - pad2.y_um)**2)
            distances.append(dist)
        
        # In clustered placement, some distances should be small (within cluster)
        # and some should be large (between clusters)
        min_dist = min(distances)
        max_dist = max(distances)
        assert max_dist > min_dist * 3  # Clusters should be separated


def test_io_pad_placement():
    """Test I/O pad placement."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    num_io = 100
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        num_io_pads=num_io,
    )
    
    # Check I/O pads are placed
    assert len(plan.io_pad_placements) == num_io
    
    # Check all I/O pads have correct type
    for pad in plan.io_pad_placements:
        assert pad.pad_type == PadType.IO_PAD
        assert pad.net_name.startswith("IO_")


def test_bond_pad_placement():
    """Test bond pad placement."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    num_bond = 50
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        num_io_pads=100,
        num_bond_pads=num_bond,
    )
    
    # Check bond pads are placed
    assert len(plan.bond_pad_placements) == num_bond
    
    # Check bond pads are larger than regular pads
    for pad in plan.bond_pad_placements:
        assert pad.pad_type == PadType.BOND_PAD
        assert pad.width_um >= 80.0  # Default pad width is 80um
        assert pad.height_um >= 80.0


def test_ir_drop_estimation():
    """Test IR-drop estimation."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=2.0,  # Higher power = higher IR-drop
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )
    
    # IR-drop should be calculated
    assert plan.estimated_ir_drop_mv > 0
    
    # IR-drop should be reasonable (< 500mV for this design)
    assert plan.estimated_ir_drop_mv < 500


def test_power_config_multiple_domains():
    """Test power configuration with multiple domains."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        vddq_voltage=1.8,
        total_power_w=1.5,
        core_power_w=1.0,
        io_power_w=0.5,
        num_power_domains=2,
        power_domain_names=["VDD", "VDDQ"],
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )
    
    # Should have recommendations for multiple domains
    assert any("multiple power domains" in rec.lower() for rec in plan.recommendations)


def test_pg_script_generation():
    """Test ICC2 PG script generation."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        num_io_pads=50,
    )
    
    # Generate script
    output_path = "/tmp/test_pg.tcl"
    advisor.generate_pg_script(plan, output_path, tool="icc2")
    
    # Check file exists
    assert Path(output_path).exists()
    
    # Check script content
    content = Path(output_path).read_text()
    assert "create_pg_ring_pattern" in content
    assert "create_pg_mesh_pattern" in content
    assert "compile_pg" in content
    assert "create_pg_pad" in content
    
    # Check pads are in script
    for pad in plan.pg_pad_placements[:5]:  # Check first 5
        assert pad.net_name in content
    
    # Cleanup
    Path(output_path).unlink()


def test_corner_placement_strategy():
    """Test corner placement strategy."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.5,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        placement_strategy=PlacementStrategy.CORNER,
        num_io_pads=50,
    )
    
    # Check pads are placed
    assert len(plan.pg_pad_placements) > 0
    
    # Corner placement should concentrate pads near corners
    # Check that some pads are near corners
    corner_threshold = 500  # um from corner
    
    corners = [
        (0, 0),
        (2900, 0),
        (2900, 1900),
        (0, 1900),
    ]
    
    near_corner_count = 0
    for pad in plan.pg_pad_placements:
        for cx, cy in corners:
            dist = math.sqrt((pad.x_um - cx)**2 + (pad.y_um - cy)**2)
            if dist < corner_threshold:
                near_corner_count += 1
                break
    
    # At least 50% of pads should be near corners
    assert near_corner_count >= len(plan.pg_pad_placements) * 0.5


def test_high_power_design():
    """Test PG planning for high-power design."""
    advisor = PGNetworkAdvisor()
    
    # High power: 5W at 0.9V = 5.56A
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=5.0,
    )
    
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        max_current_a=0.05,  # Lower current limit
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        pad_spec=pad_spec,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )
    
    # Should need many pads
    assert plan.total_pg_pads_needed > 50
    
    # Should have recommendations about high pad count
    assert len(plan.recommendations) > 0


def test_low_power_design():
    """Test PG planning for low-power design."""
    advisor = PGNetworkAdvisor()
    
    # Low power: 0.1W at 0.9V = 0.11A
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=0.1,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=1000.0,  # Small die
        die_height_um=1000.0,
    )
    
    # Should need few pads
    assert plan.total_pg_pads_needed >= 2  # Minimum 1 VDD + 1 VSS
    assert plan.total_pg_pads_needed < 20


def test_summary_generation():
    """Test summary report generation."""
    advisor = PGNetworkAdvisor()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.0,
    )
    
    plan = advisor.plan_pg_network(
        power_config=power_config,
        die_width_um=2900.0,
        die_height_um=1900.0,
        num_io_pads=100,
    )
    
    # Check summary is generated
    assert plan.summary is not None
    assert len(plan.summary) > 0
    
    # Check summary contains key information
    assert "PG NETWORK PLAN" in plan.summary
    assert "PG PAD REQUIREMENTS" in plan.summary
    assert "PLACEMENT SUMMARY" in plan.summary
    assert "POWER INTEGRITY ANALYSIS" in plan.summary
    
    # Check numbers are in summary
    assert str(plan.total_pg_pads_needed) in plan.summary
    assert str(len(plan.io_pad_placements)) in plan.summary
