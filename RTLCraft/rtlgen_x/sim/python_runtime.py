"""Pure-Python reference simulator for the local executable model."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Mapping, Optional, Sequence, Tuple

from rtlgen_x.sim.cpp_backend import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    Expr,
    MaskExpr,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Memory,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
    pack_u64_words,
)


@dataclass
class PythonSimulator:
    """Simple reference interpreter for the compiled-simulator local model."""

    module: SimModule

    def __post_init__(self) -> None:
        self._signal_map = self.module.signal_map()
        self.input_names = tuple(
            signal.name for signal in self.module.signals if signal.kind == "input"
        )
        self.output_names = tuple(self.module.outputs)
        self.input_count = len(self.input_names)
        self.output_count = len(self.output_names)
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
        self._memory_map = self.module.memory_map()
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
            joined = ", ".join(unknown_inputs)
            raise KeyError(f"unknown simulator inputs: {joined}")
        raw_inputs = tuple(int(inputs.get(name, 0)) for name in self.input_names)
        raw_outputs = self.step_raw(raw_inputs)
        return {
            name: raw_outputs[idx] & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        }

    def step_raw(self, input_values: Sequence[int]) -> Tuple[int, ...]:
        if len(input_values) != self.input_count:
            raise ValueError(
                f"expected {self.input_count} input values, got {len(input_values)}"
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
        outputs = tuple(values[name] & self._output_masks[idx] for idx, name in enumerate(self.output_names))
        return outputs

    def run_batch_raw(self, flat_inputs: Sequence[int], cycles: int) -> Tuple[int, ...]:
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        output_buffer = self.run_batch_buffered(pack_u64_words(flat_inputs), cycles)
        return tuple(int(value) for value in output_buffer)

    def run_batch_buffered(
        self,
        flat_inputs: array,
        cycles: int,
        output_buffer: Optional[array] = None,
    ) -> array:
        """Run a packed batch using reusable unsigned-64 buffers."""

        if flat_inputs.typecode != "Q":
            raise TypeError("flat_inputs must be array('Q')")
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        total_outputs = cycles * self.output_count
        if output_buffer is None:
            output_buffer = array("Q", [0]) * total_outputs
        else:
            if output_buffer.typecode != "Q":
                raise TypeError("output_buffer must be array('Q')")
            if len(output_buffer) != total_outputs:
                raise ValueError(
                    f"expected output_buffer length {total_outputs}, got {len(output_buffer)}"
                )
        for cycle in range(cycles):
            start = cycle * self.input_count
            row = flat_inputs[start : start + self.input_count]
            outputs = self.step_raw(row)
            output_start = cycle * self.output_count
            for idx, value in enumerate(outputs):
                output_buffer[output_start + idx] = value & self._output_masks[idx]
        return output_buffer

    def iter_batch_buffered(
        self,
        input_rows: Iterable[Sequence[int]],
        *,
        chunk_cycles: int = 65536,
    ) -> Iterator[array]:
        """Stream arbitrarily long batches in bounded chunks."""

        if chunk_cycles < 1:
            raise ValueError("chunk_cycles must be positive")
        chunk_inputs = array("Q")
        chunk_len = 0
        for row in input_rows:
            if len(row) != self.input_count:
                raise ValueError(f"expected {self.input_count} input values, got {len(row)}")
            for value in row:
                chunk_inputs.append(int(value) & 0xFFFFFFFFFFFFFFFF)
            chunk_len += 1
            if chunk_len == chunk_cycles:
                yield self.run_batch_buffered(chunk_inputs, chunk_len)
                chunk_inputs = array("Q")
                chunk_len = 0
        if chunk_len:
            yield self.run_batch_buffered(chunk_inputs, chunk_len)

    def run_batch(self, input_rows: Sequence[Sequence[int]]) -> Tuple[Dict[str, int], ...]:
        outputs = []
        for row in input_rows:
            raw_outputs = self.step_raw(row)
            outputs.append(
                {
                    name: raw_outputs[idx] & self._output_masks[idx]
                    for idx, name in enumerate(self.output_names)
                }
            )
        return tuple(outputs)

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
                    signed_lhs = (
                        masked_lhs - (1 << lhs_width) if masked_lhs & sign_bit else masked_lhs
                    )
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
            cond = self._eval_expr(expr.cond, values)
            branch = expr.when_true if cond else expr.when_false
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
            if expr.op == "$unsigned":
                return False
            if expr.op == "!":
                return False
            return self._expr_is_signed(expr.value)
        if isinstance(expr, BinaryExpr):
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                return False
            return self._expr_is_signed(expr.lhs) or self._expr_is_signed(expr.rhs)
        if isinstance(expr, MuxExpr):
            return self._expr_is_signed(expr.when_true) and self._expr_is_signed(
                expr.when_false
            )
        raise TypeError(f"unsupported expression type: {type(expr)!r}")
