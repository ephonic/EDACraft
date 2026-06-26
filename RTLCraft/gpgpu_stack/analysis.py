"""Architecture-report helpers for software-side workload traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from rtlgen_x.archsim import (
    ArchitectureModel,
    ArchitectureReportSummary,
    BehaviorReport,
    BehaviorSimulator,
    CycleReport,
    CycleSimulator,
    StageSweepReport,
    UpgradeCandidate,
    Workload,
    emit_architecture_report_markdown,
    summarize_architecture_report,
)

from gpgpu_stack.abi import WorkloadTrace, workload_trace_to_archsim_workload


@dataclass(frozen=True)
class TraceArchitectureEvaluation:
    """One completed architecture evaluation for a software-side workload trace."""

    trace: WorkloadTrace
    workload: Workload
    behavior_report: BehaviorReport
    cycle_report: CycleReport
    summary: ArchitectureReportSummary
    markdown: str


def evaluate_workload_trace(
    trace: WorkloadTrace,
    model: ArchitectureModel,
    *,
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
    title: Optional[str] = None,
) -> TraceArchitectureEvaluation:
    """Run behavior/cycle/report flow for one software-side workload trace."""

    workload = workload_trace_to_archsim_workload(trace)
    behavior_report = BehaviorSimulator().run(model, workload)
    cycle_report = CycleSimulator().run(model, workload)
    summary = summarize_architecture_report(
        model,
        workload,
        behavior_report=behavior_report,
        cycle_report=cycle_report,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
    )
    markdown = emit_architecture_report_markdown(
        summary=summary,
        model=model,
        title=title or f"{trace.kernel.kernel_name} Architecture Report",
    )
    return TraceArchitectureEvaluation(
        trace=trace,
        workload=workload,
        behavior_report=behavior_report,
        cycle_report=cycle_report,
        summary=summary,
        markdown=markdown,
    )


def emit_workload_trace_architecture_report_markdown(
    trace: WorkloadTrace,
    model: ArchitectureModel,
    *,
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
    title: Optional[str] = None,
) -> str:
    """Convenience helper that returns only the rendered report."""

    return evaluate_workload_trace(
        trace,
        model,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
        title=title,
    ).markdown


__all__ = [
    "TraceArchitectureEvaluation",
    "emit_workload_trace_architecture_report_markdown",
    "evaluate_workload_trace",
]
