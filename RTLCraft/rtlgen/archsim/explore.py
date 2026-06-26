"""What-if exploration helpers built on top of archsim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from rtlgen.archsim.behavior import BehaviorReport, BehaviorSimulator
from rtlgen.archsim.cycle import CycleReport, CycleSimulator
from rtlgen.archsim.model import ArchitectureModel, StageSpec, Workload


@dataclass(frozen=True)
class SweepPoint:
    """One explored stage configuration point."""

    stage_name: str
    latency: int
    capacity: int
    initiation_interval: int
    queue_depth: int
    bandwidth_bytes_per_cycle: int
    behavior_makespan_cycles: float
    cycle_total_cycles: int
    aggregate_throughput_tokens_per_cycle: float
    speedup_vs_baseline: float


@dataclass(frozen=True)
class StageSweepReport:
    """Result of sweeping one stage-level knob."""

    stage_name: str
    knob: str
    baseline_cycles: int
    baseline_throughput_tokens_per_cycle: float
    points: Tuple[SweepPoint, ...]

    @property
    def best_point(self) -> SweepPoint:
        return min(self.points, key=lambda point: point.cycle_total_cycles)


@dataclass(frozen=True)
class UpgradeCandidate:
    """A ranked upgrade suggestion backed by a sweep."""

    stage_name: str
    knob: str
    baseline_value: int
    recommended_value: int
    baseline_cycles: int
    improved_cycles: int
    cycle_reduction: int
    speedup: float
    rationale: str


def run_stage_capacity_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    capacities: Sequence[int],
) -> StageSweepReport:
    """Sweep stage capacity and collect throughput/latency changes."""

    return _run_stage_sweep(
        model,
        workload,
        stage_name,
        knob="capacity",
        values=capacities,
    )


def run_stage_initiation_interval_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    initiation_intervals: Sequence[int],
) -> StageSweepReport:
    """Sweep stage initiation interval and collect throughput/latency changes."""

    return _run_stage_sweep(
        model,
        workload,
        stage_name,
        knob="initiation_interval",
        values=initiation_intervals,
    )


def run_stage_latency_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    latencies: Sequence[int],
) -> StageSweepReport:
    """Sweep stage latency and collect throughput/latency changes."""

    return _run_stage_sweep(
        model,
        workload,
        stage_name,
        knob="latency",
        values=latencies,
    )


def run_stage_queue_depth_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    queue_depths: Sequence[int],
) -> StageSweepReport:
    """Sweep stage queue depth and collect throughput/latency changes."""

    return _run_stage_sweep(
        model,
        workload,
        stage_name,
        knob="queue_depth",
        values=queue_depths,
    )


def run_stage_bandwidth_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    bandwidths: Sequence[int],
) -> StageSweepReport:
    """Sweep stage bandwidth and collect throughput/latency changes."""

    return _run_stage_sweep(
        model,
        workload,
        stage_name,
        knob="bandwidth_bytes_per_cycle",
        values=bandwidths,
    )


def rank_capacity_upgrades(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_capacities: Sequence[int] = (2, 4),
    max_recommendations: int = 5,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank stage-capacity upgrades by cycle reduction."""

    candidates = []
    for stage_name, stage in model.stages.items():
        sweep_values = [stage.capacity] + [value for value in candidate_capacities if value > stage.capacity]
        if len(sweep_values) < 2:
            continue
        report = run_stage_capacity_sweep(model, workload, stage_name, sweep_values)
        best = report.best_point
        if best.cycle_total_cycles >= report.baseline_cycles:
            continue
        candidates.append(
            UpgradeCandidate(
                stage_name=stage_name,
                knob="capacity",
                baseline_value=stage.capacity,
                recommended_value=best.capacity,
                baseline_cycles=report.baseline_cycles,
                improved_cycles=best.cycle_total_cycles,
                cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
                speedup=best.speedup_vs_baseline,
                rationale=(
                    f"Improves total cycles from {report.baseline_cycles} to {best.cycle_total_cycles} "
                    f"by widening stage '{stage_name}' from {stage.capacity} to {best.capacity}."
                ),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name),
    )
    return tuple(ranked[:max_recommendations])


