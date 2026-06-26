"""Benchmark helpers for comparing Python and compiled simulator performance."""

from __future__ import annotations

import time
from array import array
from dataclasses import asdict, dataclass, is_dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Tuple

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
    pack_signal_values_u64_words,
    _word_count,
)
from rtlgen_x.sim.python_runtime import PythonSimulator
from rtlgen_x.sim.cosim import run_dsl_multiclock_rtl_cosim, run_dsl_rtl_cosim


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


@dataclass(frozen=True)
class StressSweepPoint:
    """One benchmark point in a stress sweep."""

    width: int
    cycles: int
    simulator: SimulatorBenchmarkReport
    streaming: StreamingBenchmarkReport


@dataclass(frozen=True)
class StressSweepReport:
    """Batch benchmark summary across multiple widths and cycle counts."""

    points: Tuple[StressSweepPoint, ...]

    @property
    def max_step_speedup(self) -> float:
        return max((point.simulator.step_speedup for point in self.points), default=0.0)

    @property
    def max_batch_speedup(self) -> float:
        return max((point.simulator.batch_speedup for point in self.points), default=0.0)

    @property
    def max_stream_speedup(self) -> float:
        return max((point.streaming.stream_speedup for point in self.points), default=0.0)

    @property
    def max_cycles(self) -> int:
        return max((point.cycles for point in self.points), default=0)

    @property
    def widths(self) -> Tuple[int, ...]:
        return tuple(sorted({point.width for point in self.points}))

    def to_dict(self) -> dict[str, object]:
        return {
            "point_count": len(self.points),
            "widths": list(self.widths),
            "max_cycles": self.max_cycles,
            "max_step_speedup": self.max_step_speedup,
            "max_batch_speedup": self.max_batch_speedup,
            "max_stream_speedup": self.max_stream_speedup,
            "points": [asdict(point) for point in self.points],
        }


@dataclass(frozen=True)
class CosimBenchmarkReport:
    """Measured cold/warm runtime for emitted RTL cosim backends."""

    module_name: str
    backend: str
    mode: str
    vector_count: int
    compile_cache_enabled: bool
    first_cache_hit: bool
    second_cache_hit: bool
    cache_key: Optional[str]
    cache_dir: Optional[str]
    first_run_seconds: float
    second_run_seconds: float
    warm_speedup: float
    cache_artifact_present: bool
    first_report_passed: bool
    second_report_passed: bool
    skipped_reason: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CosimBackendSweepReport:
    """Backend-by-backend cold/warm cosim benchmark summary."""

    module_name: str
    mode: str
    vector_count: int
    backends: Tuple[CosimBenchmarkReport, ...]

    @property
    def available_backends(self) -> Tuple[str, ...]:
        return tuple(report.backend for report in self.backends if report.skipped_reason is None)

    @property
    def skipped_backends(self) -> Tuple[str, ...]:
        return tuple(report.backend for report in self.backends if report.skipped_reason is not None)

    def to_dict(self) -> dict[str, object]:
        return {
            "module_name": self.module_name,
            "mode": self.mode,
            "vector_count": self.vector_count,
            "available_backends": list(self.available_backends),
            "skipped_backends": list(self.skipped_backends),
            "backends": [_cosim_benchmark_to_dict(report) for report in self.backends],
        }


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
    packed_inputs = _normalize_packed_inputs(flat_inputs, cycles, python_sim)
    total_outputs = cycles * python_sim.output_word_count
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

    input_words = sum(_word_count(signal.width) for signal in module.signals if signal.kind == "input")
    output_words = sum(_word_count(signal.width) for signal in module.signals if signal.kind == "output")
    return StreamingBenchmarkReport(
        module_name=module.name,
        cycles=cycles,
        chunk_cycles=chunk_cycles,
        compile_seconds=compile_seconds,
        chunk_input_bytes=chunk_cycles * input_words * 8,
        chunk_output_bytes=chunk_cycles * output_words * 8,
        python_stream_seconds=python_stream_seconds,
        cpp_stream_seconds=cpp_stream_seconds,
        stream_speedup=python_stream_seconds / cpp_stream_seconds,
        checksum=python_checksum,
    )


