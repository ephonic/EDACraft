"""Earphone SoC — document-driven layered design entry point.

This module orchestrates the Spec2RTL flow across layered IRs and modules.
During the document-driven refactor it delegates to the legacy monolithic
entry point for the full-SoC verification closure, while exercising the new
per-module, per-IR-layer package structure as the migration pilot.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
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


def _run_legacy_full_soc() -> int:
    print("\n[Legacy] Run full SoC flow")
    sys.stdout.flush()
    result = subprocess.run(
        [sys.executable, "-m", "earphone.design_earphone"],
        cwd=_PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        print("  Full SoC flow FAILED")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Earphone document-driven flow")
    parser.add_argument("--module", default="rv32", help="'rv32' or 'all'")
    parser.add_argument("--check", action="store_true", help="Run docs/tests without legacy full SoC flow")
    parser.add_argument("--legacy-full-soc", action="store_true", help="Run legacy full SoC flow after module checks")
    args = parser.parse_args()

    print("=" * 70)
    print("Earphone SoC — Document-Driven Layered Flow")
    print("=" * 70)
    print("\n[Step 1] Validate new module-level API")
    print(f"  RV32IM_ISS: {RV32IM_ISS}")
    print(f"  EarphoneRV32: {EarphoneRV32}")

    discovered = discover_modules()
    modules = discovered if args.module == "all" else [args.module]
    unknown = [module for module in modules if module not in discovered]
    if unknown:
        print(f"Unknown module(s): {', '.join(unknown)}")
        return 2
    results: Dict[str, Dict[str, object]] = {}
    overall_pass = True

    for module in modules:
        print(f"\n[Step 2] Generate {module} per-IR-layer documents")
        try:
            module_result = run_module(module, strict=(module == "rv32") or args.check or args.module == "all")
        except Exception as exc:
            print(f"  {module}: FAILED to generate or validate docs ({exc})")
            overall_pass = False
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
        else:
            print("  Layer tests PASSED")

    if args.check:
        print("\n" + "=" * 70)
        for module, module_result in results.items():
            summary = module_result["summary"]
            print(
                f"  {module}: layers={summary['layers']} tests={summary['total']} "
                f"passed={summary['passed']} failed={summary['failed']} missing={summary['missing_tests']}"
            )
        print("Document-driven check completed." if overall_pass else "Document-driven check found blockers.")
        print("=" * 70)
        return 0 if overall_pass else 1

    if args.legacy_full_soc or args.module == "rv32":
        rc = _run_legacy_full_soc()
        if rc != 0:
            return rc
    elif not overall_pass:
        return 1

    print("\n" + "=" * 70)
    print("Document-driven flow completed successfully.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
