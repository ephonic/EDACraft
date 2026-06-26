"""Functional verification for the fully-pipelined 128-bit Barrett modular multiplier.

Verification strategy
---------------------
The golden Python reference model remains the mathematical source of truth, and
the design is exercised through both:

  1. the lowered rtlgen_x executable model, and
  2. iverilog on the emitted Verilog.

This keeps the DSL/simulator path and the emitted RTL path honest at the same
time.
"""

from __future__ import annotations

import os
import random

import pytest

from crypto.barrett128.reference import (
    barrett_constant,
    barrett_reduce,
    is_valid_modulus,
    modmul,
    K,
)

# A representative full-width 128-bit modulus (MSB set), Barrett-valid.
N_FULL = (1 << 127) | 0x123456789ABCDEF0123456789ABCDEF


# ---------------------------------------------------------------------------
# 0. Golden reference model self-consistency (always runs)
# ---------------------------------------------------------------------------

def test_reference_modulus_constraint():
    assert is_valid_modulus(N_FULL)
    assert not is_valid_modulus(7)  # tiny modulus violates the precondition


def test_reference_barrett_constant_width():
    m = barrett_constant(N_FULL)
    assert m.bit_length() <= K + 1   # exactly 129 bits for a full-width N


@pytest.mark.parametrize("a,b", [
    (0, 0), (1, 1), (N_FULL - 1, 1), (N_FULL - 1, N_FULL - 1),
    ((1 << 128) - 1, (1 << 128) - 1), (1 << 64, 1 << 64),
])
def test_reference_matches_python_mod(a, b):
    """The Barrett reference must agree with Python's `%` for full-width N."""
    assert modmul(a, b, N_FULL) == (a * b) % N_FULL


def test_reference_random_matches_python_mod():
    rng = random.Random(0xC0FFEE)
    mism = 0
    for _ in range(500):
        a = rng.getrandbits(K)
        b = rng.getrandbits(K)
        if modmul(a, b, N_FULL) != (a * b) % N_FULL:
            mism += 1
    assert mism == 0


def test_reference_result_in_range():
    rng = random.Random(20260620)
    for _ in range(200):
        n = rng.getrandbits(K - 1) | (1 << (K - 1))  # full-width modulus
        a = rng.getrandbits(K)
        b = rng.getrandbits(K)
        r = modmul(a, b, n)
        assert 0 <= r < n


# ---------------------------------------------------------------------------
# 1. Bundled-sim functional checks
# ---------------------------------------------------------------------------

def test_bundled_sim_directed():
    from rtlgen_x.dsl import lower_legacy_module_to_sim
    from rtlgen_x.sim import PythonSimulator
    from crypto.barrett128 import BarrettModMul
    from crypto.barrett128.driver import reset_sim, run_one
    sim = PythonSimulator(lower_legacy_module_to_sim(BarrettModMul()).module)
    reset_sim(sim)
    assert run_one(sim, 2, 3, N_FULL) == modmul(2, 3, N_FULL)


def test_bundled_sim_back_to_back_stream():
    from rtlgen_x.dsl import lower_legacy_module_to_sim
    from rtlgen_x.sim import PythonSimulator
    from crypto.barrett128 import BarrettModMul
    from crypto.barrett128.driver import random_cases, reset_sim, run_stream

    rng = random.Random(0xC0FFEE)
    cases = list(random_cases(rng, 6))
    expected = [modmul(a, b, n, m) for a, b, n, m in cases]
    sim = PythonSimulator(lower_legacy_module_to_sim(BarrettModMul()).module)
    reset_sim(sim)
    assert run_stream(sim, cases) == expected


# ---------------------------------------------------------------------------
# 2. iverilog streaming cosim
# ---------------------------------------------------------------------------

def test_iverilog_directed_cosim():
    if os.environ.get("RTLGEN_X_SKIP_COSIM"):
        pytest.skip("RTLGEN_X_SKIP_COSIM set")
    from crypto.barrett128.tests.iverilog_cosim import run
    assert run(vec_count=16, seed=20260620)


def test_iverilog_streaming_cosim_smoke():
    if os.environ.get("RTLGEN_X_SKIP_COSIM"):
        pytest.skip("RTLGEN_X_SKIP_COSIM set")
    from crypto.barrett128.tests.iverilog_cosim import run
    assert run(vec_count=100, seed=1)


# ---------------------------------------------------------------------------
# 3. Emitted-RTL structural sanity (iverilog compiles the pipeline)
# ---------------------------------------------------------------------------

def test_emitted_rtl_compiles():
    """The emitted pipeline Verilog must at least compile under iverilog."""
    if os.environ.get("RTLGEN_X_SKIP_COSIM"):
        pytest.skip("RTLGEN_X_SKIP_COSIM set")
    import subprocess
    from pathlib import Path
    from rtlgen_x.dsl import VerilogEmitter
    from crypto.barrett128 import BarrettModMul
    build = Path("crypto/barrett128/build/compile_check")
    build.mkdir(parents=True, exist_ok=True)
    rtl = build / "barrett_mod_mul.v"
    rtl.write_text(VerilogEmitter().emit(BarrettModMul()), encoding="utf-8")
    out = build / "c.vvp"
    cp = subprocess.run(["iverilog", "-g2012", "-o", str(out), str(rtl)],
                        capture_output=True, text=True)
    assert cp.returncode == 0, f"iverilog compile failed:\n{cp.stderr}"
