"""Unit tests for the cross-layer constraint and intent framework."""

import pytest

from rtlgen.contracts import (
    ConstraintFeedback,
    ConstraintPropagator,
    DesignDecision,
    DesignGate,
    FeedbackSeverity,
    FunctionalConstraint,
    IRConstraint,
    PerformanceConstraint,
    PowerConstraint,
)
from rtlgen.core import Module, Signal
from rtlgen.scaffold import DesignScaffold, make_scaffold


class TestIRConstraint:
    def test_basic_constraint(self):
        c = IRConstraint(
            uid="C1",
            name="test_constraint",
            category="functional",
            layer="SpecIR",
            expr="x > 0",
        )
        assert c.uid == "C1"
        assert c.category == "functional"
        assert not c.is_derived()

    def test_derived_constraint(self):
        child = IRConstraint(
            uid="C2",
            name="derived",
            category="functional",
            layer="BehaviorIR",
            expr="x > 0",
            derived_from=("C1",),
        )
        assert child.is_derived()
        assert child.derived_from == ("C1",)


class TestIREntity:
    def test_signal_carries_constraints(self):
        s = Signal(8, "my_sig")
        s.add_constraint(
            FunctionalConstraint(
                uid="S1",
                name="signal_range",
                layer="SpecIR",
                expr="0 <= value <= 255",
            )
        )
        assert len(s.constraints()) == 1
        assert s.constraints_by(category="functional")[0].name == "signal_range"

    def test_module_carries_constraints(self):
        m = Module("test_mod")
        m.add_constraint(
            PerformanceConstraint(
                uid="M1",
                name="max_latency",
                layer="SpecIR",
                expr="< 10",
                unit="cycles",
            )
        )
        assert len(m.constraints()) == 1
        assert m.constraints_by(layer="SpecIR")[0].name == "max_latency"


class TestConstraintPropagator:
    def test_forward_propagation(self):
        prop = ConstraintPropagator()

        def spec_to_behavior(c, src, dst):
            if c.layer == "SpecIR" and c.category == "functional":
                return FunctionalConstraint(
                    uid=f"{c.uid}_B",
                    name=f"{c.name}_behavior",
                    layer=dst,
                    expr=f"iss_check({c.expr})",
                    derived_from=(c.uid,),
                )
            return None

        prop.register_forward("SpecIR", "BehaviorIR", spec_to_behavior)

        constraints = [
            FunctionalConstraint(
                uid="C1",
                name="div_zero",
                layer="SpecIR",
                expr="div by zero returns -1",
            )
        ]
        result = prop.propagate_forward(constraints, "SpecIR", "BehaviorIR")
        assert len(result) == 1
        assert result[0].layer == "BehaviorIR"
        assert result[0].derived_from == ("C1",)

    def test_backward_validation(self):
        prop = ConstraintPropagator()

        def check_power(c, src, dst):
            if c.category == "power" and c.layer == src:
                # Simulate: Verilog implementation exceeds budget
                if c.expr == "< 0.5":
                    return ConstraintFeedback(
                        uid="FB1",
                        severity=FeedbackSeverity.VIOLATION,
                        source_constraint_uid=c.uid,
                        detected_at_layer=dst,
                        message="Estimated power is 0.72 mW/MHz",
                        suggested_resolutions=["relax budget", "add clock gating"],
                    )
            return None

        prop.register_backward("SpecIR", "Verilog", check_power)

        constraints = [
            PowerConstraint(
                uid="P1",
                name="cpu_power",
                layer="SpecIR",
                expr="< 0.5",
                unit="mW/MHz",
            )
        ]
        feedback = prop.propagate_backward(constraints, "SpecIR", "Verilog")
        assert len(feedback) == 1
        assert feedback[0].severity == FeedbackSeverity.VIOLATION
        assert feedback[0].is_blocking() is False

    def test_propagate_all(self):
        prop = ConstraintPropagator()

        def forward(c, src, dst):
            return IRConstraint(
                uid=f"{c.uid}_{dst[:3]}",
                name=c.name,
                category=c.category,
                layer=dst,
                expr=c.expr,
                derived_from=(c.uid,),
            )

        for src, dst in [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "ArchitectureIR"),
        ]:
            prop.register_forward(src, dst, forward)

        m = Module("test")
        m.add_constraint(
            FunctionalConstraint(
                uid="C1",
                name="test",
                layer="SpecIR",
                expr="true",
            )
        )
        result = prop.propagate_all(
            m,
            [("SpecIR", "BehaviorIR"), ("BehaviorIR", "CycleIR"), ("CycleIR", "ArchitectureIR")],
        )
        assert len(result) == 1
        assert result[0].layer == "ArchitectureIR"


class TestDesignGate:
    def test_gate_detects_blocker(self):
        def check(entity, src, dst):
            fb = []
            for c in entity.constraints_by(layer=src):
                if c.name == "unmeetable":
                    fb.append(
                        ConstraintFeedback(
                            uid="G1",
                            severity=FeedbackSeverity.BLOCKER,
                            source_constraint_uid=c.uid,
                            detected_at_layer=dst,
                            message="Cannot meet timing",
                            suggested_resolutions=["relax constraint"],
                        )
                    )
            return fb

        gate = DesignGate("SpecIR", "Verilog", [check])
        m = Module("test")
        m.add_constraint(
            FunctionalConstraint(
                uid="C1",
                name="unmeetable",
                layer="SpecIR",
                expr="1 GHz on 22nm",
            )
        )
        issues = gate.evaluate(m)
        assert len(issues) == 1
        assert issues[0].is_blocking()
        assert gate.has_blockers(m)


class TestDesignScaffold:
    def test_scaffold_run_clean(self):
        scaffold = make_scaffold()

        def forward(c, src, dst):
            return IRConstraint(
                uid=f"{c.uid}_{dst}",
                name=c.name,
                category=c.category,
                layer=dst,
                expr=c.expr,
                derived_from=(c.uid,),
            )

        for src, dst in DesignScaffold.DEFAULT_LAYERS:
            scaffold.propagator.register_forward(src, dst, forward)

        m = Module("test")
        scaffold.register_entity(m)
        scaffold.propose(
            m,
            [
                FunctionalConstraint(
                    uid="C1",
                    name="div_zero",
                    layer="SpecIR",
                    expr="div by zero returns -1",
                )
            ],
        )
        scaffold.record_decision(
            DesignDecision(
                uid="D1",
                layer="ArchitectureIR",
                topic="divider",
                decision="use iterative divider",
                rationale="save area",
            )
        )

        ok, feedback = scaffold.run()
        assert ok
        assert not feedback

    def test_compliance_checklist(self):
        scaffold = make_scaffold()
        m = Module("test")
        scaffold.register_entity(m)
        checklist = scaffold.compliance_checklist()
        assert checklist["has_entities"] is True
        assert checklist["has_constraints"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
