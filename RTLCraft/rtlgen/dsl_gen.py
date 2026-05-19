"""
rtlgen.dsl_gen — DSL Skeleton Generator (ArchitectureIR → Module)

Generates a complete Python DSL Module from ArchitectureIR for the
4 supported module categories:
  1. comb_alu: pure combinational with Switch-based opcode dispatch
  2. register_update: counters, accumulators
  3. fsm_controller: state machines with configurable encoding
  4. stream_pipeline: ready-valid pipelined datapaths

Uses ``with self.comb:`` and ``with self.seq(...):`` context managers
for clean, uniform signal assignment syntax.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Union

from rtlgen.core import Module, Signal, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Switch, Mux, Const
from rtlgen.spec_ir import (
    ArchitectureIR,
    FlowControlSpec,
    PortSpec,
    SpecIR,
    StageSpec,
)


# ---------------------------------------------------------------------------
# Expression parser — handles "a * b + c", "a[7:0] & b", etc.
# ---------------------------------------------------------------------------

class _ExprParser:
    """Tokenize and parse RTL-like expressions into Signal AST nodes."""

    def __init__(self, module: "_GeneratedModule"):
        self._module = module

    def parse(self, text: str) -> Signal:
        tokens = self._tokenize(text.strip())
        self._pos = 0
        self._tokens = tokens
        return self._parse_bitwise_or()

    def _tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        i = 0
        while i < len(text):
            if text[i].isspace():
                i += 1
                continue
            if i + 1 < len(text) and text[i:i+2] in ("<<", ">>"):
                tokens.append(text[i:i+2])
                i += 2
                continue
            if text[i] in "+-*&|^()[]:":
                tokens.append(text[i])
                i += 1
                continue
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            if j == i:
                i += 1
                continue
            tokens.append(text[i:j])
            i = j
        return tokens

    def _parse_bitwise_or(self) -> Signal:
        left = self._parse_bitwise_xor()
        while self._peek() == "|":
            self._advance()
            left = left | self._parse_bitwise_xor()
        return left

    def _parse_bitwise_xor(self) -> Signal:
        left = self._parse_bitwise_and()
        while self._peek() == "^":
            self._advance()
            left = left ^ self._parse_bitwise_and()
        return left

    def _parse_bitwise_and(self) -> Signal:
        left = self._parse_additive()
        while self._peek() == "&":
            self._advance()
            left = left & self._parse_additive()
        return left

    def _parse_additive(self) -> Signal:
        left = self._parse_multiplicative()
        while self._peek() in ("+", "-"):
            op = self._advance()
            right = self._parse_multiplicative()
            left = left + right if op == "+" else left - right
        return left

    def _parse_multiplicative(self) -> Signal:
        left = self._parse_shift()
        while self._peek() == "*":
            self._advance()
            left = left * self._parse_shift()
        return left

    def _parse_shift(self) -> Signal:
        left = self._parse_primary()
        while self._peek() in ("<<", ">>"):
            op = self._advance()
            right = self._parse_primary()
            left = left << right if op == "<<" else left >> right
        return left

    def _parse_primary(self) -> Signal:
        tok = self._peek()
        if tok == "(":
            self._advance()
            expr = self._parse_bitwise_or()
            if self._peek() == ")":
                self._advance()
            return expr
        if tok and re.match(r'^[a-zA-Z_]\w*$', tok):
            name = self._advance()
            if self._peek() == "[":
                self._advance()
                hi = int(self._advance())
                if self._peek() == ":":
                    self._advance()
                lo = int(self._advance())
                if self._peek() == "]":
                    self._advance()
                sig = self._resolve(name)
                return sig[lo:hi+1] if hasattr(sig, '__getitem__') else sig
            return self._resolve(name)
        if tok and tok.isdigit():
            self._advance()
            return Const(int(tok), 32)
        self._advance()
        return self._resolve(tok) if tok else Const(0, 1)

    def _resolve(self, name: str) -> Signal:
        return self._module._resolve_operand(name)

    def _peek(self) -> Optional[str]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> str:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok


# ---------------------------------------------------------------------------
# DSL Generator
# ---------------------------------------------------------------------------

class DSLGenerator:
    """Generate a Module from SpecIR + ArchitectureIR."""

    def __init__(self, spec: SpecIR, arch: ArchitectureIR):
        self.spec = spec
        self.arch = arch

    def generate(self) -> Module:
        category = self.spec.category
        if category == "comb_alu":
            return self._generate_comb_alu()
        elif category == "register_update":
            return self._generate_register_update()
        elif category == "fsm_controller":
            return self._generate_fsm_controller()
        elif category == "stream_pipeline":
            return self._generate_stream_pipeline()
        else:
            return self._generate_comb_alu()

    def _generate_comb_alu(self) -> Module:
        m = CombALUModule(self.spec, self.arch)
        m._build()
        return m

    def _generate_register_update(self) -> Module:
        m = RegUpdateModule(self.spec, self.arch)
        m._build()
        return m

    def _generate_fsm_controller(self) -> Module:
        m = FSMControllerModule(self.spec, self.arch)
        m._build()
        return m

    def _generate_stream_pipeline(self) -> Module:
        m = StreamPipelineModule(self.spec, self.arch)
        m._build()
        return m


# ------------------------------------------------------------------
# Module implementations
# ------------------------------------------------------------------

class _GeneratedModule(Module):
    """Base class for generated modules."""

    def __init__(self, spec: SpecIR, arch: ArchitectureIR):
        super().__init__(spec.name)
        self._spec = spec
        self._arch = arch

    def _declare_ports(self):
        for port in self._spec.ports:
            if port.direction == "input":
                setattr(self, port.name, Input(port.width, port.name))
            else:
                setattr(self, port.name, Output(port.width, port.name))

    def _get_port(self, name: str) -> Signal:
        return getattr(self, name)

    def _resolve_operand(self, name: str) -> Signal:
        name = name.strip()
        if name.isdigit():
            return Const(int(name), 32)
        try:
            return self._get_port(name)
        except AttributeError:
            return Signal(1, name)

    def _parse_expr(self, text: str) -> Signal:
        return _ExprParser(self).parse(text)

    def _set(self, target_name: str, value) -> None:
        """Assign to a signal by name (used for dynamic f-string names)."""
        from rtlgen.core import Assign, Context, Wire, Output, _to_expr
        target = getattr(self, target_name)
        expr = _to_expr(value)
        blocking = isinstance(target, (Wire, Output))
        stmt = Assign(target=target, value=expr, blocking=blocking)
        ctx = Context.current()
        if ctx and ctx.stmt_container is not None:
            ctx.stmt_container.append(stmt)
        elif ctx and ctx.module is not None:
            ctx.module._top_level.append(stmt)
        else:
            raise RuntimeError(f"Assignment to '{target_name}' outside of any logic block")
        target._driven_by = "comb" if blocking else "seq"
        target._written_by_ilshift = True


class CombALUModule(_GeneratedModule):
    """Generated combinational ALU module."""

    def _build(self):
        self._declare_ports()
        func = self._spec.function

        if func.opcode_field:
            self._build_switch_alu()
        elif func.expr:
            self._build_expr_alu()

    def _build_switch_alu(self):
        func = self._spec.function
        if not func.operations:
            return

        out_name = None
        for port in self._spec.ports:
            if port.direction == "output":
                out_name = port.name
                break
        if out_name is None:
            return

        with self.comb:
            opcode = getattr(self, func.opcode_field)
            out = getattr(self, out_name)
            with Switch(opcode) as sw:
                for opcode_val, expr in func.operations.items():
                    with sw.case(int(opcode_val, 2)):
                        out <<= self._parse_expr(expr)
                with sw.default():
                    out <<= 0

    def _build_expr_alu(self):
        expr = self._spec.function.expr
        if not expr:
            return

        lhs, rhs = expr.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()

        with self.comb:
            out = getattr(self, lhs)
            out <<= self._parse_expr(rhs)


class RegUpdateModule(_GeneratedModule):
    """Generated register update module (counter, accumulator)."""

    def _build(self):
        self._declare_ports()
        func = self._spec.function

        reset_async = (self._spec.reset_type == "async")
        reset_active_low = (self._spec.reset_active == "low")

        expr = func.expr
        if "=" not in expr:
            return

        lhs, rhs = expr.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()

        reg = self._get_or_create_reg(lhs)
        update_expr = self._parse_expr(rhs)
        reset_name = self._spec.reset_name

        # Create clock and reset
        setattr(self, "clk", Input(1, "clk"))
        try:
            self._get_port(reset_name)
        except AttributeError:
            setattr(self, reset_name, Input(1, reset_name))

        rst = getattr(self, reset_name)

        with self.seq(self.clk, rst, reset_async=reset_async, reset_active_low=reset_active_low):
            if reset_active_low:
                with If(rst == 0):
                    reg <<= 0
                with Else():
                    reg <<= update_expr
            else:
                with If(rst == 1):
                    reg <<= 0
                with Else():
                    reg <<= update_expr

    def _get_or_create_reg(self, name: str) -> Signal:
        """Get or create a Reg for the given name."""
        try:
            sig = self._get_port(name)
            if isinstance(sig, Reg):
                return sig
            reg = Reg(32, name)
            setattr(self, name, reg)
            self._outputs[name] = reg
            return reg
        except AttributeError:
            reg = Reg(32, name)
            setattr(self, name, reg)
            self._outputs[name] = reg
            return reg


class FSMControllerModule(_GeneratedModule):
    """Generated FSM controller module.

    骨架结构：
      - clk / rst 输入
      - state 寄存器（时序逻辑更新）
      - next_state 组合逻辑（由智能体填充）

    智能体应在 comb 块中为 next_state 赋值，实现状态转换表。
    """

    def _build(self):
        self._declare_ports()

        reset_async = (self._spec.reset_type == "async")
        reset_active_low = (self._spec.reset_active == "low")

        state_width = 2
        for port in self._spec.ports:
            if "state" in port.name.lower():
                state_width = port.width
                break

        reset_name = self._spec.reset_name

        setattr(self, "clk", Input(1, "clk"))
        try:
            self._get_port(reset_name)
        except AttributeError:
            setattr(self, reset_name, Input(1, reset_name))

        state = Reg(state_width, "state")
        setattr(self, "state", state)

        if "state" not in self._outputs:
            setattr(self, "state_out", Output(state_width, "state_out"))
            self._outputs["state_out"] = getattr(self, "state_out")

        rst = getattr(self, reset_name)

        # 组合逻辑：next_state 由智能体在子类或外部填充
        next_state = Wire(state_width, "next_state")
        setattr(self, "next_state", next_state)

        with self.comb:
            # 默认保持当前状态；智能体应覆盖此赋值
            self.next_state <<= self.state

        with self.seq(self.clk, rst, reset_async=reset_async, reset_active_low=reset_active_low):
            if reset_active_low:
                with If(rst == 0):
                    self.state <<= 0
                with Else():
                    self.state <<= self.next_state
            else:
                with If(rst == 1):
                    self.state <<= 0
                with Else():
                    self.state <<= self.next_state


class StreamPipelineModule(_GeneratedModule):
    """Generated ready-valid stream pipeline module."""

    def _build(self):
        self._declare_ports()

        iface = self._spec.interfaces
        use_handshake = (iface and (
            iface.input_protocol == "ready_valid"
            or iface.output_protocol == "ready_valid"
        ))

        if use_handshake:
            self._build_pipeline_with_handshake()
        else:
            self._build_simple_pipeline()

    def _build_pipeline_with_handshake(self):
        stages = self._arch.stages
        if not stages:
            self._build_single_stage_handshake()
            return

        iface = self._spec.interfaces
        payload_width = 32
        if iface.input_payload:
            payload_width = iface.input_payload[0].width
        elif iface.output_payload:
            payload_width = iface.output_payload[0].width

        n = len(stages)
        reset_active_low = (self._spec.reset_active == "low")
        reset_async = (self._spec.reset_type == "async")
        reset_name = self._spec.reset_name

        setattr(self, "clk", Input(1, "clk"))
        try:
            self._get_port(reset_name)
        except AttributeError:
            setattr(self, reset_name, Input(1, reset_name))

        for i in range(n):
            setattr(self, f"valid_{i}", Reg(1, f"valid_{i}"))
        for i in range(1, n):
            setattr(self, f"pipe_{i}", Reg(payload_width, f"pipe_{i}"))
        for i in range(n):
            setattr(self, f"ready_{i}", Wire(1, f"ready_{i}"))

        rst = getattr(self, reset_name)

        with self.seq(self.clk, rst, reset_async=reset_async, reset_active_low=reset_active_low):
            with If(rst == 0) if reset_active_low else If(rst == 1):
                for i in range(n):
                    self._set(f"valid_{i}", 0)
                for i in range(1, n):
                    self._set(f"pipe_{i}", 0)
            with Else():
                self._emit_pipeline_stages(n)

        with self.comb:
            if hasattr(self, "out_ready"):
                self._set(f"ready_{n - 1}", self.out_ready)
            else:
                self._set(f"ready_{n - 1}", 1)
            for i in range(n - 2, -1, -1):
                self._set(f"ready_{i}",
                    ~getattr(self, f"valid_{i + 1}") |
                    getattr(self, f"ready_{i + 1}")
                )
            if hasattr(self, "out_valid"):
                self.out_valid <<= getattr(self, f"valid_{n - 1}")

    def _emit_pipeline_stages(self, n: int):
        for i in range(n - 1, 0, -1):
            self._set(f"valid_{i}",
                getattr(self, f"valid_{i - 1}") &
                getattr(self, f"ready_{i}")
            )
        for i in range(n - 1, 1, -1):
            self._set(f"pipe_{i}", getattr(self, f"pipe_{i - 1}"))
        if hasattr(self, "in_data"):
            self._set("pipe_1", self.in_data)
        if hasattr(self, "in_valid"):
            self._set("valid_0",
                self.in_valid & getattr(self, "ready_0")
            )

    def _build_single_stage_handshake(self):
        reset_active_low = (self._spec.reset_active == "low")
        reset_async = (self._spec.reset_type == "async")
        reset_name = self._spec.reset_name

        setattr(self, "clk", Input(1, "clk"))
        try:
            self._get_port(reset_name)
        except AttributeError:
            setattr(self, reset_name, Input(1, reset_name))

        setattr(self, "valid", Reg(1, "valid"))

        rst = getattr(self, reset_name)

        with self.seq(self.clk, rst, reset_async=reset_async, reset_active_low=reset_active_low):
            with If(rst == 0) if reset_active_low else If(rst == 1):
                self.valid <<= 0
            with Else():
                self.valid <<= self.in_valid & self.out_ready

        with self.comb:
            if hasattr(self, "out_ready"):
                self.out_ready <<= ~self.valid
            if hasattr(self, "out_valid"):
                self.out_valid <<= self.valid
            if hasattr(self, "in_ready"):
                self.in_ready <<= ~self.valid

    def _build_simple_pipeline(self):
        stages = self._arch.stages
        if not stages:
            return

        reset_active_low = (self._spec.reset_active == "low")
        reset_async = (self._spec.reset_type == "async")
        reset_name = self._spec.reset_name

        setattr(self, "clk", Input(1, "clk"))
        try:
            self._get_port(reset_name)
        except AttributeError:
            setattr(self, reset_name, Input(1, reset_name))

        pipe_indices = []
        for i, stage in enumerate(stages):
            if stage.register_outputs and i < len(stages) - 1:
                setattr(self, f"pipe_{i}", Reg(32, f"pipe_{i}"))
                pipe_indices.append(i)

        rst = getattr(self, reset_name)

        with self.seq(self.clk, rst, reset_async=reset_async, reset_active_low=reset_active_low):
            with If(rst == 0) if reset_active_low else If(rst == 1):
                for i in pipe_indices:
                    self._set(f"pipe_{i}", 0)
            with Else():
                pass

    def _ensure_port(self, name: str, default: Signal) -> Signal:
        try:
            return self._get_port(name)
        except AttributeError:
            setattr(self, name, default)
            if isinstance(default, Input):
                self._inputs[name] = default
            elif isinstance(default, Output):
                self._outputs[name] = default
            return default
