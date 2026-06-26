"""Agent design scaffold for standardized Spec2RTL workflows.

The DesignScaffold supports a small set of built-in layer profiles so projects
can choose an appropriate refinement depth instead of forcing every module to
materialize the same six authored layers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.contracts import (
    ConstraintFeedback,
    ConstraintPropagator,
    DesignDecision,
    DesignGate,
    IREntity,
    IRConstraint,
    LayerEmitter,
)


@dataclass
class ScaffoldStep:
    """One step in the standardized agent design loop."""

    name: str
    description: str
    action: Callable[[], Any]
    gate: Optional[DesignGate] = None
    allow_skip_on_warning: bool = True


class DesignScaffold:
    """Standardized scaffold for agent-driven design flows.

    The default loop is:
        propose → propagate → generate → validate → resolve → commit

    Each step can be associated with a DesignGate. BLOCKER feedback stops the
    loop until resolved; WARNING/INFO feedback is logged.
    """

    LAYER_PROFILES: Dict[str, List[Tuple[str, str]]] = {
        "leaf_min": [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "DSL"),
            ("DSL", "Verilog"),
        ],
        "leaf_arch": [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "ArchitectureIR"),
            ("ArchitectureIR", "DSL"),
            ("DSL", "Verilog"),
        ],
        "hier_full": [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "ArchitectureIR"),
            ("ArchitectureIR", "StructuralIR"),
            ("StructuralIR", "DSL"),
            ("DSL", "Verilog"),
        ],
    }

    DEFAULT_PROFILE = "hier_full"
    DEFAULT_LAYERS = [
        ("SpecIR", "BehaviorIR"),
        ("BehaviorIR", "CycleIR"),
        ("CycleIR", "ArchitectureIR"),
        ("ArchitectureIR", "StructuralIR"),
        ("StructuralIR", "DSL"),
        ("DSL", "Verilog"),
    ]

    def __init__(
        self,
        propagator: ConstraintPropagator,
        emitter: LayerEmitter,
        layers: Optional[List[Tuple[str, str]]] = None,
        profile: Optional[str] = None,
    ):
        self.propagator = propagator
        self.emitter = emitter
        self.profile = profile or self.DEFAULT_PROFILE
        if layers is not None:
            self.layers = list(layers)
        else:
            self.layers = self.layers_for_profile(self.profile)
        self.entities: List[IREntity] = []
        self.decisions: List[DesignDecision] = []
        self.feedback: List[ConstraintFeedback] = []
        self.gates: List[DesignGate] = []
        self.artifacts: Dict[str, str] = {}
        self.max_iterations = 3

    @classmethod
    def layers_for_profile(cls, profile: str) -> List[Tuple[str, str]]:
        """Return a copy of the layer path for a built-in profile."""
        if profile not in cls.LAYER_PROFILES:
            supported = ", ".join(sorted(cls.LAYER_PROFILES))
            raise ValueError(f"Unknown scaffold profile '{profile}'. Supported profiles: {supported}")
        return list(cls.LAYER_PROFILES[profile])

    def register_entity(self, entity: IREntity) -> "DesignScaffold":
        self.entities.append(entity)
        return self

    def register_gate(self, gate: DesignGate) -> "DesignScaffold":
        self.gates.append(gate)
        return self

    def record_decision(self, decision: DesignDecision) -> "DesignScaffold":
        self.decisions.append(decision)
        return self

    def propose(self, entity: IREntity, constraints: List[IRConstraint]) -> "DesignScaffold":
        """Attach human/AI constraints at the SpecIR/BehaviorIR layer."""
        for c in constraints:
            entity.add_constraint(c)
        return self

    def propagate_forward(self, entity: IREntity) -> List[IRConstraint]:
        """Propagate constraints down through all configured layers and attach them."""
        existing_uids = {c.uid for c in entity.constraints()}
        derived = self.propagator.propagate_all(entity, self.layers)
        for c in derived:
            if c.uid not in existing_uids:
                entity.add_constraint(c)
                existing_uids.add(c.uid)
        return derived

    def validate_backward(self, entity: IREntity) -> List[ConstraintFeedback]:
        """Validate constraints backward (from Verilog toward SpecIR)."""
        reverse_path = list(reversed(self.layers))
        return self.propagator.validate_all(entity, reverse_path)

    def run_gates(self) -> List[ConstraintFeedback]:
        """Evaluate all registered design gates."""
        issues: List[ConstraintFeedback] = []
        for gate in self.gates:
            for entity in self.entities:
                issues.extend(gate.evaluate(entity))
        self.feedback.extend(issues)
        return issues

    def has_blockers(self) -> bool:
        return any(fb.is_blocking() for fb in self.feedback)

    def resolve(self, resolver: Optional[Callable[[ConstraintFeedback], bool]] = None) -> bool:
        """Apply resolutions to feedback. Returns True if all blockers cleared."""
        for fb in self.feedback:
            if fb.is_blocking():
                if resolver is None or not resolver(fb):
                    return False
        return True

    def generate_artifacts(self) -> Dict[str, str]:
        """Emit artifacts for all entities at their target layers."""
        artifacts: Dict[str, str] = {}
        for entity in self.entities:
            for layer in {c.layer for c in entity.constraints()}:
                emitted = self.emitter.emit(entity, layer)
                for name, content in emitted.items():
                    artifacts[f"{entity.name}_{layer}_{name}"] = content
        self.artifacts.update(artifacts)
        return artifacts

    def run(
        self,
        resolver: Optional[Callable[[ConstraintFeedback], bool]] = None,
    ) -> Tuple[bool, List[ConstraintFeedback]]:
        """Run the full scaffold loop with iteration until clean or max_iterations."""
        for iteration in range(self.max_iterations):
            self.feedback.clear()

            # Forward propagation
            for entity in self.entities:
                self.propagate_forward(entity)

            # Artifact generation
            self.generate_artifacts()

            # Backward validation
            for entity in self.entities:
                self.feedback.extend(self.validate_backward(entity))

            # Gate evaluation
            self.run_gates()

            if not self.has_blockers():
                return True, self.feedback

            if not self.resolve(resolver):
                return False, self.feedback

        return False, self.feedback

    def compliance_checklist(self) -> Dict[str, bool]:
        """Return a checklist of scaffold compliance items."""
        return {
            "has_entities": len(self.entities) > 0,
            "has_constraints": any(e.constraints() for e in self.entities),
            "has_decisions": len(self.decisions) > 0,
            "forward_propagated": any(
                c.layer == "Verilog" for e in self.entities for c in e.constraints()
            ),
            "no_unresolved_blockers": not self.has_blockers(),
            "artifacts_generated": len(self.artifacts) > 0,
        }

    def generate_decision_log(self) -> str:
        """Generate a markdown decision log."""
        lines = ["# Design Decision Log", ""]
        for d in self.decisions:
            lines.append(f"## {d.uid}: {d.topic}")
            lines.append(f"- **Layer**: {d.layer}")
            lines.append(f"- **Owner**: {d.owner}")
            lines.append(f"- **Decision**: {d.decision}")
            lines.append(f"- **Rationale**: {d.rationale}")
            if d.alternatives_considered:
                lines.append(f"- **Alternatives**: {', '.join(d.alternatives_considered)}")
            if d.impacted_constraints:
                lines.append(f"- **Impacted constraints**: {', '.join(d.impacted_constraints)}")
            lines.append("")
        return "\n".join(lines)

    def generate_feedback_report(self) -> str:
        """Generate a markdown feedback/issue report."""
        lines = ["# Design Feedback Report", ""]
        if not self.feedback:
            lines.append("No feedback items.")
            return "\n".join(lines)
        for fb in self.feedback:
            lines.append(f"## {fb.uid} [{fb.severity.value}]")
            lines.append(f"- **Source constraint**: {fb.source_constraint_uid}")
            lines.append(f"- **Detected at layer**: {fb.detected_at_layer}")
            lines.append(f"- **Message**: {fb.message}")
            if fb.suggested_resolutions:
                lines.append(f"- **Suggested resolutions**: {', '.join(fb.suggested_resolutions)}")
            lines.append("")
        return "\n".join(lines)


def make_scaffold(
    propagator: Optional[ConstraintPropagator] = None,
    emitter: Optional[LayerEmitter] = None,
    profile: str = DesignScaffold.DEFAULT_PROFILE,
    layers: Optional[List[Tuple[str, str]]] = None,
) -> DesignScaffold:
    """Factory for a DesignScaffold with default propagator and no-op emitter."""
    if propagator is None:
        propagator = ConstraintPropagator()
    if emitter is None:

        class NoopEmitter(LayerEmitter):
            def emit(self, entity: IREntity, layer: str) -> Dict[str, str]:
                return {}

        emitter = NoopEmitter()
    return DesignScaffold(propagator, emitter, layers=layers, profile=profile)
