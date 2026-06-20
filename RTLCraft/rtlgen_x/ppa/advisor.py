"""First-pass PPA analysis and recommendation helpers for rtlgen_x."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from rtlgen_x.archsim import (
    ArchitectureModel,
    BehaviorReport,
    BehaviorSimulator,
    CycleReport,
    CycleSimulator,
    UpgradeCandidate,
    Workload,
    run_stage_bandwidth_sweep,
    run_stage_capacity_sweep,
    run_stage_initiation_interval_sweep,
    run_stage_latency_sweep,
    run_stage_queue_depth_sweep,
)
from rtlgen_x.dsl import LoweredLegacyModule, lower_legacy_module_to_sim
from rtlgen_x.ppa.reports import ImplementationReportBundle
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    MaskExpr,
    MemoryReadExpr,
    MuxExpr,
    SignalRef,
    SimModule,
    UnaryExpr,
)


@dataclass(frozen=True)
class PpaGoals:
    """User-facing optimization priorities and optional thresholds."""

    priority: str = "balanced"
    max_logic_depth: Optional[int] = None
    max_state_bits: Optional[int] = None
    max_memory_bits: Optional[int] = None
    min_throughput_tokens_per_cycle: Optional[float] = None
    max_stall_ratio: Optional[float] = None

    def __post_init__(self) -> None:
        if self.priority not in {"balanced", "timing_first", "area_first", "power_first"}:
            raise ValueError(f"unsupported PPA priority '{self.priority}'")
        if self.min_throughput_tokens_per_cycle is not None and self.min_throughput_tokens_per_cycle <= 0:
            raise ValueError("min_throughput_tokens_per_cycle must be positive")
        if self.max_stall_ratio is not None and self.max_stall_ratio < 0:
            raise ValueError("max_stall_ratio must be non-negative")


@dataclass(frozen=True)
class ModulePpaStats:
    module_name: str
    input_bits: int
    output_bits: int
    state_bits: int
    memory_bits: int
    state_count: int
    memory_count: int
    comb_assignments: int
    seq_assignments: int
    memory_writes: int
    arithmetic_ops: int
    compare_ops: int
    mux_ops: int
    max_expr_depth: int


@dataclass(frozen=True)
class FlowPpaStats:
    name: str
    throughput_tokens_per_cycle: float
    total_cycles: float
    stall_ratio: float
    bottleneck_stage: Optional[str]


@dataclass(frozen=True)
class StagePpaStats:
    name: str
    kind: str
    utilization: float
    queue_pressure: float
    bandwidth_bytes_per_cycle: int


@dataclass(frozen=True)
class ArchitecturePpaStats:
    total_cycles: int
    makespan_cycles: float
    flow_stats: Mapping[str, FlowPpaStats]
    stage_stats: Mapping[str, StagePpaStats]


@dataclass(frozen=True)
class PpaRecommendation:
    category: str
    severity: str
    title: str
    rationale: str
    evidence: Mapping[str, object] = field(default_factory=dict)
    suggestions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PpaTransformCandidate:
    name: str
    category: str
    target: str
    expected_benefit: str
    rationale: str
    suggested_knob: Optional[str] = None
    suggested_value: Optional[object] = None


@dataclass(frozen=True)
class PpaReport:
    goals: PpaGoals
    module_stats: Optional[ModulePpaStats]
    architecture_stats: Optional[ArchitecturePpaStats]
    recommendations: Tuple[PpaRecommendation, ...]
    calibrated_module_estimate: Optional["CalibratedModulePpaEstimate"] = None
    calibrated_architecture_estimate: Optional["CalibratedArchitecturePpaEstimate"] = None
    transform_candidates: Tuple[PpaTransformCandidate, ...] = ()


def analyze_module_ppa(module: Any) -> ModulePpaStats:
    """Compute lightweight structural PPA signals from one executable module."""

    module = _normalize_executable_module(module)
    signal_map = module.signal_map()
    input_bits = sum(signal.width for signal in module.signals if signal.kind == "input")
    output_bits = sum(signal_map[name].width for name in module.outputs)
    state_bits = sum(signal.width for signal in module.signals if signal.kind == "state")
    memory_bits = sum(memory.width * memory.depth for memory in module.memories)
    comb_assignments = sum(1 for assignment in module.assignments if assignment.phase == "comb")
    seq_assignments = sum(1 for assignment in module.assignments if assignment.phase == "seq")

    arithmetic_ops = 0
    compare_ops = 0
    mux_ops = 0
    max_expr_depth = 0
    for assignment in module.assignments:
        metrics = _expr_metrics(assignment.expr)
        arithmetic_ops += metrics["arithmetic_ops"]
        compare_ops += metrics["compare_ops"]
        mux_ops += metrics["mux_ops"]
        max_expr_depth = max(max_expr_depth, int(metrics["depth"]))
    for write in module.memory_writes:
        for expr in (write.addr, write.value, write.enable):
            metrics = _expr_metrics(expr)
            arithmetic_ops += metrics["arithmetic_ops"]
            compare_ops += metrics["compare_ops"]
            mux_ops += metrics["mux_ops"]
            max_expr_depth = max(max_expr_depth, int(metrics["depth"]))

    return ModulePpaStats(
        module_name=module.name,
        input_bits=input_bits,
        output_bits=output_bits,
        state_bits=state_bits,
        memory_bits=memory_bits,
        state_count=sum(1 for signal in module.signals if signal.kind == "state"),
        memory_count=len(module.memories),
        comb_assignments=comb_assignments,
        seq_assignments=seq_assignments,
        memory_writes=len(module.memory_writes),
        arithmetic_ops=arithmetic_ops,
        compare_ops=compare_ops,
        mux_ops=mux_ops,
        max_expr_depth=max_expr_depth,
    )


def analyze_architecture_ppa(
    model: ArchitectureModel,
    workload: Workload,
    *,
    behavior_report: Optional[BehaviorReport] = None,
    cycle_report: Optional[CycleReport] = None,
) -> ArchitecturePpaStats:
    """Derive PPA-relevant signals from the architecture-level simulators."""

    behavior_report = behavior_report or BehaviorSimulator().run(model, workload)
    cycle_report = cycle_report or CycleSimulator().run(model, workload)
    flow_stats: Dict[str, FlowPpaStats] = {}
    for flow in workload.flows:
        cycle_metrics = cycle_report.flow_metrics[flow.name]
        behavior_metrics = behavior_report.flow_metrics[flow.name]
        issued = max(cycle_metrics.issued_tokens, 1)
        stall_ratio = cycle_metrics.stalled_cycles / issued
        flow_stats[flow.name] = FlowPpaStats(
            name=flow.name,
            throughput_tokens_per_cycle=behavior_metrics.throughput_tokens_per_cycle,
            total_cycles=behavior_metrics.total_cycles,
            stall_ratio=stall_ratio,
            bottleneck_stage=behavior_metrics.bottleneck_stage,
        )

    stage_stats: Dict[str, StagePpaStats] = {}
    for stage_name, stage in model.stages.items():
        cycle_metrics = cycle_report.stage_metrics[stage_name]
        queue_capacity = max(model.queue_capacity(stage_name), 1)
        utilization = cycle_metrics.busy_token_cycles / max(cycle_report.total_cycles * stage.capacity, 1)
        queue_pressure = cycle_metrics.max_ready_depth / queue_capacity
        stage_stats[stage_name] = StagePpaStats(
            name=stage_name,
            kind=stage.kind,
            utilization=utilization,
            queue_pressure=queue_pressure,
            bandwidth_bytes_per_cycle=stage.bandwidth_bytes_per_cycle,
        )

    return ArchitecturePpaStats(
        total_cycles=cycle_report.total_cycles,
        makespan_cycles=behavior_report.makespan_cycles,
        flow_stats=flow_stats,
        stage_stats=stage_stats,
    )


def advise_ppa(
    *,
    module: Optional[Any] = None,
    model: Optional[ArchitectureModel] = None,
    workload: Optional[Workload] = None,
    behavior_report: Optional[BehaviorReport] = None,
    cycle_report: Optional[CycleReport] = None,
    goals: Optional[PpaGoals] = None,
    include_sweep_evidence: bool = True,
    implementation_reports: Optional[ImplementationReportBundle] = None,
    module_calibration: Optional["ModulePpaCalibrationModel"] = None,
    architecture_calibration: Optional["ArchitecturePpaCalibrationModel"] = None,
) -> PpaReport:
    """Return a lightweight set of PPA recommendations from structural/runtime evidence."""

    goals = goals or PpaGoals()
    module_stats = analyze_module_ppa(module) if module is not None else None
    arch_stats = None
    if model is not None and workload is not None:
        arch_stats = analyze_architecture_ppa(
            model,
            workload,
            behavior_report=behavior_report,
            cycle_report=cycle_report,
        )
    calibrated_module_estimate = None
    calibrated_architecture_estimate = None
    if module_stats is not None and module_calibration is not None:
        from rtlgen_x.ppa.calibration import estimate_calibrated_module_ppa

        calibrated_module_estimate = estimate_calibrated_module_ppa(module_stats, module_calibration)
    if arch_stats is not None and architecture_calibration is not None:
        from rtlgen_x.ppa.calibration import estimate_calibrated_architecture_ppa

        calibrated_architecture_estimate = estimate_calibrated_architecture_ppa(
            stats=arch_stats,
            calibration=architecture_calibration,
        )

    recommendations: List[PpaRecommendation] = []
    if module_stats is not None:
        recommendations.extend(_module_recommendations(module_stats, goals))
    if implementation_reports is not None:
        recommendations.extend(_implementation_report_recommendations(implementation_reports, goals))
    if calibrated_module_estimate is not None:
        recommendations.extend(_calibrated_module_recommendations(calibrated_module_estimate))
    if arch_stats is not None and model is not None:
        recommendations.extend(
            _architecture_recommendations(
                model,
                workload,
                arch_stats,
                goals,
                include_sweep_evidence=include_sweep_evidence,
            )
        )
    if calibrated_architecture_estimate is not None:
        recommendations.extend(_calibrated_architecture_recommendations(calibrated_architecture_estimate))
    recommendations.sort(key=_recommendation_rank)
    transform_candidates = tuple(_derive_transform_candidates(recommendations))
    return PpaReport(
        goals=goals,
        module_stats=module_stats,
        architecture_stats=arch_stats,
        recommendations=tuple(recommendations),
        calibrated_module_estimate=calibrated_module_estimate,
        calibrated_architecture_estimate=calibrated_architecture_estimate,
        transform_candidates=transform_candidates,
    )


def _expr_metrics(expr) -> Dict[str, int]:
    if isinstance(expr, (ConstExpr, SignalRef, MemoryReadExpr)):
        return {"depth": 1, "arithmetic_ops": 0, "compare_ops": 0, "mux_ops": 0}
    if isinstance(expr, MaskExpr):
        child = _expr_metrics(expr.value)
        return {"depth": child["depth"] + 1, **{key: child[key] for key in ("arithmetic_ops", "compare_ops", "mux_ops")}}
    if isinstance(expr, UnaryExpr):
        child = _expr_metrics(expr.value)
        return {"depth": child["depth"] + 1, **{key: child[key] for key in ("arithmetic_ops", "compare_ops", "mux_ops")}}
    if isinstance(expr, BinaryExpr):
        lhs = _expr_metrics(expr.lhs)
        rhs = _expr_metrics(expr.rhs)
        arithmetic_ops = lhs["arithmetic_ops"] + rhs["arithmetic_ops"]
        compare_ops = lhs["compare_ops"] + rhs["compare_ops"]
        if expr.op in {"+", "-", "*", "<<", ">>", ">>>", "&", "|", "^"}:
            arithmetic_ops += 1
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            compare_ops += 1
        return {
            "depth": max(lhs["depth"], rhs["depth"]) + 1,
            "arithmetic_ops": arithmetic_ops,
            "compare_ops": compare_ops,
            "mux_ops": lhs["mux_ops"] + rhs["mux_ops"],
        }
    if isinstance(expr, MuxExpr):
        cond = _expr_metrics(expr.cond)
        when_true = _expr_metrics(expr.when_true)
        when_false = _expr_metrics(expr.when_false)
        return {
            "depth": max(cond["depth"], when_true["depth"], when_false["depth"]) + 1,
            "arithmetic_ops": cond["arithmetic_ops"] + when_true["arithmetic_ops"] + when_false["arithmetic_ops"],
            "compare_ops": cond["compare_ops"] + when_true["compare_ops"] + when_false["compare_ops"],
            "mux_ops": cond["mux_ops"] + when_true["mux_ops"] + when_false["mux_ops"] + 1,
        }
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _module_recommendations(stats: ModulePpaStats, goals: PpaGoals) -> List[PpaRecommendation]:
    recs: List[PpaRecommendation] = []
    depth_limit = goals.max_logic_depth if goals.max_logic_depth is not None else 6
    if stats.max_expr_depth > depth_limit:
        recs.append(
            PpaRecommendation(
                category="timing",
                severity="high",
                title="Pipeline or rebalance deep combinational logic",
                rationale=(
                    f"Module '{stats.module_name}' reaches expression depth {stats.max_expr_depth}, "
                    f"above the target depth {depth_limit}."
                ),
                evidence={"module": stats.module_name, "max_expr_depth": stats.max_expr_depth, "target_depth": depth_limit},
                suggestions=(
                    "Insert a register boundary around the deepest arithmetic chain.",
                    "Split wide mux/arithmetic trees so the critical path spans fewer operators.",
                ),
            )
        )
    if stats.memory_bits > (goals.max_memory_bits if goals.max_memory_bits is not None else 16_384):
        recs.append(
            PpaRecommendation(
                category="area_power",
                severity="medium",
                title="Bank or isolate large memories",
                rationale=(
                    f"Module '{stats.module_name}' carries {stats.memory_bits} memory bits across "
                    f"{stats.memory_count} storage objects."
                ),
                evidence={"memory_bits": stats.memory_bits, "memory_count": stats.memory_count},
                suggestions=(
                    "Consider banking the storage or mapping it onto dedicated SRAM macros.",
                    "Gate read/write enables so inactive banks do not toggle every cycle.",
                ),
            )
        )
    state_limit = goals.max_state_bits if goals.max_state_bits is not None else 256
    if stats.state_bits > state_limit:
        recs.append(
            PpaRecommendation(
                category="power",
                severity="medium",
                title="Reduce or gate large sequential state",
                rationale=(
                    f"Module '{stats.module_name}' has {stats.state_bits} explicit state bits, "
                    f"above the working threshold {state_limit}."
                ),
                evidence={"state_bits": stats.state_bits, "state_count": stats.state_count},
                suggestions=(
                    "Clock-gate inactive state groups or split cold state into a separate block.",
                    "Audit whether infrequently used registers can move to memory-backed storage.",
                ),
            )
        )
    if stats.arithmetic_ops >= 8 and stats.comb_assignments >= 4:
        mode_hint = {
            "timing_first": "swap hot operators for faster implementations and add pipeline boundaries",
            "area_first": "share arithmetic units across mutually exclusive paths",
            "power_first": "serialize low-duty arithmetic and gate inactive operands",
        }.get(goals.priority, "rebalance arithmetic and share low-duty operators")
        recs.append(
            PpaRecommendation(
                category="tradeoff",
                severity="medium",
                title="Revisit arithmetic structure",
                rationale=(
                    f"Module '{stats.module_name}' uses {stats.arithmetic_ops} arithmetic/bitwise ops "
                    f"across {stats.comb_assignments} combinational assignments."
                ),
                evidence={"arithmetic_ops": stats.arithmetic_ops, "comb_assignments": stats.comb_assignments},
                suggestions=(mode_hint,),
            )
        )
    return recs


def _implementation_report_recommendations(
    reports: ImplementationReportBundle,
    goals: PpaGoals,
) -> List[PpaRecommendation]:
    recs: List[PpaRecommendation] = []
    if reports.timing.wns_ns is not None and reports.timing.wns_ns < 0:
        recs.append(
            PpaRecommendation(
                category="timing",
                severity="high",
                title="Close negative timing slack",
                rationale=(
                    f"Imported implementation evidence reports WNS {reports.timing.wns_ns:.3f} ns, "
                    "so the current design misses timing."
                ),
                evidence={
                    "wns_ns": reports.timing.wns_ns,
                    "tns_ns": reports.timing.tns_ns,
                    "sources": reports.sources,
                },
                suggestions=(
                    "Pipeline the longest arithmetic/control path or lower fanout on timing-critical nets.",
                    "Use the architecture and sweep-backed recommendations to identify the most leverageful bottleneck first.",
                ),
            )
        )
    if reports.power.total_mw is not None and reports.power.total_mw > 1.0:
        recs.append(
            PpaRecommendation(
                category="power",
                severity="medium",
                title="Reduce implementation power hotspots",
                rationale=(
                    f"Imported implementation evidence reports total power {reports.power.total_mw:.3f} mW."
                ),
                evidence={
                    "dynamic_mw": reports.power.dynamic_mw,
                    "leakage_mw": reports.power.leakage_mw,
                    "total_mw": reports.power.total_mw,
                    "sources": reports.sources,
                },
                suggestions=(
                    "Clock-gate idle state and reduce standing queue occupancy where possible.",
                    "Revisit memory banking and wide always-active datapaths if dynamic power dominates.",
                ),
            )
        )
    if reports.area.total_area is not None and reports.area.total_area > 20_000:
        recs.append(
            PpaRecommendation(
                category="area_power",
                severity="medium",
                title="Revisit large implementation area",
                rationale=(
                    f"Imported implementation evidence reports total area {reports.area.total_area:.1f}."
                ),
                evidence={
                    "total_area": reports.area.total_area,
                    "combinational_area": reports.area.combinational_area,
                    "sequential_area": reports.area.sequential_area,
                    "sources": reports.sources,
                },
                suggestions=(
                    "Share low-duty datapaths or serialize infrequently used arithmetic.",
                    "Move large storage-heavy structures toward banked memories or denser macros.",
                ),
            )
        )
    return recs


def _calibrated_module_recommendations(estimate: "CalibratedModulePpaEstimate") -> List[PpaRecommendation]:
    evidence: Dict[str, object] = {
        "module": estimate.module_name,
        "critical_path_ns": estimate.critical_path_ns,
        "fmax_mhz": estimate.fmax_mhz,
        "total_area": estimate.total_area,
        "total_power_mw": estimate.total_power_mw,
        "timing_score": estimate.timing_score,
        "area_score": estimate.area_score,
        "power_score": estimate.power_score,
        "calibration_sample_count": estimate.calibration_sample_count,
    }
    return [
        PpaRecommendation(
            category="tradeoff",
            severity="low",
            title="Use calibration-backed module PPA estimate",
            rationale=(
                f"Module '{estimate.module_name}' now carries timing/area/power estimates scaled from "
                f"{estimate.calibration_sample_count} implementation calibration sample(s)."
            ),
            evidence=evidence,
            suggestions=(
                "Use the calibrated critical-path, area, and power estimates as the default ranking signal before new implementation reports arrive.",
                "Refresh the calibration set when synthesis or signoff data moves materially.",
            ),
        )
    ]


def _calibrated_architecture_recommendations(
    estimate: "CalibratedArchitecturePpaEstimate",
) -> List[PpaRecommendation]:
    flow_estimates = tuple(estimate.flow_estimates.values())
    evidence: Dict[str, object] = {
        "total_cycles": estimate.total_cycles,
        "makespan_cycles": estimate.makespan_cycles,
        "cycle_scale": estimate.cycle_scale,
        "makespan_scale": estimate.makespan_scale,
        "throughput_scale": estimate.throughput_scale,
        "stall_scale": estimate.stall_scale,
        "calibration_sample_count": estimate.calibration_sample_count,
    }
    if flow_estimates:
        evidence["min_flow_throughput_tokens_per_cycle"] = min(
            flow.throughput_tokens_per_cycle for flow in flow_estimates
        )
        evidence["max_flow_stall_ratio"] = max(flow.stall_ratio for flow in flow_estimates)
    return [
        PpaRecommendation(
            category="tradeoff",
            severity="low",
            title="Use calibration-backed architecture estimate",
            rationale=(
                "Architecture throughput, cycle, and stall projections are now scaled by measured feedback "
                f"from {estimate.calibration_sample_count} calibration sample(s)."
            ),
            evidence=evidence,
            suggestions=(
                "Use the calibrated architecture estimate when comparing stage-level what-if sweeps against measured silicon or RTL behavior.",
                "Feed updated measurements back into calibration whenever the bottleneck stage or workload mix changes.",
            ),
        )
    ]


def _architecture_recommendations(
    model: ArchitectureModel,
    workload: Optional[Workload],
    stats: ArchitecturePpaStats,
    goals: PpaGoals,
    *,
    include_sweep_evidence: bool,
) -> List[PpaRecommendation]:
    recs: List[PpaRecommendation] = []
    min_tp = goals.min_throughput_tokens_per_cycle if goals.min_throughput_tokens_per_cycle is not None else 0.5
    max_stall_ratio = goals.max_stall_ratio if goals.max_stall_ratio is not None else 0.25
    sweep_cache: Dict[str, Tuple[UpgradeCandidate, ...]] = {}
    for flow_name, flow in stats.flow_stats.items():
        if flow.throughput_tokens_per_cycle < min_tp and flow.bottleneck_stage is not None:
            bottleneck = model.stage(flow.bottleneck_stage)
            upgrade = _best_stage_upgrade(
                model,
                workload,
                flow.bottleneck_stage,
                sweep_cache=sweep_cache,
                include_sweep_evidence=include_sweep_evidence,
            )
            evidence = {
                "flow": flow_name,
                "throughput_tokens_per_cycle": flow.throughput_tokens_per_cycle,
                "bottleneck_stage": flow.bottleneck_stage,
                "stage_kind": bottleneck.kind,
            }
            suggestions = list(_throughput_suggestions(bottleneck))
            if upgrade is not None:
                evidence.update(_upgrade_evidence(upgrade))
                suggestions.insert(0, _upgrade_suggestion(upgrade))
            recs.append(
                PpaRecommendation(
                    category="throughput",
                    severity="high",
                    title=f"Relieve bottleneck stage '{flow.bottleneck_stage}'",
                    rationale=(
                        f"Flow '{flow_name}' only reaches {flow.throughput_tokens_per_cycle:.3f} tokens/cycle "
                        f"and bottlenecks on stage '{flow.bottleneck_stage}'."
                    ),
                    evidence=evidence,
                    suggestions=tuple(suggestions),
                )
            )
        if flow.stall_ratio > max_stall_ratio and flow.bottleneck_stage is not None:
            upgrade = _best_stage_upgrade(
                model,
                workload,
                flow.bottleneck_stage,
                preferred_knobs=("queue_depth", "capacity", "initiation_interval"),
                sweep_cache=sweep_cache,
                include_sweep_evidence=include_sweep_evidence,
            )
            evidence = {"flow": flow_name, "stall_ratio": flow.stall_ratio}
            suggestions = [
                f"Increase buffering in front of '{flow.bottleneck_stage}' or widen its capacity.",
                "Shift independent work earlier so the bottleneck stage stays better utilized.",
            ]
            if upgrade is not None:
                evidence.update(_upgrade_evidence(upgrade))
                suggestions.insert(0, _upgrade_suggestion(upgrade))
            recs.append(
                PpaRecommendation(
                    category="latency",
                    severity="medium",
                    title=f"Trim queueing stalls for flow '{flow_name}'",
                    rationale=(
                        f"Flow '{flow_name}' spends {flow.stall_ratio:.2%} of issued-token opportunities stalled."
                    ),
                    evidence=evidence,
                    suggestions=tuple(suggestions),
                )
            )
    for stage_name, stage in stats.stage_stats.items():
        if stage.utilization > 0.85:
            upgrade = _best_stage_upgrade(
                model,
                workload,
                stage_name,
                sweep_cache=sweep_cache,
                include_sweep_evidence=include_sweep_evidence,
            )
            evidence = {"stage": stage_name, "utilization": stage.utilization, "kind": stage.kind}
            suggestions = list(_throughput_suggestions(model.stage(stage_name)))
            if upgrade is not None:
                evidence.update(_upgrade_evidence(upgrade))
                suggestions.insert(0, _upgrade_suggestion(upgrade))
            recs.append(
                PpaRecommendation(
                    category="throughput",
                    severity="medium",
                    title=f"High utilization at stage '{stage_name}'",
                    rationale=(
                        f"Stage '{stage_name}' runs at {stage.utilization:.1%} effective utilization."
                    ),
                    evidence=evidence,
                    suggestions=tuple(suggestions),
                )
            )
        if stage.queue_pressure > 0.8:
            upgrade = _best_stage_upgrade(
                model,
                workload,
                stage_name,
                preferred_knobs=("queue_depth", "capacity"),
                sweep_cache=sweep_cache,
                include_sweep_evidence=include_sweep_evidence,
            )
            evidence = {"stage": stage_name, "queue_pressure": stage.queue_pressure}
            suggestions = [
                "Increase queue depth if burst absorption matters more than area.",
                "Balance upstream issue rate to reduce standing occupancy.",
            ]
            if upgrade is not None:
                evidence.update(_upgrade_evidence(upgrade))
                suggestions.insert(0, _upgrade_suggestion(upgrade))
            recs.append(
                PpaRecommendation(
                    category="latency",
                    severity="medium",
                    title=f"Queue pressure is high at '{stage_name}'",
                    rationale=(
                        f"Stage '{stage_name}' reaches {stage.queue_pressure:.1%} of its configured queue capacity."
                    ),
                    evidence=evidence,
                    suggestions=tuple(suggestions),
                )
            )
    return recs


def _best_stage_upgrade(
    model: ArchitectureModel,
    workload: Optional[Workload],
    stage_name: str,
    *,
    preferred_knobs: Optional[Sequence[str]] = None,
    sweep_cache: Dict[str, Tuple[UpgradeCandidate, ...]],
    include_sweep_evidence: bool,
) -> Optional[UpgradeCandidate]:
    if not include_sweep_evidence or workload is None:
        return None
    candidates = sweep_cache.get(stage_name)
    if candidates is None:
        candidates = _stage_upgrade_candidates(model, workload, stage_name)
        sweep_cache[stage_name] = candidates
    if preferred_knobs is not None:
        preferred = set(preferred_knobs)
        candidates = tuple(candidate for candidate in candidates if candidate.knob in preferred)
    return candidates[0] if candidates else None


def _stage_upgrade_candidates(
    model: ArchitectureModel,
    workload: Workload,
    stage_name: str,
) -> Tuple[UpgradeCandidate, ...]:
    stage = model.stage(stage_name)
    candidates: List[UpgradeCandidate] = []

    capacity_values = _candidate_capacity_values(stage.capacity)
    if len(capacity_values) > 1:
        report = run_stage_capacity_sweep(model, workload, stage_name, capacity_values)
        candidate = _candidate_from_report(
            report,
            stage_name=stage_name,
            knob="capacity",
            baseline_value=stage.capacity,
            recommended_value=report.best_point.capacity,
            rationale=f"Widen stage '{stage_name}' from capacity {stage.capacity} to {report.best_point.capacity}.",
        )
        if candidate is not None:
            candidates.append(candidate)

    ii_values = _candidate_reduced_values(stage.initiation_interval)
    if len(ii_values) > 1:
        report = run_stage_initiation_interval_sweep(model, workload, stage_name, ii_values)
        candidate = _candidate_from_report(
            report,
            stage_name=stage_name,
            knob="initiation_interval",
            baseline_value=stage.initiation_interval,
            recommended_value=report.best_point.initiation_interval,
            rationale=(
                f"Reduce stage '{stage_name}' initiation interval from {stage.initiation_interval} "
                f"to {report.best_point.initiation_interval}."
            ),
        )
        if candidate is not None:
            candidates.append(candidate)

    latency_values = _candidate_reduced_values(stage.latency)
    if len(latency_values) > 1:
        report = run_stage_latency_sweep(model, workload, stage_name, latency_values)
        candidate = _candidate_from_report(
            report,
            stage_name=stage_name,
            knob="latency",
            baseline_value=stage.latency,
            recommended_value=report.best_point.latency,
            rationale=f"Reduce stage '{stage_name}' latency from {stage.latency} to {report.best_point.latency}.",
        )
        if candidate is not None:
            candidates.append(candidate)

    queue_values = _candidate_queue_depth_values(stage.queue_depth, stage.capacity)
    if len(queue_values) > 1:
        report = run_stage_queue_depth_sweep(model, workload, stage_name, queue_values)
        candidate = _candidate_from_report(
            report,
            stage_name=stage_name,
            knob="queue_depth",
            baseline_value=stage.queue_depth,
            recommended_value=report.best_point.queue_depth,
            rationale=(
                f"Increase queue depth at '{stage_name}' from {stage.queue_depth} "
                f"to {report.best_point.queue_depth}."
            ),
        )
        if candidate is not None:
            candidates.append(candidate)

    bandwidth_values = _candidate_bandwidth_values(stage.bandwidth_bytes_per_cycle)
    if len(bandwidth_values) > 1:
        report = run_stage_bandwidth_sweep(model, workload, stage_name, bandwidth_values)
        candidate = _candidate_from_report(
            report,
            stage_name=stage_name,
            knob="bandwidth_bytes_per_cycle",
            baseline_value=stage.bandwidth_bytes_per_cycle,
            recommended_value=report.best_point.bandwidth_bytes_per_cycle,
            rationale=(
                f"Increase bandwidth at '{stage_name}' from {stage.bandwidth_bytes_per_cycle} "
                f"to {report.best_point.bandwidth_bytes_per_cycle} bytes/cycle."
            ),
        )
        if candidate is not None:
            candidates.append(candidate)

    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.cycle_reduction, -candidate.speedup, candidate.stage_name, candidate.knob),
    )
    return tuple(ranked)


def _candidate_from_report(
    report,
    *,
    stage_name: str,
    knob: str,
    baseline_value: int,
    recommended_value: int,
    rationale: str,
) -> Optional[UpgradeCandidate]:
    best = report.best_point
    if best.cycle_total_cycles >= report.baseline_cycles or recommended_value == baseline_value:
        return None
    return UpgradeCandidate(
        stage_name=stage_name,
        knob=knob,
        baseline_value=baseline_value,
        recommended_value=recommended_value,
        baseline_cycles=report.baseline_cycles,
        improved_cycles=best.cycle_total_cycles,
        cycle_reduction=report.baseline_cycles - best.cycle_total_cycles,
        speedup=best.speedup_vs_baseline,
        rationale=(
            f"{rationale} Expected total cycles improve from {report.baseline_cycles} "
            f"to {best.cycle_total_cycles}."
        ),
    )


def _candidate_capacity_values(baseline: int) -> Tuple[int, ...]:
    return tuple(dict.fromkeys((baseline, baseline + 1, baseline * 2, baseline * 4)))


def _candidate_reduced_values(baseline: int) -> Tuple[int, ...]:
    values = [baseline]
    for value in (baseline - 1, baseline // 2, 1):
        if value >= 1:
            values.append(value)
    return tuple(dict.fromkeys(values))


def _candidate_queue_depth_values(baseline: int, capacity: int) -> Tuple[int, ...]:
    values = [baseline]
    for value in (max(capacity, baseline + 1), max(capacity * 2, baseline + 2), max(capacity * 4, baseline + 4)):
        if value > baseline:
            values.append(value)
    return tuple(dict.fromkeys(values))


def _candidate_bandwidth_values(baseline: int) -> Tuple[int, ...]:
    if baseline <= 0:
        return (baseline,)
    return tuple(dict.fromkeys((baseline, baseline * 2, baseline * 4)))


def _upgrade_evidence(candidate: UpgradeCandidate) -> Mapping[str, object]:
    return {
        "sweep_knob": candidate.knob,
        "sweep_baseline_value": candidate.baseline_value,
        "sweep_recommended_value": candidate.recommended_value,
        "sweep_baseline_cycles": candidate.baseline_cycles,
        "sweep_improved_cycles": candidate.improved_cycles,
        "sweep_cycle_reduction": candidate.cycle_reduction,
        "sweep_speedup": candidate.speedup,
    }


def _upgrade_suggestion(candidate: UpgradeCandidate) -> str:
    if candidate.knob == "capacity":
        return (
            f"Local sweep favors increasing capacity at '{candidate.stage_name}' "
            f"from {candidate.baseline_value} to {candidate.recommended_value}."
        )
    if candidate.knob == "initiation_interval":
        return (
            f"Local sweep favors reducing initiation interval at '{candidate.stage_name}' "
            f"from {candidate.baseline_value} to {candidate.recommended_value}."
        )
    if candidate.knob == "latency":
        return (
            f"Local sweep favors reducing latency at '{candidate.stage_name}' "
            f"from {candidate.baseline_value} to {candidate.recommended_value}."
        )
    if candidate.knob == "queue_depth":
        return (
            f"Local sweep favors increasing queue depth at '{candidate.stage_name}' "
            f"from {candidate.baseline_value} to {candidate.recommended_value}."
        )
    if candidate.knob == "bandwidth_bytes_per_cycle":
        return (
            f"Local sweep favors increasing bandwidth at '{candidate.stage_name}' "
            f"from {candidate.baseline_value} to {candidate.recommended_value} bytes/cycle."
        )
    return candidate.rationale


def _throughput_suggestions(stage) -> Tuple[str, ...]:
    if stage.kind == "memory":
        return (
            "Increase banking or outstanding accesses for the memory stage.",
            "Prefetch or reorder traffic so the memory pipeline stays full with fewer bubbles.",
        )
    if stage.kind == "interconnect":
        return (
            "Widen the interconnect or split high-contention traffic classes.",
            "Add buffering around arbitration points to smooth bursts.",
        )
    if stage.kind == "compute":
        return (
            "Increase compute lane count or shorten initiation interval with additional pipelining.",
            "Move low-duty operations onto a shared side path so the hot compute lane stays lean.",
        )
    return (
        "Increase stage capacity or shorten initiation interval.",
        "Rebalance adjacent stages so this resource sees fewer bursts.",
    )


def _recommendation_rank(rec: PpaRecommendation) -> Tuple[int, str, str]:
    severity_order = {"high": 0, "medium": 1, "low": 2}
    category_order = {
        "timing": 0,
        "throughput": 1,
        "latency": 2,
        "area_power": 3,
        "power": 4,
        "tradeoff": 5,
    }
    return (
        severity_order.get(rec.severity, 99),
        category_order.get(rec.category, 99),
        rec.title,
    )


def _derive_transform_candidates(
    recommendations: Sequence[PpaRecommendation],
) -> Iterable[PpaTransformCandidate]:
    for rec in recommendations:
        evidence = dict(rec.evidence)
        knob = evidence.get("sweep_knob")
        value = evidence.get("sweep_recommended_value")
        target = str(evidence.get("bottleneck_stage") or evidence.get("stage") or evidence.get("flow") or "design")
        if knob is not None and value is not None:
            yield PpaTransformCandidate(
                name=rec.title,
                category=rec.category,
                target=target,
                expected_benefit=f"Improve cycles by {evidence.get('sweep_cycle_reduction', 'unknown')} or speedup {evidence.get('sweep_speedup', 'unknown')}",
                rationale=rec.rationale,
                suggested_knob=str(knob),
                suggested_value=value,
            )
            continue
        if rec.category == "timing":
            yield PpaTransformCandidate(
                name=rec.title,
                category=rec.category,
                target=target,
                expected_benefit="Improve timing slack / reduce critical path depth",
                rationale=rec.rationale,
            )
        elif rec.category in {"power", "area_power"}:
            yield PpaTransformCandidate(
                name=rec.title,
                category=rec.category,
                target=target,
                expected_benefit="Reduce power or implementation area",
                rationale=rec.rationale,
            )


def _normalize_executable_module(module: Any) -> SimModule:
    if isinstance(module, SimModule):
        return module
    if isinstance(module, LoweredLegacyModule):
        return module.module
    if hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks"):
        return lower_legacy_module_to_sim(module).module
    raise TypeError(f"unsupported executable module type: {type(module)!r}")
