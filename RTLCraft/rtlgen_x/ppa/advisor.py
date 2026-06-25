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
from rtlgen_x.dsl import LoweredDslModule, lower_dsl_module_to_sim
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
    multiplier_ops: int
    adder_ops: int
    shift_ops: int
    max_expr_depth: int
    max_memory_width: int = 0
    max_memory_depth: int = 0
    wide_memory_count: int = 0
    small_memory_count: int = 0
    largest_memory_name: Optional[str] = None
    largest_memory_bits: int = 0
    largest_memory_width: int = 0
    largest_memory_depth: int = 0
    largest_memory_source_file: Optional[str] = None
    largest_memory_source_line: Optional[int] = None
    largest_state_name: Optional[str] = None
    largest_state_bits: int = 0
    largest_state_source_file: Optional[str] = None
    largest_state_source_line: Optional[int] = None
    area_state_score: float = 0.0
    area_memory_score: float = 0.0
    area_io_score: float = 0.0
    area_arithmetic_score: float = 0.0
    area_compare_score: float = 0.0
    area_mux_score: float = 0.0
    area_memory_write_score: float = 0.0
    area_comb_assignment_score: float = 0.0
    area_seq_assignment_score: float = 0.0
    estimated_area_score: float = 0.0
    power_state_score: float = 0.0
    power_memory_score: float = 0.0
    power_arithmetic_score: float = 0.0
    power_compare_score: float = 0.0
    power_mux_score: float = 0.0
    power_memory_write_score: float = 0.0
    estimated_power_score: float = 0.0
    dominant_area_bucket: Optional[str] = None
    dominant_power_bucket: Optional[str] = None
    critical_assignment_target: Optional[str] = None
    critical_assignment_phase: Optional[str] = None
    critical_assignment_source_file: Optional[str] = None
    critical_assignment_source_line: Optional[int] = None
    critical_expr_kind: Optional[str] = None
    critical_expr_op: Optional[str] = None
    critical_expr_operand_widths: Tuple[int, ...] = ()
    widest_multiplier_operand_widths: Tuple[int, int] = ()
    widest_multiplier_assignment_target: Optional[str] = None
    widest_multiplier_phase: Optional[str] = None
    widest_multiplier_source_file: Optional[str] = None
    widest_multiplier_source_line: Optional[int] = None


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
    bytes_moved: int
    queue_capacity: int
    max_ready_depth: int
    started_tokens: int
    completed_tokens: int
    activity_proxy: float
    transport_pressure_proxy: float
    queue_occupancy_proxy: float
    compute_pressure_proxy: float
    estimated_area_proxy: float
    estimated_power_proxy: float


@dataclass(frozen=True)
class ArchitecturePpaStats:
    total_cycles: int
    makespan_cycles: float
    flow_stats: Mapping[str, FlowPpaStats]
    stage_stats: Mapping[str, StagePpaStats]
    total_bytes_moved: int = 0
    estimated_area_proxy: float = 0.0
    estimated_power_proxy: float = 0.0
    dominant_area_stage: Optional[str] = None
    dominant_power_stage: Optional[str] = None


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
    rewrite_proposals: Tuple["RewriteProposal", ...] = ()


def analyze_module_ppa(module: Any) -> ModulePpaStats:
    """Compute lightweight structural PPA signals from one DSL design instance."""

    module = _normalize_executable_module(module, context="analyze_module_ppa(...)")
    return _analyze_executable_module_ppa(module)


