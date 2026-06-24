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
    read_during_write: str = "write_first"
    read_ports: int = 1
    write_ports: int = 1
    read_style: str = "async"
    read_latency: int = 0
    byte_enable_granularity: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("memory name must not be empty")
        if self.width < 1:
            raise ValueError("memory width must be positive")
        if self.depth < 1:
            raise ValueError("memory depth must be positive")
        if self.init and len(self.init) != self.depth:
            raise ValueError("memory init must be empty or match depth")
        if self.read_during_write not in {"write_first", "read_first"}:
            raise ValueError(
                "memory read_during_write must be 'write_first' or 'read_first'"
            )
        if self.read_ports < 1:
            raise ValueError("memory read_ports must be >= 1")
        if self.write_ports < 1:
            raise ValueError("memory write_ports must be >= 1")
        if self.read_style not in {"async", "sync"}:
            raise ValueError("memory read_style must be 'async' or 'sync'")
        if self.read_latency < 0:
            raise ValueError("memory read_latency must be >= 0")
        if self.byte_enable_granularity is not None:
            if self.byte_enable_granularity < 1:
                raise ValueError("memory byte_enable_granularity must be >= 1")
            if self.width % self.byte_enable_granularity != 0:
                raise ValueError(
                    "memory width must be divisible by byte_enable_granularity"
                )

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    @property
    def byte_enable_width(self) -> Optional[int]:
        if self.byte_enable_granularity is None:
            return None
        return self.width // self.byte_enable_granularity


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
    clock_domain: Optional[str] = None

    def __post_init__(self) -> None:
        if self.phase not in {"comb", "latch", "seq"}:
            raise ValueError("assignment phase must be 'comb', 'latch', or 'seq'")


@dataclass(frozen=True)
class MemoryWrite:
    memory: str
    addr: Expr
    value: Expr
    enable: Expr = ConstExpr(1, 1)
    clock_domain: Optional[str] = None
    byte_enable: Optional[Expr] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class ClockDomain:
    name: str
    reset_signal: Optional[str] = None
    reset_async: bool = False
    reset_active_low: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("clock domain name must not be empty")


