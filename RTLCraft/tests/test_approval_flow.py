"""Tests for approval gate helpers and structured flow feedback."""

from __future__ import annotations

import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from earphone import approval
from earphone.flow import (
    _collect_module_feedback,
    _ensure_soc_approval,
    _ensure_module_approval,
    _scaffold_feedback_to_items,
    _refresh_top_level_review_artifacts,
    _run_legacy_full_soc,
    _write_flow_feedback,
)


def test_soc_approval_gate_blocks_without_artifact():
    original_dir = approval.APPROVAL_DIR
    with tempfile.TemporaryDirectory() as tmpdir:
        approval.APPROVAL_DIR = str(Path(tmpdir) / "approvals")
        try:
            assert _ensure_soc_approval() is False
        finally:
            approval.APPROVAL_DIR = original_dir


def test_module_approval_gate_accepts_written_artifact():
    original_dir = approval.APPROVAL_DIR
    original_root = approval.PROJECT_ROOT
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        approval.APPROVAL_DIR = str(root / "approvals")
        approval.PROJECT_ROOT = str(root)
        try:
            module_gate = next(gate for gate in approval.DEFAULT_APPROVAL_GATES if gate.gate_id == "CP0_MODULE")
            artifacts = []
            for artifact in module_gate.artifacts:
                formatted = artifact.format(module="rv32")
                path = root / formatted
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{formatted}\n", encoding="utf-8")
                artifacts.append(formatted)
            approval.write_approval(
                "CP0_MODULE",
                reviewer="tester",
                artifacts=artifacts,
                module="rv32",
            )
            assert _ensure_module_approval("rv32") is True
        finally:
            approval.APPROVAL_DIR = original_dir
            approval.PROJECT_ROOT = original_root


def test_approval_hash_mismatch_invalidates_gate():
    original_dir = approval.APPROVAL_DIR
    with tempfile.TemporaryDirectory() as tmpdir:
        approval.APPROVAL_DIR = str(Path(tmpdir) / "approvals")
        reviewed = Path(tmpdir) / "reviewed.md"
        reviewed.write_text("approved\n", encoding="utf-8")
        try:
            approval.write_approval(
                "CP1_SOC",
                reviewer="tester",
                artifacts=[str(reviewed)],
            )
            assert approval.has_approval("CP1_SOC") is True

            reviewed.write_text("changed after approval\n", encoding="utf-8")
            assert approval.has_approval("CP1_SOC") is False
        finally:
            approval.APPROVAL_DIR = original_dir


def test_module_approval_gate_requires_plan_report_and_feedback_artifacts():
    original_dir = approval.APPROVAL_DIR
    original_root = approval.PROJECT_ROOT
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        approval.APPROVAL_DIR = str(root / "approvals")
        approval.PROJECT_ROOT = str(root)
        try:
            spec_path = root / "earphone/modules/foo/specs/00_module_spec.md"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text("spec\n", encoding="utf-8")

            approval.write_approval(
                "CP0_MODULE",
                reviewer="tester",
                module="foo",
                artifacts=["earphone/modules/foo/specs/00_module_spec.md"],
            )
            module_gate = next(gate for gate in approval.DEFAULT_APPROVAL_GATES if gate.gate_id == "CP0_MODULE")
            ok, reasons = approval.validate_approval(
                module_gate.gate_id,
                module="foo",
                required_artifacts=module_gate.artifacts,
            )
            assert ok is False
            assert any("07_module_test_plan.md" in reason for reason in reasons)
            assert any("08_module_test_report.json" in reason for reason in reasons)
            assert any("docgen_feedback.json" in reason for reason in reasons)
        finally:
            approval.APPROVAL_DIR = original_dir
            approval.PROJECT_ROOT = original_root


def test_flow_legacy_runner_uses_top_level_closure_orchestrator():
    with patch("earphone.flow.run_top_level_closure", return_value=0) as closure:
        with patch(
            "earphone.design_earphone.build_legacy_top_level_closure_context",
            return_value={
                "review_bundle_fn": lambda: None,
                "l1_tests_fn": lambda: (True, []),
                "l3_tests_fn": lambda: (True, []),
                "cross_layer_fn": lambda: (True, []),
                "verilog_fn": lambda: [],
                "intent_tests_fn": lambda: (True, []),
                "cocotb_gen_fn": lambda: None,
                "scaffold_fn": lambda: (True, {}, [], []),
            },
        ):
            assert _run_legacy_full_soc() == 0
    closure.assert_called_once()


