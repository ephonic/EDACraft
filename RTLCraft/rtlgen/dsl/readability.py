"""Review-oriented RTL readability analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Sequence

from rtlgen.dsl.codegen import EmitProfile, VerilogEmitter
from rtlgen.dsl.core import Module


@dataclass(frozen=True)
class ReadabilityFinding:
    kind: str
    line: int
    detail: str


@dataclass(frozen=True)
class ReadabilityReport:
    profile: str
    line_count: int
    max_line_length: int
    long_line_count: int
    anonymous_helper_count: int
    duplicated_block_prefix_count: int
    deep_mux_assign_count: int
    findings: tuple[ReadabilityFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class MarkerSequenceFinding:
    kind: str
    marker: str
    detail: str


@dataclass(frozen=True)
class MarkerSequenceReport:
    context: str
    expected_marker_count: int
    matched_marker_count: int
    findings: tuple[MarkerSequenceFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


class ReadabilityContractError(AssertionError):
    """Raised when emitted RTL violates the review readability contract."""


def analyze_emitted_readability(
    module: Module,
    *,
    profile: EmitProfile | None = None,
    max_line_length: int = 120,
    max_mux_ternaries_per_assign: int = 3,
) -> ReadabilityReport:
    """Emit RTL for ``module`` and run lightweight review-oriented checks."""

    resolved_profile = profile or EmitProfile.review()
    emitted = VerilogEmitter(profile=resolved_profile).emit(module)
    return analyze_verilog_readability(
        emitted,
        profile=resolved_profile.style or "review",
        max_line_length=max_line_length,
        max_mux_ternaries_per_assign=max_mux_ternaries_per_assign,
    )


def analyze_verilog_readability(
    text: str,
    *,
    profile: str = "review",
    max_line_length: int = 120,
    max_mux_ternaries_per_assign: int = 3,
) -> ReadabilityReport:
    """Analyze already-emitted Verilog text for review-grade readability."""

    lines = text.splitlines()
    findings: List[ReadabilityFinding] = []
    anonymous_helper_pattern = re.compile(r"\b(?:wire|logic)\s+(?:\[[^\]]+\]\s+)?(_(?:tmp|cse)_\d+)\b")
    assign_prefix_pattern = re.compile(r"//\s+(Comb|Seq):\s+\1:")

    long_line_count = 0
    anonymous_helper_count = 0
    duplicated_block_prefix_count = 0
    deep_mux_assign_count = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")
        if len(stripped) > max_line_length:
            long_line_count += 1
            findings.append(
                ReadabilityFinding(
                    kind="long_line",
                    line=lineno,
                    detail=f"line length {len(stripped)} exceeds review budget {max_line_length}",
                )
            )

        anonymous_match = anonymous_helper_pattern.search(stripped)
        if anonymous_match:
            anonymous_helper_count += 1
            findings.append(
                ReadabilityFinding(
                    kind="anonymous_helper",
                    line=lineno,
                    detail=f"anonymous helper name '{anonymous_match.group(1)}' leaks into review RTL",
                )
            )

        if assign_prefix_pattern.search(stripped):
            duplicated_block_prefix_count += 1
            findings.append(
                ReadabilityFinding(
                    kind="duplicated_block_prefix",
                    line=lineno,
                    detail="duplicated review block prefix found",
                )
            )

        if "assign " in stripped and stripped.count("?") > max_mux_ternaries_per_assign:
            deep_mux_assign_count += 1
            findings.append(
                ReadabilityFinding(
                    kind="deep_mux_assign",
                    line=lineno,
                    detail=(
                        f"assign contains {stripped.count('?')} ternaries; "
                        f"review budget is {max_mux_ternaries_per_assign}"
                    ),
                )
            )

    return ReadabilityReport(
        profile=profile,
        line_count=len(lines),
        max_line_length=max((len(line) for line in lines), default=0),
        long_line_count=long_line_count,
        anonymous_helper_count=anonymous_helper_count,
        duplicated_block_prefix_count=duplicated_block_prefix_count,
        deep_mux_assign_count=deep_mux_assign_count,
        findings=tuple(findings),
    )


def analyze_marker_sequence(
    text: str,
    expected_markers: Sequence[str],
    *,
    context: str = "RTL marker contract",
) -> MarkerSequenceReport:
    """Check that expected marker strings appear in order inside emitted RTL."""

    search_start = 0
    matched_marker_count = 0
    findings: List[MarkerSequenceFinding] = []
    for marker in expected_markers:
        ordered_index = text.find(marker, search_start)
        if ordered_index >= 0:
            matched_marker_count += 1
            search_start = ordered_index + len(marker)
            continue
        first_index = text.find(marker)
        if first_index >= 0:
            findings.append(
                MarkerSequenceFinding(
                    kind="out_of_order_marker",
                    marker=marker,
                    detail=(
                        f"marker appears at line {_line_number_for_offset(text, first_index)} "
                        f"but not in the expected order"
                    ),
                )
            )
        else:
            findings.append(
                MarkerSequenceFinding(
                    kind="missing_marker",
                    marker=marker,
                    detail="marker not found in emitted RTL",
                )
            )

    return MarkerSequenceReport(
        context=context,
        expected_marker_count=len(tuple(expected_markers)),
        matched_marker_count=matched_marker_count,
        findings=tuple(findings),
    )


def emit_readability_report_markdown(
    report: ReadabilityReport,
    *,
    title: str = "RTL Readability Report",
) -> str:
    """Render a compact Markdown summary for readability checks."""

    lines: List[str] = [f"# {title}", ""]
    lines.append(f"- profile: `{report.profile}`")
    lines.append(f"- passed: `{str(report.passed).lower()}`")
    lines.append(f"- line_count: `{report.line_count}`")
    lines.append(f"- max_line_length: `{report.max_line_length}`")
    lines.append(f"- long_line_count: `{report.long_line_count}`")
    lines.append(f"- anonymous_helper_count: `{report.anonymous_helper_count}`")
    lines.append(f"- duplicated_block_prefix_count: `{report.duplicated_block_prefix_count}`")
    lines.append(f"- deep_mux_assign_count: `{report.deep_mux_assign_count}`")
    if report.findings:
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        for finding in report.findings:
            lines.append(f"- L{finding.line} `{finding.kind}`: {finding.detail}")
    return "\n".join(lines)


def emit_marker_sequence_report_markdown(
    report: MarkerSequenceReport,
    *,
    title: str = "RTL Marker Contract Report",
) -> str:
    """Render a compact Markdown summary for expected marker ordering."""

    lines: List[str] = [f"# {title}", ""]
    lines.append(f"- context: `{report.context}`")
    lines.append(f"- passed: `{str(report.passed).lower()}`")
    lines.append(f"- expected_marker_count: `{report.expected_marker_count}`")
    lines.append(f"- matched_marker_count: `{report.matched_marker_count}`")
    if report.findings:
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        for finding in report.findings:
            lines.append(f"- `{finding.kind}` `{finding.marker}`: {finding.detail}")
    return "\n".join(lines)


def assert_readable_verilog(
    text: str,
    *,
    profile: str = "review",
    max_line_length: int = 120,
    max_mux_ternaries_per_assign: int = 3,
    title: str = "RTL Readability Report",
) -> ReadabilityReport:
    """Raise a structured error if already-emitted Verilog violates readability checks."""

    report = analyze_verilog_readability(
        text,
        profile=profile,
        max_line_length=max_line_length,
        max_mux_ternaries_per_assign=max_mux_ternaries_per_assign,
    )
    if not report.passed:
        raise ReadabilityContractError(emit_readability_report_markdown(report, title=title))
    return report


def assert_readable_emitted_rtl(
    module: Module,
    *,
    profile: EmitProfile | None = None,
    max_line_length: int = 120,
    max_mux_ternaries_per_assign: int = 3,
    title: str = "RTL Readability Report",
) -> ReadabilityReport:
    """Raise a structured error if emitted RTL for ``module`` violates readability checks."""

    resolved_profile = profile or EmitProfile.review()
    emitted = VerilogEmitter(profile=resolved_profile).emit(module)
    return assert_readable_verilog(
        emitted,
        profile=resolved_profile.style or "review",
        max_line_length=max_line_length,
        max_mux_ternaries_per_assign=max_mux_ternaries_per_assign,
        title=title,
    )


def assert_marker_sequence(
    text: str,
    expected_markers: Sequence[str],
    *,
    context: str = "RTL marker contract",
    title: str = "RTL Marker Contract Report",
) -> MarkerSequenceReport:
    """Raise a structured error if expected markers are missing or out of order."""

    report = analyze_marker_sequence(text, expected_markers, context=context)
    if not report.passed:
        raise ReadabilityContractError(emit_marker_sequence_report_markdown(report, title=title))
    return report


def assert_emitted_rtl_contract(
    module: Module,
    *,
    expected_markers: Sequence[str] = (),
    profile: EmitProfile | None = None,
    max_line_length: int = 120,
    max_mux_ternaries_per_assign: int = 3,
) -> str:
    """Emit RTL, enforce readability checks, and optionally gate marker order."""

    resolved_profile = profile or EmitProfile.review()
    emitted = VerilogEmitter(profile=resolved_profile).emit(module)
    assert_readable_verilog(
        emitted,
        profile=resolved_profile.style or "review",
        max_line_length=max_line_length,
        max_mux_ternaries_per_assign=max_mux_ternaries_per_assign,
        title=f"RTL Readability Report: {module.name}",
    )
    if expected_markers:
        assert_marker_sequence(
            emitted,
            expected_markers,
            context=f"{module.name} review RTL",
            title=f"RTL Marker Contract Report: {module.name}",
        )
    return emitted


def _line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1
