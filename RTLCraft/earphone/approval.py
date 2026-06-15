"""Approval gate helpers for Earphone design flow.

Approval files are intentionally small JSON artifacts.  They are not generated
by the normal flow because they represent a human checkpoint, but the helper
does hash reviewed files so stale approvals stop being accepted after edits.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVAL_DIR = os.path.join(os.path.dirname(__file__), "specs", "approvals")


@dataclass(frozen=True)
class ApprovalRequirement:
    gate_id: str
    label: str
    artifacts: List[str]
    scope: str


DEFAULT_APPROVAL_GATES = [
    ApprovalRequirement(
        gate_id="CP0_MODULE",
        label="Module layer approval",
        artifacts=["earphone/modules/{module}/specs/00_module_spec.md"],
        scope="module",
    ),
    ApprovalRequirement(
        gate_id="CP1_SOC",
        label="Top-level SoC approval",
        artifacts=["earphone/specs/09_constraint_traceability.md", "earphone/specs/11_decision_log.md"],
        scope="soc",
    ),
]


def _approval_file_stem(gate_id: str, module: Optional[str] = None) -> str:
    if module:
        safe_module = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in module)
        return f"{gate_id}.{safe_module}"
    return gate_id


def approval_path(gate_id: str, module: Optional[str] = None) -> str:
    return os.path.join(APPROVAL_DIR, f"{_approval_file_stem(gate_id, module)}.json")


def ensure_approval_dir() -> str:
    os.makedirs(APPROVAL_DIR, exist_ok=True)
    return APPROVAL_DIR


def load_approval(gate_id: str, module: Optional[str] = None) -> Optional[Dict[str, object]]:
    path = approval_path(gate_id, module=module)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_artifact_path(artifact: str, module: Optional[str]) -> str:
    if "{module}" in artifact:
        if module is None:
            raise ValueError(f"artifact path requires module: {artifact}")
        return artifact.format(module=module)
    return artifact


def _resolve_artifact_path(artifact: str) -> str:
    if os.path.isabs(artifact):
        return artifact
    return os.path.join(PROJECT_ROOT, artifact)


def _hash_artifact(artifact: str) -> str:
    path = _resolve_artifact_path(artifact)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format_artifacts(artifacts: Iterable[str], module: Optional[str]) -> List[str]:
    return [_format_artifact_path(artifact, module) for artifact in artifacts]


def validate_approval(
    gate_id: str,
    module: Optional[str] = None,
    required_artifacts: Optional[Iterable[str]] = None,
) -> tuple[bool, List[str]]:
    payload = load_approval(gate_id, module=module)
    if payload is None:
        return False, [f"approval file not found: {approval_path(gate_id, module=module)}"]

    reasons: List[str] = []
    if payload.get("gate_id") != gate_id:
        reasons.append(f"gate_id mismatch: expected {gate_id}, got {payload.get('gate_id')}")
    if module is not None and payload.get("module") != module:
        reasons.append(f"module mismatch: expected {module}, got {payload.get('module')}")
    if payload.get("status") != "approved":
        reasons.append("status is not approved")
    if not payload.get("reviewer"):
        reasons.append("reviewer is missing")
    if not payload.get("approved_at"):
        reasons.append("approved_at timestamp is missing")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        reasons.append("artifacts must be a non-empty list")
        artifacts = []

    expected = _format_artifacts(required_artifacts or [], module)
    for artifact in expected:
        if artifact not in artifacts:
            reasons.append(f"required artifact not approved: {artifact}")

    artifact_hashes = payload.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict):
        reasons.append("artifact_hashes is missing")
        artifact_hashes = {}

    for artifact in artifacts:
        if not isinstance(artifact, str):
            reasons.append(f"artifact path is not a string: {artifact!r}")
            continue
        try:
            current_hash = _hash_artifact(artifact)
        except FileNotFoundError:
            reasons.append(f"approved artifact is missing: {artifact}")
            continue
        approved_hash = artifact_hashes.get(artifact)
        if approved_hash != current_hash:
            reasons.append(f"approved artifact hash is stale: {artifact}")

    return not reasons, reasons


def has_approval(
    gate_id: str,
    module: Optional[str] = None,
    required_artifacts: Optional[Iterable[str]] = None,
) -> bool:
    ok, _ = validate_approval(gate_id, module=module, required_artifacts=required_artifacts)
    return ok


def missing_gates(gates: Iterable[ApprovalRequirement], module: Optional[str] = None) -> List[ApprovalRequirement]:
    missing: List[ApprovalRequirement] = []
    for gate in gates:
        if gate.scope == "module" and module is None:
            continue
        gate_module = module if gate.scope == "module" else None
        if not has_approval(gate.gate_id, module=gate_module, required_artifacts=gate.artifacts):
            missing.append(gate)
    return missing


def write_approval(
    gate_id: str,
    reviewer: str,
    artifacts: List[str],
    notes: str = "",
    module: Optional[str] = None,
) -> str:
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    ensure_approval_dir()
    formatted_artifacts = _format_artifacts(artifacts, module)
    artifact_hashes = {artifact: _hash_artifact(artifact) for artifact in formatted_artifacts}
    payload = {
        "gate_id": gate_id,
        "module": module,
        "status": "approved",
        "reviewer": reviewer,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": formatted_artifacts,
        "artifact_hashes": artifact_hashes,
        "notes": notes,
    }
    path = approval_path(gate_id, module=module)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return path
