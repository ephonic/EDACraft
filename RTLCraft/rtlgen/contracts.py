"""Layer and module contracts for multi-layer constrained generation."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple


class Layer(IntEnum):
    """Design representation layers."""

    L0_INTENT = 0
    L1_SPEC = 1
    L2_BEHAVIOR = 2
    L3_DSL = 3
    L4_SKELETON = 4
    L5_RTL = 5
    UNKNOWN = -1


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
class PortContract:
    name: str
    direction: str
    width: int
    protocol: str = "raw"
    description: str = ""


@dataclass
class ProtocolContract:
    name: str
    kind: str
    recipe: str = ""
    request_signals: List[str] = field(default_factory=list)
    response_signals: List[str] = field(default_factory=list)
    flow_control_signals: List[str] = field(default_factory=list)
    ordering: str = "in_order"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionContract:
    name: str
    trigger_signals: List[str] = field(default_factory=list)
    completion_signals: List[str] = field(default_factory=list)
    recipe: str = ""
    trigger_event: str = "level"
    completion_event: str = "level"
    trigger_qualifiers: List[str] = field(default_factory=list)
    completion_qualifiers: List[str] = field(default_factory=list)
    max_cycles: Optional[int] = None
    sample_cycles: int = 0
    ordering: str = "in_order"
    allow_overlap: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceContract:
    name: str
    kind: str
    capacity: Optional[int] = None
    arbitration: str = ""
    observable_signals: List[str] = field(default_factory=list)
    contention_signals: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class FunctionalObjective:
    name: str
    description: str
    invariants: List[str] = field(default_factory=list)
    corner_cases: List[str] = field(default_factory=list)


@dataclass
class PerformanceObjective:
    latency_target: Optional[str] = None
    throughput_target: Optional[str] = None
    structural_budget: Dict[str, Any] = field(default_factory=dict)
    optimization_knobs: List[str] = field(default_factory=list)
    checks: List["PerfCheck"] = field(default_factory=list)
    scenarios: List["PerfScenario"] = field(default_factory=list)


@dataclass
class PerfCheck:
    name: str
    kind: str
    description: str
    source_signals: List[str] = field(default_factory=list)
    sink_signals: List[str] = field(default_factory=list)
    source_event: str = "level"
    sink_event: str = "level"
    source_qualifiers: List[str] = field(default_factory=list)
    sink_qualifiers: List[str] = field(default_factory=list)
    max_cycles: Optional[int] = None
    min_ratio: Optional[float] = None
    min_rate: Optional[float] = None
    max_ratio: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    budget_key: str = ""
    sample_cycles: int = 0
    required_value: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerfScenario:
    name: str
    description: str
    reset_cycles: int = 3
    cycles: int = 8
    stimulus: Dict[str, Any] = field(default_factory=dict)
    linked_checks: List[str] = field(default_factory=list)
    linked_transactions: List[str] = field(default_factory=list)
    stimulus_recipes: List["PerfStimulusRecipe"] = field(default_factory=list)
    stimulus_timeline: List["PerfStimulusStep"] = field(default_factory=list)
    expected_observations: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def resolved_linked_checks(self) -> List[str]:
        linked = list(self.linked_checks)
        legacy = self.expected_observations.get("linked_checks", [])
        if isinstance(legacy, list):
            for check_name in legacy:
                if check_name not in linked:
                    linked.append(check_name)
        return linked

    def expected_signal_names(self) -> List[str]:
        return [
            name for name in self.expected_observations.keys()
            if name != "linked_checks"
        ]

    def stimulus_signal_names(self) -> List[str]:
        names = set(self.stimulus.keys())
        for recipe in self.stimulus_recipes:
            names.update(recipe.values.keys())
        for step in self.stimulus_timeline:
            names.update(step.values.keys())
        return sorted(names)

    def value_for_cycle(self, signal_name: str, cycle_idx: int, default: Any) -> Any:
        value = self.stimulus.get(signal_name, default)
        for recipe in self.stimulus_recipes:
            if recipe.applies(cycle_idx) and signal_name in recipe.values:
                value = recipe.values[signal_name]
        for step in self.stimulus_timeline:
            if step.applies(cycle_idx) and signal_name in step.values:
                value = step.values[signal_name]
        return value


@dataclass
class PerfStimulusStep:
    start_cycle: int
    values: Dict[str, Any] = field(default_factory=dict)
    end_cycle: Optional[int] = None
    description: str = ""

    def applies(self, cycle_idx: int) -> bool:
        if cycle_idx < self.start_cycle:
            return False
        if self.end_cycle is None:
            return cycle_idx == self.start_cycle
        return cycle_idx <= self.end_cycle


@dataclass
class PerfStimulusRecipe:
    kind: str
    values: Dict[str, Any] = field(default_factory=dict)
    start_cycle: int = 0
    end_cycle: Optional[int] = None
    period: int = 1
    duty_cycles: int = 1
    description: str = ""

    def applies(self, cycle_idx: int) -> bool:
        if cycle_idx < self.start_cycle:
            return False
        if self.end_cycle is not None and cycle_idx > self.end_cycle:
            return False
        if self.kind == "pulse":
            return cycle_idx == self.start_cycle
        if self.kind == "hold":
            return True
        phase = cycle_idx - self.start_cycle
        period = max(int(self.period), 1)
        duty = max(min(int(self.duty_cycles), period), 0)
        return (phase % period) < duty


@dataclass
class PerfCheckResult:
    name: str
    kind: str
    passed: bool
    observed: Dict[str, Any] = field(default_factory=dict)
    expected: Dict[str, Any] = field(default_factory=dict)
    details: List[str] = field(default_factory=list)


@dataclass
class ModulePerfReport:
    module_name: str
    contract_present: bool = False
    static_checks: List[PerfCheckResult] = field(default_factory=list)
    dynamic_checks: List[PerfCheckResult] = field(default_factory=list)
    passed: bool = False
    blocking_failures: List[str] = field(default_factory=list)
    failure_records: List[Dict[str, Any]] = field(default_factory=list)
    recommended_knobs: List[str] = field(default_factory=list)


@dataclass
class VerificationHook:
    name: str
    kind: str
    description: str
    signals: List[str] = field(default_factory=list)


@dataclass
class ModuleContract:
    module_name: str
    role: str
    layer: Layer
    trace_id: str = ""
    ports: List[PortContract] = field(default_factory=list)
    protocols: List[ProtocolContract] = field(default_factory=list)
    transactions: List[TransactionContract] = field(default_factory=list)
    resources: List[ResourceContract] = field(default_factory=list)
    state_elements: List[str] = field(default_factory=list)
    timing_assumptions: List[str] = field(default_factory=list)
    functional_objectives: List[FunctionalObjective] = field(default_factory=list)
    performance_objective: PerformanceObjective = field(default_factory=PerformanceObjective)
    verification_hooks: List[VerificationHook] = field(default_factory=list)
    allowed_submodules: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["layer"] = int(self.layer)
        return data


@dataclass
class L1ToL2:
    """Contract: L1 (Spec) -> L2 (Behavior/Plan)."""

    spec: Any
    task_description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:16]


@dataclass
class L2ToL3:
    """Contract: L2 (Behavior) -> L3 (DSL/Exec)."""

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


# =====================================================================
# Cross-Layer Constraint & Intent Framework
#
# This section extends rtlgen.contracts with first-class constraints,
# bidirectional propagation, design gates, and decision records.
# It is designed to be reusable across RTLCraft projects.
# =====================================================================


class FeedbackSeverity(Enum):
    """Severity levels for backward constraint feedback."""

    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class IRConstraint:
    """A first-class constraint or intent attached to an IR entity.

    Constraints can be functional, performance, power, timing, or verification
    oriented. They are created at one IR layer and may be propagated to other
    layers via registered transforms.
    """

    uid: str
    name: str
    category: str  # "functional" | "performance" | "power" | "timing" | "verification"
    layer: str     # e.g., "SpecIR", "BehaviorIR", ..., "Verilog"
    expr: Any      # layer-specific expression
    target: Optional[str] = None
    unit: Optional[str] = None
    owner: str = "human"  # "human" | "ai"
    source_ref: Optional[str] = None
    derived_from: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_derived(self) -> bool:
        return bool(self.derived_from)


@dataclass(frozen=True)
class FunctionalConstraint(IRConstraint):
    """A constraint about functional correctness."""

    def __init__(self, **kwargs):
        kwargs.setdefault("category", "functional")
        super().__init__(**kwargs)


@dataclass(frozen=True)
class PerformanceConstraint(IRConstraint):
    """A constraint about performance (throughput, latency, etc.)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("category", "performance")
        super().__init__(**kwargs)


