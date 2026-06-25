"""Architecture-report summarization helpers for archsim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from rtlgen_x.archsim.behavior import BehaviorReport, BehaviorSimulator
from rtlgen_x.archsim.cycle import CycleReport, CycleSimulator
from rtlgen_x.archsim.explore import StageSweepReport, UpgradeCandidate
from rtlgen_x.archsim.model import ArchitectureModel, FlowSpec, Workload


@dataclass(frozen=True)
class ArchitectureFlowSummary:
    name: str
    path: Tuple[str, ...]
    tokens: int
    bytes_per_token: int
    start_cycle: int
    pipeline_latency: int
    steady_state_ii: float
    throughput_tokens_per_cycle: float
    behavior_total_cycles: float
    cycle_total_cycles: int
    cycle_throughput_tokens_per_cycle: float
    stall_ratio: float
    bottleneck_stage: str


@dataclass(frozen=True)
class ArchitectureStageSummary:
    name: str
    kind: str
    latency: int
    initiation_interval: int
    capacity: int
    queue_depth: int
    bandwidth_bytes_per_cycle: int
    behavior_tokens: int
    behavior_busy_cycles: float
    bytes_moved: int
    cycle_started_tokens: int
    cycle_completed_tokens: int
    busy_token_cycles: int
    max_ready_depth: int
    utilization: float
    queue_pressure: float
    shared_resource: str
    shared_resource_utilization: float
    contention_capacity: int
    flows: Tuple[str, ...]


@dataclass(frozen=True)
class ArchitectureSweepSummary:
    stage_name: str
    knob: str
    baseline_value: int
    recommended_value: int
    baseline_cycles: int
    improved_cycles: int
    cycle_reduction: int
    speedup: float
    baseline_throughput_tokens_per_cycle: float
    improved_throughput_tokens_per_cycle: float


@dataclass(frozen=True)
class ArchitectureReportSummary:
    stage_count: int
    flow_count: int
    total_tokens: int
    behavior_makespan_cycles: float
    cycle_total_cycles: int
    aggregate_throughput_tokens_per_cycle: float
    flow_summaries: Tuple[ArchitectureFlowSummary, ...]
    stage_summaries: Tuple[ArchitectureStageSummary, ...]
    sweep_summaries: Tuple[ArchitectureSweepSummary, ...]
    upgrade_candidates: Tuple[UpgradeCandidate, ...]
    findings: Tuple[str, ...]


def summarize_architecture_report(
    model: ArchitectureModel,
    workload: Workload,
    *,
    behavior_report: Optional[BehaviorReport] = None,
    cycle_report: Optional[CycleReport] = None,
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
) -> ArchitectureReportSummary:
    """Condense architecture simulation artifacts into an agent-friendly summary."""

    behavior_report = behavior_report or BehaviorSimulator().run(model, workload)
    cycle_report = cycle_report or CycleSimulator().run(model, workload)
    stage_names = tuple(model.stages)

    flow_summaries = tuple(
        _summarize_flow(flow, behavior_report=behavior_report, cycle_report=cycle_report)
        for flow in workload.flows
    )
    stage_summaries = tuple(
        _summarize_stage(
            model,
            stage_name,
            behavior_report=behavior_report,
            cycle_report=cycle_report,
        )
        for stage_name in stage_names
    )
    sweep_summaries = tuple(
        sorted(
            (
                _summarize_sweep(model, report)
                for report in sweep_reports
            ),
            key=lambda item: (-item.cycle_reduction, -item.speedup, item.stage_name, item.knob),
        )
    )
    candidates = tuple(
        sorted(
            upgrade_candidates,
            key=lambda item: (-item.cycle_reduction, -item.speedup, item.stage_name, item.knob),
        )
    )

    return ArchitectureReportSummary(
        stage_count=len(stage_names),
        flow_count=len(workload.flows),
        total_tokens=sum(flow.tokens for flow in workload.flows),
        behavior_makespan_cycles=behavior_report.makespan_cycles,
        cycle_total_cycles=cycle_report.total_cycles,
        aggregate_throughput_tokens_per_cycle=_aggregate_cycle_throughput(workload, cycle_report),
        flow_summaries=flow_summaries,
        stage_summaries=stage_summaries,
        sweep_summaries=sweep_summaries,
        upgrade_candidates=candidates,
        findings=_build_findings(flow_summaries, stage_summaries, sweep_summaries),
    )


def emit_architecture_report_markdown(
    summary: Optional[ArchitectureReportSummary] = None,
    *,
    model: Optional[ArchitectureModel] = None,
    workload: Optional[Workload] = None,
    behavior_report: Optional[BehaviorReport] = None,
    cycle_report: Optional[CycleReport] = None,
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
    title: str = "Architecture Report",
) -> str:
    """Render an architecture summary as compact Markdown."""

    if summary is None:
        if model is None or workload is None:
            raise ValueError("provide either summary or both model and workload")
        summary = summarize_architecture_report(
            model,
            workload,
            behavior_report=behavior_report,
            cycle_report=cycle_report,
            sweep_reports=sweep_reports,
            upgrade_candidates=upgrade_candidates,
        )

    lines = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        f"- stages: {summary.stage_count}",
        f"- flows: {summary.flow_count}",
        f"- total tokens: {summary.total_tokens}",
        f"- behavior makespan cycles: {summary.behavior_makespan_cycles:.3f}",
        f"- cycle total cycles: {summary.cycle_total_cycles}",
        f"- aggregate throughput: {summary.aggregate_throughput_tokens_per_cycle:.3f} tokens/cycle",
    ]
    heuristic_notes = _collect_estimation_notes(model) if model is not None else ()
    if heuristic_notes:
        lines.extend(
            [
                "",
                "### Modeling Scope",
                "",
            ]
        )
        lines.extend(f"- {note}" for note in heuristic_notes)
    if summary.findings:
        lines.extend(["", "### Findings", ""])
        lines.extend(f"- {finding}" for finding in summary.findings)

    lines.extend(
        [
            "",
            "## Flows",
            "",
            "| Flow | Path | Tokens | Start | B/Tok | Bottleneck | Beh II | Beh TP | Cycle Cycles | Stall Ratio |",
            "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for flow in summary.flow_summaries:
        lines.append(
            "| "
            f"{flow.name} | {' -> '.join(flow.path)} | {flow.tokens} | {flow.start_cycle} | {flow.bytes_per_token} | "
            f"{flow.bottleneck_stage} | {flow.steady_state_ii:.3f} | {flow.throughput_tokens_per_cycle:.3f} | "
            f"{flow.cycle_total_cycles} | {flow.stall_ratio:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Stages",
            "",
            "| Stage | Kind | Lat | II | Cap | Queue | BW | Util | Shared Util | Queue Pressure | Bytes | Flows |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for stage in summary.stage_summaries:
        lines.append(
            "| "
            f"{stage.name} | {stage.kind} | {stage.latency} | {stage.initiation_interval} | {stage.capacity} | "
            f"{stage.queue_depth} | {stage.bandwidth_bytes_per_cycle} | {stage.utilization:.3f} | "
            f"{stage.shared_resource_utilization:.3f} | "
            f"{stage.queue_pressure:.3f} | {stage.bytes_moved} | {', '.join(stage.flows) or '-'} |"
        )

    if summary.sweep_summaries:
        lines.extend(
            [
                "",
                "## Sweep Evidence",
                "",
                "| Stage | Knob | Baseline | Recommended | Baseline Cycles | Improved Cycles | Delta | Speedup | TP Delta |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for sweep in summary.sweep_summaries:
            throughput_delta = (
                sweep.improved_throughput_tokens_per_cycle - sweep.baseline_throughput_tokens_per_cycle
            )
            lines.append(
                "| "
                f"{sweep.stage_name} | {sweep.knob} | {sweep.baseline_value} | {sweep.recommended_value} | "
                f"{sweep.baseline_cycles} | {sweep.improved_cycles} | {sweep.cycle_reduction} | "
                f"{sweep.speedup:.3f} | {throughput_delta:.3f} |"
            )

    if summary.upgrade_candidates:
        lines.extend(["", "## Ranked Upgrades", ""])
        for candidate in summary.upgrade_candidates:
            lines.append(
                "- "
                f"`{candidate.stage_name}` `{candidate.knob}`: {candidate.baseline_value} -> "
                f"{candidate.recommended_value} ({candidate.cycle_reduction} cycle reduction, "
                f"{candidate.speedup:.3f}x speedup). {candidate.rationale}"
            )

    return "\n".join(lines).rstrip() + "\n"


def _summarize_flow(
    flow: FlowSpec,
    *,
    behavior_report: BehaviorReport,
    cycle_report: CycleReport,
) -> ArchitectureFlowSummary:
    behavior_metrics = behavior_report.flow_metrics[flow.name]
    cycle_metrics = cycle_report.flow_metrics[flow.name]
    stall_ratio = cycle_metrics.stalled_cycles / max(cycle_metrics.issued_tokens, 1)
    cycle_tp = (
        cycle_metrics.completed_tokens / cycle_metrics.total_cycles
        if cycle_metrics.total_cycles > 0
        else 0.0
    )
    return ArchitectureFlowSummary(
        name=flow.name,
        path=tuple(flow.path),
        tokens=flow.tokens,
        bytes_per_token=flow.bytes_per_token,
        start_cycle=flow.start_cycle,
        pipeline_latency=behavior_metrics.pipeline_latency,
        steady_state_ii=behavior_metrics.steady_state_ii,
        throughput_tokens_per_cycle=behavior_metrics.throughput_tokens_per_cycle,
        behavior_total_cycles=behavior_metrics.total_cycles,
        cycle_total_cycles=cycle_metrics.total_cycles,
        cycle_throughput_tokens_per_cycle=cycle_tp,
        stall_ratio=stall_ratio,
        bottleneck_stage=behavior_metrics.bottleneck_stage,
    )


def _summarize_stage(
    model: ArchitectureModel,
    stage_name: str,
    *,
    behavior_report: BehaviorReport,
    cycle_report: CycleReport,
) -> ArchitectureStageSummary:
    stage = model.stage(stage_name)
    behavior_metrics = behavior_report.stage_metrics.get(stage_name)
    cycle_metrics = cycle_report.stage_metrics[stage_name]
    queue_capacity = max(model.queue_capacity(stage_name), 1)
    utilization = cycle_metrics.busy_token_cycles / max(cycle_report.total_cycles * stage.capacity, 1)
    contention_capacity = model.stage_contention_capacity(stage_name)
    shared_resource_utilization = (
        cycle_metrics.shared_resource_busy_cycles / max(cycle_report.total_cycles * contention_capacity, 1)
    )
    queue_pressure = cycle_metrics.max_ready_depth / queue_capacity
    return ArchitectureStageSummary(
        name=stage.name,
        kind=stage.kind,
        latency=stage.latency,
        initiation_interval=stage.initiation_interval,
        capacity=stage.capacity,
        queue_depth=stage.queue_depth,
        bandwidth_bytes_per_cycle=stage.bandwidth_bytes_per_cycle,
        behavior_tokens=behavior_metrics.tokens if behavior_metrics is not None else 0,
        behavior_busy_cycles=behavior_metrics.busy_cycles if behavior_metrics is not None else 0.0,
        bytes_moved=behavior_metrics.bytes_moved if behavior_metrics is not None else 0,
        cycle_started_tokens=cycle_metrics.started_tokens,
        cycle_completed_tokens=cycle_metrics.completed_tokens,
        busy_token_cycles=cycle_metrics.busy_token_cycles,
        max_ready_depth=cycle_metrics.max_ready_depth,
        utilization=utilization,
        queue_pressure=queue_pressure,
        shared_resource=cycle_metrics.shared_resource,
        shared_resource_utilization=shared_resource_utilization,
        contention_capacity=contention_capacity,
        flows=tuple(behavior_metrics.flows) if behavior_metrics is not None else (),
    )


def _summarize_sweep(model: ArchitectureModel, report: StageSweepReport) -> ArchitectureSweepSummary:
    stage = model.stage(report.stage_name)
    best_point = report.best_point
    return ArchitectureSweepSummary(
        stage_name=report.stage_name,
        knob=report.knob,
        baseline_value=_stage_knob_value(stage, report.knob),
        recommended_value=_sweep_point_value(best_point, report.knob),
        baseline_cycles=report.baseline_cycles,
        improved_cycles=best_point.cycle_total_cycles,
        cycle_reduction=report.baseline_cycles - best_point.cycle_total_cycles,
        speedup=best_point.speedup_vs_baseline,
        baseline_throughput_tokens_per_cycle=report.baseline_throughput_tokens_per_cycle,
        improved_throughput_tokens_per_cycle=best_point.aggregate_throughput_tokens_per_cycle,
    )


def _build_findings(
    flow_summaries: Sequence[ArchitectureFlowSummary],
    stage_summaries: Sequence[ArchitectureStageSummary],
    sweep_summaries: Sequence[ArchitectureSweepSummary],
) -> Tuple[str, ...]:
    findings = []
    if flow_summaries:
        lowest_tp = min(
            flow_summaries,
            key=lambda item: (item.throughput_tokens_per_cycle, -item.stall_ratio, item.name),
        )
        findings.append(
            f"Lowest-throughput flow '{lowest_tp.name}' bottlenecks on '{lowest_tp.bottleneck_stage}' "
            f"at {lowest_tp.throughput_tokens_per_cycle:.3f} tokens/cycle with II {lowest_tp.steady_state_ii:.3f}."
        )
        highest_stall = max(flow_summaries, key=lambda item: (item.stall_ratio, item.name))
        if highest_stall.stall_ratio > 0:
            findings.append(
                f"Flow '{highest_stall.name}' sees stall ratio {highest_stall.stall_ratio:.3f} "
                f"over {highest_stall.cycle_total_cycles} cycle-level cycles."
            )
    if stage_summaries:
        hottest_stage = max(
            stage_summaries,
            key=lambda item: (item.queue_pressure, item.utilization, item.bytes_moved, item.name),
        )
        findings.append(
            f"Stage '{hottest_stage.name}' ({hottest_stage.kind}) reaches queue pressure "
            f"{hottest_stage.queue_pressure:.3f} and utilization {hottest_stage.utilization:.3f}."
        )
        if hottest_stage.queue_pressure >= 0.75:
            findings.append(
                f"Stage '{hottest_stage.name}' is queue-pressure limited; explore deeper buffering "
                f"or upstream/downstream rate balancing around that stage."
            )
        most_contended = max(
            stage_summaries,
            key=lambda item: (item.shared_resource_utilization, item.utilization, item.name),
        )
        if most_contended.shared_resource and most_contended.shared_resource_utilization > 0.8:
            findings.append(
                f"Shared resource '{most_contended.shared_resource}' is contended across stage group including "
                f"'{most_contended.name}' at effective utilization {most_contended.shared_resource_utilization:.3f}."
            )
    if sweep_summaries:
        best_sweep = max(
            sweep_summaries,
            key=lambda item: (item.cycle_reduction, item.speedup, item.stage_name, item.knob),
        )
        if best_sweep.cycle_reduction > 0:
            findings.append(
                f"Best explored knob was '{best_sweep.knob}' on stage '{best_sweep.stage_name}', "
                f"reducing total cycles by {best_sweep.cycle_reduction}."
            )
            if best_sweep.knob == "bandwidth_bytes_per_cycle":
                findings.append(
                    f"Explored evidence points to a bandwidth-limited bottleneck at '{best_sweep.stage_name}'."
                )
            elif best_sweep.knob == "queue_depth":
                findings.append(
                    f"Explored evidence points to queueing pressure around '{best_sweep.stage_name}'."
                )
            elif best_sweep.knob == "capacity":
                findings.append(
                    f"Explored evidence points to insufficient parallel capacity at '{best_sweep.stage_name}'."
                )
            elif best_sweep.knob == "initiation_interval":
                findings.append(
                    f"Explored evidence points to initiation-interval pressure at '{best_sweep.stage_name}'."
                )
            elif best_sweep.knob == "latency":
                findings.append(
                    f"Explored evidence points to latency pressure at '{best_sweep.stage_name}'."
                )
    return tuple(findings)


def _collect_estimation_notes(model: ArchitectureModel) -> Tuple[str, ...]:
    notes = []
    seen = set()
    for stage in model.stages.values():
        note = stage.metadata.get("estimation")
        if not note:
            continue
        text = str(note)
        if text in seen:
            continue
        seen.add(text)
        notes.append(text)
    return tuple(notes)


def _aggregate_cycle_throughput(workload: Workload, cycle_report: CycleReport) -> float:
    total_tokens = sum(flow.tokens for flow in workload.flows)
    if cycle_report.total_cycles <= 0:
        return 0.0
    return total_tokens / cycle_report.total_cycles


def _stage_knob_value(stage, knob: str) -> int:
    return int(getattr(stage, knob))


def _sweep_point_value(point, knob: str) -> int:
    return int(getattr(point, knob))
