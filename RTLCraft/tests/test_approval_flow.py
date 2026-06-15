"""Tests for approval gate helpers in the Earphone flow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from earphone import approval
from earphone.flow import _ensure_soc_approval, _ensure_module_approval


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
