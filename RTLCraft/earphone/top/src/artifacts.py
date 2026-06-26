"""Artifact-generation helpers for top-level SoC closure."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from rtlgen.codegen import VerilogEmitter

from earphone.constraints import (
    build_earphone_propagator,
    generate_cocotb_test_content,
    generate_l1_tests_from_constraints,
    generate_l3_tests_from_constraints,
    propagate_module_constraints,
)
from earphone.modules.rv32 import EarphoneRV32
from earphone.modules.simd16.layer_L5_dsl.src.dsl import EarphoneSIMD16
from earphone.top.layer_L5_dsl.src.dsl import EarphoneTop
from earphone.modules.fft256.layer_L5_dsl.src.dsl import EarphoneFFT256
from earphone.modules.qspi.layer_L5_dsl.src.dsl import EarphoneQSPI
from earphone.modules.i2c.layer_L5_dsl.src.dsl import EarphoneI2C
from earphone.modules.sram256k.layer_L5_dsl.src.dsl import EarphoneSRAM256K
from earphone.modules.apb_bridge.layer_L5_dsl.src.dsl import EarphoneAPBBridge

try:
    from rtlgen.lint import VerilogLinter
except ImportError:  # pragma: no cover - optional dependency
    VerilogLinter = None


def generate_verilog_bundle() -> List[Tuple[str, bool, int, int]]:
    """Generate Verilog for all top-level closure modules and run lint."""
    print("\n" + "=" * 70)
    print("Verilog Generation")
    print("=" * 70)

    out_dir = "earphone/verilog"
    os.makedirs(out_dir, exist_ok=True)

    from design_scripts.design_fft import FFTController

    modules = [
        ("earphone_rv32", EarphoneRV32(), False),
        ("earphone_simd16", EarphoneSIMD16(), False),
        ("earphone_fft256", EarphoneFFT256(), False),
        ("fft_controller_256", FFTController(N=256, width=16, name="FFTController"), True),
        ("earphone_qspi", EarphoneQSPI(), False),
        ("earphone_i2c", EarphoneI2C(), False),
        ("earphone_sram256k", EarphoneSRAM256K(), False),
        ("earphone_apb_bridge", EarphoneAPBBridge(), False),
        ("earphone_top", EarphoneTop(), False),
    ]

    emitter = VerilogEmitter()
    linter = VerilogLinter() if VerilogLinter else None
    results: List[Tuple[str, bool, int, int]] = []

    for name, mod, use_design in modules:
        try:
            verilog = emitter.emit_design(mod) if use_design else emitter.emit(mod)
            path = os.path.join(out_dir, f"{name}.v")
            with open(path, "w", encoding="utf-8") as f:
                f.write(verilog)
            line_count = verilog.count("\n")
            lint_issues = 0
            if linter:
                try:
                    lint_result = linter.lint(verilog)
                    lint_issues = len([i for i in lint_result.issues if i.severity in ("error", "warning")])
                except Exception as exc:
                    print(f"    Lint warning for {name}: {exc}")
            results.append((name, True, line_count, lint_issues))
            print(f"  {name:25s}  {line_count:5d} lines  lint_issues={lint_issues}")
        except Exception as exc:
            results.append((name, False, 0, 0))
            print(f"  {name:25s}  FAIL: {exc}")

    return results


def build_constraint_artifacts() -> Dict[str, str]:
    """Generate cocotb tests from propagated constraints."""
    print("\n" + "=" * 70)
    print("cocotb Test Generation (Intent-Driven)")
    print("=" * 70)

    out_dir = "earphone/tb/cocotb"
    os.makedirs(out_dir, exist_ok=True)

    propagator = build_earphone_propagator()
    modules = [
        ("EarphoneRV32", EarphoneRV32()),
        ("EarphoneSIMD16", EarphoneSIMD16()),
    ]

    all_constraints = []
    for _, mod in modules:
        all_constraints.extend(propagate_module_constraints(mod, propagator))

    files = generate_cocotb_test_content(all_constraints)
    for fname, content in files.items():
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  wrote {path}")

    return files


def run_intent_driven_tests() -> Tuple[bool, list]:
    """Run L1 and L3 tests derived from constraints."""
    print("\n" + "=" * 70)
    print("Intent-Driven Tests")
    print("=" * 70)

    propagator = build_earphone_propagator()
    modules = [
        ("EarphoneRV32", EarphoneRV32()),
        ("EarphoneSIMD16", EarphoneSIMD16()),
    ]

    all_constraints = []
    for _, mod in modules:
        all_constraints.extend(propagate_module_constraints(mod, propagator))

    results = []

    print("\n[L1 intent-driven tests]")
    for test_name, test_fn in generate_l1_tests_from_constraints(all_constraints):
        try:
            ok = test_fn()
            results.append((test_name, ok))
            print(f"  {test_name:40s} {'PASS' if ok else 'FAIL'}")
        except Exception as exc:
            results.append((test_name, False))
            print(f"  {test_name:40s} FAIL: {exc}")

    print("\n[L3 intent-driven tests]")
    for test_name, test_fn in generate_l3_tests_from_constraints(all_constraints):
        try:
            ok = test_fn()
            results.append((test_name, ok))
            print(f"  {test_name:40s} {'PASS' if ok else 'FAIL'}")
        except Exception as exc:
            results.append((test_name, False))
            print(f"  {test_name:40s} FAIL: {exc}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {name:40s} {'PASS' if ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)

    return passed == len(results), results


__all__ = ["generate_verilog_bundle", "build_constraint_artifacts", "run_intent_driven_tests"]
