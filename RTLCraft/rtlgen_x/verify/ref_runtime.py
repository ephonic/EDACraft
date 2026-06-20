"""Minimal self-contained runtime for generated Python reference models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class Signal:
    name: str
    width: int
    kind: str
    signed: bool = False
    init: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("signal name must not be empty")
        if self.width < 1:
            raise ValueError("signal width must be positive")
        if self.kind not in {"input", "output", "state", "wire"}:
            raise ValueError(f"unsupported signal kind '{self.kind}'")

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1


@dataclass(frozen=True)
class Memory:
    name: str
    width: int
    depth: int
    init: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("memory name must not be empty")
        if self.width < 1:
            raise ValueError("memory width must be positive")
        if self.depth < 1:
            raise ValueError("memory depth must be positive")
        if self.init and len(self.init) != self.depth:
            raise ValueError("memory init must be empty or match depth")

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1


@dataclass(frozen=True)
class ConstExpr:
    value: int
    width: int

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError("const width must be positive")


@dataclass(frozen=True)
class SignalRef:
    name: str


@dataclass(frozen=True)
class MemoryReadExpr:
    memory: str
    addr: "Expr"


@dataclass(frozen=True)
class MaskExpr:
    value: "Expr"
    width: int

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError("mask width must be positive")


@dataclass(frozen=True)
class UnaryExpr:
    op: str
    value: "Expr"

    def __post_init__(self) -> None:
        if self.op not in {"~", "-", "!", "$signed", "$unsigned"}:
            raise ValueError(f"unsupported unary op '{self.op}'")


@dataclass(frozen=True)
class BinaryExpr:
    op: str
    lhs: "Expr"
    rhs: "Expr"

    def __post_init__(self) -> None:
        if self.op not in {
            "+",
            "-",
            "*",
            "&",
            "|",
            "^",
            "<<",
            ">>",
            ">>>",
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
        }:
            raise ValueError(f"unsupported binary op '{self.op}'")


@dataclass(frozen=True)
class MuxExpr:
    cond: "Expr"
    when_true: "Expr"
    when_false: "Expr"


Expr = Union[ConstExpr, SignalRef, MemoryReadExpr, MaskExpr, UnaryExpr, BinaryExpr, MuxExpr]


@dataclass(frozen=True)
class Assignment:
    target: str
    expr: Expr
    phase: str = "comb"

    def __post_init__(self) -> None:
        if self.phase not in {"comb", "seq"}:
            raise ValueError("assignment phase must be 'comb' or 'seq'")


@dataclass(frozen=True)
class MemoryWrite:
    memory: str
    addr: Expr
    value: Expr
    enable: Expr = ConstExpr(1, 1)


@dataclass(frozen=True)
class SimModule:
    name: str
    signals: Tuple[Signal, ...]
    assignments: Tuple[Assignment, ...]
    outputs: Tuple[str, ...]
    memories: Tuple[Memory, ...] = ()
    memory_writes: Tuple[MemoryWrite, ...] = ()
    reset_signal: Optional[str] = None
    outputs_post_state: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("module name must not be empty")
        if not self.signals:
            raise ValueError("module must contain at least one signal")
        signal_map: Dict[str, Signal] = {}
        for signal in self.signals:
            if signal.name in signal_map:
                raise ValueError(f"duplicate signal '{signal.name}'")
            signal_map[signal.name] = signal
        memory_map: Dict[str, Memory] = {}
        for memory in self.memories:
            if memory.name in signal_map:
                raise ValueError(f"memory '{memory.name}' conflicts with an existing signal")
            if memory.name in memory_map:
                raise ValueError(f"duplicate memory '{memory.name}'")
            memory_map[memory.name] = memory
        if not self.outputs:
            raise ValueError("module must expose at least one output")
        for output_name in self.outputs:
            signal = signal_map.get(output_name)
            if signal is None:
                raise ValueError(f"unknown output '{output_name}'")
            if signal.kind != "output":
                raise ValueError(f"output '{output_name}' must have kind='output'")
        if self.reset_signal is not None:
            reset_signal = signal_map.get(self.reset_signal)
            if reset_signal is None:
                raise ValueError(f"unknown reset signal '{self.reset_signal}'")
            if reset_signal.kind != "input":
                raise ValueError("reset signal must be declared as an input")
        for assignment in self.assignments:
            target = signal_map.get(assignment.target)
            if target is None:
                raise ValueError(f"assignment targets unknown signal '{assignment.target}'")
            if assignment.phase == "seq" and target.kind != "state":
                raise ValueError("sequential assignments may only target state signals")
            if assignment.phase == "comb" and target.kind == "state":
                raise ValueError("combinational assignments may not target state signals")
            self._validate_expr(assignment.expr, signal_map, memory_map)
        for write in self.memory_writes:
            memory = memory_map.get(write.memory)
            if memory is None:
                raise ValueError(f"memory write targets unknown memory '{write.memory}'")
            self._validate_expr(write.addr, signal_map, memory_map)
            self._validate_expr(write.value, signal_map, memory_map)
            self._validate_expr(write.enable, signal_map, memory_map)

    @staticmethod
    def _validate_expr(
        expr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
    ) -> None:
        if isinstance(expr, ConstExpr):
            return
        if isinstance(expr, SignalRef):
            if expr.name not in signal_map:
                raise ValueError(f"expression references unknown signal '{expr.name}'")
            return
        if isinstance(expr, MemoryReadExpr):
            if expr.memory not in memory_map:
                raise ValueError(f"expression references unknown memory '{expr.memory}'")
            SimModule._validate_expr(expr.addr, signal_map, memory_map)
            return
        if isinstance(expr, MaskExpr):
            SimModule._validate_expr(expr.value, signal_map, memory_map)
            return
        if isinstance(expr, UnaryExpr):
            SimModule._validate_expr(expr.value, signal_map, memory_map)
            return
        if isinstance(expr, BinaryExpr):
            SimModule._validate_expr(expr.lhs, signal_map, memory_map)
            SimModule._validate_expr(expr.rhs, signal_map, memory_map)
            return
        if isinstance(expr, MuxExpr):
            SimModule._validate_expr(expr.cond, signal_map, memory_map)
            SimModule._validate_expr(expr.when_true, signal_map, memory_map)
            SimModule._validate_expr(expr.when_false, signal_map, memory_map)
            return
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def signal_map(self) -> Dict[str, Signal]:
        return {signal.name: signal for signal in self.signals}

    def memory_map(self) -> Dict[str, Memory]:
        return {memory.name: memory for memory in self.memories}


@dataclass
class PythonSimulator:
    module: SimModule

    def __post_init__(self) -> None:
        self._signal_map = self.module.signal_map()
        self._memory_map = self.module.memory_map()
        self.input_names = tuple(
            signal.name for signal in self.module.signals if signal.kind == "input"
        )
        self.output_names = tuple(self.module.outputs)
        self._input_masks = tuple(self._signal_map[name].mask for name in self.input_names)
        self._output_masks = tuple(self._signal_map[name].mask for name in self.output_names)
        self._comb_assignments = tuple(
            assignment for assignment in self.module.assignments if assignment.phase == "comb"
        )
        self._seq_assignments = tuple(
            assignment for assignment in self.module.assignments if assignment.phase == "seq"
        )
        self._state_init = {
            signal.name: signal.init & signal.mask
            for signal in self.module.signals
            if signal.kind == "state"
        }
        self._memory_init = {
            memory.name: tuple(
                (memory.init[idx] if memory.init else 0) & memory.mask
                for idx in range(memory.depth)
            )
            for memory in self.module.memories
        }
        self._wire_and_output_names = tuple(
            signal.name for signal in self.module.signals if signal.kind in {"wire", "output"}
        )
        self.reset()

    def reset(self) -> None:
        self._state = dict(self._state_init)
        self._memories = {name: list(values) for name, values in self._memory_init.items()}

    def step(self, inputs: Mapping[str, int]) -> Dict[str, int]:
        unknown_inputs = sorted(set(inputs) - set(self.input_names))
        if unknown_inputs:
            raise KeyError(f"unknown simulator inputs: {', '.join(unknown_inputs)}")
        raw_inputs = tuple(int(inputs.get(name, 0)) for name in self.input_names)
        raw_outputs = self.step_raw(raw_inputs)
        return {
            name: raw_outputs[idx] & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        }

    def step_raw(self, input_values: Sequence[int]) -> Tuple[int, ...]:
        if len(input_values) != len(self.input_names):
            raise ValueError(
                f"expected {len(self.input_names)} input values, got {len(input_values)}"
            )
        values = {
            name: int(input_values[idx]) & self._input_masks[idx]
            for idx, name in enumerate(self.input_names)
        }
        for name in self._wire_and_output_names:
            values[name] = 0

        for assignment in self._comb_assignments:
            signal = self._signal_map[assignment.target]
            values[assignment.target] = self._eval_expr(assignment.expr, values) & signal.mask

        next_state = dict(self._state)
        pending_writes: Tuple[Tuple[str, int, int], ...] = ()
        reset_active = False
        if self.module.reset_signal is not None:
            reset_active = bool(values[self.module.reset_signal])
        if reset_active:
            next_state = dict(self._state_init)
        else:
            for assignment in self._seq_assignments:
                signal = self._signal_map[assignment.target]
                next_state[assignment.target] = self._eval_expr(assignment.expr, values) & signal.mask
            pending_writes = self._compute_memory_writes(values)
        self._state = next_state
        if reset_active:
            self._memories = {name: list(values) for name, values in self._memory_init.items()}
        else:
            for memory_name, addr, value in pending_writes:
                self._memories[memory_name][addr] = value
        if self.module.outputs_post_state:
            for name in self._wire_and_output_names:
                values[name] = 0
            for assignment in self._comb_assignments:
                signal = self._signal_map[assignment.target]
                values[assignment.target] = self._eval_expr(assignment.expr, values) & signal.mask
        return tuple(
            values[name] & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        )

    def run_batch(self, input_rows: Sequence[Sequence[int]]) -> Tuple[Dict[str, int], ...]:
        rows = []
        for row in input_rows:
            raw_outputs = self.step_raw(row)
            rows.append(
                {
                    name: raw_outputs[idx] & self._output_masks[idx]
                    for idx, name in enumerate(self.output_names)
                }
            )
        return tuple(rows)

    def _eval_expr(self, expr: Expr, values: Mapping[str, int]) -> int:
        if isinstance(expr, ConstExpr):
            return expr.value & ((1 << expr.width) - 1)
        if isinstance(expr, SignalRef):
            signal = self._signal_map[expr.name]
            if signal.kind == "state":
                return self._state[expr.name]
            return values[expr.name]
        if isinstance(expr, MemoryReadExpr):
            memory = self._memory_map[expr.memory]
            addr = self._eval_expr(expr.addr, values) % memory.depth
            return self._memories[expr.memory][addr]
        if isinstance(expr, MaskExpr):
            return self._eval_expr(expr.value, values) & ((1 << expr.width) - 1)
        if isinstance(expr, UnaryExpr):
            value = self._eval_expr(expr.value, values)
            width = self._expr_width(expr.value)
            if expr.op == "~":
                return (~value) & ((1 << width) - 1)
            if expr.op == "-":
                return -value
            if expr.op == "!":
                return int(not value)
            if expr.op == "$signed":
                sign_bit = 1 << (width - 1)
                masked = value & ((1 << width) - 1)
                return masked - (1 << width) if masked & sign_bit else masked
            if expr.op == "$unsigned":
                return value & ((1 << width) - 1)
            raise TypeError(f"unsupported unary op '{expr.op}'")
        if isinstance(expr, BinaryExpr):
            lhs = self._eval_expr(expr.lhs, values)
            rhs = self._eval_expr(expr.rhs, values)
            if expr.op == "+":
                return lhs + rhs
            if expr.op == "-":
                return lhs - rhs
            if expr.op == "*":
                return lhs * rhs
            if expr.op == "&":
                return lhs & rhs
            if expr.op == "|":
                return lhs | rhs
            if expr.op == "^":
                return lhs ^ rhs
            if expr.op == "<<":
                return lhs << rhs
            if expr.op == ">>":
                return lhs >> rhs
            if expr.op == ">>>":
                lhs_width = self._expr_width(expr.lhs)
                masked_lhs = lhs & ((1 << lhs_width) - 1)
                if self._expr_is_signed(expr.lhs):
                    sign_bit = 1 << (lhs_width - 1)
                    signed_lhs = masked_lhs - (1 << lhs_width) if masked_lhs & sign_bit else masked_lhs
                    return signed_lhs >> rhs
                return masked_lhs >> rhs
            if expr.op == "==":
                return int(lhs == rhs)
            if expr.op == "!=":
                return int(lhs != rhs)
            if expr.op == "<":
                return int(lhs < rhs)
            if expr.op == "<=":
                return int(lhs <= rhs)
            if expr.op == ">":
                return int(lhs > rhs)
            if expr.op == ">=":
                return int(lhs >= rhs)
            raise TypeError(f"unsupported binary op '{expr.op}'")
        if isinstance(expr, MuxExpr):
            branch = expr.when_true if self._eval_expr(expr.cond, values) else expr.when_false
            return self._eval_expr(branch, values)
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _compute_memory_writes(self, values: Mapping[str, int]) -> Tuple[Tuple[str, int, int], ...]:
        writes = []
        for write in self.module.memory_writes:
            memory = self._memory_map[write.memory]
            if not self._eval_expr(write.enable, values):
                continue
            addr = self._eval_expr(write.addr, values) % memory.depth
            value = self._eval_expr(write.value, values) & memory.mask
            writes.append((write.memory, addr, value))
        return tuple(writes)

    def _expr_width(self, expr: Expr) -> int:
        if isinstance(expr, ConstExpr):
            return expr.width
        if isinstance(expr, SignalRef):
            return self._signal_map[expr.name].width
        if isinstance(expr, MemoryReadExpr):
            return self._memory_map[expr.memory].width
        if isinstance(expr, MaskExpr):
            return expr.width
        if isinstance(expr, UnaryExpr):
            return self._expr_width(expr.value)
        if isinstance(expr, BinaryExpr):
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                return 1
            return max(self._expr_width(expr.lhs), self._expr_width(expr.rhs))
        if isinstance(expr, MuxExpr):
            return max(self._expr_width(expr.when_true), self._expr_width(expr.when_false))
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _expr_is_signed(self, expr: Expr) -> bool:
        if isinstance(expr, ConstExpr):
            return False
        if isinstance(expr, SignalRef):
            return self._signal_map[expr.name].signed
        if isinstance(expr, MemoryReadExpr):
            return False
        if isinstance(expr, MaskExpr):
            return False
        if isinstance(expr, UnaryExpr):
            if expr.op == "$signed":
                return True
            if expr.op in {"$unsigned", "!"}:
                return False
            return self._expr_is_signed(expr.value)
        if isinstance(expr, BinaryExpr):
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                return False
            return self._expr_is_signed(expr.lhs) or self._expr_is_signed(expr.rhs)
        if isinstance(expr, MuxExpr):
            return self._expr_is_signed(expr.when_true) and self._expr_is_signed(expr.when_false)
        raise TypeError(f"unsupported expression type: {type(expr)!r}")