def test_refresh_top_level_review_artifacts_runs_scaffold_and_review():
    calls = []

    def record(name):
        calls.append(name)

    with patch(
        "earphone.design_earphone.build_legacy_top_level_closure_context",
        return_value={
            "review_bundle_fn": lambda: record("review"),
            "l1_tests_fn": lambda: (True, []),
            "l3_tests_fn": lambda: (True, []),
            "cross_layer_fn": lambda: (True, []),
            "verilog_fn": lambda: [],
            "intent_tests_fn": lambda: (True, []),
            "cocotb_gen_fn": lambda: None,
            "scaffold_fn": lambda: (record("scaffold"), (True, {"gate": True}, [], []))[1],
        },
    ):
        result = _refresh_top_level_review_artifacts()

    assert calls == ["scaffold", "review"]
    assert result["passed"] is True
    assert result["checklist"] == {"gate": True}


def test_resolved_scaffold_feedback_is_downgraded_to_warning():
    class Severity:
        value = "blocker"

    class FakeFeedback:
        severity = Severity()
        source_constraint_uid = "C-1"
        detected_at_layer = "Verilog"
        suggested_resolutions = ["fix it"]
        message = "needs attention"

    items = _scaffold_feedback_to_items([FakeFeedback()], resolved=True)

    assert len(items) == 1
    assert items[0]["severity"] == "warning"
    assert items[0]["metadata"]["resolved"] is True


def test_collect_module_feedback_lifts_docgen_issues():
    with tempfile.TemporaryDirectory() as tmpdir:
        feedback_path = Path(tmpdir) / "docgen_feedback.json"
        feedback_path.write_text(
            json.dumps(
                {
                    "schema_version": "2026-06-15.docgen_feedback.v1",
                    "module_name": "rv32",
                    "issue_count": 1,
                    "blocker_count": 1,
                    "warning_count": 0,
                    "issues": [
                        {
                            "path": "earphone/modules/rv32/layer_L2_cycle/specs/02_cycle_test_report.md",
                            "line": 0,
                            "severity": "blocker",
                            "code": "layer_test_failure",
                            "detected_at_layer": "L2_cycle",
                            "feedback_target_layer": "L1_behavior",
                            "message": "rv32/L2_cycle has 1 failing test(s)",
                            "text": "pytest failure excerpt",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        module_result = {
            "written": [str(feedback_path)],
            "summary": {"layers": 6, "failed": 1},
            "layers": [],
            "passed": False,
        }
        items = _collect_module_feedback("rv32", module_result)

        assert len(items) == 1
        assert items[0]["module"] == "rv32"
        assert items[0]["code"] == "layer_test_failure"
        assert items[0]["detected_at_layer"] == "L2_cycle"
        assert items[0]["feedback_target_layer"] == "L1_behavior"
        assert items[0]["artifacts"] == ["earphone/modules/rv32/layer_L2_cycle/specs/02_cycle_test_report.md"]


def test_write_flow_feedback_includes_module_and_top_level_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "flow_feedback.json"
        module_feedback = Path(tmpdir) / "docgen_feedback.json"
        module_feedback.write_text(
            json.dumps(
                {
                    "schema_version": "2026-06-15.docgen_feedback.v1",
                    "module_name": "rv32",
                    "issue_count": 0,
                    "blocker_count": 0,
                    "warning_count": 0,
                    "issues": [],
                }
            ),
            encoding="utf-8",
        )
        module_results = {
            "rv32": {
                "written": [str(module_feedback)],
                "summary": {"layers": 6, "total": 10, "passed": 10, "failed": 0, "missing_tests": 0},
                "layers": [("L1_behavior", {"total": 2, "passed": 2, "failed": 0, "skipped": 0, "duration": 0.1})],
                "passed": True,
            }
        }

        with patch("earphone.flow._flow_feedback_path", return_value=str(target)):
            path = _write_flow_feedback(
                "pass",
                [],
                module_results=module_results,
                top_result={"total": 3, "passed": 3, "failed": 0, "skipped": 0, "duration": 0.2},
            )

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert payload["schema_version"] == "2026-06-18.flow_feedback.v2"
        assert payload["status"] == "pass"
        assert payload["item_count"] == 0
        assert payload["modules"]["rv32"]["summary"]["passed"] == 10
        assert payload["modules"]["rv32"]["docgen_feedback"] == str(module_feedback)
        assert payload["top_level"]["passed"] == 3
