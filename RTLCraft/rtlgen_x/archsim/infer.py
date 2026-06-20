"""Inference and calibration helpers for architecture simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from rtlgen_x.archsim.model import ArchitectureModel, FlowSpec, StageSpec
from rtlgen_x.sim import SimModule


@dataclass(frozen=True)
class CalibrationTarget:
    stage_name: str
    latency: Optional[int] = None
    initiation_interval: Optional[int] = None
    capacity: Optional[int] = None
    queue_depth: Optional[int] = None
    bandwidth_bytes_per_cycle: Optional[int] = None


def infer_architecture_from_module(
    module: SimModule,
    *,
    prefix: Optional[str] = None,
) -> ArchitectureModel:
    prefix = prefix or module.name
    comb_count = sum(1 for assignment in module.assignments if assignment.phase == "comb")
    seq_count = sum(1 for assignment in module.assignments if assignment.phase == "seq")
    input_signals = tuple(signal for signal in module.signals if signal.kind == "input")
    stages = []
    if input_signals:
        stages.append(
            StageSpec(
                f"{prefix}_ingress",
                kind="control",
                latency=1,
                initiation_interval=1,
                capacity=max(1, min(4, len(input_signals))),
                queue_depth=max(1, len(input_signals)),
                metadata={"inferred_from": "inputs"},
            )
        )
    if module.memories:
        stages.append(
            StageSpec(
                f"{prefix}_memory",
                kind="memory",
                latency=max(2, len(module.memories)),
                initiation_interval=1,
                capacity=max(1, len(module.memories)),
                queue_depth=max(2, len(module.memories) * 2),
                bandwidth_bytes_per_cycle=max(16, len(module.memories) * 16),
                metadata={"inferred_from": "memories"},
            )
        )
    stages.append(
        StageSpec(
            f"{prefix}_compute",
            kind="compute",
            latency=max(1, min(8, comb_count)),
            initiation_interval=max(1, min(4, seq_count or 1)),
            capacity=max(1, min(4, max(1, comb_count // 2 or 1))),
            queue_depth=max(1, seq_count or 1),
            metadata={"inferred_from": "assignments"},
        )
    )
    stages.append(
        StageSpec(
            f"{prefix}_egress",
            kind="datapath",
            latency=1,
            initiation_interval=1,
            capacity=max(1, len(module.outputs)),
            queue_depth=max(1, len(module.outputs)),
            bandwidth_bytes_per_cycle=max(8, sum(module.signal_map()[name].width for name in module.outputs) // 8 or 1),
            metadata={"inferred_from": "outputs"},
        )
    )
    return ArchitectureModel(stages)


def infer_flow_from_module(
    module: SimModule,
    *,
    tokens: int = 8,
    bytes_per_token: int = 0,
    prefix: Optional[str] = None,
) -> FlowSpec:
    prefix = prefix or module.name
    input_signals = tuple(signal for signal in module.signals if signal.kind == "input")
    path = []
    if input_signals:
        path.append(f"{prefix}_ingress")
    if module.memories:
        path.append(f"{prefix}_memory")
    path.extend((f"{prefix}_compute", f"{prefix}_egress"))
    return FlowSpec(
        f"{prefix}_flow",
        path=tuple(path),
        tokens=tokens,
        bytes_per_token=bytes_per_token,
    )


def calibrate_architecture_model(
    model: ArchitectureModel,
    targets: Sequence[CalibrationTarget],
) -> ArchitectureModel:
    target_map = {target.stage_name: target for target in targets}
    calibrated = []
    for stage_name, stage in model.stages.items():
        target = target_map.get(stage_name)
        if target is None:
            calibrated.append(stage)
            continue
        calibrated.append(
            StageSpec(
                name=stage.name,
                kind=stage.kind,
                latency=target.latency if target.latency is not None else stage.latency,
                initiation_interval=target.initiation_interval if target.initiation_interval is not None else stage.initiation_interval,
                capacity=target.capacity if target.capacity is not None else stage.capacity,
                queue_depth=target.queue_depth if target.queue_depth is not None else stage.queue_depth,
                bandwidth_bytes_per_cycle=(
                    target.bandwidth_bytes_per_cycle
                    if target.bandwidth_bytes_per_cycle is not None
                    else stage.bandwidth_bytes_per_cycle
                ),
                metadata=dict(stage.metadata),
            )
        )
    return ArchitectureModel(calibrated)