@dataclass(frozen=True)
class SimModule:
    name: str
    signals: Tuple[Signal, ...]
    assignments: Tuple[Assignment, ...]
    outputs: Tuple[str, ...]
    memories: Tuple[Memory, ...] = ()
    memory_writes: Tuple[MemoryWrite, ...] = ()
    clock_domains: Tuple[ClockDomain, ...] = ()
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
            _validate_executable_memory_contract(memory)
            memory_map[memory.name] = memory
        if not self.outputs:
            raise ValueError("module must expose at least one output")
        for output_name in self.outputs:
            signal = signal_map.get(output_name)
            if signal is None:
                raise ValueError(f"unknown output '{output_name}'")
            if signal.kind != "output":
                raise ValueError(f"output '{output_name}' must have kind='output'")
        domain_map: Dict[str, ClockDomain] = {}
        for domain in self.clock_domains:
            if domain.name in domain_map:
                raise ValueError(f"duplicate clock domain '{domain.name}'")
            clock_signal = signal_map.get(domain.name)
            if clock_signal is None:
                raise ValueError(f"unknown clock domain signal '{domain.name}'")
            if clock_signal.kind != "input":
                raise ValueError("clock domain signal must be declared as an input")
            if domain.reset_signal is not None:
                reset_signal = signal_map.get(domain.reset_signal)
                if reset_signal is None:
                    raise ValueError(
                        f"unknown reset signal '{domain.reset_signal}' for clock domain '{domain.name}'"
                    )
                if reset_signal.kind != "input":
                    raise ValueError("clock domain reset signal must be declared as an input")
            domain_map[domain.name] = domain
        if self.reset_signal is not None:
            reset_signal = signal_map.get(self.reset_signal)
            if reset_signal is None:
                raise ValueError(f"unknown reset signal '{self.reset_signal}'")
            if reset_signal.kind != "input":
                raise ValueError("reset signal must be declared as an input")
        if len(self.clock_domains) > 1 and self.reset_signal is not None:
            raise ValueError("multi-clock modules must use per-domain reset signals, not module.reset_signal")
        if len(self.clock_domains) == 1 and self.reset_signal is not None:
            domain_reset = self.clock_domains[0].reset_signal
            if domain_reset is not None and domain_reset != self.reset_signal:
                raise ValueError("single clock-domain reset disagrees with module.reset_signal")

        def resolve_domain_name(explicit_name: Optional[str], *, kind: str) -> Optional[str]:
            if not domain_map:
                return explicit_name
            if explicit_name is None:
                if len(domain_map) == 1:
                    return next(iter(domain_map))
                raise ValueError(f"{kind} in a multi-clock module must declare clock_domain")
            if explicit_name not in domain_map:
                raise ValueError(f"{kind} references unknown clock domain '{explicit_name}'")
            return explicit_name

        state_domains: Dict[str, str] = {}
        memory_domains: Dict[str, str] = {}
        for assignment in self.assignments:
            target = signal_map.get(assignment.target)
            if target is None:
                raise ValueError(f"assignment targets unknown signal '{assignment.target}'")
            if assignment.phase != "seq" and assignment.clock_domain is not None:
                raise ValueError("clock_domain metadata is only valid on sequential assignments")
            if assignment.phase == "seq" and target.kind != "state":
                raise ValueError("sequential assignments may only target state signals")
            if assignment.phase == "comb" and target.kind == "state":
                raise ValueError("combinational assignments may not target state signals")
            if assignment.phase == "latch" and target.kind != "state":
                raise ValueError("latch assignments may only target state signals")
            if assignment.phase == "seq":
                domain_name = resolve_domain_name(assignment.clock_domain, kind="sequential assignment")
                if domain_name is not None:
                    previous = state_domains.get(assignment.target)
                    if previous is not None and previous != domain_name:
                        raise ValueError(
                            f"state '{assignment.target}' is written from multiple clock domains: "
                            f"'{previous}' and '{domain_name}'"
                        )
                    state_domains[assignment.target] = domain_name
            self._validate_expr(assignment.expr, signal_map, memory_map)
        for write in self.memory_writes:
            memory = memory_map.get(write.memory)
            if memory is None:
                raise ValueError(f"memory write targets unknown memory '{write.memory}'")
            if write.byte_enable is not None and memory.byte_enable_granularity is None:
                raise ValueError(
                    f"memory write targets '{write.memory}' with byte_enable, but the memory "
                    "does not declare byte_enable_granularity"
                )
            if write.byte_enable is None and memory.byte_enable_granularity is not None:
                raise ValueError(
                    f"memory write targets '{write.memory}' without byte_enable, but the memory "
                    "declares byte_enable_granularity"
                )
            domain_name = resolve_domain_name(write.clock_domain, kind="memory write")
            if domain_name is not None:
                previous = memory_domains.get(write.memory)
                if previous is not None and previous != domain_name:
                    raise ValueError(
                        f"memory '{write.memory}' is written from multiple clock domains: "
                        f"'{previous}' and '{domain_name}'"
                    )
                memory_domains[write.memory] = domain_name
            self._validate_expr(write.addr, signal_map, memory_map)
            self._validate_expr(write.value, signal_map, memory_map)
            self._validate_expr(write.enable, signal_map, memory_map)
            if write.byte_enable is not None:
                self._validate_expr(write.byte_enable, signal_map, memory_map)

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
        self._memory_read_policies = {
            memory.name: memory.read_during_write
            for memory in self.module.memories
        }
        self.input_names = tuple(
            signal.name for signal in self.module.signals if signal.kind == "input"
        )
        self.output_names = tuple(self.module.outputs)
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
        self._clock_domains = {
            domain.name: domain
            for domain in self.module.clock_domains
        }
        self.clock_domain_names = tuple(self._clock_domains.keys())
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
            return explicit_name
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
        ordered = tuple(dict.fromkeys(selected))
        unknown = sorted(set(ordered) - set(self.clock_domain_names))
        if unknown:
            raise KeyError(f"unknown clock domains: {', '.join(unknown)}")
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
            raise KeyError(f"unknown simulator inputs: {', '.join(unknown_inputs)}")
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
            raise KeyError(f"unknown simulator inputs: {', '.join(unknown_inputs)}")
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
                    pending_writes.extend(
                        self._compute_memory_writes(values, domain_writes)
                    )
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
                pending_writes = self._compute_memory_writes(values)
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
            for memory_name, addr, value in pending_writes:
                self._memories[memory_name][addr] = value
        if self.module.outputs_post_state:
            for name in self._wire_and_output_names:
                values[name] = 0
            for assignment in self._comb_assignments:
                signal = self._signal_map[assignment.target]
                values[assignment.target] = (
                    self._eval_expr(assignment.expr, values, memory_overrides=read_first_overrides)
                    & signal.mask
                )
        return tuple(
            values[name] & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        )

    def run_batch(self, input_rows: Sequence[Sequence[int]]) -> Tuple[Dict[str, int], ...]:
        if self._multi_clock:
            raise ValueError("run_batch() is only supported for single-clock modules")
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
            branch = (
                expr.when_true
                if self._eval_expr(expr.cond, values, memory_overrides=memory_overrides)
                else expr.when_false
            )
            return self._eval_expr(branch, values, memory_overrides=memory_overrides)
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _compute_memory_writes(
        self,
        values: Mapping[str, int],
        writes_subset: Optional[Sequence[MemoryWrite]] = None,
    ) -> Tuple[Tuple[str, int, int], ...]:
        writes = []
        for write in self.module.memory_writes if writes_subset is None else writes_subset:
            memory = self._memory_map[write.memory]
            if not self._eval_expr(write.enable, values):
                continue
            addr = self._eval_expr(write.addr, values) % memory.depth
            value = self._eval_expr(write.value, values) & memory.mask
            writes.append((write.memory, addr, value))
        return tuple(writes)

    def _capture_read_first_memory_overrides(
        self,
        pending_writes: Sequence[Tuple[str, int, int]],
    ) -> Dict[Tuple[str, int], int]:
        overrides: Dict[Tuple[str, int], int] = {}
        for memory_name, addr, _value in pending_writes:
            if self._memory_read_policies.get(memory_name) != "read_first":
                continue
            overrides[(memory_name, addr)] = self._memories[memory_name][addr]
        return overrides

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


def _validate_executable_memory_contract(memory: Memory) -> None:
    problems = []
    if memory.read_ports != 1:
        problems.append(f"read_ports={memory.read_ports}")
    if memory.write_ports != 1:
        problems.append(f"write_ports={memory.write_ports}")
    if memory.read_style != "async":
        problems.append(f"read_style={memory.read_style!r}")
    if memory.read_latency != 0:
        problems.append(f"read_latency={memory.read_latency}")
    if memory.byte_enable_granularity is not None:
        problems.append(
            f"byte_enable_granularity={memory.byte_enable_granularity}"
        )
    if not problems:
        return
    details = ", ".join(problems)
    raise ValueError(
        f"memory '{memory.name}' is outside the executable storage subset ({details}); "
        "supported executable memories currently require read_ports=1, "
        "write_ports=1, read_style='async', read_latency=0, and no byte-enable lanes"
    )
