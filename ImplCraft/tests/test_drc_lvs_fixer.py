"""Tests for DRC/LVS Fixer — error analysis and ECO generation."""
import pytest
from pathlib import Path
from src.analysis.drc_lvs_fixer import (
    DRCFixer,
    ErrorAnalyzer,
    ECOGenerator,
    DRCError,
    LVSError,
    ErrorAnalysis,
    ECOFix,
    ErrorSeverity,
    Fixability,
    FixType,
)


class TestDRCError:
    """Test DRCError data class."""
    
    def test_error_creation(self):
        """Test error creation."""
        error = DRCError(
            rule_name="M1.S.1",
            layer="M1",
            location=(100, 200, 150, 250),
            severity=ErrorSeverity.HIGH,
        )
        
        assert error.rule_name == "M1.S.1"
        assert error.layer == "M1"
        assert error.severity == ErrorSeverity.HIGH
    
    def test_error_area(self):
        """Test error area calculation."""
        error = DRCError(
            rule_name="test",
            layer="M1",
            location=(0, 0, 100, 200),
        )
        
        assert error.area_um2 == 20000.0


class TestLVSError:
    """Test LVSError data class."""
    
    def test_error_creation(self):
        """Test error creation."""
        error = LVSError(
            error_type="device_mismatch",
            description="Device count mismatch",
            severity=ErrorSeverity.CRITICAL,
        )
        
        assert error.error_type == "device_mismatch"
        assert error.severity == ErrorSeverity.CRITICAL


class TestErrorAnalyzer:
    """Test ErrorAnalyzer functionality."""
    
    def test_analyze_drc(self):
        """Test DRC error analysis."""
        analyzer = ErrorAnalyzer()
        
        drc_results = {
            "errors_by_rule": {
                "M1.S.1": 50,
                "M2.W.1": 30,
                "M3.SP.1": 20,
            },
            "errors_by_layer": {
                "M1": 50,
                "M2": 30,
                "M3": 20,
            },
        }
        
        analysis = analyzer.analyze_drc(drc_results)
        
        assert analysis.total_errors == 100
        assert len(analysis.drc_errors) == 100
        assert analysis.errors_by_rule["M1.S.1"] == 50
        assert analysis.fixable_count > 0
    
    def test_analyze_lvs(self):
        """Test LVS error analysis."""
        analyzer = ErrorAnalyzer()
        
        lvs_results = {
            "device_mismatches": 5,
            "net_mismatches": 3,
            "property_errors": 10,
        }
        
        analysis = analyzer.analyze_lvs(lvs_results)
        
        assert analysis.total_errors == 18
        assert len(analysis.lvs_errors) == 18
        assert analysis.design_change_count == 5  # device mismatches
        assert analysis.manual_required_count == 3  # net mismatches
        assert analysis.fixable_count == 10  # property errors
    
    def test_severity_classification(self):
        """Test severity classification."""
        analyzer = ErrorAnalyzer()
        
        # Critical rules
        assert analyzer._classify_severity("ANT.1", 10) == ErrorSeverity.CRITICAL
        
        # High count
        assert analyzer._classify_severity("M1.S.1", 150) == ErrorSeverity.HIGH
        
        # Medium count
        assert analyzer._classify_severity("M1.S.1", 50) == ErrorSeverity.MEDIUM
        
        # Low count
        assert analyzer._classify_severity("M1.S.1", 5) == ErrorSeverity.LOW
    
    def test_fixability_classification(self):
        """Test fixability classification."""
        analyzer = ErrorAnalyzer()
        
        # Auto-fixable (layer.rule.number format)
        assert analyzer._classify_fixability("M1.W.1") == Fixability.AUTO_FIXABLE
        assert analyzer._classify_fixability("M2.S.1") == Fixability.AUTO_FIXABLE
        assert analyzer._classify_fixability("M3.SP.1") == Fixability.AUTO_FIXABLE
        
        # Also support simple format
        assert analyzer._classify_fixability("W") == Fixability.AUTO_FIXABLE
        assert analyzer._classify_fixability("S") == Fixability.AUTO_FIXABLE
        
        # Manual required
        assert analyzer._classify_fixability("DRC.1") == Fixability.MANUAL_REQUIRED
        
        # Unknown
        assert analyzer._classify_fixability("UNKNOWN") == Fixability.UNKNOWN
    
    def test_recommendations(self):
        """Test recommendation generation."""
        analyzer = ErrorAnalyzer()
        
        analysis = ErrorAnalysis(
            total_errors=100,
            fixable_count=50,
            manual_required_count=30,
            design_change_count=20,
            errors_by_layer={"M1": 80, "M2": 20},
        )
        
        recs = analyzer._generate_recommendations(analysis)
        
        assert len(recs) > 0
        assert any("auto-fixable" in rec for rec in recs)
        assert any("manual" in rec.lower() for rec in recs)


