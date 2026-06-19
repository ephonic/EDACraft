"""Benchmark helpers for comparing Python and compiled simulator performance."""

from __future__ import annotations

import time
from array import array
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional, Sequence, Tuple

from rtlgen_x.sim.cpp_backend import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    CppBackendScaffold,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
    pack_u64_words,
)
from rtlgen_x.sim.python_runtime import PythonSimulator


@dataclass(frozen=True)
class SimulatorBenchmarkReport:
    """Measured runtime and speedup for Python vs compiled simulation."""

    module_name: str
    cycles: int
    compile_seconds: float
    python_step_seconds: float
    cpp_step_seconds: float
    python_batch_seconds: float
    cpp_batch_seconds: float
    step_speedup: float
    batch_speedup: float


@dataclass(frozen=True)
class StreamingBenchmarkReport:
    """Measured throughput and bounded-buffer footprint for streamed batches."""

    module_name: str
    cycles: int
    chunk_cycles: int
    compile_seconds: float
    chunk_input_bytes: int
    chunk_output_bytes: int
    python_stream_seconds: float
    cpp_stream_seconds: float
    stream_speedup: float
    checksum: int


def build_stress_module(width: int = 32) -> SimModule:
    """Create a moderately arithmetic-heavy stateful module for benchmarking."""

    if width < 2 or width > 64:
        raise ValueError("width must be in [2, 64]")
    signals = (
        Signal("sel", width=1, kind="input"),
        Signal("inp0", width=width, kind="input"),
        Signal("inp1", width=width, kind="input"),
        Signal("inp2", width=width, kind="input"),
        Signal("inp3", width=width, kind="input"),
        Signal("s0", width=width, kind="state", init=0x11),
        Signal("s1", width=width, kind="state", init=0x23),
        Signal("s2", width=width, kind="state", init=0x37),
        Signal("s3", width=width, kind="state", init=0x41),
        Signal("s4", width=width, kind="state", init=0x53),
        Signal("s5", width=width, kind="state", init=0x67),
        Signal("s6", width=width, kind="state", init=0x79),
        Signal("s7", width=width, kind="state", init=0x8D),
        Signal("w0", width=width, kind="wire"),
        Signal("w1", width=width, kind="wire"),
        Signal("w2", width=width, kind="wire"),
        Signal("w3", width=width, kind="wire"),
        Signal("w4", width=width, kind="wire"),
        Signal("w5", width=width, kind="wire"),
        Signal("w6", width=width, kind="wire"),
        Signal("w7", width=width, kind="wire"),
        Signal("w8", width=width, kind="wire"),
        Signal("w9", width=width, kind="wire"),
        Signal("w10", width=width, kind="wire"),
        Signal("w11", width=width, kind="wire"),
        Signal("w12", width=width, kind="wire"),
        Signal("w13", width=width, kind="wire"),
        Signal("w14", width=width, kind="wire"),
        Signal("out0", width=width, kind="output"),
        Signal("out1", width=width, kind="output"),
    )
    assignments = (
        Assignment("w0", BinaryExpr("+", SignalRef("s0"), SignalRef("inp0"))),
        Assignment("w1", BinaryExpr("^", SignalRef("s1"), SignalRef("inp1"))),
        Assignment(
            "w2",
            BinaryExpr(
                "*",
                SignalRef("w0"),
                BinaryExpr("+", SignalRef("inp2"), ConstExpr(1, width)),
            ),
        ),
        Assignment("w3", BinaryExpr("+", SignalRef("w2"), SignalRef("w1"))),
        Assignment(
            "w4",
            MuxExpr(
                SignalRef("sel"),
                SignalRef("w3"),
                BinaryExpr("+", SignalRef("s2"), SignalRef("inp3")),
            ),
        ),
        Assignment("w5", BinaryExpr("^", SignalRef("w4"), SignalRef("s3"))),
        Assignment("w6", BinaryExpr("+", SignalRef("w5"), SignalRef("s4"))),
        Assignment("w7", BinaryExpr("*", SignalRef("w6"), ConstExpr(3, width))),
        Assignment("w8", BinaryExpr("+", SignalRef("w7"), SignalRef("s5"))),
        Assignment("w9", BinaryExpr("^", SignalRef("w8"), SignalRef("inp0"))),
        Assignment("w10", MuxExpr(SignalRef("sel"), SignalRef("w9"), SignalRef("w6"))),
        Assignment("w11", BinaryExpr("+", SignalRef("w10"), SignalRef("s6"))),
        Assignment("w12", BinaryExpr("*", SignalRef("w11"), ConstExpr(5, width))),
        Assignment("w13", BinaryExpr("+", SignalRef("w12"), SignalRef("w4"))),
        Assignment("w14", BinaryExpr("^", SignalRef("w13"), SignalRef("s7"))),
        Assignment("out0", BinaryExpr("+", SignalRef("w14"), SignalRef("inp1"))),
        Assignment("out1", BinaryExpr("^", SignalRef("w10"), SignalRef("inp2"))),
        Assignment("s0", SignalRef("w4"), phase="seq"),
        Assignment("s1", SignalRef("w5"), phase="seq"),
        Assignment("s2", SignalRef("w6"), phase="seq"),
        Assignment("s3", SignalRef("w7"), phase="seq"),
        Assignment("s4", SignalRef("w8"), phase="seq"),
        Assignment("s5", SignalRef("w9"), phase="seq"),
        Assignment("s6", SignalRef("out0"), phase="seq"),
        Assignment("s7", SignalRef("out1"), phase="seq"),
    )
    return SimModule(
        name=f"stress_{width}",
        signals=signals,
        assignments=assignments,
        outputs=("out0", "out1"),
    )


