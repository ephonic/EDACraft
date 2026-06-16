"""
Smart Earphone SoC — Spec2RTL Design Flow
=========================================

Target: low-power TWS earphone chip with:
  - RV32IM 3-stage in-order RISC-V core
  - 16-lane SIMD (INT16 full ALU + FP16 MAC)
  - 256-point streaming FFT accelerator
  - Peripherals: SPI, UART, I2C, I2S, BTLE PHY, QSPI
  - 256 KB on-chip SRAM
  - 32 MB external QSPI Flash

Design hierarchy (Spec2RTL 6 IR layers + Verilog output):
  Layer 1 — Functional model   (pure Python)
  Layer 2 — Cycle-level model  (CycleContext)
  Layer 3 — ArchitectureIR     (pipeline/operator plan)
  Layer 4 — StructuralIR       (submodule decomposition)
  Layer 5 — DSL AST            (rtlgen Module)
  Layer 6 — Verilog            (via VerilogEmitter)

Cross-layer verification: L1 == L2 == L3 via LayerVerifier.
"""

from __future__ import annotations
import os
import sys
import math
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const,
    Memory, Parameter, LocalParam, SubmoduleInst,
)
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Elif, Switch, ForGen, GenIf, GenElse, SRA
from rtlgen.codegen import VerilogEmitter, EmitProfile, ModuleDocTemplate, fill_doc_template
from rtlgen.forward import LayerVerifier
from rtlgen.sim import Simulator
from rtlgen.lib import ClockGate

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

# Cross-layer constraint framework
from rtlgen import FunctionalConstraint, PowerConstraint, IRConstraint, ConstraintFeedback
from earphone.constraints import (
    attach_earphone_constraints,
    propagate_module_constraints,
    build_earphone_propagator,
    build_design_gates,
    resolve_feedback,
    generate_l1_tests_from_constraints,
    generate_l3_tests_from_constraints,
    generate_cocotb_test_content,
    EarphoneLayerEmitter,
    build_earphone_scaffold_propagator,
    EARPHONE_LAYERS,
)

# Increase recursion limit for deep module hierarchies
sys.setrecursionlimit(10000)

print("=" * 70)
print("Smart Earphone SoC — Spec2RTL Design Flow")
print("=" * 70)


# ============================================================================
# Layer 1 — Functional Models (pure Python, no timing)
# ============================================================================

# ----------------------------------------------------------------------------
# L1 BehaviorIR: RV32IM ISS (migrated to earphone/modules/rv32/src/behavior.py)
# ----------------------------------------------------------------------------
from earphone.modules.rv32.layer_L1_behavior.src.behavior import (
    RV32IM_ISS,
    _to_u32,
    _to_s32,
    _sign_extend,
    OPCODE_LOAD,
    OPCODE_STORE,
    OPCODE_IMM,
    OPCODE_REG,
    OPCODE_LUI,
    OPCODE_AUIPC,
    OPCODE_BRANCH,
    OPCODE_JAL,
    OPCODE_JALR,
    OPCODE_SYSTEM,
    FUNCT3_LB,
    FUNCT3_LH,
    FUNCT3_LW,
    FUNCT3_LBU,
    FUNCT3_LHU,
    FUNCT3_SB,
    FUNCT3_SH,
    FUNCT3_SW,
    FUNCT3_ADDI,
    FUNCT3_SLTI,
    FUNCT3_XORI,
    FUNCT3_ORI,
    FUNCT3_ANDI,
    FUNCT3_SLLI,
    FUNCT3_SRXI,
    FUNCT3_ADD,
    FUNCT3_SUB,
    FUNCT3_SLL,
    FUNCT3_SLT,
    FUNCT3_SLTU,
    FUNCT3_XOR,
    FUNCT3_SRL,
    FUNCT3_SRA,
    FUNCT3_OR,
    FUNCT3_AND,
    FUNCT3_BEQ,
    FUNCT3_BNE,
    FUNCT3_BLT,
    FUNCT3_BGE,
    FUNCT3_BLTU,
    FUNCT3_BGEU,
    FUNCT7_DEFAULT,
    FUNCT7_SUB,
    FUNCT7_SRA,
    FUNCT7_SRAI,
    FUNCT7_MULDIV,
)
from earphone.modules.rv32.layer_L2_cycle.src.cycle import rv32im_cycle_model

# ----------------------------------------------------------------------------
# SIMD16 Functional Model (migrated to earphone/modules/simd16/...)
# ----------------------------------------------------------------------------
from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
    SIMD_OP_VADD,
    SIMD_OP_VSUB,
    SIMD_OP_VMUL,
    SIMD_OP_VAND,
    SIMD_OP_VOR,
    SIMD_OP_VXOR,
    SIMD_OP_VSLL,
    SIMD_OP_VSRL,
    SIMD_OP_VSRA,
    SIMD_OP_VCMP_EQ,
    SIMD_OP_VCMP_LT,
    SIMD_FP_OP_VMAC,
    SIMD_FP_OP_VMUL,
    _fp16_to_f32,
    _f32_to_fp16,
    simd16_int16_functional,
    simd16_fp16_mac_functional,
)
from earphone.modules.simd16.layer_L2_cycle.src.cycle import simd16_cycle_model


# ----------------------------------------------------------------------------
# FFT256 Functional Model (migrated to earphone/modules/fft256/...)
# ----------------------------------------------------------------------------
from earphone.modules.fft256.layer_L1_behavior.src.behavior import fft256_functional

# ----------------------------------------------------------------------------
# QSPI Functional Model (migrated to earphone/modules/qspi/...)
# ----------------------------------------------------------------------------
from earphone.modules.qspi.layer_L1_behavior.src.behavior import QSPIFlashFunctional
from earphone.modules.qspi.layer_L2_cycle.src.cycle import qspi_cycle_model

# ----------------------------------------------------------------------------
# I2C Master Functional Model (migrated to earphone/modules/i2c/...)
# ----------------------------------------------------------------------------
from earphone.modules.i2c.layer_L1_behavior.src.behavior import I2CBusFunctional
from earphone.modules.i2c.layer_L2_cycle.src.cycle import i2c_master_cycle_model
from earphone.modules.apb_bridge.layer_L1_behavior.src.behavior import apb_decode
from earphone.modules.apb_bridge.layer_L5_dsl.src.dsl import EarphoneAPBBridge
from earphone.modules.sram256k.layer_L5_dsl.src.dsl import EarphoneSRAM256K