@dataclass(frozen=True)
class PowerConstraint(IRConstraint):
    """A constraint about power consumption."""

    def __init__(self, **kwargs):
        kwargs.setdefault("category", "power")
        super().__init__(**kwargs)


@dataclass(frozen=True)
class TimingConstraint(IRConstraint):
    """A constraint about timing (setup/hold, clock frequency, etc.)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("category", "timing")
        super().__init__(**kwargs)


@dataclass(frozen=True)
class VerificationIntent(IRConstraint):
    """A verification artifact intent (sequence, scoreboard, coverage, assertion)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("category", "verification")
        super().__init__(**kwargs)


@dataclass(frozen=True)
class ConstraintFeedback:
    """Structured feedback emitted when a lower layer cannot satisfy an upper-layer constraint."""

    uid: str
    severity: FeedbackSeverity
    source_constraint_uid: str
    detected_at_layer: str
    message: str
    suggested_resolutions: List[str] = field(default_factory=list)
    owner: str = "ai"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_blocking(self) -> bool:
        return self.severity == FeedbackSeverity.BLOCKER


@dataclass
class DesignDecision:
    """A recorded design decision with rationale and traceability."""

    uid: str
    layer: str
    topic: str
    decision: str
    rationale: str
    alternatives_considered: List[str] = field(default_factory=list)
    impacted_constraints: List[str] = field(default_factory=list)
    owner: str = "ai"