def iter_stress_input_rows(module: SimModule, cycles: int, seed: int = 1) -> Iterator[Tuple[int, ...]]:
    """Generate deterministic row-wise input vectors lazily."""

    if cycles < 0:
        raise ValueError("cycles must be non-negative")
    if seed == 0:
        seed = 1
    signal_map = module.signal_map()
    input_names = [signal.name for signal in module.signals if signal.kind == "input"]
    input_signals = [signal_map[name] for name in input_names]
    state = seed & 0xFFFFFFFFFFFFFFFF
    for cycle in range(cycles):
        row = []
        for idx, signal in enumerate(input_signals):
            state ^= (state << 7) & 0xFFFFFFFFFFFFFFFF
            state ^= state >> 9
            state ^= (state << 8) & 0xFFFFFFFFFFFFFFFF
            if signal.width == 1:
                row.append((state >> (cycle + idx)) & 1)
            else:
                row.append(state & signal.mask)
        yield tuple(row)


def generate_stress_inputs(module: SimModule, cycles: int, seed: int = 1) -> Tuple[int, ...]:
    """Generate deterministic row-major input vectors for benchmark repeats."""

    flat_values = []
    for row in iter_stress_input_rows(module, cycles, seed):
        flat_values.extend(row)
    return tuple(flat_values)


def generate_stress_input_buffer(module: SimModule, cycles: int, seed: int = 1) -> array:
    """Generate deterministic packed input vectors for zero-copy batch runs."""

    flat_values = array("Q")
    for row in iter_stress_input_rows(module, cycles, seed):
        flat_values.extend(row)
    return flat_values


def benchmark_compiled_speedup(
    module: SimModule,
    flat_inputs: Sequence[int],
    cycles: int,
    *,
    repeats: int = 5,
    warmup: int = 1,
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
) -> SimulatorBenchmarkReport:
    """Benchmark step-wise and packed-batch simulation speed for Python and C++ paths."""

    if repeats < 1:
        raise ValueError("repeats must be positive")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")

    runtime_builder = builder if builder is not None else CppBackendScaffold()
    python_sim = PythonSimulator(module)
    step_rows = _split_rows(flat_inputs, cycles, python_sim.input_count)
    packed_inputs = flat_inputs if isinstance(flat_inputs, array) else pack_u64_words(flat_inputs)
    total_outputs = cycles * python_sim.output_count
    python_output_buffer = array("Q", [0]) * total_outputs
    cpp_output_buffer = array("Q", [0]) * total_outputs

    compile_start = time.perf_counter()
    cpp_sim = runtime_builder.build(module, build_dir)
    compile_seconds = time.perf_counter() - compile_start
    try:
        python_sim.reset()
        python_outputs = python_sim.run_batch_buffered(packed_inputs, cycles, python_output_buffer)
        cpp_sim.reset()
        cpp_outputs = cpp_sim.run_batch_buffered(packed_inputs, cycles, cpp_output_buffer)
        if tuple(python_outputs) != tuple(cpp_outputs):
            raise AssertionError("python and compiled simulator traces diverged")

        for _ in range(warmup):
            python_sim.reset()
            python_sim.run_batch_buffered(packed_inputs, cycles, python_output_buffer)
            cpp_sim.reset()
            cpp_sim.run_batch_buffered(packed_inputs, cycles, cpp_output_buffer)

        python_step_seconds = _measure_min(
            repeats,
            lambda: _run_python_step_loop(python_sim, step_rows),
        )
        cpp_step_seconds = _measure_min(
            repeats,
            lambda: _run_cpp_step_loop(cpp_sim, step_rows),
        )
        python_batch_seconds = _measure_min(
            repeats,
            lambda: _run_python_batch(python_sim, packed_inputs, cycles, python_output_buffer),
        )
        cpp_batch_seconds = _measure_min(
            repeats,
            lambda: _run_cpp_batch(cpp_sim, packed_inputs, cycles, cpp_output_buffer),
        )
    finally:
        cpp_sim.close()

    return SimulatorBenchmarkReport(
        module_name=module.name,
        cycles=cycles,
        compile_seconds=compile_seconds,
        python_step_seconds=python_step_seconds,
        cpp_step_seconds=cpp_step_seconds,
        python_batch_seconds=python_batch_seconds,
        cpp_batch_seconds=cpp_batch_seconds,
        step_speedup=python_step_seconds / cpp_step_seconds,
        batch_speedup=python_batch_seconds / cpp_batch_seconds,
    )