class TestECOGenerator:
    """Test ECOGenerator functionality."""
    
    @pytest.fixture
    def sample_fixes(self):
        """Create sample ECO fixes."""
        return [
            ECOFix(
                fix_id="fix_0001",
                fix_type=FixType.SPACING_ADJUST,
                target="net_123",
                priority=1,
            ),
            ECOFix(
                fix_id="fix_0002",
                fix_type=FixType.ROUTE_REROUTE,
                target="net_456",
                priority=2,
            ),
        ]
    
    def test_generate_drc_eco_icc2(self, sample_fixes):
        """Test ICC2 DRC ECO generation."""
        generator = ECOGenerator()
        
        script = generator.generate_drc_eco(sample_fixes, tool="icc2")
        
        assert "DRC ECO Script" in script
        assert "fix_0001" in script
        assert "fix_0002" in script
        assert "route_opt" in script
        assert "exit" in script
    
    def test_generate_drc_eco_innovus(self, sample_fixes):
        """Test Innovus DRC ECO generation."""
        generator = ECOGenerator()
        
        script = generator.generate_drc_eco(sample_fixes, tool="innovus")
        
        assert "DRC ECO Script" in script
        assert "ecoOptDesign" in script
        assert "exit" in script
    
    def test_generate_lvs_eco_icc2(self, sample_fixes):
        """Test ICC2 LVS ECO generation."""
        generator = ECOGenerator()
        
        fixes = [
            ECOFix(
                fix_id="fix_0001",
                fix_type=FixType.CELL_RESIZE,
                target="cell_123",
                parameters={"new_size": "BUF_X2"},
            )
        ]
        
        script = generator.generate_lvs_eco(fixes, tool="icc2")
        
        assert "LVS ECO Script" in script
        assert "size_cell" in script
        assert "BUF_X2" in script
    
    def test_generate_lvs_eco_innovus(self, sample_fixes):
        """Test Innovus LVS ECO generation."""
        generator = ECOGenerator()
        
        fixes = [
            ECOFix(
                fix_id="fix_0001",
                fix_type=FixType.CELL_RESIZE,
                target="cell_123",
                parameters={"new_size": "BUF_X2"},
            )
        ]
        
        script = generator.generate_lvs_eco(fixes, tool="innovus")
        
        assert "LVS ECO Script" in script
        assert "resizeInst" in script
        assert "BUF_X2" in script


class TestDRCFixer:
    """Test DRCFixer main interface."""
    
    def test_fixer_initialization(self):
        """Test fixer initialization."""
        fixer = DRCFixer()
        
        assert fixer.analyzer is not None
        assert fixer.eco_generator is not None
    
    def test_create_fix_plan(self):
        """Test fix plan creation."""
        fixer = DRCFixer()
        
        analysis = ErrorAnalysis(
            total_errors=100,
            drc_errors=[
                DRCError(
                    rule_name="M1.S.1",
                    layer="M1",
                    location=(0, 0, 100, 100),
                    fixability=Fixability.AUTO_FIXABLE,
                    severity=ErrorSeverity.HIGH,
                )
                for _ in range(100)
            ],
        )
        
        fixes = fixer.create_fix_plan(analysis, max_fixes_per_iteration=50)
        
        assert len(fixes) == 50
        assert all(f.fix_id.startswith("fix_") for f in fixes)
    
    def test_generate_eco_scripts(self, tmp_path):
        """Test ECO script generation."""
        fixer = DRCFixer()
        
        fixes = [
            ECOFix(
                fix_id="fix_0001",
                fix_type=FixType.ROUTE_REROUTE,
                target="net_123",
            )
        ]
        
        scripts = fixer.generate_eco_scripts(
            fixes,
            output_dir=tmp_path,
            tool="icc2",
            is_drc=True,
        )
        
        assert "drc_eco" in scripts
        assert "report" in scripts
        assert scripts["drc_eco"].exists()
        assert scripts["report"].exists()
        
        # Check script content
        script_content = scripts["drc_eco"].read_text()
        assert "fix_0001" in script_content


