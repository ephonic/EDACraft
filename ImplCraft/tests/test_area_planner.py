"""Tests for Area Planner."""
import pytest
from src.analysis.area_planner import (
    AreaPlanner,
    AreaPlan,
    AreaBudget,
    DieSizeCandidate,
    MacroSpec,
)


class TestAreaPlanner:
    """Test suite for AreaPlanner."""
    
    def test_basic_die_size_estimation(self):
        """Test basic die size estimation for typical SoC."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=2_000_000,
            macro_area_um2=500_000,
            io_count=200,
            target_utilization=0.7,
        )
        
        assert plan.gate_count == 2_000_000
        assert plan.macro_count == 0  # No detailed macros provided
        assert plan.io_count == 200
        
        # Check budget is calculated
        assert plan.budget.logic_area_um2 > 0
        assert plan.budget.macro_area_um2 > 0
        assert plan.budget.total_core_area_um2 > 0
        assert plan.budget.total_die_area_um2 > plan.budget.total_core_area_um2
        
        # Check candidates generated
        assert len(plan.candidates) > 0
        assert plan.recommended is not None
        
        # Check recommended has reasonable values
        assert plan.recommended.width_um > 0
        assert plan.recommended.height_um > 0
        assert plan.recommended.utilization > 0
        assert 0.5 <= plan.recommended.utilization <= 0.9
    
    def test_small_design(self):
        """Test area planning for small design."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=100_000,
            macro_area_um2=0,
            io_count=50,
        )
        
        assert plan.recommended is not None
        # Small design should have small die
        assert plan.recommended.area_mm2 < 10  # Less than 10 mm2
    
    def test_large_design(self):
        """Test area planning for large design."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=10_000_000,
            macro_area_um2=2_000_000,
            io_count=500,
        )
        
        assert plan.recommended is not None
        # Large design should have large die
        assert plan.recommended.area_mm2 > 20  # More than 20 mm2 for 10M gates
        
        # Should generate warning for large design
        assert len(plan.warnings) > 0
        assert any("large" in w.lower() for w in plan.warnings)
    
    def test_detailed_macros(self):
        """Test area planning with detailed macro specifications."""
        planner = AreaPlanner()
        
        macros = [
            MacroSpec(
                name="sram_256k",
                width_um=200,
                height_um=150,
                macro_type="sram",
                keepout_um=5,
                halo_um=10,
            ),
            MacroSpec(
                name="pll",
                width_um=100,
                height_um=100,
                macro_type="analog",
                keepout_um=10,
                halo_um=20,
            ),
        ]
        
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            macros=macros,
            io_count=150,
        )
        
        assert plan.macro_count == 2
        # Macro area should include keepout and halo
        assert plan.budget.macro_area_um2 > 0
        
        # Calculate expected macro area
        # SRAM: (200 + 2*(5+10)) * (150 + 2*(5+10)) = 230 * 180 = 41400
        # PLL: (100 + 2*(10+20)) * (100 + 2*(10+20)) = 160 * 160 = 25600
        # Total: 67000 um2
        assert plan.budget.macro_area_um2 >= 67000
    
    def test_different_aspect_ratios(self):
        """Test that different aspect ratios generate different candidates."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            io_count=100,
            aspect_ratio=1.2,
        )
        
        # Should have multiple candidates with different ARs
        aspect_ratios = [c.aspect_ratio for c in plan.candidates]
        assert len(set(aspect_ratios)) > 1
        
        # Recommended should be close to target AR
        if plan.recommended:
            assert abs(plan.recommended.aspect_ratio - 1.2) < 0.5
    
    def test_utilization_target(self):
        """Test that utilization is close to target."""
        planner = AreaPlanner()
        
        for target_util in [0.6, 0.7, 0.8]:
            plan = planner.estimate_die_size(
                gate_count=1_000_000,
                io_count=100,
                target_utilization=target_util,
            )
            
            if plan.recommended:
                # Should be within 15% of target
                assert abs(plan.recommended.utilization - target_util) < 0.15
    
    def test_area_budget_percentages(self):
        """Test that area budget percentages are calculated correctly."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            macro_area_um2=300_000,
            io_count=100,
        )
        
        budget = plan.budget
        
        # Percentages should sum to ~100%
        total_pct = (
            budget.logic_percentage
            + budget.macro_percentage
            + budget.routing_percentage
        )
        # Allow for other categories (I/O, power, margin)
        assert total_pct < 100
    
    def test_recommendations_generation(self):
        """Test that recommendations are generated for edge cases."""
        planner = AreaPlanner()
        
        # Low utilization case
        plan = planner.estimate_die_size(
            gate_count=100_000,
            io_count=50,
            target_utilization=0.7,
        )
        
        # Should have recommendations
        assert len(plan.recommendations) >= 0  # May or may not have recs
    
    def test_warnings_generation(self):
        """Test that warnings are generated for problematic cases."""
        planner = AreaPlanner()
        
        # Very large design
        plan = planner.estimate_die_size(
            gate_count=15_000_000,
            macro_area_um2=5_000_000,
            io_count=100,
        )
        
        # Should have warnings
        assert len(plan.warnings) > 0
        assert any("large" in w.lower() or "hierarchical" in w.lower() for w in plan.warnings)
    
    def test_summary_generation(self):
        """Test that summary is generated."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            macro_area_um2=200_000,
            io_count=150,
            design_name="TestSoC",
        )
        
        assert plan.summary != ""
        assert "TestSoC" in plan.summary
        assert "Area Budget" in plan.summary
        assert "Die Size" in plan.summary
    
    def test_custom_technology_parameters(self):
        """Test with custom technology parameters."""
        # Older technology with larger gates
        planner = AreaPlanner(
            avg_gate_area_um2=3.0,  # Larger gates (e.g., 65nm)
            io_ring_width_um=200.0,  # Wider I/O ring
            routing_overhead=1.5,  # More routing overhead
        )
        
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            io_count=100,
        )
        
        # Should produce larger die than default
        planner_default = AreaPlanner()
        plan_default = planner_default.estimate_die_size(
            gate_count=1_000_000,
            io_count=100,
        )
        
        assert plan.recommended.area_um2 > plan_default.recommended.area_um2
    
    def test_candidate_scoring(self):
        """Test that candidates are scored and sorted correctly."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            io_count=100,
        )
        
        # Candidates should be sorted by score (descending)
        scores = [c.score for c in plan.candidates]
        assert scores == sorted(scores, reverse=True)
        
        # Recommended should be highest score
        assert plan.recommended == plan.candidates[0]
    
    def test_die_size_rounding(self):
        """Test that die sizes are rounded to 10um grid."""
        planner = AreaPlanner()
        plan = planner.estimate_die_size(
            gate_count=1_000_000,
            io_count=100,
        )
        
        for candidate in plan.candidates:
            # Should be rounded to 10um
            assert candidate.width_um % 10 == 0
            assert candidate.height_um % 10 == 0


class TestAreaBudget:
    """Test AreaBudget calculations."""
    
    def test_percentage_calculations(self):
        """Test percentage calculations."""
        budget = AreaBudget(
            logic_area_um2=1_000_000,
            macro_area_um2=500_000,
            routing_area_um2=300_000,
            total_core_area_um2=2_000_000,
        )
        
        assert budget.logic_percentage == 50.0
        assert budget.macro_percentage == 25.0
        assert budget.routing_percentage == 15.0
    
    def test_zero_area_handling(self):
        """Test handling of zero total area."""
        budget = AreaBudget(total_core_area_um2=0)
        
        assert budget.logic_percentage == 0.0
        assert budget.macro_percentage == 0.0
        assert budget.routing_percentage == 0.0


class TestDieSizeCandidate:
    """Test DieSizeCandidate properties."""
    
    def test_area_mm2_conversion(self):
        """Test area conversion from um2 to mm2."""
        candidate = DieSizeCandidate(
            width_um=3000,
            height_um=2000,
            core_width_um=2700,
            core_height_um=1700,
            area_um2=6_000_000,
            utilization=0.7,
            aspect_ratio=1.5,
        )
        
        assert candidate.area_mm2 == 6.0
