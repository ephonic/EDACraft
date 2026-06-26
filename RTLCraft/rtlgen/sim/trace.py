"""Trace, replay, and parity helpers for executable simulators."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
from typing import Dict, Mapping, Optional, Sequence, Tuple

from rtlgen.sim.cpp_backend import CppBackendScaffold, SimModule
from rtlgen.sim.python_runtime import PythonSimulator


@dataclass(frozen=True)
class TraceStep:
    cycle: int
    inputs: Mapping[str, int]
    active_domains: Tuple[str, ...]
    outputs: Mapping[str, int]
    state: Mapping[str, int]


@dataclass(frozen=True)
class ExecutionTrace:
    module_name: str
    backend: str
    steps: Tuple[TraceStep, ...]


@dataclass(frozen=True)
class TraceMismatch:
    cycle: int
    kind: str
    name: str
    expected: int
    actual: int


@dataclass(frozen=True)
class SimulatorParityReport:
    module_name: str
    matched: bool
    mismatches: Tuple[TraceMismatch, ...]
    python_trace: ExecutionTrace
    compiled_trace: ExecutionTrace


@dataclass(frozen=True)
class RandomParityConfig:
    cycles: int = 64
    seed: int = 1234


@dataclass(frozen=True)
class RandomParityHarnessReport:
    module_name: str
    cycles: int
    seed: int
    vectors: Tuple[Mapping[str, int], ...]
    parity: SimulatorParityReport


def capture_execution_trace(
    simulator,
    vectors: Sequence[object],
    *,
    module_name: Optional[str] = None,
    backend: Optional[str] = None,
) -> ExecutionTrace:
    """Execute one vector sequence and capture outputs plus post-step state snapshots."""

    steps = []
    resolved_module_name = module_name or getattr(getattr(simulator, "module", None), "name", "unknown")
    resolved_backend = backend or type(simulator).__name__
    for cycle, vector in enumerate(vectors):
        inputs, active_domains = _decode_trace_vector(vector)
        if active_domains:
            if not hasattr(simulator, "step_clocks"):
                raise ValueError("trace vector requested active clock domains but simulator has no step_clocks()")
            outputs = dict(simulator.step_clocks(dict(inputs), active_domains))
        else:
            outputs = dict(simulator.step(dict(inputs)))
        state = _snapshot_state_dict(simulator)
        steps.append(
            TraceStep(
                cycle=cycle,
                inputs={name: int(value) for name, value in dict(inputs).items()},
                active_domains=tuple(active_domains),
                outputs={name: int(value) for name, value in outputs.items()},
                state=state,
            )
        )
    return ExecutionTrace(
        module_name=resolved_module_name,
        backend=resolved_backend,
        steps=tuple(steps),
    )


def replay_execution_trace(
    simulator,
    trace: ExecutionTrace,
) -> Tuple[TraceMismatch, ...]:
    """Replay one captured trace and return any output/state mismatches."""

    mismatches = []
    for step in trace.steps:
        if step.active_domains:
            if not hasattr(simulator, "step_clocks"):
                raise ValueError("trace step requested active clock domains but simulator has no step_clocks()")
            outputs = dict(simulator.step_clocks(dict(step.inputs), step.active_domains))
        else:
            outputs = dict(simulator.step(dict(step.inputs)))
        for name, expected in step.outputs.items():
            actual = int(outputs.get(name, 0))
            if actual != int(expected):
                mismatches.append(
                    TraceMismatch(
                        cycle=step.cycle,
                        kind="output",
                        name=name,
                        expected=int(expected),
                        actual=actual,
                    )
                )
        current_state = _snapshot_state_dict(simulator)
        for name, expected in step.state.items():
            actual = int(current_state.get(name, 0))
            if actual != int(expected):
                mismatches.append(
                    TraceMismatch(
                        cycle=step.cycle,
                        kind="state",
                        name=name,
                        expected=int(expected),
                        actual=actual,
                    )
                )
    return tuple(mismatches)


def compare_python_and_compiled(
    module: SimModule,
    vectors: Sequence[object],
    *,
    builder: Optional[CppBackendScaffold] = None,
    build_dir: Optional[Path | str] = None,
) -> SimulatorParityReport:
    """Capture traces from Python and compiled execution and compare them."""

    python_sim = PythonSimulator(module)
    python_trace = capture_execution_trace(python_sim, vectors, module_name=module.name, backend="PythonSimulator")
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    with runtime_builder.build(module, build_dir=build_dir) as compiled:
        compiled_trace = capture_execution_trace(compiled, vectors, module_name=module.name, backend="CompiledSimulator")

    mismatches = []
    for py_step, cpp_step in zip(python_trace.steps, compiled_trace.steps):
        for output_name, expected in py_step.outputs.items():
            actual = int(cpp_step.outputs.get(output_name, 0))
            if actual != int(expected):
                mismatches.append(
                    TraceMismatch(
                        cycle=py_step.cycle,
                        kind="output",
                        name=output_name,
                        expected=int(expected),
                        actual=actual,
                    )
                )
        for state_name, expected in py_step.state.items():
            actual = int(cpp_step.state.get(state_name, 0))
            if actual != int(expected):
                mismatches.append(
                    TraceMismatch(
                        cycle=py_step.cycle,
                        kind="state",
                        name=state_name,
                        expected=int(expected),
                        actual=actual,
                    )
                )
    return SimulatorParityReport(
        module_name=module.name,
        matched=not mismatches,
        mismatches=tuple(mismatches),
        python_trace=python_trace,
        compiled_trace=compiled_trace,
    )


def run_random_parity_fuzz(
    module: SimModule,
    *,
    config: RandomParityConfig = RandomParityConfig(),
    builder: Optional[CppBackendScaffold] = None,
    build_dir: Optional[Path | str] = None,
) -> RandomParityHarnessReport:
    """Generate random vectors from module input widths and compare Python vs compiled execution."""

    rng = random.Random(config.seed)
    signal_map = module.signal_map()
    input_names = tuple(signal.name for signal in module.signals if signal.kind == "input")
    vectors = tuple(
        {
            name: rng.randrange(1 << min(signal_map[name].width, 16))
            for name in input_names
        }
        for _ in range(config.cycles)
    )
    parity = compare_python_and_compiled(
        module,
        vectors,
        builder=builder,
        build_dir=build_dir,
    )
    return RandomParityHarnessReport(
        module_name=module.name,
        cycles=config.cycles,
        seed=config.seed,
        vectors=vectors,
        parity=parity,
    )


def _snapshot_state_dict(simulator) -> Dict[str, int]:
    if hasattr(simulator, "snapshot_state_values") and hasattr(simulator, "state_names"):
        state = simulator.snapshot_state_values()
        return {
            name: int(state[idx])
            for idx, name in enumerate(getattr(simulator, "state_names", ()))
        }
    if not hasattr(simulator, "snapshot_state_numpy") or not hasattr(simulator, "state_names"):
        return {}
    state = simulator.snapshot_state_numpy()
    return {
        name: int(state[idx])
        for idx, name in enumerate(getattr(simulator, "state_names", ()))
    }


def _decode_trace_vector(
    vector: object,
) -> Tuple[Mapping[str, int], Tuple[str, ...]]:
    if (
        isinstance(vector, tuple)
        and len(vector) == 2
        and isinstance(vector[0], Mapping)
    ):
        inputs = vector[0]
        active_domains = _normalize_active_domains(vector[1])
        return inputs, active_domains
    if isinstance(vector, Mapping):
        return vector, ()
    raise TypeError("trace vectors must be input mappings or (inputs, active_domains) tuples")


def _normalize_active_domains(active_domains: object) -> Tuple[str, ...]:
    if isinstance(active_domains, Mapping):
        selected = [name for name, enabled in active_domains.items() if enabled]
        return tuple(str(name) for name in selected)
    if isinstance(active_domains, Sequence) and not isinstance(active_domains, (str, bytes, bytearray)):
        return tuple(str(name) for name in active_domains)
    raise TypeError("active_domains must be a sequence of names or a name->bool mapping")
