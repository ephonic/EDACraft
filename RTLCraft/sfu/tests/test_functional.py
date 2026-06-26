"""Functional and emitted-RTL verification for the pipelined FP16 SFU."""

from __future__ import annotations

import random
import subprocess

import pytest

from rtlgen_x.dsl import VerilogEmitter, lower_legacy_module_to_sim
from rtlgen_x.ppa import PpaGoals, advise_ppa, analyze_module_ppa
from rtlgen_x.sim import PythonSimulator, run_legacy_rtl_cosim

from sfu.driver import ALL_OPS, random_cases, reset_sim, run_one, run_stream
from sfu.dsl import Fp16Sfu
from sfu.iverilog_cosim import build_vectors, directed_vectors, emit_rtl, run as run_iverilog_cosim
from sfu.reference import (
    OP_COS,
    OP_RELU,
    OP_SIGMOID,
    OP_SIN,
    OP_TANH,
    eval_fp16_sfu_scalar,
)


def test_reference_directed_examples():
    vectors = (
        (OP_RELU, 0xBC00, 0x0000),
        (OP_RELU, 0x3C00, 0x3C00),
        (OP_SIGMOID, 0x3C00, 0x39D9),
        (OP_TANH, 0xBC00, 0xBA17),
        (OP_SIN, 0x3C00, 0x3ABB),
        (OP_COS, 0x3C00, 0x3853),
    )
    for op, operand, expected in vectors:
        assert eval_fp16_sfu_scalar(op, operand) == expected


def test_lowered_python_runtime_directed():
    sim = PythonSimulator(lower_legacy_module_to_sim(Fp16Sfu()).module)
    reset_sim(sim)

    vectors = (
        (OP_RELU, 0xBC00),
        (OP_RELU, 0x3C00),
        (OP_SIGMOID, 0x3C00),
        (OP_TANH, 0xBC00),
        (OP_SIN, 0x3C00),
        (OP_COS, 0x3C00),
    )
    for op, operand in vectors:
        assert run_one(sim, op, operand) == eval_fp16_sfu_scalar(op, operand)


def test_lowered_python_runtime_stream_random():
    rng = random.Random(0x5F17A11)
    cases = list(random_cases(rng, 128))
    expected = [eval_fp16_sfu_scalar(op, operand) for op, operand in cases]

    sim = PythonSimulator(lower_legacy_module_to_sim(Fp16Sfu()).module)
    reset_sim(sim)
    assert run_stream(sim, cases) == expected


def test_all_ops_are_covered():
    assert set(ALL_OPS) == {OP_RELU, OP_SIGMOID, OP_TANH, OP_SIN, OP_COS}


def test_emitted_rtl_contains_expected_structures():
    text = VerilogEmitter().emit(Fp16Sfu())
    assert "module fp16_sfu" in text
    assert "sig_lut" in text
    assert "cos_lut" in text
    assert ">>>" in text


def test_iverilog_directed_cosim():
    assert run_iverilog_cosim(directed_vectors(), tag="pytest_directed")


def test_iverilog_streaming_cosim_smoke():
    assert run_iverilog_cosim(build_vectors(4, 20260621), tag="pytest_stream4")


def test_generic_cosim_supports_valid_gated_sfu_stream():
    vectors = tuple(
        {"in_valid": 1, "op": op, "operand": operand}
        for op, operand, _expected in directed_vectors()
    )
    report = run_legacy_rtl_cosim(
        Fp16Sfu(),
        vectors,
        valid_signal="out_valid",
        flush_cycles=Fp16Sfu.LATENCY + 2,
        flush_inputs={"in_valid": 0, "op": 0, "operand": 0},
        build_dir="sfu/build/generic_cosim",
    )

    assert report.skipped_reason is None
    assert report.legacy_matches_rtl is True
    assert report.compiled_matches_rtl is True
    assert report.mismatches == ()
    assert [step["result"] for step in report.rtl_trace] == [expected for _op, _operand, expected in directed_vectors()]


def test_emitted_rtl_compiles_under_iverilog(tmp_path):
    compiler = subprocess.run(["iverilog", "-V"], capture_output=True, text=True)
    if compiler.returncode != 0:
        pytest.skip("iverilog not installed")

    rtl = emit_rtl("pytest_compile")
    out = tmp_path / "fp16_sfu_compile.vvp"
    cp = subprocess.run(["iverilog", "-g2012", "-o", str(out), str(rtl)], capture_output=True, text=True)
    assert cp.returncode == 0, f"iverilog compile failed:\n{cp.stderr}"


def test_sfu_ppa_analysis_surfaces_memory_and_multiplier_tradeoffs():
    stats = analyze_module_ppa(Fp16Sfu())
    assert stats.module_name == "fp16_sfu"
    assert stats.memory_count == 4
    assert stats.memory_bits == 4 * 32 * 54
    assert stats.small_memory_count == 4
    assert stats.max_memory_width == 54
    assert stats.multiplier_ops >= 4
    assert max(stats.widest_multiplier_operand_widths) >= 18

    report = advise_ppa(
        module=Fp16Sfu(),
        goals=PpaGoals(priority="timing_first", max_logic_depth=8, max_memory_bits=4096, max_state_bits=512),
    )
    titles = [rec.title for rec in report.recommendations]
    assert "Consolidate many small lookup memories" in titles
    assert "Audit multiplier-heavy stages" in titles