def _analyze_executable_module_ppa(module: SimModule) -> ModulePpaStats:
    """Compute lightweight structural PPA signals from one executable module."""

    signal_map = module.signal_map()
    memory_map = {memory.name: memory for memory in module.memories}
    input_bits = sum(signal.width for signal in module.signals if signal.kind == "input")
    output_bits = sum(signal_map[name].width for name in module.outputs)
    state_signals = tuple(signal for signal in module.signals if signal.kind == "state")
    state_bits = sum(signal.width for signal in state_signals)
    memory_bits = sum(memory.width * memory.depth for memory in module.memories)
    comb_assignments = sum(1 for assignment in module.assignments if assignment.phase == "comb")
    seq_assignments = sum(1 for assignment in module.assignments if assignment.phase == "seq")

    arithmetic_ops = 0
    compare_ops = 0
    mux_ops = 0
    multiplier_ops = 0
    adder_ops = 0
    shift_ops = 0
    max_expr_depth = 0
    critical_assignment = None
    widest_multiplier = None
    widest_multiplier_widths: Tuple[int, int] = ()
    for assignment in module.assignments:
        metrics = _expr_metrics(assignment.expr)
        arithmetic_ops += metrics["arithmetic_ops"]
        compare_ops += metrics["compare_ops"]
        mux_ops += metrics["mux_ops"]
        multiplier_ops += metrics["multiplier_ops"]
        adder_ops += metrics["adder_ops"]
        shift_ops += metrics["shift_ops"]
        depth = int(metrics["depth"])
        if depth > max_expr_depth:
            max_expr_depth = depth
            critical_assignment = assignment
        assignment_multiplier = _select_widest_multiplier(assignment.expr, signal_map, memory_map)
        if assignment_multiplier is not None:
            candidate_widths = _expr_operand_widths(assignment_multiplier, signal_map, memory_map)
            if len(candidate_widths) == 2:
                if widest_multiplier is None or max(candidate_widths) > max(widest_multiplier_widths) or (
                    max(candidate_widths) == max(widest_multiplier_widths)
                    and sum(candidate_widths) > sum(widest_multiplier_widths)
                ):
                    widest_multiplier = (assignment, assignment_multiplier)
                    widest_multiplier_widths = (int(candidate_widths[0]), int(candidate_widths[1]))
    for write in module.memory_writes:
        for expr in (write.addr, write.value, write.enable):
            metrics = _expr_metrics(expr)
            arithmetic_ops += metrics["arithmetic_ops"]
            compare_ops += metrics["compare_ops"]
            mux_ops += metrics["mux_ops"]
            multiplier_ops += metrics["multiplier_ops"]
            adder_ops += metrics["adder_ops"]
            shift_ops += metrics["shift_ops"]
            max_expr_depth = max(max_expr_depth, int(metrics["depth"]))
    critical_expr = _select_critical_expr(critical_assignment.expr) if critical_assignment is not None else None
    max_memory_width = max((memory.width for memory in module.memories), default=0)
    max_memory_depth = max((memory.depth for memory in module.memories), default=0)
    wide_memory_count = sum(1 for memory in module.memories if memory.width >= 48)
    small_memory_count = sum(1 for memory in module.memories if memory.depth <= 64)
    largest_memory = max(
        module.memories,
        key=lambda memory: (memory.width * memory.depth, memory.width, memory.depth, memory.name),
        default=None,
    )
    largest_memory_site = _largest_memory_source_site(module, largest_memory.name if largest_memory is not None else None)
    largest_state = max(
        state_signals,
        key=lambda signal: (signal.width, signal.name),
        default=None,
    )
    largest_state_site = _largest_state_source_site(module, largest_state.name if largest_state is not None else None)

    area_state_score = float(state_bits)
    area_memory_score = 0.125 * memory_bits
    area_io_score = 0.25 * (input_bits + output_bits)
    area_arithmetic_score = 24.0 * arithmetic_ops
    area_compare_score = 10.0 * compare_ops
    area_mux_score = 14.0 * mux_ops
    area_memory_write_score = 8.0 * len(module.memory_writes)
    area_comb_assignment_score = 6.0 * comb_assignments
    area_seq_assignment_score = 4.0 * seq_assignments
    estimated_area_score = max(
        area_state_score
        + area_memory_score
        + area_io_score
        + area_arithmetic_score
        + area_compare_score
        + area_mux_score
        + area_memory_write_score
        + area_comb_assignment_score
        + area_seq_assignment_score,
        1.0,
    )

    power_state_score = 0.02 * state_bits
    power_memory_score = 0.002 * memory_bits
    power_arithmetic_score = 0.2 * arithmetic_ops
    power_compare_score = 0.08 * compare_ops
    power_mux_score = 0.1 * mux_ops
    power_memory_write_score = 0.04 * len(module.memory_writes)
    estimated_power_score = max(
        power_state_score
        + power_memory_score
        + power_arithmetic_score
        + power_compare_score
        + power_mux_score
        + power_memory_write_score,
        1.0,
    )

    area_breakdown = {
        "state": area_state_score,
        "memory": area_memory_score,
        "io": area_io_score,
        "arithmetic": area_arithmetic_score,
        "compare": area_compare_score,
        "mux": area_mux_score,
        "memory_write": area_memory_write_score,
        "comb_assignment": area_comb_assignment_score,
        "seq_assignment": area_seq_assignment_score,
    }
    power_breakdown = {
        "state": power_state_score,
        "memory": power_memory_score,
        "arithmetic": power_arithmetic_score,
        "compare": power_compare_score,
        "mux": power_mux_score,
        "memory_write": power_memory_write_score,
    }

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
        multiplier_ops=multiplier_ops,
        adder_ops=adder_ops,
        shift_ops=shift_ops,
        max_expr_depth=max_expr_depth,
        max_memory_width=max_memory_width,
        max_memory_depth=max_memory_depth,
        wide_memory_count=wide_memory_count,
        small_memory_count=small_memory_count,
        largest_memory_name=largest_memory.name if largest_memory is not None else None,
        largest_memory_bits=(largest_memory.width * largest_memory.depth) if largest_memory is not None else 0,
        largest_memory_width=largest_memory.width if largest_memory is not None else 0,
        largest_memory_depth=largest_memory.depth if largest_memory is not None else 0,
        largest_memory_source_file=largest_memory_site[0],
        largest_memory_source_line=largest_memory_site[1],
        largest_state_name=largest_state.name if largest_state is not None else None,
        largest_state_bits=largest_state.width if largest_state is not None else 0,
        largest_state_source_file=largest_state_site[0],
        largest_state_source_line=largest_state_site[1],
        area_state_score=area_state_score,
        area_memory_score=area_memory_score,
        area_io_score=area_io_score,
        area_arithmetic_score=area_arithmetic_score,
        area_compare_score=area_compare_score,
        area_mux_score=area_mux_score,
        area_memory_write_score=area_memory_write_score,
        area_comb_assignment_score=area_comb_assignment_score,
        area_seq_assignment_score=area_seq_assignment_score,
        estimated_area_score=estimated_area_score,
        power_state_score=power_state_score,
        power_memory_score=power_memory_score,
        power_arithmetic_score=power_arithmetic_score,
        power_compare_score=power_compare_score,
        power_mux_score=power_mux_score,
        power_memory_write_score=power_memory_write_score,
        estimated_power_score=estimated_power_score,
        dominant_area_bucket=_dominant_score_bucket(area_breakdown),
        dominant_power_bucket=_dominant_score_bucket(power_breakdown),
        critical_assignment_target=(
            critical_assignment.target if critical_assignment is not None else None
        ),
        critical_assignment_phase=(
            critical_assignment.phase if critical_assignment is not None else None
        ),
        critical_assignment_source_file=(
            critical_assignment.source_file if critical_assignment is not None else None
        ),
        critical_assignment_source_line=(
            critical_assignment.source_line if critical_assignment is not None else None
        ),
        critical_expr_kind=type(critical_expr).__name__ if critical_expr is not None else None,
        critical_expr_op=_expr_op_name(critical_expr),
        critical_expr_operand_widths=(
            _expr_operand_widths(critical_expr, signal_map, memory_map)
            if critical_expr is not None
            else ()
        ),
        widest_multiplier_operand_widths=widest_multiplier_widths,
        widest_multiplier_assignment_target=(
            widest_multiplier[0].target if widest_multiplier is not None else None
        ),
        widest_multiplier_phase=(
            widest_multiplier[0].phase if widest_multiplier is not None else None
        ),
        widest_multiplier_source_file=(
            widest_multiplier[0].source_file if widest_multiplier is not None else None
        ),
        widest_multiplier_source_line=(
            widest_multiplier[0].source_line if widest_multiplier is not None else None
        ),
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
    total_bytes_moved = 0
    total_area_proxy = 0.0
    total_power_proxy = 0.0
    for stage_name, stage in model.stages.items():
        cycle_metrics = cycle_report.stage_metrics[stage_name]
        behavior_metrics = behavior_report.stage_metrics.get(stage_name)
        queue_capacity = max(model.queue_capacity(stage_name), 1)
        utilization = cycle_metrics.busy_token_cycles / max(cycle_report.total_cycles * stage.capacity, 1)
        queue_pressure = cycle_metrics.max_ready_depth / queue_capacity
        bytes_moved = behavior_metrics.bytes_moved if behavior_metrics is not None else 0
        activity_proxy = float(cycle_metrics.busy_token_cycles)
        transport_pressure_proxy = (
            float(bytes_moved) / float(max(stage.bandwidth_bytes_per_cycle, 16))
            if bytes_moved > 0
            else 0.0
        )
        queue_occupancy_proxy = queue_pressure * queue_capacity
        compute_pressure_proxy = (
            utilization * stage.capacity * stage.latency
            if stage.kind in {"compute", "datapath"}
            else 0.0
        )
        estimated_area_proxy = (
            float(stage.capacity * stage.latency)
            + float(queue_capacity)
            + (float(stage.bandwidth_bytes_per_cycle) / 16.0)
            + (
                float(stage.capacity * stage.latency)
                if stage.kind in {"compute", "datapath"}
                else 0.0
            )
        )
        estimated_power_proxy = (
            0.1 * activity_proxy
            + transport_pressure_proxy
            + queue_occupancy_proxy
            + compute_pressure_proxy
        )
        stage_stats[stage_name] = StagePpaStats(
            name=stage_name,
            kind=stage.kind,
            utilization=utilization,
            queue_pressure=queue_pressure,
            bandwidth_bytes_per_cycle=stage.bandwidth_bytes_per_cycle,
            bytes_moved=bytes_moved,
            queue_capacity=queue_capacity,
            max_ready_depth=cycle_metrics.max_ready_depth,
            started_tokens=cycle_metrics.started_tokens,
            completed_tokens=cycle_metrics.completed_tokens,
            activity_proxy=activity_proxy,
            transport_pressure_proxy=transport_pressure_proxy,
            queue_occupancy_proxy=queue_occupancy_proxy,
            compute_pressure_proxy=compute_pressure_proxy,
            estimated_area_proxy=estimated_area_proxy,
            estimated_power_proxy=estimated_power_proxy,
        )
        total_bytes_moved += bytes_moved
        total_area_proxy += estimated_area_proxy
        total_power_proxy += estimated_power_proxy

    return ArchitecturePpaStats(
        total_cycles=cycle_report.total_cycles,
        makespan_cycles=behavior_report.makespan_cycles,
        flow_stats=flow_stats,
        stage_stats=stage_stats,
        total_bytes_moved=total_bytes_moved,
        estimated_area_proxy=total_area_proxy,
        estimated_power_proxy=total_power_proxy,
        dominant_area_stage=_dominant_architecture_stage(stage_stats, bucket="area"),
        dominant_power_stage=_dominant_architecture_stage(stage_stats, bucket="power"),
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
    executable_module = None
    module_stats = None
    if module is not None:
        executable_module = _normalize_executable_module(module, context="advise_ppa(...)")
        module_stats = _analyze_executable_module_ppa(executable_module)
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
        recommendations.extend(_module_recommendations(module_stats, goals, executable_module))
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
    report = PpaReport(
        goals=goals,
        module_stats=module_stats,
        architecture_stats=arch_stats,
        recommendations=tuple(recommendations),
        calibrated_module_estimate=calibrated_module_estimate,
        calibrated_architecture_estimate=calibrated_architecture_estimate,
        transform_candidates=transform_candidates,
    )
    rewrite_proposals = ()
    if executable_module is not None:
        from rtlgen_x.ppa.rewrite import derive_rewrite_proposals

        rewrite_proposals = derive_rewrite_proposals(executable_module, report)
    return PpaReport(
        goals=report.goals,
        module_stats=report.module_stats,
        architecture_stats=report.architecture_stats,
        recommendations=report.recommendations,
        calibrated_module_estimate=report.calibrated_module_estimate,
        calibrated_architecture_estimate=report.calibrated_architecture_estimate,
        transform_candidates=report.transform_candidates,
        rewrite_proposals=rewrite_proposals,
    )


def _expr_metrics(expr) -> Dict[str, int]:
    if isinstance(expr, (ConstExpr, SignalRef, MemoryReadExpr)):
        return {
            "depth": 1,
            "arithmetic_ops": 0,
            "compare_ops": 0,
            "mux_ops": 0,
            "multiplier_ops": 0,
            "adder_ops": 0,
            "shift_ops": 0,
        }
    if isinstance(expr, MaskExpr):
        child = _expr_metrics(expr.value)
        return {
            "depth": child["depth"] + 1,
            **{
                key: child[key]
                for key in ("arithmetic_ops", "compare_ops", "mux_ops", "multiplier_ops", "adder_ops", "shift_ops")
            },
        }
    if isinstance(expr, UnaryExpr):
        child = _expr_metrics(expr.value)
        return {
            "depth": child["depth"] + 1,
            **{
                key: child[key]
                for key in ("arithmetic_ops", "compare_ops", "mux_ops", "multiplier_ops", "adder_ops", "shift_ops")
            },
        }
    if isinstance(expr, BinaryExpr):
        lhs = _expr_metrics(expr.lhs)
        rhs = _expr_metrics(expr.rhs)
        arithmetic_ops = lhs["arithmetic_ops"] + rhs["arithmetic_ops"]
        compare_ops = lhs["compare_ops"] + rhs["compare_ops"]
        multiplier_ops = lhs["multiplier_ops"] + rhs["multiplier_ops"]
        adder_ops = lhs["adder_ops"] + rhs["adder_ops"]
        shift_ops = lhs["shift_ops"] + rhs["shift_ops"]
        if expr.op in {"+", "-", "*", "<<", ">>", ">>>", "&", "|", "^"}:
            arithmetic_ops += 1
        if expr.op == "*":
            multiplier_ops += 1
        if expr.op in {"+", "-"}:
            adder_ops += 1
        if expr.op in {"<<", ">>", ">>>"}:
            shift_ops += 1
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            compare_ops += 1
        return {
            "depth": max(lhs["depth"], rhs["depth"]) + 1,
            "arithmetic_ops": arithmetic_ops,
            "compare_ops": compare_ops,
            "mux_ops": lhs["mux_ops"] + rhs["mux_ops"],
            "multiplier_ops": multiplier_ops,
            "adder_ops": adder_ops,
            "shift_ops": shift_ops,
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
            "multiplier_ops": cond["multiplier_ops"] + when_true["multiplier_ops"] + when_false["multiplier_ops"],
            "adder_ops": cond["adder_ops"] + when_true["adder_ops"] + when_false["adder_ops"],
            "shift_ops": cond["shift_ops"] + when_true["shift_ops"] + when_false["shift_ops"],
        }
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _select_widest_multiplier(expr, signal_map: Mapping[str, object], memory_map: Mapping[str, object]):
    best = None
    best_widths: Tuple[int, int] = ()

    def visit(node) -> None:
        nonlocal best, best_widths
        if isinstance(node, BinaryExpr):
            if node.op == "*":
                widths = _expr_operand_widths(node, signal_map, memory_map)
                if len(widths) == 2:
                    widths = (int(widths[0]), int(widths[1]))
                    if best is None or max(widths) > max(best_widths) or (
                        max(widths) == max(best_widths) and sum(widths) > sum(best_widths)
                    ):
                        best = node
                        best_widths = widths
            visit(node.lhs)
            visit(node.rhs)
            return
        if isinstance(node, MuxExpr):
            visit(node.cond)
            visit(node.when_true)
            visit(node.when_false)
            return
        if isinstance(node, MaskExpr):
            visit(node.value)
            return
        if isinstance(node, UnaryExpr):
            visit(node.value)
            return
        if isinstance(node, MemoryReadExpr):
            visit(node.addr)

    visit(expr)
    return best


def _select_critical_expr(expr):
    candidates: List[object] = []

    def visit(node) -> None:
        if isinstance(node, (BinaryExpr, MuxExpr, MaskExpr, UnaryExpr)):
            candidates.append(node)
        if isinstance(node, BinaryExpr):
            visit(node.lhs)
            visit(node.rhs)
            return
        if isinstance(node, MuxExpr):
            visit(node.cond)
            visit(node.when_true)
            visit(node.when_false)
            return
        if isinstance(node, MaskExpr):
            visit(node.value)
            return
        if isinstance(node, UnaryExpr):
            visit(node.value)
            return
        if isinstance(node, MemoryReadExpr):
            visit(node.addr)

    visit(expr)
    if not candidates:
        return expr
    candidates.sort(
        key=lambda node: (
            _expr_hotspot_score(node),
            _expr_hotspot_priority(node),
            _expr_node_count(node),
        ),
        reverse=True,
    )
    return candidates[0]


def _expr_hotspot_score(expr) -> int:
    if isinstance(expr, (ConstExpr, SignalRef)):
        return 1
    if isinstance(expr, MemoryReadExpr):
        return max(1, _expr_hotspot_score(expr.addr))
    if isinstance(expr, MaskExpr):
        return _expr_hotspot_score(expr.value)
    if isinstance(expr, UnaryExpr):
        child = _expr_hotspot_score(expr.value)
        return child if expr.op in {"$signed", "$unsigned"} else child + 1
    if isinstance(expr, BinaryExpr):
        child = max(_expr_hotspot_score(expr.lhs), _expr_hotspot_score(expr.rhs))
        return child if expr.op in {"<<", ">>", ">>>"} else child + 1
    if isinstance(expr, MuxExpr):
        return max(
            _expr_hotspot_score(expr.cond),
            _expr_hotspot_score(expr.when_true),
            _expr_hotspot_score(expr.when_false),
        )
    return 1


def _expr_hotspot_priority(expr) -> int:
    if isinstance(expr, BinaryExpr):
        if expr.op == "*":
            return 5
        if expr.op in {"+", "-"}:
            return 4
        if expr.op in {"&", "|", "^"}:
            return 3
        if expr.op in {"<<", ">>", ">>>"}:
            return 2
        return 1
    if isinstance(expr, MuxExpr):
        return 1
    return 0


def _expr_node_count(expr) -> int:
    if isinstance(expr, (ConstExpr, SignalRef)):
        return 1
    if isinstance(expr, MemoryReadExpr):
        return 1 + _expr_node_count(expr.addr)
    if isinstance(expr, MaskExpr):
        return 1 + _expr_node_count(expr.value)
    if isinstance(expr, UnaryExpr):
        return 1 + _expr_node_count(expr.value)
    if isinstance(expr, BinaryExpr):
        return 1 + _expr_node_count(expr.lhs) + _expr_node_count(expr.rhs)
    if isinstance(expr, MuxExpr):
        return 1 + _expr_node_count(expr.cond) + _expr_node_count(expr.when_true) + _expr_node_count(expr.when_false)
    return 1


def _expr_op_name(expr) -> Optional[str]:
    if isinstance(expr, BinaryExpr):
        return expr.op
    if isinstance(expr, UnaryExpr):
        return expr.op
    if isinstance(expr, MuxExpr):
        return "?:"
    if isinstance(expr, MaskExpr):
        return "mask"
    return None


def _expr_operand_widths(
    expr,
    signal_map: Mapping[str, object],
    memory_map: Mapping[str, object],
) -> Tuple[int, ...]:
    if isinstance(expr, BinaryExpr):
        return (
            _expr_width(expr.lhs, signal_map, memory_map),
            _expr_width(expr.rhs, signal_map, memory_map),
        )
    if isinstance(expr, UnaryExpr):
        return (_expr_width(expr.value, signal_map, memory_map),)
    if isinstance(expr, MaskExpr):
        return (_expr_width(expr.value, signal_map, memory_map),)
    if isinstance(expr, MuxExpr):
        return (
            _expr_width(expr.cond, signal_map, memory_map),
            _expr_width(expr.when_true, signal_map, memory_map),
            _expr_width(expr.when_false, signal_map, memory_map),
        )
    return ()


def _expr_width(
    expr,
    signal_map: Mapping[str, object],
    memory_map: Mapping[str, object],
) -> int:
    if isinstance(expr, ConstExpr):
        return expr.width
    if isinstance(expr, SignalRef):
        return signal_map[expr.name].width
    if isinstance(expr, MemoryReadExpr):
        return memory_map[expr.memory].width
    if isinstance(expr, MaskExpr):
        return expr.width
    if isinstance(expr, UnaryExpr):
        return 1 if expr.op == "!" else _expr_width(expr.value, signal_map, memory_map)
    if isinstance(expr, BinaryExpr):
        lhs_width = _expr_width(expr.lhs, signal_map, memory_map)
        rhs_width = _expr_width(expr.rhs, signal_map, memory_map)
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            return 1
        if expr.op == "*":
            return lhs_width + rhs_width
        if expr.op in {"+", "-"}:
            return max(lhs_width, rhs_width) + 1
        return max(lhs_width, rhs_width)
    if isinstance(expr, MuxExpr):
        return max(
            _expr_width(expr.when_true, signal_map, memory_map),
            _expr_width(expr.when_false, signal_map, memory_map),
        )
    return 1


def _module_area_breakdown(stats: ModulePpaStats) -> Dict[str, float]:
    return {
        "state": stats.area_state_score,
        "memory": stats.area_memory_score,
        "io": stats.area_io_score,
        "arithmetic": stats.area_arithmetic_score,
        "compare": stats.area_compare_score,
        "mux": stats.area_mux_score,
        "memory_write": stats.area_memory_write_score,
        "comb_assignment": stats.area_comb_assignment_score,
        "seq_assignment": stats.area_seq_assignment_score,
    }


def _module_power_breakdown(stats: ModulePpaStats) -> Dict[str, float]:
    return {
        "state": stats.power_state_score,
        "memory": stats.power_memory_score,
        "arithmetic": stats.power_arithmetic_score,
        "compare": stats.power_compare_score,
        "mux": stats.power_mux_score,
        "memory_write": stats.power_memory_write_score,
    }


def _module_breakdown_evidence(stats: ModulePpaStats) -> Dict[str, object]:
    return {
        "area_breakdown": _module_area_breakdown(stats),
        "power_breakdown": _module_power_breakdown(stats),
        "estimated_area_score": stats.estimated_area_score,
        "estimated_power_score": stats.estimated_power_score,
        "dominant_area_bucket": stats.dominant_area_bucket,
        "dominant_power_bucket": stats.dominant_power_bucket,
    }


def _source_site(source_file: Optional[str], source_line: Optional[int]) -> Optional[str]:
    if not source_file:
        return None
    if source_line is None:
        return source_file
    return f"{source_file}:{source_line}"


def _module_target_label(
    module_name: str,
    target_name: Optional[str],
    *,
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
) -> Optional[str]:
    base = module_name
    if target_name:
        base = f"{module_name}.{target_name}"
    location = _source_site(source_file, source_line)
    if location is None:
        return base
    return f"{base} @ {location}"


def _module_target_evidence(
    *,
    module_name: str,
    target_kind: str,
    target_name: Optional[str],
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
) -> Dict[str, object]:
    evidence: Dict[str, object] = {
        "target_kind": target_kind,
    }
    if target_name is not None:
        evidence["target_name"] = target_name
    location = _source_site(source_file, source_line)
    if location is not None:
        evidence["target_location"] = location
    label = _module_target_label(
        module_name,
        target_name,
        source_file=source_file,
        source_line=source_line,
    )
    if label is not None:
        evidence["target_label"] = label
        evidence["rtl_anchor"] = label
    return evidence


def _find_memory_write_site(
    module_name: str,
    memory_name: str,
    module: Optional[SimModule],
) -> Optional[str]:
    if module is None:
        return None
    for write in module.memory_writes:
        if write.memory == memory_name:
            return _module_target_label(
                module_name,
                memory_name,
                source_file=write.source_file,
                source_line=write.source_line,
            )
    return None


def _find_assignment_site(
    module_name: str,
    target_name: str,
    module: Optional[SimModule],
    *,
    phase: Optional[str] = None,
) -> Optional[str]:
    if module is None:
        return None
    for assignment in module.assignments:
        if assignment.target != target_name:
            continue
        if phase is not None and assignment.phase != phase:
            continue
        return _module_target_label(
            module_name,
            target_name,
            source_file=assignment.source_file,
            source_line=assignment.source_line,
        )
    signal = next((signal for signal in module.signals if signal.name == target_name), None)
    if signal is None:
        return None
    return _module_target_label(module_name, target_name)


def _protocol_target_hints(stats: ModulePpaStats, module: Optional[SimModule] = None) -> Dict[str, object]:
    module_name_lower = stats.module_name.lower()
    hints: Dict[str, object] = {}
    available_memory_names = {memory.name for memory in module.memories} if module is not None else set()
    if "fifo" in module_name_lower or "queue" in module_name_lower:
        control_targets = tuple(
            name
            for name in (
                stats.critical_assignment_target,
                "count",
                "wr_ptr",
                "rd_ptr",
                "push_fire",
                "pop_fire",
            )
            if isinstance(name, str) and name
        )
        if control_targets:
            hints["queue_control_targets"] = tuple(dict.fromkeys(control_targets))
            hints["queue_control_anchors"] = tuple(
                anchor
                for anchor in (
                    _find_assignment_site(stats.module_name, name, module, phase="seq")
                    or _find_assignment_site(stats.module_name, name, module)
                    for name in dict.fromkeys(control_targets)
                )
                if anchor is not None
            )
        if "queue" in module_name_lower:
            sideband_targets = tuple(
                name
                for name in ("req_storage", "addr_storage", "write_storage", "strb_storage")
                if name in available_memory_names
            )
            if sideband_targets:
                hints["queue_sideband_targets"] = sideband_targets
                hints["queue_sideband_anchors"] = tuple(
                    anchor
                    for anchor in (
                        _find_memory_write_site(stats.module_name, name, module)
                        for name in sideband_targets
                    )
                    if anchor is not None
                )
    if "registerbank" in module_name_lower:
        control_targets = tuple(
            name
            for name in (
                stats.critical_assignment_target,
                stats.largest_state_name,
                "write_commit",
                "read_fire",
                "aw_seen",
                "w_seen",
                "bvalid_state",
                "rvalid_state",
                "ack_state",
                "read_valid_state",
            )
            if isinstance(name, str) and name
        )
        if control_targets:
            hints["register_bank_control_targets"] = tuple(dict.fromkeys(control_targets))
            hints["register_bank_control_anchors"] = tuple(
                anchor
                for anchor in (
                    _find_assignment_site(stats.module_name, name, module, phase="seq")
                    or _find_assignment_site(stats.module_name, name, module)
                    for name in dict.fromkeys(control_targets)
                )
                if anchor is not None
            )
    if "skidbuffer" in module_name_lower:
        payload_targets = tuple(
            name for name in (stats.largest_state_name, "buf_valid") if isinstance(name, str) and name
        )
        if payload_targets:
            hints["handshake_payload_targets"] = tuple(dict.fromkeys(payload_targets))
            hints["handshake_payload_anchors"] = tuple(
                anchor
                for anchor in (
                    _find_assignment_site(stats.module_name, name, module, phase="seq")
                    or _find_assignment_site(stats.module_name, name, module)
                    for name in dict.fromkeys(payload_targets)
                )
                if anchor is not None
            )
    elif "readyvalidregister" in module_name_lower:
        payload_targets = tuple(
            name for name in (stats.largest_state_name, "valid_reg") if isinstance(name, str) and name
        )
        if payload_targets:
            hints["handshake_payload_targets"] = tuple(dict.fromkeys(payload_targets))
            hints["handshake_payload_anchors"] = tuple(
                anchor
                for anchor in (
                    _find_assignment_site(stats.module_name, name, module, phase="seq")
                    or _find_assignment_site(stats.module_name, name, module)
                    for name in dict.fromkeys(payload_targets)
                )
                if anchor is not None
            )
    return hints


def _infer_multiplier_pattern(stats: ModulePpaStats) -> str:
    target = (stats.widest_multiplier_assignment_target or "").lower()
    if target.startswith("mpd_"):
        return "signed_multiplier_pipeline"
    if stats.multiplier_ops == 1 and target == "prod" and stats.adder_ops > 0:
        return "mac_style"
    if stats.multiplier_ops >= 2:
        return "multi_multiplier_datapath"
    return "inline_multiplier_logic"


def _infer_memory_pattern(stats: ModulePpaStats) -> str:
    module = stats.module_name.lower()
    target = (stats.largest_memory_name or "").lower()
    if target.startswith("lut"):
        return "lut_rom"
    if target in {"storage", "fifo_storage"} and "fifo" in module and stats.memory_count == 1:
        return "fifo_queue_storage"
    if target.endswith("_storage") and "queue" in module and stats.memory_count >= 2:
        return "queue_metadata_arrays"
    if target in {"regmem", "wbmem"} or "registerbank" in module:
        return "control_register_bank"
    if target == "mem" and stats.memory_count == 1 and stats.max_memory_depth <= 16:
        return "small_ram"
    if stats.memory_count == 1 and stats.max_memory_depth >= 256:
        return "large_single_memory"
    if stats.small_memory_count >= 4:
        return "many_small_tables"
    return "generic_storage"


def _infer_state_pattern(stats: ModulePpaStats) -> str:
    module = stats.module_name.lower()
    target = (stats.largest_state_name or "").lower()
    if target.startswith("rf_"):
        return "register_file_rows"
    if target in {"buf_data", "data_reg"} and ("readyvalid" in module or "skidbuffer" in module):
        return "handshake_payload_state"
    if ("registerbank" in module) and (target.endswith("_latched") or target.endswith("_state")):
        return "register_bank_control_state"
    if target.startswith("mpd_") or target.startswith("mpv_"):
        return "multiplier_pipeline_state"
    if target in {"acc", "prod", "pipe_a", "pipe_b"} or target.startswith("pipe_"):
        return "mac_pipeline_state"
    return "generic_sequential_state"


def _largest_memory_source_site(
    module: SimModule,
    memory_name: Optional[str],
) -> Tuple[Optional[str], Optional[int]]:
    if memory_name is None:
        return None, None
    candidates = [
        (write.source_file, write.source_line)
        for write in module.memory_writes
        if write.memory == memory_name and write.source_file
    ]
    if not candidates:
        return None, None
    return candidates[0]


def _largest_state_source_site(
    module: SimModule,
    state_name: Optional[str],
) -> Tuple[Optional[str], Optional[int]]:
    if state_name is None:
        return None, None
    candidates = [
        (assignment.source_file, assignment.source_line)
        for assignment in module.assignments
        if assignment.target == state_name and assignment.phase == "seq" and assignment.source_file
    ]
    if not candidates:
        return None, None
    return candidates[0]


def _timing_suggestions(stats: ModulePpaStats) -> Tuple[str, ...]:
    suggestions = [
        "Insert a register boundary around the deepest arithmetic/control chain so one stage owns fewer operators.",
        "Split wide mux or adder trees so the critical path does not cross every combine point in one cycle.",
    ]
    if stats.critical_expr_op == "*":
        target = stats.critical_assignment_target or "the critical multiply"
        suggestions.insert(
            0,
            f"Treat '{target}' as the timing anchor and pipeline the multiply or its partial-product accumulation explicitly.",
        )
    elif stats.critical_expr_op in {"+", "-"} and stats.critical_assignment_target is not None:
        suggestions.insert(
            0,
            f"Rebalance the adder tree feeding '{stats.critical_assignment_target}' so the add depth is spread across stages.",
        )
    return tuple(suggestions)


def _memory_suggestions(stats: ModulePpaStats) -> Tuple[str, ...]:
    target = stats.largest_memory_name or "the largest memory"
    pattern = _infer_memory_pattern(stats)
    suggestions = [
        f"Bank '{target}' by address range or port demand if concurrent accesses are limiting frequency or macro mapping.",
        f"Gate read/write enables on '{target}' so inactive storage rows do not toggle every cycle.",
    ]
    if pattern == "lut_rom":
        suggestions.insert(
            0,
            f"Treat '{target}' as a coefficient ROM first: compare wider packed rows or shared LUT banks before rewriting it into generic RAM logic."
        )
    elif pattern == "fifo_queue_storage":
        suggestions.insert(
            0,
            f"Treat '{target}' as FIFO payload storage first: compare flop, shift-register, and RAM-style implementations before rewriting queue control."
        )
        suggestions.append(
            "Keep payload storage dense and let pointer/count logic stay small; avoid spreading queue payload bits across always-toggling control paths."
        )
    elif pattern == "queue_metadata_arrays":
        suggestions.insert(
            0,
            f"Treat '{target}' as queue metadata storage: pack request payload and sideband fields per entry before adding more shallow arrays."
        )
        suggestions.append(
            "Prefer one per-entry bundle RAM over several lock-step metadata arrays when addr/write/strobe fields are always dequeued together."
        )
    elif pattern == "control_register_bank":
        suggestions.insert(
            0,
            f"Treat '{target}' as control-plane register-bank storage: compare byte-lane packing and address-aperture partitioning before deeper protocol rewrites."
        )
        suggestions.append(
            "Keep protocol capture/response logic shallow and move CSR density decisions into the storage layout rather than duplicating decode around every lane."
        )
    elif pattern == "many_small_tables":
        suggestions.insert(
            0,
            f"Treat '{target}' as part of a small-table cluster: consolidate related tables before attempting lower-level RAM rewrites."
        )
    if stats.small_memory_count >= 4 and stats.max_memory_depth <= 64:
        suggestions.append(
            "Pack lock-step coefficient tables into fewer wider ROM words when related entries are always fetched together."
        )
    else:
        suggestions.append(
            "Prefer a dedicated SRAM/ROM macro when the storage footprint dominates the module area score."
        )
    return tuple(suggestions)


def _state_suggestions(stats: ModulePpaStats) -> Tuple[str, ...]:
    target = stats.largest_state_name or "the largest state group"
    pattern = _infer_state_pattern(stats)
    suggestions = [
        f"Clock-gate or conditionally update '{target}' so idle cycles do not toggle the full state cone.",
        "Split cold or rarely observed state into a separate block if it does not need the hot datapath clock rate.",
    ]
    if pattern == "register_file_rows":
        suggestions.insert(
            0,
            f"Treat '{target}' as explicit register-file storage: compare a denser RAM-style wrapper before hand-optimizing individual rows."
        )
    elif pattern == "handshake_payload_state":
        suggestions.insert(
            0,
            f"Treat '{target}' as handshake payload state: only update payload bits on accepted transfers and keep valid/ready control independent."
        )
    elif pattern == "register_bank_control_state":
        suggestions.insert(
            0,
            f"Treat '{target}' as protocol capture state: split request capture, response tracking, and memory access state instead of widening one monolithic control block."
        )
    elif pattern == "multiplier_pipeline_state":
        suggestions.insert(
            0,
            f"Treat '{target}' as multiplier pipeline state: reduce toggling by gating valid/enable propagation before rewriting arithmetic."
        )
    elif pattern == "mac_pipeline_state":
        suggestions.insert(
            0,
            f"Treat '{target}' as MAC pipeline state: separate accumulator updates from operand staging if only one side is hot."
        )
    return tuple(suggestions)


def _expr_contains_signal_ref(expr: Any, signal_name: str) -> bool:
    if isinstance(expr, SignalRef):
        return expr.name == signal_name
    if isinstance(expr, BinaryExpr):
        return _expr_contains_signal_ref(expr.lhs, signal_name) or _expr_contains_signal_ref(expr.rhs, signal_name)
    if isinstance(expr, MuxExpr):
        return (
            _expr_contains_signal_ref(expr.cond, signal_name)
            or _expr_contains_signal_ref(expr.when_true, signal_name)
            or _expr_contains_signal_ref(expr.when_false, signal_name)
        )
    if isinstance(expr, UnaryExpr):
        return _expr_contains_signal_ref(expr.value, signal_name)
    if isinstance(expr, MaskExpr):
        return _expr_contains_signal_ref(expr.value, signal_name)
    if isinstance(expr, MemoryReadExpr):
        return _expr_contains_signal_ref(expr.addr, signal_name)
    return False


def _handshake_payload_already_held(stats: ModulePpaStats, module: Optional[SimModule]) -> bool:
    if module is None:
        return False
    payload_name = stats.largest_state_name
    if not payload_name:
        return False
    payload_assignment = next(
        (assignment for assignment in module.assignments if assignment.target == payload_name and assignment.phase == "seq"),
        None,
    )
    if payload_assignment is None or not isinstance(payload_assignment.expr, MuxExpr):
        return False
    outer_mux = payload_assignment.expr.when_false
    if not isinstance(outer_mux, MuxExpr):
        return False
    if not isinstance(outer_mux.when_false, SignalRef) or outer_mux.when_false.name != payload_name:
        return False
    inner_mux = outer_mux.when_true
    if not isinstance(inner_mux, MuxExpr):
        return False
    return isinstance(inner_mux.when_false, SignalRef) and inner_mux.when_false.name == payload_name


def _register_bank_control_already_partitioned(stats: ModulePpaStats, module: Optional[SimModule]) -> bool:
    if module is None:
        return False
    signal_names = {signal.name for signal in module.signals}
    if "capture_fire" not in signal_names:
        return False
    payload_name = stats.largest_state_name
    if not payload_name:
        return False
    payload_assignment = next(
        (assignment for assignment in module.assignments if assignment.target == payload_name and assignment.phase == "seq"),
        None,
    )
    if payload_assignment is None or not _expr_contains_signal_ref(payload_assignment.expr, "capture_fire"):
        return False
    response_targets = {"bvalid_state", "rvalid_state", "rdata_state", "ack_state", "read_valid_state", "read_data_state"}
    response_assignments = [assignment for assignment in module.assignments if assignment.target in response_targets and assignment.phase == "seq"]
    if not response_assignments:
        return False
    return not any(_expr_contains_signal_ref(assignment.expr, "capture_fire") for assignment in response_assignments)


def _suggested_multiplier_tile_width(widths: Tuple[int, int]) -> int:
    widest = max(widths, default=0)
    if widest >= 64:
        return 16
    if widest >= 24:
        return 8
    return 4


def _multiplier_strategy(widths: Tuple[int, int]) -> str:
    widest = max(widths, default=0)
    if widest >= 64:
        return "karatsuba_or_tiled"
    if widest >= 24:
        return "dsp_or_tiled"
    return "direct_or_shared"


def _multiplier_suggestions(stats: ModulePpaStats) -> Tuple[str, ...]:
    widths = stats.widest_multiplier_operand_widths
    target = stats.widest_multiplier_assignment_target or "the widest multiply"
    pattern = _infer_multiplier_pattern(stats)
    if len(widths) != 2:
        return (
            f"Check whether '{target}' should be pipelined or shared instead of left as a monolithic multiplier.",
            "If throughput allows, serialize mutually exclusive multiplies onto a smaller shared datapath.",
        )
    tile_width = _suggested_multiplier_tile_width(widths)
    widest = max(widths)
    suggestions = [
        (
            f"Rewrite '{target}' as a pipelined tree of {tile_width}x{tile_width} partial products "
            f"instead of one monolithic {widths[0]}x{widths[1]} multiply."
        ),
        "Place a register cut between partial-product generation and accumulation so the multiply and following add do not land in one stage.",
    ]
    if pattern == "signed_multiplier_pipeline":
        suggestions.insert(
            0,
            f"Treat '{target}' as a SignedMultiplier-style staged datapath: keep the valid/payload shell and only retime the product stages."
        )
    elif pattern == "mac_style":
        suggestions.insert(
            0,
            f"Treat '{target}' as part of a MAC-style pipeline: split operand staging, product generation, and accumulate paths instead of rewriting the whole block at once."
        )
    if widest >= 64:
        suggestions.insert(
            1,
            "For very wide operands, compare schoolbook tiling against Karatsuba/Ofman decomposition once the base tile size is fixed.",
        )
    else:
        suggestions.insert(
            1,
            "If the multiply is low duty-cycle, compare a shared DSP-style macro against a fully parallel implementation.",
        )
    return tuple(suggestions)


def _architecture_area_power_suggestions(stage, *, bucket: str) -> Tuple[str, ...]:
    if stage.kind == "memory":
        if bucket == "area":
            return (
                f"Reduce banks, queue depth, or bandwidth width at '{stage.name}' if the memory system is over-provisioned for the measured workload.",
                f"Consolidate adjacent lookup or SRAM structures around '{stage.name}' when traffic does not need separate ports.",
            )
        return (
            f"Lower standing traffic and queue occupancy around '{stage.name}' so the memory path is not active every cycle.",
            f"Prefer narrower or demand-gated accesses at '{stage.name}' when bytes moved dominate power proxy.",
        )
    if stage.kind in {"compute", "datapath"}:
        if bucket == "area":
            return (
                f"Reduce lane count or share low-duty operators inside '{stage.name}' if the current capacity is rarely saturated.",
                f"Narrow the heaviest arithmetic inside '{stage.name}' or move infrequent operations onto a side path.",
            )
        return (
            f"Clock-gate idle compute lanes in '{stage.name}' and avoid keeping all lanes toggling during light workloads.",
            f"Pipeline or stage-localize hot arithmetic inside '{stage.name}' so wide logic does not toggle across the full datapath every cycle.",
        )
    if bucket == "area":
        return (
            f"Trim queueing and buffering resources around '{stage.name}' if this stage's area proxy is materially above its neighbors.",
            f"Check whether '{stage.name}' needs its current capacity and bandwidth settings for the target workload mix.",
        )
    return (
        f"Reduce standing occupancy and unnecessary activity around '{stage.name}' to lower stage power proxy.",
        f"Gate or decouple always-on control work around '{stage.name}' when the workload is bursty.",
    )


def _dominant_score_bucket(breakdown: Mapping[str, float]) -> Optional[str]:
    if not breakdown:
        return None
    key, value = max(breakdown.items(), key=lambda item: (item[1], item[0]))
    return key if value > 0 else None


def _dominant_architecture_stage(
    stage_stats: Mapping[str, StagePpaStats],
    *,
    bucket: str,
) -> Optional[str]:
    if not stage_stats:
        return None
    if bucket == "area":
        stage_name, stats = max(
            stage_stats.items(),
            key=lambda item: (item[1].estimated_area_proxy, item[0]),
        )
        return stage_name if stats.estimated_area_proxy > 0 else None
    if bucket == "power":
        stage_name, stats = max(
            stage_stats.items(),
            key=lambda item: (item[1].estimated_power_proxy, item[0]),
        )
        return stage_name if stats.estimated_power_proxy > 0 else None
    raise ValueError(f"unsupported architecture proxy bucket '{bucket}'")


def _architecture_stage_evidence(stats: ArchitecturePpaStats, stage_name: str) -> Dict[str, object]:
    stage = stats.stage_stats[stage_name]
    return {
        "stage": stage_name,
        "stage_kind": stage.kind,
        "stage_utilization": stage.utilization,
        "stage_queue_pressure": stage.queue_pressure,
        "stage_queue_capacity": stage.queue_capacity,
        "stage_max_ready_depth": stage.max_ready_depth,
        "stage_bandwidth_bytes_per_cycle": stage.bandwidth_bytes_per_cycle,
        "stage_bytes_moved": stage.bytes_moved,
        "stage_started_tokens": stage.started_tokens,
        "stage_completed_tokens": stage.completed_tokens,
        "stage_activity_proxy": stage.activity_proxy,
        "stage_transport_pressure_proxy": stage.transport_pressure_proxy,
        "stage_queue_occupancy_proxy": stage.queue_occupancy_proxy,
        "stage_compute_pressure_proxy": stage.compute_pressure_proxy,
        "stage_area_proxy": stage.estimated_area_proxy,
        "stage_power_proxy": stage.estimated_power_proxy,
    }


def _module_recommendations(
    stats: ModulePpaStats,
    goals: PpaGoals,
    module: Optional[SimModule] = None,
) -> List[PpaRecommendation]:
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
                evidence={
                    "module": stats.module_name,
                    "max_expr_depth": stats.max_expr_depth,
                    "target_depth": depth_limit,
                    "critical_assignment_target": stats.critical_assignment_target,
                    "critical_assignment_phase": stats.critical_assignment_phase,
                    "critical_assignment_source_file": stats.critical_assignment_source_file,
                    "critical_assignment_source_line": stats.critical_assignment_source_line,
                    "critical_expr_kind": stats.critical_expr_kind,
                    "critical_expr_op": stats.critical_expr_op,
                    "critical_expr_operand_widths": stats.critical_expr_operand_widths,
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="assignment",
                        target_name=stats.critical_assignment_target,
                        source_file=stats.critical_assignment_source_file,
                        source_line=stats.critical_assignment_source_line,
                    ),
                    **_protocol_target_hints(stats, module),
                },
                suggestions=_timing_suggestions(stats),
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
                evidence={
                    "module": stats.module_name,
                    "memory_bits": stats.memory_bits,
                    "memory_count": stats.memory_count,
                    "max_memory_width": stats.max_memory_width,
                    "max_memory_depth": stats.max_memory_depth,
                    "memory_pattern_hint": _infer_memory_pattern(stats),
                    "wide_memory_count": stats.wide_memory_count,
                    "small_memory_count": stats.small_memory_count,
                    "largest_memory_name": stats.largest_memory_name,
                    "largest_memory_bits": stats.largest_memory_bits,
                    "largest_memory_width": stats.largest_memory_width,
                    "largest_memory_depth": stats.largest_memory_depth,
                    "largest_memory_source_file": stats.largest_memory_source_file,
                    "largest_memory_source_line": stats.largest_memory_source_line,
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="memory",
                        target_name=stats.largest_memory_name,
                        source_file=stats.largest_memory_source_file,
                        source_line=stats.largest_memory_source_line,
                    ),
                    **_protocol_target_hints(stats, module),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=_memory_suggestions(stats),
            )
        )
    if stats.small_memory_count >= 4 and stats.max_memory_depth <= 64:
        recs.append(
            PpaRecommendation(
                category="area_power",
                severity="medium",
                title="Consolidate many small lookup memories",
                rationale=(
                    f"Module '{stats.module_name}' uses {stats.small_memory_count} shallow memories; "
                    "packing related coefficient tables can reduce decoder duplication and simplify routing."
                ),
                evidence={
                    "module": stats.module_name,
                    "small_memory_count": stats.small_memory_count,
                    "memory_count": stats.memory_count,
                    "memory_pattern_hint": _infer_memory_pattern(stats),
                    "max_memory_depth": stats.max_memory_depth,
                    "max_memory_width": stats.max_memory_width,
                    "largest_memory_name": stats.largest_memory_name,
                    "largest_memory_bits": stats.largest_memory_bits,
                    "largest_memory_source_file": stats.largest_memory_source_file,
                    "largest_memory_source_line": stats.largest_memory_source_line,
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="memory_group",
                        target_name=stats.largest_memory_name,
                        source_file=stats.largest_memory_source_file,
                        source_line=stats.largest_memory_source_line,
                    ),
                    **_protocol_target_hints(stats, module),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=(
                    "Pack related coefficient rows into one wider ROM word when the read access pattern is lock-step.",
                    "Prefer fewer coefficient banks when c0/c1/c2 are always fetched together.",
                ),
            )
        )
    state_limit = goals.max_state_bits if goals.max_state_bits is not None else 256
    if stats.state_bits > state_limit:
        state_pattern_hint = _infer_state_pattern(stats)
        skip_payload_gating = (
            state_pattern_hint == "handshake_payload_state"
            and _handshake_payload_already_held(stats, module)
        )
        skip_control_partition = (
            state_pattern_hint == "register_bank_control_state"
            and _register_bank_control_already_partitioned(stats, module)
        )
        recs.append(
            PpaRecommendation(
                category="power",
                severity="medium",
                title="Reduce or gate large sequential state",
                rationale=(
                    f"Module '{stats.module_name}' has {stats.state_bits} explicit state bits, "
                    f"above the working threshold {state_limit}."
                ),
                evidence={
                    "module": stats.module_name,
                    "state_bits": stats.state_bits,
                    "state_count": stats.state_count,
                    "state_pattern_hint": state_pattern_hint,
                    "payload_gating_already_applied": skip_payload_gating,
                    "control_partition_already_applied": skip_control_partition,
                    "largest_state_name": stats.largest_state_name,
                    "largest_state_bits": stats.largest_state_bits,
                    "largest_state_source_file": stats.largest_state_source_file,
                    "largest_state_source_line": stats.largest_state_source_line,
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="state",
                        target_name=stats.largest_state_name,
                        source_file=stats.largest_state_source_file,
                        source_line=stats.largest_state_source_line,
                    ),
                    **_protocol_target_hints(stats, module),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=_state_suggestions(stats),
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
                evidence={
                    "module": stats.module_name,
                    "arithmetic_ops": stats.arithmetic_ops,
                    "comb_assignments": stats.comb_assignments,
                    "multiplier_ops": stats.multiplier_ops,
                    "adder_ops": stats.adder_ops,
                    "shift_ops": stats.shift_ops,
                    "critical_assignment_target": stats.critical_assignment_target,
                    "critical_assignment_phase": stats.critical_assignment_phase,
                    "critical_assignment_source_file": stats.critical_assignment_source_file,
                    "critical_assignment_source_line": stats.critical_assignment_source_line,
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="assignment",
                        target_name=stats.critical_assignment_target,
                        source_file=stats.critical_assignment_source_file,
                        source_line=stats.critical_assignment_source_line,
                    ),
                    **_protocol_target_hints(stats, module),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=(
                    f"Start from '{stats.critical_assignment_target or 'the hottest assignment'}' and {mode_hint}.",
                    "Keep rare or mutually exclusive arithmetic off the hottest always-active path.",
                ),
            )
        )
    if stats.multiplier_ops >= 2 or (
        stats.multiplier_ops >= 1
        and len(stats.widest_multiplier_operand_widths) == 2
        and max(stats.widest_multiplier_operand_widths) >= 8
    ):
        widest = stats.widest_multiplier_operand_widths
        product_width = sum(widest)
        multiplier_severity = "high" if widest and (max(widest) >= 64 or product_width >= 128) else "medium"
        recs.append(
            PpaRecommendation(
                category="timing",
                severity=multiplier_severity,
                title="Audit multiplier-heavy stages",
                rationale=(
                    f"Module '{stats.module_name}' contains {stats.multiplier_ops} multiplier nodes; "
                    "wide signed multiplies usually dominate SFU-style fixed-point timing and energy."
                ),
                evidence={
                    "module": stats.module_name,
                    "multiplier_ops": stats.multiplier_ops,
                    "multiplier_pattern_hint": _infer_multiplier_pattern(stats),
                    "widest_multiplier_operand_widths": widest,
                    "widest_multiplier_assignment_target": stats.widest_multiplier_assignment_target,
                    "widest_multiplier_phase": stats.widest_multiplier_phase,
                    "widest_multiplier_source_file": stats.widest_multiplier_source_file,
                    "widest_multiplier_source_line": stats.widest_multiplier_source_line,
                    "widest_multiplier_product_width": product_width,
                    "recommended_multiplier_tile_width": (
                        _suggested_multiplier_tile_width(widest) if widest else None
                    ),
                    "recommended_multiplier_strategy": (
                        _multiplier_strategy(widest) if widest else None
                    ),
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="multiplier",
                        target_name=stats.widest_multiplier_assignment_target,
                        source_file=stats.widest_multiplier_source_file,
                        source_line=stats.widest_multiplier_source_line,
                    ),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=_multiplier_suggestions(stats),
            )
        )
    if stats.dominant_area_bucket == "arithmetic" and stats.multiplier_ops > 0:
        recs.append(
            PpaRecommendation(
                category="area_power",
                severity="medium",
                title="Arithmetic dominates module area proxy",
                rationale=(
                    f"Module '{stats.module_name}' is area-limited mainly by arithmetic structure, "
                    f"with {stats.multiplier_ops} multiplies and {stats.adder_ops} add/sub nodes."
                ),
                evidence={
                    "module": stats.module_name,
                    "multiplier_ops": stats.multiplier_ops,
                    "adder_ops": stats.adder_ops,
                    "shift_ops": stats.shift_ops,
                    "multiplier_pattern_hint": _infer_multiplier_pattern(stats),
                    **_module_target_evidence(
                        module_name=stats.module_name,
                        target_kind="multiplier",
                        target_name=stats.widest_multiplier_assignment_target,
                        source_file=stats.widest_multiplier_source_file,
                        source_line=stats.widest_multiplier_source_line,
                    ),
                    **_module_breakdown_evidence(stats),
                },
                suggestions=(
                    "Share or time-multiplex low-duty arithmetic first, then revisit whether the widest multiply really needs full-width parallel hardware.",
                    "If the datapath is coefficient-driven, compare exact multiply against ROM-plus-interpolation or shift-add alternatives before rewriting RTL.",
                ),
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
                **_architecture_stage_evidence(stats, flow.bottleneck_stage),
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
            evidence = {
                "flow": flow_name,
                "stall_ratio": flow.stall_ratio,
                **_architecture_stage_evidence(stats, flow.bottleneck_stage),
            }
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
            evidence = {
                "stage": stage_name,
                "utilization": stage.utilization,
                "kind": stage.kind,
                **_architecture_stage_evidence(stats, stage_name),
            }
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
            evidence = {
                "stage": stage_name,
                "queue_pressure": stage.queue_pressure,
                **_architecture_stage_evidence(stats, stage_name),
            }
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
    if stats.dominant_area_stage is not None:
        stage_name = stats.dominant_area_stage
        stage_stats = stats.stage_stats[stage_name]
        total_proxy = max(stats.estimated_area_proxy, 1.0)
        share = stage_stats.estimated_area_proxy / total_proxy
        if share >= 0.35:
            recs.append(
                PpaRecommendation(
                    category="area_power",
                    severity="medium",
                    title=f"Area proxy concentrates at stage '{stage_name}'",
                    rationale=(
                        f"Stage '{stage_name}' contributes {stage_stats.estimated_area_proxy:.2f} of "
                        f"{stats.estimated_area_proxy:.2f} total architecture area proxy ({share:.1%})."
                    ),
                    evidence={
                        "dominant_area_stage": stage_name,
                        "dominant_area_share": share,
                        "target_kind": "stage",
                        "target_name": stage_name,
                        "target_label": f"stage {stage_name}",
                        **_architecture_stage_evidence(stats, stage_name),
                    },
                    suggestions=_architecture_area_power_suggestions(model.stage(stage_name), bucket="area"),
                )
            )
    if stats.dominant_power_stage is not None:
        stage_name = stats.dominant_power_stage
        stage_stats = stats.stage_stats[stage_name]
        total_proxy = max(stats.estimated_power_proxy, 1.0)
        share = stage_stats.estimated_power_proxy / total_proxy
        if share >= 0.35:
            recs.append(
                PpaRecommendation(
                    category="power",
                    severity="medium",
                    title=f"Power proxy concentrates at stage '{stage_name}'",
                    rationale=(
                        f"Stage '{stage_name}' contributes {stage_stats.estimated_power_proxy:.2f} of "
                        f"{stats.estimated_power_proxy:.2f} total architecture power proxy ({share:.1%})."
                    ),
                    evidence={
                        "dominant_power_stage": stage_name,
                        "dominant_power_share": share,
                        "target_kind": "stage",
                        "target_name": stage_name,
                        "target_label": f"stage {stage_name}",
                        **_architecture_stage_evidence(stats, stage_name),
                    },
                    suggestions=_architecture_area_power_suggestions(model.stage(stage_name), bucket="power"),
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
        explicit_target = evidence.get("target_label") or evidence.get("rtl_anchor") or evidence.get("target_name")
        if isinstance(explicit_target, str) and explicit_target:
            target = explicit_target
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
        storage_candidate = _storage_transform_candidate(rec, target=target)
        if storage_candidate is not None:
            yield storage_candidate
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


def _storage_transform_candidate(
    rec: PpaRecommendation,
    *,
    target: str,
) -> Optional[PpaTransformCandidate]:
    evidence = rec.evidence
    memory_pattern = evidence.get("memory_pattern_hint")
    state_pattern = evidence.get("state_pattern_hint")
    if memory_pattern == "lut_rom":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce decoder duplication, simplify ROM access structure, or lower table power",
            rationale=rec.rationale,
            suggested_knob="table_layout",
            suggested_value="pack_rows_or_share_banks",
        )
    if memory_pattern == "fifo_queue_storage":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce FIFO payload storage overhead and improve queue payload density",
            rationale=rec.rationale,
            suggested_knob="storage_impl",
            suggested_value="compare_fifo_storage_impls",
        )
    if memory_pattern == "queue_metadata_arrays":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce duplicated shallow-array decode logic and keep lock-step queue metadata co-located",
            rationale=rec.rationale,
            suggested_knob="metadata_layout",
            suggested_value="bundle_queue_sideband_fields",
        )
    if memory_pattern == "control_register_bank":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce CSR storage fragmentation and simplify control-plane memory organization",
            rationale=rec.rationale,
            suggested_knob="register_layout",
            suggested_value="partition_or_pack_register_bank",
        )
    if memory_pattern == "small_ram":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce storage implementation overhead or enable denser macro inference",
            rationale=rec.rationale,
            suggested_knob="storage_impl",
            suggested_value="compare_ram_wrapper_vs_flops",
        )
    if memory_pattern == "many_small_tables":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce duplicated table decode logic and improve coefficient-table locality",
            rationale=rec.rationale,
            suggested_knob="table_consolidation",
            suggested_value="merge_related_tables",
        )
    if state_pattern == "register_file_rows":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce row-by-row flop cost and simplify explicit decode/update logic",
            rationale=rec.rationale,
            suggested_knob="storage_impl",
            suggested_value="register_file_to_ram_wrapper",
        )
    if state_pattern == "handshake_payload_state":
        if evidence.get("payload_gating_already_applied"):
            return None
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce idle payload toggling in protocol stages while keeping valid/ready control readable",
            rationale=rec.rationale,
            suggested_knob="payload_gating",
            suggested_value="update_payload_only_on_handshake",
        )
    if state_pattern == "register_bank_control_state":
        if evidence.get("control_partition_already_applied"):
            return None
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Keep protocol capture state shallow and isolate request/response bookkeeping",
            rationale=rec.rationale,
            suggested_knob="control_partition",
            suggested_value="split_capture_and_response_state",
        )
    if state_pattern == "multiplier_pipeline_state":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce unnecessary toggling in multiplier payload/valid pipeline state",
            rationale=rec.rationale,
            suggested_knob="pipeline_gating",
            suggested_value="gate_valid_and_payload_updates",
        )
    if state_pattern == "mac_pipeline_state":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce MAC staging activity and isolate accumulator updates from operand movement",
            rationale=rec.rationale,
            suggested_knob="pipeline_partition",
            suggested_value="split_stage_accumulate_and_operands",
        )
    multiplier_pattern = evidence.get("multiplier_pattern_hint")
    if multiplier_pattern == "signed_multiplier_pipeline":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Retain the handshake shell while shortening the product critical path or reducing idle toggling",
            rationale=rec.rationale,
            suggested_knob="pipeline_partition",
            suggested_value="retime_product_stages_keep_valid_shell",
        )
    if multiplier_pattern == "mac_style":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Separate product generation from accumulate updates and reduce unnecessary MAC staging activity",
            rationale=rec.rationale,
            suggested_knob="pipeline_partition",
            suggested_value="split_operands_product_accumulate",
        )
    if multiplier_pattern == "multi_multiplier_datapath":
        return PpaTransformCandidate(
            name=rec.title,
            category=rec.category,
            target=target,
            expected_benefit="Reduce monolithic multiplier timing pressure or share expensive arithmetic across mutually exclusive paths",
            rationale=rec.rationale,
            suggested_knob="multiplier_impl",
            suggested_value="tile_or_share_wide_multipliers",
        )
    return None


def _normalize_executable_module(module: Any, *, context: str) -> SimModule:
    if isinstance(module, SimModule):
        raise TypeError(
            f"{context} is a DSL-facing API and does not accept raw SimModule. "
            "Pass a rtlgen_x.dsl.Module instance, or pass the LoweredDslModule returned by "
            "lower_dsl_module_to_sim(...), not lowered.module."
        )
    if isinstance(module, LoweredDslModule):
        return module.module
    if hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks"):
        return lower_dsl_module_to_sim(module).module
    raise TypeError(
        f"{context} expects a rtlgen_x.dsl.Module or LoweredDslModule; "
        f"got {type(module)!r}"
    )
