"""Functional verification for the compact GPU SM.

Tests cover:
  * golden reference model directed examples
  * lowered Python simulator parity against the reference
  * emitted RTL cosim through iverilog
  * PPA structural analysis
  * generated SV/UVM collateral packaging
"""

from __future__ import annotations

from pathlib import Path

import random
import subprocess

import pytest

from rtlgen_x.dsl import EmitProfile, VerilogEmitter, lower_dsl_module_to_sim
from rtlgen_x.ppa import PpaGoals, advise_ppa, analyze_module_ppa
from rtlgen_x.sim import PythonSimulator
from rtlgen_x.verify import (
    PythonUvmSequenceItem,
    generate_uvm_collateral,
    generate_uvm_runtime_bundle,
    probe_iverilog_uvm_collateral,
    run_python_uvm_test,
    smoke_test_generated_reference_model,
)

from gpu_sm.driver import (
    collect_writebacks,
    directed_program,
    random_program,
    reset_sim,
    run_program,
)
from gpu_sm.dsl import GpuSm
from gpu_sm.iverilog_cosim import run as run_iverilog_cosim
from gpu_sm.reference import (
    OP_LOAD_IMM,
    OP_SIMD_ADD,
    OP_SIMD_MUL,
    OP_SIMD_SUB,
    GpuSmRef,
    Instruction,
)


def _step_dict(sim, instr_valid: int = 0, instr: int = 0):
    return sim.step({"clk": 0, "rst": 0, "instr_valid": instr_valid, "instr": instr})


def test_reference_load_imm_and_simd():
    """Golden reference: load-immediate followed by SIMD add."""
    ref = GpuSmRef()
    ref.reset()

    i1 = Instruction.encode(OP_SIMD_ADD, 0, 3, 1, 2, 0, 0)
    # Sanity: decode round-trips
    decoded = Instruction.decode(i1)
    assert decoded.opcode == OP_SIMD_ADD
    assert decoded.dst == 3
    assert decoded.src0 == 1
    assert decoded.src1 == 2

    ref.step({"instr_valid": 1, "instr": Instruction.encode(OP_LOAD_IMM, 0, 1, 0, 0, 0, 5)})
    ref.step({"instr_valid": 0, "instr": 0})
    ref.step({"instr_valid": 1, "instr": Instruction.encode(OP_LOAD_IMM, 0, 2, 0, 0, 0, 7)})
    ref.step({"instr_valid": 0, "instr": 0})
    ref.step({"instr_valid": 1, "instr": Instruction.encode(OP_SIMD_ADD, 0, 3, 1, 2, 0, 0)})
    out = ref.step({"instr_valid": 0, "instr": 0})

    assert out["out_valid"] == 1
    assert out["out_reg"] == 3
    assert out["out_data"] == 0x000C000C000C000C


def test_lowered_python_runtime_directed():
    """Lowered SimModule running on PythonSimulator matches the reference."""
    module = lower_dsl_module_to_sim(GpuSm()).module
    sim = PythonSimulator(module)
    reset_sim(sim)

    ref = GpuSmRef()
    ref.reset()

    program = directed_program()
    ref_outputs = run_program(ref, program)
    sim_outputs = run_program(sim, program)

    assert collect_writebacks(ref_outputs) == collect_writebacks(sim_outputs)


def test_iverilog_cosim_directed():
    """Emitted RTL driven by iverilog matches the golden reference."""
    assert run_iverilog_cosim(directed_program(), tag="pytest_directed")


def test_python_uvm_smoke():
    """Python-UVM style verification on the lowered module."""
    module = lower_dsl_module_to_sim(GpuSm())
    program = directed_program()
    sequence = [
        PythonUvmSequenceItem(inputs={"clk": 0, "rst": 0, "instr_valid": v, "instr": i}, label=f"p{t}")
        for t, (v, i) in enumerate(program)
    ]
    # Append drain NOPs
    for _ in range(16):
        sequence.append(PythonUvmSequenceItem(inputs={"clk": 0, "rst": 0, "instr_valid": 0, "instr": 0}, label="drain"))

    report = run_python_uvm_test(
        module,
        sequence,
        name="gpu_sm_uvm_smoke",
        reference_model=GpuSmRef(),
    )
    assert report.passed is True


def test_emitted_rtl_contains_expected_structures():
    text = VerilogEmitter().emit(GpuSm())
    assert "module gpu_sm" in text
    assert "reg_file_0" in text
    assert "shared_mem" in text
    assert "sfu_lut" in text


