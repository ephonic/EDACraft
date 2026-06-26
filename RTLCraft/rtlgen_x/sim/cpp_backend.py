"""Local model and compiled C++ runtime support for the simulator capability."""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import tempfile
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np


@dataclass(frozen=True)
class Signal:
    """One signal in the compiled-simulator local model."""

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
    """One comb-read / seq-write storage object in the executable model."""

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
    def addr_width(self) -> int:
        return max((self.depth - 1).bit_length(), 1)

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
    source_file: Optional[str] = None
    source_line: Optional[int] = None

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
    clock_signal: Optional[str] = None
    reset_signal: Optional[str] = None
    reset_async: bool = False
    reset_active_low: bool = False
    aliases: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("clock domain name must not be empty")


@dataclass(frozen=True)
class SimModule:
    """Local executable module description for the compiled simulator."""

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
        if len(self.clock_domains) > 64:
            raise ValueError("clock domain count must be <= 64")
        domain_map: Dict[str, ClockDomain] = {}
        for domain in self.clock_domains:
            if domain.name in domain_map:
                raise ValueError(f"duplicate clock domain '{domain.name}'")
            clock_signal_name = domain.clock_signal or domain.name
            clock_signal = signal_map.get(clock_signal_name)
            if clock_signal is None:
                raise ValueError(
                    f"unknown clock domain signal '{clock_signal_name}' for clock domain '{domain.name}'"
                )
            if clock_signal.kind != "input":
                raise ValueError("clock domain signal must be declared as an input")
            if domain.reset_signal is not None:
                reset_signal = signal_map.get(domain.reset_signal)
                if reset_signal is None:
                    raise ValueError(f"unknown reset signal '{domain.reset_signal}' for clock domain '{domain.name}'")
            domain_map[domain.name] = domain
        if self.reset_signal is not None:
            signal = signal_map.get(self.reset_signal)
            if signal is None:
                raise ValueError(f"unknown reset signal '{self.reset_signal}'")
            if signal.kind != "input":
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


def _cpp_ident(name: str) -> str:
    chars = [c if c.isalnum() or c == "_" else "_" for c in name]
    ident = "".join(chars)
    if ident and (ident[0].isalpha() or ident[0] == "_"):
        return ident
    return f"sig_{ident}"


def _validate_executable_memory_contract(memory: Memory) -> None:
    problems: List[str] = []
    if memory.read_ports != 1:
        problems.append(f"read_ports={memory.read_ports}")
    if memory.write_ports != 1:
        problems.append(f"write_ports={memory.write_ports}")
    if memory.read_style != "async":
        problems.append(f"read_style={memory.read_style!r}")
    if memory.read_latency != 0:
        problems.append(f"read_latency={memory.read_latency}")
    if not problems:
        return
    details = ", ".join(problems)
    raise ValueError(
        f"memory '{memory.name}' is outside the executable storage subset ({details}); "
        "supported executable memories currently require read_ports=1, "
        "write_ports=1, and read_style='async', read_latency=0"
    )


def _cpp_value_name(name: str) -> str:
    return f"value_{_cpp_ident(name)}"


def _mask(width: int) -> int:
    return (1 << width) - 1


def _mask_expr(width: int) -> str:
    if width == 64:
        return "UINT64_MAX"
    return f"((uint64_t(1) << {width}) - 1u)"


def _expr_references_signal(expr: Expr, signal_name: Optional[str]) -> bool:
    if not signal_name:
        return False
    if isinstance(expr, ConstExpr):
        return False
    if isinstance(expr, SignalRef):
        return expr.name == signal_name
    if isinstance(expr, MemoryReadExpr):
        return _expr_references_signal(expr.addr, signal_name)
    if isinstance(expr, MaskExpr):
        return _expr_references_signal(expr.value, signal_name)
    if isinstance(expr, UnaryExpr):
        return _expr_references_signal(expr.value, signal_name)
    if isinstance(expr, BinaryExpr):
        return _expr_references_signal(expr.lhs, signal_name) or _expr_references_signal(expr.rhs, signal_name)
    if isinstance(expr, MuxExpr):
        return (
            _expr_references_signal(expr.cond, signal_name)
            or _expr_references_signal(expr.when_true, signal_name)
            or _expr_references_signal(expr.when_false, signal_name)
        )
    return False


def _sign_extend_expr(expr: str, width: int) -> str:
    if width == 64:
        return f"int64_t(uint64_t({expr}))"
    sign_bit = f"(uint64_t(1) << {width - 1})"
    masked = f"(uint64_t({expr}) & {_mask_expr(width)})"
    return f"int64_t(({masked} ^ {sign_bit}) - {sign_bit})"


def _masked_scalar_expr(expr: str, width: int) -> str:
    return f"(uint64_t({expr}) & {_mask_expr(width)})"


def _scalar_numeric_operand_expr(
    expr: str,
    width: int,
    *,
    signed: bool,
    signed_context: bool,
) -> str:
    masked = _masked_scalar_expr(expr, width)
    if signed_context:
        if signed:
            return f"static_cast<__int128>({_sign_extend_expr(masked, width)})"
        return f"static_cast<__int128>({masked})"
    return f"static_cast<unsigned __int128>({masked})"


