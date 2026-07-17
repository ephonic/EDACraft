"""
EDA Error/Warning Checker — comprehensive check for all EDA tool outputs.

Scans log files from all EDA tools (DC, ICC2, Calibre, PT) for:
- Fatal errors
- Warnings (categorized by severity)
- Informational messages that indicate issues
- Tool-specific patterns

Categorizes findings and provides actionable recommendations.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger("ic_backend")


class MessageSeverity(Enum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ToolName(Enum):
    DC = "DesignCompiler"
    ICC2 = "ICC2"
    CALIBRE = "Calibre"
    PT = "PrimeTime"
    STAR_RC = "StarRC"
    UNKNOWN = "Unknown"


@dataclass
class EDAErrorMessage:
    """A single error/warning message from an EDA tool."""
    tool: ToolName
    severity: MessageSeverity
    code: str  # e.g. "PSYN-074", "DRC-U42"
    message: str
    file_path: str = ""
    line_number: int | None = None
    recommendation: str = ""
    is_acknowledged: bool = False


@dataclass
class ErrorCheckResult:
    """Result of error checking across all tool logs."""
    tool_name: str
    log_file: str
    fatal_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    messages: list[EDAErrorMessage] = field(default_factory=list)
    summary: str = ""


# ---- Tool-specific error patterns ----

# Design Compiler patterns
_DC_PATTERNS = [
    (MessageSeverity.FATAL, r'Error:\s*(\w+-\d+)', "DC fatal error"),
    (MessageSeverity.ERROR, r'Warning:\s*(\w+-\d+).*cannot resolve', "Unresolved reference"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*unconnected', "Unconnected port"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*latch.*inferred', "Latch inferred — check RTL"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*constant.*propagat', "Constant propagation"),
    (MessageSeverity.WARNING, r'Warning:\s*(PSYN-\d+).*DRC.*violat', "DRC violation at gate level"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*clock.*gate.*cell.*not found', "Missing clock gate cell"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*set_dont_touch.*cannot be removed', "Cannot remove dont_touch"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*black.box', "Black box reference"),
    (MessageSeverity.WARNING, r'Warning:\s*(TIM-\d+)', "Timing constraint issue"),
    (MessageSeverity.WARNING, r'Warning:\s*(PSYN-\d+)', "Synthesis warning"),
    (MessageSeverity.WARNING, r'Warning:\s*(OPT-\d+)', "Optimization warning"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+)', "DC warning"),
    (MessageSeverity.INFO, r'Information:\s*(\w+-\d+)', "DC informational"),
]

# ICC2 patterns
_ICC2_PATTERNS = [
    (MessageSeverity.FATAL, r'Error:\s*(\w+-\d+)', "ICC2 fatal error"),
    (MessageSeverity.ERROR, r'Warning:\s*(\w+-\d+).*cannot.*open.*library', "Library access failure"),
    (MessageSeverity.ERROR, r'Warning:\s*(\w+-\d+).*cannot.*read.*netlist', "Netlist read failure"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*unplaced.*cell', "Unplaced cells remain"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*unconnected.*pin', "Unconnected pins"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*overlap.*cell', "Cell overlap detected"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*legality.*violation', "Legality violation"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*congestion.*high', "High congestion warning"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*clock.*route.*fail', "Clock routing failure"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*antenna.*violat', "Antenna violation"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*via.*missing', "Missing vias"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+)', "ICC2 warning"),
    (MessageSeverity.INFO, r'Information:\s*(\w+-\d+)', "ICC2 informational"),
]

# Calibre patterns
_CALIBRE_PATTERNS = [
    (MessageSeverity.FATAL, r'ERROR:\s*(.*)', "Calibre fatal"),
    (MessageSeverity.ERROR, r'Error:\s*(\w+-\d+)', "Calibre error"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+)', "Calibre warning"),
    (MessageSeverity.INFO, r'INFO:\s*(.*)', "Calibre info"),
]

# PrimeTime patterns
_PT_PATTERNS = [
    (MessageSeverity.FATAL, r'Error:\s*(\w+-\d+)', "PT fatal error"),
    (MessageSeverity.ERROR, r'Warning:\s*(\w+-\d+).*cannot.*link', "Link failure — missing cells"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*unconstrained.*path', "Unconstrained path"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*clock.*tree.*missing', "Missing clock tree"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*SPEF.*error', "SPEF read error"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*SI.*analysis', "SI analysis issue"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*false.*path.*conflict', "False path conflict"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+).*multicycle.*path', "Multicycle path issue"),
    (MessageSeverity.WARNING, r'Warning:\s*(\w+-\d+)', "PT warning"),
    (MessageSeverity.INFO, r'Information:\s*(\w+-\d+)', "PT informational"),
]

_TOOL_PATTERNS = {
    ToolName.DC: _DC_PATTERNS,
    ToolName.ICC2: _ICC2_PATTERNS,
    ToolName.CALIBRE: _CALIBRE_PATTERNS,
    ToolName.PT: _PT_PATTERNS,
}

# Recommendation map for common error codes
_RECOMMENDATIONS = {
    # DC common
    "PSYN-074": "Check if the cell exists in the target library. Verify library path.",
    "PSYN-523": "Unconnected ports detected. Check RTL port connections.",
    "PSYN-088": "Clock not defined. Check SDC constraints.",
    "PSYN-899": "Design has latches. Review RTL for incomplete if/case statements.",
    "TIM-052": "Clock period too tight. Consider relaxing or pipelining.",
    "TIM-134": "Unconstrained path. Add SDC constraint.",
    "OPT-9963": "Design has undriven inputs. Check RTL connectivity.",
    # ICC2 common
    "NLIB-505": "NDM library issue. Verify NDM file paths and versions.",
    "RMUI-112": "Unmatched cells between netlist and library.",
    "APF-406": "Antenna violation. Enable antenna fixing in routing.",
    "RT-007": "Routing DRC not clean. Increase search_repair_loop or check congestion.",
    # PT common
    "PTE-500": "Cannot link design. Check netlist and library consistency.",
    "PTE-004": "Timing constraint issue. Review SDC.",
    "PARA-004": "SPEF mismatch. Check netlist vs SPEF consistency.",
}


class ErrorChecker:
    """
    Comprehensive error/warning checker for EDA tool outputs.

    Usage:
        checker = ErrorChecker()
        result = checker.check_log("work/synthesis/log/run.log", ToolName.DC)
        report = checker.generate_report(results)
    """

    def __init__(self):
        self.all_results: list[ErrorCheckResult] = []

    def check_log(self, log_path: str | Path, tool: ToolName) -> ErrorCheckResult:
        """Check a single log file for errors and warnings."""
        log_path = Path(log_path)
        result = ErrorCheckResult(tool_name=tool.value, log_file=str(log_path))

        if not log_path.exists():
            result.messages.append(EDAErrorMessage(
                tool=tool,
                severity=MessageSeverity.WARNING,
                code="LOG-000",
                message=f"Log file not found: {log_path}",
            ))
            result.warning_count = 1
            return result

        text = log_path.read_text(errors="ignore")
        patterns = _TOOL_PATTERNS.get(tool, [])

        for line_no, line in enumerate(text.splitlines(), 1):
            for severity, pattern, desc in patterns:
                m = re.search(pattern, line)
                if m:
                    code = m.group(1) if m.lastindex else "UNKNOWN"
                    msg = EDAErrorMessage(
                        tool=tool,
                        severity=severity,
                        code=code,
                        message=line.strip()[:200],
                        file_path=str(log_path),
                        line_number=line_no,
                        recommendation=_RECOMMENDATIONS.get(code, ""),
                    )
                    result.messages.append(msg)

                    if severity == MessageSeverity.FATAL:
                        result.fatal_count += 1
                    elif severity == MessageSeverity.ERROR:
                        result.error_count += 1
                    elif severity == MessageSeverity.WARNING:
                        result.warning_count += 1
                    elif severity == MessageSeverity.INFO:
                        result.info_count += 1

                    break  # one match per line

        self.all_results.append(result)
        return result

    def check_all_logs(self, work_root: str | Path) -> list[ErrorCheckResult]:
        """Check all tool logs in the work directory."""
        work_root = Path(work_root)
        results = []

        log_mappings = [
            ("synthesis", ToolName.DC, ["log/run.log", "DC/log/run.log"]),
            ("create_lib", ToolName.ICC2, ["log/run.log"]),
            ("floorplan", ToolName.ICC2, ["log/run.log"]),
            ("placement", ToolName.ICC2, ["log/run.log"]),
            ("cts", ToolName.ICC2, ["log/run.log"]),
            ("routing", ToolName.ICC2, ["log/run.log"]),
            ("route_opt", ToolName.ICC2, ["log/run.log"]),
            ("primetime", ToolName.PT, ["log/run.log", "PT/log/run.log"]),
            ("drc", ToolName.CALIBRE, ["log/run.log"]),
            ("lvs", ToolName.CALIBRE, ["log/run.log"]),
        ]

        for stage_name, tool, log_paths in log_mappings:
            stage_dir = work_root / stage_name
            if not stage_dir.exists():
                continue
            for lp in log_paths:
                log_file = stage_dir / lp
                if log_file.exists():
                    result = self.check_log(log_file, tool)
                    result.tool_name = f"{tool.value} ({stage_name})"
                    results.append(result)
                    break

        return results

    def generate_report(self, results: list[ErrorCheckResult] | None = None) -> str:
        """Generate a comprehensive error/warning report."""
        if results is None:
            results = self.all_results

        lines = ["=" * 70, "EDA Error/Warning Check Report", "=" * 70, ""]

        total_fatal = 0
        total_error = 0
        total_warning = 0
        all_warnings: list[EDAErrorMessage] = []
        all_fatals: list[EDAErrorMessage] = []

        for result in results:
            total_fatal += result.fatal_count
            total_error += result.error_count
            total_warning += result.warning_count

            status = "PASS"
            if result.fatal_count > 0:
                status = "FAIL"
            elif result.error_count > 0:
                status = "ERRORS"
            elif result.warning_count > 0:
                status = "WARNINGS"

            lines.append(f"[{status}] {result.tool_name} ({Path(result.log_file).name})")
            lines.append(f"  Fatal: {result.fatal_count}  Error: {result.error_count}  Warning: {result.warning_count}  Info: {result.info_count}")

            for msg in result.messages:
                if msg.severity == MessageSeverity.FATAL:
                    all_fatals.append(msg)
                elif msg.severity == MessageSeverity.WARNING:
                    all_warnings.append(msg)

                severity_tag = msg.severity.value.upper()
                lines.append(f"  [{severity_tag}] L{msg.line_number}: {msg.code} — {msg.message[:120]}")
                if msg.recommendation:
                    lines.append(f"    → Recommendation: {msg.recommendation}")

            lines.append("")

        # Summary
        lines.append("=" * 70)
        lines.append("SUMMARY")
        lines.append(f"  Total: {total_fatal} fatal, {total_error} errors, {total_warning} warnings")
        if total_fatal > 0:
            lines.append("  *** FATAL ERRORS DETECTED — flow will not complete ***")
        elif total_error > 0:
            lines.append("  *** ERRORS DETECTED — review and fix before proceeding ***")
        elif total_warning > 0:
            lines.append("  Warnings detected — review recommended but flow may proceed")
        else:
            lines.append("  No significant issues found")
        lines.append("=" * 70)

        return "\n".join(lines)

    def has_fatal(self, results: list[ErrorCheckResult] | None = None) -> bool:
        """Check if any fatal errors exist."""
        if results is None:
            results = self.all_results
        return any(r.fatal_count > 0 for r in results)

    def get_critical_warnings(self, results: list[ErrorCheckResult] | None = None) -> list[EDAErrorMessage]:
        """Get all warnings that need attention."""
        if results is None:
            results = self.all_results
        critical = []
        for r in results:
            for msg in r.messages:
                if msg.severity in (MessageSeverity.FATAL, MessageSeverity.ERROR):
                    critical.append(msg)
                elif msg.severity == MessageSeverity.WARNING and msg.recommendation:
                    critical.append(msg)
        return critical