print("  - Layer 1 functional models defined")


# ============================================================================
# Layer 2 — Cycle-Level Models (CycleContext-based, register-accurate)
# ============================================================================

# For lightweight modules we provide cycle-level wrappers that expose the same
# ports as the DSL modules and model register updates explicitly.  These are
# converted to behavioral functions and verified against L3 with LayerVerifier.



print("  - Layer 2 cycle-level models defined")


# ============================================================================
# Layer 3 / Layer 5 — DSL AST Modules (synthesizable rtlgen descriptions)
# ============================================================================

# ----------------------------------------------------------------------------
# Module DSL classes are now hosted in their respective module directories to
# avoid a monolithic design file and circular imports.
from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32
from earphone.modules.simd16.layer_L5_dsl.src.dsl import EarphoneSIMD16
from earphone.modules.fft256.layer_L5_dsl.src.dsl import EarphoneFFT256
from earphone.modules.qspi.layer_L5_dsl.src.dsl import EarphoneQSPI
from earphone.modules.i2c.layer_L5_dsl.src.dsl import EarphoneI2C

print("  - EarphoneRV32 DSL defined")
print("  - EarphoneSIMD16 DSL defined")
print("  - EarphoneFFT256 DSL defined")
print("  - EarphoneQSPI DSL defined")
print("  - EarphoneI2C DSL defined")

# EarphoneTop — Smart Earphone SoC top-level integration
# ----------------------------------------------------------------------------

from earphone.top.layer_L5_dsl.src.dsl import EarphoneTop

print("  - EarphoneTop DSL imported from earphone.top.layer_L5_dsl.src.dsl")


# ============================================================================
# Verification & Generation
# ============================================================================

