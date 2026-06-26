"""
rtlgen.arch_planner — Architecture Planner (SpecIR → ArchitectureIR)

Rules-based mapper that selects architecture style, operator implementations,
pipeline structure, and flow control based on SpecIR PPA goals.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional

from rtlgen.spec_ir import (
    ArchitectureIR,
    FlowControlSpec,
    HandshakeIR,
    OperationSpec,
    OperatorImpl,
    RegisterTransferSpec,
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
        elif category == "hierarchical":
            return self._plan_hierarchical()
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
        arch.signal_widths = self._port_widths()

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
        else:
            planned = self._plan_expression_pipeline(spec, arch_type="combinational", stage_count=1)
            arch.stages = planned.stages
            arch.signal_widths = planned.signal_widths
            arch.output_names = planned.output_names

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

        # Determine number of stages from timing
        n_stages = self._determine_pipeline_stages(spec)
        arch = self._plan_expression_pipeline(spec, arch_type="pipelined_datapath", stage_count=n_stages)

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
            arch.handshake = HandshakeIR(
                valid_in="in_valid",
                ready_out="in_ready",
                ready_in="out_ready",
                valid_out="out_valid",
                stall_signal="pipe_stall",
            )

        # Operator implementations
        expr = spec.function.expr.lower()
        if "*" in expr:
            arch.operator_impl["mul"] = self._select_multiplier(ppa)
        if "+" in expr or "-" in expr:
            arch.operator_impl["add"] = self._select_adder(ppa)

        return arch

    def _plan_hierarchical(self) -> ArchitectureIR:
        arch = ArchitectureIR(arch_type="hierarchical")
        arch.signal_widths = self._port_widths()
        arch.output_names = [p.name for p in self.spec.ports if p.direction == "output"]
        arch.flow_control = FlowControlSpec(flow_type="none")
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

        planned = self._plan_expression_pipeline(spec, arch_type="pipelined_datapath", stage_count=n_stages)
        arch.arch_type = planned.arch_type
        arch.stages = planned.stages
        arch.signal_widths = planned.signal_widths
        arch.output_names = planned.output_names
        arch.handshake = planned.handshake
        return arch

    def _plan_expression_pipeline(
        self,
        spec: SpecIR,
        arch_type: str,
        stage_count: int,
    ) -> ArchitectureIR:
        """Build a structured operation pipeline from the function expression."""
        arch = ArchitectureIR(arch_type=arch_type)
        arch.signal_widths = self._port_widths()

        output_name, operations = self._extract_operation_specs(spec.function.expr, arch.signal_widths)
        arch.output_names = [output_name] if output_name else []

        stages = [
            StageSpec(
                stage_id=i,
                name=f"stage_{i}",
                ops=[],
                operation_specs=[],
                registers=[],
                register_inputs=(i > 0),
                register_outputs=(i < stage_count - 1),
            )
            for i in range(max(stage_count, 1))
        ]

        if operations:
            assignments = self._assign_operation_stages(operations, len(stages))
            for op, stage_id in zip(operations, assignments):
                op.stage_id = stage_id
                stages[stage_id].operation_specs.append(op)
                stages[stage_id].ops.append(f"{op.output} = {op.expr}")
            self._plan_stage_registers(stages, operations, arch.signal_widths, output_name)
        elif output_name:
            stages[0].ops.append(f"{output_name} = {spec.function.expr.split('=', 1)[-1].strip()}")

        arch.stages = stages
        return arch

    def _port_widths(self) -> Dict[str, int]:
        return {p.name: p.width for p in self.spec.ports}

    def _extract_operation_specs(
        self,
        expr: str,
        signal_widths: Dict[str, int],
    ) -> tuple[str, List[OperationSpec]]:
        """Lower an expression into topologically ordered operation specs."""
        text = expr.strip()
        if "=" in text:
            lhs, rhs = text.split("=", 1)
            output_name = lhs.strip()
            rhs = rhs.strip()
        else:
            outputs = [p.name for p in self.spec.ports if p.direction == "output"]
            output_name = outputs[0] if outputs else "out"
            rhs = text

        if not rhs:
            return output_name, []

        tree = ast.parse(rhs, mode="eval")
        operations: List[OperationSpec] = []
        temp_idx = 0
        declared_output_width = self._port_widths().get(output_name)

        def ensure_width(token: str) -> int:
            if token in signal_widths:
                return signal_widths[token]
            if self._is_literal(token):
                value = int(token, 0)
                return max(value.bit_length(), 1)
            return 1

        def lower(node: ast.AST, is_root: bool = False) -> str:
            nonlocal temp_idx
            if isinstance(node, ast.Name):
                signal_widths.setdefault(node.id, 8)
                return node.id
            if isinstance(node, ast.Constant):
                token = repr(int(node.value))
                signal_widths.setdefault(token, max(int(node.value).bit_length(), 1))
                return token
            if isinstance(node, ast.UnaryOp):
                if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
                    value = -int(node.operand.value)
                    token = repr(value)
                    signal_widths.setdefault(token, max(abs(value).bit_length() + 1, 1))
                    return token
                input_name = lower(node.operand)
                out_name = output_name if is_root else f"tmp_{temp_idx}"
                temp_idx += 1
                kind = self._unary_kind(node.op)
                width = ensure_width(input_name)
                if is_root and declared_output_width is not None:
                    width = declared_output_width
                operations.append(OperationSpec(
                    op_id=len(operations),
                    kind=kind,
                    output=out_name,
                    inputs=[input_name],
                    expr=f"{kind} {input_name}",
                    width=width,
                ))
                signal_widths[out_name] = width
                return out_name
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                lhs_name = lower(node.left)
                rhs_name = lower(node.comparators[0])
                out_name = output_name if is_root else f"tmp_{temp_idx}"
                temp_idx += 1
                kind = self._compare_kind(node.ops[0])
                width = declared_output_width if is_root and declared_output_width is not None else 1
                operations.append(OperationSpec(
                    op_id=len(operations),
                    kind=kind,
                    output=out_name,
                    inputs=[lhs_name, rhs_name],
                    expr=f"{lhs_name} {kind} {rhs_name}",
                    width=width,
                ))
                signal_widths[out_name] = width
                return out_name
            if isinstance(node, ast.BinOp):
                lhs_name = lower(node.left)
                rhs_name = lower(node.right)
                out_name = output_name if is_root else f"tmp_{temp_idx}"
                temp_idx += 1
                kind = self._binop_kind(node.op)
                width = self._infer_result_width(kind, ensure_width(lhs_name), ensure_width(rhs_name))
                if is_root and declared_output_width is not None:
                    width = declared_output_width
                operations.append(OperationSpec(
                    op_id=len(operations),
                    kind=kind,
                    output=out_name,
                    inputs=[lhs_name, rhs_name],
                    expr=f"{lhs_name} {self._symbol_for_kind(kind)} {rhs_name}",
                    width=width,
                ))
                signal_widths[out_name] = width
                return out_name
            raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

        lower(tree.body, is_root=True)
        signal_widths[output_name] = self._port_widths().get(output_name, signal_widths.get(output_name, 1))
        return output_name, operations

    @staticmethod
    def _assign_operation_stages(operations: List[OperationSpec], stage_count: int) -> List[int]:
        if not operations:
            return []
        if stage_count <= 1:
            return [0 for _ in operations]
        if len(operations) <= stage_count:
            return list(range(len(operations)))
        return [min((idx * stage_count) // len(operations), stage_count - 1) for idx in range(len(operations))]

    def _plan_stage_registers(
        self,
        stages: List[StageSpec],
        operations: List[OperationSpec],
        signal_widths: Dict[str, int],
        output_name: str,
    ) -> None:
        producers: Dict[str, int] = {name: -1 for name in self._port_widths()}
        consumers: Dict[str, set[int]] = {}

        for op in operations:
            producers[op.output] = op.stage_id if op.stage_id is not None else 0
            for token in op.inputs:
                if self._is_literal(token):
                    continue
                consumers.setdefault(token, set()).add(op.stage_id if op.stage_id is not None else 0)

        # Force the final output to be preserved through any tail stages.
        if output_name:
            consumers.setdefault(output_name, set()).add(len(stages))

        for stage in stages[:-1]:
            boundary_regs: List[RegisterTransferSpec] = []
            for signal_name, producer_stage in producers.items():
                if producer_stage > stage.stage_id or self._is_literal(signal_name):
                    continue
                later_uses = consumers.get(signal_name, set())
                if any(use_stage > stage.stage_id for use_stage in later_uses):
                    boundary_regs.append(RegisterTransferSpec(
                        name=f"s{stage.stage_id + 1}_{self._sanitize_identifier(signal_name)}",
                        source=signal_name,
                        width=signal_widths.get(signal_name, 1),
                    ))
            stage.registers = boundary_regs

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        return re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "sig"

    @staticmethod
    def _is_literal(token: str) -> bool:
        try:
            int(token, 0)
            return True
        except Exception:
            return False

    @staticmethod
    def _binop_kind(node: ast.operator) -> str:
        mapping = {
            ast.Add: "add",
            ast.Sub: "sub",
            ast.Mult: "mul",
            ast.BitAnd: "and",
            ast.BitOr: "or",
            ast.BitXor: "xor",
            ast.LShift: "shl",
            ast.RShift: "shr",
        }
        for ast_type, kind in mapping.items():
            if isinstance(node, ast_type):
                return kind
        raise ValueError(f"Unsupported binary operator: {type(node).__name__}")

    @staticmethod
    def _unary_kind(node: ast.unaryop) -> str:
        mapping = {
            ast.Invert: "not",
            ast.USub: "neg",
        }
        for ast_type, kind in mapping.items():
            if isinstance(node, ast_type):
                return kind
        raise ValueError(f"Unsupported unary operator: {type(node).__name__}")

    @staticmethod
    def _compare_kind(node: ast.cmpop) -> str:
        mapping = {
            ast.Eq: "eq",
            ast.NotEq: "ne",
            ast.Lt: "lt",
            ast.LtE: "le",
            ast.Gt: "gt",
            ast.GtE: "ge",
        }
        for ast_type, kind in mapping.items():
            if isinstance(node, ast_type):
                return kind
        raise ValueError(f"Unsupported comparison operator: {type(node).__name__}")

    @staticmethod
    def _symbol_for_kind(kind: str) -> str:
        mapping = {
            "add": "+",
            "sub": "-",
            "mul": "*",
            "and": "&",
            "or": "|",
            "xor": "^",
            "shl": "<<",
            "shr": ">>",
            "eq": "==",
            "ne": "!=",
            "lt": "<",
            "le": "<=",
            "gt": ">",
            "ge": ">=",
            "not": "~",
            "neg": "-",
        }
        return mapping.get(kind, kind)

    @staticmethod
    def _infer_result_width(kind: str, lhs_width: int, rhs_width: int) -> int:
        if kind in ("add", "sub"):
            return max(lhs_width, rhs_width) + 1
        if kind == "mul":
            return lhs_width + rhs_width
        if kind in ("eq", "ne", "lt", "le", "gt", "ge"):
            return 1
        if kind in ("shl", "shr"):
            return lhs_width
        return max(lhs_width, rhs_width)

    def _extract_ops(self, expr: str) -> List[str]:
        """Compatibility helper returning human-readable operation strings."""
        widths = self._port_widths()
        _, operations = self._extract_operation_specs(expr, widths)
        return [f"{op.output} = {op.expr}" for op in operations] or [f"assign = {expr.strip()}"]

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
