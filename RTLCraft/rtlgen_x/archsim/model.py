"""Shared model objects for lightweight architecture simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Tuple


_ALLOWED_STAGE_KINDS = {
    "compute",
    "memory",
    "control",
    "interconnect",
    "datapath",
    "custom",
}

_BANDWIDTH_LIMITED_STAGE_KINDS = {
    "memory",
    "interconnect",
    "datapath",
}


@dataclass(frozen=True)
class StageSpec:
    """One architectural stage or shared resource shell."""

    name: str
    kind: str = "compute"
    latency: int = 1
    initiation_interval: int = 1
    capacity: int = 1
    queue_depth: int = 0
    bandwidth_bytes_per_cycle: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("stage name must not be empty")
        if self.kind not in _ALLOWED_STAGE_KINDS:
            raise ValueError(f"unsupported stage kind '{self.kind}'")
        if self.latency < 1:
            raise ValueError("stage latency must be >= 1")
        if self.initiation_interval < 1:
            raise ValueError("stage initiation_interval must be >= 1")
        if self.capacity < 1:
            raise ValueError("stage capacity must be >= 1")
        if self.queue_depth < 0:
            raise ValueError("stage queue_depth must be >= 0")
        if self.bandwidth_bytes_per_cycle < 0:
            raise ValueError("stage bandwidth_bytes_per_cycle must be >= 0")


@dataclass(frozen=True)
class FlowSpec:
    """A generic architectural flow through shared stage primitives."""

    name: str
    path: Tuple[str, ...]
    tokens: int = 1
    bytes_per_token: int = 0
    start_cycle: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("flow name must not be empty")
        if not self.path:
            raise ValueError("flow path must not be empty")
        if self.tokens < 1:
            raise ValueError("flow tokens must be >= 1")
        if self.bytes_per_token < 0:
            raise ValueError("flow bytes_per_token must be >= 0")
        if self.start_cycle < 0:
            raise ValueError("flow start_cycle must be >= 0")


@dataclass(frozen=True)
class Workload:
    """A named collection of flows for architecture-level simulation."""

    flows: Tuple[FlowSpec, ...]

    def __post_init__(self) -> None:
        if not self.flows:
            raise ValueError("workload must contain at least one flow")
        seen = set()
        for flow in self.flows:
            if flow.name in seen:
                raise ValueError(f"duplicate flow name '{flow.name}'")
            seen.add(flow.name)

    @classmethod
    def from_flows(cls, *flows: FlowSpec) -> "Workload":
        return cls(flows=tuple(flows))


class ArchitectureModel:
    """Lightweight architecture model shared by behavior and cycle simulation."""

    def __init__(self, stages: Iterable[StageSpec]):
        stage_map: Dict[str, StageSpec] = {}
        for stage in stages:
            if stage.name in stage_map:
                raise ValueError(f"duplicate stage '{stage.name}'")
            stage_map[stage.name] = stage
        if not stage_map:
            raise ValueError("architecture model requires at least one stage")
        self._stages = stage_map

    @property
    def stages(self) -> Dict[str, StageSpec]:
        return dict(self._stages)

    def stage(self, name: str) -> StageSpec:
        try:
            return self._stages[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"unknown stage '{name}'") from exc

    def validate_flow(self, flow: FlowSpec) -> None:
        for stage_name in flow.path:
            if stage_name not in self._stages:
                raise KeyError(f"flow '{flow.name}' references unknown stage '{stage_name}'")

    def validate_workload(self, workload: Workload) -> None:
        for flow in workload.flows:
            self.validate_flow(flow)

    def queue_capacity(self, stage_name: str) -> int:
        stage = self.stage(stage_name)
        return stage.queue_depth if stage.queue_depth > 0 else stage.capacity

    def stage_service_initiation_interval(self, stage_name: str, flow: FlowSpec) -> int:
        """Return the effective service II for one flow at one stage."""

        self.validate_flow(flow)
        stage = self.stage(stage_name)
        service_ii = stage.initiation_interval
        if (
            flow.bytes_per_token > 0
            and stage.bandwidth_bytes_per_cycle > 0
            and stage.kind in _BANDWIDTH_LIMITED_STAGE_KINDS
        ):
            bandwidth_ii = (
                flow.bytes_per_token + stage.bandwidth_bytes_per_cycle - 1
            ) // stage.bandwidth_bytes_per_cycle
            service_ii = max(service_ii, bandwidth_ii)
        return service_ii

    def path_latency(self, flow: FlowSpec) -> int:
        self.validate_flow(flow)
        return sum(self.stage(stage_name).latency for stage_name in flow.path)

    def bottleneck_stage(self, flow: FlowSpec) -> Optional[str]:
        self.validate_flow(flow)
        worst_name = None
        worst_ii = -1.0
        for stage_name in flow.path:
            stage = self.stage(stage_name)
            service_ii = self.stage_service_initiation_interval(stage_name, flow) / stage.capacity
            if service_ii > worst_ii:
                worst_ii = service_ii
                worst_name = stage_name
        return worst_name
