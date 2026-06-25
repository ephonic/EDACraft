"""Report-oriented summarization helpers for PPA results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from rtlgen_x.ppa.advisor import ArchitecturePpaStats, ModulePpaStats, PpaRecommendation, PpaReport
from rtlgen_x.ppa.calibration import CalibratedArchitecturePpaEstimate, CalibratedModulePpaEstimate


@dataclass(frozen=True)
class PpaRecommendationSummary:
    title: str
    category: str
    severity: str
    target: Optional[str]
    pattern_hint: Optional[str]
    focus_anchors: Tuple[str, ...]
    rationale: str
    actions: Tuple[str, ...]


@dataclass(frozen=True)
class RewriteProposalSummary:
    summary: str
    target: str
    origin_anchor: Optional[str]
    applicability: str
    applicability_reason: Optional[str]
    edit_kinds: Tuple[str, ...]


@dataclass(frozen=True)
class PpaTrustSummary:
    scope: str
    mode: str
    sample_count: int
    metrics_available: Tuple[str, ...]
    ranking_signal: str
    recommendation: str


@dataclass(frozen=True)
class PpaReportSummary:
    module_name: Optional[str]
    architecture_present: bool
    module_trust: Optional[PpaTrustSummary]
    architecture_trust: Optional[PpaTrustSummary]
    top_recommendations: Tuple[PpaRecommendationSummary, ...]
    rewrite_proposals: Tuple[RewriteProposalSummary, ...]
    findings: Tuple[str, ...]


def summarize_ppa_report(report: PpaReport, *, max_recommendations: int = 5) -> PpaReportSummary:
    """Condense a PPA report into an agent-friendly summary."""

    if max_recommendations < 1:
        raise ValueError("max_recommendations must be >= 1")
    module_stats = report.module_stats
    architecture_stats = report.architecture_stats
    top_recommendations = tuple(
        _summarize_recommendation(rec) for rec in report.recommendations[:max_recommendations]
    )
    return PpaReportSummary(
        module_name=module_stats.module_name if module_stats is not None else None,
        architecture_present=architecture_stats is not None,
        module_trust=_summarize_module_trust(
            module_stats=module_stats,
            estimate=report.calibrated_module_estimate,
        ),
        architecture_trust=_summarize_architecture_trust(
            stats=architecture_stats,
            estimate=report.calibrated_architecture_estimate,
        ),
        top_recommendations=top_recommendations,
        rewrite_proposals=tuple(_summarize_rewrite_proposal(proposal) for proposal in report.rewrite_proposals),
        findings=_build_findings(
            module_stats=module_stats,
            architecture_stats=architecture_stats,
            recommendations=top_recommendations,
        ),
    )


def emit_ppa_report_markdown(
    report: Optional[PpaReport] = None,
    *,
    summary: Optional[PpaReportSummary] = None,
    title: str = "PPA Report",
) -> str:
    """Render a PPA report summary as compact Markdown."""

    if summary is None:
        if report is None:
            raise ValueError("provide either report or summary")
        summary = summarize_ppa_report(report)
    lines = [
        f"# {title}",
        "",
        "## Scope",
        "",
        f"- module heuristics: {'yes' if summary.module_name is not None else 'no'}",
        f"- architecture heuristics: {'yes' if summary.architecture_present else 'no'}",
    ]
    if summary.module_name is not None:
        lines.append(f"- module name: {summary.module_name}")
    if summary.findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- {finding}" for finding in summary.findings)
    if summary.module_trust is not None or summary.architecture_trust is not None:
        lines.extend(["", "## Calibration Guidance", ""])
        for trust in (summary.module_trust, summary.architecture_trust):
            if trust is None:
                continue
            lines.append(f"### {trust.scope.title()}")
            lines.append("")
            lines.append(f"- mode: `{trust.mode}`")
            lines.append(f"- sample count: {trust.sample_count}")
            lines.append(
                f"- metrics available: {', '.join(trust.metrics_available) if trust.metrics_available else 'heuristic only'}"
            )
            lines.append(f"- preferred ranking signal: `{trust.ranking_signal}`")
            lines.append(f"- guidance: {trust.recommendation}")
            lines.append("")
        if lines[-1] == "":
            lines.pop()
    if summary.top_recommendations:
        lines.extend(["", "## Top Recommendations", ""])
        for rec in summary.top_recommendations:
            target_text = f" ({rec.target})" if rec.target else ""
            pattern_text = f" [{rec.pattern_hint}]" if rec.pattern_hint else ""
            lines.append(f"- [{rec.severity}/{rec.category}] {rec.title}{target_text}{pattern_text}: {rec.rationale}")
            for anchor in rec.focus_anchors:
                lines.append(f"  focus: {anchor}")
            for action in rec.actions:
                lines.append(f"  next: {action}")
    if summary.rewrite_proposals:
        lines.extend(["", "## Rewrite Proposals", ""])
        for proposal in summary.rewrite_proposals:
            lines.append(
                f"- [{proposal.applicability}] {proposal.summary} ({proposal.target})"
            )
            if proposal.origin_anchor:
                lines.append(f"  origin: {proposal.origin_anchor}")
            lines.append(f"  edits: {', '.join(proposal.edit_kinds) if proposal.edit_kinds else 'none'}")
            if proposal.applicability_reason:
                lines.append(f"  note: {proposal.applicability_reason}")
    return "\n".join(lines).rstrip() + "\n"


def _summarize_recommendation(rec: PpaRecommendation) -> PpaRecommendationSummary:
    target = _recommendation_target(rec)
    return PpaRecommendationSummary(
        title=rec.title,
        category=rec.category,
        severity=rec.severity,
        target=target,
        pattern_hint=_recommendation_pattern_hint(rec),
        focus_anchors=_recommendation_focus_anchors(rec),
        rationale=rec.rationale,
        actions=tuple(rec.suggestions[:2]),
    )


def _recommendation_target(rec: PpaRecommendation) -> Optional[str]:
    evidence = rec.evidence
    label = evidence.get("target_label")
    if isinstance(label, str) and label:
        return label
    multiplier_target = _module_target_with_location(
        module_name=evidence.get("module"),
        target_name=evidence.get("widest_multiplier_assignment_target"),
        source_file=evidence.get("widest_multiplier_source_file"),
        source_line=evidence.get("widest_multiplier_source_line"),
    )
    if multiplier_target is not None:
        return multiplier_target
    critical_target = _module_target_with_location(
        module_name=evidence.get("module"),
        target_name=evidence.get("critical_assignment_target"),
        source_file=evidence.get("critical_assignment_source_file"),
        source_line=evidence.get("critical_assignment_source_line"),
    )
    if critical_target is not None:
        return critical_target
    for key in ("largest_memory_name", "largest_state_name", "dominant_area_stage", "dominant_power_stage"):
        value = evidence.get(key)
        module_name = evidence.get("module")
        if isinstance(value, str) and value:
            if key == "largest_memory_name":
                source_file = evidence.get("largest_memory_source_file")
                source_line = evidence.get("largest_memory_source_line")
                target = _module_target_with_location(
                    module_name=module_name,
                    target_name=value,
                    source_file=source_file,
                    source_line=source_line,
                )
                if target is not None:
                    return target
            if key == "largest_state_name":
                source_file = evidence.get("largest_state_source_file")
                source_line = evidence.get("largest_state_source_line")
                target = _module_target_with_location(
                    module_name=module_name,
                    target_name=value,
                    source_file=source_file,
                    source_line=source_line,
                )
                if target is not None:
                    return target
            if isinstance(module_name, str) and module_name:
                return f"{module_name}.{value}"
            return value
    for key in ("module", "stage", "bottleneck_stage", "flow"):
        value = evidence.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _summarize_rewrite_proposal(proposal) -> RewriteProposalSummary:
    anchor_target = proposal.source_assignment
    for edit in proposal.edits:
        if edit.kind in {"replace_assignment_expr", "append_assignment"} and isinstance(edit.target, str) and edit.target:
            anchor_target = edit.target
            break
    return RewriteProposalSummary(
        summary=proposal.summary,
        target=anchor_target,
        origin_anchor=getattr(proposal, "origin_anchor", None),
        applicability=proposal.applicability,
        applicability_reason=proposal.applicability_reason,
        edit_kinds=tuple(edit.kind for edit in proposal.edits),
    )


def _recommendation_focus_anchors(rec: PpaRecommendation) -> Tuple[str, ...]:
    evidence = rec.evidence
    for key in (
        "handshake_payload_anchors",
        "queue_control_anchors",
        "queue_sideband_anchors",
        "register_bank_control_anchors",
    ):
        value = evidence.get(key)
        if isinstance(value, tuple):
            anchors = tuple(anchor for anchor in value if isinstance(anchor, str) and anchor)
            if anchors:
                return anchors[:3]
    return ()


def _recommendation_pattern_hint(rec: PpaRecommendation) -> Optional[str]:
    evidence = rec.evidence
    for key in ("multiplier_pattern_hint", "memory_pattern_hint", "state_pattern_hint"):
        value = evidence.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _module_target_with_location(
    *,
    module_name: object,
    target_name: object,
    source_file: object,
    source_line: object,
) -> Optional[str]:
    if not isinstance(module_name, str) or not module_name:
        return None
    if not isinstance(target_name, str) or not target_name:
        return None
    base = f"{module_name}.{target_name}"
    location = _source_site(source_file, source_line)
    if location is None:
        return base
    return f"{base} @ {location}"


def _source_site(source_file: object, source_line: object) -> Optional[str]:
    if not isinstance(source_file, str) or not source_file:
        return None
    if isinstance(source_line, int):
        return f"{source_file}:{source_line}"
    return source_file


def _summarize_module_trust(
    *,
    module_stats: Optional[ModulePpaStats],
    estimate: Optional[CalibratedModulePpaEstimate],
) -> Optional[PpaTrustSummary]:
    if module_stats is None and estimate is None:
        return None
    if estimate is None:
        return PpaTrustSummary(
            scope="module",
            mode="heuristic_only",
            sample_count=0,
            metrics_available=(),
            ranking_signal="heuristic_score",
            recommendation=(
                "Use structural hotspot attribution and heuristic area/power scores for early triage. "
                "Treat the numbers as relative, not signoff-quality."
            ),
        )
    metrics = []
    if estimate.critical_path_ns is not None:
        metrics.append("timing")
    if estimate.total_area is not None:
        metrics.append("area")
    if estimate.total_power_mw is not None:
        metrics.append("power")
    if not metrics:
        return PpaTrustSummary(
            scope="module",
            mode="heuristic_only",
            sample_count=estimate.calibration_sample_count,
            metrics_available=(),
            ranking_signal="heuristic_score",
            recommendation=(
                "Calibration samples exist, but no concrete timing/area/power scaling landed yet. "
                "Stay on heuristic ranking until implementation data is richer."
            ),
        )
    mode, recommendation = _calibration_mode_and_guidance(estimate.calibration_sample_count, scope="module")
    return PpaTrustSummary(
        scope="module",
        mode=mode,
        sample_count=estimate.calibration_sample_count,
        metrics_available=tuple(metrics),
        ranking_signal="calibrated_estimate",
        recommendation=recommendation,
    )


def _summarize_architecture_trust(
    *,
    stats: Optional[ArchitecturePpaStats],
    estimate: Optional[CalibratedArchitecturePpaEstimate],
) -> Optional[PpaTrustSummary]:
    if stats is None and estimate is None:
        return None
    if estimate is None:
        return PpaTrustSummary(
            scope="architecture",
            mode="heuristic_only",
            sample_count=0,
            metrics_available=(),
            ranking_signal="throughput_stall_proxy",
            recommendation=(
                "Use architecture throughput, stall, queue-pressure, and stage proxy totals for relative ranking. "
                "Treat them as exploration signals rather than physical predictions."
            ),
        )
    mode, recommendation = _calibration_mode_and_guidance(estimate.calibration_sample_count, scope="architecture")
    return PpaTrustSummary(
        scope="architecture",
        mode=mode,
        sample_count=estimate.calibration_sample_count,
        metrics_available=("cycles", "makespan", "throughput", "stall"),
        ranking_signal="calibrated_estimate",
        recommendation=recommendation,
    )


def _calibration_mode_and_guidance(sample_count: int, *, scope: str) -> Tuple[str, str]:
    if sample_count <= 1:
        return (
            "directional_calibrated",
            (
                f"Use the calibrated {scope} estimate directionally inside the same design family and "
                "implementation setup, but refresh it before trusting close tradeoffs."
            ),
        )
    if sample_count < 3:
        return (
            "limited_calibrated",
            (
                f"Prefer the calibrated {scope} estimate over raw heuristic scores for similar variants, "
                "but keep collecting implementation feedback before using it as the only ranking signal."
            ),
        )
    return (
        "calibrated_default",
        (
            f"Use the calibrated {scope} estimate as the default ranking signal for nearby design variants, "
            "and refresh it whenever workload mix or backend flow moves materially."
        ),
    )


def _build_findings(
    *,
    module_stats: Optional[ModulePpaStats],
    architecture_stats: Optional[ArchitecturePpaStats],
    recommendations: Tuple[PpaRecommendationSummary, ...],
) -> Tuple[str, ...]:
    findings = []
    if module_stats is not None:
        findings.append(
            f"Module '{module_stats.module_name}' reaches logic depth {module_stats.max_expr_depth}; "
            f"dominant area bucket is '{module_stats.dominant_area_bucket}' and dominant power bucket is "
            f"'{module_stats.dominant_power_bucket}'."
        )
        if module_stats.largest_memory_name is not None:
            target = _module_target_with_location(
                module_name=module_stats.module_name,
                target_name=module_stats.largest_memory_name,
                source_file=module_stats.largest_memory_source_file,
                source_line=module_stats.largest_memory_source_line,
            )
            findings.append(
                f"Largest storage object is '{target or module_stats.largest_memory_name}' at "
                f"{module_stats.largest_memory_bits} bits."
            )
    if architecture_stats is not None and architecture_stats.flow_stats:
        lowest_flow = min(
            architecture_stats.flow_stats.values(),
            key=lambda item: (item.throughput_tokens_per_cycle, -item.stall_ratio, item.name),
        )
        findings.append(
            f"Slowest architectural flow is '{lowest_flow.name}', bottlenecking on "
            f"'{lowest_flow.bottleneck_stage}' at {lowest_flow.throughput_tokens_per_cycle:.3f} tokens/cycle."
        )
        findings.append(
            f"Architecture proxy totals: bytes moved={architecture_stats.total_bytes_moved}, "
            f"dominant area stage='{architecture_stats.dominant_area_stage}', "
            f"dominant power stage='{architecture_stats.dominant_power_stage}'."
        )
    if recommendations:
        findings.append(f"Highest-priority recommendation is '{recommendations[0].title}'.")
    return tuple(findings)
