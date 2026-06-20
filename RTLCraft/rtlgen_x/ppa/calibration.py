"""Calibration helpers for making PPA and architecture estimates more realistic."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from math import ceil, floor
from pathlib import Path
from statistics import fmean
from typing import Mapping, Optional, Sequence, Tuple

from rtlgen_x.archsim import ArchitectureModel, CalibrationTarget, Workload
from rtlgen_x.ppa.advisor import (
    ArchitecturePpaStats,
    FlowPpaStats,
    ModulePpaStats,
    analyze_architecture_ppa,
    analyze_module_ppa,
)
from rtlgen_x.ppa.reports import (
    AreaReportSummary,
    ImplementationReportBundle,
    PowerReportSummary,
    TimingReportSummary,
)


@dataclass(frozen=True)
class ModulePpaCalibrationSample:
    stats: ModulePpaStats
    timing: TimingReportSummary = field(default_factory=TimingReportSummary)
    area: AreaReportSummary = field(default_factory=AreaReportSummary)
    power: PowerReportSummary = field(default_factory=PowerReportSummary)
    source: str = "inline"


@dataclass(frozen=True)
class ModulePpaCalibrationModel:
    timing_ns_per_depth: Optional[float]
    area_per_score: Optional[float]
    power_mw_per_score: Optional[float]
    sample_count: int
    timing_sample_count: int
    area_sample_count: int
    power_sample_count: int
    sources: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "timing_ns_per_depth": self.timing_ns_per_depth,
            "area_per_score": self.area_per_score,
            "power_mw_per_score": self.power_mw_per_score,
            "sample_count": self.sample_count,
            "timing_sample_count": self.timing_sample_count,
            "area_sample_count": self.area_sample_count,
            "power_sample_count": self.power_sample_count,
            "sources": list(self.sources),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ModulePpaCalibrationModel":
        return cls(
            timing_ns_per_depth=_optional_float(payload.get("timing_ns_per_depth")),
            area_per_score=_optional_float(payload.get("area_per_score")),
            power_mw_per_score=_optional_float(payload.get("power_mw_per_score")),
            sample_count=int(payload.get("sample_count", 0)),
            timing_sample_count=int(payload.get("timing_sample_count", 0)),
            area_sample_count=int(payload.get("area_sample_count", 0)),
            power_sample_count=int(payload.get("power_sample_count", 0)),
            sources=tuple(payload.get("sources", ())),
        )

    def to_json_file(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ModulePpaCalibrationModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class CalibratedModulePpaEstimate:
    module_name: str
    critical_path_ns: Optional[float]
    fmax_mhz: Optional[float]
    total_area: Optional[float]
    total_power_mw: Optional[float]
    timing_score: float
    area_score: float
    power_score: float
    calibration_sample_count: int


@dataclass(frozen=True)
class ArchitecturePpaCalibrationSample:
    stats: ArchitecturePpaStats
    measured_total_cycles: Optional[float] = None
    measured_makespan_cycles: Optional[float] = None
    measured_flow_throughputs: Mapping[str, float] = field(default_factory=dict)
    measured_flow_stall_ratios: Mapping[str, float] = field(default_factory=dict)
    source: str = "inline"


@dataclass(frozen=True)
class ArchitecturePpaCalibrationModel:
    cycle_scale: float
    makespan_scale: float
    throughput_scale: float
    stall_scale: float
    sample_count: int
    cycle_sample_count: int
    makespan_sample_count: int
    throughput_sample_count: int
    stall_sample_count: int
    sources: Tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "cycle_scale": self.cycle_scale,
            "makespan_scale": self.makespan_scale,
            "throughput_scale": self.throughput_scale,
            "stall_scale": self.stall_scale,
            "sample_count": self.sample_count,
            "cycle_sample_count": self.cycle_sample_count,
            "makespan_sample_count": self.makespan_sample_count,
            "throughput_sample_count": self.throughput_sample_count,
            "stall_sample_count": self.stall_sample_count,
            "sources": list(self.sources),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ArchitecturePpaCalibrationModel":
        return cls(
            cycle_scale=float(payload.get("cycle_scale", 1.0)),
            makespan_scale=float(payload.get("makespan_scale", 1.0)),
            throughput_scale=float(payload.get("throughput_scale", 1.0)),
            stall_scale=float(payload.get("stall_scale", 1.0)),
            sample_count=int(payload.get("sample_count", 0)),
            cycle_sample_count=int(payload.get("cycle_sample_count", 0)),
            makespan_sample_count=int(payload.get("makespan_sample_count", 0)),
            throughput_sample_count=int(payload.get("throughput_sample_count", 0)),
            stall_sample_count=int(payload.get("stall_sample_count", 0)),
            sources=tuple(payload.get("sources", ())),
        )

    def to_json_file(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ArchitecturePpaCalibrationModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class CalibratedArchitectureFlowEstimate:
    name: str
    throughput_tokens_per_cycle: float
    total_cycles: float
    stall_ratio: float
    bottleneck_stage: Optional[str]


@dataclass(frozen=True)
class CalibratedArchitecturePpaEstimate:
    total_cycles: float
    makespan_cycles: float
    flow_estimates: Mapping[str, CalibratedArchitectureFlowEstimate]
    cycle_scale: float
    makespan_scale: float
    throughput_scale: float
    stall_scale: float
    calibration_sample_count: int


def build_module_ppa_calibration_sample(
    module,
    reports: ImplementationReportBundle,
) -> ModulePpaCalibrationSample:
    return ModulePpaCalibrationSample(
        stats=analyze_module_ppa(module),
        timing=reports.timing,
        area=reports.area,
        power=reports.power,
        source=";".join(reports.sources) if reports.sources else "implementation_reports",
    )


def fit_module_ppa_calibration(
    samples: Sequence[ModulePpaCalibrationSample],
) -> ModulePpaCalibrationModel:
    if not samples:
        raise ValueError("module calibration requires at least one sample")
    timing_ratios = [
        sample.timing.critical_path_ns / _module_timing_score(sample.stats)
        for sample in samples
        if sample.timing.critical_path_ns is not None and _module_timing_score(sample.stats) > 0
    ]
    area_ratios = [
        sample.area.total_area / _module_area_score(sample.stats)
        for sample in samples
        if sample.area.total_area is not None and _module_area_score(sample.stats) > 0
    ]
    power_ratios = [
        sample.power.total_mw / _module_power_score(sample.stats)
        for sample in samples
        if sample.power.total_mw is not None and _module_power_score(sample.stats) > 0
    ]
    return ModulePpaCalibrationModel(
        timing_ns_per_depth=fmean(timing_ratios) if timing_ratios else None,
        area_per_score=fmean(area_ratios) if area_ratios else None,
        power_mw_per_score=fmean(power_ratios) if power_ratios else None,
        sample_count=len(samples),
        timing_sample_count=len(timing_ratios),
        area_sample_count=len(area_ratios),
        power_sample_count=len(power_ratios),
        sources=tuple(sample.source for sample in samples),
    )


def estimate_calibrated_module_ppa(
    module_or_stats,
    calibration: ModulePpaCalibrationModel,
) -> CalibratedModulePpaEstimate:
    stats = module_or_stats if isinstance(module_or_stats, ModulePpaStats) else analyze_module_ppa(module_or_stats)
    timing_score = _module_timing_score(stats)
    area_score = _module_area_score(stats)
    power_score = _module_power_score(stats)
    critical_path_ns = (
        timing_score * calibration.timing_ns_per_depth
        if calibration.timing_ns_per_depth is not None
        else None
    )
    fmax_mhz = 1000.0 / critical_path_ns if critical_path_ns not in (None, 0) else None
    total_area = area_score * calibration.area_per_score if calibration.area_per_score is not None else None
    total_power_mw = (
        power_score * calibration.power_mw_per_score
        if calibration.power_mw_per_score is not None
        else None
    )
    return CalibratedModulePpaEstimate(
        module_name=stats.module_name,
        critical_path_ns=critical_path_ns,
        fmax_mhz=fmax_mhz,
        total_area=total_area,
        total_power_mw=total_power_mw,
        timing_score=timing_score,
        area_score=area_score,
        power_score=power_score,
        calibration_sample_count=calibration.sample_count,
    )


def build_architecture_ppa_calibration_sample(
    model: ArchitectureModel,
    workload: Workload,
    *,
    measured_total_cycles: Optional[float] = None,
    measured_makespan_cycles: Optional[float] = None,
    measured_flow_throughputs: Optional[Mapping[str, float]] = None,
    measured_flow_stall_ratios: Optional[Mapping[str, float]] = None,
) -> ArchitecturePpaCalibrationSample:
    return ArchitecturePpaCalibrationSample(
        stats=analyze_architecture_ppa(model, workload),
        measured_total_cycles=measured_total_cycles,
        measured_makespan_cycles=measured_makespan_cycles,
        measured_flow_throughputs=dict(measured_flow_throughputs or {}),
        measured_flow_stall_ratios=dict(measured_flow_stall_ratios or {}),
        source="architecture_measurements",
    )


def fit_architecture_ppa_calibration(
    samples: Sequence[ArchitecturePpaCalibrationSample],
) -> ArchitecturePpaCalibrationModel:
    if not samples:
        raise ValueError("architecture calibration requires at least one sample")
    cycle_scales = [
        sample.measured_total_cycles / sample.stats.total_cycles
        for sample in samples
        if sample.measured_total_cycles is not None and sample.stats.total_cycles > 0
    ]
    makespan_scales = [
        sample.measured_makespan_cycles / sample.stats.makespan_cycles
        for sample in samples
        if sample.measured_makespan_cycles is not None and sample.stats.makespan_cycles > 0
    ]
    throughput_scales = []
    stall_scales = []
    for sample in samples:
        for flow_name, measured in sample.measured_flow_throughputs.items():
            simulated = sample.stats.flow_stats.get(flow_name)
            if simulated is None or simulated.throughput_tokens_per_cycle <= 0:
                continue
            throughput_scales.append(measured / simulated.throughput_tokens_per_cycle)
        for flow_name, measured in sample.measured_flow_stall_ratios.items():
            simulated = sample.stats.flow_stats.get(flow_name)
            if simulated is None:
                continue
            if simulated.stall_ratio == 0:
                if measured == 0:
                    stall_scales.append(1.0)
                continue
            stall_scales.append(measured / simulated.stall_ratio)
    return ArchitecturePpaCalibrationModel(
        cycle_scale=fmean(cycle_scales) if cycle_scales else 1.0,
        makespan_scale=fmean(makespan_scales) if makespan_scales else 1.0,
        throughput_scale=fmean(throughput_scales) if throughput_scales else 1.0,
        stall_scale=fmean(stall_scales) if stall_scales else 1.0,
        sample_count=len(samples),
        cycle_sample_count=len(cycle_scales),
        makespan_sample_count=len(makespan_scales),
        throughput_sample_count=len(throughput_scales),
        stall_sample_count=len(stall_scales),
        sources=tuple(sample.source for sample in samples),
    )


def estimate_calibrated_architecture_ppa(
    *,
    calibration: ArchitecturePpaCalibrationModel,
    stats: Optional[ArchitecturePpaStats] = None,
    model: Optional[ArchitectureModel] = None,
    workload: Optional[Workload] = None,
) -> CalibratedArchitecturePpaEstimate:
    if stats is None:
        if model is None or workload is None:
            raise ValueError("provide either stats or both model and workload")
        stats = analyze_architecture_ppa(model, workload)
    flow_estimates = {
        flow_name: CalibratedArchitectureFlowEstimate(
            name=flow.name,
            throughput_tokens_per_cycle=max(0.0, flow.throughput_tokens_per_cycle * calibration.throughput_scale),
            total_cycles=flow.total_cycles * calibration.cycle_scale,
            stall_ratio=max(flow.stall_ratio * calibration.stall_scale, 0.0),
            bottleneck_stage=flow.bottleneck_stage,
        )
        for flow_name, flow in stats.flow_stats.items()
    }
    return CalibratedArchitecturePpaEstimate(
        total_cycles=stats.total_cycles * calibration.cycle_scale,
        makespan_cycles=stats.makespan_cycles * calibration.makespan_scale,
        flow_estimates=flow_estimates,
        cycle_scale=calibration.cycle_scale,
        makespan_scale=calibration.makespan_scale,
        throughput_scale=calibration.throughput_scale,
        stall_scale=calibration.stall_scale,
        calibration_sample_count=calibration.sample_count,
    )


def derive_architecture_calibration_targets(
    model: ArchitectureModel,
    sample: ArchitecturePpaCalibrationSample,
    *,
    throughput_tolerance: float = 0.05,
    cycle_tolerance: float = 0.05,
    stall_tolerance: float = 0.10,
) -> Tuple[CalibrationTarget, ...]:
    """Turn measured-vs-simulated deltas into stage override targets.

    The intent is lightweight feedback: when measured behavior diverges from the
    architecture simulator, provide the agent with a first set of stage knobs to
    re-run against `calibrate_architecture_model(...)`.
    """

    if throughput_tolerance < 0 or cycle_tolerance < 0 or stall_tolerance < 0:
        raise ValueError("tolerances must be non-negative")

    cycle_scales = []
    if sample.measured_total_cycles is not None and sample.stats.total_cycles > 0:
        cycle_scales.append(sample.measured_total_cycles / sample.stats.total_cycles)
    if sample.measured_makespan_cycles is not None and sample.stats.makespan_cycles > 0:
        cycle_scales.append(sample.measured_makespan_cycles / sample.stats.makespan_cycles)
    aggregate_cycle_scale = fmean(cycle_scales) if cycle_scales else 1.0

    stage_targets: dict[str, dict[str, int]] = {}
    for flow_name, flow_stats in sample.stats.flow_stats.items():
        stage_name = flow_stats.bottleneck_stage
        if not stage_name or stage_name not in model.stages:
            continue
        stage = model.stage(stage_name)
        stage_target = stage_targets.setdefault(stage_name, {})

        measured_throughput = sample.measured_flow_throughputs.get(flow_name)
        if measured_throughput is not None and flow_stats.throughput_tokens_per_cycle > 0:
            throughput_ratio = measured_throughput / flow_stats.throughput_tokens_per_cycle
            if abs(throughput_ratio - 1.0) > throughput_tolerance:
                if stage.bandwidth_bytes_per_cycle > 0 and stage.kind in {"memory", "interconnect", "datapath"}:
                    candidate = _scale_bandwidth(stage.bandwidth_bytes_per_cycle, throughput_ratio)
                    if candidate != stage.bandwidth_bytes_per_cycle:
                        stage_target["bandwidth_bytes_per_cycle"] = _merge_stage_override(
                            stage_target.get("bandwidth_bytes_per_cycle"),
                            candidate,
                            prefer_larger=throughput_ratio > 1.0,
                        )
                else:
                    candidate = _scale_initiation_interval(stage.initiation_interval, throughput_ratio)
                    if candidate != stage.initiation_interval:
                        stage_target["initiation_interval"] = _merge_stage_override(
                            stage_target.get("initiation_interval"),
                            candidate,
                            prefer_larger=throughput_ratio < 1.0,
                        )

        if abs(aggregate_cycle_scale - 1.0) > cycle_tolerance:
            candidate = _scale_latency(stage.latency, aggregate_cycle_scale)
            if candidate != stage.latency:
                stage_target["latency"] = _merge_stage_override(
                    stage_target.get("latency"),
                    candidate,
                    prefer_larger=aggregate_cycle_scale > 1.0,
                )

        measured_stall = sample.measured_flow_stall_ratios.get(flow_name)
        current_queue_depth = model.queue_capacity(stage_name)
        if measured_stall is not None:
            if flow_stats.stall_ratio == 0:
                stall_scale = 2.0 if measured_stall > 0 else 1.0
            elif measured_stall == 0:
                stall_scale = 0.5
            else:
                stall_scale = measured_stall / flow_stats.stall_ratio
            if abs(stall_scale - 1.0) > stall_tolerance:
                candidate = _scale_queue_depth(current_queue_depth, stall_scale)
                if candidate != current_queue_depth:
                    stage_target["queue_depth"] = _merge_stage_override(
                        stage_target.get("queue_depth"),
                        candidate,
                        prefer_larger=stall_scale < 1.0,
                    )

    return tuple(
        CalibrationTarget(
            stage_name=stage_name,
            latency=overrides.get("latency"),
            initiation_interval=overrides.get("initiation_interval"),
            queue_depth=overrides.get("queue_depth"),
            bandwidth_bytes_per_cycle=overrides.get("bandwidth_bytes_per_cycle"),
        )
        for stage_name, overrides in sorted(stage_targets.items())
        if overrides
    )


def _module_timing_score(stats: ModulePpaStats) -> float:
    return float(max(stats.max_expr_depth, 1))


def _module_area_score(stats: ModulePpaStats) -> float:
    return max(
        (
            stats.state_bits
            + 0.125 * stats.memory_bits
            + 0.25 * (stats.input_bits + stats.output_bits)
            + 24.0 * stats.arithmetic_ops
            + 10.0 * stats.compare_ops
            + 14.0 * stats.mux_ops
            + 8.0 * stats.memory_writes
            + 6.0 * stats.comb_assignments
            + 4.0 * stats.seq_assignments
        ),
        1.0,
    )


def _module_power_score(stats: ModulePpaStats) -> float:
    return max(
        (
            0.02 * stats.state_bits
            + 0.002 * stats.memory_bits
            + 0.2 * stats.arithmetic_ops
            + 0.08 * stats.compare_ops
            + 0.1 * stats.mux_ops
            + 0.04 * stats.memory_writes
        ),
        1.0,
    )


def _merge_stage_override(
    current: Optional[int],
    candidate: int,
    *,
    prefer_larger: bool,
) -> int:
    if current is None:
        return candidate
    return max(current, candidate) if prefer_larger else min(current, candidate)


def _scale_latency(base: int, ratio: float) -> int:
    if ratio >= 1.0:
        return max(1, int(ceil(base * ratio)))
    return max(1, int(floor(base * ratio)))


def _scale_initiation_interval(base: int, throughput_ratio: float) -> int:
    safe_ratio = max(throughput_ratio, 1e-9)
    raw = base / safe_ratio
    if throughput_ratio >= 1.0:
        return max(1, int(floor(raw)))
    return max(1, int(ceil(raw)))


def _scale_bandwidth(base: int, throughput_ratio: float) -> int:
    safe_ratio = max(throughput_ratio, 1e-9)
    raw = base * safe_ratio
    if throughput_ratio >= 1.0:
        return max(1, int(ceil(raw)))
    return max(1, int(floor(raw)))


def _scale_queue_depth(base: int, stall_scale: float) -> int:
    safe_scale = max(stall_scale, 1e-9)
    raw = base / safe_scale
    if stall_scale >= 1.0:
        return max(1, int(floor(raw)))
    return max(1, int(ceil(raw)))


def _optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    return float(value)