def _word_count(width: int) -> int:
    return max((width + 63) // 64, 1)


def _word_slices(widths: Sequence[int]) -> Tuple[Tuple[int, int], ...]:
    slices = []
    cursor = 0
    for width in widths:
        words = _word_count(width)
        slices.append((cursor, words))
        cursor += words
    return tuple(slices)


def pack_signal_values_u64_words(values: Sequence[int], widths: Sequence[int]) -> array:
    """Pack logical signal values into little-endian uint64 words."""

    if len(values) != len(widths):
        raise ValueError(f"expected {len(widths)} values, got {len(values)}")
    packed = array("Q")
    for value, width in zip(values, widths):
        masked = int(value) & _mask(width)
        for word_idx in range(_word_count(width)):
            packed.append((masked >> (64 * word_idx)) & 0xFFFFFFFFFFFFFFFF)
    return packed


def unpack_signal_values_u64_words(words: Sequence[int], widths: Sequence[int]) -> Tuple[int, ...]:
    """Unpack little-endian uint64 words into logical Python integers."""

    expected_words = sum(_word_count(width) for width in widths)
    if len(words) != expected_words:
        raise ValueError(f"expected {expected_words} packed words, got {len(words)}")
    values = []
    cursor = 0
    for width in widths:
        value = 0
        for word_idx in range(_word_count(width)):
            value |= (int(words[cursor + word_idx]) & 0xFFFFFFFFFFFFFFFF) << (64 * word_idx)
        values.append(value & _mask(width))
        cursor += _word_count(width)
    return tuple(values)


def _infer_expr_width(
    expr: Expr,
    signal_map: Dict[str, Signal],
    memory_map: Dict[str, Memory],
) -> int:
    if isinstance(expr, ConstExpr):
        return expr.width
    if isinstance(expr, SignalRef):
        signal = signal_map[expr.name]
        return signal.width
    if isinstance(expr, MemoryReadExpr):
        return memory_map[expr.memory].width
    if isinstance(expr, MaskExpr):
        return expr.width
    if isinstance(expr, UnaryExpr):
        return _infer_expr_width(expr.value, signal_map, memory_map)
    if isinstance(expr, BinaryExpr):
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            return 1
        if expr.op in {"+", "-"}:
            return max(
                _infer_expr_width(expr.lhs, signal_map, memory_map),
                _infer_expr_width(expr.rhs, signal_map, memory_map),
            ) + 1
        if expr.op == "*":
            return _infer_expr_width(expr.lhs, signal_map, memory_map) + _infer_expr_width(
                expr.rhs, signal_map, memory_map
            )
        return max(
            _infer_expr_width(expr.lhs, signal_map, memory_map),
            _infer_expr_width(expr.rhs, signal_map, memory_map),
        )
    if isinstance(expr, MuxExpr):
        return max(
            _infer_expr_width(expr.when_true, signal_map, memory_map),
            _infer_expr_width(expr.when_false, signal_map, memory_map),
        )
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _expr_is_signed(
    expr: Expr,
    signal_map: Dict[str, Signal],
    memory_map: Dict[str, Memory],
) -> bool:
    if isinstance(expr, ConstExpr):
        return False
    if isinstance(expr, SignalRef):
        return signal_map[expr.name].signed
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
        return _expr_is_signed(expr.value, signal_map, memory_map)
    if isinstance(expr, BinaryExpr):
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            return False
        return _expr_is_signed(expr.lhs, signal_map, memory_map) or _expr_is_signed(
            expr.rhs, signal_map, memory_map
        )
    if isinstance(expr, MuxExpr):
        return _expr_is_signed(expr.when_true, signal_map, memory_map) and _expr_is_signed(
            expr.when_false, signal_map, memory_map
        )
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def pack_u64_words(values: Sequence[int]) -> array:
    """Pack arbitrary Python integers into an unsigned 64-bit array."""

    packed = array("Q")
    packed.extend(int(value) & 0xFFFFFFFFFFFFFFFF for value in values)
    return packed


def pack_u64_numpy(values: Sequence[int]) -> np.ndarray:
    """Pack values into a contiguous uint64 numpy array."""

    packed = np.asarray(values, dtype=np.uint64)
    if not packed.flags.c_contiguous:
        packed = np.ascontiguousarray(packed)
    return packed.reshape(-1)


def pack_u64_numpy_rows(rows: Sequence[Sequence[int]]) -> np.ndarray:
    """Pack row-major values into a 2D contiguous uint64 numpy array."""

    packed = np.asarray(rows, dtype=np.uint64)
    if packed.ndim != 2:
        raise ValueError("rows must form a 2D array")
    if not packed.flags.c_contiguous:
        packed = np.ascontiguousarray(packed)
    return packed


class CppBuildError(RuntimeError):
    """Raised when the local compiled simulator cannot be built or loaded."""


class CompiledSimulator:
    """Python-facing handle to a compiled simulator instance."""

    def __init__(
        self,
        *,
        library: ctypes.CDLL,
        handle: int,
        destroy_fn,
        reset_fn,
        step_fn,
        step_many_fn,
        save_state_fn,
        load_state_fn,
        input_names: Sequence[str],
        input_widths: Sequence[int],
        output_names: Sequence[str],
        output_widths: Sequence[int],
        state_names: Sequence[str],
        state_widths: Sequence[int],
        step_domains_fn=None,
        clock_domain_names: Sequence[str] = (),
        clock_domain_aliases: Optional[Mapping[str, Sequence[str]]] = None,
        artifact_dir: Path,
        source_path: Path,
        library_path: Path,
        tempdir: Optional[tempfile.TemporaryDirectory] = None,
    ) -> None:
        self._library = library
        self._handle = handle
        self._destroy_fn = destroy_fn
        self._reset_fn = reset_fn
        self._step_fn = step_fn
        self._step_many_fn = step_many_fn
        self._save_state_fn = save_state_fn
        self._load_state_fn = load_state_fn
        self._step_domains_fn = step_domains_fn
        self.input_names = tuple(input_names)
        self.output_names = tuple(output_names)
        self.state_names = tuple(state_names)
        self.clock_domain_names = tuple(clock_domain_names)
        self.clock_domain_aliases = {
            str(name): tuple(str(alias) for alias in values)
            for name, values in (clock_domain_aliases or {}).items()
        }
        self.input_widths = tuple(input_widths)
        self.output_widths = tuple(output_widths)
        self.state_widths = tuple(state_widths)
        self.input_count = len(self.input_names)
        self.output_count = len(self.output_names)
        self.state_count = len(self.state_names)
        self.input_word_slices = _word_slices(self.input_widths)
        self.output_word_slices = _word_slices(self.output_widths)
        self.state_word_slices = _word_slices(self.state_widths)
        self.input_word_count = sum(words for _, words in self.input_word_slices)
        self.output_word_count = sum(words for _, words in self.output_word_slices)
        self.state_word_count = sum(words for _, words in self.state_word_slices)
        self._input_masks = tuple(_mask(width) for width in self.input_widths)
        self._output_masks = tuple(_mask(width) for width in self.output_widths)
        self._state_masks = tuple(_mask(width) for width in self.state_widths)
        self._step_input_buffer = (ctypes.c_uint64 * self.input_word_count)()
        self._step_output_buffer = (ctypes.c_uint64 * self.output_word_count)()
        self._state_buffer = np.zeros(self.state_word_count, dtype=np.uint64)
        self.artifact_dir = artifact_dir
        self.source_path = source_path
        self.library_path = library_path
        self._tempdir = tempdir
        self._input_index = {name: idx for idx, name in enumerate(self.input_names)}
        self._clock_domain_index = {
            name: idx for idx, name in enumerate(self.clock_domain_names)
        }
        self._clock_domain_name_by_alias = {}
        for name in self.clock_domain_names:
            self._clock_domain_name_by_alias[name] = name
        for canonical, values in self.clock_domain_aliases.items():
            self._clock_domain_name_by_alias[canonical] = canonical
            for alias in values:
                self._clock_domain_name_by_alias.setdefault(alias, canonical)
        self._multi_clock = len(self.clock_domain_names) > 1

    def close(self) -> None:
        if self._handle is not None:
            self._destroy_fn(self._handle)
            self._handle = None
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None

    def reset(self) -> None:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        self._reset_fn(self._handle)

    def step(self, inputs: Mapping[str, int]) -> Dict[str, int]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if self._multi_clock:
            raise ValueError("multi-clock modules must use step_clocks(...) with explicit active domains")
        unknown_inputs = sorted(set(inputs) - set(self.input_names))
        if unknown_inputs:
            joined = ", ".join(unknown_inputs)
            raise KeyError(f"unknown simulator inputs: {joined}")
        output_values = self.step_raw([int(inputs.get(name, 0)) for name in self.input_names])
        return {
            name: int(output_values[idx]) & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        }

    def step_raw(self, input_values: Sequence[int]) -> Tuple[int, ...]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if self._multi_clock:
            raise ValueError("multi-clock modules must use step_raw_clocks(...) with explicit active domains")
        if len(input_values) != self.input_count:
            raise ValueError(f"expected {self.input_count} input values, got {len(input_values)}")
        packed_inputs = pack_signal_values_u64_words(input_values, self.input_widths)
        for idx, raw_word in enumerate(packed_inputs):
            self._step_input_buffer[idx] = int(raw_word) & 0xFFFFFFFFFFFFFFFF
        self._step_fn(self._handle, self._step_input_buffer, self._step_output_buffer)
        return unpack_signal_values_u64_words(self._step_output_buffer, self.output_widths)

    def _normalize_active_domains(
        self,
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Tuple[str, ...]:
        if not self.clock_domain_names:
            raise ValueError("step_clocks() requires clock-domain metadata")
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

    def _active_domain_mask(
        self,
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> int:
        ordered = self._normalize_active_domains(active_domains)
        mask = 0
        for name in ordered:
            mask |= 1 << self._clock_domain_index[name]
        return mask

    def step_clocks(
        self,
        inputs: Mapping[str, int],
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Dict[str, int]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        unknown_inputs = sorted(set(inputs) - set(self.input_names))
        if unknown_inputs:
            joined = ", ".join(unknown_inputs)
            raise KeyError(f"unknown simulator inputs: {joined}")
        output_values = self.step_raw_clocks(
            [int(inputs.get(name, 0)) for name in self.input_names],
            active_domains,
        )
        return {
            name: int(output_values[idx]) & self._output_masks[idx]
            for idx, name in enumerate(self.output_names)
        }

    def step_raw_clocks(
        self,
        input_values: Sequence[int],
        active_domains: Mapping[str, bool] | Sequence[str],
    ) -> Tuple[int, ...]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if self._step_domains_fn is None:
            raise ValueError("step_raw_clocks() requires clock-domain metadata")
        if len(input_values) != self.input_count:
            raise ValueError(f"expected {self.input_count} input values, got {len(input_values)}")
        active_mask = self._active_domain_mask(active_domains)
        packed_inputs = pack_signal_values_u64_words(input_values, self.input_widths)
        for idx, raw_word in enumerate(packed_inputs):
            self._step_input_buffer[idx] = int(raw_word) & 0xFFFFFFFFFFFFFFFF
        self._step_domains_fn(
            self._handle,
            ctypes.c_uint64(active_mask),
            self._step_input_buffer,
            self._step_output_buffer,
        )
        return unpack_signal_values_u64_words(self._step_output_buffer, self.output_widths)

    def run_batch_raw(self, flat_inputs: Sequence[int], cycles: int) -> Tuple[int, ...]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
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
        flat_inputs: Union[array, np.ndarray],
        cycles: int,
        output_buffer: Optional[Union[array, np.ndarray]] = None,
    ) -> Union[array, np.ndarray]:
        """Run a packed batch using reusable unsigned-64 buffers."""

        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if self._multi_clock:
            raise ValueError("run_batch_buffered() is only supported for single-clock modules")
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_word_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        total_outputs = cycles * self.output_word_count
        input_view = self._u64_input_view(flat_inputs, expected_values)
        output_buffer = self._prepare_output_buffer(output_buffer, total_outputs)
        if cycles == 0:
            return output_buffer
        output_view = self._u64_output_view(output_buffer, total_outputs)
        self._step_many_fn(
            self._handle,
            ctypes.c_uint64(cycles),
            input_view,
            output_view,
        )
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
        flat_inputs: List[int] = []
        for row in input_rows:
            if len(row) != self.input_count:
                raise ValueError(f"expected {self.input_count} input values, got {len(row)}")
            flat_inputs.extend(int(value) for value in row)
        raw_outputs = self.run_batch_raw(flat_inputs, len(input_rows))
        outputs = []
        for cycle in range(len(input_rows)):
            start = cycle * self.output_count
            outputs.append(
                {
                    name: raw_outputs[start + idx] & self._output_masks[idx]
                    for idx, name in enumerate(self.output_names)
                }
            )
        return tuple(outputs)

    def run_batch_matrix(
        self,
        input_rows: np.ndarray,
        output_buffer: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Run a 2D uint64 input matrix and return a 2D uint64 output matrix."""

        if self._multi_clock:
            raise ValueError("run_batch_matrix() is only supported for single-clock modules")
        if input_rows.dtype != np.uint64:
            raise TypeError("input_rows must have dtype=uint64")
        if input_rows.ndim != 2:
            raise TypeError("input_rows must be a 2D numpy array")
        if input_rows.shape[1] != self.input_word_count:
            raise ValueError(
                f"expected input_rows.shape[1] == {self.input_word_count}, got {input_rows.shape[1]}"
            )
        if not input_rows.flags.c_contiguous:
            raise TypeError("input_rows must be C-contiguous")
        cycles = int(input_rows.shape[0])
        if output_buffer is None:
            output_buffer = np.zeros((cycles, self.output_word_count), dtype=np.uint64)
        else:
            if output_buffer.dtype != np.uint64:
                raise TypeError("output_buffer must have dtype=uint64")
            if output_buffer.ndim != 2:
                raise TypeError("output_buffer must be a 2D numpy array")
            if output_buffer.shape != (cycles, self.output_word_count):
                raise ValueError(
                    f"expected output_buffer.shape == {(cycles, self.output_word_count)}, got {output_buffer.shape}"
                )
            if not output_buffer.flags.c_contiguous:
                raise TypeError("output_buffer must be C-contiguous")
        self.run_batch_buffered(input_rows.reshape(-1), cycles, output_buffer.reshape(-1))
        return output_buffer

    def _u64_input_view(self, flat_inputs: Union[array, np.ndarray], expected_values: int):
        if isinstance(flat_inputs, array):
            if flat_inputs.typecode != "Q":
                raise TypeError("flat_inputs must be array('Q') or numpy.uint64 ndarray")
            return (ctypes.c_uint64 * expected_values).from_buffer(flat_inputs)
        if isinstance(flat_inputs, np.ndarray):
            if flat_inputs.dtype != np.uint64:
                raise TypeError("flat_inputs numpy array must have dtype=uint64")
            if flat_inputs.ndim != 1:
                raise TypeError("flat_inputs numpy array must be one-dimensional")
            if not flat_inputs.flags.c_contiguous:
                raise TypeError("flat_inputs numpy array must be C-contiguous")
            return flat_inputs.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64))
        raise TypeError("flat_inputs must be array('Q') or numpy.uint64 ndarray")

    def _prepare_output_buffer(
        self,
        output_buffer: Optional[Union[array, np.ndarray]],
        total_outputs: int,
    ) -> Union[array, np.ndarray]:
        if output_buffer is None:
            return np.zeros(total_outputs, dtype=np.uint64)
        if isinstance(output_buffer, array):
            if output_buffer.typecode != "Q":
                raise TypeError("output_buffer must be array('Q') or numpy.uint64 ndarray")
            if len(output_buffer) != total_outputs:
                raise ValueError(
                    f"expected output_buffer length {total_outputs}, got {len(output_buffer)}"
                )
            return output_buffer
        if isinstance(output_buffer, np.ndarray):
            if output_buffer.dtype != np.uint64:
                raise TypeError("output_buffer numpy array must have dtype=uint64")
            if output_buffer.ndim != 1:
                raise TypeError("output_buffer numpy array must be one-dimensional")
            if not output_buffer.flags.c_contiguous:
                raise TypeError("output_buffer numpy array must be C-contiguous")
            if len(output_buffer) != total_outputs:
                raise ValueError(
                    f"expected output_buffer length {total_outputs}, got {len(output_buffer)}"
                )
            return output_buffer
        raise TypeError("output_buffer must be array('Q') or numpy.uint64 ndarray")

    def _u64_output_view(self, output_buffer: Union[array, np.ndarray], total_outputs: int):
        if isinstance(output_buffer, array):
            return (ctypes.c_uint64 * total_outputs).from_buffer(output_buffer)
        return output_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64))

    def snapshot_state_numpy(self) -> np.ndarray:
        """Return a contiguous uint64 snapshot of the current simulator state."""

        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if self.state_count == 0:
            return np.zeros(0, dtype=np.uint64)
        self._save_state_fn(
            self._handle,
            self._state_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)),
        )
        return self._state_buffer.copy()

    def snapshot_state_values(self) -> Tuple[int, ...]:
        return unpack_signal_values_u64_words(self.snapshot_state_numpy(), self.state_widths)

    def restore_state_numpy(self, state: np.ndarray) -> None:
        """Restore the simulator state from a uint64 numpy snapshot."""

        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if state.dtype != np.uint64:
            raise TypeError("state must have dtype=uint64")
        if state.ndim != 1:
            raise TypeError("state must be a 1D numpy array")
        if len(state) != self.state_word_count:
            raise ValueError(f"expected state length {self.state_word_count}, got {len(state)}")
        if not state.flags.c_contiguous:
            state = np.ascontiguousarray(state)
        self._load_state_fn(
            self._handle,
            state.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)),
        )

    def restore_state_values(self, state: Sequence[int]) -> None:
        packed = np.asarray(pack_signal_values_u64_words(state, self.state_widths), dtype=np.uint64)
        self.restore_state_numpy(packed)

    def __enter__(self) -> "CompiledSimulator":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


@dataclass(frozen=True)
class CppBackendScaffold:
    """Emit C++ source and build a minimal compiled simulator runtime."""

    namespace: str = "rtlgen_x"
    compiler: Optional[str] = None
    cxxflags: Tuple[str, ...] = ("-std=c++17", "-O2")

    def _ensure_supported_clock_domains(self, module: SimModule) -> None:
        return None

    def _group_seq_assignments_by_domain(
        self,
        module: SimModule,
    ) -> Dict[str, List[Assignment]]:
        grouped = {domain.name: [] for domain in module.clock_domains}
        if not module.clock_domains:
            return grouped
        default_domain = module.clock_domains[0].name if len(module.clock_domains) == 1 else None
        for assignment in module.assignments:
            if assignment.phase != "seq":
                continue
            domain_name = assignment.clock_domain or default_domain
            if domain_name is None:
                raise ValueError("multi-clock sequential assignment is missing clock_domain")
            grouped[domain_name].append(assignment)
        return grouped

    def _group_memory_writes_by_domain(
        self,
        module: SimModule,
    ) -> Dict[str, List[MemoryWrite]]:
        grouped = {domain.name: [] for domain in module.clock_domains}
        if not module.clock_domains:
            return grouped
        default_domain = module.clock_domains[0].name if len(module.clock_domains) == 1 else None
        for write in module.memory_writes:
            domain_name = write.clock_domain or default_domain
            if domain_name is None:
                raise ValueError("multi-clock memory write is missing clock_domain")
            grouped[domain_name].append(write)
        return grouped

    def emit_translation_unit(self, module: SimModule) -> str:
        self._ensure_supported_clock_domains(module)
        if self._requires_wide_support(module):
            return self._emit_wide_translation_unit(module)
        signal_map = module.signal_map()
        memory_map = module.memory_map()
        module_ident = _cpp_ident(module.name)
        wire_output_signals = [
            signal for signal in module.signals if signal.kind in {"wire", "output"}
        ]
        comb_assignments = [a for a in module.assignments if a.phase == "comb"]
        latch_assignments = [a for a in module.assignments if a.phase == "latch"]
        seq_assignments = [a for a in module.assignments if a.phase == "seq"]
        memory_writes = list(module.memory_writes)
        domain_names = [domain.name for domain in module.clock_domains]
        seq_by_domain = self._group_seq_assignments_by_domain(module)
        writes_by_domain = self._group_memory_writes_by_domain(module)
        domain_names = [domain.name for domain in module.clock_domains]
        seq_by_domain = self._group_seq_assignments_by_domain(module)
        writes_by_domain = self._group_memory_writes_by_domain(module)

        def emit_comb(indent: str, *, declare: bool, state_expr: str = "state_") -> List[str]:
            block_lines: List[str] = []
            for signal in wire_output_signals:
                lhs = _cpp_value_name(signal.name)
                prefix = "uint64_t " if declare else ""
                block_lines.append(f"{indent}{prefix}{lhs} = 0u;")
            if wire_output_signals and comb_assignments:
                block_lines.append("")
            for assignment in comb_assignments:
                target = signal_map[assignment.target]
                block_lines.append(
                    f"{indent}{_cpp_value_name(assignment.target)} = "
                    f"({self._emit_expr(assignment.expr, signal_map, memory_map, state_expr=state_expr)}) & {_mask_expr(target.width)};"
                )
            return block_lines

        lines: List[str] = [
            "#include <cstdint>",
            "#include <limits>",
            "",
            f"namespace {self.namespace} {{",
            "",
            f"struct {module_ident}State {{",
        ]
        for signal in module.signals:
            if signal.kind == "state":
                lines.append(f"  uint64_t {_cpp_ident(signal.name)} = {signal.init & signal.mask}u;")
        for memory in module.memories:
            lines.append(f"  uint64_t {_cpp_ident(memory.name)}[{memory.depth}] = {{}};")
        lines.extend([
            "};",
            "",
            f"struct {module_ident}Inputs {{",
        ])
        for signal in module.signals:
            if signal.kind == "input":
                lines.append(f"  uint64_t {_cpp_ident(signal.name)} = 0u;")
        lines.extend([
            "};",
            "",
            f"struct {module_ident}Outputs {{",
        ])
        for output_name in module.outputs:
            lines.append(f"  uint64_t {_cpp_ident(output_name)} = 0u;")
        lines.extend([
            "};",
            "",
            f"class {module_ident}Simulator {{",
            " public:",
        ])
        if domain_names:
            for index, domain in enumerate(module.clock_domains):
                lines.append(f"  static constexpr uint64_t kDomainMask_{_cpp_ident(domain.name)} = 1ull << {index}u;")
            all_domains_mask = " | ".join(
                f"kDomainMask_{_cpp_ident(domain.name)}" for domain in module.clock_domains
            )
            lines.extend([
                f"  static constexpr uint64_t kAllClockDomainsMask = {all_domains_mask};",
                "",
            ])
        lines.extend([
            f"  static {module_ident}State initial_state() {{",
            f"    {module_ident}State state{{}};",
        ])
        for signal in module.signals:
            if signal.kind == "state":
                lines.append(f"    state.{_cpp_ident(signal.name)} = {signal.init & signal.mask}u;")
        for memory in module.memories:
            if memory.init:
                for idx, value in enumerate(memory.init):
                    masked_value = value & memory.mask
                    if masked_value:
                        lines.append(
                            f"    state.{_cpp_ident(memory.name)}[{idx}] = {masked_value}u;"
                        )
        lines.extend([
            "    return state;",
            "  }",
            "",
            "  void reset() {",
            "    state_ = initial_state();",
            "  }",
            "",
            f"  {module_ident}Outputs step(const {module_ident}Inputs& in) {{",
        ])
        if domain_names:
            lines.extend([
                "    return step_domains(in, kAllClockDomainsMask);",
                "  }",
                "",
                f"  {module_ident}Outputs step_domains(const {module_ident}Inputs& in, uint64_t active_domains_mask) {{",
            ])
        lines.extend([
            f"    {module_ident}State next_state = state_;",
        ])
        lines.extend(emit_comb("    ", declare=True))
        if latch_assignments:
            lines.append("")
            for assignment in latch_assignments:
                target = signal_map[assignment.target]
                lines.append(
                    f"    next_state.{_cpp_ident(assignment.target)} = "
                    f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
                )
                lines.append(
                    f"    state_.{_cpp_ident(assignment.target)} = next_state.{_cpp_ident(assignment.target)};"
                )
        if domain_names:
            if seq_assignments or memory_writes:
                lines.append("")
            for domain in module.clock_domains:
                domain_ident = _cpp_ident(domain.name)
                domain_seq = seq_by_domain[domain.name]
                domain_writes = writes_by_domain[domain.name]
                lines.append(f"    if ((active_domains_mask & kDomainMask_{domain_ident}) != 0u) {{")
                if domain.reset_signal is not None:
                    reset_expr = f"in.{_cpp_ident(domain.reset_signal)}"
                    if domain.reset_active_low:
                        reset_expr = f"!({reset_expr})"
                    lines.append(f"      if ({reset_expr}) {{")
                    for assignment in domain_seq:
                        target = signal_map[assignment.target]
                        if _expr_references_signal(assignment.expr, domain.reset_signal):
                            lines.append(
                                f"        next_state.{_cpp_ident(assignment.target)} = "
                                f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
                            )
                        else:
                            lines.append(
                                f"        next_state.{_cpp_ident(assignment.target)} = {target.init & target.mask}u;"
                            )
                    for write in domain_writes:
                        memory = memory_map[write.memory]
                        if (
                            _expr_references_signal(write.addr, domain.reset_signal)
                            or _expr_references_signal(write.value, domain.reset_signal)
                            or _expr_references_signal(write.enable, domain.reset_signal)
                            or (
                                write.byte_enable is not None
                                and _expr_references_signal(write.byte_enable, domain.reset_signal)
                            )
                        ):
                            addr_expr = self._emit_memory_addr(write.addr, signal_map, memory, memory_map)
                            enable_expr = self._emit_expr(write.enable, signal_map, memory_map)
                            value_expr = self._emit_expr(write.value, signal_map, memory_map)
                            lines.append(f"        if ({enable_expr}) {{")
                            if memory.byte_enable_granularity is None:
                                lines.append(
                                    f"          next_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                                    f"({value_expr}) & {_mask_expr(memory.width)};"
                                )
                            else:
                                assert write.byte_enable is not None
                                be_expr = self._emit_expr(write.byte_enable, signal_map, memory_map)
                                lane_width = memory.byte_enable_granularity
                                lane_count = memory.byte_enable_width
                                assert lane_count is not None
                                lines.append(
                                    f"          uint64_t merged_write = "
                                    f"next_state.{_cpp_ident(write.memory)}[{addr_expr}];"
                                )
                                lines.append(
                                    f"          const uint64_t write_value = "
                                    f"({value_expr}) & {_mask_expr(memory.width)};"
                                )
                                lines.append(f"          const uint64_t be_value = {be_expr};")
                                for lane_idx in range(lane_count):
                                    shift = lane_idx * lane_width
                                    lane_mask = _mask(lane_width)
                                    full_mask = lane_mask << shift
                                    lines.append(
                                        f"          if (((be_value >> {lane_idx}u) & 1u) != 0u) {{"
                                    )
                                    lines.append(
                                        f"            merged_write = "
                                        f"(merged_write & ~0x{full_mask:x}ull) | "
                                        f"(((write_value >> {shift}u) & 0x{lane_mask:x}ull) << {shift}u);"
                                    )
                                    lines.append("          }")
                                lines.append(
                                    f"          next_state.{_cpp_ident(write.memory)}[{addr_expr}] = merged_write;"
                                )
                            lines.append("        }")
                        else:
                            for idx, value in enumerate(memory.init):
                                lines.append(
                                    f"        next_state.{_cpp_ident(write.memory)}[{idx}] = {value & memory.mask}u;"
                                )
                            if not memory.init:
                                lines.append(f"        for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
                                lines.append(f"          next_state.{_cpp_ident(write.memory)}[idx] = 0u;")
                                lines.append("        }")
                    lines.append("      } else {")
                    indent = "        "
                else:
                    indent = "      "
                for assignment in domain_seq:
                    target = signal_map[assignment.target]
                    lines.append(
                        f"{indent}next_state.{_cpp_ident(assignment.target)} = "
                        f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
                    )
                for write in domain_writes:
                    memory = memory_map[write.memory]
                    addr_expr = self._emit_memory_addr(write.addr, signal_map, memory, memory_map)
                    enable_expr = self._emit_expr(write.enable, signal_map, memory_map)
                    value_expr = self._emit_expr(write.value, signal_map, memory_map)
                    lines.append(f"{indent}if ({enable_expr}) {{")
                    if memory.byte_enable_granularity is None:
                        lines.append(
                            f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                            f"({value_expr}) & {_mask_expr(memory.width)};"
                        )
                    else:
                        assert write.byte_enable is not None
                        be_expr = self._emit_expr(write.byte_enable, signal_map, memory_map)
                        lane_width = memory.byte_enable_granularity
                        lane_count = memory.byte_enable_width
                        assert lane_count is not None
                        lines.append(
                            f"{indent}  uint64_t merged_write = "
                            f"next_state.{_cpp_ident(write.memory)}[{addr_expr}];"
                        )
                        lines.append(
                            f"{indent}  const uint64_t write_value = "
                            f"({value_expr}) & {_mask_expr(memory.width)};"
                        )
                        lines.append(f"{indent}  const uint64_t be_value = {be_expr};")
                        for lane_idx in range(lane_count):
                            shift = lane_idx * lane_width
                            lane_mask = _mask(lane_width)
                            full_mask = lane_mask << shift
                            lines.append(
                                f"{indent}  if (((be_value >> {lane_idx}u) & 1u) != 0u) {{"
                            )
                            lines.append(
                                f"{indent}    merged_write = "
                                f"(merged_write & ~0x{full_mask:x}ull) | "
                                f"(((write_value >> {shift}u) & 0x{lane_mask:x}ull) << {shift}u);"
                            )
                            lines.append(f"{indent}  }}")
                        lines.append(
                            f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = merged_write;"
                        )
                    lines.append(f"{indent}}}")
                if domain.reset_signal is not None:
                    lines.append("      }")
                lines.append("    }")
        elif seq_assignments or memory_writes:
            lines.append("")
            if module.reset_signal is not None:
                lines.append(f"    if (in.{_cpp_ident(module.reset_signal)}) {{")
                handled_memories = set()
                for assignment in seq_assignments:
                    target = signal_map[assignment.target]
                    if _expr_references_signal(assignment.expr, module.reset_signal):
                        lines.append(
                            f"      next_state.{_cpp_ident(assignment.target)} = "
                            f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
                        )
                    else:
                        lines.append(
                            f"      next_state.{_cpp_ident(assignment.target)} = {target.init & target.mask}u;"
                        )
                for write in memory_writes:
                    memory = memory_map[write.memory]
                    if (
                        _expr_references_signal(write.addr, module.reset_signal)
                        or _expr_references_signal(write.value, module.reset_signal)
                        or _expr_references_signal(write.enable, module.reset_signal)
                        or (
                            write.byte_enable is not None
                            and _expr_references_signal(write.byte_enable, module.reset_signal)
                        )
                    ):
                        handled_memories.add(write.memory)
                        addr_expr = self._emit_memory_addr(write.addr, signal_map, memory)
                        enable_expr = self._emit_expr(write.enable, signal_map, memory_map)
                        value_expr = self._emit_expr(write.value, signal_map, memory_map)
                        lines.append(f"      if ({enable_expr}) {{")
                        if memory.byte_enable_granularity is None:
                            lines.append(
                                f"        next_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                                f"({value_expr}) & {_mask_expr(memory.width)};"
                            )
                        else:
                            assert write.byte_enable is not None
                            be_expr = self._emit_expr(write.byte_enable, signal_map, memory_map)
                            lane_width = memory.byte_enable_granularity
                            lane_count = memory.byte_enable_width
                            assert lane_count is not None
                            lines.append(
                                f"        uint64_t merged_write = "
                                f"next_state.{_cpp_ident(write.memory)}[{addr_expr}];"
                            )
                            lines.append(
                                f"        const uint64_t write_value = "
                                f"({value_expr}) & {_mask_expr(memory.width)};"
                            )
                            lines.append(f"        const uint64_t be_value = {be_expr};")
                            for lane_idx in range(lane_count):
                                shift = lane_idx * lane_width
                                lane_mask = _mask(lane_width)
                                full_mask = lane_mask << shift
                                lines.append(
                                    f"        if (((be_value >> {lane_idx}u) & 1u) != 0u) {{"
                                )
                                lines.append(
                                    f"          merged_write = "
                                    f"(merged_write & ~0x{full_mask:x}ull) | "
                                    f"(((write_value >> {shift}u) & 0x{lane_mask:x}ull) << {shift}u);"
                                )
                                lines.append("        }")
                            lines.append(
                                f"        next_state.{_cpp_ident(write.memory)}[{addr_expr}] = merged_write;"
                            )
                        lines.append("      }")
                for memory in module.memories:
                    if memory.name in handled_memories:
                        continue
                    for idx, value in enumerate(memory.init):
                        lines.append(
                            f"      next_state.{_cpp_ident(memory.name)}[{idx}] = {value & memory.mask}u;"
                        )
                    if not memory.init:
                        lines.append(f"      for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
                        lines.append(f"        next_state.{_cpp_ident(memory.name)}[idx] = 0u;")
                        lines.append("      }")
                lines.append("    } else {")
                indent = "      "
            else:
                indent = "    "
            for assignment in seq_assignments:
                target = signal_map[assignment.target]
                lines.append(
                    f"{indent}next_state.{_cpp_ident(assignment.target)} = "
                    f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
                )
            for write in memory_writes:
                memory = memory_map[write.memory]
                addr_expr = self._emit_memory_addr(write.addr, signal_map, memory)
                enable_expr = self._emit_expr(write.enable, signal_map, memory_map)
                value_expr = self._emit_expr(write.value, signal_map, memory_map)
                lines.append(f"{indent}if ({enable_expr}) {{")
                if memory.byte_enable_granularity is None:
                    lines.append(
                        f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                        f"({value_expr}) & {_mask_expr(memory.width)};"
                    )
                else:
                    assert write.byte_enable is not None
                    be_expr = self._emit_expr(write.byte_enable, signal_map, memory_map)
                    lane_width = memory.byte_enable_granularity
                    lane_count = memory.byte_enable_width
                    assert lane_count is not None
                    lines.append(
                        f"{indent}  uint64_t merged_write = "
                        f"next_state.{_cpp_ident(write.memory)}[{addr_expr}];"
                    )
                    lines.append(
                        f"{indent}  const uint64_t write_value = "
                        f"({value_expr}) & {_mask_expr(memory.width)};"
                    )
                    lines.append(f"{indent}  const uint64_t be_value = {be_expr};")
                    for lane_idx in range(lane_count):
                        shift = lane_idx * lane_width
                        lane_mask = _mask(lane_width)
                        full_mask = lane_mask << shift
                        lines.append(
                            f"{indent}  if (((be_value >> {lane_idx}u) & 1u) != 0u) {{"
                        )
                        lines.append(
                            f"{indent}    merged_write = "
                            f"(merged_write & ~0x{full_mask:x}ull) | "
                            f"(((write_value >> {shift}u) & 0x{lane_mask:x}ull) << {shift}u);"
                        )
                        lines.append(f"{indent}  }}")
                    lines.append(
                        f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = merged_write;"
                    )
                lines.append(f"{indent}}}")
            if module.reset_signal is not None:
                lines.append("    }")
        if module.outputs_post_state:
            lines.append("")
            read_first_memories = [memory for memory in module.memories if memory.read_during_write == "read_first"]
            if read_first_memories:
                lines.append(f"    {module_ident}State comb_state = next_state;")
                for write in memory_writes:
                    memory = memory_map[write.memory]
                    if memory.read_during_write != "read_first":
                        continue
                    addr_expr = self._emit_memory_addr(write.addr, signal_map, memory, memory_map)
                    enable_expr = self._emit_expr(write.enable, signal_map, memory_map)
                    lines.append(f"    if ({enable_expr}) {{")
                    lines.append(
                        f"      comb_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                        f"state_.{_cpp_ident(write.memory)}[{addr_expr}];"
                    )
                    lines.append("    }")
                lines.append("")
                lines.extend(emit_comb("    ", declare=False, state_expr="comb_state"))
            else:
                lines.extend(emit_comb("    ", declare=False, state_expr="next_state"))
        lines.extend([
            "",
            "    state_ = next_state;",
        ])
        lines.extend([
            "",
            f"    {module_ident}Outputs outputs;",
        ])
        for output_name in module.outputs:
            lines.append(f"    outputs.{_cpp_ident(output_name)} = {_cpp_value_name(output_name)};")
        lines.extend([
            "    return outputs;",
            "  }",
            "",
            "  void export_state(uint64_t* state_out) const {",
        ])
        state_signals = [signal for signal in module.signals if signal.kind == "state"]
        state_cursor = 0
        for signal in state_signals:
            lines.append(
                f"    state_out[{state_cursor}] = state_.{_cpp_ident(signal.name)} & {_mask_expr(signal.width)};"
            )
            state_cursor += 1
        for memory in module.memories:
            lines.append(f"    for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
            lines.append(
                f"      state_out[{state_cursor}u + idx] = state_.{_cpp_ident(memory.name)}[idx] & {_mask_expr(memory.width)};"
            )
            lines.append("    }")
            state_cursor += memory.depth
        lines.extend([
            "  }",
            "",
            "  void import_state(const uint64_t* state_in) {",
        ])
        state_cursor = 0
        for signal in state_signals:
            lines.append(
                f"    state_.{_cpp_ident(signal.name)} = state_in[{state_cursor}] & {_mask_expr(signal.width)};"
            )
            state_cursor += 1
        for memory in module.memories:
            lines.append(f"    for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
            lines.append(
                f"      state_.{_cpp_ident(memory.name)}[idx] = state_in[{state_cursor}u + idx] & {_mask_expr(memory.width)};"
            )
            lines.append("    }")
            state_cursor += memory.depth
        lines.extend([
            "  }",
            "",
            " private:",
            f"  {module_ident}State state_ = initial_state();",
            "};",
            "",
            f"}}  // namespace {self.namespace}",
            "",
        ])
        return "\n".join(lines)

    def emit_runtime_translation_unit(self, module: SimModule) -> str:
        self._ensure_supported_clock_domains(module)
        if self._requires_wide_support(module):
            return self._emit_wide_runtime_translation_unit(module)
        module_ident = _cpp_ident(module.name)
        symbol_prefix = self._symbol_prefix(module)
        inputs = [signal for signal in module.signals if signal.kind == "input"]
        signal_map = module.signal_map()
        lines = [self.emit_translation_unit(module)]
        lines.extend([
            'extern "C" {',
            "",
            f"void* {symbol_prefix}_create() {{",
            f"  return new {self.namespace}::{module_ident}Simulator();",
            "}",
            "",
            f"void {symbol_prefix}_destroy(void* handle) {{",
            f"  delete static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "}",
            "",
            f"void {symbol_prefix}_reset(void* handle) {{",
            f"  static_cast<{self.namespace}::{module_ident}Simulator*>(handle)->reset();",
            "}",
            "",
            f"void {symbol_prefix}_step(void* handle, const uint64_t* inputs, uint64_t* outputs) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            f"  {self.namespace}::{module_ident}Inputs in;",
        ])
        for idx, signal in enumerate(inputs):
            lines.append(
                f"  in.{_cpp_ident(signal.name)} = inputs[{idx}] & {_mask_expr(signal.width)};"
            )
        lines.extend([
            "  auto result = simulator->step(in);",
        ])
        for idx, output_name in enumerate(module.outputs):
            signal = signal_map[output_name]
            lines.append(
                f"  outputs[{idx}] = result.{_cpp_ident(output_name)} & {_mask_expr(signal.width)};"
            )
        lines.extend([
            "}",
            "",
            f"void {symbol_prefix}_step_domains(void* handle, uint64_t active_domains_mask, const uint64_t* inputs, uint64_t* outputs) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            f"  {self.namespace}::{module_ident}Inputs in;",
        ])
        for idx, signal in enumerate(inputs):
            lines.append(
                f"  in.{_cpp_ident(signal.name)} = inputs[{idx}] & {_mask_expr(signal.width)};"
            )
        if module.clock_domains:
            lines.extend([
                "  auto result = simulator->step_domains(in, active_domains_mask);",
            ])
        else:
            lines.extend([
                "  auto result = simulator->step(in);",
            ])
        for idx, output_name in enumerate(module.outputs):
            signal = signal_map[output_name]
            lines.append(
                f"  outputs[{idx}] = result.{_cpp_ident(output_name)} & {_mask_expr(signal.width)};"
            )
        lines.extend([
            "}",
            "",
            f"void {symbol_prefix}_step_many(",
            "    void* handle,",
            "    uint64_t cycles,",
            "    const uint64_t* inputs,",
            "    uint64_t* outputs) {",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  for (uint64_t cycle = 0; cycle < cycles; ++cycle) {",
            f"    {self.namespace}::{module_ident}Inputs in;",
        ])
        for idx, signal in enumerate(inputs):
            lines.append(
                f"    in.{_cpp_ident(signal.name)} = "
                f"inputs[cycle * {len(inputs)}u + {idx}u] & {_mask_expr(signal.width)};"
            )
        lines.extend([
            "    auto result = simulator->step(in);",
        ])
        for idx, output_name in enumerate(module.outputs):
            signal = signal_map[output_name]
            lines.append(
                f"    outputs[cycle * {len(module.outputs)}u + {idx}u] = "
                f"result.{_cpp_ident(output_name)} & {_mask_expr(signal.width)};"
            )
        lines.extend([
            "  }",
            "}",
            "",
            f"void {symbol_prefix}_save_state(void* handle, uint64_t* state_out) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  simulator->export_state(state_out);",
            "}",
            "",
            f"void {symbol_prefix}_load_state(void* handle, const uint64_t* state_in) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  simulator->import_state(state_in);",
            "}",
            "",
            "}  // extern \"C\"",
            "",
        ])
        return "\n".join(lines)

    def _requires_wide_support(self, module: SimModule) -> bool:
        return any(signal.width > 64 for signal in module.signals) or any(
            memory.width > 64 for memory in module.memories
        )

    def _wide_storage_bits(self, module: SimModule) -> int:
        signal_map = module.signal_map()
        memory_map = module.memory_map()
        object_bits = [signal.width for signal in module.signals]
        object_bits.extend(memory.width for memory in module.memories)
        expr_bits = [
            self._estimate_wide_expr_bits(assignment.expr, signal_map, memory_map)
            for assignment in module.assignments
        ]
        for write in module.memory_writes:
            expr_bits.extend(
                (
                    self._estimate_wide_expr_bits(write.addr, signal_map, memory_map),
                    self._estimate_wide_expr_bits(write.value, signal_map, memory_map),
                    self._estimate_wide_expr_bits(write.enable, signal_map, memory_map),
                )
            )
            if write.byte_enable is not None:
                expr_bits.append(
                    self._estimate_wide_expr_bits(write.byte_enable, signal_map, memory_map)
                )
        needed = max([1, *object_bits, *expr_bits])
        return _word_count(needed + 64) * 64

    def _estimate_wide_expr_bits(
        self,
        expr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
    ) -> int:
        if isinstance(expr, ConstExpr):
            return max(expr.width, int(expr.value).bit_length() or 1)
        if isinstance(expr, SignalRef):
            return signal_map[expr.name].width
        if isinstance(expr, MemoryReadExpr):
            return memory_map[expr.memory].width
        if isinstance(expr, MaskExpr):
            return expr.width
        if isinstance(expr, UnaryExpr):
            child_bits = self._estimate_wide_expr_bits(expr.value, signal_map, memory_map)
            if expr.op == "!":
                return 1
            if expr.op == "~":
                return _infer_expr_width(expr.value, signal_map, memory_map)
            if expr.op == "-":
                return child_bits + 1
            return _infer_expr_width(expr.value, signal_map, memory_map)
        if isinstance(expr, BinaryExpr):
            lhs_bits = self._estimate_wide_expr_bits(expr.lhs, signal_map, memory_map)
            rhs_bits = self._estimate_wide_expr_bits(expr.rhs, signal_map, memory_map)
            if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
                return 1
            if expr.op in {"+", "-"}:
                return max(lhs_bits, rhs_bits) + 1
            if expr.op == "*":
                return lhs_bits + rhs_bits
            if expr.op == "<<":
                return lhs_bits + self._estimate_shift_extent(expr.rhs, signal_map, memory_map)
            if expr.op in {">>", ">>>"}:
                return lhs_bits
            return max(lhs_bits, rhs_bits)
        if isinstance(expr, MuxExpr):
            return max(
                self._estimate_wide_expr_bits(expr.when_true, signal_map, memory_map),
                self._estimate_wide_expr_bits(expr.when_false, signal_map, memory_map),
            )
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _estimate_shift_extent(
        self,
        expr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
    ) -> int:
        if isinstance(expr, ConstExpr):
            return min(int(expr.value), 4096)
        width = _infer_expr_width(expr, signal_map, memory_map)
        if width <= 8:
            return (1 << width) - 1
        if width <= 12:
            return 4095
        return 4096

    def _emit_wide_translation_unit(self, module: SimModule) -> str:
        signal_map = module.signal_map()
        memory_map = module.memory_map()
        module_ident = _cpp_ident(module.name)
        storage_bits = self._wide_storage_bits(module)
        storage_words = _word_count(storage_bits)
        wire_output_signals = [
            signal for signal in module.signals if signal.kind in {"wire", "output"}
        ]
        comb_assignments = [a for a in module.assignments if a.phase == "comb"]
        latch_assignments = [a for a in module.assignments if a.phase == "latch"]
        seq_assignments = [a for a in module.assignments if a.phase == "seq"]
        memory_writes = list(module.memory_writes)
        domain_names = [domain.name for domain in module.clock_domains]
        seq_by_domain = self._group_seq_assignments_by_domain(module)
        writes_by_domain = self._group_memory_writes_by_domain(module)

        def emit_comb(indent: str, *, declare: bool, state_expr: str = "state_") -> List[str]:
            block_lines: List[str] = []
            for signal in wire_output_signals:
                lhs = _cpp_value_name(signal.name)
                prefix = "Value " if declare else ""
                block_lines.append(f"{indent}{prefix}{lhs} = Value::zero();")
            if wire_output_signals and comb_assignments:
                block_lines.append("")
            for assignment in comb_assignments:
                target = signal_map[assignment.target]
                block_lines.append(
                    f"{indent}{_cpp_value_name(assignment.target)} = "
                    f"value_mask({self._emit_wide_expr(assignment.expr, signal_map, memory_map, state_expr=state_expr)}, {target.width}u);"
                )
            return block_lines

        lines: List[str] = [
            "#include <array>",
            "#include <cstddef>",
            "#include <cstdint>",
            "#include <initializer_list>",
            "",
            f"namespace {self.namespace} {{",
            "",
            f"template <std::size_t Words> struct BigValue {{",
            "  std::array<uint64_t, Words> words{};",
            "  static BigValue zero() { return BigValue{}; }",
            "  static BigValue from_u64(uint64_t value) {",
            "    BigValue out{};",
            "    out.words[0] = value;",
            "    return out;",
            "  }",
            "};",
            "",
            f"static constexpr std::size_t kStorageBits = {storage_bits}u;",
            f"static constexpr std::size_t kStorageWords = {storage_words}u;",
            "using Value = BigValue<kStorageWords>;",
            "",
            "template <std::size_t Words>",
            "inline BigValue<Words> make_value(std::initializer_list<uint64_t> init) {",
            "  BigValue<Words> out{};",
            "  std::size_t idx = 0;",
            "  for (uint64_t word : init) {",
            "    if (idx >= Words) {",
            "      break;",
            "    }",
            "    out.words[idx++] = word;",
            "  }",
            "  return out;",
            "}",
            "",
            "inline bool value_nonzero(const Value& value) {",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    if (value.words[idx] != 0u) {",
            "      return true;",
            "    }",
            "  }",
            "  return false;",
            "}",
            "",
            "inline bool value_sign_bit(const Value& value) {",
            "  return ((value.words[kStorageWords - 1u] >> 63u) & 1u) != 0u;",
            "}",
            "",
            "inline Value value_mask(Value value, std::size_t width) {",
            "  if (width >= kStorageBits) {",
            "    return value;",
            "  }",
            "  const std::size_t word_idx = width / 64u;",
            "  const std::size_t bit_idx = width % 64u;",
            "  if (bit_idx != 0u && word_idx < kStorageWords) {",
            "    value.words[word_idx] &= ((uint64_t(1) << bit_idx) - 1u);",
            "    for (std::size_t idx = word_idx + 1u; idx < kStorageWords; ++idx) {",
            "      value.words[idx] = 0u;",
            "    }",
            "    return value;",
            "  }",
            "  for (std::size_t idx = word_idx; idx < kStorageWords; ++idx) {",
            "    value.words[idx] = 0u;",
            "  }",
            "  return value;",
            "}",
            "",
            "inline Value value_sign_extend(Value value, std::size_t width) {",
            "  value = value_mask(value, width);",
            "  if (width == 0u || width >= kStorageBits) {",
            "    return value;",
            "  }",
            "  const std::size_t sign_word = (width - 1u) / 64u;",
            "  const std::size_t sign_bit = (width - 1u) % 64u;",
            "  if (((value.words[sign_word] >> sign_bit) & 1u) == 0u) {",
            "    return value;",
            "  }",
            "  const std::size_t next_bit = width % 64u;",
            "  const std::size_t next_word = width / 64u;",
            "  if (next_bit != 0u && next_word < kStorageWords) {",
            "    value.words[next_word] |= ~((uint64_t(1) << next_bit) - 1u);",
            "    for (std::size_t idx = next_word + 1u; idx < kStorageWords; ++idx) {",
            "      value.words[idx] = UINT64_MAX;",
            "    }",
            "    return value;",
            "  }",
            "  for (std::size_t idx = next_word; idx < kStorageWords; ++idx) {",
            "    value.words[idx] = UINT64_MAX;",
            "  }",
            "  return value;",
            "}",
            "",
            "inline int value_cmp_unsigned(const Value& lhs, const Value& rhs) {",
            "  for (std::size_t rev = 0; rev < kStorageWords; ++rev) {",
            "    const std::size_t idx = kStorageWords - 1u - rev;",
            "    if (lhs.words[idx] < rhs.words[idx]) {",
            "      return -1;",
            "    }",
            "    if (lhs.words[idx] > rhs.words[idx]) {",
            "      return 1;",
            "    }",
            "  }",
            "  return 0;",
            "}",
            "",
            "inline int value_cmp_signed(const Value& lhs, const Value& rhs) {",
            "  const bool lhs_neg = value_sign_bit(lhs);",
            "  const bool rhs_neg = value_sign_bit(rhs);",
            "  if (lhs_neg != rhs_neg) {",
            "    return lhs_neg ? -1 : 1;",
            "  }",
            "  return value_cmp_unsigned(lhs, rhs);",
            "}",
            "",
            "inline Value value_not(const Value& value) {",
            "  Value out{};",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    out.words[idx] = ~value.words[idx];",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_and(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    out.words[idx] = lhs.words[idx] & rhs.words[idx];",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_or(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    out.words[idx] = lhs.words[idx] | rhs.words[idx];",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_memory_byte_merge(",
            "    const Value& prior,",
            "    const Value& value,",
            "    const Value& byte_enable,",
            "    std::size_t width,",
            "    std::size_t lane_width) {",
            "  Value out = value_mask(prior, width);",
            "  const Value masked_value = value_mask(value, width);",
            "  if (lane_width == 0u) {",
            "    return out;",
            "  }",
            "  const std::size_t lane_count = width / lane_width;",
            "  for (std::size_t lane_idx = 0; lane_idx < lane_count; ++lane_idx) {",
            "    const std::size_t be_word = lane_idx / 64u;",
            "    const std::size_t be_bit = lane_idx % 64u;",
            "    if (((byte_enable.words[be_word] >> be_bit) & 1u) == 0u) {",
            "      continue;",
            "    }",
            "    const std::size_t start = lane_idx * lane_width;",
            "    for (std::size_t bit = 0; bit < lane_width; ++bit) {",
            "      const std::size_t abs_bit = start + bit;",
            "      const std::size_t word_idx = abs_bit / 64u;",
            "      const std::size_t bit_idx = abs_bit % 64u;",
            "      const uint64_t mask = uint64_t(1) << bit_idx;",
            "      if ((masked_value.words[word_idx] & mask) != 0u) {",
            "        out.words[word_idx] |= mask;",
            "      } else {",
            "        out.words[word_idx] &= ~mask;",
            "      }",
            "    }",
            "  }",
            "  return value_mask(out, width);",
            "}",
            "",
            "inline Value value_xor(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    out.words[idx] = lhs.words[idx] ^ rhs.words[idx];",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_add(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  unsigned __int128 carry = 0;",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    unsigned __int128 sum = static_cast<unsigned __int128>(lhs.words[idx]) +",
            "        static_cast<unsigned __int128>(rhs.words[idx]) + carry;",
            "    out.words[idx] = static_cast<uint64_t>(sum);",
            "    carry = sum >> 64u;",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_add_signed(const Value& lhs, const Value& rhs, std::size_t lhs_width, std::size_t rhs_width) {",
            "  return value_add(value_sign_extend(value_mask(lhs, lhs_width), lhs_width),",
            "                   value_sign_extend(value_mask(rhs, rhs_width), rhs_width));",
            "}",
            "",
            "inline Value value_sub(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  unsigned __int128 borrow = 0;",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    const unsigned __int128 minuend = static_cast<unsigned __int128>(lhs.words[idx]);",
            "    const unsigned __int128 subtrahend = static_cast<unsigned __int128>(rhs.words[idx]) + borrow;",
            "    out.words[idx] = static_cast<uint64_t>(minuend - subtrahend);",
            "    borrow = minuend < subtrahend ? 1u : 0u;",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_sub_signed(const Value& lhs, const Value& rhs, std::size_t lhs_width, std::size_t rhs_width) {",
            "  return value_sub(value_sign_extend(value_mask(lhs, lhs_width), lhs_width),",
            "                   value_sign_extend(value_mask(rhs, rhs_width), rhs_width));",
            "}",
            "",
            "inline Value value_neg(const Value& value) {",
            "  return value_sub(Value::zero(), value);",
            "}",
            "",
            "inline Value value_mul(const Value& lhs, const Value& rhs) {",
            "  Value out{};",
            "  for (std::size_t lhs_idx = 0; lhs_idx < kStorageWords; ++lhs_idx) {",
            "    unsigned __int128 carry = 0;",
            "    for (std::size_t rhs_idx = 0; rhs_idx + lhs_idx < kStorageWords; ++rhs_idx) {",
            "      const std::size_t out_idx = lhs_idx + rhs_idx;",
            "      unsigned __int128 accum = static_cast<unsigned __int128>(lhs.words[lhs_idx]) *",
            "          static_cast<unsigned __int128>(rhs.words[rhs_idx]);",
            "      accum += static_cast<unsigned __int128>(out.words[out_idx]);",
            "      accum += carry;",
            "      out.words[out_idx] = static_cast<uint64_t>(accum);",
            "      carry = accum >> 64u;",
            "    }",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_mul_signed(const Value& lhs, const Value& rhs, std::size_t lhs_width, std::size_t rhs_width) {",
            "  const Value lhs_ext = value_sign_extend(value_mask(lhs, lhs_width), lhs_width);",
            "  const Value rhs_ext = value_sign_extend(value_mask(rhs, rhs_width), rhs_width);",
            "  const bool lhs_neg = value_sign_bit(lhs_ext);",
            "  const bool rhs_neg = value_sign_bit(rhs_ext);",
            "  const Value lhs_mag = lhs_neg ? value_neg(lhs_ext) : lhs_ext;",
            "  const Value rhs_mag = rhs_neg ? value_neg(rhs_ext) : rhs_ext;",
            "  Value product = value_mul(lhs_mag, rhs_mag);",
            "  if (lhs_neg != rhs_neg) {",
            "    product = value_neg(product);",
            "  }",
            "  return product;",
            "}",
            "",
            "inline std::size_t value_to_size(const Value& value) {",
            "  for (std::size_t idx = 1; idx < kStorageWords; ++idx) {",
            "    if (value.words[idx] != 0u) {",
            "      return kStorageBits;",
            "    }",
            "  }",
            "  if (value.words[0] > static_cast<uint64_t>(kStorageBits)) {",
            "    return kStorageBits;",
            "  }",
            "  return static_cast<std::size_t>(value.words[0]);",
            "}",
            "",
            "inline Value value_shl(const Value& value, std::size_t shift) {",
            "  if (shift == 0u) {",
            "    return value;",
            "  }",
            "  if (shift >= kStorageBits) {",
            "    return Value::zero();",
            "  }",
            "  Value out{};",
            "  const std::size_t word_shift = shift / 64u;",
            "  const std::size_t bit_shift = shift % 64u;",
            "  for (std::size_t rev = 0; rev < kStorageWords; ++rev) {",
            "    const std::size_t idx = kStorageWords - 1u - rev;",
            "    if (idx < word_shift) {",
            "      continue;",
            "    }",
            "    const std::size_t src = idx - word_shift;",
            "    out.words[idx] |= value.words[src] << bit_shift;",
            "    if (bit_shift != 0u && src > 0u) {",
            "      out.words[idx] |= value.words[src - 1u] >> (64u - bit_shift);",
            "    }",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_lshr(const Value& value, std::size_t shift) {",
            "  if (shift == 0u) {",
            "    return value;",
            "  }",
            "  if (shift >= kStorageBits) {",
            "    return Value::zero();",
            "  }",
            "  Value out{};",
            "  const std::size_t word_shift = shift / 64u;",
            "  const std::size_t bit_shift = shift % 64u;",
            "  for (std::size_t idx = 0; idx < kStorageWords; ++idx) {",
            "    const std::size_t src = idx + word_shift;",
            "    if (src >= kStorageWords) {",
            "      continue;",
            "    }",
            "    out.words[idx] |= value.words[src] >> bit_shift;",
            "    if (bit_shift != 0u && (src + 1u) < kStorageWords) {",
            "      out.words[idx] |= value.words[src + 1u] << (64u - bit_shift);",
            "    }",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_ashr(const Value& value, std::size_t shift) {",
            "  if (shift == 0u) {",
            "    return value;",
            "  }",
            "  if (shift >= kStorageBits) {",
            "    return value_sign_bit(value) ? value_not(Value::zero()) : Value::zero();",
            "  }",
            "  Value out = value_lshr(value, shift);",
            "  if (!value_sign_bit(value)) {",
            "    return out;",
            "  }",
            "  const std::size_t fill_from = kStorageBits - shift;",
            "  const std::size_t start_word = fill_from / 64u;",
            "  const std::size_t start_bit = fill_from % 64u;",
            "  if (start_bit != 0u && start_word < kStorageWords) {",
            "    out.words[start_word] |= ~((uint64_t(1) << start_bit) - 1u);",
            "    for (std::size_t idx = start_word + 1u; idx < kStorageWords; ++idx) {",
            "      out.words[idx] = UINT64_MAX;",
            "    }",
            "    return out;",
            "  }",
            "  for (std::size_t idx = start_word; idx < kStorageWords; ++idx) {",
            "    out.words[idx] = UINT64_MAX;",
            "  }",
            "  return out;",
            "}",
            "",
            "inline Value value_select(bool cond, const Value& when_true, const Value& when_false) {",
            "  return cond ? when_true : when_false;",
            "}",
            "",
            "inline Value value_bool(bool cond) {",
            "  return Value::from_u64(cond ? 1u : 0u);",
            "}",
            "",
            "inline Value value_from_words(const uint64_t* src, std::size_t count) {",
            "  Value out{};",
            "  const std::size_t bound = count < kStorageWords ? count : kStorageWords;",
            "  for (std::size_t idx = 0; idx < bound; ++idx) {",
            "    out.words[idx] = src[idx];",
            "  }",
            "  return out;",
            "}",
            "",
            "inline void value_to_words(const Value& value, uint64_t* dst, std::size_t count, std::size_t width) {",
            "  const Value masked = value_mask(value, width);",
            "  for (std::size_t idx = 0; idx < count; ++idx) {",
            "    dst[idx] = idx < kStorageWords ? masked.words[idx] : 0u;",
            "  }",
            "}",
            "",
            f"struct {module_ident}State {{",
        ]
        for signal in module.signals:
            if signal.kind == "state":
                init_expr = self._emit_wide_const(signal.init, signal.width)
                lines.append(f"  Value {_cpp_ident(signal.name)} = {init_expr};")
        for memory in module.memories:
            lines.append(f"  Value {_cpp_ident(memory.name)}[{memory.depth}] = {{}};")
        lines.extend([
            "};",
            "",
            f"struct {module_ident}Inputs {{",
        ])
        for signal in module.signals:
            if signal.kind == "input":
                lines.append(f"  Value {_cpp_ident(signal.name)} = Value::zero();")
        lines.extend([
            "};",
            "",
            f"struct {module_ident}Outputs {{",
        ])
        for output_name in module.outputs:
            lines.append(f"  Value {_cpp_ident(output_name)} = Value::zero();")
        lines.extend([
            "};",
            "",
            f"class {module_ident}Simulator {{",
            " public:",
        ])
        if domain_names:
            for index, domain in enumerate(module.clock_domains):
                lines.append(f"  static constexpr uint64_t kDomainMask_{_cpp_ident(domain.name)} = 1ull << {index}u;")
            all_domains_mask = " | ".join(
                f"kDomainMask_{_cpp_ident(domain.name)}" for domain in module.clock_domains
            )
            lines.extend([
                f"  static constexpr uint64_t kAllClockDomainsMask = {all_domains_mask};",
                "",
            ])
        lines.extend([
            f"  static {module_ident}State initial_state() {{",
            f"    {module_ident}State state{{}};",
        ])
        for signal in module.signals:
            if signal.kind == "state":
                lines.append(
                    f"    state.{_cpp_ident(signal.name)} = {self._emit_wide_const(signal.init, signal.width)};"
                )
        for memory in module.memories:
            if memory.init:
                for idx, value in enumerate(memory.init):
                    masked_value = value & memory.mask
                    if masked_value:
                        lines.append(
                            f"    state.{_cpp_ident(memory.name)}[{idx}] = {self._emit_wide_const(masked_value, memory.width)};"
                        )
        lines.extend([
            "    return state;",
            "  }",
            "",
            "  void reset() {",
            "    state_ = initial_state();",
            "  }",
            "",
            f"  {module_ident}Outputs step(const {module_ident}Inputs& in) {{",
        ])
        if domain_names:
            lines.extend([
                "    return step_domains(in, kAllClockDomainsMask);",
                "  }",
                "",
                f"  {module_ident}Outputs step_domains(const {module_ident}Inputs& in, uint64_t active_domains_mask) {{",
            ])
        lines.extend([
            f"    {module_ident}State next_state = state_;",
        ])
        lines.extend(emit_comb("    ", declare=True))
        if latch_assignments:
            lines.append("")
            for assignment in latch_assignments:
                target = signal_map[assignment.target]
                lines.append(
                    f"    next_state.{_cpp_ident(assignment.target)} = "
                    f"value_mask({self._emit_wide_expr(assignment.expr, signal_map, memory_map)}, {target.width}u);"
                )
                lines.append(
                    f"    state_.{_cpp_ident(assignment.target)} = next_state.{_cpp_ident(assignment.target)};"
                )
        if domain_names:
            if seq_assignments or memory_writes:
                lines.append("")
            for domain in module.clock_domains:
                domain_ident = _cpp_ident(domain.name)
                domain_seq = seq_by_domain[domain.name]
                domain_writes = writes_by_domain[domain.name]
                lines.append(f"    if ((active_domains_mask & kDomainMask_{domain_ident}) != 0u) {{")
                if domain.reset_signal is not None:
                    reset_expr = f"value_nonzero(in.{_cpp_ident(domain.reset_signal)})"
                    if domain.reset_active_low:
                        reset_expr = f"!({reset_expr})"
                    lines.append(f"      if ({reset_expr}) {{")
                    for assignment in domain_seq:
                        target = signal_map[assignment.target]
                        lines.append(
                            f"        next_state.{_cpp_ident(assignment.target)} = {self._emit_wide_const(target.init, target.width)};"
                        )
                    for write in domain_writes:
                        memory = memory_map[write.memory]
                        for idx, value in enumerate(memory.init):
                            lines.append(
                                f"        next_state.{_cpp_ident(write.memory)}[{idx}] = {self._emit_wide_const(value & memory.mask, memory.width)};"
                            )
                        if not memory.init:
                            lines.append(f"        for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
                            lines.append(
                                f"          next_state.{_cpp_ident(write.memory)}[idx] = {self._emit_wide_const(0, memory.width)};"
                            )
                            lines.append("        }")
                    lines.append("      } else {")
                    indent = "        "
                else:
                    indent = "      "
                for assignment in domain_seq:
                    target = signal_map[assignment.target]
                    lines.append(
                        f"{indent}next_state.{_cpp_ident(assignment.target)} = "
                        f"value_mask({self._emit_wide_expr(assignment.expr, signal_map, memory_map)}, {target.width}u);"
                    )
                for write in domain_writes:
                    memory = memory_map[write.memory]
                    addr_expr = self._emit_wide_memory_addr(write.addr, signal_map, memory_map, memory)
                    enable_expr = self._emit_wide_expr(write.enable, signal_map, memory_map)
                    value_expr = self._emit_wide_expr(write.value, signal_map, memory_map)
                    lines.append(f"{indent}if (value_nonzero({enable_expr})) {{")
                    if memory.byte_enable_granularity is None:
                        write_expr = f"value_mask({value_expr}, {memory.width}u)"
                    else:
                        assert write.byte_enable is not None
                        byte_enable_expr = self._emit_wide_expr(write.byte_enable, signal_map, memory_map)
                        write_expr = (
                            f"value_memory_byte_merge("
                            f"next_state.{_cpp_ident(write.memory)}[{addr_expr}], "
                            f"{value_expr}, "
                            f"{byte_enable_expr}, "
                            f"{memory.width}u, "
                            f"{memory.byte_enable_granularity}u)"
                        )
                    lines.append(
                        f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = {write_expr};"
                    )
                    lines.append(f"{indent}}}")
                if domain.reset_signal is not None:
                    lines.append("      }")
                lines.append("    }")
        elif seq_assignments or memory_writes:
            lines.append("")
            if module.reset_signal is not None:
                lines.append(f"    if (value_nonzero(in.{_cpp_ident(module.reset_signal)})) {{")
                handled_memories = set()
                for assignment in seq_assignments:
                    target = signal_map[assignment.target]
                    if _expr_references_signal(assignment.expr, module.reset_signal):
                        lines.append(
                            f"      next_state.{_cpp_ident(assignment.target)} = "
                            f"value_mask({self._emit_wide_expr(assignment.expr, signal_map, memory_map)}, {target.width}u);"
                        )
                    else:
                        lines.append(
                            f"      next_state.{_cpp_ident(assignment.target)} = {self._emit_wide_const(target.init, target.width)};"
                        )
                for write in memory_writes:
                    memory = memory_map[write.memory]
                    if (
                        _expr_references_signal(write.addr, module.reset_signal)
                        or _expr_references_signal(write.value, module.reset_signal)
                        or _expr_references_signal(write.enable, module.reset_signal)
                        or (
                            write.byte_enable is not None
                            and _expr_references_signal(write.byte_enable, module.reset_signal)
                        )
                    ):
                        handled_memories.add(write.memory)
                        addr_expr = self._emit_wide_memory_addr(write.addr, signal_map, memory_map, memory)
                        enable_expr = self._emit_wide_expr(write.enable, signal_map, memory_map)
                        value_expr = self._emit_wide_expr(write.value, signal_map, memory_map)
                        lines.append(f"      if (value_nonzero({enable_expr})) {{")
                        if memory.byte_enable_granularity is None:
                            write_expr = f"value_mask({value_expr}, {memory.width}u)"
                        else:
                            assert write.byte_enable is not None
                            byte_enable_expr = self._emit_wide_expr(write.byte_enable, signal_map, memory_map)
                            write_expr = (
                                f"value_memory_byte_merge("
                                f"next_state.{_cpp_ident(write.memory)}[{addr_expr}], "
                                f"{value_expr}, "
                                f"{byte_enable_expr}, "
                                f"{memory.width}u, "
                                f"{memory.byte_enable_granularity}u)"
                            )
                        lines.append(
                            f"        next_state.{_cpp_ident(write.memory)}[{addr_expr}] = {write_expr};"
                        )
                        lines.append("      }")
                for memory in module.memories:
                    if memory.name in handled_memories:
                        continue
                    for idx, value in enumerate(memory.init):
                        lines.append(
                            f"      next_state.{_cpp_ident(memory.name)}[{idx}] = {self._emit_wide_const(value & memory.mask, memory.width)};"
                        )
                    if not memory.init:
                        lines.append(f"      for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
                        lines.append(
                            f"        next_state.{_cpp_ident(memory.name)}[idx] = {self._emit_wide_const(0, memory.width)};"
                        )
                        lines.append("      }")
                lines.append("    } else {")
                indent = "      "
            else:
                indent = "    "
            for assignment in seq_assignments:
                target = signal_map[assignment.target]
                lines.append(
                    f"{indent}next_state.{_cpp_ident(assignment.target)} = "
                    f"value_mask({self._emit_wide_expr(assignment.expr, signal_map, memory_map)}, {target.width}u);"
                )
            for write in memory_writes:
                memory = memory_map[write.memory]
                addr_expr = self._emit_wide_memory_addr(write.addr, signal_map, memory_map, memory)
                enable_expr = self._emit_wide_expr(write.enable, signal_map, memory_map)
                value_expr = self._emit_wide_expr(write.value, signal_map, memory_map)
                lines.append(f"{indent}if (value_nonzero({enable_expr})) {{")
                if memory.byte_enable_granularity is None:
                    write_expr = f"value_mask({value_expr}, {memory.width}u)"
                else:
                    assert write.byte_enable is not None
                    byte_enable_expr = self._emit_wide_expr(write.byte_enable, signal_map, memory_map)
                    write_expr = (
                        f"value_memory_byte_merge("
                        f"next_state.{_cpp_ident(write.memory)}[{addr_expr}], "
                        f"{value_expr}, "
                        f"{byte_enable_expr}, "
                        f"{memory.width}u, "
                        f"{memory.byte_enable_granularity}u)"
                    )
                lines.append(
                    f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = {write_expr};"
                )
                lines.append(f"{indent}}}")
            if module.reset_signal is not None:
                lines.append("    }")
        if module.outputs_post_state:
            lines.append("")
            read_first_memories = [memory for memory in module.memories if memory.read_during_write == "read_first"]
            if read_first_memories:
                lines.append(f"    {module_ident}State comb_state = next_state;")
                for write in memory_writes:
                    memory = memory_map[write.memory]
                    if memory.read_during_write != "read_first":
                        continue
                    addr_expr = self._emit_wide_memory_addr(write.addr, signal_map, memory_map, memory)
                    enable_expr = self._emit_wide_expr(write.enable, signal_map, memory_map)
                    lines.append(f"    if (value_nonzero({enable_expr})) {{")
                    lines.append(
                        f"      comb_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                        f"state_.{_cpp_ident(write.memory)}[{addr_expr}];"
                    )
                    lines.append("    }")
                lines.append("")
                lines.extend(emit_comb("    ", declare=False, state_expr="comb_state"))
            else:
                lines.extend(emit_comb("    ", declare=False, state_expr="next_state"))
        lines.extend([
            "",
            "    state_ = next_state;",
        ])
        lines.extend([
            "",
            f"    {module_ident}Outputs outputs;",
        ])
        for output_name in module.outputs:
            lines.append(f"    outputs.{_cpp_ident(output_name)} = {_cpp_value_name(output_name)};")
        lines.extend([
            "    return outputs;",
            "  }",
            "",
            "  void export_state(uint64_t* state_out) const {",
        ])
        state_signals = [signal for signal in module.signals if signal.kind == "state"]
        state_cursor = 0
        for signal in state_signals:
            word_count = _word_count(signal.width)
            lines.append(
                f"    value_to_words(state_.{_cpp_ident(signal.name)}, state_out + {state_cursor}u, {word_count}u, {signal.width}u);"
            )
            state_cursor += word_count
        for memory in module.memories:
            word_count = _word_count(memory.width)
            lines.append(f"    for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
            lines.append(
                f"      value_to_words(state_.{_cpp_ident(memory.name)}[idx], state_out + {state_cursor}u + idx * {word_count}u, {word_count}u, {memory.width}u);"
            )
            lines.append("    }")
            state_cursor += memory.depth * word_count
        lines.extend([
            "  }",
            "",
            "  void import_state(const uint64_t* state_in) {",
        ])
        state_cursor = 0
        for signal in state_signals:
            word_count = _word_count(signal.width)
            lines.append(
                f"    state_.{_cpp_ident(signal.name)} = value_mask(value_from_words(state_in + {state_cursor}u, {word_count}u), {signal.width}u);"
            )
            state_cursor += word_count
        for memory in module.memories:
            word_count = _word_count(memory.width)
            lines.append(f"    for (uint64_t idx = 0; idx < {memory.depth}u; ++idx) {{")
            lines.append(
                f"      state_.{_cpp_ident(memory.name)}[idx] = value_mask(value_from_words(state_in + {state_cursor}u + idx * {word_count}u, {word_count}u), {memory.width}u);"
            )
            lines.append("    }")
            state_cursor += memory.depth * word_count
        lines.extend([
            "  }",
            "",
            " private:",
            f"  {module_ident}State state_ = initial_state();",
            "};",
            "",
            f"}}  // namespace {self.namespace}",
            "",
        ])
        return "\n".join(lines)

    def _emit_wide_runtime_translation_unit(self, module: SimModule) -> str:
        module_ident = _cpp_ident(module.name)
        symbol_prefix = self._symbol_prefix(module)
        inputs = [signal for signal in module.signals if signal.kind == "input"]
        signal_map = module.signal_map()
        lines = [self._emit_wide_translation_unit(module)]
        lines.extend([
            'extern "C" {',
            "",
            f"void* {symbol_prefix}_create() {{",
            f"  return new {self.namespace}::{module_ident}Simulator();",
            "}",
            "",
            f"void {symbol_prefix}_destroy(void* handle) {{",
            f"  delete static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "}",
            "",
            f"void {symbol_prefix}_reset(void* handle) {{",
            f"  static_cast<{self.namespace}::{module_ident}Simulator*>(handle)->reset();",
            "}",
            "",
            f"void {symbol_prefix}_step(void* handle, const uint64_t* inputs, uint64_t* outputs) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            f"  {self.namespace}::{module_ident}Inputs in;",
        ])
        input_cursor = 0
        for signal in inputs:
            word_count = _word_count(signal.width)
            lines.append(
                f"  in.{_cpp_ident(signal.name)} = {self.namespace}::value_mask({self.namespace}::value_from_words(inputs + {input_cursor}u, {word_count}u), {signal.width}u);"
            )
            input_cursor += word_count
        lines.extend([
            "  auto result = simulator->step(in);",
        ])
        output_cursor = 0
        for output_name in module.outputs:
            signal = signal_map[output_name]
            word_count = _word_count(signal.width)
            lines.append(
                f"  {self.namespace}::value_to_words(result.{_cpp_ident(output_name)}, outputs + {output_cursor}u, {word_count}u, {signal.width}u);"
            )
            output_cursor += word_count
        lines.extend([
            "}",
            "",
            f"void {symbol_prefix}_step_domains(void* handle, uint64_t active_domains_mask, const uint64_t* inputs, uint64_t* outputs) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            f"  {self.namespace}::{module_ident}Inputs in;",
        ])
        input_cursor = 0
        for signal in inputs:
            word_count = _word_count(signal.width)
            lines.append(
                f"  in.{_cpp_ident(signal.name)} = {self.namespace}::value_mask({self.namespace}::value_from_words(inputs + {input_cursor}u, {word_count}u), {signal.width}u);"
            )
            input_cursor += word_count
        if module.clock_domains:
            lines.extend([
                "  auto result = simulator->step_domains(in, active_domains_mask);",
            ])
        else:
            lines.extend([
                "  auto result = simulator->step(in);",
            ])
        output_cursor = 0
        for output_name in module.outputs:
            signal = signal_map[output_name]
            word_count = _word_count(signal.width)
            lines.append(
                f"  {self.namespace}::value_to_words(result.{_cpp_ident(output_name)}, outputs + {output_cursor}u, {word_count}u, {signal.width}u);"
            )
            output_cursor += word_count
        lines.extend([
            "}",
            "",
            f"void {symbol_prefix}_step_many(",
            "    void* handle,",
            "    uint64_t cycles,",
            "    const uint64_t* inputs,",
            "    uint64_t* outputs) {",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  for (uint64_t cycle = 0; cycle < cycles; ++cycle) {",
            f"    {self.namespace}::{module_ident}Inputs in;",
        ])
        input_stride = sum(_word_count(signal.width) for signal in inputs)
        input_cursor = 0
        for signal in inputs:
            word_count = _word_count(signal.width)
            lines.append(
                f"    in.{_cpp_ident(signal.name)} = {self.namespace}::value_mask({self.namespace}::value_from_words(inputs + cycle * {input_stride}u + {input_cursor}u, {word_count}u), {signal.width}u);"
            )
            input_cursor += word_count
        lines.extend([
            "    auto result = simulator->step(in);",
        ])
        output_stride = sum(_word_count(signal_map[name].width) for name in module.outputs)
        output_cursor = 0
        for output_name in module.outputs:
            signal = signal_map[output_name]
            word_count = _word_count(signal.width)
            lines.append(
                f"    {self.namespace}::value_to_words(result.{_cpp_ident(output_name)}, outputs + cycle * {output_stride}u + {output_cursor}u, {word_count}u, {signal.width}u);"
            )
            output_cursor += word_count
        lines.extend([
            "  }",
            "}",
            "",
            f"void {symbol_prefix}_save_state(void* handle, uint64_t* state_out) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  simulator->export_state(state_out);",
            "}",
            "",
            f"void {symbol_prefix}_load_state(void* handle, const uint64_t* state_in) {{",
            f"  auto* simulator = static_cast<{self.namespace}::{module_ident}Simulator*>(handle);",
            "  simulator->import_state(state_in);",
            "}",
            "",
            "}  // extern \"C\"",
            "",
        ])
        return "\n".join(lines)

    def _emit_wide_const(self, value: int, width: int) -> str:
        words = [
            f"0x{((int(value) & _mask(width)) >> (64 * idx)) & 0xFFFFFFFFFFFFFFFF:016x}ull"
            for idx in range(_word_count(width))
        ]
        return f"value_mask(make_value<kStorageWords>({{{', '.join(words)}}}), {width}u)"

    def _emit_wide_expr(
        self,
        expr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
        *,
        state_expr: str = "state_",
    ) -> str:
        if isinstance(expr, ConstExpr):
            words = [
                f"0x{((expr.value & _mask(expr.width)) >> (64 * idx)) & 0xFFFFFFFFFFFFFFFF:016x}ull"
                for idx in range(_word_count(expr.width))
            ]
            return f"value_mask(make_value<kStorageWords>({{{', '.join(words)}}}), {expr.width}u)"
        if isinstance(expr, SignalRef):
            signal = signal_map[expr.name]
            if signal.kind == "input":
                return f"in.{_cpp_ident(expr.name)}"
            if signal.kind == "state":
                return f"{state_expr}.{_cpp_ident(expr.name)}"
            return _cpp_value_name(expr.name)
        if isinstance(expr, MemoryReadExpr):
            memory = memory_map[expr.memory]
            return (
                f"{state_expr}.{_cpp_ident(expr.memory)}"
                f"[{self._emit_wide_memory_addr(expr.addr, signal_map, memory_map, memory, state_expr=state_expr)}]"
            )
        if isinstance(expr, MaskExpr):
            return (
                f"value_mask({self._emit_wide_expr(expr.value, signal_map, memory_map, state_expr=state_expr)}, "
                f"{expr.width}u)"
            )
        if isinstance(expr, UnaryExpr):
            child_width = _infer_expr_width(expr.value, signal_map, memory_map)
            child_expr = self._emit_wide_expr(expr.value, signal_map, memory_map, state_expr=state_expr)
            if expr.op == "!":
                return f"value_bool(!value_nonzero({child_expr}))"
            if expr.op == "$signed":
                return f"value_sign_extend(value_mask({child_expr}, {child_width}u), {child_width}u)"
            if expr.op == "$unsigned":
                return f"value_mask({child_expr}, {child_width}u)"
            if expr.op == "~":
                return f"value_mask(value_not({child_expr}), {child_width}u)"
            if expr.op == "-":
                return f"value_neg({child_expr})"
            return child_expr
        if isinstance(expr, BinaryExpr):
            lhs_expr = self._emit_wide_expr(expr.lhs, signal_map, memory_map, state_expr=state_expr)
            rhs_expr = self._emit_wide_expr(expr.rhs, signal_map, memory_map, state_expr=state_expr)
            lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
            rhs_width = _infer_expr_width(expr.rhs, signal_map, memory_map)
            signed_arith = _expr_is_signed(expr.lhs, signal_map, memory_map) or _expr_is_signed(
                expr.rhs, signal_map, memory_map
            )
            if expr.op == "+":
                if signed_arith:
                    return f"value_add_signed({lhs_expr}, {rhs_expr}, {lhs_width}u, {rhs_width}u)"
                return f"value_add({lhs_expr}, {rhs_expr})"
            if expr.op == "-":
                if signed_arith:
                    return f"value_sub_signed({lhs_expr}, {rhs_expr}, {lhs_width}u, {rhs_width}u)"
                return f"value_sub({lhs_expr}, {rhs_expr})"
            if expr.op == "*":
                if signed_arith:
                    return f"value_mul_signed({lhs_expr}, {rhs_expr}, {lhs_width}u, {rhs_width}u)"
                return f"value_mul({lhs_expr}, {rhs_expr})"
            if expr.op == "&":
                return f"value_and({lhs_expr}, {rhs_expr})"
            if expr.op == "|":
                return f"value_or({lhs_expr}, {rhs_expr})"
            if expr.op == "^":
                return f"value_xor({lhs_expr}, {rhs_expr})"
            if expr.op == "<<":
                return f"value_shl({lhs_expr}, value_to_size({rhs_expr}))"
            if expr.op == ">>":
                lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
                masked_lhs = f"value_mask({lhs_expr}, {lhs_width}u)"
                shift_expr = f"value_to_size({rhs_expr})"
                if _expr_is_signed(expr.lhs, signal_map, memory_map):
                    signed_lhs = f"value_sign_extend({masked_lhs}, {lhs_width}u)"
                    return f"value_ashr({signed_lhs}, {shift_expr})"
                return f"value_lshr({masked_lhs}, {shift_expr})"
            if expr.op == ">>>":
                lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
                masked_lhs = f"value_mask({lhs_expr}, {lhs_width}u)"
                shift_expr = f"value_to_size({rhs_expr})"
                if _expr_is_signed(expr.lhs, signal_map, memory_map):
                    signed_lhs = f"value_sign_extend({masked_lhs}, {lhs_width}u)"
                    return f"value_ashr({signed_lhs}, {shift_expr})"
                return f"value_lshr({masked_lhs}, {shift_expr})"
            if expr.op == "==":
                return f"value_bool(value_cmp_unsigned({lhs_expr}, {rhs_expr}) == 0)"
            if expr.op == "!=":
                return f"value_bool(value_cmp_unsigned({lhs_expr}, {rhs_expr}) != 0)"
            compare_fn = (
                "value_cmp_signed"
                if _expr_is_signed(expr.lhs, signal_map, memory_map)
                or _expr_is_signed(expr.rhs, signal_map, memory_map)
                else "value_cmp_unsigned"
            )
            if expr.op == "<":
                return f"value_bool({compare_fn}({lhs_expr}, {rhs_expr}) < 0)"
            if expr.op == "<=":
                return f"value_bool({compare_fn}({lhs_expr}, {rhs_expr}) <= 0)"
            if expr.op == ">":
                return f"value_bool({compare_fn}({lhs_expr}, {rhs_expr}) > 0)"
            if expr.op == ">=":
                return f"value_bool({compare_fn}({lhs_expr}, {rhs_expr}) >= 0)"
        if isinstance(expr, MuxExpr):
            return (
                f"value_select(value_nonzero({self._emit_wide_expr(expr.cond, signal_map, memory_map, state_expr=state_expr)}), "
                f"{self._emit_wide_expr(expr.when_true, signal_map, memory_map, state_expr=state_expr)}, "
                f"{self._emit_wide_expr(expr.when_false, signal_map, memory_map, state_expr=state_expr)})"
            )
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _emit_wide_memory_addr(
        self,
        addr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
        memory: Memory,
        *,
        state_expr: str = "state_",
    ) -> str:
        return (
            f"(value_to_size({self._emit_wide_expr(addr, signal_map, memory_map, state_expr=state_expr)}) "
            f"% {memory.depth}u)"
        )

    def build(self, module: SimModule, build_dir: Optional[Path | str] = None) -> CompiledSimulator:
        compiler = self._resolve_compiler()
        tempdir: Optional[tempfile.TemporaryDirectory] = None
        if build_dir is None:
            tempdir = tempfile.TemporaryDirectory(prefix=f"rtlgen_x_{_cpp_ident(module.name)}_")
            artifact_dir = Path(tempdir.name)
        else:
            artifact_dir = Path(build_dir)
            artifact_dir.mkdir(parents=True, exist_ok=True)

        source_path = artifact_dir / f"{_cpp_ident(module.name)}_sim.cc"
        library_path = artifact_dir / self._library_name(module)
        source_path.write_text(self.emit_runtime_translation_unit(module))

        command = self._compile_command(compiler, source_path, library_path)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if tempdir is not None:
                tempdir.cleanup()
            message = (
                f"compiled simulator build failed for module '{module.name}'\n"
                f"command: {' '.join(command)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
            raise CppBuildError(message)

        try:
            library = ctypes.CDLL(str(library_path))
            symbol_prefix = self._symbol_prefix(module)
            create_fn = getattr(library, f"{symbol_prefix}_create")
            destroy_fn = getattr(library, f"{symbol_prefix}_destroy")
            reset_fn = getattr(library, f"{symbol_prefix}_reset")
            step_fn = getattr(library, f"{symbol_prefix}_step")
            step_domains_fn = getattr(library, f"{symbol_prefix}_step_domains")
            step_many_fn = getattr(library, f"{symbol_prefix}_step_many")
            save_state_fn = getattr(library, f"{symbol_prefix}_save_state")
            load_state_fn = getattr(library, f"{symbol_prefix}_load_state")
        except (AttributeError, OSError) as exc:
            if tempdir is not None:
                tempdir.cleanup()
            raise CppBuildError(f"failed to load compiled simulator runtime: {exc}") from exc

        create_fn.restype = ctypes.c_void_p
        destroy_fn.argtypes = [ctypes.c_void_p]
        destroy_fn.restype = None
        reset_fn.argtypes = [ctypes.c_void_p]
        reset_fn.restype = None
        step_fn.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64),
        ]
        step_fn.restype = None
        step_domains_fn.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64),
        ]
        step_domains_fn.restype = None
        step_many_fn.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64),
        ]
        step_many_fn.restype = None
        save_state_fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
        save_state_fn.restype = None
        load_state_fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
        load_state_fn.restype = None

        handle = create_fn()
        if not handle:
            if tempdir is not None:
                tempdir.cleanup()
            raise CppBuildError("compiled simulator returned a null instance handle")

        input_signals = [signal for signal in module.signals if signal.kind == "input"]
        output_signals = [module.signal_map()[name] for name in module.outputs]
        state_signals = [signal for signal in module.signals if signal.kind == "state"]
        state_widths = [signal.width for signal in state_signals]
        state_names = [signal.name for signal in state_signals]
        for memory in module.memories:
            state_names.extend(f"{memory.name}[{idx}]" for idx in range(memory.depth))
            state_widths.extend([memory.width] * memory.depth)
        return CompiledSimulator(
            library=library,
            handle=handle,
            destroy_fn=destroy_fn,
            reset_fn=reset_fn,
            step_fn=step_fn,
            step_domains_fn=step_domains_fn,
            step_many_fn=step_many_fn,
            save_state_fn=save_state_fn,
            load_state_fn=load_state_fn,
            input_names=[signal.name for signal in input_signals],
            input_widths=[signal.width for signal in input_signals],
            output_names=list(module.outputs),
            output_widths=[signal.width for signal in output_signals],
            state_names=state_names,
            state_widths=state_widths,
            clock_domain_names=[domain.name for domain in module.clock_domains],
            clock_domain_aliases={
                domain.name: tuple(domain.aliases)
                for domain in module.clock_domains
                if domain.aliases
            },
            artifact_dir=artifact_dir,
            source_path=source_path,
            library_path=library_path,
            tempdir=tempdir,
        )

    def _emit_expr(
        self,
        expr: Expr,
        signal_map: Dict[str, Signal],
        memory_map: Dict[str, Memory],
        *,
        state_expr: str = "state_",
    ) -> str:
        if isinstance(expr, ConstExpr):
            return f"{expr.value & _mask(expr.width)}u"
        if isinstance(expr, SignalRef):
            signal = signal_map[expr.name]
            if signal.kind == "input":
                return f"in.{_cpp_ident(expr.name)}"
            if signal.kind == "state":
                return f"{state_expr}.{_cpp_ident(expr.name)}"
            return _cpp_value_name(expr.name)
        if isinstance(expr, MemoryReadExpr):
            memory = memory_map[expr.memory]
            return (
                f"{state_expr}.{_cpp_ident(expr.memory)}"
                f"[{self._emit_memory_addr(expr.addr, signal_map, memory, memory_map, state_expr=state_expr)}]"
            )
        if isinstance(expr, MaskExpr):
            return (
                f"(({self._emit_expr(expr.value, signal_map, memory_map, state_expr=state_expr)}) "
                f"& {_mask_expr(expr.width)})"
            )
        if isinstance(expr, UnaryExpr):
            child_width = _infer_expr_width(expr.value, signal_map, memory_map)
            child_expr = self._emit_expr(expr.value, signal_map, memory_map, state_expr=state_expr)
            if expr.op == "!":
                return f"(!({child_expr}))"
            if expr.op == "$signed":
                return _sign_extend_expr(child_expr, child_width)
            if expr.op == "$unsigned":
                return f"(uint64_t({child_expr}) & {_mask_expr(child_width)})"
            if expr.op == "~":
                width = _infer_expr_width(expr, signal_map, memory_map)
                return (
                    f"((~({child_expr})) & "
                    f"{_mask_expr(width)})"
                )
            return f"({expr.op}({child_expr}))"
        if isinstance(expr, BinaryExpr):
            if expr.op == ">>>":
                lhs_src = self._emit_expr(expr.lhs, signal_map, memory_map, state_expr=state_expr)
                rhs_src = self._emit_expr(expr.rhs, signal_map, memory_map, state_expr=state_expr)
                if not _expr_is_signed(expr.lhs, signal_map, memory_map):
                    return f"(uint64_t({lhs_src}) >> ({rhs_src}))"
                lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
                masked_lhs = f"(uint64_t({lhs_src}) & {_mask_expr(lhs_width)})"
                signed_lhs = _sign_extend_expr(masked_lhs, lhs_width)
                return f"(uint64_t(({signed_lhs}) >> ({rhs_src})))"
            lhs_src = self._emit_expr(expr.lhs, signal_map, memory_map, state_expr=state_expr)
            rhs_src = self._emit_expr(expr.rhs, signal_map, memory_map, state_expr=state_expr)
            lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
            rhs_width = _infer_expr_width(expr.rhs, signal_map, memory_map)
            lhs_signed = _expr_is_signed(expr.lhs, signal_map, memory_map)
            rhs_signed = _expr_is_signed(expr.rhs, signal_map, memory_map)
            signed_context = lhs_signed or rhs_signed
            lhs_num = _scalar_numeric_operand_expr(
                lhs_src,
                lhs_width,
                signed=lhs_signed,
                signed_context=signed_context,
            )
            rhs_num = _scalar_numeric_operand_expr(
                rhs_src,
                rhs_width,
                signed=rhs_signed,
                signed_context=signed_context,
            )
            if expr.op in {"+", "-", "*"}:
                if signed_context:
                    return f"(uint64_t(static_cast<__int128>({lhs_num} {expr.op} {rhs_num})))"
                return f"(uint64_t(static_cast<unsigned __int128>({lhs_num} {expr.op} {rhs_num})))"
            if expr.op in {"<", "<=", ">", ">="}:
                return f"(({lhs_num}) {expr.op} ({rhs_num}))"
            if expr.op in {"==", "!="}:
                lhs_cmp = _masked_scalar_expr(lhs_src, lhs_width)
                rhs_cmp = _masked_scalar_expr(rhs_src, rhs_width)
                return f"(({lhs_cmp}) {expr.op} ({rhs_cmp}))"
            return (
                f"(({lhs_src}) "
                f"{expr.op} "
                f"({rhs_src}))"
            )
        if isinstance(expr, MuxExpr):
            return (
                f"(({self._emit_expr(expr.cond, signal_map, memory_map, state_expr=state_expr)}) ? "
                f"({self._emit_expr(expr.when_true, signal_map, memory_map, state_expr=state_expr)}) : "
                f"({self._emit_expr(expr.when_false, signal_map, memory_map, state_expr=state_expr)}))"
            )
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _emit_memory_addr(
        self,
        addr: Expr,
        signal_map: Dict[str, Signal],
        memory: Memory,
        memory_map: Optional[Dict[str, Memory]] = None,
        *,
        state_expr: str = "state_",
    ) -> str:
        backing_memory_map = memory_map if memory_map is not None else {}
        expr = self._emit_expr(addr, signal_map, backing_memory_map, state_expr=state_expr)
        return f"(({expr}) % {memory.depth}u)"

    def _library_name(self, module: SimModule) -> str:
        stem = f"lib{_cpp_ident(module.name)}_sim"
        if sys.platform == "darwin":
            return f"{stem}.dylib"
        return f"{stem}.so"

    def _resolve_compiler(self) -> str:
        if self.compiler is not None:
            return self.compiler
        for candidate in ("clang++", "g++", "c++"):
            resolved = shutil.which(candidate)
            if resolved is not None:
                return resolved
        raise CppBuildError("no C++ compiler found; expected clang++, g++, or c++")

    def _compile_command(self, compiler: str, source_path: Path, library_path: Path) -> List[str]:
        command = [compiler, *self.cxxflags]
        if sys.platform == "darwin":
            command.extend(self._darwin_sdk_flags())
            command.extend(["-dynamiclib", str(source_path), "-o", str(library_path)])
        else:
            command.extend(["-shared", "-fPIC", str(source_path), "-o", str(library_path)])
        return command

    def _symbol_prefix(self, module: SimModule) -> str:
        return f"{_cpp_ident(self.namespace)}_{_cpp_ident(module.name)}"

    def _darwin_sdk_flags(self) -> List[str]:
        try:
            result = subprocess.run(
                ["xcrun", "--show-sdk-path"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []
        if result.returncode != 0:
            return []
        sdk_path = result.stdout.strip()
        if not sdk_path:
            return []
        flags = ["-isysroot", sdk_path]
        libcxx_headers = Path(sdk_path) / "usr/include/c++/v1"
        if libcxx_headers.exists():
            flags.extend(["-isystem", str(libcxx_headers)])
        return flags
