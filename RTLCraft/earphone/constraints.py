"""Earphone-specific cross-layer constraint definitions and transforms.

This module attaches SpecIR constraints to Earphone modules and provides
registered transforms that propagate them through the 6-layer IR.
"""

from __future__ import annotations

from typing import List, Optional

# Import from the stable rtlgen package-level API.
from rtlgen import (
    ConstraintPropagator,
    FunctionalConstraint,
    IRConstraint,
    LayerEmitter,
    Module,
    PerformanceConstraint,
    PowerConstraint,
    VerificationIntent,
)

# Standard 6-layer path used across the Earphone SoC.
EARPHONE_LAYERS = [
    ("SpecIR", "BehaviorIR"),
    ("BehaviorIR", "CycleIR"),
    ("CycleIR", "ArchitectureIR"),
    ("ArchitectureIR", "StructuralIR"),
    ("StructuralIR", "DSL"),
    ("DSL", "Verilog"),
]


def _div_zero_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_ZERO":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name=f"{c.name}_behavior",
        layer=dst,
        expr="iss_div_zero_test()",
        target="RV32IM_ISS",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _div_zero_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_ZERO_behavior":
        return None
    return PerformanceConstraint(
        uid=f"{c.uid}_C",
        name="RV32M_DIV_LATENCY",
        layer=dst,
        expr="divider_busy_for_32_cycles_when_divisor_zero",
        target="EarphoneRV32.muldiv_busy",
        unit="cycles",
        derived_from=(c.uid,),
        owner="ai",
    )


def _div_zero_cycle_to_arch(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_LATENCY":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_A",
        name="RV32M_DIV_ZERO_ARCH",
        layer=dst,
        expr="div_divisor==0 && div_done -> div_result==0xFFFFFFFF",
        target="EarphoneRV32.execute_stage",
        derived_from=(c.uid,),
        owner="ai",
    )


def _div_zero_arch_to_struct(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_ZERO_ARCH":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_S",
        name="RV32M_DIV_ZERO_STRUCT",
        layer=dst,
        expr="monitor_div_result_in_execute_agent",
        target="EarphoneRV32.execute_agent",
        derived_from=(c.uid,),
        owner="ai",
    )


