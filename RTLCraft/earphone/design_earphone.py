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
from earphone.top.src.artifacts import (
    build_constraint_artifacts,
    generate_verilog_bundle,
    run_intent_driven_tests as run_top_intent_driven_tests,
)
from earphone.top.src.closure import run_top_level_closure
from earphone.top.src.review_bundle import generate_review_bundle as generate_top_review_bundle
from earphone.top.src.scaffold import run_design_scaffold_phase as run_top_design_scaffold_phase
from earphone.top.src.verification import (
    run_dsl_sim_tests as run_top_dsl_sim_tests,
    run_functional_tests as run_top_functional_tests,
    run_layer_verification as run_top_layer_verification,
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
    return run_top_functional_tests(
        rv32_iss_cls=RV32IM_ISS,
        to_u32=_to_u32,
        simd_op_vadd=SIMD_OP_VADD,
        simd_int16_functional=simd16_int16_functional,
        simd_fp16_mac_functional=simd16_fp16_mac_functional,
        f32_to_fp16=_f32_to_fp16,
        fp16_to_f32=_fp16_to_f32,
        fft256_functional=fft256_functional,
    )


def run_dsl_sim_tests():
    """Layer 3 DSL simulation tests."""
    return run_top_dsl_sim_tests(
        simulator_cls=Simulator,
        simd_cls=EarphoneSIMD16,
        qspi_cls=EarphoneQSPI,
        rv32_cls=EarphoneRV32,
        sram_cls=EarphoneSRAM256K,
        simd_op_vadd=SIMD_OP_VADD,
    )


def run_layer_verification():
    """Cross-layer verification: L1 functional == L2 cycle == L3 DSL."""
    return run_top_layer_verification(
        simulator_cls=Simulator,
        rv32_iss_cls=RV32IM_ISS,
        rv32_cls=EarphoneRV32,
        simd_cls=EarphoneSIMD16,
        fft_cls=EarphoneFFT256,
        qspi_cls=EarphoneQSPI,
        sram_cls=EarphoneSRAM256K,
        apb_bridge_cls=EarphoneAPBBridge,
        simd_cycle_model_factory=simd16_cycle_model,
        simd_op_vadd=SIMD_OP_VADD,
        simd_op_vsub=SIMD_OP_VSUB,
        simd_int16_functional=simd16_int16_functional,
        fft256_functional=fft256_functional,
        apb_decode_fn=apb_decode,
    )


def generate_verilog():
    """Generate Verilog for all modules and run lint."""
    return generate_verilog_bundle()


def generate_cocotb_tests_from_constraints():
    """Generate cocotb Python test files from Verilog-layer constraints."""
    return build_constraint_artifacts()


def run_intent_driven_tests():
    """Run L1 and L3 tests that are derived from constraints."""
    return run_top_intent_driven_tests()


def generate_review_bundle():
    """Emit the 7-stage review bundle markdown files."""
    generate_top_review_bundle()


def run_design_scaffold_phase() -> tuple[bool, dict, list, list]:
    """Run the design scaffold phase and persist traceability artifacts."""
    return run_top_design_scaffold_phase(
        propagator_factory=build_earphone_scaffold_propagator,
        layer_emitter_factory=EarphoneLayerEmitter,
        layers=EARPHONE_LAYERS,
        entity_factories=[EarphoneRV32, EarphoneSIMD16],
        design_gates_factory=build_design_gates,
        feedback_resolver=resolve_feedback,
    )


def build_legacy_top_level_closure_context() -> dict:
    """Return the current top-level closure steps for the shared orchestrator."""
    # Generate FFT twiddle files first
    print("\n[Setup] Generating FFT256 twiddle tables...")
    from design_scripts.design_fft import generate_twiddle_hex
    re_path, im_path = generate_twiddle_hex(256, 16, out_dir="earphone/twiddle")
    print(f"  {re_path}\n  {im_path}")

    return {
        "review_bundle_fn": generate_review_bundle,
        "l1_tests_fn": run_functional_tests,
        "l3_tests_fn": run_dsl_sim_tests,
        "cross_layer_fn": run_layer_verification,
        "verilog_fn": generate_verilog,
        "intent_tests_fn": run_intent_driven_tests,
        "cocotb_gen_fn": generate_cocotb_tests_from_constraints,
        "scaffold_fn": run_design_scaffold_phase,
    }


def run_legacy_full_soc_flow() -> int:
    """Run the legacy full SoC flow and return an exit code."""
    return run_top_level_closure(**build_legacy_top_level_closure_context())


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
        print("  Use `python -m earphone.flow --module all --check --top-level` to refresh evidence before approval.")
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
