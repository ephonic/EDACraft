"""Pure-Python reference simulator for the local executable model."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Mapping, Optional, Sequence, Tuple

import numpy as np

from rtlgen_x.sim.cpp_backend import (
    Assignment,
    BinaryExpr,
    ClockDomain,
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
    pack_signal_values_u64_words,
    pack_u64_words,
    unpack_signal_values_u64_words,
    _word_count,
    _word_slices,
)


@dataclass(frozen=True)
class _PendingMemoryWrite:
    memory_name: str
    addr: int
    value: int
    byte_enable: Optional[int] = None


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
        self.state_names = tuple(
            [signal.name for signal in self.module.signals if signal.kind == "state"]
            + [
                f"{memory.name}[{idx}]"
                for memory in self.module.memories
                for idx in range(memory.depth)
            ]
        )
        self.input_count = len(self.input_names)
        self.output_count = len(self.output_names)
        self.state_count = len(self.state_names)
        self.input_widths = tuple(self._signal_map[name].width for name in self.input_names)
        self.output_widths = tuple(self._signal_map[name].width for name in self.output_names)
        self.state_widths = tuple(
            [self._signal_map[signal.name].width for signal in self.module.signals if signal.kind == "state"]
            + [memory.width for memory in self.module.memories for _ in range(memory.depth)]
        )
        self.input_word_slices = _word_slices(self.input_widths)
        self.output_word_slices = _word_slices(self.output_widths)
        self.state_word_slices = _word_slices(self.state_widths)
        self.input_word_count = sum(words for _, words in self.input_word_slices)
        self.output_word_count = sum(words for _, words in self.output_word_slices)
        self.state_word_count = sum(words for _, words in self.state_word_slices)
        self._input_masks = tuple(self._signal_map[name].mask for name in self.input_names)
        self._output_masks = tuple(self._signal_map[name].mask for name in self.output_names)
        self._comb_assignments = tuple(
            assignment for assignment in self.module.assignments if assignment.phase == "comb"
        )
        self._latch_assignments = tuple(
            assignment for assignment in self.module.assignments if assignment.phase == "latch"
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
        self._memory_read_policies = {
            memory.name: memory.read_during_write
            for memory in self.module.memories
        }
        self._clock_domains = {
            domain.name: domain
            for domain in self.module.clock_domains
        }
        self.clock_domain_names = tuple(self._clock_domains.keys())
        self._clock_domain_name_by_alias = {
            domain.name: domain.name
            for domain in self.module.clock_domains
        }
        for domain in self.module.clock_domains:
            for alias in getattr(domain, "aliases", ()):
                self._clock_domain_name_by_alias.setdefault(str(alias), domain.name)
        self._multi_clock = len(self.clock_domain_names) > 1
        self._memory_init = {
            memory.name: tuple(
                (memory.init[idx] if memory.init else 0) & memory.mask
                for idx in range(memory.depth)
            )
            for memory in self.module.memories
        }
        self._seq_assignments_by_domain = self._group_seq_assignments_by_domain()
        self._memory_writes_by_domain = self._group_memory_writes_by_domain()
        self._state_targets_by_domain = {
            domain_name: tuple(dict.fromkeys(assignment.target for assignment in assignments))
            for domain_name, assignments in self._seq_assignments_by_domain.items()
        }
        self._memories_by_domain = {
            domain_name: tuple(dict.fromkeys(write.memory for write in writes))
            for domain_name, writes in self._memory_writes_by_domain.items()
        }
        self._wire_and_output_names = tuple(
            signal.name for signal in self.module.signals if signal.kind in {"wire", "output"}
        )
        self.reset()

    def reset(self) -> None:
        self._state = dict(self._state_init)
        self._memories = {name: list(values) for name, values in self._memory_init.items()}

    def _default_clock_domain(self) -> Optional[str]:
        if len(self.clock_domain_names) == 1:
            return self.clock_domain_names[0]
        return None

    def _resolve_clock_domain_name(self, explicit_name: Optional[str]) -> Optional[str]:
        if not self._clock_domains:
            return explicit_name
        if explicit_name is not None:
            return self._clock_domain_name_by_alias.get(explicit_name, explicit_name)
        return self._default_clock_domain()

    def _group_seq_assignments_by_domain(self) -> Dict[str, Tuple[Assignment, ...]]:
        if not self._clock_domains:
            return {}
        grouped = {name: [] for name in self.clock_domain_names}
        for assignment in self._seq_assignments:
            domain_name = self._resolve_clock_domain_name(assignment.clock_domain)
            if domain_name is None:
                raise ValueError(
                    "sequential assignments in a multi-clock module must declare clock_domain"
                )
            grouped[domain_name].append(assignment)
        return {
            domain_name: tuple(assignments)
            for domain_name, assignments in grouped.items()
        }

    def _group_memory_writes_by_domain(self) -> Dict[str, Tuple[MemoryWrite, ...]]:
        if not self._clock_domains:
            return {}
        grouped = {name: [] for name in self.clock_domain_names}
        for write in self.module.memory_writes:
            domain_name = self._resolve_clock_domain_name(write.clock_domain)
            if domain_name is None:
                raise ValueError("memory writes in a multi-clock module must declare clock_domain")
            grouped[domain_name].append(write)
        return {
            domain_name: tuple(writes)
            for domain_name, writes in grouped.items()
        }

    def _normalize_active_domains(
        self,
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Tuple[str, ...]:
        if not self._clock_domains:
            raise ValueError("step_clocks() requires module.clock_domains metadata")
        if isinstance(active_domains, Mapping):
            selected = [name for name, enabled in active_domains.items() if enabled]
        else:
            selected = list(active_domains)
        normalized = []
        unknown = []
        for raw_name in selected:
            canonical = self._clock_domain_name_by_alias.get(str(raw_name))
            if canonical is None:
                unknown.append(str(raw_name))
                continue
            normalized.append(canonical)
        ordered = tuple(dict.fromkeys(normalized))
        if unknown:
            joined = ", ".join(unknown)
            raise KeyError(f"unknown clock domains: {joined}")
        return ordered

    def _domain_reset_active(self, domain_name: str, values: Mapping[str, int]) -> bool:
        domain = self._clock_domains[domain_name]
        if domain.reset_signal is None:
            return False
        reset_value = bool(values.get(domain.reset_signal, 0))
        return not reset_value if domain.reset_active_low else reset_value

    def _expr_references_signal(self, expr: Expr, signal_name: Optional[str]) -> bool:
        if not signal_name:
            return False
        if isinstance(expr, ConstExpr):
            return False
        if isinstance(expr, SignalRef):
            return expr.name == signal_name
        if isinstance(expr, MemoryReadExpr):
            return self._expr_references_signal(expr.addr, signal_name)
        if isinstance(expr, MaskExpr):
            return self._expr_references_signal(expr.value, signal_name)
        if isinstance(expr, UnaryExpr):
            return self._expr_references_signal(expr.value, signal_name)
        if isinstance(expr, BinaryExpr):
            return self._expr_references_signal(expr.lhs, signal_name) or self._expr_references_signal(
                expr.rhs,
                signal_name,
            )
        if isinstance(expr, MuxExpr):
            return (
                self._expr_references_signal(expr.cond, signal_name)
                or self._expr_references_signal(expr.when_true, signal_name)
                or self._expr_references_signal(expr.when_false, signal_name)
            )
        return False

    def _assignment_handles_domain_reset(self, assignment: Assignment, reset_signal: Optional[str]) -> bool:
        return self._expr_references_signal(assignment.expr, reset_signal)

    def _memory_write_handles_domain_reset(
        self,
        write: MemoryWrite,
        reset_signal: Optional[str],
    ) -> bool:
        return (
            self._expr_references_signal(write.addr, reset_signal)
            or self._expr_references_signal(write.value, reset_signal)
            or self._expr_references_signal(write.enable, reset_signal)
            or (
                write.byte_enable is not None
                and self._expr_references_signal(write.byte_enable, reset_signal)
            )
        )

    def step(self, inputs: Mapping[str, int]) -> Dict[str, int]:
        if self._multi_clock:
            raise ValueError("multi-clock modules must use step_clocks(...) with explicit active domains")
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

    def step_clocks(
        self,
        inputs: Mapping[str, int],
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Dict[str, int]:
        unknown_inputs = sorted(set(inputs) - set(self.input_names))
        if unknown_inputs:
            joined = ", ".join(unknown_inputs)
            raise KeyError(f"unknown simulator inputs: {joined}")
        raw_inputs = tuple(int(inputs.get(name, 0)) for name in self.input_names)
        raw_outputs = self.step_raw_clocks(raw_inputs, active_domains)
        return {
            name: raw_outputs[idx] & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        }

    def step_raw(self, input_values: Sequence[int]) -> Tuple[int, ...]:
        if self._multi_clock:
            raise ValueError("multi-clock modules must use step_raw_clocks(...) with explicit active domains")
        if self._clock_domains:
            return self._step_raw_with_domains(input_values, self.clock_domain_names)
        return self._step_raw_with_domains(input_values, ())

    def step_raw_clocks(
        self,
        input_values: Sequence[int],
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Tuple[int, ...]:
        normalized_domains = self._normalize_active_domains(active_domains)
        return self._step_raw_with_domains(input_values, normalized_domains)

    def _step_raw_with_domains(
        self,
        input_values: Sequence[int],
        active_domains: Sequence[str],
    ) -> Tuple[int, ...]:
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
        pending_writes: Tuple[_PendingMemoryWrite, ...] = ()
        for assignment in self._latch_assignments:
            signal = self._signal_map[assignment.target]
            latched_value = self._eval_expr(assignment.expr, values) & signal.mask
            next_state[assignment.target] = latched_value
            self._state[assignment.target] = latched_value
        if self._clock_domains:
            state_updates: Dict[str, int] = {}
            pending_writes = []
            pending_memory_resets = set()
            for domain_name in active_domains:
                domain = self._clock_domains[domain_name]
                reset_active = self._domain_reset_active(domain_name, values)
                for assignment in self._seq_assignments_by_domain.get(domain_name, ()):
                    signal = self._signal_map[assignment.target]
                    if reset_active and not self._assignment_handles_domain_reset(
                        assignment,
                        domain.reset_signal,
                    ):
                        state_updates[assignment.target] = self._state_init[assignment.target]
                        continue
                    state_updates[assignment.target] = self._eval_expr(assignment.expr, values) & signal.mask
                domain_writes = self._memory_writes_by_domain.get(domain_name, ())
                if reset_active:
                    handled_memories = set()
                    for write in domain_writes:
                        if not self._memory_write_handles_domain_reset(write, domain.reset_signal):
                            continue
                        pending_writes.extend(self._compute_memory_writes(values, (write,)))
                        handled_memories.add(write.memory)
                    for memory_name in self._memories_by_domain.get(domain_name, ()):
                        if memory_name not in handled_memories:
                            pending_memory_resets.add(memory_name)
                else:
                    pending_writes.extend(self._compute_memory_writes(values, domain_writes))
            next_state.update(state_updates)
        else:
            reset_active = False
            handled_memories = set()
            if self.module.reset_signal is not None:
                reset_active = bool(values[self.module.reset_signal])
            for assignment in self._seq_assignments:
                signal = self._signal_map[assignment.target]
                if reset_active and not self._assignment_handles_domain_reset(
                    assignment,
                    self.module.reset_signal,
                ):
                    next_state[assignment.target] = self._state_init[assignment.target]
                    continue
                next_state[assignment.target] = self._eval_expr(assignment.expr, values) & signal.mask
            if reset_active:
                computed_writes = []
                for write in self.module.memory_writes:
                    if not self._memory_write_handles_domain_reset(write, self.module.reset_signal):
                        continue
                    computed_writes.extend(self._compute_memory_writes(values, (write,)))
                    handled_memories.add(write.memory)
                pending_writes = tuple(computed_writes)
            else:
                pending_writes = self._compute_memory_writes(values, self.module.memory_writes)
        read_first_overrides = self._capture_read_first_memory_overrides(pending_writes)
        self._state = next_state
        if not self._clock_domains and reset_active:
            for memory_name, init_values in self._memory_init.items():
                if memory_name in handled_memories:
                    continue
                self._memories[memory_name] = list(init_values)
        else:
            for memory_name in pending_memory_resets if self._clock_domains else ():
                self._memories[memory_name] = list(self._memory_init[memory_name])
            for write in pending_writes:
                self._memories[write.memory_name][write.addr] = self._merge_memory_write(write)
        if self.module.outputs_post_state:
            for name in self._wire_and_output_names:
                values[name] = 0
            for assignment in self._comb_assignments:
                signal = self._signal_map[assignment.target]
                values[assignment.target] = (
                    self._eval_expr(assignment.expr, values, memory_overrides=read_first_overrides)
                    & signal.mask
                )
        outputs = tuple(values[name] & self._output_masks[idx] for idx, name in enumerate(self.output_names))
        return outputs

    def run_batch_raw(self, flat_inputs: Sequence[int], cycles: int) -> Tuple[int, ...]:
        if self._multi_clock:
            raise ValueError("run_batch_raw() is only supported for single-clock modules")
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        packed_inputs = array("Q")
        for cycle in range(cycles):
            start = cycle * self.input_count
            packed_inputs.extend(
                pack_signal_values_u64_words(
                    flat_inputs[start : start + self.input_count],
                    self.input_widths,
                )
            )
        output_buffer = self.run_batch_buffered(packed_inputs, cycles)
        unpacked_outputs = []
        for cycle in range(cycles):
            start = cycle * self.output_word_count
            unpacked_outputs.extend(
                unpack_signal_values_u64_words(
                    output_buffer[start : start + self.output_word_count],
                    self.output_widths,
                )
            )
        return tuple(unpacked_outputs)

    def run_batch_buffered(
        self,
        flat_inputs: array,
        cycles: int,
        output_buffer: Optional[array] = None,
    ) -> array:
        """Run a packed batch using reusable unsigned-64 buffers."""

        if self._multi_clock:
            raise ValueError("run_batch_buffered() is only supported for single-clock modules")
        if flat_inputs.typecode != "Q":
            raise TypeError("flat_inputs must be array('Q')")
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_word_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        total_outputs = cycles * self.output_word_count
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
            start = cycle * self.input_word_count
            row_words = flat_inputs[start : start + self.input_word_count]
            row = unpack_signal_values_u64_words(row_words, self.input_widths)
            outputs = self.step_raw(row)
            packed_outputs = pack_signal_values_u64_words(outputs, self.output_widths)
            output_start = cycle * self.output_word_count
            for idx, value in enumerate(packed_outputs):
                output_buffer[output_start + idx] = value & 0xFFFFFFFFFFFFFFFF
        return output_buffer

    def iter_batch_buffered(
        self,
        input_rows: Iterable[Sequence[int]],
        *,
        chunk_cycles: int = 65536,
    ) -> Iterator[array]:
        """Stream arbitrarily long batches in bounded chunks."""

        if self._multi_clock:
            raise ValueError("iter_batch_buffered() is only supported for single-clock modules")
        if chunk_cycles < 1:
            raise ValueError("chunk_cycles must be positive")
        chunk_inputs = array("Q")
        chunk_len = 0
        for row in input_rows:
            if len(row) != self.input_count:
                raise ValueError(f"expected {self.input_count} input values, got {len(row)}")
            chunk_inputs.extend(pack_signal_values_u64_words(row, self.input_widths))
            chunk_len += 1
            if chunk_len == chunk_cycles:
                yield self.run_batch_buffered(chunk_inputs, chunk_len)
                chunk_inputs = array("Q")
                chunk_len = 0
        if chunk_len:
            yield self.run_batch_buffered(chunk_inputs, chunk_len)

    def run_batch(self, input_rows: Sequence[Sequence[int]]) -> Tuple[Dict[str, int], ...]:
        if self._multi_clock:
            raise ValueError("run_batch() is only supported for single-clock modules")
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

    def _eval_expr(
        self,
        expr: Expr,
        values: Mapping[str, int],
        *,
        memory_overrides: Optional[Mapping[Tuple[str, int], int]] = None,
    ) -> int:
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
            if memory_overrides is not None:
                override = memory_overrides.get((expr.memory, addr))
                if override is not None:
                    return override
            return self._memories[expr.memory][addr]
        if isinstance(expr, MaskExpr):
            return self._eval_expr(expr.value, values, memory_overrides=memory_overrides) & ((1 << expr.width) - 1)
        if isinstance(expr, UnaryExpr):
            value = self._eval_expr(expr.value, values, memory_overrides=memory_overrides)
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
            lhs = self._eval_expr(expr.lhs, values, memory_overrides=memory_overrides)
            rhs = self._eval_expr(expr.rhs, values, memory_overrides=memory_overrides)
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
                lhs_width = self._expr_width(expr.lhs)
                masked_lhs = lhs & ((1 << lhs_width) - 1)
                if self._expr_is_signed(expr.lhs):
                    sign_bit = 1 << (lhs_width - 1)
                    signed_lhs = masked_lhs - (1 << lhs_width) if masked_lhs & sign_bit else masked_lhs
                    return signed_lhs >> rhs
                return masked_lhs >> rhs
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
            cond = self._eval_expr(expr.cond, values, memory_overrides=memory_overrides)
            branch = expr.when_true if cond else expr.when_false
            return self._eval_expr(branch, values, memory_overrides=memory_overrides)
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _compute_memory_writes(
        self,
        values: Mapping[str, int],
        writes: Sequence[MemoryWrite],
    ) -> Tuple["_PendingMemoryWrite", ...]:
        pending = []
        for write in writes:
            memory = self._memory_map[write.memory]
            if not self._eval_expr(write.enable, values):
                continue
            addr = self._eval_expr(write.addr, values) % memory.depth
            value = self._eval_expr(write.value, values) & memory.mask
            byte_enable = None
            if write.byte_enable is not None:
                byte_enable_width = memory.byte_enable_width
                assert byte_enable_width is not None
                byte_enable = self._eval_expr(write.byte_enable, values) & (
                    (1 << byte_enable_width) - 1
                )
            pending.append(_PendingMemoryWrite(write.memory, addr, value, byte_enable))
        return tuple(pending)

    def _capture_read_first_memory_overrides(
        self,
        pending_writes: Sequence["_PendingMemoryWrite"],
    ) -> Dict[Tuple[str, int], int]:
        overrides: Dict[Tuple[str, int], int] = {}
        for write in pending_writes:
            if self._memory_read_policies.get(write.memory_name) != "read_first":
                continue
            overrides[(write.memory_name, write.addr)] = self._memories[write.memory_name][
                write.addr
            ]
        return overrides

    def _merge_memory_write(self, write: "_PendingMemoryWrite") -> int:
        memory = self._memory_map[write.memory_name]
        if memory.byte_enable_granularity is None:
            return write.value & memory.mask
        if write.byte_enable is None:
            raise ValueError(
                f"memory '{write.memory_name}' declares byte_enable_granularity, "
                "but the pending write does not provide byte_enable"
            )
        lane_width = memory.byte_enable_granularity
        lane_count = memory.byte_enable_width
        assert lane_count is not None
        prior = self._memories[write.memory_name][write.addr] & memory.mask
        merged = prior
        lane_mask = (1 << lane_width) - 1
        for lane_idx in range(lane_count):
            if ((write.byte_enable >> lane_idx) & 1) == 0:
                continue
            shift = lane_idx * lane_width
            merged &= ~(lane_mask << shift)
            merged |= ((write.value >> shift) & lane_mask) << shift
        return merged & memory.mask

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
            if expr.op == "*":
                return self._expr_width(expr.lhs) + self._expr_width(expr.rhs)
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

    def snapshot_state_numpy(self) -> np.ndarray:
        payload = array("Q")
        for signal in self.module.signals:
            if signal.kind == "state":
                payload.extend(pack_signal_values_u64_words((self._state[signal.name] & signal.mask,), (signal.width,)))
        for memory in self.module.memories:
            for value in self._memories[memory.name]:
                payload.extend(pack_signal_values_u64_words((value & memory.mask,), (memory.width,)))
        return np.asarray(payload, dtype=np.uint64)

    def snapshot_state_values(self) -> Tuple[int, ...]:
        payload = []
        for signal in self.module.signals:
            if signal.kind == "state":
                payload.append(self._state[signal.name] & signal.mask)
        for memory in self.module.memories:
            payload.extend(value & memory.mask for value in self._memories[memory.name])
        return tuple(payload)

    def restore_state_numpy(self, state: np.ndarray) -> None:
        if state.dtype != np.uint64:
            raise TypeError("state must have dtype=uint64")
        if state.ndim != 1:
            raise TypeError("state must be a 1D numpy array")
        if len(state) != self.state_word_count:
            raise ValueError(f"expected state length {self.state_word_count}, got {len(state)}")
        values = unpack_signal_values_u64_words(state, self.state_widths)
        self.restore_state_values(values)

    def restore_state_values(self, state: Sequence[int]) -> None:
        if len(state) != self.state_count:
            raise ValueError(f"expected state length {self.state_count}, got {len(state)}")
        cursor = 0
        for signal in self.module.signals:
            if signal.kind == "state":
                self._state[signal.name] = int(state[cursor]) & signal.mask
                cursor += 1
        for memory in self.module.memories:
            for idx in range(memory.depth):
                self._memories[memory.name][idx] = int(state[cursor]) & memory.mask
                cursor += 1
