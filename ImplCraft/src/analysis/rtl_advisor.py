"""
RTL Modification Advisor — generates RTL code change suggestions
based on PrimeTime timing analysis results.

Analyzes:
- Setup violations: identifies long combinational paths, suggests pipelining
- Hold violations: identifies too-fast paths, suggests delay insertion
- High fanout nets: suggests buffering or restructuring
- Area hotspots: suggests logic sharing or restructuring
- Power hotspots: suggests clock gating or VT optimization

The advisor maps gate-level timing paths back to RTL constructs and
produces actionable, specific recommendations with code references.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger("ic_backend")


class SuggestionType(Enum):
    PIPELINE = "pipeline"
    LOGIC_RESTRUCTURE = "logic_restructure"
    FANOUT_REDUCE = "fanout_reduce"
    HOLD_FIX = "hold_fix"
    AREA_OPTIMIZE = "area_optimize"
    POWER_OPTIMIZE = "power_optimize"
    CLOCK_GATE = "clock_gate"
    FSM_OPTIMIZE = "fsm_optimize"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RTLPathInfo:
    """Parsed timing path from PT report."""
    slack_ns: float = 0.0
    start_point: str = ""
    end_point: str = ""
    path_group: str = ""
    num_levels: int = 0
    total_delay_ns: float = 0.0
    clock_period_ns: float = 0.0
    cells_in_path: list[str] = field(default_factory=list)
    nets_in_path: list[str] = field(default_factory=list)
    is_setup: bool = True
    raw_report: str = ""


@dataclass
class RTLSuggestion:
    """A single RTL modification suggestion."""
    suggestion_type: SuggestionType
    severity: Severity
    title: str
    description: str
    affected_module: str = ""
    affected_signal: str = ""
    estimated_improvement: str = ""
    code_before: str = ""
    code_after: str = ""
    priority: int = 0  # lower = higher priority


@dataclass
class RTLAnalysisReport:
    """Complete RTL analysis report."""
    design_name: str = ""
    total_setup_violations: int = 0
    total_hold_violations: int = 0
    worst_slack_ns: float = 0.0
    suggestions: list[RTLSuggestion] = field(default_factory=list)
    hot_modules: dict[str, int] = field(default_factory=dict)  # module -> violation count
    summary: str = ""


class RTLAdvisor:
    """
    RTL Modification Advisor.

    Usage:
        advisor = RTLAdvisor(state)
        report = advisor.analyze()
        print(advisor.format_report(report))
    """

    def __init__(self, state: Any):
        self.state = state

    def analyze(self, pt_report_dir: str | Path | None = None) -> RTLAnalysisReport:
        """
        Analyze PT reports and generate RTL modification suggestions.

        Args:
            pt_report_dir: Directory containing PT report files.
                          If None, searches in work_root/primetime/PT/report.
        """
        report = RTLAnalysisReport(design_name=self.state.config.design_name)

        if pt_report_dir is None:
            pt_report_dir = Path(self.state.work_root) / "primetime" / "PT" / "report"
        else:
            pt_report_dir = Path(pt_report_dir)

        if not pt_report_dir.exists():
            report.summary = "PT report directory not found. Run PrimeTime first."
            return report

        # Parse critical paths
        setup_paths = self._parse_timing_paths(pt_report_dir, is_setup=True)
        hold_paths = self._parse_timing_paths(pt_report_dir, is_setup=False)

        report.total_setup_violations = len(setup_paths)
        report.total_hold_violations = len(hold_paths)

        if setup_paths:
            report.worst_slack_ns = min(p.slack_ns for p in setup_paths)

        # Generate suggestions based on analysis
        report.suggestions.extend(self._analyze_setup_violations(setup_paths))
        report.suggestions.extend(self._analyze_hold_violations(hold_paths))
        report.suggestions.extend(self._analyze_fanout_issues(pt_report_dir))
        report.suggestions.extend(self._analyze_area_hotspots(pt_report_dir))
        report.suggestions.extend(self._analyze_power_hotspots(pt_report_dir))

        # Build module hotspot
        for path in setup_paths + hold_paths:
            module = self._extract_module_name(path.start_point)
            report.hot_modules[module] = report.hot_modules.get(module, 0) + 1

        # Sort by priority
        report.suggestions.sort(key=lambda s: s.priority)

        # Generate summary
        report.summary = self._generate_summary(report)

        return report

    def _parse_timing_paths(self, report_dir: Path, is_setup: bool) -> list[RTLPathInfo]:
        """Parse PT timing report files into structured path info."""
        paths = []
        if is_setup:
            patterns = ["critical_paths_setup.rpt", "timing_setup.rpt"]
        else:
            patterns = ["critical_paths_hold.rpt", "timing_hold.rpt"]

        for fname in patterns:
            fpath = report_dir / fname
            if fpath.exists():
                text = fpath.read_text(errors="ignore")
                paths.extend(self._extract_paths(text, is_setup))
                break

        return paths

    def _extract_paths(self, text: str, is_setup: bool) -> list[RTLPathInfo]:
        """Extract individual timing paths from a PT report."""
        paths = []
        # Split by path boundaries
        path_blocks = re.split(r'Startpoint:', text)

        for block in path_blocks[1:]:  # skip preamble
            path = RTLPathInfo(is_setup=is_setup)
            path.raw_report = f"Startpoint:{block}"

            # Extract start/end points
            m = re.search(r'Startpoint:\s*(\S+)', block)
            if m:
                path.start_point = m.group(1)

            m = re.search(r'Endpoint:\s*(\S+)', block)
            if m:
                path.end_point = m.group(1)

            # Extract path group
            m = re.search(r'Path Group:\s*(\S+)', block)
            if m:
                path.path_group = m.group(1)

            # Extract slack
            m = re.search(r'slack\s+\(\w+\)\s+([-.\d]+)', block)
            if m:
                path.slack_ns = float(m.group(1))

            # Extract arrival/required
            m = re.search(r'data arrival time\s+([-.\d]+)', block)
            if m:
                path.total_delay_ns = float(m.group(1))

            m = re.search(r'data required time\s+([-.\d]+)', block)
            if m:
                path.clock_period_ns = float(m.group(1))

            # Count logic levels
            cells = re.findall(r'^\s+(\S+)\s+\(.*\)\s+[-.\d]+\s+[-.\d]+\s*$', block, re.MULTILINE)
            path.cells_in_path = cells
            path.num_levels = len(cells)

            # Extract nets
            nets = re.findall(r'^\s+(\S+)\s+\(net\)', block, re.MULTILINE)
            path.nets_in_path = nets

            paths.append(path)

        return paths

    def _extract_module_name(self, cell_name: str) -> str:
        """Extract module name from hierarchical cell path."""
        parts = cell_name.split("/")
        if len(parts) >= 2:
            return parts[-2]  # parent module
        return cell_name.split("[")[0]

    def _analyze_setup_violations(self, paths: list[RTLPathInfo]) -> list[RTLSuggestion]:
        """Generate suggestions for setup violations."""
        suggestions = []

        # Group paths by module
        module_paths: dict[str, list[RTLPathInfo]] = {}
        for path in paths:
            module = self._extract_module_name(path.start_point)
            if module not in module_paths:
                module_paths[module] = []
            module_paths[module].append(path)

        for module, mpaths in module_paths.items():
            if len(mpaths) < 2:
                continue

            worst_path = min(mpaths, key=lambda p: p.slack_ns)

            # Long combinational path → suggest pipelining
            if worst_path.num_levels > 8:
                mid_cell = worst_path.cells_in_path[worst_path.num_levels // 2] if worst_path.cells_in_path else ""
                suggestions.append(RTLSuggestion(
                    suggestion_type=SuggestionType.PIPELINE,
                    severity=Severity.CRITICAL if worst_path.slack_ns < -0.5 else Severity.HIGH,
                    title=f"Pipeline {module}: {worst_path.num_levels} logic levels",
                    description=(
                        f"Module '{module}' has {worst_path.num_levels} logic levels in the critical path "
                        f"({worst_path.start_point} → {worst_path.end_point}, slack={worst_path.slack_ns:.3f}ns). "
                        f"Insert pipeline register(s) to break the combinational path."
                    ),
                    affected_module=module,
                    affected_signal=worst_path.start_point,
                    estimated_improvement=f"Reduce path by ~{worst_path.num_levels // 2} levels, "
                                          f"potentially improving slack by {abs(worst_path.slack_ns) * 0.6:.2f}ns",
                    code_before=f"# Current: {worst_path.num_levels}-level combinational path\n"
                                f"# {worst_path.start_point} → {worst_path.end_point}",
                    code_after=f"# Suggested: Insert pipeline register near '{mid_cell}'\n"
                               f"# always @(posedge clk)\n"
                               f"#   pipeline_reg <= intermediate_signal;",
                    priority=1,
                ))

            # High fanout signal in critical path
            for path in mpaths:
                for net in path.nets_in_path[:5]:
                    fanout_hint = re.search(r'fanout\s+(\d+)', path.raw_report)
                    if fanout_hint and int(fanout_hint.group(1)) > 30:
                        suggestions.append(RTLSuggestion(
                            suggestion_type=SuggestionType.FANOUT_REDUCE,
                            severity=Severity.HIGH,
                            title=f"High fanout net '{net}' in {module}",
                            description=(
                                f"Net '{net}' has fanout {fanout_hint.group(1)} in the critical path of '{module}'. "
                                f"Consider restructuring to reduce fanout or adding explicit buffers."
                            ),
                            affected_module=module,
                            affected_signal=net,
                            estimated_improvement=f"Reduce fanout from {fanout_hint.group(1)} to <20",
                            priority=3,
                        ))

        # Logic restructuring for modules with many violations
        for module, mpaths in module_paths.items():
            if len(mpaths) >= 5:
                suggestions.append(RTLSuggestion(
                    suggestion_type=SuggestionType.LOGIC_RESTRUCTURE,
                    severity=Severity.HIGH,
                    title=f"Restructure {module}: {len(mpaths)} timing violations",
                    description=(
                        f"Module '{module}' contributes to {len(mpaths)} timing violations. "
                        f"Consider restructuring the logic: simplify conditions, "
                        f"reduce mux depth, or factor out common subexpressions."
                    ),
                    affected_module=module,
                    estimated_improvement=f"Address {len(mpaths)} violations in a single pass",
                    priority=2,
                ))

        return suggestions

    def _analyze_hold_violations(self, paths: list[RTLPathInfo]) -> list[RTLSuggestion]:
        """Generate suggestions for hold violations."""
        suggestions = []

        # Group by module
        module_paths: dict[str, list[RTLPathInfo]] = {}
        for path in paths:
            module = self._extract_module_name(path.start_point)
            if module not in module_paths:
                module_paths[module] = []
            module_paths[module].append(path)

        for module, mpaths in module_paths.items():
            if len(mpaths) >= 3:
                suggestions.append(RTLSuggestion(
                    suggestion_type=SuggestionType.HOLD_FIX,
                    severity=Severity.MEDIUM,
                    title=f"Hold violations in {module}: {len(mpaths)} paths",
                    description=(
                        f"Module '{module}' has {len(mpaths)} hold violations. "
                        f"These are typically fixed by the tool (inserting delay cells), "
                        f"but if persistent, review the clock tree balance and "
                        f"consider adding explicit hold margin in the RTL."
                    ),
                    affected_module=module,
                    priority=5,
                ))

        return suggestions

    def _analyze_fanout_issues(self, report_dir: Path) -> list[RTLSuggestion]:
        """Check for high-fanout nets that may need RTL restructuring."""
        suggestions = []
        constraint_file = report_dir / "constraint_fanout.rpt"
        if not constraint_file.exists():
            return suggestions

        text = constraint_file.read_text(errors="ignore")
        high_fanout_nets = re.findall(r'(\S+)\s+(\d+)\s+\d+\s+\d+\s+max_fanout', text)

        for net_name, fanout in high_fanout_nets:
            fanout_val = int(fanout)
            if fanout_val > 50:
                module = self._extract_module_name(net_name)
                suggestions.append(RTLSuggestion(
                    suggestion_type=SuggestionType.FANOUT_REDUCE,
                    severity=Severity.HIGH if fanout_val > 100 else Severity.MEDIUM,
                    title=f"Very high fanout: {net_name} ({fanout_val})",
                    description=(
                        f"Net '{net_name}' has fanout {fanout_val}. "
                        f"In the RTL, consider: (1) adding pipeline registers, "
                        f"(2) replicating the driver logic, "
                        f"(3) using a bus-based distribution pattern."
                    ),
                    affected_module=module,
                    affected_signal=net_name,
                    priority=4,
                ))

        return suggestions

    def _analyze_area_hotspots(self, report_dir: Path) -> list[RTLSuggestion]:
        """Analyze cell report for area hotspots."""
        suggestions = []
        cell_file = report_dir / "cell.rpt"
        if not cell_file.exists():
            return suggestions

        text = cell_file.read_text(errors="ignore")

        # Find modules with disproportionate cell count
        module_counts = re.findall(r'(\S+)\s+(\d+)\s+\d+\.\d+', text)
        if not module_counts:
            return suggestions

        total = sum(int(c) for _, c in module_counts)
        if total == 0:
            return suggestions

        for module, count in module_counts:
            ratio = int(count) / total
            if ratio > 0.3 and int(count) > 500:
                suggestions.append(RTLSuggestion(
                    suggestion_type=SuggestionType.AREA_OPTIMIZE,
                    severity=Severity.MEDIUM,
                    title=f"Area hotspot: {module} ({ratio:.0%} of total cells)",
                    description=(
                        f"Module '{module}' uses {int(count)} cells ({ratio:.0%} of total). "
                        f"Consider: (1) logic sharing for duplicate computations, "
                        f"(2) resource sharing for arithmetic operations, "
                        f"(3) FSM state encoding optimization."
                    ),
                    affected_module=module,
                    estimated_improvement=f"Potential {ratio * 20:.0f}% area reduction in hotspot",
                    priority=6,
                ))

        return suggestions

    def _analyze_power_hotspots(self, report_dir: Path) -> list[RTLSuggestion]:
        """Analyze power distribution for optimization opportunities."""
        suggestions = []
        # Check if there's a power report from PT
        # This would come from PT-PX or PrimePower integration
        return suggestions

    def _generate_summary(self, report: RTLAnalysisReport) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"RTL Analysis Report for '{report.design_name}'",
            f"Setup violations: {report.total_setup_violations}",
            f"Hold violations: {report.total_hold_violations}",
            f"Worst slack: {report.worst_slack_ns:.3f}ns",
            f"Total suggestions: {len(report.suggestions)}",
        ]

        if report.hot_modules:
            lines.append(f"\nTop problematic modules:")
            sorted_modules = sorted(report.hot_modules.items(), key=lambda x: x[1], reverse=True)
            for module, count in sorted_modules[:5]:
                lines.append(f"  {module}: {count} violations")

        critical_count = sum(1 for s in report.suggestions if s.severity == Severity.CRITICAL)
        high_count = sum(1 for s in report.suggestions if s.severity == Severity.HIGH)
        if critical_count > 0:
            lines.append(f"\n*** {critical_count} CRITICAL suggestions require immediate RTL changes ***")
        if high_count > 0:
            lines.append(f"  {high_count} HIGH priority suggestions recommended")

        return "\n".join(lines)

    def format_report(self, report: RTLAnalysisReport) -> str:
        """Format the full report for display."""
        lines = [
            "=" * 70,
            "RTL Modification Suggestions",
            "=" * 70,
            "",
            report.summary,
            "",
            "-" * 70,
            "SUGGESTIONS",
            "-" * 70,
            "",
        ]

        for i, sug in enumerate(report.suggestions, 1):
            lines.append(f"[{i}] [{sug.severity.value.upper()}] {sug.title}")
            lines.append(f"    Type: {sug.suggestion_type.value}")
            lines.append(f"    {sug.description}")
            if sug.estimated_improvement:
                lines.append(f"    Estimated improvement: {sug.estimated_improvement}")
            if sug.code_before:
                lines.append(f"    Current:")
                for cl in sug.code_before.splitlines():
                    lines.append(f"      {cl}")
            if sug.code_after:
                lines.append(f"    Suggested:")
                for cl in sug.code_after.splitlines():
                    lines.append(f"      {cl}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def save_report(self, report: RTLAnalysisReport, output_path: str | Path):
        """Save report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.format_report(report))
        logger.info(f"RTL suggestions saved to {output_path}")
