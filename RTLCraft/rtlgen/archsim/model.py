"""Shared model objects for lightweight architecture simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
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

    def to_dict(self) -> dict[str, object]:
        return {"flows": [asdict(flow) for flow in self.flows]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Workload":
        flows = tuple(
            FlowSpec(
                name=str(flow["name"]),
                path=tuple(flow["path"]),
                tokens=int(flow.get("tokens", 1)),
                bytes_per_token=int(flow.get("bytes_per_token", 0)),
                start_cycle=int(flow.get("start_cycle", 0)),
                metadata=dict(flow.get("metadata", {})),
            )
            for flow in payload.get("flows", ())
        )
        return cls(flows=flows)

    def to_json_file(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Workload":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


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

    def to_dict(self) -> dict[str, object]:
        return {"stages": [asdict(stage) for stage in self._stages.values()]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ArchitectureModel":
        return cls(
            StageSpec(
                name=str(stage["name"]),
                kind=str(stage.get("kind", "compute")),
                latency=int(stage.get("latency", 1)),
                initiation_interval=int(stage.get("initiation_interval", 1)),
                capacity=int(stage.get("capacity", 1)),
                queue_depth=int(stage.get("queue_depth", 0)),
                bandwidth_bytes_per_cycle=int(stage.get("bandwidth_bytes_per_cycle", 0)),
                metadata=dict(stage.get("metadata", {})),
            )
            for stage in payload.get("stages", ())
        )

    def to_json_file(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ArchitectureModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

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

    def shared_resource_tag(self, stage_name: str) -> Optional[str]:
        """Return the contention-group tag for one stage, if any."""

        stage = self.stage(stage_name)
        tag = stage.metadata.get("shared_resource")
        if tag is None:
            return None
        text = str(tag).strip()
        return text or None

    def stage_contention_capacity(self, stage_name: str) -> int:
        """Return effective service slots after shared-resource grouping.

        By default each stage contends only with itself. When multiple stages
        share the same non-empty ``metadata['shared_resource']`` tag, they are
        treated as consuming a common aggregate service budget equal to the sum
        of the grouped stage capacities. This is intentionally lightweight: it
        does not try to model arbitration policies, only the fact that several
        micro-stages are backed by one broader resource pool.
        """

        tag = self.shared_resource_tag(stage_name)
        if tag is None:
            return self.stage(stage_name).capacity
        total = 0
        for other in self._stages.values():
            other_tag = other.metadata.get("shared_resource")
            if other_tag is not None and str(other_tag).strip() == tag:
                total += other.capacity
        return max(total, self.stage(stage_name).capacity)

    def shared_resource_groups(self) -> Dict[str, Tuple[str, ...]]:
        """Return stage-name groups keyed by shared-resource tag."""

        groups: Dict[str, list[str]] = {}
        for stage in self._stages.values():
            tag = self.shared_resource_tag(stage.name)
            if tag is None:
                continue
            groups.setdefault(tag, []).append(stage.name)
        return {
            tag: tuple(names)
            for tag, names in groups.items()
            if len(names) > 1
        }

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
            service_ii = self.stage_service_initiation_interval(stage_name, flow) / self.stage_contention_capacity(stage_name)
            if service_ii > worst_ii:
                worst_ii = service_ii
                worst_name = stage_name
        return worst_name
