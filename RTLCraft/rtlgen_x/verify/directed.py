"""Directed and streamed verification built on top of the compiled simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from rtlgen_x.sim import CppBackendScaffold, SimModule
from rtlgen_x.verify.module_adapter import normalize_executable_module


@dataclass(frozen=True)
class StepVector:
    """One simulator step with its expected observed outputs."""

    inputs: Mapping[str, int]
    expected: Mapping[str, int]


@dataclass(frozen=True)
class VerificationFailure:
    """One signal mismatch detected during verification."""

    cycle: int
    signal: str
    expected: int
    actual: int
    inputs: Dict[str, int]


@dataclass(frozen=True)
class DirectedTestReport:
    """Verification result for a sequence of vectors."""

    name: str
    passed: bool
    traces: Tuple[Dict[str, int], ...]
    failures: Tuple[VerificationFailure, ...]


@dataclass(frozen=True)
class StreamingVerificationReport:
    """Chunked scoreboard-style verification result."""

    name: str
    passed: bool
    total_cycles: int
    executed_cycles: int
    checked_signals: Tuple[str, ...]
    stopped_early: bool
    max_failures: Optional[int]
    failures: Tuple[VerificationFailure, ...]
    sampled_traces: Tuple["TraceSample", ...]


@dataclass(frozen=True)
class TraceSample:
    """One sampled trace point captured during streaming verification."""

    cycle: int
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    expected: Dict[str, int]


@dataclass(frozen=True)
class _ChunkConsumeResult:
    executed_cycles: int
    limit_reached: bool


def run_directed_test(
    module: Any,
    vectors: Sequence[StepVector],
    *,
    name: str = "directed_test",
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
    reset_before_run: bool = True,
) -> DirectedTestReport:
    """Compile the module, run directed vectors, and collect mismatches."""

    module = normalize_executable_module(module)
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    traces = []
    failures = []
    with runtime_builder.build(module, build_dir) as simulator:
        if reset_before_run:
            simulator.reset()
        for cycle, vector in enumerate(vectors):
            observed = simulator.step(vector.inputs)
            traces.append(observed)
            _check_expected(observed, vector.expected, cycle, dict(vector.inputs), failures)
    return DirectedTestReport(
        name=name,
        passed=not failures,
        traces=tuple(traces),
        failures=tuple(failures),
    )


def run_streaming_test(
    module: Any,
    vectors: Iterable[StepVector],
    *,
    name: str = "streaming_test",
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
    reset_before_run: bool = True,
    chunk_cycles: int = 65536,
    max_failures: Optional[int] = None,
    trace_stride: Optional[int] = None,
    failure_block_cycles: Optional[int] = None,
    trace_sink: Optional[Callable[[TraceSample], None]] = None,
) -> StreamingVerificationReport:
    """Run chunked verification without materializing the full output trace."""

    if chunk_cycles < 1:
        raise ValueError("chunk_cycles must be positive")
    if max_failures is not None and max_failures < 1:
        raise ValueError("max_failures must be positive when provided")
    if trace_stride is not None and trace_stride < 1:
        raise ValueError("trace_stride must be positive when provided")
    if failure_block_cycles is not None and failure_block_cycles < 1:
        raise ValueError("failure_block_cycles must be positive when provided")
    module = normalize_executable_module(module)
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    failures = []
    sampled_traces = []
    checked_signals = None
    total_cycles = 0
    executed_cycles = 0
    stopped_early = False
    block_cycles = failure_block_cycles if failure_block_cycles is not None else chunk_cycles
    with runtime_builder.build(module, build_dir) as simulator:
        if reset_before_run:
            simulator.reset()
        chunk_inputs = []
        chunk_expected = []
        chunk_input_snapshots = []
        cycle_base = 0
        for vector in vectors:
            chunk_inputs.append(tuple(int(vector.inputs.get(name, 0)) for name in simulator.input_names))
            chunk_expected.append(dict(vector.expected))
            chunk_input_snapshots.append(dict(vector.inputs))
            if checked_signals is None:
                checked_signals = tuple(vector.expected.keys())
            total_cycles += 1
            if len(chunk_inputs) == chunk_cycles:
                chunk_result = _consume_streaming_chunk(
                    simulator,
                    chunk_inputs,
                    chunk_expected,
                    chunk_input_snapshots,
                    cycle_base,
                    failures,
                    sampled_traces,
                    max_failures=max_failures,
                    trace_stride=trace_stride,
                    failure_block_cycles=block_cycles,
                    trace_sink=trace_sink,
                )
                executed_cycles += chunk_result.executed_cycles
                cycle_base += chunk_result.executed_cycles
                if (
                    chunk_result.executed_cycles < len(chunk_inputs)
                    or chunk_result.limit_reached
                ):
                    stopped_early = True
                    chunk_inputs = []
                    chunk_expected = []
                    chunk_input_snapshots = []
                    break
                chunk_inputs = []
                chunk_expected = []
                chunk_input_snapshots = []
        if chunk_inputs and not stopped_early:
            chunk_result = _consume_streaming_chunk(
                simulator,
                chunk_inputs,
                chunk_expected,
                chunk_input_snapshots,
                cycle_base,
                failures,
                sampled_traces,
                max_failures=max_failures,
                trace_stride=trace_stride,
                failure_block_cycles=block_cycles,
                trace_sink=trace_sink,
            )
            executed_cycles += chunk_result.executed_cycles
            if chunk_result.executed_cycles < len(chunk_inputs):
                stopped_early = True
    if checked_signals is None:
        checked_signals = ()
    return StreamingVerificationReport(
        name=name,
        passed=not failures and not stopped_early,
        total_cycles=total_cycles,
        executed_cycles=executed_cycles,
        checked_signals=checked_signals,
        stopped_early=stopped_early,
        max_failures=max_failures,
        failures=tuple(failures),
        sampled_traces=tuple(sampled_traces),
    )


def run_streaming_check(
    module: Any,
    inputs: Iterable[Mapping[str, int]],
    expected_fn: Callable[[int, Mapping[str, int]], Mapping[str, int]],
    *,
    name: str = "streaming_check",
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
    reset_before_run: bool = True,
    chunk_cycles: int = 65536,
    max_failures: Optional[int] = None,
    trace_stride: Optional[int] = None,
    failure_block_cycles: Optional[int] = None,
    trace_sink: Optional[Callable[[TraceSample], None]] = None,
) -> StreamingVerificationReport:
    """Run chunked verification against an online expected-value function."""

    if chunk_cycles < 1:
        raise ValueError("chunk_cycles must be positive")
    if max_failures is not None and max_failures < 1:
        raise ValueError("max_failures must be positive when provided")
    if trace_stride is not None and trace_stride < 1:
        raise ValueError("trace_stride must be positive when provided")
    if failure_block_cycles is not None and failure_block_cycles < 1:
        raise ValueError("failure_block_cycles must be positive when provided")
    module = normalize_executable_module(module)
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    failures = []
    sampled_traces = []
    checked_signals = None
    total_cycles = 0
    executed_cycles = 0
    stopped_early = False
    block_cycles = failure_block_cycles if failure_block_cycles is not None else chunk_cycles
    with runtime_builder.build(module, build_dir) as simulator:
        if reset_before_run:
            simulator.reset()
        chunk_inputs = []
        chunk_expected = []
        chunk_input_snapshots = []
        cycle_base = 0
        for raw_inputs in inputs:
            snapshot = dict(raw_inputs)
            expected = dict(expected_fn(total_cycles, snapshot))
            chunk_inputs.append(tuple(int(snapshot.get(name, 0)) for name in simulator.input_names))
            chunk_expected.append(expected)
            chunk_input_snapshots.append(snapshot)
            if checked_signals is None:
                checked_signals = tuple(expected.keys())
            total_cycles += 1
            if len(chunk_inputs) == chunk_cycles:
                chunk_result = _consume_streaming_chunk(
                    simulator,
                    chunk_inputs,
                    chunk_expected,
                    chunk_input_snapshots,
                    cycle_base,
                    failures,
                    sampled_traces,
                    max_failures=max_failures,
                    trace_stride=trace_stride,
                    failure_block_cycles=block_cycles,
                    trace_sink=trace_sink,
                )
                executed_cycles += chunk_result.executed_cycles
                cycle_base += chunk_result.executed_cycles
                if (
                    chunk_result.executed_cycles < len(chunk_inputs)
                    or chunk_result.limit_reached
                ):
                    stopped_early = True
                    chunk_inputs = []
                    chunk_expected = []
                    chunk_input_snapshots = []
                    break
                chunk_inputs = []
                chunk_expected = []
                chunk_input_snapshots = []
        if chunk_inputs and not stopped_early:
            chunk_result = _consume_streaming_chunk(
                simulator,
                chunk_inputs,
                chunk_expected,
                chunk_input_snapshots,
                cycle_base,
                failures,
                sampled_traces,
                max_failures=max_failures,
                trace_stride=trace_stride,
                failure_block_cycles=block_cycles,
                trace_sink=trace_sink,
            )
            executed_cycles += chunk_result.executed_cycles
            if chunk_result.executed_cycles < len(chunk_inputs):
                stopped_early = True
    if checked_signals is None:
        checked_signals = ()
    return StreamingVerificationReport(
        name=name,
        passed=not failures and not stopped_early,
        total_cycles=total_cycles,
        executed_cycles=executed_cycles,
        checked_signals=checked_signals,
        stopped_early=stopped_early,
        max_failures=max_failures,
        failures=tuple(failures),
        sampled_traces=tuple(sampled_traces),
    )


def run_streaming_check_adaptive(
    module: Any,
    inputs: Iterable[Mapping[str, int]],
    expected_fn: Callable[[int, Mapping[str, int]], Mapping[str, int]],
    *,
    name: str = "streaming_check_adaptive",
    build_dir: Optional[str] = None,
    builder: Optional[CppBackendScaffold] = None,
    reset_before_run: bool = True,
    chunk_cycles: int = 65536,
    max_failures: Optional[int] = None,
    trace_stride: Optional[int] = None,
    trace_sink: Optional[Callable[[TraceSample], None]] = None,
) -> StreamingVerificationReport:
    """Run chunked verification and replay only the suffix needed to stop at the failure budget."""

    if chunk_cycles < 1:
        raise ValueError("chunk_cycles must be positive")
    if max_failures is not None and max_failures < 1:
        raise ValueError("max_failures must be positive when provided")
    if trace_stride is not None and trace_stride < 1:
        raise ValueError("trace_stride must be positive when provided")

    module = normalize_executable_module(module)
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    failures = []
    sampled_traces = []
    checked_signals = None
    total_cycles = 0
    executed_cycles = 0
    stopped_early = False
    with runtime_builder.build(module, build_dir) as simulator:
        if reset_before_run:
            simulator.reset()
        chunk_inputs = []
        chunk_expected = []
        chunk_input_snapshots = []
        cycle_base = 0
        for raw_inputs in inputs:
            snapshot = dict(raw_inputs)
            expected = dict(expected_fn(total_cycles, snapshot))
            chunk_inputs.append(tuple(int(snapshot.get(name, 0)) for name in simulator.input_names))
            chunk_expected.append(expected)
            chunk_input_snapshots.append(snapshot)
            if checked_signals is None:
                checked_signals = tuple(expected.keys())
            total_cycles += 1
            if len(chunk_inputs) == chunk_cycles:
                chunk_result = _consume_streaming_chunk_adaptive(
                    simulator,
                    chunk_inputs,
                    chunk_expected,
                    chunk_input_snapshots,
                    cycle_base,
                    failures,
                    sampled_traces,
                    max_failures=max_failures,
                    trace_stride=trace_stride,
                    trace_sink=trace_sink,
                )
                executed_cycles += chunk_result.executed_cycles
                cycle_base += chunk_result.executed_cycles
                if (
                    chunk_result.executed_cycles < len(chunk_inputs)
                    or chunk_result.limit_reached
                ):
                    stopped_early = True
                    chunk_inputs = []
                    chunk_expected = []
                    chunk_input_snapshots = []
                    break
                chunk_inputs = []
                chunk_expected = []
                chunk_input_snapshots = []
        if chunk_inputs and not stopped_early:
            chunk_result = _consume_streaming_chunk_adaptive(
                simulator,
                chunk_inputs,
                chunk_expected,
                chunk_input_snapshots,
                cycle_base,
                failures,
                sampled_traces,
                max_failures=max_failures,
                trace_stride=trace_stride,
                trace_sink=trace_sink,
            )
            executed_cycles += chunk_result.executed_cycles
            if chunk_result.executed_cycles < len(chunk_inputs):
                stopped_early = True
    if checked_signals is None:
        checked_signals = ()
    return StreamingVerificationReport(
        name=name,
        passed=not failures and not stopped_early,
        total_cycles=total_cycles,
        executed_cycles=executed_cycles,
        checked_signals=checked_signals,
        stopped_early=stopped_early,
        max_failures=max_failures,
        failures=tuple(failures),
        sampled_traces=tuple(sampled_traces),
    )


def _consume_streaming_chunk(
    simulator,
    chunk_inputs,
    chunk_expected,
    chunk_input_snapshots,
    cycle_base: int,
    failures,
    sampled_traces,
    *,
    max_failures: Optional[int],
    trace_stride: Optional[int],
    failure_block_cycles: int,
    trace_sink: Optional[Callable[[TraceSample], None]],
) -> int:
    if max_failures is not None and len(failures) >= max_failures:
        return _ChunkConsumeResult(executed_cycles=0, limit_reached=True)
    executed = 0
    cursor = 0
    while cursor < len(chunk_inputs):
        if max_failures is not None and len(failures) >= max_failures:
            return _ChunkConsumeResult(executed_cycles=executed, limit_reached=True)
        block_end = min(cursor + failure_block_cycles, len(chunk_inputs))
        observed_rows = simulator.run_batch(chunk_inputs[cursor:block_end])
        for block_idx, observed in enumerate(observed_rows):
            idx = cursor + block_idx
            cycle = cycle_base + idx
            _record_observed_row(
                cycle=cycle,
                observed=observed,
                expected=chunk_expected[idx],
                input_snapshot=chunk_input_snapshots[idx],
                failures=failures,
                sampled_traces=sampled_traces,
                trace_stride=trace_stride,
                trace_sink=trace_sink,
            )
            executed += 1
            if max_failures is not None and len(failures) >= max_failures:
                return _ChunkConsumeResult(executed_cycles=executed, limit_reached=True)
        cursor = block_end
    return _ChunkConsumeResult(executed_cycles=executed, limit_reached=False)


def _consume_streaming_chunk_adaptive(
    simulator,
    chunk_inputs,
    chunk_expected,
    chunk_input_snapshots,
    cycle_base: int,
    failures,
    sampled_traces,
    *,
    max_failures: Optional[int],
    trace_stride: Optional[int],
    trace_sink: Optional[Callable[[TraceSample], None]],
) -> _ChunkConsumeResult:
    if max_failures is not None and len(failures) >= max_failures:
        return _ChunkConsumeResult(executed_cycles=0, limit_reached=True)
    state_before = simulator.snapshot_state_numpy()
    observed_rows = simulator.run_batch(chunk_inputs)
    remaining_budget = None if max_failures is None else max_failures - len(failures)
    row_failure_counts = [
        _count_expected_mismatches(observed, chunk_expected[idx])
        for idx, observed in enumerate(observed_rows)
    ]
    total_new_failures = sum(row_failure_counts)
    if remaining_budget is None or total_new_failures < remaining_budget:
        for idx, observed in enumerate(observed_rows):
            _record_observed_row(
                cycle=cycle_base + idx,
                observed=observed,
                expected=chunk_expected[idx],
                input_snapshot=chunk_input_snapshots[idx],
                failures=failures,
                sampled_traces=sampled_traces,
                trace_stride=trace_stride,
                trace_sink=trace_sink,
            )
        return _ChunkConsumeResult(executed_cycles=len(observed_rows), limit_reached=False)

    simulator.restore_state_numpy(state_before)
    executed = 0
    cumulative_failures = 0
    stop_idx = len(chunk_inputs) - 1
    for idx, failure_count in enumerate(row_failure_counts):
        cumulative_failures += failure_count
        if cumulative_failures >= remaining_budget:
            stop_idx = idx
            break

    for idx in range(stop_idx + 1):
        observed_values = simulator.step_raw(chunk_inputs[idx])
        observed = {
            name: int(observed_values[col])
            for col, name in enumerate(simulator.output_names)
        }
        _record_observed_row(
            cycle=cycle_base + idx,
            observed=observed,
            expected=chunk_expected[idx],
            input_snapshot=chunk_input_snapshots[idx],
            failures=failures,
            sampled_traces=sampled_traces,
            trace_stride=trace_stride,
            trace_sink=trace_sink,
        )
        executed += 1
        if max_failures is not None and len(failures) >= max_failures:
            return _ChunkConsumeResult(executed_cycles=executed, limit_reached=True)
    return _ChunkConsumeResult(executed_cycles=executed, limit_reached=False)


def _has_expected_mismatch(observed, expected) -> bool:
    return _count_expected_mismatches(observed, expected) > 0


def _count_expected_mismatches(observed, expected) -> int:
    mismatch_count = 0
    for signal, expected_value in expected.items():
        if signal not in observed:
            raise KeyError(f"unknown expected output '{signal}'")
        if observed[signal] != int(expected_value):
            mismatch_count += 1
    return mismatch_count


def _record_observed_row(
    *,
    cycle: int,
    observed: Mapping[str, int],
    expected: Mapping[str, int],
    input_snapshot: Dict[str, int],
    failures,
    sampled_traces,
    trace_stride: Optional[int],
    trace_sink: Optional[Callable[[TraceSample], None]],
) -> None:
    if trace_stride is not None and cycle % trace_stride == 0:
        sample = TraceSample(
            cycle=cycle,
            inputs=dict(input_snapshot),
            outputs=dict(observed),
            expected=dict(expected),
        )
        sampled_traces.append(sample)
        if trace_sink is not None:
            trace_sink(sample)
    _check_expected(observed, expected, cycle, input_snapshot, failures)


def _check_expected(observed, expected, cycle: int, input_snapshot: Dict[str, int], failures) -> None:
    for signal, expected_value in expected.items():
        if signal not in observed:
            raise KeyError(f"unknown expected output '{signal}'")
        actual = observed[signal]
        if actual != int(expected_value):
            failures.append(
                VerificationFailure(
                    cycle=cycle,
                    signal=signal,
                    expected=int(expected_value),
                    actual=actual,
                    inputs=input_snapshot,
                )
            )