def benchmark_streaming_capacity(
    module: SimModule,
    row_factory: Callable[[], Iterable[Sequence[int]]],
    cycles: int,
    *,
    chunk_cycles: int = 65536,
    repeats: int = 3,
    warmup: int = 1,
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
) -> StreamingBenchmarkReport:
    """Benchmark chunked streaming throughput with bounded in-flight buffers."""

    if repeats < 1:
        raise ValueError("repeats must be positive")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")
    if chunk_cycles < 1:
        raise ValueError("chunk_cycles must be positive")

    runtime_builder = builder if builder is not None else CppBackendScaffold()
    python_sim = PythonSimulator(module)

    compile_start = time.perf_counter()
    cpp_sim = runtime_builder.build(module, build_dir)
    compile_seconds = time.perf_counter() - compile_start
    try:
        python_sim.reset()
        python_checksum = _consume_chunk_stream(
            python_sim.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles)
        )
        cpp_sim.reset()
        cpp_checksum = _consume_chunk_stream(
            cpp_sim.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles)
        )
        if python_checksum != cpp_checksum:
            raise AssertionError("python and compiled streaming checksums diverged")

        for _ in range(warmup):
            python_sim.reset()
            _consume_chunk_stream(python_sim.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles))
            cpp_sim.reset()
            _consume_chunk_stream(cpp_sim.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles))

        python_stream_seconds = _measure_min(
            repeats,
            lambda: _run_python_stream(python_sim, row_factory, chunk_cycles),
        )
        cpp_stream_seconds = _measure_min(
            repeats,
            lambda: _run_cpp_stream(cpp_sim, row_factory, chunk_cycles),
        )
    finally:
        cpp_sim.close()

    input_count = len([signal for signal in module.signals if signal.kind == "input"])
    output_count = len(module.outputs)
    return StreamingBenchmarkReport(
        module_name=module.name,
        cycles=cycles,
        chunk_cycles=chunk_cycles,
        compile_seconds=compile_seconds,
        chunk_input_bytes=chunk_cycles * input_count * 8,
        chunk_output_bytes=chunk_cycles * output_count * 8,
        python_stream_seconds=python_stream_seconds,
        cpp_stream_seconds=cpp_stream_seconds,
        stream_speedup=python_stream_seconds / cpp_stream_seconds,
        checksum=python_checksum,
    )


def _measure_min(repeats: int, run: Callable[[], None]) -> float:
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        run()
        duration = time.perf_counter() - start
        if duration < best:
            best = duration
    return best


def _split_rows(flat_inputs: Sequence[int], cycles: int, input_count: int) -> Tuple[Tuple[int, ...], ...]:
    return tuple(
        tuple(flat_inputs[cycle * input_count : (cycle + 1) * input_count])
        for cycle in range(cycles)
    )


def _consume_chunk_stream(chunks: Iterable[array]) -> int:
    checksum = 0
    for chunk in chunks:
        checksum = (checksum + int(sum(chunk))) & 0xFFFFFFFFFFFFFFFF
    return checksum


def _run_python_step_loop(simulator: PythonSimulator, step_rows: Sequence[Sequence[int]]) -> None:
    simulator.reset()
    for row in step_rows:
        simulator.step_raw(row)


def _run_cpp_step_loop(simulator, step_rows: Sequence[Sequence[int]]) -> None:
    simulator.reset()
    for row in step_rows:
        simulator.step_raw(row)


def _run_python_batch(
    simulator: PythonSimulator,
    packed_inputs: array,
    cycles: int,
    output_buffer: array,
) -> None:
    simulator.reset()
    simulator.run_batch_buffered(packed_inputs, cycles, output_buffer)


def _run_cpp_batch(simulator, packed_inputs: array, cycles: int, output_buffer: array) -> None:
    simulator.reset()
    simulator.run_batch_buffered(packed_inputs, cycles, output_buffer)


def _run_python_stream(
    simulator: PythonSimulator,
    row_factory: Callable[[], Iterable[Sequence[int]]],
    chunk_cycles: int,
) -> None:
    simulator.reset()
    _consume_chunk_stream(simulator.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles))


def _run_cpp_stream(simulator, row_factory: Callable[[], Iterable[Sequence[int]]], chunk_cycles: int) -> None:
    simulator.reset()
    _consume_chunk_stream(simulator.iter_batch_buffered(row_factory(), chunk_cycles=chunk_cycles))
