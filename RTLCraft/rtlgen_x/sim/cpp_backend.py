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
        if self.width < 1 or self.width > 64:
            raise ValueError("signal width must be in [1, 64]")
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

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("memory name must not be empty")
        if self.width < 1 or self.width > 64:
            raise ValueError("memory width must be in [1, 64]")
        if self.depth < 1:
            raise ValueError("memory depth must be positive")
        if self.init and len(self.init) != self.depth:
            raise ValueError("memory init must be empty or match depth")

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    @property
    def addr_width(self) -> int:
        return max((self.depth - 1).bit_length(), 1)


@dataclass(frozen=True)
class ConstExpr:
    value: int
    width: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.width > 64:
            raise ValueError("const width must be in [1, 64]")


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
        if self.width < 1 or self.width > 64:
            raise ValueError("mask width must be in [1, 64]")


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
    """Local executable module description for the compiled simulator."""

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
            signal = signal_map.get(self.reset_signal)
            if signal is None:
                raise ValueError(f"unknown reset signal '{self.reset_signal}'")
            if signal.kind != "input":
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


def _cpp_ident(name: str) -> str:
    chars = [c if c.isalnum() or c == "_" else "_" for c in name]
    ident = "".join(chars)
    if ident and (ident[0].isalpha() or ident[0] == "_"):
        return ident
    return f"sig_{ident}"


def _cpp_value_name(name: str) -> str:
    return f"value_{_cpp_ident(name)}"


def _mask(width: int) -> int:
    return (1 << width) - 1


