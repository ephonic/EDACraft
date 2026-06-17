"""Design-scaffold helpers for top-level SoC closure."""

from __future__ import annotations

import os
from typing import Callable, List

from rtlgen import DesignDecision, DesignScaffold, generate_constraint_report


def run_design_scaffold_phase(
    *,
    propagator_factory: Callable[[], object],
    layer_emitter_factory: Callable[[], object],
    layers: list,
    entity_factories: list[Callable[[], object]],
    design_gates_factory: Callable[[], list],
    feedback_resolver: Callable[[object, list], bool],
) -> tuple[bool, dict, list, list]:
    """Run the design scaffold phase and persist traceability artifacts."""
    scaffold = DesignScaffold(propagator_factory(), layer_emitter_factory(), layers=layers)

    for entity_factory in entity_factories:
        scaffold.register_entity(entity_factory())

    for gate in design_gates_factory():
        scaffold.register_gate(gate)

    scaffold.record_decision(
        DesignDecision(
            uid="DEC-RV32-001",
            layer="ArchitectureIR",
            topic="Divider implementation",
            decision="Use 32-cycle iterative restoring divider for DIV/DIVU/REM/REMU",
            rationale="Reduce divider area vs combinational implementation; acceptable latency for Earphone control code.",
            alternatives_considered=["Combinational divider", "Radix-4 SRT divider"],
            impacted_constraints=["EARP-RV32-001", "EARP-RV32-002"],
            owner="ai",
        )
    )
    scaffold.record_decision(
        DesignDecision(
            uid="DEC-RV32-002",
            layer="ArchitectureIR",
            topic="Pipeline clock gating",
            decision="Gate pipeline registers with core_clk_en = ~core_stall & ~muldiv_busy",
            rationale="Cut dynamic power during memory stalls and divide operations with minimal control overhead.",
            alternatives_considered=["Per-register fine-grained gating", "Module-level clock gate only"],
            impacted_constraints=["EARP-RV32-002"],
            owner="ai",
        )
    )
    scaffold.record_decision(
        DesignDecision(
            uid="DEC-SIMD-001",
            layer="ArchitectureIR",
            topic="SIMD datapath gating",
            decision="Independent int_ce and fp_ce clock enables for INT16/FP16 datapaths",
            rationale="FP16 MAC pipeline toggles only when FP16 workloads are active; INT16 audio path remains active.",
            alternatives_considered=["Shared SIMD clock enable", "Per-lane clock gating"],
            impacted_constraints=["EARP-SIMD-001"],
            owner="ai",
        )
    )

    print("\n" + "=" * 70)
    print("Design Scaffold — Constraint Propagation & Validation")
    print("=" * 70)

    resolution_log: List[str] = []
    resolved_feedback: List[object] = []

    def _scaffold_resolver(feedback_item):
        resolved = feedback_resolver(feedback_item, scaffold.entities)
        if resolved:
            resolution_log.append(
                f"Resolved {feedback_item.uid}: {feedback_item.message} -> applied suggested resolution"
            )
            resolved_feedback.append(feedback_item)
        return resolved

    scaffold_ok, feedback = scaffold.run(resolver=_scaffold_resolver)
    print(f"  Scaffold propagation/validation: {'PASS' if scaffold_ok else 'BLOCKERS'}")
    checklist = scaffold.compliance_checklist()
    for item, ok in checklist.items():
        print(f"  compliance.{item}: {'OK' if ok else 'MISSING'}")

    out_dir = "earphone/tb/constraints"
    os.makedirs(out_dir, exist_ok=True)
    for artifact_name, content in scaffold.artifacts.items():
        path = os.path.join(out_dir, artifact_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  wrote {path}")

    report_path = "earphone/specs/09_constraint_traceability.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(
            generate_constraint_report(
                entities=scaffold.entities,
                feedback=feedback,
                decisions=scaffold.decisions,
                artifacts=scaffold.artifacts,
            )
        )
    print(f"  wrote {report_path}")

    issue_lines = [
        "# 10 Design Feedback / Issues Report",
        "",
        "## Resolution Log",
        "",
    ]
    if resolution_log:
        for entry in resolution_log:
            issue_lines.append(f"- {entry}")
    else:
        issue_lines.append("- No auto-resolutions performed.")

    all_feedback = feedback + resolved_feedback
    issue_lines.extend([
        "",
        "## Feedback Items",
        "",
    ])
    if all_feedback:
        issue_lines.extend([
            "| UID | Severity | Source Constraint | Detected At | Message |",
            "|-----|----------|-------------------|-------------|---------|",
        ])
        for feedback_item in sorted(all_feedback, key=lambda x: x.severity.value):
            issue_lines.append(
                f"| {feedback_item.uid} | {feedback_item.severity.value} | {feedback_item.source_constraint_uid} | "
                f"{feedback_item.detected_at_layer} | {feedback_item.message} |"
            )
    else:
        issue_lines.append("- No feedback items.")

    issue_lines.extend([
        "",
        "## Remaining Blockers",
        "",
    ])
    remaining_blockers = [feedback_item for feedback_item in feedback if feedback_item.is_blocking()]
    if remaining_blockers:
        for feedback_item in remaining_blockers:
            issue_lines.append(f"- **{feedback_item.uid}**: {feedback_item.message}")
            for suggestion in feedback_item.suggested_resolutions:
                issue_lines.append(f"  - Suggested: {suggestion}")
    else:
        issue_lines.append("- None. All blockers resolved or no blockers detected.")

    issue_path = "earphone/specs/10_design_issues.md"
    with open(issue_path, "w", encoding="utf-8") as f:
        f.write("\n".join(issue_lines))
    print(f"  wrote {issue_path}")

    decision_log_path = "earphone/specs/11_decision_log.md"
    with open(decision_log_path, "w", encoding="utf-8") as f:
        f.write(scaffold.generate_decision_log())
    print(f"  wrote {decision_log_path}")

    return scaffold_ok, checklist, feedback, resolved_feedback


__all__ = ["run_design_scaffold_phase"]