def test_emitted_rtl_review_profile_matches_readability_snapshot():
    emitted = VerilogEmitter(profile=EmitProfile.review()).emit(GpuSm())

    expected_markers = (
        "// Module: gpu_sm",
        "// Storage declarations",
        "reg [63:0] reg_file_0 [0:15];",
        "reg [63:0] reg_file_1 [0:15];",
        "reg [15:0] shared_mem [0:255];",
        "reg [15:0] sfu_lut [0:63];",
        "// Internal declarations",
        "logic [3:0] dec_opcode;",
        "logic [63:0] simd_result;",
        "logic [63:0] wb_data;",
        "// Combinational logic",
        "// Comb: busy, dec_dst, dec_imm (+9)",
        "// Comb: simd_a_0, simd_a_1, simd_a_2 (+14)",
        "// Comb: gemm_a_0, gemm_a_1, gemm_a_2 (+26)",
        "// Comb: sfu_a_0, sfu_a_1, sfu_a_2 (+10)",
        "// Comb: out_data, out_reg, out_valid (+1)",
        "assign out_valid = out_valid_reg;",
        "assign out_data = out_data_reg;",
        "// Sequential logic",
        "// Seq timing: clk=clk, reset=rst (sync, active-high)",
        "// Seq: out_data_reg, out_reg_reg, out_valid_reg (+1)",
        "always @(posedge clk) begin",
    )
    last_index = -1
    for marker in expected_markers:
        index = emitted.find(marker)
        assert index >= 0, f"missing readability marker: {marker}"
        assert index > last_index, f"marker out of order: {marker}"
        last_index = index

    assert "Comb: Comb:" not in emitted
    assert "Seq: Seq:" not in emitted
    assert "_cse_" not in emitted


def test_emitted_rtl_compiles_under_iverilog(tmp_path):
    compiler = subprocess.run(["iverilog", "-V"], capture_output=True, text=True)
    if compiler.returncode != 0:
        pytest.skip("iverilog not installed")

    rtl_path = tmp_path / "gpu_sm_compile.v"
    rtl_path.write_text(VerilogEmitter().emit(GpuSm()), encoding="utf-8")
    out = tmp_path / "gpu_sm_compile.vvp"
    cp = subprocess.run(["iverilog", "-g2012", "-o", str(out), str(rtl_path)], capture_output=True, text=True)
    assert cp.returncode == 0, f"iverilog compile failed:\n{cp.stderr}"

    review_rtl_path = tmp_path / "gpu_sm_compile_review.v"
    review_rtl_path.write_text(
        VerilogEmitter(profile=EmitProfile.review()).emit(GpuSm()),
        encoding="utf-8",
    )
    review_out = tmp_path / "gpu_sm_compile_review.vvp"
    review_cp = subprocess.run(
        ["iverilog", "-g2012", "-o", str(review_out), str(review_rtl_path)],
        capture_output=True,
        text=True,
    )
    assert review_cp.returncode == 0, f"iverilog compile failed for review profile:\n{review_cp.stderr}"


def test_ppa_analysis_surfaces_compute_and_memory_tradeoffs():
    stats = analyze_module_ppa(GpuSm())
    assert stats.module_name == "gpu_sm"
    assert stats.memory_count >= 3  # 2 register files + shared mem + LUT
    assert stats.state_bits > 0
    assert stats.multiplier_ops >= 8  # SIMD*4 + GEMM*4

    report = advise_ppa(
        module=GpuSm(),
        goals=PpaGoals(priority="balanced", max_logic_depth=12, max_state_bits=4096),
    )
    titles = [rec.title for rec in report.recommendations]
    assert any("multiplier" in t.lower() or "memory" in t.lower() or "pipeline" in t.lower() for t in titles)


def test_uvm_collateral_generates_cleanly():
    collateral = generate_uvm_collateral(GpuSm(), clock_name="clk")
    artifact_paths = " ".join(a.path for a in collateral.artifacts)
    assert "gpu_sm_if" in artifact_paths
    assert "gpu_sm_agent" in artifact_paths


def test_uvm_runtime_bundle_smoke():
    bundle = generate_uvm_runtime_bundle(GpuSm(), clock_name="clk")
    artifacts = bundle.artifact_map()
    assert any("dut" in k for k in artifacts)
    assert any("top" in k for k in artifacts)
    assert any("run_vcs" in k for k in artifacts)


def test_generated_reference_model_smokes():
    from rtlgen_x.verify import write_uvm_runtime_bundle
    import tempfile
    bundle = generate_uvm_runtime_bundle(GpuSm(), clock_name="clk")
    with tempfile.TemporaryDirectory() as tmpdir:
        write_uvm_runtime_bundle(bundle, tmpdir, include_runtime_package=True)
        ref_model_path = next(Path(tmpdir) / k for k in bundle.artifact_map() if "ref_model" in k)
        report = smoke_test_generated_reference_model(
            str(ref_model_path),
            inputs={"clk": 0, "rst": 0, "instr_valid": 0, "instr": 0},
        )
        assert report.predicted is not None