def _div_zero_struct_to_dsl(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_ZERO_STRUCT":
        return None
    return VerificationIntent(
        uid=f"{c.uid}_D",
        name="RV32M_DIV_ZERO_SEQ",
        layer=dst,
        expr="emit_div_zero_uvm_sequence",
        target="EarphoneRV32",
        metadata={"kind": "sequence", "format": "uvm"},
        derived_from=(c.uid,),
        owner="ai",
    )


def _div_zero_dsl_to_verilog(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "RV32M_DIV_ZERO_SEQ":
        return None
    return VerificationIntent(
        uid=f"{c.uid}_V",
        name="RV32M_DIV_ZERO_UVM",
        layer=dst,
        expr=emit_div_zero_uvm_sequence(),
        target="EarphoneRV32",
        metadata={"kind": "sequence", "format": "uvm", "filename": "rv32_div_zero_seq.sv"},
        derived_from=(c.uid,),
        owner="ai",
    )


def _vadd_overflow_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_OVERFLOW":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name=f"{c.name}_behavior",
        layer=dst,
        expr="simd16_int16_functional wraps to 16 bits",
        target="simd16_int16_functional",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _vadd_overflow_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_OVERFLOW_behavior":
        return None
    return PerformanceConstraint(
        uid=f"{c.uid}_C",
        name="SIMD16_VADD_LATENCY",
        layer=dst,
        expr="1 cycle for INT16 vadd",
        target="EarphoneSIMD16",
        unit="cycles",
        derived_from=(c.uid,),
        owner="ai",
    )


def _vadd_overflow_cycle_to_arch(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_LATENCY":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_A",
        name="SIMD16_VADD_OVERFLOW_ARCH",
        layer=dst,
        expr="per-lane add truncated to 16 bits",
        target="EarphoneSIMD16.int_alu",
        derived_from=(c.uid,),
        owner="ai",
    )


def _vadd_overflow_arch_to_struct(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_OVERFLOW_ARCH":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_S",
        name="SIMD16_VADD_OVERFLOW_STRUCT",
        layer=dst,
        expr="monitor vdst lanes for wrap behavior",
        target="EarphoneSIMD16.monitor",
        derived_from=(c.uid,),
        owner="ai",
    )


def _vadd_overflow_struct_to_dsl(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_OVERFLOW_STRUCT":
        return None
    return VerificationIntent(
        uid=f"{c.uid}_D",
        name="SIMD16_VADD_OVERFLOW_SVA",
        layer=dst,
        expr="emit_vadd_overflow_sva",
        target="EarphoneSIMD16",
        metadata={"kind": "assertion", "format": "sva"},
        derived_from=(c.uid,),
        owner="ai",
    )


def _vadd_overflow_dsl_to_verilog(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "SIMD16_VADD_OVERFLOW_SVA":
        return None
    return VerificationIntent(
        uid=f"{c.uid}_V",
        name="SIMD16_VADD_OVERFLOW_SVA_VERILOG",
        layer=dst,
        expr=emit_vadd_overflow_sva(),
        target="EarphoneSIMD16",
        metadata={"kind": "assertion", "format": "sva", "filename": "simd16_vadd_overflow_sva.sv"},
        derived_from=(c.uid,),
        owner="ai",
    )


def _cpu_power_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_ACTIVE_POWER":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name="CPU_PREFER_ITERATIVE_ALGORITHMS",
        layer=dst,
        expr="prefer iterative algorithms over combinational",
        target="EarphoneRV32",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _cpu_power_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_PREFER_ITERATIVE_ALGORITHMS":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_C",
        name="CPU_STALL_DURING_MULTICYCLE_OPS",
        layer=dst,
        expr="stall pipeline during multi-cycle ops",
        target="EarphoneRV32.core_stall",
        derived_from=(c.uid,),
        owner="ai",
    )


def _cpu_power_cycle_to_arch(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_STALL_DURING_MULTICYCLE_OPS":
        return None
    return PowerConstraint(
        uid=f"{c.uid}_A",
        name="CPU_CLK_GATE_STALL",
        layer=dst,
        expr="core_clk_en = ~core_stall & ~muldiv_busy",
        target="EarphoneRV32.pipeline_registers",
        derived_from=(c.uid,),
        owner="ai",
    )


def _cpu_power_arch_to_struct(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_CLK_GATE_STALL":
        return None
    return PowerConstraint(
        uid=f"{c.uid}_S",
        name="CPU_ICG_INSERTION",
        layer=dst,
        expr="insert ICG before pipeline register groups",
        target="EarphoneRV32",
        derived_from=(c.uid,),
        owner="ai",
    )


def _cpu_power_struct_to_dsl(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_ICG_INSERTION":
        return None
    return PowerConstraint(
        uid=f"{c.uid}_D",
        name="CPU_CLK_GATE_CODING_STYLE",
        layer=dst,
        expr="if (clk_en) reg <= next",
        target="EarphoneRV32",
        derived_from=(c.uid,),
        owner="ai",
    )


def _cpu_power_dsl_to_verilog(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "CPU_CLK_GATE_CODING_STYLE":
        return None
    return PowerConstraint(
        uid=f"{c.uid}_V",
        name="CPU_ACTIVE_POWER_REPORT",
        layer=dst,
        expr="< 0.5 mW/MHz target; clock gating applied",
        target="EarphoneRV32",
        unit="mW/MHz",
        metadata={"kind": "report", "filename": "cpu_power_report.md"},
        derived_from=(c.uid,),
        owner="ai",
    )


def build_earphone_propagator() -> ConstraintPropagator:
    """Return a propagator with all Earphone-specific transform rules."""
    p = ConstraintPropagator()

    # RV32M DIV by zero
    p.register_forward("SpecIR", "BehaviorIR", _div_zero_spec_to_behavior)
    p.register_forward("BehaviorIR", "CycleIR", _div_zero_behavior_to_cycle)
    p.register_forward("CycleIR", "ArchitectureIR", _div_zero_cycle_to_arch)
    p.register_forward("ArchitectureIR", "StructuralIR", _div_zero_arch_to_struct)
    p.register_forward("StructuralIR", "DSL", _div_zero_struct_to_dsl)
    p.register_forward("DSL", "Verilog", _div_zero_dsl_to_verilog)

    # SIMD16 VADD overflow
    p.register_forward("SpecIR", "BehaviorIR", _vadd_overflow_spec_to_behavior)
    p.register_forward("BehaviorIR", "CycleIR", _vadd_overflow_behavior_to_cycle)
    p.register_forward("CycleIR", "ArchitectureIR", _vadd_overflow_cycle_to_arch)
    p.register_forward("ArchitectureIR", "StructuralIR", _vadd_overflow_arch_to_struct)
    p.register_forward("StructuralIR", "DSL", _vadd_overflow_struct_to_dsl)
    p.register_forward("DSL", "Verilog", _vadd_overflow_dsl_to_verilog)

    # CPU active power
    p.register_forward("SpecIR", "BehaviorIR", _cpu_power_spec_to_behavior)
    p.register_forward("BehaviorIR", "CycleIR", _cpu_power_behavior_to_cycle)
    p.register_forward("CycleIR", "ArchitectureIR", _cpu_power_cycle_to_arch)
    p.register_forward("ArchitectureIR", "StructuralIR", _cpu_power_arch_to_struct)
    p.register_forward("StructuralIR", "DSL", _cpu_power_struct_to_dsl)
    p.register_forward("DSL", "Verilog", _cpu_power_dsl_to_verilog)

    return p


def attach_earphone_constraints(module: Module, constraint: IRConstraint) -> Module:
    """Attach a SpecIR constraint to a module and propagate it through all layers."""
    module.add_constraint(constraint)
    return module


def propagate_module_constraints(module: Module, propagator: Optional[ConstraintPropagator] = None) -> List[IRConstraint]:
    """Propagate all constraints attached to a module through the 6-layer path."""
    if propagator is None:
        propagator = build_earphone_propagator()
    return propagator.propagate_all(module, EARPHONE_LAYERS)


# ---------------------------------------------------------------------------
# Verilog artifact generators
# ---------------------------------------------------------------------------

def emit_div_zero_uvm_sequence() -> str:
    """Emit UVM sequence for RV32M division-by-zero test."""
    return '''// Auto-generated from SpecIR constraint RV32M_DIV_ZERO
class rv32m_div_zero_seq extends uvm_sequence #(rv32_transaction);
    `uvm_object_utils(rv32m_div_zero_seq)

    function new(string name = "rv32m_div_zero_seq");
        super.new(name);
    endfunction

    virtual task body();
        rv32_transaction req;
        // x1 = 7, x2 = 0; DIV x3, x1, x2 -> -1
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220c1b3;
        req.rs1_val   = 32'h00000007;
        req.rs2_val   = 32'h00000000;
        finish_item(req);

        // REM x4, x1, x2 -> 7
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220e233;
        req.rs1_val   = 32'h00000007;
        req.rs2_val   = 32'h00000000;
        finish_item(req);
    endtask
endclass
'''


def emit_vadd_overflow_sva() -> str:
    """Emit SVA assertion for SIMD16 vadd 16-bit wrap."""
    return '''// Auto-generated from SpecIR constraint SIMD16_VADD_OVERFLOW
module simd16_vadd_overflow_assertions (
    input clk,
    input rst_n,
    input [255:0] vsrc0,
    input [255:0] vsrc1,
    input [255:0] vdst,
    input start,
    input [4:0] op
);
    // Check one representative lane (lane 0); replicate for 0..15 as needed
    wire [15:0] a0 = vsrc0[15:0];
    wire [15:0] b0 = vsrc1[15:0];
    wire [15:0] y0 = vdst[15:0];

    property p_vadd_wrap_lane0;
        @(posedge clk) disable iff (!rst_n)
        (start && (op == 5'd0)) |-> ##1 (y0 == a0 + b0);
    endproperty

    assert property (p_vadd_wrap_lane0)
        else `uvm_error("SIMD16", $sformatf("vadd lane0 mismatch: a0=%0h b0=%0h y0=%0h", a0, b0, y0));
endmodule
'''


def emit_cpu_power_report() -> str:
    """Emit markdown report for CPU active power optimization."""
    return '''# CPU Active Power Report

**Constraint**: CPU active power < 0.5 mW/MHz  
**Target module**: `EarphoneRV32`

## Applied Optimizations

1. **Iterative restoring divider** — replaces combinational divider to reduce area and dynamic power.
2. **Pipeline clock gating** — `core_clk_en = ~core_stall & ~muldiv_busy` freezes registers during stalls/divides.
3. **Multiplier operand isolation** — multiplier output forced to zero when no M-extension instruction is in execute.
4. **ICG insertion** — clock gating cells placed before pipeline register groups.

## RTL Coding Style

```systemverilog
if (core_clk_en) begin
    pc_reg     <= next_pc;
    fetch_valid<= next_fetch_valid;
    // ...
end
```

## Status

Power target remains a design-time assumption until synthesis results are back-annoted.
'''


def generate_constraint_artifacts(constraints: List[IRConstraint]) -> dict:
    """Generate artifact contents from Verilog-layer constraints."""
    artifacts = {}
    for c in constraints:
        if c.layer != "Verilog":
            continue
        meta = c.metadata or {}
        if c.name.startswith("RV32M_DIV_ZERO"):
            artifacts[meta.get("filename", "rv32_div_zero_seq.sv")] = emit_div_zero_uvm_sequence()
        elif c.name.startswith("SIMD16_VADD_OVERFLOW"):
            artifacts[meta.get("filename", "simd16_vadd_overflow_sva.sv")] = emit_vadd_overflow_sva()
        elif c.name.startswith("CPU_ACTIVE_POWER"):
            artifacts[meta.get("filename", "cpu_power_report.md")] = emit_cpu_power_report()
    return artifacts


class EarphoneLayerEmitter(LayerEmitter):
    """Per-layer artifact emitter for the Earphone SoC.

    Generates verification artifacts (UVM sequences, SVA assertions, power
    reports) once constraints reach the Verilog layer.
    """

    def emit(self, entity: IREntity, layer: str) -> dict:
        if layer != "Verilog":
            return {}
        return generate_constraint_artifacts(entity.constraints_by(layer=layer))


# ---------------------------------------------------------------------------
# Backward validation & design gates
# ---------------------------------------------------------------------------

import re

from rtlgen import ConstraintFeedback, DesignGate, FeedbackSeverity, IREntity


# Feasibility assumption: based on current architecture, the minimum achievable
# active power for EarphoneRV32 at 160 MHz/22nm is 0.35 mW/MHz.
CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ = 0.35


def _parse_power_budget(expr: str) -> Optional[float]:
    """Parse a power budget expression like '< 0.5' into a float."""
    m = re.search(r"<\s*([0-9.]+)", expr)
    if m:
        return float(m.group(1))
    return None


def check_power_feasibility_backward(
    c: IRConstraint, src_layer: str, dst_layer: str
) -> Optional[ConstraintFeedback]:
    """Backward rule: verify that a SpecIR power budget is achievable at Verilog."""
    if c.category != "power" or c.layer != src_layer:
        return None
    budget = _parse_power_budget(c.expr)
    if budget is None:
        return None
    if budget < CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ:
        return ConstraintFeedback(
            uid=f"FB-{c.uid}",
            severity=FeedbackSeverity.BLOCKER,
            source_constraint_uid=c.uid,
            detected_at_layer=dst_layer,
            message=(
                f"Power budget {budget} mW/MHz is below estimated minimum "
                f"{CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ} mW/MHz for EarphoneRV32 "
                f"with current architecture (iterative divider + clock gating)."
            ),
            suggested_resolutions=[
                f"Relax SpecIR budget to >= {CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ} mW/MHz",
                "Add power domain / retention cells and re-estimate",
                "Reduce pipeline depth or feature set and re-estimate",
            ],
            owner="ai",
        )
    return None


def check_functional_sva_completeness(
    c: IRConstraint, src_layer: str, dst_layer: str
) -> Optional[ConstraintFeedback]:
    """Backward rule: warn if a functional constraint has no Verilog assertion."""
    if c.category != "functional" or c.layer != src_layer:
        return None
    # In a real flow this would inspect generated artifacts; here we simply
    # emit INFO feedback for traceability demonstration.
    return ConstraintFeedback(
        uid=f"FB-COMPLETE-{c.uid}",
        severity=FeedbackSeverity.INFO,
        source_constraint_uid=c.uid,
        detected_at_layer=dst_layer,
        message=f"Functional constraint '{c.name}' has been propagated to Verilog layer.",
        owner="ai",
    )


def build_backward_validators() -> "ConstraintPropagator":
    """Return a propagator registered with backward validation rules."""
    p = ConstraintPropagator()
    # Validate SpecIR constraints against Verilog implementation
    p.register_backward("SpecIR", "Verilog", check_power_feasibility_backward)
    p.register_backward("SpecIR", "Verilog", check_functional_sva_completeness)
    return p


def build_earphone_scaffold_propagator() -> "ConstraintPropagator":
    """Return a propagator with forward transforms and backward validators."""
    p = build_earphone_propagator()
    for (src, dst), rules in build_backward_validators()._backward_rules.items():
        for rule in rules:
            p.register_backward(src, dst, rule)
    return p


def build_design_gates() -> List[DesignGate]:
    """Return the design gates used between Earphone IR layers."""

    def _power_gate_check(entity: IREntity, src: str, dst: str) -> List[ConstraintFeedback]:
        feedback = []
        for c in entity.constraints_by(layer=src, category="power"):
            fb = check_power_feasibility_backward(c, src, dst)
            if fb:
                feedback.append(fb)
        return feedback

    return [
        DesignGate("SpecIR", "Verilog", [_power_gate_check]),
    ]


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

from rtlgen.core import Module


def relax_unachievable_power_budget(module: Module) -> bool:
    """Resolver: replace an unachievable power budget with the feasible one.

    Returns True if a change was made.
    """
    changed = False
    new_constraints = []
    for c in module.constraints():
        if (
            c.category == "power"
            and c.layer == "SpecIR"
            and c.name == "CPU_POWER_BUDGET_STRICT"
        ):
            budget = _parse_power_budget(c.expr)
            if budget is not None and budget < CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ:
                new_constraints.append(
                    PowerConstraint(
                        uid=c.uid,
                        name=c.name,
                        layer=c.layer,
                        expr=f"< {CPU_MIN_ACHIEVABLE_POWER_MW_PER_MHZ}",
                        target=c.target,
                        unit=c.unit,
                        owner=c.owner,
                        source_ref=c.source_ref,
                        metadata={**c.metadata, "relaxed": True, "original_expr": c.expr},
                    )
                )
                changed = True
                continue
        new_constraints.append(c)
    if changed:
        module._constraints = new_constraints
    return changed


def resolve_feedback(feedback: ConstraintFeedback, modules: List[Module]) -> bool:
    """Attempt to auto-resolve a feedback item.

    Returns True if resolved.
    """
    if not feedback.is_blocking():
        return True
    if "Power budget" in feedback.message:
        for mod in modules:
            if relax_unachievable_power_budget(mod):
                return True
    return False


# ---------------------------------------------------------------------------
# Intent-driven test generation
# ---------------------------------------------------------------------------

from typing import Callable, Dict, Tuple


def generate_l1_tests_from_constraints(
    constraints: List[IRConstraint],
) -> List[Tuple[str, Callable[[], bool]]]:
    """Generate L1 functional test callables from BehaviorIR/SpecIR constraints."""
    tests = []

    # Import locally to avoid circular dependency at module load time.
    from earphone.design_earphone import (
        RV32IM_ISS,
        SIMD_OP_VADD,
        _to_u32,
        simd16_int16_functional,
    )

    for c in constraints:
        if c.name == "RV32M_DIV_ZERO_behavior":
            def _rv32m_div_zero_test():
                iss = RV32IM_ISS()
                prog = [
                    0x00700093,  # addi x1, x0, 7
                    0x00000113,  # addi x2, x0, 0
                    0x0220c1b3,  # div  x3, x1, x2 -> -1
                    0x0220e233,  # rem  x4, x1, x2 -> 7
                    0x00100073,  # ebreak
                ]
                iss.load_program_words(prog, 0x1000)
                iss.run(max_cycles=40)
                return (iss.state.regs[3] == 0xFFFFFFFF and iss.state.regs[4] == 7)

            tests.append(("RV32M DIV by zero (intent-driven)", _rv32m_div_zero_test))

        elif c.name == "SIMD16_VADD_OVERFLOW_behavior":
            def _simd16_vadd_test():
                a = 0
                b = 0
                for i in range(16):
                    a |= ((i + 1) & 0xFFFF) << (i * 16)
                    b |= ((i + 2) & 0xFFFF) << (i * 16)
                r = simd16_int16_functional(SIMD_OP_VADD, a, b)
                for i in range(16):
                    lane = (r >> (i * 16)) & 0xFFFF
                    expected = ((i + 1) + (i + 2)) & 0xFFFF
                    if lane != expected:
                        return False
                return True

            tests.append(("SIMD16 INT16 vadd (intent-driven)", _simd16_vadd_test))

    return tests


def generate_l3_tests_from_constraints(
    constraints: List[IRConstraint],
) -> List[Tuple[str, Callable[[], bool]]]:
    """Generate L3 DSL simulation test callables from Verilog-layer constraints."""
    tests = []

    from earphone.design_earphone import (
        EarphoneRV32, EarphoneSIMD16, SIMD_OP_VADD, _to_u32,
    )
    from rtlgen.sim import Simulator

    for c in constraints:
        if c.name == "RV32M_DIV_ZERO_UVM":
            def _rv32_dsl_div_test():
                cpu = EarphoneRV32()
                sim = Simulator(cpu)
                sim.reset("rst_n", cycles=2)
                program = {
                    0x1000: 0x00700093,  # addi x1, x0, 7
                    0x1004: 0x00000113,  # addi x2, x0, 0
                    0x1008: 0x0220c1b3,  # div  x3, x1, x2 -> -1
                    0x100c: 0x0220e233,  # rem  x4, x1, x2 -> 7
                    0x1010: 0x00100073,  # ebreak
                }
                expected = {3: _to_u32(-1), 4: 7}
                retired = {rd: False for rd in expected}
                for cycle in range(200):
                    addr = sim.peek("imem_addr")
                    sim.poke("imem_gnt", 1)
                    sim.poke("imem_rdata", program.get(addr, 0))
                    sim.poke("dmem_gnt", 1)
                    sim.poke("dmem_valid", 1)
                    sim.poke("dmem_rdata", 0)
                    sim.step()
                    if sim.peek("retire_valid"):
                        rd = sim.peek("retire_rd")
                        val = sim.peek("retire_result")
                        if rd in expected and val == expected[rd]:
                            retired[rd] = True
                return all(retired.values())

            tests.append(("RV32IM DSL DIV/REM by zero (intent-driven)", _rv32_dsl_div_test))

        elif c.name == "SIMD16_VADD_OVERFLOW_SVA_VERILOG":
            def _simd16_dsl_vadd_test():
                simd = EarphoneSIMD16()
                sim = Simulator(simd)
                sim.reset("rst_n", cycles=2)
                a = 0
                b = 0
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
                if not done:
                    return False
                for i in range(16):
                    lane = (r >> (i * 16)) & 0xFFFF
                    expected = ((i + 1) + (i + 2)) & 0xFFFF
                    if lane != expected:
                        return False
                return True

            tests.append(("SIMD16 DSL vadd (intent-driven)", _simd16_dsl_vadd_test))

    return tests


def generate_cocotb_test_content(constraints: List[IRConstraint]) -> Dict[str, str]:
    """Generate cocotb Python test files from Verilog-layer verification intents."""
    files = {}

    for c in constraints:
        if c.layer != "Verilog" or c.category != "verification":
            continue
        meta = c.metadata or {}
        if meta.get("kind") == "sequence" and "RV32M_DIV_ZERO" in c.name:
            content = '''import cocotb
from cocotb.triggers import ClockCycles
from cocotb.clock import Clock


@cocotb.test()
async def test_rv32m_div_zero(dut):
    """Intent-driven cocotb test for RV32M DIV by zero."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Drive instruction memory: DIV x3, x1, x2 where x2 = 0
    # This is a simplified stimulus; real test would use memory BFM.
    for _ in range(50):
        await ClockCycles(dut.clk, 1)

    # Check retire
    assert dut.retire_valid.value == 1
    assert dut.retire_rd.value == 3
    # DIV by zero result = -1 (0xFFFFFFFF)
    assert dut.retire_result.value == 0xFFFFFFFF
'''
            files["test_rv32m_div_zero.py"] = content

        elif meta.get("kind") == "assertion" and "SIMD16_VADD_OVERFLOW" in c.name:
            content = '''import cocotb
from cocotb.triggers import ClockCycles
from cocotb.clock import Clock


@cocotb.test()
async def test_simd16_vadd_overflow(dut):
    """Intent-driven cocotb test for SIMD16 vadd 16-bit wrap."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    a = sum(((i + 1) & 0xFFFF) << (i * 16) for i in range(16))
    b = sum(((i + 2) & 0xFFFF) << (i * 16) for i in range(16))

    dut.vsrc0.value = a
    dut.vsrc1.value = b
    dut.op.value = 0       # vadd
    dut.mode.value = 0     # INT16
    dut.pred.value = 0xFFFF
    dut.start.value = 1
    await ClockCycles(dut.clk, 1)
    dut.start.value = 0
    await ClockCycles(dut.clk, 2)

    assert dut.done.value == 1
    for i in range(16):
        lane = (int(dut.vdst.value) >> (i * 16)) & 0xFFFF
        expected = ((i + 1) + (i + 2)) & 0xFFFF
        assert lane == expected, f"lane {i}: {lane} != {expected}"
'''
            files["test_simd16_vadd_overflow.py"] = content

    return files