class TestErrorAnalysis:
    """Test ErrorAnalysis data class."""
    
    def test_analysis_creation(self):
        """Test analysis creation."""
        analysis = ErrorAnalysis(
            total_errors=100,
            fixable_count=60,
            manual_required_count=30,
            design_change_count=10,
        )
        
        assert analysis.total_errors == 100
        assert analysis.fixable_count == 60
    
    def test_analysis_summary(self):
        """Test summary generation."""
        analysis = ErrorAnalysis(
            total_errors=100,
            errors_by_severity={"high": 30, "medium": 50, "low": 20},
            errors_by_fixability={"auto_fixable": 60, "manual_required": 30},
            errors_by_rule={"M1.S.1": 50, "M2.W.1": 30},
            recommendations=["Run ECO first"],
        )
        
        summary = analysis.summary()
        
        assert "Error Analysis Summary" in summary
        assert "Total errors: 100" in summary
        assert "high: 30" in summary
        assert "M1.S.1: 50" in summary
        assert "Run ECO first" in summary


class TestECOFix:
    """Test ECOFix data class."""
    
    def test_fix_creation(self):
        """Test fix creation."""
        fix = ECOFix(
            fix_id="fix_0001",
            fix_type=FixType.SPACING_ADJUST,
            target="net_123",
            parameters={"spacing": 0.1},
            priority=1,
            expected_impact="Fix spacing violations",
        )
        
        assert fix.fix_id == "fix_0001"
        assert fix.fix_type == FixType.SPACING_ADJUST
        assert fix.priority == 1
        assert fix.applied is False


class TestIntegration:
    """Integration tests for DRC/LVS Fixer."""
    
    def test_complete_drc_flow(self, tmp_path):
        """Test complete DRC fix flow."""
        fixer = DRCFixer()
        
        # Analyze errors
        drc_results = {
            "errors_by_rule": {
                "M1.S.1": 50,
                "M2.W.1": 30,
            },
            "errors_by_layer": {
                "M1": 50,
                "M2": 30,
            },
        }
        
        analysis = fixer.analyzer.analyze_drc(drc_results)
        
        assert analysis.total_errors == 80
        assert len(analysis.recommendations) > 0
        
        # Create fix plan
        fixes = fixer.create_fix_plan(analysis, max_fixes_per_iteration=20)
        
        assert len(fixes) == 20
        
        # Generate scripts
        scripts = fixer.generate_eco_scripts(
            fixes,
            output_dir=tmp_path,
            tool="icc2",
            is_drc=True,
        )
        
        assert scripts["drc_eco"].exists()
        assert scripts["report"].exists()
    
    def test_complete_lvs_flow(self, tmp_path):
        """Test complete LVS fix flow."""
        fixer = DRCFixer()
        
        # Analyze errors
        lvs_results = {
            "device_mismatches": 5,
            "net_mismatches": 3,
            "property_errors": 10,
        }
        
        analysis = fixer.analyzer.analyze_lvs(lvs_results)
        
        assert analysis.total_errors == 18
        
        # Create fix plan (only for fixable errors)
        fixes = fixer.create_fix_plan(analysis, max_fixes_per_iteration=10)
        
        # Generate scripts
        scripts = fixer.generate_eco_scripts(
            fixes,
            output_dir=tmp_path,
            tool="icc2",
            is_drc=False,
        )
        
        assert scripts["lvs_eco"].exists()
        assert scripts["report"].exists()
