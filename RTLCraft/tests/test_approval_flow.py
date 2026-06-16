"""Tests for approval gate helpers in the Earphone flow."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from earphone import approval
from earphone.flow import _ensure_soc_approval, _ensure_module_approval, _run_legacy_full_soc


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
    with tempfile.TemporaryDirectory() as tmpdir:
        approval.APPROVAL_DIR = str(Path(tmpdir) / "approvals")
        try:
            approval.write_approval(
                "CP0_MODULE",
                reviewer="tester",
                artifacts=["earphone/modules/{module}/specs/00_module_spec.md"],
                module="rv32",
            )
            assert _ensure_module_approval("rv32") is True
        finally:
            approval.APPROVAL_DIR = original_dir


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