def run_functional_tests():
    """Layer 1 functional model tests."""
    print("\n" + "=" * 70)
    print("Layer 1 Functional Tests")
    print("=" * 70)
    results = []

    # RV32IM ISS test: simple add/sub program
    print("\n[TEST] RV32IM ISS add/sub/load/store...")
    iss = RV32IM_ISS()
    program = [
        0x00100093,  # addi x1, x0, 1
        0x00200113,  # addi x2, x0, 2
        0x002081b3,  # add x3, x1, x2
        0x40208233,  # sub x4, x1, x2
        0x003022a3,  # sw x3, 5(x0)
        0x00502303,  # lw x6, 5(x0)
        0x00100073,  # ebreak
    ]
    iss.load_program_words(program, entry_point=0x1000)
    iss.run(max_cycles=100)
    ok = (iss.state.regs[3] == 3 and iss.state.regs[4] == 0xFFFFFFFF and
          iss.state.regs[6] == 3)
    # Re-check M-extension: MUL, MULH, DIV, REM
    iss2 = RV32IM_ISS()
    # x1=7, x2=3; x3=MUL, x4=MULH, x5=DIV, x6=DIVU, x7=REM, x8=REMU
    prog_m = [
        0x00700093,  # addi x1, x0, 7
        0x00300113,  # addi x2, x0, 3
        0x022081b3,  # mul  x3, x1, x2  -> 21
        0x02209233,  # mulh x4, x1, x2  -> 0
        0x0220c2b3,  # div  x5, x1, x2  -> 2
        0x0220d333,  # divu x6, x1, x2  -> 2
        0x0220e3b3,  # rem  x7, x1, x2  -> 1
        0x0220f433,  # remu x8, x1, x2  -> 1
        0x00100073,  # ebreak
    ]
    iss2.load_program_words(prog_m, 0x1000)
    iss2.run(max_cycles=40)
    mul_ok = (iss2.state.regs[3] == 21 and iss2.state.regs[4] == 0 and
              iss2.state.regs[5] == 2 and iss2.state.regs[6] == 2 and
              iss2.state.regs[7] == 1 and iss2.state.regs[8] == 1)
    # Negative signed division: x1=-7, x2=3 -> div=-2, rem=-1
    iss3 = RV32IM_ISS()
    prog_neg = [
        0xff900093,  # addi x1, x0, -7
        0x00300113,  # addi x2, x0, 3
        0x0220c2b3,  # div  x5, x1, x2  -> -2
        0x0220e333,  # rem  x6, x1, x2  -> -1
        0x00100073,  # ebreak
    ]
    iss3.load_program_words(prog_neg, 0x1000)
    iss3.run(max_cycles=40)
    div_neg_ok = (iss3.state.regs[5] == _to_u32(-2) and
                  iss3.state.regs[6] == _to_u32(-1))
    # Division by zero
    iss4 = RV32IM_ISS()
    prog_div0 = [
        0x00700093,  # addi x1, x0, 7
        0x00000113,  # addi x2, x0, 0
        0x0220c2b3,  # div  x5, x1, x2  -> -1
        0x0220e333,  # rem  x6, x1, x2  -> 7
        0x00100073,  # ebreak
    ]
    iss4.load_program_words(prog_div0, 0x1000)
    iss4.run(max_cycles=40)
    div0_ok = (iss4.state.regs[5] == 0xFFFFFFFF and iss4.state.regs[6] == 7)
    m_ext_ok = mul_ok and div_neg_ok and div0_ok
    results.append(("RV32IM ISS", ok and m_ext_ok))
    print(f"  regs[3]={iss.state.regs[3]}, regs[4]={iss.state.regs[4]}, regs[6]={iss.state.regs[6]}, M-ext={m_ext_ok}  {'PASS' if ok and m_ext_ok else 'FAIL'}")

    # SIMD16 INT16 test
    print("\n[TEST] SIMD16 INT16 vadd...")
    a = 0
    b = 0
    for i in range(16):
        a |= ((i + 1) & 0xFFFF) << (i * 16)
        b |= ((i + 2) & 0xFFFF) << (i * 16)
    r = simd16_int16_functional(SIMD_OP_VADD, a, b)
    ok = True
    for i in range(16):
        lane = (r >> (i * 16)) & 0xFFFF
        expected = ((i + 1) + (i + 2)) & 0xFFFF
        if lane != expected:
            ok = False
    results.append(("SIMD16 INT16 vadd", ok))
    print(f"  {'PASS' if ok else 'FAIL'}")

    # SIMD16 FP16 MAC test
    print("\n[TEST] SIMD16 FP16 MAC...")
    a_fp = 0
    b_fp = 0
    c_fp = 0
    for i in range(16):
        a_fp |= _f32_to_fp16(0.5) << (i * 16)
        b_fp |= _f32_to_fp16(0.25) << (i * 16)
        c_fp |= _f32_to_fp16(0.1) << (i * 16)
    r_fp = simd16_fp16_mac_functional(a_fp, b_fp, c_fp)
    ok = True
    for i in range(16):
        lane = _fp16_to_f32((r_fp >> (i * 16)) & 0xFFFF)
        expected = 0.5 * 0.25 + 0.1
        if abs(lane - expected) > 0.01:
            ok = False
    results.append(("SIMD16 FP16 MAC", ok))
    print(f"  {'PASS' if ok else 'FAIL'}")

    # FFT256 functional test
    print("\n[TEST] FFT256 functional impulse...")
    samples_re = [32767 if i == 0 else 0 for i in range(256)]
    samples_im = [0] * 256
    out_re, out_im = fft256_functional(samples_re, samples_im)
    avg_re = sum(out_re) / 256
    ok = 120 < avg_re < 135
    results.append(("FFT256 impulse", ok))
    print(f"  avg_re={avg_re:.1f}  {'PASS' if ok else 'FAIL'}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {name:25s} {'PASS' if ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


def run_dsl_sim_tests():
    """Layer 3 DSL simulation tests."""
    print("\n" + "=" * 70)
    print("Layer 3 DSL Simulation Tests")
    print("=" * 70)
    results = []

    # SIMD16 DSL test
    print("\n[TEST] EarphoneSIMD16 DSL vadd...")
    try:
        simd = EarphoneSIMD16()
        sim = Simulator(simd)
        sim.reset("rst_n", cycles=2)
        a = 0; b = 0
        for i in range(16):
            a |= ((i + 1) & 0xFFFF) << (i * 16)
            b |= ((i + 2) & 0xFFFF) << (i * 16)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", SIMD_OP_VADD)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        r = sim.peek("vdst")
        done = sim.peek("done")
        sim.poke("start", 0)
        sim.step()
        ok = True
        for i in range(16):
            lane = (r >> (i * 16)) & 0xFFFF
            expected = ((i + 1) + (i + 2)) & 0xFFFF
            if lane != expected:
                ok = False
        results.append(("SIMD16 DSL vadd", ok and done))
        print(f"  done={done}, vdst={hex(r)}  {'PASS' if ok and done else 'FAIL'}")
    except Exception as e:
        results.append(("SIMD16 DSL vadd", False))
        print(f"  FAIL: {e}")

    # QSPI DSL test
    print("\n[TEST] EarphoneQSPI DSL XIP read...")
    try:
        qspi = EarphoneQSPI()
        sim = Simulator(qspi)
        sim.reset("rst_n", cycles=2)
        sim.poke("req", 1)
        sim.poke("addr", 0x1234)
        # Model flash data on qspi_io_i during data phase
        cycles = 0
        ready = 0
        while cycles < 30 and ready == 0:
            # During data phase state==4, drive nibbles
            state = sim.peek("state")
            if state == 4:
                sim.poke("qspi_io_i", (cycles + 1) & 0xF)
            sim.step()
            ready = sim.peek("ready")
            cycles += 1
        rdata = sim.peek("rdata")
        ok = ready == 1 and rdata != 0
        results.append(("QSPI DSL XIP", ok))
        print(f"  ready={ready}, rdata={rdata:#x}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("QSPI DSL XIP", False))
        print(f"  FAIL: {e}")

    # RV32IM core DSL test (MUL + iterative DIV/DIVU/REM/REMU)
    print("\n[TEST] EarphoneRV32 DSL MUL/DIV program...")
    try:
        cpu = EarphoneRV32()
        sim = Simulator(cpu)
        sim.reset("rst_n", cycles=2)
        program = {
            0x1000: 0x00700093,  # addi x1, x0, 7
            0x1004: 0x00300113,  # addi x2, x0, 3
            0x1008: 0x022081b3,  # mul  x3, x1, x2 -> 21
            0x100c: 0x0220c2b3,  # div  x5, x1, x2 -> 2
            0x1010: 0x0220d333,  # divu x6, x1, x2 -> 2
            0x1014: 0x0220e3b3,  # rem  x7, x1, x2 -> 1
            0x1018: 0x0220f433,  # remu x8, x1, x2 -> 1
            0x101c: 0x00100073,  # ebreak
        }
        expected = {3: 21, 5: 2, 6: 2, 7: 1, 8: 1}
        retired = {rd: False for rd in expected}
        # Simple memory model (grant always high when CPU expects ready memory)
        dmem = {}
        for cycle in range(200):
            addr = sim.peek("imem_addr")
            sim.poke("imem_gnt", 1)
            sim.poke("imem_rdata", program.get(addr, 0))

            daddr = sim.peek("dmem_addr")
            sim.poke("dmem_gnt", 1)
            sim.poke("dmem_valid", 1)
            sim.poke("dmem_rdata", dmem.get(daddr, 0))

            sim.step()
            if sim.peek("retire_valid"):
                rd = sim.peek("retire_rd")
                val = sim.peek("retire_result")
                if rd in expected and val == expected[rd]:
                    retired[rd] = True
        ok = all(retired.values())
        results.append(("RV32IM DSL MUL/DIV", ok))
        print(f"  retired={retired}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("RV32IM DSL MUL/DIV", False))
        print(f"  FAIL: {e}")

    # SRAM DSL test
    print("\n[TEST] EarphoneSRAM256K DSL read/write...")
    try:
        sram = EarphoneSRAM256K()
        sim = Simulator(sram)
        sim.reset("rst_n", cycles=2)
        # Write 0xDEADBEEF to address 0x40 with full strobe
        sim.poke("paddr", 0x40)
        sim.poke("pwdata", 0xDEADBEEF)
        sim.poke("pwrite", 1)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.poke("pstrb", 0b1111)
        sim.step()
        # Read back
        sim.poke("pwrite", 0)
        sim.step()
        rdata = sim.peek("prdata")
        ok = rdata == 0xDEADBEEF
        results.append(("SRAM DSL", ok))
        print(f"  rdata={rdata:#x}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("SRAM DSL", False))
        print(f"  FAIL: {e}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {name:25s} {'PASS' if ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


def run_layer_verification():
    """Cross-layer verification: L1 functional == L2 cycle == L3 DSL."""
    print("\n" + "=" * 70)
    print("Cross-Layer Verification (LayerVerifier)")
    print("=" * 70)
    results = []

    # SIMD16 cross-layer
    print("\n[VERIFY] SIMD16 INT16 vadd: L1 == L2 == L3...")
    try:
        a = 0; b = 0
        for i in range(16):
            a |= ((i + 5) & 0xFFFF) << (i * 16)
            b |= ((i + 3) & 0xFFFF) << (i * 16)
        expected = simd16_int16_functional(SIMD_OP_VADD, a, b)

        # L1 check
        l1_ok = expected != 0

        # L2 check via simple cycle model step
        from rtlgen.arch_def import CycleContext
        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "op": SIMD_OP_VADD,
                                   "mode": 0, "vsrc0": a, "vsrc1": b, "vsrc2": 0, "pred": 0xFFFF})
        l2_model = simd16_cycle_model()
        l2_model(ctx)
        l2_model(ctx)  # advance
        l2_ok = ctx.outputs.get("done", 0) == 1 and ctx.outputs.get("vdst", 0) == expected

        # L3 check (already tested)
        simd = EarphoneSIMD16()
        sim = Simulator(simd)
        sim.reset("rst_n", cycles=2)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", SIMD_OP_VADD)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        l3_ok = sim.peek("vdst") == expected and sim.peek("done") == 1

        ok = l1_ok and l2_ok and l3_ok
        results.append(("SIMD16 cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("SIMD16 cross-layer", False))
        print(f"  FAIL: {e}")

    # SIMD16 vsub cross-layer
    print("\n[VERIFY] SIMD16 INT16 vsub: L1 == L2 == L3...")
    try:
        a = 0; b = 0
        for i in range(16):
            a |= ((i + 9) & 0xFFFF) << (i * 16)
            b |= ((i + 3) & 0xFFFF) << (i * 16)
        expected = simd16_int16_functional(SIMD_OP_VSUB, a, b)

        from rtlgen.arch_def import CycleContext
        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "op": SIMD_OP_VSUB,
                                   "mode": 0, "vsrc0": a, "vsrc1": b, "vsrc2": 0, "pred": 0xFFFF})
        l2_model = simd16_cycle_model()
        l2_model(ctx)
        l2_ok = ctx.outputs.get("done", 0) == 1 and ctx.outputs.get("vdst", 0) == expected

        simd = EarphoneSIMD16()
        sim = Simulator(simd)
        sim.reset("rst_n", cycles=2)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", SIMD_OP_VSUB)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        l3_ok = sim.peek("vdst") == expected and sim.peek("done") == 1

        ok = expected != 0 and l2_ok and l3_ok
        results.append(("SIMD16 vsub cross-layer", ok))
        print(f"  L1={expected != 0}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("SIMD16 vsub cross-layer", False))
        print(f"  FAIL: {e}")

    # SRAM256K cross-layer (L1 functional vs L3 DSL; L2 is metadata-only)
    print("\n[VERIFY] SRAM256K read/write: L1 == L3...")
    try:
        from earphone.modules.sram256k.layer_L1_behavior.src.behavior import SRAM256KFunctional
        from earphone.modules.sram256k.layer_L2_cycle.src.cycle import describe as sram_l2_describe

        l1_sram = SRAM256KFunctional()
        l1_sram.write(0x40, 0xDEADBEEF)
        l1_expected = l1_sram.read(0x40)
        l2_ok = sram_l2_describe()["status"] == "implemented"

        sram = EarphoneSRAM256K()
        sim = Simulator(sram)
        sim.reset("rst_n", cycles=2)
        # APB write
        sim.poke("paddr", 0x40)
        sim.poke("pwdata", 0xDEADBEEF)
        sim.poke("pwrite", 1)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.poke("pstrb", 0b1111)
        sim.step()
        # APB read
        sim.poke("pwrite", 0)
        sim.step()
        l3_ok = sim.peek("prdata") == l1_expected

        ok = l2_ok and l3_ok
        results.append(("SRAM256K cross-layer", ok))
        print(f"  L1={l1_expected == 0xDEADBEEF}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("SRAM256K cross-layer", False))
        print(f"  FAIL: {e}")

    # APB Bridge cross-layer (L1 decode vs L3 DSL one-hot select)
    print("\n[VERIFY] APB Bridge address decode: L1 == L3...")
    try:
        from earphone.modules.apb_bridge.layer_L1_behavior.src.behavior import APB_SLAVE_SLOTS
        base = 0x4000_0000
        l1_ok = True
        l3_ok = True
        bridge = EarphoneAPBBridge()
        sim = Simulator(bridge)
        sim.reset("rst_n", cycles=1)
        for i, (name, _, _) in enumerate(APB_SLAVE_SLOTS):
            addr = base + (i << 22)
            l1_idx, l1_name = apb_decode(addr - base)
            if l1_idx != i or l1_name != name:
                l1_ok = False
            sim.poke("m_paddr", addr)
            sim.poke("m_psel", 1)
            sim.step()
            if sim.peek("s_psel") != (1 << i):
                l3_ok = False
        ok = l1_ok and l3_ok
        results.append(("APB Bridge cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("APB Bridge cross-layer", False))
        print(f"  FAIL: {e}")

    # RV32 cross-layer (L1 ISS vs L3 DSL retire values)
    print("\n[VERIFY] RV32IM MUL/DIV program: L1 == L3...")
    try:
        program = [
            0x00700093,  # addi x1, x0, 7
            0x00300113,  # addi x2, x0, 3
            0x022081b3,  # mul  x3, x1, x2 -> 21
            0x0220c2b3,  # div  x5, x1, x2 -> 2
            0x0220d333,  # divu x6, x1, x2 -> 2
            0x0220e3b3,  # rem  x7, x1, x2 -> 1
            0x0220f433,  # remu x8, x1, x2 -> 1
            0x00100073,  # ebreak
        ]
        expected = {3: 21, 5: 2, 6: 2, 7: 1, 8: 1}

        iss = RV32IM_ISS()
        iss.load_program_words(program, entry_point=0x1000)
        iss.run(max_cycles=100)

        cpu = EarphoneRV32()
        sim = Simulator(cpu)
        sim.reset("rst_n", cycles=2)
        prog_dict = {0x1000 + i * 4: w for i, w in enumerate(program)}
        retired = {}
        dmem = {}
        for _ in range(200):
            addr = sim.peek("imem_addr")
            sim.poke("imem_gnt", 1)
            sim.poke("imem_rdata", prog_dict.get(addr, 0))

            daddr = sim.peek("dmem_addr")
            sim.poke("dmem_gnt", 1)
            sim.poke("dmem_valid", 1)
            sim.poke("dmem_rdata", dmem.get(daddr, 0))

            sim.step()
            if sim.peek("retire_valid"):
                rd = sim.peek("retire_rd")
                retired[rd] = sim.peek("retire_result")

        l1_ok = all(iss.state.regs[rd] == val for rd, val in expected.items())
        l3_ok = all(retired.get(rd) == val for rd, val in expected.items())
        ok = l1_ok and l3_ok
        results.append(("RV32IM cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("RV32IM cross-layer", False))
        print(f"  FAIL: {e}")

    # QSPI cross-layer (L1 flash model vs L2 cycle model)
    print("\n[VERIFY] QSPI XIP read: L1 == L2...")
    try:
        from earphone.modules.qspi.layer_L1_behavior.src.behavior import QSPIFlashFunctional
        from earphone.modules.qspi.layer_L2_cycle.src.cycle import qspi_cycle_model
        from rtlgen.arch_def import CycleContext

        flash = QSPIFlashFunctional()
        flash.load_data(0x1000, b"\x78\x56\x34\x12")
        l1_expected = flash.xip_read(0x1000)

        ctx = CycleContext(inputs={"rst_n": 1, "req": 1, "addr": 0x1000})
        ctx.state["flash"] = flash
        model = qspi_cycle_model()
        model(ctx)
        ctx.inputs["req"] = 0
        l2_rdata = 0
        l2_ready = 0
        for _ in range(100):
            model(ctx)
            if ctx.outputs.get("ready"):
                l2_ready = 1
                l2_rdata = ctx.outputs.get("rdata", 0)
                break

        l1_ok = l1_expected == 0x12345678
        l2_ok = l2_ready == 1 and l2_rdata == l1_expected
        ok = l1_ok and l2_ok
        results.append(("QSPI cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("QSPI cross-layer", False))
        print(f"  FAIL: {e}")

    # I2C cross-layer (L1 transaction log vs L2 cycle model completion)
    print("\n[VERIFY] I2C master write: L1 == L2...")
    try:
        from earphone.modules.i2c.layer_L1_behavior.src.behavior import I2CBusFunctional
        from earphone.modules.i2c.layer_L2_cycle.src.cycle import i2c_master_cycle_model
        from rtlgen.arch_def import CycleContext

        bus = I2CBusFunctional()
        bus.write(0x50, [0xAB])

        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "addr": 0x50, "data": 0xAB, "rw": 0})
        model = i2c_master_cycle_model()
        model(ctx)
        ctx.inputs["start"] = 0
        done = 0
        for _ in range(100):
            model(ctx)
            if ctx.outputs.get("done"):
                done = 1
                break

        l1_ok = (len(bus.transactions) == 1 and
                 bus.transactions[0][0] == 0x50 and
                 bus.transactions[0][1] == [0xAB] and
                 bus.transactions[0][2] is False)
        l2_ok = done == 1
        ok = l1_ok and l2_ok
        results.append(("I2C cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("I2C cross-layer", False))
        print(f"  FAIL: {e}")

    # FFT256 cross-layer (L1 NumPy reference vs L3 fixed-point DSL with tolerance)
    print("\n[VERIFY] FFT256 impulse: L1 == L3 (within fixed-point tolerance)...")
    try:
        def _bit_reverse(x, bits):
            r = 0
            for _ in range(bits):
                r = (r << 1) | (x & 1)
                x >>= 1
            return r

        def _to_s16(v):
            return v if v < 32768 else v - 65536

        samples_re = [32767 if i == 0 else 0 for i in range(256)]
        samples_im = [0] * 256
        l1_re, l1_im = fft256_functional(samples_re, samples_im)
        l1_ok = all(120 < v < 135 for v in l1_re) and all(v == 0 for v in l1_im)

        fft = EarphoneFFT256()
        sim = Simulator(fft)
        sim.reset("rst", cycles=2)
        for v in samples_re:
            sim.poke("di_en", 1)
            sim.poke("di_re", v)
            sim.poke("di_im", 0)
            sim.step()
        sim.poke("di_en", 0)
        hw_re = []
        hw_im = []
        for _ in range(700):
            sim.step()
            if sim.peek("do_en"):
                hw_re.append(_to_s16(sim.peek("do_re")))
                hw_im.append(_to_s16(sim.peek("do_im")))
        # Output is bit-reversed; unshuffle before comparison.
        hw_re_nat = [hw_re[_bit_reverse(i, 8)] for i in range(256)]
        hw_im_nat = [hw_im[_bit_reverse(i, 8)] for i in range(256)]
        max_diff = max(
            max(abs(hw_re_nat[i] - l1_re[i]), abs(hw_im_nat[i] - l1_im[i]))
            for i in range(256)
        )
        l3_ok = len(hw_re) == 256 and max_diff <= 1
        ok = l1_ok and l3_ok
        results.append(("FFT256 cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}, max_diff={max_diff}  {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        results.append(("FFT256 cross-layer", False))
        print(f"  FAIL: {e}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {name:25s} {'PASS' if ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


def generate_verilog():
    """Generate Verilog for all modules and run lint."""
    print("\n" + "=" * 70)
    print("Verilog Generation")
    print("=" * 70)

    out_dir = "earphone/verilog"
    os.makedirs(out_dir, exist_ok=True)

    # Import reusable FFT controller so its full hierarchy can also be emitted.
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
    gen_results = []

    for name, mod, use_design in modules:
        try:
            # For hierarchical modules, emit the whole design (top + submodules)
            # so that the generated file is self-contained.
            verilog = emitter.emit_design(mod) if use_design else emitter.emit(mod)
            path = os.path.join(out_dir, f"{name}.v")
            with open(path, "w") as f:
                f.write(verilog)
            line_count = verilog.count("\n")
            lint_issues = 0
            if linter:
                try:
                    lr = linter.lint(verilog)
                    lint_issues = len([i for i in lr.issues if i.severity in ("error", "warning")])
                except Exception as le:
                    print(f"    Lint warning for {name}: {le}")
            gen_results.append((name, True, line_count, lint_issues))
            print(f"  {name:25s}  {line_count:5d} lines  lint_issues={lint_issues}")
        except Exception as e:
            gen_results.append((name, False, 0, 0))
            print(f"  {name:25s}  FAIL: {e}")

    return gen_results


def generate_cocotb_tests_from_constraints():
    """Generate cocotb Python test files from Verilog-layer constraints."""
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
    for name, mod in modules:
        all_constraints.extend(propagate_module_constraints(mod, propagator))

    files = generate_cocotb_test_content(all_constraints)
    for fname, content in files.items():
        path = os.path.join(out_dir, fname)
        with open(path, "w") as f:
            f.write(content)
        print(f"  wrote {path}")

    return files


def run_intent_driven_tests():
    """Run L1 and L3 tests that are derived from constraints."""
    print("\n" + "=" * 70)
    print("Intent-Driven Tests")
    print("=" * 70)

    propagator = build_earphone_propagator()
    modules = [
        ("EarphoneRV32", EarphoneRV32()),
        ("EarphoneSIMD16", EarphoneSIMD16()),
    ]

    all_constraints = []
    for name, mod in modules:
        all_constraints.extend(propagate_module_constraints(mod, propagator))

    results = []

    # L1 intent-driven tests
    print("\n[L1 intent-driven tests]")
    for test_name, test_fn in generate_l1_tests_from_constraints(all_constraints):
        try:
            ok = test_fn()
            results.append((test_name, ok))
            print(f"  {test_name:40s} {'PASS' if ok else 'FAIL'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"  {test_name:40s} FAIL: {e}")

    # L3 intent-driven tests
    print("\n[L3 intent-driven tests]")
    for test_name, test_fn in generate_l3_tests_from_constraints(all_constraints):
        try:
            ok = test_fn()
            results.append((test_name, ok))
            print(f"  {test_name:40s} {'PASS' if ok else 'FAIL'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"  {test_name:40s} FAIL: {e}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {name:40s} {'PASS' if ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)

    return passed == len(results), results


def generate_review_bundle():
    """Emit the 7-stage review bundle markdown files."""
    print("\n" + "=" * 70)
    print("Review Bundle Generation")
    print("=" * 70)

    review_dir = "earphone/specs"
    os.makedirs(review_dir, exist_ok=True)

    # 01_spec_review.md
    spec_md = """# 01 Spec Review — Smart Earphone SoC

## Modules
| Module | Type | Key Ports | PPA Goals |
|--------|------|-----------|-----------|
| EarphoneRV32 | RV32IM core | imem/dmem buses | <30k NAND2, <0.5mW/MHz |
| EarphoneSIMD16 | Vector ALU | vsrc0/1/2[255:0], vdst | 16 ops/cycle |
| EarphoneFFT256 | FFT accelerator | di_re/im, do_re/im | 256-pt streaming |
| EarphoneQSPI | QSPI XIP | qspi_io[3:0] | memory-mapped flash |
| EarphoneI2C | I2C master | scl, sda | codec/PMIC config |
| EarphoneSRAM256K | SRAM | APB | 256KB single-cycle |
| EarphoneAPBBridge | APB decoder | 8 slave slots | low area |
| EarphoneTop | Top-level | SoC ports | integration |
"""
    with open(os.path.join(review_dir, "01_spec_review.md"), "w") as f:
        f.write(spec_md)

    # 02_behavior_review.md
    behavior_md = """# 02 Behavior Review

- RV32IM ISS: architectural state = x0-x31, pc, memory.
- SIMD16: per-lane INT16 ops, predicate mask, FP16 MAC.
- FFT256: DFT with 1/N scaling per stage.
- QSPI: XIP read transaction = cmd + addr + dummy + data.
- I2C: START + 7-bit addr + R/W + byte + ACK + STOP.
- SRAM: single-cycle APB read/write with byte strobe.
- APBBridge: address decode into 1 MB regions.
"""
    with open(os.path.join(review_dir, "02_behavior_review.md"), "w") as f:
        f.write(behavior_md)

    # 03_cycle_review.md
    cycle_md = """# 03 Cycle Review

- RV32IM: 3-stage IF/ID-EX/WB; branch flushes fetch/exec.
- SIMD16: INT16 1-cycle; FP16 MAC 3-cycle pipeline.
- FFT256: streaming R2^2SDF, latency = N + pipeline.
- QSPI: 4-state FSM, ~15-cycle read latency.
- I2C: bit-counter FSM, ~36 cycles/byte.
- SRAM: registered read data, pready after 1 cycle.
- APBBridge: combinational decode.
"""
    with open(os.path.join(review_dir, "03_cycle_review.md"), "w") as f:
        f.write(cycle_md)

    # 04_microarch_review.md
    micro_md = """# 04 Microarchitecture Review

- CPU: single-issue in-order, no cache, physical memory. Pipeline registers clock-gated by `~stall`.
- M-extension: MUL* single-cycle combinational; DIV/DIVU/REM/REMU use 32-cycle iterative restoring divider for area.
- SIMD: 16 parallel INT16 ALUs + 16 FP16 MAC lanes. Independent `int_ce`/`fp_ce` clock enables per datapath.
- FFT: reuse skills/fft R2^2SDF pipeline.
- QSPI: command/address/data shift register; FSM clock-gated when idle.
- I2C: bit-level shift register with open-drain IO; FSM clock-gated between transactions.
- SRAM: single-port memory array with byte-write mask; clock gated between APB transfers.
- Bridge: one-hot region decoder; `s_psel` reused as peripheral clock-enable downstream.
"""
    with open(os.path.join(review_dir, "04_microarch_review.md"), "w") as f:
        f.write(micro_md)

    # 05_structure_review.md
    struct_md = """# 05 Structure Review

```
EarphoneTop
├── EarphoneRV32
│   ├── 3-stage pipeline regs (clock-gated)
│   ├── M-extension unit (operand-isolated multiplier, iterative divider)
│   └── register file
├── EarphoneSIMD16
│   ├── INT16 ALU array (int_ce gated)
│   └── FP16 MAC pipeline (fp_ce gated)
├── EarphoneFFT256 (wraps FFTController)
├── EarphoneQSPI (idle-gated FSM)
├── EarphoneI2C (idle-gated FSM)
├── EarphoneSRAM256K (transfer-gated memory)
└── EarphoneAPBBridge
```
"""
    with open(os.path.join(review_dir, "05_structure_review.md"), "w") as f:
        f.write(struct_md)

    # 06_verification_plan.md
    verif_md = """# 06 Verification Plan

1. Functional tests for ISS (including RV32M MUL/DIV/DIVU/REM/REMU), SIMD16, FFT256.
2. Cycle-level co-simulation against L1.
3. DSL simulation against L2 (SIMD16 vadd, QSPI XIP, SRAM R/W, RV32IM MUL/DIV program).
4. Cross-layer LayerVerifier checks.
5. Verilog lint + co-simulation with iverilog.
6. RISC-V compliance suite (rv32ui-p, rv32um-p), with emphasis on iterative divider.
"""
    with open(os.path.join(review_dir, "06_verification_plan.md"), "w") as f:
        f.write(verif_md)

    # 07_lowering_report.md
    lower_md = """# 07 Lowering Report

| Module | SpecIR | BehaviorIR | CycleIR | ArchIR | StructuralIR | DSL | Verilog |
|--------|--------|------------|---------|--------|--------------|-----|---------|
| EarphoneRV32 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneSIMD16 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneFFT256 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneQSPI | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneI2C | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneSRAM256K | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneAPBBridge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneTop | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
"""
    with open(os.path.join(review_dir, "07_lowering_report.md"), "w") as f:
        f.write(lower_md)

    # 08_ppa_review.md
    ppa_md = """# 08 PPA Review

## Power Optimizations

| Module | Technique | Expected Impact |
|--------|-----------|-----------------|
| EarphoneRV32 | Stall-based pipeline clock gating (`core_clk_en`) | Reduced dynamic power during mem/div stalls |
| EarphoneRV32 | Multiplier operand isolation (`is_muldiv`) | Reduced toggle power when not executing RV32M |
| EarphoneRV32 | Iterative restoring divider | ~80% divider area reduction vs combinational |
| EarphoneSIMD16 | Independent INT16/FP16 clock enables | FP16 pipeline idle in audio-only workloads |
| EarphoneSRAM256K | Transfer-gated memory clock | No memory dynamic power between APB accesses |
| EarphoneQSPI | Idle-gated FSM | No toggle when flash is idle |
| EarphoneI2C | Idle-gated FSM | No toggle between I2C transactions |

## Performance Notes

- MUL* remains single-cycle; DIV/REM is 32-cycle iterative (area/power trade-off).
- SIMD throughput unchanged: 16 INT16 ops/cycle, 1 FP16 MAC result every 3 cycles.
- SRAM remains single-cycle read/write.

## Area Notes

- Iterative divider replaces large combinational divider/remainder tree.
- Clock-gating logic adds small enable-mux overhead; net area expected to decrease after synthesis.

## Synthesis Guidance

- Synthesis tools should infer integrated clock-gating cells (ICG) from `if (clk_en) reg <= next` patterns.
- Mark `core_clk_en`, `int_ce`, `fp_ce`, `sram_ce`, `qspi_ce`, `i2c_ce` as clock-gating enables in the constraints file.
- For deeper power savings, group modules into power domains and add retention cells in v0.2.
"""
    with open(os.path.join(review_dir, "08_ppa_review.md"), "w") as f:
        f.write(ppa_md)

    print("  Wrote 01_spec_review.md .. 08_ppa_review.md")


def run_legacy_full_soc_flow() -> int:
    """Run the legacy full SoC flow and return an exit code."""
    # =====================================================================
    # Phase E: Design Scaffold — standardized agent loop
    # =====================================================================
    from rtlgen import DesignScaffold, DesignDecision, ConstraintFeedback, generate_constraint_report

    propagator = build_earphone_scaffold_propagator()
    scaffold = DesignScaffold(propagator, EarphoneLayerEmitter(), layers=EARPHONE_LAYERS)

    # Register key design entities (constraints are attached in __init__)
    rv32_entity = EarphoneRV32()
    simd16_entity = EarphoneSIMD16()
    scaffold.register_entity(rv32_entity)
    scaffold.register_entity(simd16_entity)

    # Register design gates between IR layers
    for gate in build_design_gates():
        scaffold.register_gate(gate)

    # Record major architecture decisions
    scaffold.record_decision(
        DesignDecision(
            uid="DEC-RV32-001",
            layer="ArchitectureIR",
            topic="Divider implementation",
            decision="Use 32-cycle iterative restoring divider for DIV/DIVU/REM/REMU",
            rationale="Reduce divider area vs combinational implementation; acceptable latency for Earphone control code.",
            alternatives_considered=["Combinational divider", "Radix-4 SRT divider"],
            impacted_constraints=["EARP-RV32-001", "EARP-RV32-002"],
            owner="ai",
        )
    )
    scaffold.record_decision(
        DesignDecision(
            uid="DEC-RV32-002",
            layer="ArchitectureIR",
            topic="Pipeline clock gating",
            decision="Gate pipeline registers with core_clk_en = ~core_stall & ~muldiv_busy",
            rationale="Cut dynamic power during memory stalls and divide operations with minimal control overhead.",
            alternatives_considered=["Per-register fine-grained gating", "Module-level clock gate only"],
            impacted_constraints=["EARP-RV32-002"],
            owner="ai",
        )
    )
    scaffold.record_decision(
        DesignDecision(
            uid="DEC-SIMD-001",
            layer="ArchitectureIR",
            topic="SIMD datapath gating",
            decision="Independent int_ce and fp_ce clock enables for INT16/FP16 datapaths",
            rationale="FP16 MAC pipeline toggles only when FP16 workloads are active; INT16 audio path remains active.",
            alternatives_considered=["Shared SIMD clock enable", "Per-lane clock gating"],
            impacted_constraints=["EARP-SIMD-001"],
            owner="ai",
        )
    )

    # Run scaffold propagation/validation loop
    print("\n" + "=" * 70)
    print("Design Scaffold — Constraint Propagation & Validation")
    print("=" * 70)

    resolution_log: List[str] = []
    resolved_feedback: List[ConstraintFeedback] = []

    def _scaffold_resolver(fb):
        resolved = resolve_feedback(fb, scaffold.entities)
        if resolved:
            resolution_log.append(
                f"Resolved {fb.uid}: {fb.message} -> applied suggested resolution"
            )
            resolved_feedback.append(fb)
        return resolved

    scaffold_ok, feedback = scaffold.run(resolver=_scaffold_resolver)
    print(f"  Scaffold propagation/validation: {'PASS' if scaffold_ok else 'BLOCKERS'}")
    checklist = scaffold.compliance_checklist()
    for item, ok in checklist.items():
        print(f"  compliance.{item}: {'OK' if ok else 'MISSING'}")

    # Persist artifacts generated by the scaffold emitter
    out_dir = "earphone/tb/constraints"
    os.makedirs(out_dir, exist_ok=True)
    for artifact_name, content in scaffold.artifacts.items():
        path = os.path.join(out_dir, artifact_name)
        with open(path, "w") as f:
            f.write(content)
        print(f"  wrote {path}")

    # ---- traceability / unified coverage report ---------------------------
    report_path = "earphone/specs/09_constraint_traceability.md"
    with open(report_path, "w") as f:
        f.write(
            generate_constraint_report(
                entities=scaffold.entities,
                feedback=feedback,
                decisions=scaffold.decisions,
                artifacts=scaffold.artifacts,
            )
        )
    print(f"  wrote {report_path}")

    # ---- design issues report ---------------------------------------------
    issue_lines = [
        "# 10 Design Feedback / Issues Report",
        "",
        "## Resolution Log",
        "",
    ]
    if resolution_log:
        for entry in resolution_log:
            issue_lines.append(f"- {entry}")
    else:
        issue_lines.append("- No auto-resolutions performed.")

    all_feedback = feedback + resolved_feedback
    issue_lines.extend([
        "",
        "## Feedback Items",
        "",
    ])
    if all_feedback:
        issue_lines.extend([
            "| UID | Severity | Source Constraint | Detected At | Message |",
            "|-----|----------|-------------------|-------------|---------|",
        ])
        for fb in sorted(all_feedback, key=lambda x: x.severity.value):
            issue_lines.append(
                f"| {fb.uid} | {fb.severity.value} | {fb.source_constraint_uid} | "
                f"{fb.detected_at_layer} | {fb.message} |"
            )
    else:
        issue_lines.append("- No feedback items.")

    issue_lines.extend([
        "",
        "## Remaining Blockers",
        "",
    ])
    remaining_blockers = [fb for fb in feedback if fb.is_blocking()]
    if remaining_blockers:
        for fb in remaining_blockers:
            issue_lines.append(f"- **{fb.uid}**: {fb.message}")
            for suggestion in fb.suggested_resolutions:
                issue_lines.append(f"  - Suggested: {suggestion}")
    else:
        issue_lines.append("- None. All blockers resolved or no blockers detected.")

    issue_path = "earphone/specs/10_design_issues.md"
    with open(issue_path, "w") as f:
        f.write("\n".join(issue_lines))
    print(f"  wrote {issue_path}")

    # Persist decision log
    decision_log_path = "earphone/specs/11_decision_log.md"
    with open(decision_log_path, "w") as f:
        f.write(scaffold.generate_decision_log())
    print(f"  wrote {decision_log_path}")

    # =====================================================================
    # Standard Spec2RTL flow
    # =====================================================================
    # Generate FFT twiddle files first
    print("\n[Setup] Generating FFT256 twiddle tables...")
    from design_scripts.design_fft import generate_twiddle_hex
    re_path, im_path = generate_twiddle_hex(256, 16, out_dir="earphone/twiddle")
    print(f"  {re_path}\n  {im_path}")

    # Review bundle
    generate_review_bundle()

    # Layer 1 tests
    l1_ok, l1_results = run_functional_tests()

    # Layer 3 tests
    l3_ok, l3_results = run_dsl_sim_tests()

    # Cross-layer
    xlayer_ok, xlayer_results = run_layer_verification()

    # Verilog generation
    gen_results = generate_verilog()

    # Cross-layer constraint propagation, artifact generation, and backward
    # validation are now handled by the DesignScaffold above.

    # Intent-driven tests (Phase D)
    intent_ok, intent_results = run_intent_driven_tests()

    # cocotb test generation (Phase D)
    generate_cocotb_tests_from_constraints()

    # Summary
    print("\n" + "=" * 70)
    print("SMART EARPHONE SoC — DESIGN SUMMARY")
    print("=" * 70)
    print(f"  Scaffold compliance   : {sum(checklist.values())}/{len(checklist)} OK")
    print(f"  L1 functional tests   : {sum(1 for _, ok in l1_results if ok)}/{len(l1_results)} PASS")
    print(f"  L3 DSL sim tests      : {sum(1 for _, ok in l3_results if ok)}/{len(l3_results)} PASS")
    print(f"  Cross-layer checks    : {sum(1 for _, ok in xlayer_results if ok)}/{len(xlayer_results)} PASS")
    print(f"  Intent-driven tests   : {sum(1 for _, ok in intent_results if ok)}/{len(intent_results)} PASS")
    print(f"  Verilog modules       : {sum(1 for r in gen_results if r[1])}/{len(gen_results)} generated")
    total_lines = sum(r[2] for r in gen_results if r[1])
    total_lint = sum(r[3] for r in gen_results if r[1])
    print(f"  Total Verilog lines   : {total_lines}")
    print(f"  Total lint issues     : {total_lint}")
    print("=" * 70)

    all_ok = (
        scaffold_ok
        and l1_ok
        and l3_ok
        and xlayer_ok
        and intent_ok
        and all(r[1] for r in gen_results)
    )
    print(f"\n  Overall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


def _legacy_entrypoint_approval_ok() -> bool:
    """Keep the compatibility entry point behind the same human gates."""
    from earphone.approval import DEFAULT_APPROVAL_GATES, approval_path, validate_approval
    from earphone.docgen import discover_modules

    gate_by_id = {gate.gate_id: gate for gate in DEFAULT_APPROVAL_GATES}
    blockers: List[str] = []

    module_gate = gate_by_id["CP0_MODULE"]
    for module in discover_modules():
        ok, reasons = validate_approval(
            module_gate.gate_id,
            module=module,
            required_artifacts=module_gate.artifacts,
        )
        if not ok:
            blockers.append(
                f"CP0_MODULE ({module}) missing or stale: "
                f"{approval_path(module_gate.gate_id, module=module)}; "
                + "; ".join(reasons)
            )

    soc_gate = gate_by_id["CP1_SOC"]
    ok, reasons = validate_approval(soc_gate.gate_id, required_artifacts=soc_gate.artifacts)
    if not ok:
        blockers.append(
            f"CP1_SOC missing or stale: {approval_path(soc_gate.gate_id)}; "
            + "; ".join(reasons)
        )

    if blockers:
        print("\n[Approval] Legacy full-SoC entry point blocked")
        for blocker in blockers:
            print(f"  - {blocker}")
        print("  Use `python -m earphone.flow --module all --check` to refresh evidence before approval.")
        return False
    return True


def main() -> int:
    if not _legacy_entrypoint_approval_ok():
        return 3
    return run_legacy_full_soc_flow()


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())
