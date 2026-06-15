"""Earphone SoC — document-driven layered design entry point.

This module orchestrates the Spec2RTL flow across layered IRs and modules.
During the document-driven refactor it delegates to the legacy monolithic
entry point for the full-SoC verification closure, while exercising the new
per-module, per-IR-layer package structure as the migration pilot.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Tuple

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# New module-level API (pilot: RV32)
from earphone.modules.rv32 import RV32IM_ISS, EarphoneRV32

# Document generator that extracts real design data and fills templates.
from earphone.docgen import (
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


def main() -> int:
    """Run the document-driven Earphone SoC flow."""
    print("=" * 70)
    print("Earphone SoC — Document-Driven Layered Flow")
    print("=" * 70)

    # 1. Validate new module-level API
    print("\n[Step 1] Validate new module-level API")
    print(f"  RV32IM_ISS: {RV32IM_ISS}")
    print(f"  EarphoneRV32: {EarphoneRV32}")

    # 2. Generate / refresh per-layer documents for the RV32 pilot module
    print("\n[Step 2] Generate RV32 per-IR-layer documents")
    written = generate_module_docs("rv32", strict=True)
    for path in written:
        print(f"  wrote {path}")

    # 3. Run per-layer tests and produce real test reports
    print("\n[Step 3] Run RV32 per-layer tests")
    layer_results = run_module_layer_tests("rv32")
    all_pass = True
    for layer, result in layer_results:
        total = result.get("total", 0)
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        skipped = result.get("skipped", 0)
        status = "PASS" if failed == 0 and total > 0 else "FAIL" if failed > 0 else "NO TESTS"
        print(f"  {layer}: {passed}/{total} passed, {failed} failed, {skipped} skipped — {status}")
        if failed > 0:
            all_pass = False

    if not all_pass:
        print("\n  Layer tests FAILED")
        return 1
    print("  Layer tests PASSED")

    # 4. Delegate to legacy monolithic flow for full SoC verification
    print("\n[Step 4] Run full SoC flow (legacy entry point)")
    sys.stdout.flush()
    result = subprocess.run(
        [sys.executable, "-m", "earphone.design_earphone"],
        cwd=_PROJECT_ROOT,
        text=True,
    )
    if result.returncode != 0:
        print("  Full SoC flow FAILED")
        return result.returncode

    print("\n" + "=" * 70)
    print("Document-driven flow completed successfully.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
