"""Unit tests for the cross-layer constraint and intent framework."""

import pytest

# Use the stable rtlgen package-level API for the constraint framework.
from rtlgen import (
    ConstraintFeedback,
    ConstraintPropagator,
    DesignDecision,
    DesignGate,
    DesignScaffold,
    FeedbackSeverity,
    FunctionalConstraint,
    IRConstraint,
    Module,
    PerformanceConstraint,
    PowerConstraint,
    Signal,
    VerificationIntent,
    make_scaffold,
    generate_constraint_report,
)


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
            collect_intermediate=False,
        )
        assert len(result) == 1
        assert result[0].layer == "ArchitectureIR"

    def test_propagate_all_collect_intermediate(self):
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
        assert len(result) == 4  # SpecIR + 3 intermediates
        layers = {c.layer for c in result}
        assert layers == {"SpecIR", "BehaviorIR", "CycleIR", "ArchitectureIR"}


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
    def test_layers_for_profile(self):
        assert DesignScaffold.layers_for_profile("leaf_min") == [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "DSL"),
            ("DSL", "Verilog"),
        ]
        assert DesignScaffold.layers_for_profile("leaf_arch") == [
            ("SpecIR", "BehaviorIR"),
            ("BehaviorIR", "CycleIR"),
            ("CycleIR", "ArchitectureIR"),
            ("ArchitectureIR", "DSL"),
            ("DSL", "Verilog"),
        ]

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError):
            DesignScaffold.layers_for_profile("does_not_exist")

    def test_make_scaffold_with_profile(self):
        scaffold = make_scaffold(profile="leaf_min")
        assert scaffold.profile == "leaf_min"
        assert scaffold.layers == DesignScaffold.layers_for_profile("leaf_min")

    def test_explicit_layers_override_profile(self):
        scaffold = make_scaffold(
            profile="hier_full",
            layers=[("SpecIR", "BehaviorIR"), ("BehaviorIR", "DSL")],
        )
        assert scaffold.profile == "hier_full"
        assert scaffold.layers == [("SpecIR", "BehaviorIR"), ("BehaviorIR", "DSL")]

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


class TestConstraintReport:
    def test_generate_constraint_report(self):
        m = Module("test")
        m.add_constraint(
            FunctionalConstraint(
                uid="H1",
                name="human_req",
                layer="SpecIR",
                expr="x > 0",
                owner="human",
            )
        )
        m.add_constraint(
            VerificationIntent(
                uid="H1_V",
                name="human_req_sva",
                layer="Verilog",
                expr="assert x > 0",
                derived_from=("H1",),
                owner="ai",
                metadata={"filename": "x_check.sv"},
            )
        )
        m.add_constraint(
            PowerConstraint(
                uid="H2",
                name="unmet_budget",
                layer="SpecIR",
                expr="< 0.1",
                unit="mW/MHz",
                owner="human",
            )
        )

        fb = ConstraintFeedback(
            uid="FB-H2",
            severity=FeedbackSeverity.BLOCKER,
            source_constraint_uid="H2",
            detected_at_layer="Verilog",
            message="Power budget not achievable",
            suggested_resolutions=["Relax budget"],
        )

        decision = DesignDecision(
            uid="D1",
            layer="ArchitectureIR",
            topic="clock gating",
            decision="insert ICGs",
            rationale="save power",
        )

        report = generate_constraint_report(
            entities=[m],
            feedback=[fb],
            decisions=[decision],
            artifacts={"x_check.sv": "assert x > 0;"},
        )

        assert "# Constraint Traceability & Coverage Report" in report
        assert "**Entities**: 1" in report
        assert "**Constraints**: 3" in report
        assert "**Feedback items**: 1" in report
        assert "**Decisions**: 1" in report
        assert "**Artifacts**: 1" in report
        assert "| H1 | human_req | functional | SpecIR | — | human | — |" in report
        assert "| x_check.sv | human_req_sva | Verilog |" in report
        assert "## Coverage Gaps" in report
        assert "| H2 | unmet_budget | SpecIR | power |" in report
        assert "| FB-H2 | blocker | H2 | Verilog |" in report
        assert "### D1: clock gating" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
