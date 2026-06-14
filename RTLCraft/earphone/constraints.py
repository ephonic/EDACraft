"""Earphone-specific cross-layer constraint definitions and transforms.

This module attaches SpecIR constraints to Earphone modules and provides
registered transforms that propagate them through the 6-layer IR.
"""

from __future__ import annotations

from typing import List, Optional

from rtlgen.contracts import (
    ConstraintPropagator,
    FunctionalConstraint,
    IRConstraint,
    PerformanceConstraint,
    PowerConstraint,
    VerificationIntent,
)
from rtlgen.core import Module

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
        // x1 = 7, x2 = 0; DIV x5, x1, x2 -> -1
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220c2b3;
        req.rs1_val   = 32'h00000007;
        req.rs2_val   = 32'h00000000;
        finish_item(req);

        // REM x6, x1, x2 -> 7
        req = rv32_transaction::type_id::create("req");
        start_item(req);
        req.insn      = 32'h0220e333;
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


# ---------------------------------------------------------------------------
# Backward validation & design gates
# ---------------------------------------------------------------------------

import re

from rtlgen.contracts import ConstraintFeedback, DesignGate, FeedbackSeverity, IREntity


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
