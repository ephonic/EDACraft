"""
rtlgen.arch_planner — Architecture Planner (SpecIR → ArchitectureIR)

Rules-based mapper that selects architecture style, operator implementations,
pipeline structure, and flow control based on SpecIR PPA goals.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from rtlgen.spec_ir import (
    ArchitectureIR,
    FlowControlSpec,
    OperatorImpl,
    StageSpec,
    SpecIR,
)


class ArchitecturePlanner:
    """Plan the architecture from a completed SpecIR."""

    def __init__(self, spec: SpecIR):
        self.spec = spec

    def plan(self) -> ArchitectureIR:
        """Generate ArchitectureIR based on spec category and PPA goals."""
        category = self.spec.category
        ppa = self.spec.ppa
        timing = self.spec.timing

        if category == "comb_alu":
            return self._plan_comb_alu()
        elif category == "register_update":
            return self._plan_register_update()
        elif category == "fsm_controller":
            return self._plan_fsm_controller()
        elif category == "stream_pipeline":
            return self._plan_stream_pipeline()
        else:
            return self._plan_comb_alu()  # fallback

    # ------------------------------------------------------------------
    # Category-specific planners
    # ------------------------------------------------------------------

    def _plan_comb_alu(self) -> ArchitectureIR:
        spec = self.spec
        ppa = spec.ppa
        func = spec.function

        arch = ArchitectureIR(arch_type="combinational")

        # Determine operator implementations
        expr = func.expr.lower()

        # Multiplier
        if "*" in expr:
            arch.operator_impl["mul"] = self._select_multiplier(ppa)

        # Adder/Subtractor
        if "+" in expr or "-" in expr:
            arch.operator_impl["add"] = self._select_adder(ppa)

        # ALU with opcode → use Switch-based architecture
        if func.opcode_field:
            arch.flow_control = FlowControlSpec(
                flow_type="fsm",
                stall_policy="stall_all",
                fsm_encoding=self._select_fsm_encoding(ppa),
            )

        # If latency_max > 1 and pipeline allowed, split into stages
        if spec.timing.latency_max and spec.timing.latency_max > 1 and ppa.allow_pipeline:
            arch = self._pipeline_comb_alu(arch, spec)

        return arch

    def _plan_register_update(self) -> ArchitectureIR:
        ppa = self.spec.ppa
        arch = ArchitectureIR(arch_type="fsm_controlled")

        # Register update is inherently sequential
        if self.spec.ppa.allow_clock_gating:
            arch.clock_gating = {"enable": "update_condition", "style": "ICG"}

        # Adder for increment/decrement
        arch.operator_impl["add"] = self._select_adder(ppa)

        arch.flow_control = FlowControlSpec(
            flow_type="none",
            fsm_encoding=self._select_fsm_encoding(ppa),
        )

        return arch

    def _plan_fsm_controller(self) -> ArchitectureIR:
        ppa = self.spec.ppa
        arch = ArchitectureIR(arch_type="fsm_controlled")

        arch.flow_control = FlowControlSpec(
            flow_type="fsm",
            stall_policy="stall_all",
            fsm_encoding=self._select_fsm_encoding(ppa),
        )

        # Power-first → clock gating on idle states
        if ppa.priority == "power_first":
            arch.clock_gating = {"enable": "idle", "style": "ICG"}

        return arch

    def _plan_stream_pipeline(self) -> ArchitectureIR:
        spec = self.spec
        ppa = spec.ppa

        arch = ArchitectureIR(arch_type="pipelined_datapath")

        # Determine number of stages from timing
        n_stages = self._determine_pipeline_stages(spec)

        # Build stage specs
        ops = self._extract_ops(spec.function.expr)
        for i in range(n_stages):
            stage_ops = ops[i::n_stages] if n_stages > 1 else ops
            arch.stages.append(StageSpec(
                stage_id=i,
                name=f"stage_{i}",
                ops=stage_ops,
                register_inputs=(i > 0),
                register_outputs=(i < n_stages - 1),
            ))

        # Flow control for ready-valid
        if spec.interfaces and (
            spec.interfaces.input_protocol == "ready_valid"
            or spec.interfaces.output_protocol == "ready_valid"
        ):
            arch.flow_control = FlowControlSpec(
                flow_type="ready_valid",
                stall_policy="stall_all",
                skid_buffer=(ppa.priority == "timing_first"),
            )

        # Operator implementations
        expr = spec.function.expr.lower()
        if "*" in expr:
            arch.operator_impl["mul"] = self._select_multiplier(ppa)
        if "+" in expr or "-" in expr:
            arch.operator_impl["add"] = self._select_adder(ppa)

        return arch

    # ------------------------------------------------------------------
    # Operator selection rules
    # ------------------------------------------------------------------

    def _select_multiplier(self, ppa) -> OperatorImpl:
        """Select multiplier implementation based on PPA priority."""
        if ppa.priority == "timing_first":
            return OperatorImpl(
                style="wallace",
                pipeline_stages=max(ppa.max_logic_depth or 2, 2) // 2,
            )
        elif ppa.priority == "area_first":
            return OperatorImpl(style="array", pipeline_stages=1)
        elif ppa.priority == "power_first":
            return OperatorImpl(
                style="booth",
                pipeline_stages=2,
            )
        else:
            return OperatorImpl(style="array", pipeline_stages=1)

    def _select_adder(self, ppa) -> OperatorImpl:
        """Select adder implementation based on PPA priority."""
        if ppa.priority == "timing_first":
            if ppa.allow_fast_adder:
                return OperatorImpl(style="carry_select", pipeline_stages=1)
            return OperatorImpl(style="carry_lookahead", pipeline_stages=1)
        elif ppa.priority == "area_first":
            return OperatorImpl(style="ripple", pipeline_stages=1)
        elif ppa.priority == "power_first":
            return OperatorImpl(style="carry_lookahead", pipeline_stages=1)
        else:
            return OperatorImpl(style="ripple", pipeline_stages=1)

    def _select_fsm_encoding(self, ppa) -> str:
        """Select FSM encoding style based on PPA priority."""
        if ppa.priority == "timing_first":
            return "one_hot"
        elif ppa.priority == "area_first":
            return "binary"
        elif ppa.priority == "power_first":
            return "gray"
        return "auto"

    # ------------------------------------------------------------------
    # Pipeline planning helpers
    # ------------------------------------------------------------------

    def _determine_pipeline_stages(self, spec: SpecIR) -> int:
        """Determine optimal pipeline stage count."""
        timing = spec.timing
        ppa = spec.ppa

        if not ppa.allow_pipeline:
            return 1

        # If latency_max is specified, use it
        if timing.latency_max and timing.latency_max > 0:
            return max(timing.latency_max, 1)

        # If latency_exact is specified
        if timing.latency_exact and timing.latency_exact > 0:
            return timing.latency_exact

        # Default based on expression complexity
        expr = spec.function.expr
        op_count = sum(1 for c in expr if c in "+-*&|^")
        if op_count <= 2:
            return 1
        elif op_count <= 4:
            return 2
        else:
            return 3

    def _pipeline_comb_alu(self, arch: ArchitectureIR, spec: SpecIR) -> ArchitectureIR:
        """Convert a combinational ALU to a pipelined datapath."""
        n_stages = self._determine_pipeline_stages(spec)
        if n_stages <= 1:
            return arch

        arch.arch_type = "pipelined_datapath"
        ops = self._extract_ops(spec.function.expr)

        for i in range(n_stages):
            stage_ops = ops[i::n_stages] if n_stages > 1 else ops
            arch.stages.append(StageSpec(
                stage_id=i,
                name=f"stage_{i}",
                ops=stage_ops,
                register_inputs=(i > 0),
                register_outputs=(i < n_stages - 1),
            ))

        return arch

    @staticmethod
    def _extract_ops(expr: str) -> List[str]:
        """Extract individual operations from an expression string."""
        expr = expr.strip()
        if "=" in expr:
            # Split "y = a * b + c" → ["mul = a * b", "add = ... + c"]
            lhs, rhs = expr.split("=", 1)
            rhs = rhs.strip()

            # Split by operators, keeping them
            parts: List[str] = []
            current = ""
            for ch in rhs:
                if ch in "+-*&|^":
                    if current.strip():
                        parts.append(current.strip())
                    parts.append(ch)
                    current = ""
                else:
                    current += ch
            if current.strip():
                parts.append(current.strip())

            # Group into operations
            ops = []
            i = 0
            while i < len(parts):
                if parts[i] in "+-*&|^":
                    if i + 2 <= len(parts):
                        ops.append(f"{parts[i-1] if i > 0 else ''} {parts[i]} {parts[i+1] if i+1 < len(parts) else ''}".strip())
                    i += 3
                else:
                    i += 1

            # Simpler approach: just return the split expression
            # by splitting on operators and prefixing with the operator
            ops = []
            tokens = rhs.replace(" ", "").split("(")
            remaining = rhs
            for op_char in ["*", "+", "-", "&", "|", "^"]:
                if op_char in remaining:
                    ops.append(f"{op_char}")

            if not ops:
                ops = [f"assign = {rhs}"]

            # Add output assignment
            ops = [f"assign {lhs.strip()} = {rhs}"]

            return ops

        return [f"assign = {expr}"]

    # ------------------------------------------------------------------
    # Resource sharing planner
    # ------------------------------------------------------------------

    def plan_resource_sharing(self) -> Dict[str, Any]:
        """Plan resource sharing if allowed by spec."""
        ppa = self.spec.ppa
        if not ppa.allow_resource_sharing:
            return {}

        # For ALUs with many operations, share a single adder/multiplier
        if self.spec.category == "comb_alu" and self.spec.function.operations:
            n_ops = len(self.spec.function.operations)
            if n_ops > 4:
                return {
                    "shared_adder": True,
                    "shared_multiplier": (n_ops > 6),
                    "mux_select": "opcode",
                }

        return {}
