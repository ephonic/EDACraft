"""Layer contracts — L1(Spec)/L2(Plan)/L3(Exec) interface definitions.

Each tool call is annotated with its source layer and a trace ID,
enabling problem attribution across the three representation layers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List


class Layer(IntEnum):
    """The three design representation layers."""

    L1_SPEC = 1
    L2_PLAN = 2
    L3_EXEC = 3
    UNKNOWN = 0


@dataclass
class AnnotatedToolCall:
    """A tool call annotated with source layer and trace ID."""

    layer: Layer
    tool_name: str
    args: Dict[str, Any]
    trace_id: str = ""
    retry_count: int = 0
    summary: str = ""

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]


@dataclass
class L1ToL2:
    """Contract: L1 (Spec) → L2 (Plan)."""

    spec: Any
    task_description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]


@dataclass
class L2ToL3:
    """Contract: L2 (Plan) → L3 (Exec)."""

    plan: Any
    task_sequence: List[Dict[str, Any]] = field(default_factory=list)
    rollback_strategy: str = "retry"
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]


class LayerTracer:
    """Records annotated tool calls for full execution path reconstruction."""

    def __init__(self) -> None:
        self._records: List[AnnotatedToolCall] = []

    def record(self, tc: AnnotatedToolCall) -> None:
        self._records.append(tc)

    def get_trace(self, trace_id: str) -> List[AnnotatedToolCall]:
        return [r for r in self._records if r.trace_id == trace_id]

    def get_by_layer(self, layer: Layer) -> List[AnnotatedToolCall]:
        return [r for r in self._records if r.layer == layer]

    def summary(self, trace_id: str) -> str:
        calls = self.get_trace(trace_id)
        if not calls:
            return "No trace."
        lines = [f"Trace {trace_id}: {len(calls)} calls"]
        for c in calls:
            lines.append(f"  L{c.layer.value} {c.tool_name} (retry={c.retry_count})")
        return "\n".join(lines)

    def reset(self) -> None:
        self._records.clear()
