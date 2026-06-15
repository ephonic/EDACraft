"""Earphone SoC — document-driven layered design entry point.

This module orchestrates the Spec2RTL flow across layered IRs and modules.
During the document-driven refactor it delegates to the legacy monolithic
entry point for the full-SoC verification closure, while exercising the new
per-module, per-IR-layer package structure as the migration pilot.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# New module-level API (pilot: RV32)
from earphone.modules.rv32 import RV32IM_ISS, EarphoneRV32

# Document generator that extracts real design data and fills templates.
from earphone.docgen import (
    discover_modules,
    generate_module_docs,
    run_layer_tests,
)
from earphone.approval import (
    DEFAULT_APPROVAL_GATES,
    approval_path,
    validate_approval,
)


_LAYER_ORDER = [
    "L1_behavior",
    "L2_cycle",
    "L3_architecture",
    "L4_structure",
    "L5_dsl",
    "L6_verilog",
]


def run_module_layer_tests(module: str = "rv32") -> List[Tuple[str, dict]]:
    """Run pytest for every populated layer of a module.

    Returns a list of (layer, result) tuples where result is the dict returned
    by docgen.run_layer_tests.
    """
    results: List[Tuple[str, dict]] = []
    for layer in _LAYER_ORDER:
        result = run_layer_tests(module, layer)
        results.append((layer, result))
    return results


def _module_has_layer_tests(module: str, layer: str) -> bool:
    tests_dir = os.path.join(
        os.path.dirname(__file__), "modules", module, f"layer_{layer}", "tests"
    )
    return os.path.isdir(tests_dir)


def _module_summary(module: str, layer_results: List[Tuple[str, dict]]) -> Dict[str, int]:
    summary = {
        "layers": len(layer_results),
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "missing_tests": 0,
    }
    for layer, result in layer_results:
        summary["total"] += int(result.get("total", 0))
        summary["passed"] += int(result.get("passed", 0))
        summary["failed"] += int(result.get("failed", 0))
        summary["skipped"] += int(result.get("skipped", 0))
        if result.get("total", 0) == 0 or not _module_has_layer_tests(module, layer):
            summary["missing_tests"] += 1
    return summary


def run_module(module: str, *, strict: bool = False) -> Dict[str, object]:
    """Generate docs, run tests, and return a structured module summary."""
    written = generate_module_docs(module, strict=strict)
    layer_results = run_module_layer_tests(module)
    all_pass = all(result.get("failed", 0) == 0 and result.get("total", 0) > 0 for _, result in layer_results)
    return {
        "module": module,
        "written": written,
        "layers": layer_results,
        "summary": _module_summary(module, layer_results),
        "passed": all_pass,
    }


def _print_layer_results(module: str, layer_results: List[Tuple[str, dict]]) -> bool:
    all_pass = True
    for layer, result in layer_results:
        total = result.get("total", 0)
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        skipped = result.get("skipped", 0)
        status = "PASS" if failed == 0 and total > 0 else "FAIL" if failed > 0 else "NO TESTS"
        print(f"  {module}/{layer}: {passed}/{total} passed, {failed} failed, {skipped} skipped — {status}")
        if failed > 0 or total == 0:
            all_pass = False
    return all_pass


def _module_blocker_summary(module: str, layer_results: List[Tuple[str, dict]]) -> List[str]:
    blockers: List[str] = []
    for layer, result in layer_results:
        if result.get("failed", 0) > 0:
            blockers.append(f"{module}/{layer}: {result.get('failed', 0)} failing tests")
        if result.get("total", 0) == 0:
            blockers.append(f"{module}/{layer}: no discovered tests")
    return blockers


def _run_pytest_dir(path: str, timeout: int = 120) -> Dict[str, object]:
    if not os.path.isdir(path):
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration": 0.0, "cmd": ""}

    cmd = [sys.executable, "-m", "pytest", path, "-q", "--tb=short"]
    start = __import__("time").time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "total": 0,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "duration": 0.0,
            "cmd": " ".join(cmd),
            "error": str(exc),
        }
    duration = __import__("time").time() - start

    summary: Dict[str, object] = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "duration": duration,
        "cmd": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        parts = line.strip().split()
        for i, part in enumerate(parts):
            if i == 0:
                continue
            if part == "passed":
                summary["passed"] = int(parts[i - 1])
            elif part == "failed":
                summary["failed"] = int(parts[i - 1])
            elif part == "skipped":
                summary["skipped"] = int(parts[i - 1])
            elif part == "error":
                summary["failed"] = int(summary["failed"]) + int(parts[i - 1])
    summary["total"] = int(summary["passed"]) + int(summary["failed"]) + int(summary["skipped"])
    return summary


def run_top_level_contract_tests() -> Dict[str, object]:
    """Run top-level SoC contract tests."""
    tests_root = os.path.join(os.path.dirname(__file__), "top")
    return _run_pytest_dir(tests_root)


def _print_top_level_result(result: Dict[str, object]) -> bool:
    total = int(result.get("total", 0))
    passed = int(result.get("passed", 0))
    failed = int(result.get("failed", 0))
    skipped = int(result.get("skipped", 0))
    status = "PASS" if failed == 0 and total > 0 else "FAIL" if failed > 0 else "NO TESTS"
    print(f"  top-level contracts: {passed}/{total} passed, {failed} failed, {skipped} skipped — {status}")
    return failed == 0 and total > 0


def _flow_feedback_path() -> str:
    return os.path.join(os.path.dirname(__file__), "specs", "flow_feedback.json")


def _feedback_item(
    uid: str,
    message: str,
    *,
    detected_at_layer: str,
    feedback_target_layer: str,
    severity: str = "blocker",
) -> Dict[str, str]:
    return {
        "uid": uid,
        "severity": severity,
        "message": message,
        "detected_at_layer": detected_at_layer,
        "feedback_target_layer": feedback_target_layer,
    }


def _write_flow_feedback(status: str, items: List[Dict[str, str]]) -> str:
    path = _flow_feedback_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "blocker_count": len([item for item in items if item.get("severity") == "blocker"]),
        "items": items,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def _run_legacy_full_soc() -> int:
    print("\n[Legacy] Run full SoC flow")
    sys.stdout.flush()
    from earphone.design_earphone import run_legacy_full_soc_flow

    result = run_legacy_full_soc_flow()
    if result != 0:
        print("  Full SoC flow FAILED")
    return result


def _approval_requirement(gate_id: str):
    for gate in DEFAULT_APPROVAL_GATES:
        if gate.gate_id == gate_id:
            return gate
    raise KeyError(f"unknown approval gate: {gate_id}")


def _approval_gate_status(module: str) -> List[str]:
    missing: List[str] = []
    for gate in DEFAULT_APPROVAL_GATES:
        gate_module = module if gate.scope == "module" else None
        ok, _ = validate_approval(
            gate.gate_id,
            module=gate_module,
            required_artifacts=gate.artifacts,
        )
        if not ok:
            missing.append(gate.gate_id)
    return missing


def _approval_blockers(gate_id: str, module: Optional[str] = None) -> List[Dict[str, str]]:
    gate = _approval_requirement(gate_id)
    gate_module = module if gate.scope == "module" else None
    ok, reasons = validate_approval(
        gate_id,
        module=gate_module,
        required_artifacts=gate.artifacts,
    )
    if ok:
        return []

    scope = f"module {module}" if gate.scope == "module" else "top-level SoC"
    approval_file = approval_path(gate_id, module=gate_module)
    message = f"{gate_id} approval is required for {scope}: {approval_file}"
    if reasons:
        message = f"{message}; " + "; ".join(reasons)
    return [
        _feedback_item(
            f"FB-APPROVAL-{gate_id}-{module or 'soc'}",
            message,
            detected_at_layer=gate_id,
            feedback_target_layer="SpecIR",
        )
    ]


def _ensure_module_approval(module: str) -> bool:
    blockers = _approval_blockers("CP0_MODULE", module=module)
    if not blockers:
        return True
    print(f"  approval gate missing: CP0_MODULE (module={module})")
    for blocker in blockers:
        print(f"    {blocker['message']}")
    return False


def _ensure_soc_approval() -> bool:
    blockers = _approval_blockers("CP1_SOC")
    if not blockers:
        return True
    print("  approval gate missing: CP1_SOC (top-level SoC)")
    for blocker in blockers:
        print(f"    {blocker['message']}")
    return False


def _ensure_module_approvals(modules: List[str]) -> Tuple[bool, List[Dict[str, str]]]:
    blockers: List[Dict[str, str]] = []
    for module in modules:
        module_blockers = _approval_blockers("CP0_MODULE", module=module)
        if module_blockers:
            print(f"  approval gate missing: CP0_MODULE (module={module})")
            for blocker in module_blockers:
                print(f"    {blocker['message']}")
            blockers.extend(module_blockers)
    return len(blockers) == 0, blockers


def _run_top_level_soc_flow(require_approval: bool = True) -> int:
    print("\n[Top-Level] Run SoC closure flow")
    if require_approval:
        if not _ensure_soc_approval():
            return 3
    return _run_legacy_full_soc()


def main() -> int:
    parser = argparse.ArgumentParser(description="Earphone document-driven flow")
    parser.add_argument("--module", default="rv32", help="'rv32' or 'all'")
    parser.add_argument("--check", action="store_true", help="Run docs/tests without legacy full SoC flow")
    parser.add_argument("--legacy-full-soc", action="store_true", help="Run legacy full SoC flow after module checks")
    parser.add_argument("--top-level", action="store_true", help="Run top-level SoC closure after module checks")
    args = parser.parse_args()

    print("=" * 70)
    print("Earphone SoC — Document-Driven Layered Flow")
    print("=" * 70)
    print("\n[Step 1] Validate new module-level API")
    print(f"  RV32IM_ISS: {RV32IM_ISS}")
    print(f"  EarphoneRV32: {EarphoneRV32}")

    discovered = discover_modules()
    full_soc_requested = args.top_level or args.legacy_full_soc
    if full_soc_requested and args.module != "all":
        print("  Full-SoC closure checks all discovered modules.")
    module_selection = "all" if full_soc_requested else args.module
    modules = discovered if module_selection == "all" else [module_selection]
    unknown = [module for module in modules if module not in discovered]
    if unknown:
        print(f"Unknown module(s): {', '.join(unknown)}")
        return 2
    results: Dict[str, Dict[str, object]] = {}
    overall_pass = True
    feedback_items: List[Dict[str, str]] = []
    top_result: Optional[Dict[str, object]] = None

    for module in modules:
        print(f"\n[Step 2] Generate {module} per-IR-layer documents")
        try:
            module_result = run_module(module, strict=(module == "rv32") or args.check or module_selection == "all")
        except Exception as exc:
            print(f"  {module}: FAILED to generate or validate docs ({exc})")
            overall_pass = False
            feedback_items.append(
                _feedback_item(
                    f"FB-{module.upper()}-DOCGEN",
                    f"{module}: failed to generate or validate docs ({exc})",
                    detected_at_layer="docgen",
                    feedback_target_layer="SpecIR",
                )
            )
            continue

        results[module] = module_result
        for path in module_result["written"]:
            print(f"  wrote {path}")

        print(f"\n[Step 3] Run {module} per-layer tests")
        module_ok = _print_layer_results(module, module_result["layers"])
        if not module_ok:
            overall_pass = False
            for blocker in _module_blocker_summary(module, module_result["layers"]):
                print(f"  blocker: {blocker}")
                feedback_items.append(
                    _feedback_item(
                        f"FB-{module.upper()}-TEST-{len(feedback_items) + 1}",
                        blocker,
                        detected_at_layer="layer_tests",
                        feedback_target_layer="previous_layer_contract",
                    )
                )
        else:
            print("  Layer tests PASSED")

    if full_soc_requested:
        print("\n[Step 4] Run top-level SoC contract tests")
        top_result = run_top_level_contract_tests()
        top_ok = _print_top_level_result(top_result)
        if not top_ok:
            overall_pass = False
            feedback_items.append(
                _feedback_item(
                    "FB-TOP-CONTRACT-TEST",
                    "top-level SoC contract tests failed or were not discovered",
                    detected_at_layer="top_level_contract",
                    feedback_target_layer="top_level_spec",
                )
            )

    if args.check:
        feedback_path = _write_flow_feedback("pass" if overall_pass else "blocked", feedback_items)
        print("\n" + "=" * 70)
        for module, module_result in results.items():
            summary = module_result["summary"]
            print(
                f"  {module}: layers={summary['layers']} tests={summary['total']} "
                f"passed={summary['passed']} failed={summary['failed']} missing={summary['missing_tests']}"
            )
        if top_result is not None:
            print(
                f"  top: tests={top_result['total']} passed={top_result['passed']} "
                f"failed={top_result['failed']}"
            )
        print(f"  feedback={feedback_path}")
        print("Document-driven check completed." if overall_pass else "Document-driven check found blockers.")
        print("=" * 70)
        return 0 if overall_pass else 1

    if not overall_pass:
        feedback_path = _write_flow_feedback("blocked", feedback_items)
        print(f"\nFlow feedback written to {feedback_path}")
        return 1

    if full_soc_requested:
        _, module_approval_blockers = _ensure_module_approvals(modules)
        soc_approval_blockers = _approval_blockers("CP1_SOC")
        if soc_approval_blockers:
            print("  approval gate missing: CP1_SOC (top-level SoC)")
            for blocker in soc_approval_blockers:
                print(f"    {blocker['message']}")
        approval_blockers = module_approval_blockers + soc_approval_blockers
        if approval_blockers:
            feedback_path = _write_flow_feedback("blocked", approval_blockers)
            print(f"\nFlow feedback written to {feedback_path}")
            return 3
        rc = _run_top_level_soc_flow(require_approval=False)
        if rc != 0:
            feedback_path = _write_flow_feedback(
                "blocked",
                [
                    _feedback_item(
                        "FB-SOC-CLOSURE",
                        f"top-level SoC closure failed with exit code {rc}",
                        detected_at_layer="top_level_soc",
                        feedback_target_layer="SoC integration",
                    )
                ],
            )
            print(f"\nFlow feedback written to {feedback_path}")
        return rc

    feedback_path = _write_flow_feedback("pass", feedback_items)

    print("\n" + "=" * 70)
    print("Document-driven flow completed successfully.")
    print(f"  feedback={feedback_path}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