def run_stress_sweep(
    *,
    widths: Sequence[int] = (32, 64),
    cycles_list: Sequence[int] = (256, 4096),
    chunk_cycles: int = 1024,
    repeats: int = 3,
    warmup: int = 1,
    build_root: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
) -> StressSweepReport:
    """Run a benchmark sweep over multiple stress-module sizes."""

    if not widths:
        raise ValueError("widths must not be empty")
    if not cycles_list:
        raise ValueError("cycles_list must not be empty")

    sweep_points = []
    for width in widths:
        module = build_stress_module(width)
        for cycles in cycles_list:
            inputs = generate_stress_input_buffer(module, cycles, seed=width + cycles)
            point_root = None if build_root is None else f"{build_root}/w{width}_c{cycles}"
            simulator = benchmark_compiled_speedup(
                module,
                inputs,
                cycles,
                repeats=repeats,
                warmup=warmup,
                build_dir=None if point_root is None else f"{point_root}/batch",
                builder=builder,
            )
            streaming = benchmark_streaming_capacity(
                module,
                lambda module=module, cycles=cycles, width=width: iter_stress_input_rows(
                    module,
                    cycles,
                    seed=width + cycles,
                ),
                cycles,
                chunk_cycles=min(chunk_cycles, cycles),
                repeats=repeats,
                warmup=warmup,
                build_dir=None if point_root is None else f"{point_root}/stream",
                builder=builder,
            )
            sweep_points.append(
                StressSweepPoint(
                    width=width,
                    cycles=cycles,
                    simulator=simulator,
                    streaming=streaming,
                )
            )
    return StressSweepReport(points=tuple(sweep_points))


def write_stress_sweep_report(
    report: StressSweepReport,
    path: str | Path,
) -> Path:
    """Persist one stress sweep report as JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def write_cosim_backend_sweep_report(
    report: CosimBackendSweepReport,
    path: str | Path,
) -> Path:
    """Persist one backend-sweep report as JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def emit_cosim_backend_sweep_markdown(
    report: CosimBackendSweepReport,
    *,
    title: Optional[str] = None,
) -> str:
    """Render a concise markdown summary for backend cosim comparisons."""

    heading = title or f"Cosim Backend Sweep: {report.module_name}"
    lines = [f"# {heading}", ""]
    lines.append(f"- module: `{report.module_name}`")
    lines.append(f"- mode: `{report.mode}`")
    lines.append(f"- vectors: `{report.vector_count}`")
    lines.append(f"- available backends: {', '.join(report.available_backends) or 'none'}")
    lines.append(f"- skipped backends: {', '.join(report.skipped_backends) or 'none'}")
    lines.append("")
    lines.append("| backend | status | cache | cold(s) | warm(s) | speedup | note |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | --- |")
    for entry in report.backends:
        status = "ok" if entry.skipped_reason is None else "skipped"
        cache_state = (
            f"{'on' if entry.compile_cache_enabled else 'off'} / "
            f"{'hit' if entry.second_cache_hit else 'miss'}"
        )
        note = entry.skipped_reason or (
            "pass" if entry.first_report_passed and entry.second_report_passed else "mismatch"
        )
        lines.append(
            "| "
            f"`{entry.backend}` | {status} | {cache_state} | "
            f"{entry.first_run_seconds:.6f} | {entry.second_run_seconds:.6f} | "
            f"{entry.warm_speedup:.2f} | {note} |"
        )
    return "\n".join(lines)


def benchmark_cosim_cache(
    module: Any,
    vectors: Sequence[Any],
    *,
    rtl_backend: str = "verilator",
    valid_signal: Optional[str] = None,
    build_dir: Optional[str | Path] = None,
) -> CosimBenchmarkReport:
    """Measure cold-start versus cached rerun time for emitted RTL cosim."""

    if build_dir is None:
        raise ValueError("benchmark_cosim_cache requires build_dir so the external build cache can persist")
    build_root = Path(build_dir)
    build_root.mkdir(parents=True, exist_ok=True)

    multi_clock = hasattr(module, "_seq_blocks") and len(
        {
            getattr(clk, "name", str(clk))
            for clk, _rst, _reset_async, _reset_active_low, _body in getattr(module, "_seq_blocks", ())
            if clk is not None
        }
    ) > 1

    def _run_once():
        if multi_clock:
            return run_dsl_multiclock_rtl_cosim(
                module,
                vectors,
                rtl_backend=rtl_backend,
                build_dir=build_root,
                valid_signal=valid_signal,
            )
        return run_dsl_rtl_cosim(
            module,
            vectors,
            rtl_backend=rtl_backend,
            build_dir=build_root,
            valid_signal=valid_signal,
        )

    start = time.perf_counter()
    first_report = _run_once()
    first_run_seconds = time.perf_counter() - start
    start = time.perf_counter()
    second_report = _run_once()
    second_run_seconds = time.perf_counter() - start

    compile_cache_enabled = bool(getattr(first_report, "cache_enabled", False))
    cache_key = getattr(second_report, "cache_key", None) or getattr(first_report, "cache_key", None)
    cache_dir = getattr(second_report, "cache_dir", None) or getattr(first_report, "cache_dir", None)
    cache_artifact_present = bool(cache_dir) and Path(cache_dir).joinpath(".compile_stamp").exists()
    first_ok = first_report.skipped_reason is None and first_report.dsl_matches_rtl and first_report.compiled_matches_rtl
    second_ok = second_report.skipped_reason is None and second_report.dsl_matches_rtl and second_report.compiled_matches_rtl

    return CosimBenchmarkReport(
        module_name=getattr(module, "name", getattr(module, "_type_name", type(module).__name__)),
        backend=rtl_backend,
        mode="multi_clock" if multi_clock else "seq",
        vector_count=len(vectors),
        compile_cache_enabled=compile_cache_enabled,
        first_cache_hit=bool(getattr(first_report, "cache_hit", False)),
        second_cache_hit=bool(getattr(second_report, "cache_hit", False)),
        cache_key=cache_key,
        cache_dir=cache_dir,
        first_run_seconds=first_run_seconds,
        second_run_seconds=second_run_seconds,
        warm_speedup=(first_run_seconds / second_run_seconds) if second_run_seconds > 0 else float("inf"),
        cache_artifact_present=cache_artifact_present,
        first_report_passed=first_ok,
        second_report_passed=second_ok,
        skipped_reason=getattr(second_report, "skipped_reason", None) or getattr(first_report, "skipped_reason", None),
    )


