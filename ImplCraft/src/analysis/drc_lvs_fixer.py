"""
DRC/LVS Fixer — provides interfaces for error analysis and ECO generation.

Design philosophy:
- Analyze errors and classify by fixability
- Provide ECO script templates
- Leave fix decisions to AI agents
- Support iterative fix cycles

Key interfaces:
1. ErrorAnalyzer — classify and prioritize errors
2. ECOGenerator — generate fix scripts
3. FixValidator — validate fixes

Usage:
    fixer = DRCFixer()
    
    # Analyze errors
    analysis = fixer.analyzer.analyze(drc_results)
    
    # Agent decides fix strategy
    fixes = agent.decide_fixes(analysis)
    
    # Generate ECO scripts
    scripts = fixer.eco_generator.generate(fixes)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Dict, Optional
from pathlib import Path

logger = logging.getLogger("ic_backend")


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Fixability(Enum):
    """How fixable an error is."""
    AUTO_FIXABLE = "auto_fixable"      # Can be fixed automatically
    MANUAL_REQUIRED = "manual_required"  # Requires manual intervention
    DESIGN_CHANGE = "design_change"    # Requires RTL/netlist change
    UNKNOWN = "unknown"


class FixType(Enum):
    """Types of fixes."""
    SPACING_ADJUST = "spacing_adjust"
    WIDTH_ADJUST = "width_adjust"
    ROUTE_REROUTE = "route_reroute"
    VIA_ADD = "via_add"
    VIA_REMOVE = "via_remove"
    CELL_MOVE = "cell_move"
    CELL_RESIZE = "cell_resize"
    NET_RECONNECT = "net_reconnect"
    DEVICE_RESIZE = "device_resize"


@dataclass
class DRCError:
    """Single DRC error."""
    rule_name: str
    layer: str
    location: tuple[float, float, float, float]  # x1, y1, x2, y2
    description: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    fixability: Fixability = Fixability.UNKNOWN
    suggested_fix: str = ""
    
    @property
    def area_um2(self) -> float:
        x1, y1, x2, y2 = self.location
        return (x2 - x1) * (y2 - y1)


@dataclass
class LVSError:
    """Single LVS error."""
    error_type: str  # device_mismatch, net_mismatch, property_error
    location: str = ""
    description: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    fixability: Fixability = Fixability.UNKNOWN
    suggested_fix: str = ""
    
    # Details
    layout_device: str = ""
    source_device: str = ""
    layout_net: str = ""
    source_net: str = ""


@dataclass
class ErrorAnalysis:
    """Analysis of DRC/LVS errors."""
    total_errors: int = 0
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_fixability: Dict[str, int] = field(default_factory=dict)
    errors_by_rule: Dict[str, int] = field(default_factory=dict)
    errors_by_layer: Dict[str, int] = field(default_factory=dict)
    
    drc_errors: List[DRCError] = field(default_factory=list)
    lvs_errors: List[LVSError] = field(default_factory=list)
    
    fixable_count: int = 0
    manual_required_count: int = 0
    design_change_count: int = 0
    
    recommendations: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            "Error Analysis Summary",
            "=" * 60,
            f"Total errors: {self.total_errors}",
            "",
            "By severity:",
        ]
        
        for severity, count in sorted(self.errors_by_severity.items()):
            lines.append(f"  {severity}: {count}")
        
        lines.append("")
        lines.append("By fixability:")
        for fix, count in sorted(self.errors_by_fixability.items()):
            lines.append(f"  {fix}: {count}")
        
        lines.append("")
        lines.append("Top error rules:")
        for rule, count in sorted(self.errors_by_rule.items(), 
                                  key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"  {rule}: {count}")
        
        if self.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  • {rec}")
        
        return "\n".join(lines)


@dataclass
class ECOFix:
    """Single ECO fix specification."""
    fix_id: str
    fix_type: FixType
    target: str  # Cell name, net name, or location
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    expected_impact: str = ""
    
    # Validation
    applied: bool = False
    successful: bool = False


class ErrorAnalyzer:
    """
    Analyze DRC/LVS errors and classify them.
    
    Provides analysis for agents to make fix decisions.
    """
    
    def analyze_drc(
        self,
        drc_results: Dict[str, Any],
        design_context: Optional[Any] = None,
    ) -> ErrorAnalysis:
        """
        Analyze DRC errors.
        
        Args:
            drc_results: Parsed DRC results
            design_context: Optional design context for better analysis
            
        Returns:
            ErrorAnalysis with classified errors
        """
        analysis = ErrorAnalysis()
        
        # Extract errors from results
        errors_by_rule = drc_results.get("errors_by_rule", {})
        errors_by_layer = drc_results.get("errors_by_layer", {})
        
        # Classify errors
        for rule, count in errors_by_rule.items():
            analysis.errors_by_rule[rule] = count
            analysis.total_errors += count
            
            # Determine severity
            severity = self._classify_severity(rule, count)
            severity_key = severity.value
            analysis.errors_by_severity[severity_key] = (
                analysis.errors_by_severity.get(severity_key, 0) + count
            )
            
            # Determine fixability
            fixability = self._classify_fixability(rule)
            fix_key = fixability.value
            analysis.errors_by_fixability[fix_key] = (
                analysis.errors_by_fixability.get(fix_key, 0) + count
            )
            
            # Create error objects
            for i in range(count):
                error = DRCError(
                    rule_name=rule,
                    layer=self._extract_layer(rule),
                    location=(0, 0, 0, 0),  # Would be extracted from detailed report
                    description=f"{rule} violation",
                    severity=severity,
                    fixability=fixability,
                    suggested_fix=self._suggest_fix(rule),
                )
                analysis.drc_errors.append(error)
        
        # Layer analysis
        analysis.errors_by_layer = errors_by_layer
        
        # Update counts
        analysis.fixable_count = analysis.errors_by_fixability.get("auto_fixable", 0)
        analysis.manual_required_count = analysis.errors_by_fixability.get("manual_required", 0)
        analysis.design_change_count = analysis.errors_by_fixability.get("design_change", 0)
        
        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)
        
        return analysis
    
    def analyze_lvs(
        self,
        lvs_results: Dict[str, Any],
        design_context: Optional[Any] = None,
    ) -> ErrorAnalysis:
        """
        Analyze LVS errors.
        
        Args:
            lvs_results: Parsed LVS results
            design_context: Optional design context
            
        Returns:
            ErrorAnalysis with classified errors
        """
        analysis = ErrorAnalysis()
        
        # Extract error counts
        device_mismatches = lvs_results.get("device_mismatches", 0)
        net_mismatches = lvs_results.get("net_mismatches", 0)
        property_errors = lvs_results.get("property_errors", 0)
        
        # Device mismatches
        if device_mismatches > 0:
            analysis.total_errors += device_mismatches
            analysis.errors_by_rule["device_mismatch"] = device_mismatches
            
            fixability = Fixability.DESIGN_CHANGE
            analysis.errors_by_fixability["design_change"] = (
                analysis.errors_by_fixability.get("design_change", 0) + device_mismatches
            )
            
            for i in range(device_mismatches):
                error = LVSError(
                    error_type="device_mismatch",
                    description="Device count/type mismatch",
                    severity=ErrorSeverity.HIGH,
                    fixability=fixability,
                )
                analysis.lvs_errors.append(error)
        
        # Net mismatches
        if net_mismatches > 0:
            analysis.total_errors += net_mismatches
            analysis.errors_by_rule["net_mismatch"] = net_mismatches
            
            fixability = Fixability.MANUAL_REQUIRED
            analysis.errors_by_fixability["manual_required"] = (
                analysis.errors_by_fixability.get("manual_required", 0) + net_mismatches
            )
            
            for i in range(net_mismatches):
                error = LVSError(
                    error_type="net_mismatch",
                    description="Net connectivity mismatch",
                    severity=ErrorSeverity.CRITICAL,
                    fixability=fixability,
                )
                analysis.lvs_errors.append(error)
        
        # Property errors
        if property_errors > 0:
            analysis.total_errors += property_errors
            analysis.errors_by_rule["property_error"] = property_errors
            
            fixability = Fixability.AUTO_FIXABLE
            analysis.errors_by_fixability["auto_fixable"] = (
                analysis.errors_by_fixability.get("auto_fixable", 0) + property_errors
            )
            
            for i in range(property_errors):
                error = LVSError(
                    error_type="property_error",
                    description="Device property mismatch",
                    severity=ErrorSeverity.MEDIUM,
                    fixability=fixability,
                )
                analysis.lvs_errors.append(error)
        
        # Update counts
        analysis.fixable_count = analysis.errors_by_fixability.get("auto_fixable", 0)
        analysis.manual_required_count = analysis.errors_by_fixability.get("manual_required", 0)
        analysis.design_change_count = analysis.errors_by_fixability.get("design_change", 0)
        
        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)
        
        return analysis
    
    def _classify_severity(self, rule: str, count: int) -> ErrorSeverity:
        """Classify error severity based on rule and count."""
        # Critical rules
        critical_rules = ["ANT", "LATCH", "EOD"]
        if any(rule.startswith(r) for r in critical_rules):
            return ErrorSeverity.CRITICAL
        
        # High count = high severity
        if count > 100:
            return ErrorSeverity.HIGH
        elif count > 10:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _classify_fixability(self, rule: str) -> Fixability:
        """Classify how fixable an error is."""
        # Extract rule type from patterns like M1.S.1, M2.W.1, M3.SP.1
        # Also handle simple format like W.1, S.1
        parts = rule.split(".")
        if len(parts) >= 3:
            # Full format: M1.S.1 -> S
            rule_type = parts[1]
        elif len(parts) == 2:
            # Simple format: W.1 -> W
            rule_type = parts[0]
        else:
            # Single part: W -> W
            rule_type = rule
        
        # Auto-fixable rules (spacing, width, min area)
        auto_rules = ["W", "S", "SP", "MIN", "AREA"]
        if any(rule_type.startswith(r) for r in auto_rules):
            return Fixability.AUTO_FIXABLE
        
        # Manual required
        manual_rules = ["DRC", "OFFGRID", "HOLE"]
        if any(rule_type.startswith(r) for r in manual_rules):
            return Fixability.MANUAL_REQUIRED
        
        # Default to unknown
        return Fixability.UNKNOWN
    
    def _extract_layer(self, rule: str) -> str:
        """Extract layer name from rule."""
        # Typical format: M1.S.1 -> M1
        if "." in rule:
            return rule.split(".")[0]
        return rule
    
    def _suggest_fix(self, rule: str) -> str:
        """Suggest fix for a rule violation."""
        if rule.startswith("W"):
            return "Increase wire width"
        elif rule.startswith("S") or rule.startswith("SP"):
            return "Increase spacing"
        elif rule.startswith("MIN"):
            return "Add filler or increase width"
        else:
            return "Manual review required"
    
    def _generate_recommendations(self, analysis: ErrorAnalysis) -> List[str]:
        """Generate recommendations based on analysis."""
        recs = []
        
        if analysis.fixable_count > 0:
            recs.append(
                f"{analysis.fixable_count} errors are auto-fixable. "
                f"Run ECO optimization first."
            )
        
        if analysis.manual_required_count > 0:
            recs.append(
                f"{analysis.manual_required_count} errors require manual intervention. "
                f"Review these individually."
            )
        
        if analysis.design_change_count > 0:
            recs.append(
                f"{analysis.design_change_count} errors require design changes. "
                f"Consider RTL/netlist modifications."
            )
        
        # Check for problematic layers
        high_error_layers = [
            layer for layer, count in analysis.errors_by_layer.items()
            if count > 50
        ]
        if high_error_layers:
            recs.append(
                f"High error count on layers: {', '.join(high_error_layers)}. "
                f"Check routing strategy."
            )
        
        return recs


class ECOGenerator:
    """
    Generate ECO scripts for fixes.
    
    Provides templates for different fix types.
    """
    
    def generate_drc_eco(
        self,
        fixes: List[ECOFix],
        tool: str = "icc2",
    ) -> str:
        """
        Generate DRC ECO script.
        
        Args:
            fixes: List of ECO fixes
            tool: Target tool (icc2, innovus)
            
        Returns:
            ECO script content
        """
        lines = [
            "# DRC ECO Script",
            f"# Generated for {len(fixes)} fixes",
            "",
        ]
        
        if tool == "icc2":
            lines.extend(self._generate_icc2_drc_eco(fixes))
        else:
            lines.extend(self._generate_innovus_drc_eco(fixes))
        
        return "\n".join(lines)
    
    def generate_lvs_eco(
        self,
        fixes: List[ECOFix],
        tool: str = "icc2",
    ) -> str:
        """
        Generate LVS ECO script.
        
        Args:
            fixes: List of ECO fixes
            tool: Target tool
            
        Returns:
            ECO script content
        """
        lines = [
            "# LVS ECO Script",
            f"# Generated for {len(fixes)} fixes",
            "",
        ]
        
        if tool == "icc2":
            lines.extend(self._generate_icc2_lvs_eco(fixes))
        else:
            lines.extend(self._generate_innovus_lvs_eco(fixes))
        
        return "\n".join(lines)
    
    def _generate_icc2_drc_eco(self, fixes: List[ECOFix]) -> List[str]:
        """Generate ICC2 DRC ECO commands."""
        lines = []
        
        for fix in fixes:
            if fix.fix_type == FixType.SPACING_ADJUST:
                lines.append(f"# Fix {fix.fix_id}: Adjust spacing")
                lines.append(f"# Target: {fix.target}")
                lines.append("route_opt -eco")
                lines.append("")
            
            elif fix.fix_type == FixType.WIDTH_ADJUST:
                lines.append(f"# Fix {fix.fix_id}: Adjust width")
                lines.append(f"# Target: {fix.target}")
                lines.append("route_opt -eco")
                lines.append("")
            
            elif fix.fix_type == FixType.ROUTE_REROUTE:
                lines.append(f"# Fix {fix.fix_id}: Reroute")
                lines.append(f"# Target: {fix.target}")
                lines.append(f"remove_net {fix.target}")
                lines.append(f"route_net {fix.target}")
                lines.append("")
            
            elif fix.fix_type == FixType.VIA_ADD:
                lines.append(f"# Fix {fix.fix_id}: Add via")
                lines.append(f"# Location: {fix.parameters.get('location', '')}")
                lines.append("# Manual via insertion required")
                lines.append("")
        
        lines.append("# Final optimization")
        lines.append("route_opt")
        lines.append("")
        lines.append("exit")
        
        return lines
    
    def _generate_innovus_drc_eco(self, fixes: List[ECOFix]) -> List[str]:
        """Generate Innovus DRC ECO commands."""
        lines = []
        
        for fix in fixes:
            if fix.fix_type == FixType.SPACING_ADJUST:
                lines.append(f"# Fix {fix.fix_id}: Adjust spacing")
                lines.append(f"# Target: {fix.target}")
                lines.append("ecoOptDesign")
                lines.append("")
            
            elif fix.fix_type == FixType.ROUTE_REROUTE:
                lines.append(f"# Fix {fix.fix_id}: Reroute")
                lines.append(f"# Target: {fix.target}")
                lines.append(f"deleteRoute -net {fix.target}")
                lines.append(f"routeDesign -net {fix.target}")
                lines.append("")
        
        lines.append("# Final optimization")
        lines.append("ecoOptDesign")
        lines.append("")
        lines.append("exit")
        
        return lines
    
    def _generate_icc2_lvs_eco(self, fixes: List[ECOFix]) -> List[str]:
        """Generate ICC2 LVS ECO commands."""
        lines = []
        
        for fix in fixes:
            if fix.fix_type == FixType.CELL_RESIZE:
                lines.append(f"# Fix {fix.fix_id}: Resize cell")
                lines.append(f"# Target: {fix.target}")
                new_size = fix.parameters.get("new_size", "")
                lines.append(f"size_cell {fix.target} {new_size}")
                lines.append("")
            
            elif fix.fix_type == FixType.NET_RECONNECT:
                lines.append(f"# Fix {fix.fix_id}: Reconnect net")
                lines.append(f"# Target: {fix.target}")
                lines.append("# Manual reconnection required")
                lines.append("")
        
        lines.append("legalize_placement")
        lines.append("")
        lines.append("exit")
        
        return lines
    
    def _generate_innovus_lvs_eco(self, fixes: List[ECOFix]) -> List[str]:
        """Generate Innovus LVS ECO commands."""
        lines = []
        
        for fix in fixes:
            if fix.fix_type == FixType.CELL_RESIZE:
                lines.append(f"# Fix {fix.fix_id}: Resize cell")
                lines.append(f"# Target: {fix.target}")
                new_size = fix.parameters.get("new_size", "")
                lines.append(f"resizeInst -inst {fix.target} -master {new_size}")
                lines.append("")
        
        lines.append("legalizePin")
        lines.append("")
        lines.append("exit")
        
        return lines


class DRCFixer:
    """
    Main DRC/LVS fixer interface.
    
    Provides composed access to analyzer and ECO generator.
    """
    
    def __init__(self):
        self.analyzer = ErrorAnalyzer()
        self.eco_generator = ECOGenerator()
    
    def create_fix_plan(
        self,
        analysis: ErrorAnalysis,
        max_fixes_per_iteration: int = 50,
    ) -> List[ECOFix]:
        """
        Create a fix plan from analysis.
        
        This is a template - agents should customize the plan.
        
        Args:
            analysis: Error analysis
            max_fixes_per_iteration: Maximum fixes per ECO iteration
            
        Returns:
            List of ECO fixes (agent can modify)
        """
        fixes = []
        fix_id = 1
        
        # Prioritize auto-fixable errors
        auto_fixable = [
            e for e in analysis.drc_errors
            if e.fixability == Fixability.AUTO_FIXABLE
        ]
        
        for error in auto_fixable[:max_fixes_per_iteration]:
            fix = ECOFix(
                fix_id=f"fix_{fix_id:04d}",
                fix_type=FixType.ROUTE_REROUTE,
                target=error.rule_name,
                parameters={"layer": error.layer},
                priority=1 if error.severity == ErrorSeverity.CRITICAL else 2,
                expected_impact=f"Fix {error.rule_name} violations",
            )
            fixes.append(fix)
            fix_id += 1
        
        return fixes
    
    def generate_eco_scripts(
        self,
        fixes: List[ECOFix],
        output_dir: str | Path,
        tool: str = "icc2",
        is_drc: bool = True,
    ) -> Dict[str, Path]:
        """
        Generate ECO scripts for fixes.
        
        Args:
            fixes: List of ECO fixes
            output_dir: Output directory
            tool: Target tool
            is_drc: True for DRC, False for LVS
            
        Returns:
            Dict of script paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        scripts = {}
        
        if is_drc:
            drc_script = self.eco_generator.generate_drc_eco(fixes, tool)
            drc_path = output_dir / "drc_eco.tcl"
            drc_path.write_text(drc_script)
            scripts["drc_eco"] = drc_path
        else:
            lvs_script = self.eco_generator.generate_lvs_eco(fixes, tool)
            lvs_path = output_dir / "lvs_eco.tcl"
            lvs_path.write_text(lvs_script)
            scripts["lvs_eco"] = lvs_path
        
        # Generate fix report
        report_path = output_dir / "fix_report.txt"
        with open(report_path, "w") as f:
            f.write(f"ECO Fix Report\n")
            f.write(f"Total fixes: {len(fixes)}\n\n")
            for fix in fixes:
                f.write(f"{fix.fix_id}: {fix.fix_type.value}\n")
                f.write(f"  Target: {fix.target}\n")
                f.write(f"  Priority: {fix.priority}\n")
                f.write(f"  Impact: {fix.expected_impact}\n\n")
        
        scripts["report"] = report_path
        
        return scripts
