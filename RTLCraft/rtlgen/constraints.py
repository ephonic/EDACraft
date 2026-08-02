"""Compatibility constraint and design-scaffold helpers.

This module restores the narrow public surface used by older seed flows while
keeping the implementation small and independent of the newer foundation gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass
class IRConstraint:
    uid: str
    name: str
    category: str
    layer: str
    expr: str
    target: str = ""
    unit: str = ""
    derived_from: Tuple[str, ...] = ()
    owner: str = ""
    source_ref: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.derived_from = tuple(self.derived_from)
        self.metadata = dict(self.metadata or {})

    def is_derived(self) -> bool:
        return bool(self.derived_from)


class FunctionalConstraint(IRConstraint):
    def __init__(self, uid: str, name: str, layer: str, expr: str, **kwargs: Any) -> None:
        super().__init__(uid=uid, name=name, category="functional", layer=layer, expr=expr, **kwargs)


class PerformanceConstraint(IRConstraint):
    def __init__(self, uid: str, name: str, layer: str, expr: str, **kwargs: Any) -> None:
        super().__init__(uid=uid, name=name, category="performance", layer=layer, expr=expr, **kwargs)


class PowerConstraint(IRConstraint):
    def __init__(self, uid: str, name: str, layer: str, expr: str, **kwargs: Any) -> None:
        super().__init__(uid=uid, name=name, category="power", layer=layer, expr=expr, **kwargs)


class VerificationIntent(IRConstraint):
    def __init__(self, uid: str, name: str, layer: str, expr: str, **kwargs: Any) -> None:
        super().__init__(uid=uid, name=name, category="verification", layer=layer, expr=expr, **kwargs)


class FeedbackSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    BLOCKER = "blocker"


@dataclass
class ConstraintFeedback:
    uid: str
    severity: FeedbackSeverity | str
    source_constraint_uid: str
    detected_at_layer: str
    message: str
    suggested_resolutions: Sequence[str] = ()
    owner: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.severity, str):
            self.severity = FeedbackSeverity(self.severity)
        self.suggested_resolutions = tuple(self.suggested_resolutions)
        self.metadata = dict(self.metadata or {})

    def is_blocking(self) -> bool:
        return self.severity is FeedbackSeverity.BLOCKER


RuleResult = Optional[IRConstraint | ConstraintFeedback | Sequence[IRConstraint] | Sequence[ConstraintFeedback]]
PropagationRule = Callable[[IRConstraint, str, str], RuleResult]


class ConstraintPropagator:
    """Rule registry for forward propagation and backward validation."""

    def __init__(self) -> None:
        self._forward_rules: Dict[Tuple[str, str], List[PropagationRule]] = {}
        self._backward_rules: Dict[Tuple[str, str], List[PropagationRule]] = {}

    def register_forward(self, src_layer: str, dst_layer: str, rule: PropagationRule) -> None:
        self._forward_rules.setdefault((src_layer, dst_layer), []).append(rule)

    def register_backward(self, src_layer: str, dst_layer: str, rule: PropagationRule) -> None:
        self._backward_rules.setdefault((src_layer, dst_layer), []).append(rule)

    @staticmethod
    def _flatten(result: RuleResult) -> List[Any]:
        if result is None:
            return []
        if isinstance(result, (IRConstraint, ConstraintFeedback)):
            return [result]
        return [item for item in result if item is not None]

    def propagate_forward(
        self,
        constraints: Iterable[IRConstraint],
        src_layer: str,
        dst_layer: str,
    ) -> List[IRConstraint]:
        propagated: List[IRConstraint] = []
        for constraint in constraints:
            if constraint.layer != src_layer:
                continue
            for rule in self._forward_rules.get((src_layer, dst_layer), []):
                propagated.extend(self._flatten(rule(constraint, src_layer, dst_layer)))
        return propagated

    def propagate_backward(
        self,
        constraints: Iterable[IRConstraint],
        src_layer: str,
        dst_layer: str,
    ) -> List[ConstraintFeedback]:
        feedback: List[ConstraintFeedback] = []
        for constraint in constraints:
            if constraint.layer != src_layer:
                continue
            for rule in self._backward_rules.get((src_layer, dst_layer), []):
                feedback.extend(self._flatten(rule(constraint, src_layer, dst_layer)))
        return feedback

    def propagate_all(
        self,
        entity_or_constraints: Any,
        layers: Sequence[Tuple[str, str]],
        *,
        collect_intermediate: bool = True,
    ) -> List[IRConstraint]:
        if hasattr(entity_or_constraints, "constraints"):
            current = list(entity_or_constraints.constraints())
        else:
            current = list(entity_or_constraints)
        collected = list(current)
        for src_layer, dst_layer in layers:
            current = self.propagate_forward(current, src_layer, dst_layer)
            if collect_intermediate:
                collected.extend(current)
        return collected if collect_intermediate else current


GateCheck = Callable[[Any, str, str], Sequence[ConstraintFeedback]]


class DesignGate:
    def __init__(self, src_layer: str, dst_layer: str, checks: Sequence[GateCheck]) -> None:
        self.src_layer = src_layer
        self.dst_layer = dst_layer
        self.checks = tuple(checks)

    def evaluate(self, entity: Any) -> List[ConstraintFeedback]:
        feedback: List[ConstraintFeedback] = []
        for check in self.checks:
            feedback.extend(check(entity, self.src_layer, self.dst_layer))
        return feedback

    def has_blockers(self, entity: Any) -> bool:
        return any(item.is_blocking() for item in self.evaluate(entity))


@dataclass
class DesignDecision:
    uid: str
    layer: str
    topic: str
    decision: str
    rationale: str
    alternatives_considered: Sequence[str] = ()
    impacted_constraints: Sequence[str] = ()
    owner: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.alternatives_considered = tuple(self.alternatives_considered)
        self.impacted_constraints = tuple(self.impacted_constraints)
        self.metadata = dict(self.metadata or {})


class LayerEmitter:
    def emit(self, entity: Any, layer: str) -> Dict[str, str]:
        return {}


class DesignScaffold:
    DEFAULT_LAYERS: List[Tuple[str, str]] = [
        ("SpecIR", "BehaviorIR"),
        ("BehaviorIR", "CycleIR"),
        ("CycleIR", "ArchitectureIR"),
        ("ArchitectureIR", "DSL"),
        ("DSL", "Verilog"),
    ]
    PROFILE_LAYERS: Dict[str, List[Tuple[str, str]]] = {
        "leaf_min": [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "DSL"),
            ("DSL", "Verilog"),
        ],
        "leaf_arch": DEFAULT_LAYERS,
        "hier_full": [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "ArchitectureIR"),
            ("ArchitectureIR", "StructuralIR"),
            ("StructuralIR", "DSL"),
            ("DSL", "Verilog"),
        ],
    }

    def __init__(
        self,
        propagator: Optional[ConstraintPropagator] = None,
        emitter: Optional[LayerEmitter] = None,
        *,
        profile: str = "leaf_arch",
        layers: Optional[Sequence[Tuple[str, str]]] = None,
        gates: Sequence[DesignGate] = (),
    ) -> None:
        self.profile = profile
        self.layers = list(layers) if layers is not None else self.layers_for_profile(profile)
        self.propagator = propagator or ConstraintPropagator()
        self.emitter = emitter or LayerEmitter()
        self.gates = list(gates)
        self.entities: List[Any] = []
        self.decisions: List[DesignDecision] = []
        self.artifacts: Dict[str, str] = {}

    @classmethod
    def layers_for_profile(cls, profile: str) -> List[Tuple[str, str]]:
        if profile not in cls.PROFILE_LAYERS:
            raise ValueError(f"unknown design scaffold profile '{profile}'")
        return list(cls.PROFILE_LAYERS[profile])

    def register_entity(self, entity: Any) -> Any:
        self.entities.append(entity)
        return entity

    def register_gate(self, gate: DesignGate) -> DesignGate:
        self.gates.append(gate)
        return gate

    def propose(self, entity: Any, constraints: Iterable[IRConstraint]) -> None:
        for constraint in constraints:
            entity.add_constraint(constraint)

    def record_decision(self, decision: DesignDecision) -> None:
        self.decisions.append(decision)

    def run(self, resolver: Optional[Callable[[ConstraintFeedback], bool]] = None) -> Tuple[bool, List[ConstraintFeedback]]:
        feedback: List[ConstraintFeedback] = []
        for entity in self.entities:
            propagated = self.propagator.propagate_all(entity, self.layers)
            known_uids = {constraint.uid for constraint in entity.constraints()}
            for constraint in propagated:
                if constraint.uid not in known_uids:
                    entity.add_constraint(constraint)
                    known_uids.add(constraint.uid)
            for _, dst_layer in self.layers:
                self.artifacts.update(self.emitter.emit(entity, dst_layer))
            for gate in self.gates:
                feedback.extend(gate.evaluate(entity))
        if resolver is not None:
            feedback = [item for item in feedback if not resolver(item)]
        return not any(item.is_blocking() for item in feedback), feedback

    def compliance_checklist(self) -> Dict[str, bool]:
        constraints = [constraint for entity in self.entities for constraint in entity.constraints()]
        return {
            "has_entities": bool(self.entities),
            "has_constraints": bool(constraints),
            "has_decisions": bool(self.decisions),
        }

    def generate_decision_log(self) -> str:
        lines = ["# Design Decision Log", ""]
        if not self.decisions:
            lines.append("- No design decisions recorded.")
            return "\n".join(lines)
        for decision in self.decisions:
            lines.extend(
                [
                    f"## {decision.uid}: {decision.topic}",
                    "",
                    f"- Layer: {decision.layer}",
                    f"- Decision: {decision.decision}",
                    f"- Rationale: {decision.rationale}",
                ]
            )
            if decision.alternatives_considered:
                lines.append(f"- Alternatives: {', '.join(decision.alternatives_considered)}")
            if decision.impacted_constraints:
                lines.append(f"- Impacted constraints: {', '.join(decision.impacted_constraints)}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def make_scaffold(
    *,
    profile: str = "leaf_arch",
    layers: Optional[Sequence[Tuple[str, str]]] = None,
    propagator: Optional[ConstraintPropagator] = None,
    emitter: Optional[LayerEmitter] = None,
    gates: Sequence[DesignGate] = (),
) -> DesignScaffold:
    return DesignScaffold(
        propagator=propagator,
        emitter=emitter,
        profile=profile,
        layers=layers,
        gates=gates,
    )


def generate_constraint_report(
    *,
    entities: Sequence[Any],
    feedback: Sequence[ConstraintFeedback] = (),
    decisions: Sequence[DesignDecision] = (),
    artifacts: Mapping[str, str] = {},
) -> str:
    constraints = [constraint for entity in entities for constraint in entity.constraints()]
    placeholder = "\u2014"
    lines = [
        "# Constraint Traceability & Coverage Report",
        "",
        f"**Entities**: {len(entities)}",
        f"**Constraints**: {len(constraints)}",
        f"**Feedback items**: {len(feedback)}",
        f"**Decisions**: {len(decisions)}",
        f"**Artifacts**: {len(artifacts)}",
        "",
        "## Constraints",
        "",
        "| UID | Name | Category | Layer | Target | Owner | Derived From |",
        "|-----|------|----------|-------|--------|-------|--------------|",
    ]
    for constraint in constraints:
        target = constraint.target or placeholder
        owner = constraint.owner or placeholder
        derived = ", ".join(constraint.derived_from) if constraint.derived_from else placeholder
        lines.append(
            f"| {constraint.uid} | {constraint.name} | {constraint.category} | "
            f"{constraint.layer} | {target} | {owner} | {derived} |"
        )

    lines.extend(["", "## Generated Artifacts", ""])
    if artifacts:
        lines.extend(["| Path | Constraint | Layer |", "|------|------------|-------|"])
        for constraint in constraints:
            filename = constraint.metadata.get("filename") if constraint.metadata else None
            if filename and filename in artifacts:
                lines.append(f"| {filename} | {constraint.name} | {constraint.layer} |")
    else:
        lines.append("- None.")

    lines.extend(["", "## Coverage Gaps", ""])
    gaps = [constraint for constraint in constraints if not constraint.derived_from and constraint.category != "verification"]
    if gaps:
        lines.extend(["| UID | Name | Layer | Category |", "|-----|------|-------|----------|"])
        for constraint in gaps:
            lines.append(f"| {constraint.uid} | {constraint.name} | {constraint.layer} | {constraint.category} |")
    else:
        lines.append("- None.")

    lines.extend(["", "## Feedback", ""])
    if feedback:
        lines.extend(["| UID | Severity | Source Constraint | Detected At | Message |", "|-----|----------|-------------------|-------------|---------|"])
        for item in feedback:
            lines.append(
                f"| {item.uid} | {item.severity.value} | {item.source_constraint_uid} | "
                f"{item.detected_at_layer} | {item.message} |"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Decisions", ""])
    if decisions:
        for decision in decisions:
            lines.extend([f"### {decision.uid}: {decision.topic}", "", decision.decision, ""])
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "ConstraintFeedback",
    "ConstraintPropagator",
    "DesignDecision",
    "DesignGate",
    "DesignScaffold",
    "FeedbackSeverity",
    "FunctionalConstraint",
    "IRConstraint",
    "LayerEmitter",
    "PerformanceConstraint",
    "PowerConstraint",
    "VerificationIntent",
    "generate_constraint_report",
    "make_scaffold",
]