class IREntity:
    """Mixin providing constraint/decision attachment points for IR nodes."""

    def __init__(self, name: str = ""):
        self.name = name
        self._constraints: List[IRConstraint] = []
        self._design_decisions: List[DesignDecision] = []
        self._layer_tag: str = "StructuralIR"

    def add_constraint(self, constraint: IRConstraint) -> "IREntity":
        self._constraints.append(constraint)
        return self

    def add_decision(self, decision: DesignDecision) -> "IREntity":
        self._design_decisions.append(decision)
        return self

    def constraints(self) -> List[IRConstraint]:
        return list(self._constraints)

    def decisions(self) -> List[DesignDecision]:
        return list(self._design_decisions)

    def constraints_by(
        self,
        *,
        category: Optional[str] = None,
        layer: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[IRConstraint]:
        result = self._constraints
        if category:
            result = [c for c in result if c.category == category]
        if layer:
            result = [c for c in result if c.layer == layer]
        if owner:
            result = [c for c in result if c.owner == owner]
        return result

    def set_layer_tag(self, layer: str) -> "IREntity":
        self._layer_tag = layer
        return self


ForwardTransform = Callable[[IRConstraint, str, str], Optional[IRConstraint]]
BackwardTransform = Callable[[IRConstraint, str, str], Optional[ConstraintFeedback]]


class ConstraintPropagator:
    """Transforms constraints forward (refinement) and backward (validation)."""

    def __init__(self):
        self._forward_rules: Dict[Tuple[str, str], List[ForwardTransform]] = {}
        self._backward_rules: Dict[Tuple[str, str], List[BackwardTransform]] = {}

    def register_forward(self, src_layer: str, dst_layer: str, transform: ForwardTransform):
        self._forward_rules.setdefault((src_layer, dst_layer), []).append(transform)

    def register_backward(self, src_layer: str, dst_layer: str, transform: BackwardTransform):
        """Register a validator that checks dst-layer constraints against src-layer expectations."""
        self._backward_rules.setdefault((src_layer, dst_layer), []).append(transform)

    def propagate_forward(
        self, constraints: List[IRConstraint], src_layer: str, dst_layer: str
    ) -> List[IRConstraint]:
        out = []
        for c in constraints:
            for transform in self._forward_rules.get((src_layer, dst_layer), []):
                nc = transform(c, src_layer, dst_layer)
                if nc is not None:
                    out.append(nc)
        return out

    def propagate_backward(
        self, constraints: List[IRConstraint], src_layer: str, dst_layer: str
    ) -> List[ConstraintFeedback]:
        """Check whether dst-layer constraints satisfy src-layer constraints."""
        out = []
        for c in constraints:
            for transform in self._backward_rules.get((src_layer, dst_layer), []):
                fb = transform(c, src_layer, dst_layer)
                if fb is not None:
                    out.append(fb)
        return out

    def propagate_all(
        self,
        entity: IREntity,
        path: List[Tuple[str, str]],
        collect_intermediate: bool = True,
    ) -> List[IRConstraint]:
        """Propagate constraints through a layer path.

        If ``collect_intermediate`` is True, all intermediate-layer constraints
        are returned alongside the final-layer constraints, preserving full
        traceability.
        """
        all_constraints = list(entity.constraints())
        current = all_constraints
        for src_layer, dst_layer in path:
            current = self.propagate_forward(current, src_layer, dst_layer)
            if collect_intermediate:
                all_constraints.extend(current)
        return all_constraints if collect_intermediate else current

    def validate_all(
        self,
        entity: IREntity,
        path: List[Tuple[str, str]],
    ) -> List[ConstraintFeedback]:
        """Run backward validation along a layer path (typically from Verilog back to SpecIR)."""
        feedback: List[ConstraintFeedback] = []
        constraints = entity.constraints()
        for src_layer, dst_layer in path:
            feedback.extend(self.propagate_backward(constraints, src_layer, dst_layer))
            constraints = self.propagate_forward(constraints, src_layer, dst_layer)
        return feedback


class DesignGate:
    """A checkpoint between two layers that emits feedback if the transition is invalid."""

    def __init__(
        self,
        src_layer: str,
        dst_layer: str,
        checks: List[Callable[[IREntity, str, str], List[ConstraintFeedback]]],
    ):
        self.src_layer = src_layer
        self.dst_layer = dst_layer
        self.checks = checks

    def evaluate(self, entity: IREntity) -> List[ConstraintFeedback]:
        issues = []
        for check in self.checks:
            issues.extend(check(entity, self.src_layer, self.dst_layer))
        return issues

    def has_blockers(self, entity: IREntity) -> bool:
        return any(fb.is_blocking() for fb in self.evaluate(entity))


class LayerEmitter:
    """Base class for per-layer artifact emitters."""

    def emit(self, entity: IREntity, layer: str) -> Dict[str, str]:
        raise NotImplementedError("Subclasses must implement emit().")
