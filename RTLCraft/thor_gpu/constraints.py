"""Thor-GPGPU cross-layer constraint definitions and transforms.

This module attaches SpecIR constraints to Thor-GPGPU modules and registers
transforms that propagate them through the 6-layer IR
(SpecIR -> BehaviorIR -> CycleIR -> ArchitectureIR -> StructuralIR -> DSL -> Verilog).
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

# Standard 6-layer path used across the Thor-GPGPU cluster.
THOR_LAYERS = [
    ("SpecIR", "BehaviorIR"),
    ("BehaviorIR", "CycleIR"),
    ("CycleIR", "ArchitectureIR"),
    ("ArchitectureIR", "StructuralIR"),
    ("StructuralIR", "DSL"),
    ("DSL", "Verilog"),
]


# ---------------------------------------------------------------------------
# SpecIR -> BehaviorIR transforms
# ---------------------------------------------------------------------------

def _alu_overflow_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    """VALU ADD/SUB wrap on overflow -> an L1 directed test."""
    if c.name != "THOR_VALU_MODULAR_ARITH":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name=f"{c.name}_behavior",
        layer=dst,
        expr="valu_add_sub_wraps_modulo_2_32()",
        target="ThorVectorALU",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _tensor_int8_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "THOR_TC_INT8_ACC":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name=f"{c.name}_behavior",
        layer=dst,
        expr="tc_8x8x8_int8_to_int32_reference()",
        target="ThorTensorCore",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _barrier_spec_to_behavior(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "THOR_WARP_BARRIER":
        return None
    return FunctionalConstraint(
        uid=f"{c.uid}_B",
        name=f"{c.name}_behavior",
        layer=dst,
        expr="barrier_releases_when_all_warps_at_barrier_or_done()",
        target="ThorWarpScheduler",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


# ---------------------------------------------------------------------------
# BehaviorIR -> CycleIR transforms
# ---------------------------------------------------------------------------

def _alu_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "THOR_VALU_MODULAR_ARITH_behavior":
        return None
    return PerformanceConstraint(
        uid=f"{c.uid}_C",
        name="THOR_VALU_LATENCY",
        layer=dst,
        expr="valu_result_registered_one_cycle",
        target="ThorVectorALU.result",
        unit="cycles",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _tensor_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "THOR_TC_INT8_ACC_behavior":
        return None
    return PerformanceConstraint(
        uid=f"{c.uid}_C",
        name="THOR_TC_LATENCY",
        layer=dst,
        expr="tc_done_asserted_after_mma",
        target="ThorTensorCore.done",
        unit="cycles",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


def _barrier_behavior_to_cycle(c: IRConstraint, src: str, dst: str) -> Optional[IRConstraint]:
    if c.name != "THOR_WARP_BARRIER_behavior":
        return None
    return PerformanceConstraint(
        uid=f"{c.uid}_C",
        name="THOR_BARRIER_RELEASE",
        layer=dst,
        expr="barrier_mask_cleared_cycle_after_all_at_barrier",
        target="ThorWarpScheduler.barrier_release",
        unit="cycles",
        derived_from=(c.uid,),
        owner="ai",
        source_ref=c.source_ref,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def attach_thor_constraints(module: Module, constraint: IRConstraint) -> None:
    """Attach a cross-layer constraint to a Thor-GPGPU DSL module."""
    module.add_constraint(constraint)


def build_thor_propagator() -> ConstraintPropagator:
    """Return a ConstraintPropagator pre-registered with Thor-GPGPU transforms."""
    propagator = ConstraintPropagator()
    propagator.register_forward("SpecIR", "BehaviorIR", _alu_overflow_spec_to_behavior)
    propagator.register_forward("SpecIR", "BehaviorIR", _tensor_int8_spec_to_behavior)
    propagator.register_forward("SpecIR", "BehaviorIR", _barrier_spec_to_behavior)
    propagator.register_forward("BehaviorIR", "CycleIR", _alu_behavior_to_cycle)
    propagator.register_forward("BehaviorIR", "CycleIR", _tensor_behavior_to_cycle)
    propagator.register_forward("BehaviorIR", "CycleIR", _barrier_behavior_to_cycle)
    return propagator


__all__: List[str] = [
    "THOR_LAYERS",
    "attach_thor_constraints",
    "build_thor_propagator",
]