def _mask_expr(width: int) -> str:
    if width == 64:
        return "UINT64_MAX"
    return f"((uint64_t(1) << {width}) - 1u)"


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
        self.input_names = tuple(input_names)
        self.output_names = tuple(output_names)
        self.state_names = tuple(state_names)
        self.input_count = len(self.input_names)
        self.output_count = len(self.output_names)
        self.state_count = len(self.state_names)
        self._input_masks = tuple(_mask(width) for width in input_widths)
        self._output_masks = tuple(_mask(width) for width in output_widths)
        self._state_masks = tuple(_mask(width) for width in state_widths)
        self._step_input_buffer = (ctypes.c_uint64 * self.input_count)()
        self._step_output_buffer = (ctypes.c_uint64 * self.output_count)()
        self._state_buffer = np.zeros(self.state_count, dtype=np.uint64)
        self.artifact_dir = artifact_dir
        self.source_path = source_path
        self.library_path = library_path
        self._tempdir = tempdir
        self._input_index = {name: idx for idx, name in enumerate(self.input_names)}

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
        if len(input_values) != self.input_count:
            raise ValueError(f"expected {self.input_count} input values, got {len(input_values)}")
        for idx, raw_value in enumerate(input_values):
            self._step_input_buffer[idx] = int(raw_value) & self._input_masks[idx]
        self._step_fn(self._handle, self._step_input_buffer, self._step_output_buffer)
        return tuple(
            int(self._step_output_buffer[idx]) & self._output_masks[idx]
            for idx in range(self.output_count)
        )

    def run_batch_raw(self, flat_inputs: Sequence[int], cycles: int) -> Tuple[int, ...]:
        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
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
        flat_inputs: Union[array, np.ndarray],
        cycles: int,
        output_buffer: Optional[Union[array, np.ndarray]] = None,
    ) -> Union[array, np.ndarray]:
        """Run a packed batch using reusable unsigned-64 buffers."""

        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if cycles < 0:
            raise ValueError("cycles must be non-negative")
        expected_values = cycles * self.input_count
        if len(flat_inputs) != expected_values:
            raise ValueError(
                f"expected {expected_values} flattened input values, got {len(flat_inputs)}"
            )
        total_outputs = cycles * self.output_count
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

        if input_rows.dtype != np.uint64:
            raise TypeError("input_rows must have dtype=uint64")
        if input_rows.ndim != 2:
            raise TypeError("input_rows must be a 2D numpy array")
        if input_rows.shape[1] != self.input_count:
            raise ValueError(
                f"expected input_rows.shape[1] == {self.input_count}, got {input_rows.shape[1]}"
            )
        if not input_rows.flags.c_contiguous:
            raise TypeError("input_rows must be C-contiguous")
        cycles = int(input_rows.shape[0])
        if output_buffer is None:
            output_buffer = np.zeros((cycles, self.output_count), dtype=np.uint64)
        else:
            if output_buffer.dtype != np.uint64:
                raise TypeError("output_buffer must have dtype=uint64")
            if output_buffer.ndim != 2:
                raise TypeError("output_buffer must be a 2D numpy array")
            if output_buffer.shape != (cycles, self.output_count):
                raise ValueError(
                    f"expected output_buffer.shape == {(cycles, self.output_count)}, got {output_buffer.shape}"
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

    def restore_state_numpy(self, state: np.ndarray) -> None:
        """Restore the simulator state from a uint64 numpy snapshot."""

        if self._handle is None:
            raise RuntimeError("compiled simulator is closed")
        if state.dtype != np.uint64:
            raise TypeError("state must have dtype=uint64")
        if state.ndim != 1:
            raise TypeError("state must be a 1D numpy array")
        if len(state) != self.state_count:
            raise ValueError(f"expected state length {self.state_count}, got {len(state)}")
        if not state.flags.c_contiguous:
            state = np.ascontiguousarray(state)
        self._load_state_fn(
            self._handle,
            state.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)),
        )

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

    def emit_translation_unit(self, module: SimModule) -> str:
        signal_map = module.signal_map()
        memory_map = module.memory_map()
        module_ident = _cpp_ident(module.name)
        wire_output_signals = [
            signal for signal in module.signals if signal.kind in {"wire", "output"}
        ]
        comb_assignments = [a for a in module.assignments if a.phase == "comb"]
        seq_assignments = [a for a in module.assignments if a.phase == "seq"]
        memory_writes = list(module.memory_writes)

        def emit_comb(indent: str, *, declare: bool) -> List[str]:
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
                    f"({self._emit_expr(assignment.expr, signal_map, memory_map)}) & {_mask_expr(target.width)};"
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
            f"    {module_ident}State next_state = state_;",
        ])
        lines.extend(emit_comb("    ", declare=True))
        if seq_assignments or memory_writes:
            lines.append("")
            if module.reset_signal is not None:
                lines.append(f"    if (in.{_cpp_ident(module.reset_signal)}) {{")
                lines.append("      next_state = initial_state();")
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
                lines.append(f"{indent}if ({enable_expr}) {{")
                lines.append(
                    f"{indent}  next_state.{_cpp_ident(write.memory)}[{addr_expr}] = "
                    f"({self._emit_expr(write.value, signal_map, memory_map)}) & {_mask_expr(memory.width)};"
                )
                lines.append(f"{indent}}}")
            if module.reset_signal is not None:
                lines.append("    }")
        lines.extend([
            "",
            "    state_ = next_state;",
        ])
        if module.outputs_post_state:
            lines.append("")
            lines.extend(emit_comb("    ", declare=False))
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
            step_many_fn=step_many_fn,
            save_state_fn=save_state_fn,
            load_state_fn=load_state_fn,
            input_names=[signal.name for signal in input_signals],
            input_widths=[signal.width for signal in input_signals],
            output_names=list(module.outputs),
            output_widths=[signal.width for signal in output_signals],
            state_names=state_names,
            state_widths=state_widths,
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
    ) -> str:
        if isinstance(expr, ConstExpr):
            return f"{expr.value & _mask(expr.width)}u"
        if isinstance(expr, SignalRef):
            signal = signal_map[expr.name]
            if signal.kind == "input":
                return f"in.{_cpp_ident(expr.name)}"
            if signal.kind == "state":
                return f"state_.{_cpp_ident(expr.name)}"
            return _cpp_value_name(expr.name)
        if isinstance(expr, MemoryReadExpr):
            memory = memory_map[expr.memory]
            return (
                f"state_.{_cpp_ident(expr.memory)}"
                f"[{self._emit_memory_addr(expr.addr, signal_map, memory, memory_map)}]"
            )
        if isinstance(expr, MaskExpr):
            return f"(({self._emit_expr(expr.value, signal_map, memory_map)}) & {_mask_expr(expr.width)})"
        if isinstance(expr, UnaryExpr):
            if expr.op == "!":
                return f"(!({self._emit_expr(expr.value, signal_map, memory_map)}))"
            if expr.op == "$signed":
                return f"(int64_t({self._emit_expr(expr.value, signal_map, memory_map)}))"
            if expr.op == "$unsigned":
                return f"(uint64_t({self._emit_expr(expr.value, signal_map, memory_map)}))"
            if expr.op == "~":
                width = _infer_expr_width(expr, signal_map, memory_map)
                return (
                    f"((~({self._emit_expr(expr.value, signal_map, memory_map)})) & "
                    f"{_mask_expr(width)})"
                )
            return f"({expr.op}({self._emit_expr(expr.value, signal_map, memory_map)}))"
        if isinstance(expr, BinaryExpr):
            if expr.op == ">>>":
                lhs_src = self._emit_expr(expr.lhs, signal_map, memory_map)
                rhs_src = self._emit_expr(expr.rhs, signal_map, memory_map)
                if not _expr_is_signed(expr.lhs, signal_map, memory_map):
                    return f"(uint64_t({lhs_src}) >> ({rhs_src}))"
                lhs_width = _infer_expr_width(expr.lhs, signal_map, memory_map)
                masked_lhs = f"(uint64_t({lhs_src}) & {_mask_expr(lhs_width)})"
                if lhs_width == 64:
                    signed_lhs = f"int64_t({masked_lhs})"
                else:
                    sign_bit = f"(uint64_t(1) << {lhs_width - 1})"
                    signed_lhs = f"int64_t(({masked_lhs} ^ {sign_bit}) - {sign_bit})"
                return f"(uint64_t(({signed_lhs}) >> ({rhs_src})))"
            return (
                f"(({self._emit_expr(expr.lhs, signal_map, memory_map)}) "
                f"{expr.op} "
                f"({self._emit_expr(expr.rhs, signal_map, memory_map)}))"
            )
        if isinstance(expr, MuxExpr):
            return (
                f"(({self._emit_expr(expr.cond, signal_map, memory_map)}) ? "
                f"({self._emit_expr(expr.when_true, signal_map, memory_map)}) : "
                f"({self._emit_expr(expr.when_false, signal_map, memory_map)}))"
            )
        raise TypeError(f"unsupported expression type: {type(expr)!r}")

    def _emit_memory_addr(
        self,
        addr: Expr,
        signal_map: Dict[str, Signal],
        memory: Memory,
        memory_map: Optional[Dict[str, Memory]] = None,
    ) -> str:
        backing_memory_map = memory_map if memory_map is not None else {}
        expr = self._emit_expr(addr, signal_map, backing_memory_map)
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
