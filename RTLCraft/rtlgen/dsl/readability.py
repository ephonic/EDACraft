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
    findings: tuple[ReadabilityFinding, ...] = ()
    missing_header_count: int = 0
    missing_port_table_count: int = 0
    unlabeled_always_block_count: int = 0
    unstable_generated_name_count: int = 0
    source_map_noise_count: int = 0
    memory_block_not_grouped_count: int = 0
    clock_reset_not_visible_count: int = 0

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
    anonymous_helper_pattern = re.compile(r"\b(?:wire|logic|reg)\s+(?:\[[^\]]+\]\s+)?(_(?:tmp|cse)_?\d+)\b")
    unstable_generated_name_pattern = re.compile(r"\b_(?:tmp|cse)_?\d+\b")
    assign_prefix_pattern = re.compile(r"//\s+(Comb|Seq):\s+\1:")
    module_header_pattern = re.compile(r"//\s+Module(?:\s*:|:)")
    module_decl_pattern = re.compile(r"^\s*module\s+\w+")
    memory_decl_pattern = re.compile(r"^\s*reg\s+\[[^\]]+\]\s+\w+\s+\[0:\d+\];")
    always_pattern = re.compile(r"^\s*(?:always|always_comb|always_ff|always_latch)\b")

    long_line_count = 0
    anonymous_helper_count = 0
    duplicated_block_prefix_count = 0
    deep_mux_assign_count = 0
    missing_header_count = 0
    missing_port_table_count = 0
    unlabeled_always_block_count = 0
    unstable_generated_name_count = 0
    source_map_noise_count = 0
    memory_block_not_grouped_count = 0
    clock_reset_not_visible_count = 0

    normalized_profile = (profile or "review").lower()
    enforce_review_structure = normalized_profile != "compact"

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

        unstable_match = unstable_generated_name_pattern.search(stripped)
        if unstable_match:
            unstable_generated_name_count += 1
            if not (anonymous_match and anonymous_match.group(1) == unstable_match.group(0)):
                findings.append(
                    ReadabilityFinding(
                        kind="unstable_generated_name",
                        line=lineno,
                        detail=f"unstable generated name '{unstable_match.group(0)}' appears in review RTL",
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

        if always_pattern.search(stripped):
            if not _has_recent_always_label(lines, lineno):
                unlabeled_always_block_count += 1
                findings.append(
                    ReadabilityFinding(
                        kind="unlabeled_always_block",
                        line=lineno,
                        detail="always block is missing a nearby Comb/Seq/timing label",
                    )
                )
            if ("posedge" in stripped or "negedge" in stripped) and not _has_recent_seq_timing_comment(lines, lineno):
                clock_reset_not_visible_count += 1
                findings.append(
                    ReadabilityFinding(
                        kind="clock_reset_not_visible",
                        line=lineno,
                        detail="clock/reset timing is not summarized before the sequential block",
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

    if enforce_review_structure:
        if not any(module_header_pattern.search(line) for line in lines):
            module_line = _first_matching_line(lines, module_decl_pattern)
            missing_header_count = 1
            findings.append(
                ReadabilityFinding(
                    kind="missing_module_header",
                    line=module_line,
                    detail="review RTL should include a readable module header before the module declaration",
                )
            )

        if any(module_decl_pattern.search(line) for line in lines) and not any("// Ports:" in line for line in lines):
            module_line = _first_matching_line(lines, module_decl_pattern)
            missing_port_table_count = 1
            findings.append(
                ReadabilityFinding(
                    kind="missing_port_table",
                    line=module_line,
                    detail="review RTL should include a readable port table",
                )
            )

    source_map_lines = [idx for idx, line in enumerate(lines, start=1) if "rtlcraft: source=" in line]
    source_map_budget = max(5, len(lines) // 5)
    if len(source_map_lines) > source_map_budget:
        source_map_noise_count = len(source_map_lines)
        findings.append(
            ReadabilityFinding(
                kind="source_map_noise",
                line=source_map_lines[0],
                detail=(
                    f"{len(source_map_lines)} source-map comments exceed review budget "
                    f"{source_map_budget}; prefer sidecar source maps for dense traces"
                ),
            )
        )

    memory_decl_lines = [idx for idx, line in enumerate(lines, start=1) if memory_decl_pattern.search(line)]
    if memory_decl_lines and not any("Storage declarations" in line for line in lines):
        memory_block_not_grouped_count = len(memory_decl_lines)
        findings.append(
            ReadabilityFinding(
                kind="memory_block_not_grouped",
                line=memory_decl_lines[0],
                detail="memory declarations should be grouped under a storage section marker",
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
        missing_header_count=missing_header_count,
        missing_port_table_count=missing_port_table_count,
        unlabeled_always_block_count=unlabeled_always_block_count,
        unstable_generated_name_count=unstable_generated_name_count,
        source_map_noise_count=source_map_noise_count,
        memory_block_not_grouped_count=memory_block_not_grouped_count,
        clock_reset_not_visible_count=clock_reset_not_visible_count,
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
    lines.append(f"- missing_header_count: `{report.missing_header_count}`")
    lines.append(f"- missing_port_table_count: `{report.missing_port_table_count}`")
    lines.append(f"- unlabeled_always_block_count: `{report.unlabeled_always_block_count}`")
    lines.append(f"- unstable_generated_name_count: `{report.unstable_generated_name_count}`")
    lines.append(f"- source_map_noise_count: `{report.source_map_noise_count}`")
    lines.append(f"- memory_block_not_grouped_count: `{report.memory_block_not_grouped_count}`")
    lines.append(f"- clock_reset_not_visible_count: `{report.clock_reset_not_visible_count}`")
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


def _first_matching_line(lines: Sequence[str], pattern: re.Pattern[str]) -> int:
    for lineno, line in enumerate(lines, start=1):
        if pattern.search(line):
            return lineno
    return 1


def _has_recent_always_label(lines: Sequence[str], lineno: int) -> bool:
    for prior in _recent_nonempty_lines(lines, lineno, window=4):
        stripped = prior.strip()
        if stripped.startswith("// Comb:"):
            return True
        if stripped.startswith("// Seq:"):
            return True
        if stripped.startswith("// Seq timing:"):
            return True
        if stripped.startswith("// Latch"):
            return True
        if stripped.startswith("// Initialization"):
            return True
    return False


def _has_recent_seq_timing_comment(lines: Sequence[str], lineno: int) -> bool:
    return any(prior.strip().startswith("// Seq timing:") for prior in _recent_nonempty_lines(lines, lineno, window=4))


def _recent_nonempty_lines(lines: Sequence[str], lineno: int, *, window: int) -> tuple[str, ...]:
    start = max(0, lineno - window - 1)
    end = max(0, lineno - 1)
    return tuple(line for line in lines[start:end] if line.strip())


def _line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1
