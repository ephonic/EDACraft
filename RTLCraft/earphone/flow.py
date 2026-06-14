"""Earphone SoC — document-driven layered design entry point.

This module orchestrates the Spec2RTL flow across layered IRs and modules.
During Phase 1 of the document-driven refactor it delegates to the legacy
monolithic entry point for most operations, while explicitly exercising the
new `earphone.modules.rv32` package as the migration pilot.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from typing import List, Tuple

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# New module-level API (pilot: RV32)
from earphone.modules.rv32 import RV32IM_ISS, EarphoneRV32

# Documentation renderer
from doc_templates import render_to_file


def run_module_tests(module: str = "rv32") -> Tuple[bool, str]:
    """Run pytest for a module's test directory and return success + summary."""
    test_dir = os.path.join(
        os.path.dirname(__file__), "modules", module, "tests"
    )
    if not os.path.isdir(test_dir):
        return False, f"No tests directory for {module}"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_dir, "-q"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


def generate_rv32_module_docs() -> List[str]:
    """Generate initial module spec, test plan, and test report for RV32."""
    specs_dir = os.path.join(
        os.path.dirname(__file__), "modules", "rv32", "specs"
    )
    os.makedirs(specs_dir, exist_ok=True)

    today = date.today().isoformat()
    base = {
        "module_name": "EarphoneRV32",
        "module_id": "EARPHONE-RV32",
        "doc_id": "DOC-EARPHONE-RV32-001",
        "version": "0.1",
        "date": today,
        "author": "RTLCraft Agent",
        "owner": "Earphone SoC Team",
        "status": "Draft",
    }

    # Module spec
    module_vars = {
        **base,
        "doc_id": "DOC-EARPHONE-RV32-001",
        "purpose": "RV32IM 3-stage in-order processor core for the smart earphone SoC. Executes control code, audio DSP helpers, and peripheral configuration.",
        "feature_01": "RV32IM instruction set",
        "feature_desc_01": "Full 32-bit RISC-V integer (RV32I) and multiplication/division (M) extension support.",
        "feature_02": "3-stage pipeline",
        "feature_desc_02": "IF → ID/EX → WB with stall clock-gating for low dynamic power.",
        "clk_port": "clk",
        "clk_desc": "Core clock, target 160 MHz in 22 nm.",
        "rst_port": "rst_n",
        "rst_desc": "Asynchronous active-low reset, synchronous release.",
        "param_name": "XLEN",
        "param_type": "int",
        "param_default": "32",
        "param_range": "32",
        "param_desc": "ISA register width.",
        "theory_of_operation": "The core fetches instructions from a simple memory bus, decodes and executes in ID/EX, and writes results back in WB. Branches are resolved in ID/EX. Multiplication is single-cycle; division uses a 32-cycle iterative restoring divider.",
        "mod_clk_freq": "160 MHz",
        "mod_rst_type": "asynchronous",
        "tech": "22 nm",
        "area_goal": "< 30 k NAND2",
    }
    spec_path = os.path.join(specs_dir, "00_module_spec.md")
    render_to_file("module_spec", spec_path, module_vars)

    # Test plan
    plan_vars = {
        **base,
        "project_name": "EarphoneRV32",
        "doc_id": "TP-EARPHONE-RV32-001",
        "purpose": "Verify the EarphoneRV32 RV32IM core against its L1 ISS golden model, L3 DSL implementation, and generated Verilog.",
        "dut_name": "EarphoneRV32",
        "dut_version": "0.1",
        "dut_hier": "earphone.modules.rv32.src.dsl.EarphoneRV32",
        "spec_ref": "earphone/modules/rv32/specs/00_module_spec.md",
        "tc_name_01": "RV32IM behavior parity",
        "tc_type_01": "Directed",
        "tc_prio_01": "P0",
        "tc_obj_01": "L1 ISS produces same architectural result as reference RISC-V execution for add/sub/load/store/branch/M-ext programs.",
    }
    plan_path = os.path.join(specs_dir, "01_test_plan.md")
    render_to_file("test_plan", plan_path, plan_vars)

    # Test report (initial draft)
    report_vars = {
        **base,
        "project_name": "EarphoneRV32",
        "doc_id": "TR-EARPHONE-RV32-001",
        "test_plan_ref": "TP-EARPHONE-RV32-001",
        "overall_result": "Module tests executed via earphone/flow.py.",
        "dut_name": "EarphoneRV32",
        "dut_version": "0.1",
        "rtl_commit": "local dev",
        "tb_commit": "local dev",
    }
    report_path = os.path.join(specs_dir, "02_test_report.md")
    render_to_file("test_report", report_path, report_vars)

    return [spec_path, plan_path, report_path]


def main() -> int:
    """Run the document-driven Earphone SoC flow."""
    print("=" * 70)
    print("Earphone SoC — Document-Driven Layered Flow")
    print("=" * 70)

    # 1. Validate new module-level API
    print("\n[Step 1] Validate new module-level API")
    print(f"  RV32IM_ISS: {RV32IM_ISS}")
    print(f"  EarphoneRV32: {EarphoneRV32}")

    # 2. Generate / refresh RV32 module documents
    print("\n[Step 2] Generate RV32 module documents")
    for path in generate_rv32_module_docs():
        print(f"  wrote {path}")

    # 3. Run module-level tests
    print("\n[Step 3] Run module-level tests")
    ok, output = run_module_tests("rv32")
    print(output)
    if not ok:
        print("  Module tests FAILED")
        return 1
    print("  Module tests PASSED")

    # 4. Delegate to legacy monolithic flow for full SoC verification
    print("\n[Step 4] Run full SoC flow (legacy entry point)")
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