def rank_initiation_interval_upgrades(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_initiation_intervals: Sequence[int] = (1,),
    max_recommendations: int = 5,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank stage II reductions by cycle reduction."""

    candidates = []
    for stage_name, stage in model.stages.items():
        sweep_values = [stage.initiation_interval] + [
            value for value in candidate_initiation_intervals if value < stage.initiation_interval
        ]
        if len(sweep_values) < 2:
            continue
        report = run_stage_initiation_interval_sweep(model, workload, stage_name, sweep_values)
        best = report.best_point
        if best.cycle_total_cycles >= report.baseline_cycles:
            continue
        candidates.append(
            UpgradeCandidate(
                stage_name=stage_name,
                knob="initiation_interval",
                baseline_value=stage.initiation_interval,
                recommended_value=best.initiation_interval,
                baseline_cycles=report.baseline_cycles,
                improved_cycles=best.cycle_total_cycles,
                cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
                speedup=best.speedup_vs_baseline,
                rationale=(
                    f"Improves total cycles from {report.baseline_cycles} to {best.cycle_total_cycles} "
                    f"by reducing stage '{stage_name}' II from {stage.initiation_interval} to {best.initiation_interval}."
                ),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name),
    )
    return tuple(ranked[:max_recommendations])


def rank_latency_upgrades(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_latencies: Sequence[int] = (1,),
    max_recommendations: int = 5,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank stage latency reductions by cycle reduction."""

    candidates = []
    for stage_name, stage in model.stages.items():
        sweep_values = [stage.latency] + [value for value in candidate_latencies if value < stage.latency]
        if len(sweep_values) < 2:
            continue
        report = run_stage_latency_sweep(model, workload, stage_name, sweep_values)
        best = report.best_point
        if best.cycle_total_cycles >= report.baseline_cycles:
            continue
        candidates.append(
            UpgradeCandidate(
                stage_name=stage_name,
                knob="latency",
                baseline_value=stage.latency,
                recommended_value=best.latency,
                baseline_cycles=report.baseline_cycles,
                improved_cycles=best.cycle_total_cycles,
                cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
                speedup=best.speedup_vs_baseline,
                rationale=(
                    f"Improves total cycles from {report.baseline_cycles} to {best.cycle_total_cycles} "
                    f"by reducing stage '{stage_name}' latency from {stage.latency} to {best.latency}."
                ),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name),
    )
    return tuple(ranked[:max_recommendations])


def rank_queue_depth_upgrades(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_queue_depths: Sequence[int] = (2, 4, 8),
    max_recommendations: int = 5,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank queue-depth increases by cycle reduction."""

    candidates = []
    for stage_name, stage in model.stages.items():
        sweep_values = [stage.queue_depth] + [value for value in candidate_queue_depths if value > stage.queue_depth]
        if len(sweep_values) < 2:
            continue
        report = run_stage_queue_depth_sweep(model, workload, stage_name, sweep_values)
        best = report.best_point
        if best.cycle_total_cycles >= report.baseline_cycles:
            continue
        candidates.append(
            UpgradeCandidate(
                stage_name=stage_name,
                knob="queue_depth",
                baseline_value=stage.queue_depth,
                recommended_value=best.queue_depth,
                baseline_cycles=report.baseline_cycles,
                improved_cycles=best.cycle_total_cycles,
                cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
                speedup=best.speedup_vs_baseline,
                rationale=(
                    f"Improves total cycles from {report.baseline_cycles} to {best.cycle_total_cycles} "
                    f"by increasing queue depth at '{stage_name}' from {stage.queue_depth} to {best.queue_depth}."
                ),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name),
    )
    return tuple(ranked[:max_recommendations])


def rank_bandwidth_upgrades(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_bandwidths: Sequence[int] = (32, 64, 128),
    max_recommendations: int = 5,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank stage-bandwidth increases by cycle reduction."""

    candidates = []
    for stage_name, stage in model.stages.items():
        sweep_values = [stage.bandwidth_bytes_per_cycle] + [
            value for value in candidate_bandwidths if value > stage.bandwidth_bytes_per_cycle
        ]
        if len(sweep_values) < 2:
            continue
        report = run_stage_bandwidth_sweep(model, workload, stage_name, sweep_values)
        best = report.best_point
        if best.cycle_total_cycles >= report.baseline_cycles:
            continue
        candidates.append(
            UpgradeCandidate(
                stage_name=stage_name,
                knob="bandwidth_bytes_per_cycle",
                baseline_value=stage.bandwidth_bytes_per_cycle,
                recommended_value=best.bandwidth_bytes_per_cycle,
                baseline_cycles=report.baseline_cycles,
                improved_cycles=best.cycle_total_cycles,
                cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
                speedup=best.speedup_vs_baseline,
                rationale=(
                    f"Improves total cycles from {report.baseline_cycles} to {best.cycle_total_cycles} "
                    f"by increasing bandwidth at '{stage_name}' from "
                    f"{stage.bandwidth_bytes_per_cycle} to {best.bandwidth_bytes_per_cycle} bytes/cycle."
                ),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name),
    )
    return tuple(ranked[:max_recommendations])


def rank_upgrade_opportunities(
    model: ArchitectureModel,
    workload: Workload,
    *,
    candidate_capacities: Sequence[int] = (2, 4),
    candidate_initiation_intervals: Sequence[int] = (1,),
    candidate_latencies: Sequence[int] = (1,),
    candidate_queue_depths: Sequence[int] = (2, 4, 8),
    candidate_bandwidths: Sequence[int] = (32, 64, 128),
    max_recommendations: int = 8,
) -> Tuple[UpgradeCandidate, ...]:
    """Rank all explored stage-upgrade opportunities in one combined list.

    This helper is intentionally simple: it merges the existing per-knob
    rankers, deduplicates exact repeated recommendations, and sorts by the same
    cycle-reduction-first policy used elsewhere so an agent can consume one
    compact upgrade list instead of stitching several together manually.
    """

    merged = (
        rank_capacity_upgrades(
            model,
            workload,
            candidate_capacities=candidate_capacities,
            max_recommendations=max_recommendations,
        )
        + rank_initiation_interval_upgrades(
            model,
            workload,
            candidate_initiation_intervals=candidate_initiation_intervals,
            max_recommendations=max_recommendations,
        )
        + rank_latency_upgrades(
            model,
            workload,
            candidate_latencies=candidate_latencies,
            max_recommendations=max_recommendations,
        )
        + rank_queue_depth_upgrades(
            model,
            workload,
            candidate_queue_depths=candidate_queue_depths,
            max_recommendations=max_recommendations,
        )
        + rank_bandwidth_upgrades(
            model,
            workload,
            candidate_bandwidths=candidate_bandwidths,
            max_recommendations=max_recommendations,
        )
    )
    deduped: Dict[Tuple[str, str, int, int], UpgradeCandidate] = {}
    for candidate in merged:
        key = (
            candidate.stage_name,
            candidate.knob,
            candidate.baseline_value,
            candidate.recommended_value,
        )
        prev = deduped.get(key)
        if prev is None or (
            candidate.cycle_reduction,
            candidate.speedup,
        ) > (
            prev.cycle_reduction,
            prev.speedup,
        ):
            deduped[key] = candidate
    ranked = sorted(
        deduped.values(),
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name, candidate.knob),
    )
    return tuple(ranked[:max_recommendations])


def _run_stage_sweep(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
    *,
    knob: str,
    values: Sequence[int],
) -> StageSweepReport:
    if not values:
        raise ValueError("sweep values must not be empty")
    unique_values = tuple(dict.fromkeys(int(value) for value in values))
    baseline_behavior = BehaviorSimulator().run(model, workload)
    baseline_cycle = CycleSimulator().run(model, workload)
    baseline_throughput = _aggregate_throughput(workload, baseline_cycle)
    points = []
    for value in unique_values:
        stage = model.stage(stage_name)
        if knob == "capacity":
            updated = _clone_model_with_stage_override(model, stage_name, capacity=value)
            latency = stage.latency
            capacity = value
            initiation_interval = stage.initiation_interval
            queue_depth = stage.queue_depth
            bandwidth_bytes_per_cycle = stage.bandwidth_bytes_per_cycle
        elif knob == "initiation_interval":
            updated = _clone_model_with_stage_override(model, stage_name, initiation_interval=value)
            latency = stage.latency
            capacity = stage.capacity
            initiation_interval = value
            queue_depth = stage.queue_depth
            bandwidth_bytes_per_cycle = stage.bandwidth_bytes_per_cycle
        elif knob == "latency":
            updated = _clone_model_with_stage_override(model, stage_name, latency=value)
            latency = value
            capacity = stage.capacity
            initiation_interval = stage.initiation_interval
            queue_depth = stage.queue_depth
            bandwidth_bytes_per_cycle = stage.bandwidth_bytes_per_cycle
        elif knob == "queue_depth":
            updated = _clone_model_with_stage_override(model, stage_name, queue_depth=value)
            latency = stage.latency
            capacity = stage.capacity
            initiation_interval = stage.initiation_interval
            queue_depth = value
            bandwidth_bytes_per_cycle = stage.bandwidth_bytes_per_cycle
        elif knob == "bandwidth_bytes_per_cycle":
            updated = _clone_model_with_stage_override(model, stage_name, bandwidth_bytes_per_cycle=value)
            latency = stage.latency
            capacity = stage.capacity
            initiation_interval = stage.initiation_interval
            queue_depth = stage.queue_depth
            bandwidth_bytes_per_cycle = value
        else:  # pragma: no cover - internal defensive
            raise ValueError(f"unsupported sweep knob '{knob}'")
        behavior_report = BehaviorSimulator().run(updated, workload)
        cycle_report = CycleSimulator().run(updated, workload)
        cycle_total_cycles = cycle_report.total_cycles
        speedup = baseline_cycle.total_cycles / cycle_total_cycles
        points.append(
            SweepPoint(
                stage_name=stage_name,
                latency=latency,
                capacity=capacity,
                initiation_interval=initiation_interval,
                queue_depth=queue_depth,
                bandwidth_bytes_per_cycle=bandwidth_bytes_per_cycle,
                behavior_makespan_cycles=behavior_report.makespan_cycles,
                cycle_total_cycles=cycle_total_cycles,
                aggregate_throughput_tokens_per_cycle=_aggregate_throughput(workload, cycle_report),
                speedup_vs_baseline=speedup,
            )
        )
    return StageSweepReport(
        stage_name=stage_name,
        knob=knob,
        baseline_cycles=baseline_cycle.total_cycles,
        baseline_throughput_tokens_per_cycle=baseline_throughput,
        points=tuple(points),
    )


def _aggregate_throughput(workload: Workload, cycle_report: CycleReport) -> float:
    total_tokens = sum(flow.tokens for flow in workload.flows)
    if cycle_report.total_cycles <= 0:
        return 0.0
    return total_tokens / cycle_report.total_cycles


def _clone_model_with_stage_override(
    model: ArchitectureModel,
    stage_name: str,
    **overrides,
) -> ArchitectureModel:
    stages = []
    for name, stage in model.stages.items():
        if name != stage_name:
            stages.append(stage)
            continue
        stage_dict = {
            "name": stage.name,
            "kind": stage.kind,
            "latency": stage.latency,
            "initiation_interval": stage.initiation_interval,
            "capacity": stage.capacity,
            "queue_depth": stage.queue_depth,
            "bandwidth_bytes_per_cycle": stage.bandwidth_bytes_per_cycle,
            "metadata": dict(stage.metadata),
        }
        stage_dict.update(overrides)
        stages.append(StageSpec(**stage_dict))
    return ArchitectureModel(stages)
