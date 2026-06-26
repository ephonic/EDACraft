"""Minimal GPGPU software-stack ABI and workload-bridge objects.

This module deliberately starts small. The immediate goal is not a complete
runtime/compiler stack, but a stable set of explicit software-side artifacts
that can:

1. describe a kernel launch
2. describe command/dispatch intent
3. describe a workload trace
4. bridge that workload trace into ``rtlgen_x.archsim.Workload``
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Mapping, Optional, Tuple

from rtlgen_x.archsim import FlowSpec, Workload


def _normalize_metadata(metadata: Optional[Mapping[str, object]]) -> dict[str, object]:
    return dict(metadata or {})


@dataclass(frozen=True)
class KernelMetadata:
    """Kernel-side launch metadata understood by the software stack."""

    kernel_name: str
    grid_dim: Tuple[int, int, int] = (1, 1, 1)
    block_dim: Tuple[int, int, int] = (1, 1, 1)
    shared_mem_bytes: int = 0
    register_count: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.kernel_name:
            raise ValueError("kernel_name must not be empty")
        if len(self.grid_dim) != 3 or any(int(v) < 1 for v in self.grid_dim):
            raise ValueError("grid_dim must contain exactly three positive integers")
        if len(self.block_dim) != 3 or any(int(v) < 1 for v in self.block_dim):
            raise ValueError("block_dim must contain exactly three positive integers")
        if self.shared_mem_bytes < 0:
            raise ValueError("shared_mem_bytes must be >= 0")
        if self.register_count < 0:
            raise ValueError("register_count must be >= 0")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["grid_dim"] = list(self.grid_dim)
        payload["block_dim"] = list(self.block_dim)
        payload["metadata"] = _normalize_metadata(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "KernelMetadata":
        return cls(
            kernel_name=str(payload["kernel_name"]),
            grid_dim=tuple(int(v) for v in payload.get("grid_dim", (1, 1, 1))),
            block_dim=tuple(int(v) for v in payload.get("block_dim", (1, 1, 1))),
            shared_mem_bytes=int(payload.get("shared_mem_bytes", 0)),
            register_count=int(payload.get("register_count", 0)),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class KernelLaunch:
    """One software-visible kernel launch instance."""

    metadata: KernelMetadata
    launch_id: str
    args: Mapping[str, int] = field(default_factory=dict)
    metadata_overrides: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.launch_id:
            raise ValueError("launch_id must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": self.metadata.to_dict(),
            "launch_id": self.launch_id,
            "args": dict(self.args),
            "metadata_overrides": _normalize_metadata(self.metadata_overrides),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "KernelLaunch":
        return cls(
            metadata=KernelMetadata.from_dict(payload["metadata"]),
            launch_id=str(payload["launch_id"]),
            args={str(k): int(v) for k, v in dict(payload.get("args", {})).items()},
            metadata_overrides=_normalize_metadata(payload.get("metadata_overrides")),
        )


@dataclass(frozen=True)
class CommandDescriptor:
    """A minimal command/dispatch descriptor for a future command processor."""

    opcode: str
    launch: KernelLaunch
    queue: str = "compute"
    priority: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.opcode:
            raise ValueError("opcode must not be empty")
        if not self.queue:
            raise ValueError("queue must not be empty")
        if self.priority < 0:
            raise ValueError("priority must be >= 0")

    def to_dict(self) -> dict[str, object]:
        return {
            "opcode": self.opcode,
            "launch": self.launch.to_dict(),
            "queue": self.queue,
            "priority": self.priority,
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "CommandDescriptor":
        return cls(
            opcode=str(payload["opcode"]),
            launch=KernelLaunch.from_dict(payload["launch"]),
            queue=str(payload.get("queue", "compute")),
            priority=int(payload.get("priority", 0)),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class AddressRegion:
    """One software-visible address-map region."""

    name: str
    base: int
    size_bytes: int
    kind: str = "memory"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.base < 0:
            raise ValueError("base must be >= 0")
        if self.size_bytes < 1:
            raise ValueError("size_bytes must be >= 1")
        if self.kind not in {"memory", "mmio", "csr", "scratchpad", "descriptor"}:
            raise ValueError(f"unsupported region kind '{self.kind}'")

    @property
    def end(self) -> int:
        return self.base + self.size_bytes

    def contains(self, address: int) -> bool:
        return self.base <= address < self.end

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "base": self.base,
            "size_bytes": self.size_bytes,
            "kind": self.kind,
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "AddressRegion":
        return cls(
            name=str(payload["name"]),
            base=int(payload["base"]),
            size_bytes=int(payload["size_bytes"]),
            kind=str(payload.get("kind", "memory")),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class AddressMap:
    """Minimal software-visible address map shared with hardware."""

    regions: Tuple[AddressRegion, ...]
    name: str = "addr_map0"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.regions:
            raise ValueError("regions must not be empty")
        seen = set()
        for region in self.regions:
            if region.name in seen:
                raise ValueError(f"duplicate region name '{region.name}'")
            seen.add(region.name)
        ordered = sorted(self.regions, key=lambda region: (region.base, region.end))
        for left, right in zip(ordered, ordered[1:]):
            if left.end > right.base:
                raise ValueError(
                    f"address regions '{left.name}' and '{right.name}' overlap"
                )

    def region(self, name: str) -> AddressRegion:
        for region in self.regions:
            if region.name == name:
                return region
        raise KeyError(f"unknown region '{name}'")

    def find_region(self, address: int) -> Optional[AddressRegion]:
        for region in self.regions:
            if region.contains(address):
                return region
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "regions": [region.to_dict() for region in self.regions],
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "AddressMap":
        return cls(
            name=str(payload.get("name", "addr_map0")),
            regions=tuple(
                AddressRegion.from_dict(region)
                for region in payload.get("regions", ())
            ),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class PerfCounterSpec:
    """One software-visible performance counter definition."""

    name: str
    width_bits: int = 64
    category: str = "throughput"
    description: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if self.width_bits < 1:
            raise ValueError("width_bits must be >= 1")
        if self.category not in {
            "throughput",
            "stall",
            "memory",
            "latency",
            "occupancy",
            "custom",
        }:
            raise ValueError(f"unsupported counter category '{self.category}'")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "width_bits": self.width_bits,
            "category": self.category,
            "description": self.description,
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "PerfCounterSpec":
        return cls(
            name=str(payload["name"]),
            width_bits=int(payload.get("width_bits", 64)),
            category=str(payload.get("category", "throughput")),
            description=str(payload.get("description", "")),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class PerfCounterSchema:
    """Minimal software-visible performance-counter schema."""

    counters: Tuple[PerfCounterSpec, ...]
    schema_id: str = "perf0"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.schema_id:
            raise ValueError("schema_id must not be empty")
        if not self.counters:
            raise ValueError("counters must not be empty")
        seen = set()
        for counter in self.counters:
            if counter.name in seen:
                raise ValueError(f"duplicate counter name '{counter.name}'")
            seen.add(counter.name)

    def counter(self, name: str) -> PerfCounterSpec:
        for counter in self.counters:
            if counter.name == name:
                return counter
        raise KeyError(f"unknown counter '{name}'")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "counters": [counter.to_dict() for counter in self.counters],
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "PerfCounterSchema":
        return cls(
            schema_id=str(payload.get("schema_id", "perf0")),
            counters=tuple(
                PerfCounterSpec.from_dict(counter)
                for counter in payload.get("counters", ())
            ),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class WorkloadTraceEvent:
    """One software-side workload event that can feed architecture simulation."""

    flow_name: str
    path: Tuple[str, ...]
    tokens: int
    bytes_per_token: int = 0
    start_cycle: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.flow_name:
            raise ValueError("flow_name must not be empty")
        if not self.path:
            raise ValueError("path must not be empty")
        if self.tokens < 1:
            raise ValueError("tokens must be >= 1")
        if self.bytes_per_token < 0:
            raise ValueError("bytes_per_token must be >= 0")
        if self.start_cycle < 0:
            raise ValueError("start_cycle must be >= 0")

    def to_flow_spec(self) -> FlowSpec:
        return FlowSpec(
            name=self.flow_name,
            path=self.path,
            tokens=self.tokens,
            bytes_per_token=self.bytes_per_token,
            start_cycle=self.start_cycle,
            metadata=_normalize_metadata(self.metadata),
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["path"] = list(self.path)
        payload["metadata"] = _normalize_metadata(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "WorkloadTraceEvent":
        return cls(
            flow_name=str(payload["flow_name"]),
            path=tuple(str(v) for v in payload["path"]),
            tokens=int(payload.get("tokens", 1)),
            bytes_per_token=int(payload.get("bytes_per_token", 0)),
            start_cycle=int(payload.get("start_cycle", 0)),
            metadata=_normalize_metadata(payload.get("metadata")),
        )


@dataclass(frozen=True)
class WorkloadTrace:
    """A software-side trace bundle that can be bridged into archsim."""

    kernel: KernelMetadata
    events: Tuple[WorkloadTraceEvent, ...]
    trace_id: str = "trace0"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise ValueError("trace_id must not be empty")
        if not self.events:
            raise ValueError("events must not be empty")
        seen = set()
        for event in self.events:
            if event.flow_name in seen:
                raise ValueError(f"duplicate flow_name '{event.flow_name}' in workload trace")
            seen.add(event.flow_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "kernel": self.kernel.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "trace_id": self.trace_id,
            "metadata": _normalize_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "WorkloadTrace":
        return cls(
            kernel=KernelMetadata.from_dict(payload["kernel"]),
            events=tuple(
                WorkloadTraceEvent.from_dict(event)
                for event in payload.get("events", ())
            ),
            trace_id=str(payload.get("trace_id", "trace0")),
            metadata=_normalize_metadata(payload.get("metadata")),
        )

    def to_json_file(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def from_json_file(cls, path: str | Path) -> "WorkloadTrace":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def workload_trace_to_archsim_workload(trace: WorkloadTrace) -> Workload:
    """Convert a software-side workload trace into ``rtlgen_x.archsim.Workload``."""

    return Workload.from_flows(*(event.to_flow_spec() for event in trace.events))