def benchmark_cosim_backends(
    module: Any,
    vectors: Sequence[Any],
    *,
    rtl_backends: Sequence[str] = ("iverilog", "verilator", "vcs"),
    valid_signal: Optional[str] = None,
    build_dir: Optional[str | Path] = None,
) -> CosimBackendSweepReport:
    """Benchmark a set of RTL backends under the same vector workload."""

    if build_dir is None:
        raise ValueError("benchmark_cosim_backends requires build_dir so backend caches can persist")
    build_root = Path(build_dir)
    build_root.mkdir(parents=True, exist_ok=True)

    multi_clock = hasattr(module, "_seq_blocks") and len(
        {
            getattr(clk, "name", str(clk))
            for clk, _rst, _reset_async, _reset_active_low, _body in getattr(module, "_seq_blocks", ())
            if clk is not None
        }
    ) > 1

    reports = []
    for backend in rtl_backends:
        backend_root = build_root / backend
        reports.append(
            benchmark_cosim_cache(
                module,
                vectors,
                rtl_backend=backend,
                valid_signal=valid_signal,
                build_dir=backend_root,
            )
        )
    return CosimBackendSweepReport(
        module_name=getattr(module, "name", getattr(module, "_type_name", type(module).__name__)),
        mode="multi_clock" if multi_clock else "seq",
        vector_count=len(vectors),
        backends=tuple(reports),
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


def _cosim_benchmark_to_dict(report: Any) -> dict[str, object]:
    if hasattr(report, "to_dict"):
        return dict(report.to_dict())
    if is_dataclass(report):
        return asdict(report)
    fields = (
        "module_name",
        "backend",
        "mode",
        "vector_count",
        "compile_cache_enabled",
        "first_cache_hit",
        "second_cache_hit",
        "cache_key",
        "cache_dir",
        "first_run_seconds",
        "second_run_seconds",
        "warm_speedup",
        "cache_artifact_present",
        "first_report_passed",
        "second_report_passed",
        "skipped_reason",
    )
    return {name: getattr(report, name) for name in fields if hasattr(report, name)}


def _split_rows(flat_inputs: Sequence[int], cycles: int, input_count: int) -> Tuple[Tuple[int, ...], ...]:
    return tuple(
        tuple(flat_inputs[cycle * input_count : (cycle + 1) * input_count])
        for cycle in range(cycles)
    )


def _normalize_packed_inputs(flat_inputs: Sequence[int], cycles: int, simulator: PythonSimulator) -> array:
    if isinstance(flat_inputs, array) and len(flat_inputs) == cycles * simulator.input_word_count:
        return flat_inputs
    if len(flat_inputs) != cycles * simulator.input_count:
        raise ValueError(
            f"expected either {cycles * simulator.input_count} logical inputs or "
            f"{cycles * simulator.input_word_count} packed words, got {len(flat_inputs)}"
        )
    packed = array("Q")
    for cycle in range(cycles):
        start = cycle * simulator.input_count
        packed.extend(
            pack_signal_values_u64_words(
                flat_inputs[start : start + simulator.input_count],
                simulator.input_widths,
            )
        )
    return packed


def _consume_chunk_stream(chunks: Iterable[array]) -> int:
    checksum = 0
    for chunk in chunks:
        for value in chunk:
            checksum = (checksum + int(value)) & 0xFFFFFFFFFFFFFFFF
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
