"""Lightweight UVM-style verification components for local simulator execution."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from rtlgen_x.sim import PythonSimulator, SimModule
from rtlgen_x.verify.directed import StepVector, TraceSample, VerificationFailure
from rtlgen_x.verify.module_adapter import normalize_executable_module, require_single_clock_module


@dataclass(frozen=True)
class PythonUvmSequenceItem:
    """One transaction driven through the Python-side verification framework."""

    inputs: Mapping[str, int]
    expected: Optional[Mapping[str, int]] = None
    label: Optional[str] = None
    active_domains: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonUvmReport:
    """End-to-end result for one Python-side UVM-style run."""

    name: str
    passed: bool
    total_cycles: int
    failures: Tuple[VerificationFailure, ...]
    traces: Tuple[TraceSample, ...]
    coverage: Mapping[str, object]
    used_batch_mode: bool


@dataclass
class PythonUvmReferenceModel:
    """Reference-model wrapper backed by the local Python simulator."""

    module: SimModule

    def __post_init__(self) -> None:
        self._sim = PythonSimulator(self.module)

    def reset(self) -> None:
        self._sim.reset()

    def predict(self, inputs: Mapping[str, int]) -> Dict[str, int]:
        return self._sim.step(inputs)

    def predict_clocks(
        self,
        inputs: Mapping[str, int],
        active_domains: Sequence[str],
    ) -> Dict[str, int]:
        return self._sim.step_clocks(inputs, active_domains)

    def predict_batch(
        self,
        inputs_list: Sequence[Mapping[str, int]],
    ) -> Tuple[Dict[str, int], ...]:
        rows = [
            tuple(int(item.get(name, 0)) for name in self._sim.input_names)
            for item in inputs_list
        ]
        return tuple(dict(row) for row in self._sim.run_batch(rows))


@dataclass
class PythonUvmSequencer:
    """Thin iterable wrapper that keeps UVM-like naming on the Python side."""

    items: Iterable[Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]]]

    def __iter__(self):
        for item in self.items:
            yield _normalize_item(item)


@dataclass(frozen=True)
class PythonUvmSequenceLibrary:
    """Composable sequence library for Python-side stimulus generation."""

    sequences: Tuple[Iterable[Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]]], ...]

    def __iter__(self):
        for sequence in self.sequences:
            sequencer = sequence if isinstance(sequence, PythonUvmSequencer) else PythonUvmSequencer(sequence)
            for item in sequencer:
                yield item

    @classmethod
    def from_sequences(
        cls,
        *sequences: Iterable[Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]]],
    ) -> "PythonUvmSequenceLibrary":
        return cls(sequences=tuple(sequences))


@dataclass
class PythonUvmDriver:
    """Drive transactions into any simulator exposing reset() and step()."""

    simulator: object

    def reset(self) -> None:
        if hasattr(self.simulator, "reset"):
            self.simulator.reset()

    def drive(self, item: PythonUvmSequenceItem) -> Dict[str, int]:
        if item.active_domains:
            if not hasattr(self.simulator, "step_clocks"):
                raise ValueError(
                    "multi-clock Python UVM items require a simulator exposing step_clocks(...)"
                )
            return dict(self.simulator.step_clocks(dict(item.inputs), item.active_domains))
        return dict(self.simulator.step(dict(item.inputs)))

    def supports_batch(self) -> bool:
        return hasattr(self.simulator, "input_names") and hasattr(self.simulator, "run_batch")

    def drive_batch(
        self,
        items: Sequence[PythonUvmSequenceItem],
    ) -> Optional[Tuple[Dict[str, int], ...]]:
        if not self.supports_batch() or any(item.active_domains for item in items):
            return None
        input_names = tuple(self.simulator.input_names)
        rows = [
            tuple(int(item.inputs.get(name, 0)) for name in input_names)
            for item in items
        ]
        return tuple(dict(row) for row in self.simulator.run_batch(rows))


def _normalize_active_domains_payload(payload: object) -> Tuple[str, ...]:
    if payload is None:
        return ()
    if isinstance(payload, Mapping):
        selected = [str(name) for name, enabled in payload.items() if enabled]
        return tuple(dict.fromkeys(selected))
    if isinstance(payload, str):
        return (payload,)
    if isinstance(payload, Sequence) and not isinstance(payload, (bytes, bytearray)):
        return tuple(dict.fromkeys(str(name) for name in payload))
    raise TypeError(
        "structured Python UVM items must provide active_domains as a sequence of names "
        "or a name->bool mapping"
    )


def _validate_sequence_active_domains(
    module: SimModule,
    sequence: Sequence[PythonUvmSequenceItem],
) -> None:
    known_domains = tuple(domain.name for domain in module.clock_domains)
    known_aliases = tuple(
        dict.fromkeys(
            str(alias)
            for domain in module.clock_domains
            for alias in getattr(domain, "aliases", ())
        )
    )
    alias_to_domain = {domain.name: domain.name for domain in module.clock_domains}
    for domain in module.clock_domains:
        for alias in getattr(domain, "aliases", ()):
            alias_to_domain.setdefault(str(alias), domain.name)
    known_set = set(alias_to_domain)
    for item in sequence:
        if not item.active_domains:
            continue
        unknown_domains = sorted(set(item.active_domains) - known_set)
        if unknown_domains:
            joined = ", ".join(unknown_domains)
            known_joined = ", ".join(known_domains) if known_domains else "<module clock domains>"
            alias_joined = ", ".join(known_aliases) if known_aliases else "none"
            raise ValueError(
                "run_python_uvm_test multi-clock sequences reference unknown active_domains: "
                f"{joined}. Known clock domains: {known_joined}. "
                f"Known clock aliases: {alias_joined}. "
                "Wrap each step in PythonUvmSequenceItem(..., active_domains=(...))."
            )


@dataclass
class PythonUvmMonitor:
    """Capture transaction traces from driven inputs and observed outputs."""

    def observe(
        self,
        cycle: int,
        item: PythonUvmSequenceItem,
        outputs: Mapping[str, int],
        expected: Mapping[str, int],
    ) -> TraceSample:
        return TraceSample(
            cycle=cycle,
            inputs=dict(item.inputs),
            outputs=dict(outputs),
            expected=dict(expected),
            active_domains=tuple(item.active_domains),
        )


@dataclass
class PythonUvmCoverage:
    """Very small coverage collector for transaction-level regressions."""

    cycle_count: int = 0
    labels_seen: Dict[str, int] = field(default_factory=dict)
    input_bins: Dict[str, Dict[int, int]] = field(default_factory=dict)
    output_bins: Dict[str, Dict[int, int]] = field(default_factory=dict)

    def reset(self) -> None:
        self.cycle_count = 0
        self.labels_seen.clear()
        self.input_bins.clear()
        self.output_bins.clear()

    def sample(
        self,
        item: PythonUvmSequenceItem,
        outputs: Mapping[str, int],
    ) -> None:
        self.cycle_count += 1
        if item.label:
            self.labels_seen[item.label] = self.labels_seen.get(item.label, 0) + 1
        for signal, value in item.inputs.items():
            signal_bins = self.input_bins.setdefault(signal, {})
            bucket = int(value)
            signal_bins[bucket] = signal_bins.get(bucket, 0) + 1
        for signal, value in outputs.items():
            signal_bins = self.output_bins.setdefault(signal, {})
            bucket = int(value)
            signal_bins[bucket] = signal_bins.get(bucket, 0) + 1

    def snapshot(self) -> Dict[str, object]:
        return {
            "cycle_count": self.cycle_count,
            "labels_seen": dict(self.labels_seen),
            "input_bins": {name: dict(bins) for name, bins in self.input_bins.items()},
            "output_bins": {name: dict(bins) for name, bins in self.output_bins.items()},
        }


@dataclass
class PythonUvmScoreboard:
    """Stateful scoreboard using either explicit expected values or a predictor."""

    expected_fn: Optional[Callable[[int, Mapping[str, int]], Mapping[str, int]]] = None
    reference_model: Optional[object] = None
    failures: List[VerificationFailure] = field(default_factory=list)

    def reset(self) -> None:
        self.failures.clear()
        if self.reference_model is not None and hasattr(self.reference_model, "reset"):
            self.reference_model.reset()

    def resolve_expected(
        self,
        cycle: int,
        item: PythonUvmSequenceItem,
    ) -> Dict[str, int]:
        if item.expected is not None:
            return dict(item.expected)
        if self.expected_fn is not None:
            return dict(self.expected_fn(cycle, dict(item.inputs)))
        if self.reference_model is not None:
            if item.active_domains:
                if hasattr(self.reference_model, "predict_clocks"):
                    return dict(
                        self.reference_model.predict_clocks(
                            dict(item.inputs),
                            item.active_domains,
                        )
                    )
                raise ValueError(
                    "multi-clock Python UVM items require a reference model exposing "
                    "predict_clocks(...)"
                )
            if hasattr(self.reference_model, "predict"):
                return dict(self.reference_model.predict(dict(item.inputs)))
        raise ValueError("expected values require item.expected, expected_fn, or reference_model")

    def resolve_expected_batch(
        self,
        cycle_base: int,
        items: Sequence[PythonUvmSequenceItem],
    ) -> Optional[Tuple[Dict[str, int], ...]]:
        if any(item.expected is not None or item.active_domains for item in items):
            return None
        if self.expected_fn is not None:
            return tuple(
                dict(self.expected_fn(cycle_base + idx, dict(item.inputs)))
                for idx, item in enumerate(items)
            )
        if self.reference_model is not None and hasattr(self.reference_model, "predict_batch"):
            return tuple(
                dict(row)
                for row in self.reference_model.predict_batch([dict(item.inputs) for item in items])
            )
        return None

    def supports_expected_batch(
        self,
        items: Sequence[PythonUvmSequenceItem],
    ) -> bool:
        if any(item.expected is not None or item.active_domains for item in items):
            return False
        if self.expected_fn is not None:
            return True
        return self.reference_model is not None and hasattr(self.reference_model, "predict_batch")

    def check(
        self,
        cycle: int,
        item: PythonUvmSequenceItem,
        outputs: Mapping[str, int],
        expected: Mapping[str, int],
    ) -> None:
        for signal, expected_value in expected.items():
            if signal not in outputs:
                raise KeyError(f"unknown expected output '{signal}'")
            actual = int(outputs[signal])
            if actual != int(expected_value):
                self.failures.append(
                    VerificationFailure(
                        cycle=cycle,
                        signal=signal,
                        expected=int(expected_value),
                        actual=actual,
                        inputs=dict(item.inputs),
                    )
                )


@dataclass
class PythonUvmEnv:
    """UVM-style environment that runs directly on a local simulator."""

    simulator: object
    scoreboard: PythonUvmScoreboard
    driver: Optional[PythonUvmDriver] = None
    monitor: Optional[PythonUvmMonitor] = None
    coverage: Optional[PythonUvmCoverage] = None
    reset_before_run: bool = True
    batch_cycles: int = 0

    def __post_init__(self) -> None:
        if self.driver is None:
            self.driver = PythonUvmDriver(self.simulator)
        if self.monitor is None:
            self.monitor = PythonUvmMonitor()
        if self.coverage is None:
            self.coverage = PythonUvmCoverage()

    def run(
        self,
        sequence: Iterable[Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]]],
        *,
        name: str = "python_uvm",
    ) -> PythonUvmReport:
        sequencer = sequence if isinstance(sequence, PythonUvmSequencer) else PythonUvmSequencer(sequence)
        traces = []
        used_batch_mode = False
        if self.reset_before_run:
            self.driver.reset()
        self.scoreboard.reset()
        self.coverage.reset()
        total_cycles = 0
        if self.batch_cycles and self.batch_cycles > 1:
            chunk = []
            for item in sequencer:
                chunk.append(item)
                if len(chunk) == self.batch_cycles:
                    used_batch_mode = self._consume_chunk(chunk, total_cycles, traces) or used_batch_mode
                    total_cycles += len(chunk)
                    chunk = []
            if chunk:
                used_batch_mode = self._consume_chunk(chunk, total_cycles, traces) or used_batch_mode
                total_cycles += len(chunk)
        else:
            for cycle, item in enumerate(sequencer):
                outputs = self.driver.drive(item)
                expected = self.scoreboard.resolve_expected(cycle, item)
                traces.append(self.monitor.observe(cycle, item, outputs, expected))
                self.scoreboard.check(cycle, item, outputs, expected)
                self.coverage.sample(item, outputs)
                total_cycles += 1
        return PythonUvmReport(
            name=name,
            passed=not self.scoreboard.failures,
            total_cycles=total_cycles,
            failures=tuple(self.scoreboard.failures),
            traces=tuple(traces),
            coverage=self.coverage.snapshot(),
            used_batch_mode=used_batch_mode,
        )

    def _consume_chunk(
        self,
        items: Sequence[PythonUvmSequenceItem],
        cycle_base: int,
        traces: List[TraceSample],
    ) -> bool:
        if not self.driver.supports_batch() or not self.scoreboard.supports_expected_batch(items):
            for idx, item in enumerate(items):
                cycle = cycle_base + idx
                outputs = self.driver.drive(item)
                expected = self.scoreboard.resolve_expected(cycle, item)
                traces.append(self.monitor.observe(cycle, item, outputs, expected))
                self.scoreboard.check(cycle, item, outputs, expected)
                self.coverage.sample(item, outputs)
            return False
        batch_outputs = self.driver.drive_batch(items)
        batch_expected = self.scoreboard.resolve_expected_batch(cycle_base, items)
        if batch_outputs is None or batch_expected is None:
            raise RuntimeError("batch-capable simulator/reference model returned no batch results")
        for idx, item in enumerate(items):
            cycle = cycle_base + idx
            outputs = dict(batch_outputs[idx])
            expected = dict(batch_expected[idx])
            traces.append(self.monitor.observe(cycle, item, outputs, expected))
            self.scoreboard.check(cycle, item, outputs, expected)
            self.coverage.sample(item, outputs)
        return True


def run_python_uvm_test(
    module: Any,
    sequence: Iterable[Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]]],
    *,
    simulator: Optional[object] = None,
    expected_fn: Optional[Callable[[int, Mapping[str, int]], Mapping[str, int]]] = None,
    reference_model: Optional[object] = None,
    coverage: Optional[PythonUvmCoverage] = None,
    name: str = "python_uvm",
    reset_before_run: bool = True,
    batch_cycles: int = 0,
) -> PythonUvmReport:
    """Run a lightweight UVM-style verification flow on the local simulator stack."""

    module = normalize_executable_module(module, context="run_python_uvm_test(...)")
    multi_clock = len(module.clock_domains) > 1
    normalized_sequence = tuple(
        sequence if isinstance(sequence, PythonUvmSequenceLibrary) else PythonUvmSequencer(sequence)
    )
    if multi_clock:
        if any(not item.active_domains for item in normalized_sequence):
            domain_names = ", ".join(domain.name for domain in module.clock_domains)
            raise ValueError(
                "run_python_uvm_test multi-clock sequences must provide explicit "
                f"active_domains for every item; module domains: {domain_names}. "
                "Wrap each step in PythonUvmSequenceItem(..., active_domains=(...))."
            )
        _validate_sequence_active_domains(module, normalized_sequence)
    else:
        require_single_clock_module(module, context="run_python_uvm_test")
    simulator = simulator if simulator is not None else PythonSimulator(module)
    reference_model = (
        reference_model
        if reference_model is not None
        else None if expected_fn is not None else PythonUvmReferenceModel(module)
    )
    env = PythonUvmEnv(
        simulator=simulator,
        scoreboard=PythonUvmScoreboard(
            expected_fn=expected_fn,
            reference_model=reference_model,
        ),
        coverage=coverage,
        reset_before_run=reset_before_run,
        batch_cycles=batch_cycles,
    )
    return env.run(normalized_sequence, name=name)


def dump_python_uvm_triage(
    report: PythonUvmReport,
    output_path: Path | str,
    *,
    protocol_checks: Optional[Sequence[object]] = None,
) -> Path:
    """Write a compact JSON triage bundle for a Python-side UVM run."""

    path = Path(output_path)
    payload = {
        "name": report.name,
        "passed": report.passed,
        "total_cycles": report.total_cycles,
        "coverage": report.coverage,
        "failures": [
            {
                "cycle": failure.cycle,
                "signal": failure.signal,
                "expected": failure.expected,
                "actual": failure.actual,
                "inputs": dict(failure.inputs),
            }
            for failure in report.failures
        ],
        "traces": [
            {
                "cycle": trace.cycle,
                "inputs": dict(trace.inputs),
                "outputs": dict(trace.outputs),
                "expected": dict(trace.expected),
                "active_domains": list(trace.active_domains),
            }
            for trace in report.traces
        ],
    }
    if protocol_checks is not None:
        payload["protocol_checks"] = [
            {
                "protocol": getattr(check, "protocol", "unknown"),
                "passed": bool(getattr(check, "passed", False)),
                "violations": [
                    {
                        "cycle": violation.cycle,
                        "rule": violation.rule,
                        "severity": violation.severity,
                        "message": violation.message,
                        "signal_values": dict(violation.signal_values),
                    }
                    for violation in getattr(check, "violations", ())
                ],
            }
            for check in protocol_checks
        ]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _normalize_item(
    item: Union[PythonUvmSequenceItem, StepVector, Mapping[str, int]],
) -> PythonUvmSequenceItem:
    if isinstance(item, PythonUvmSequenceItem):
        return PythonUvmSequenceItem(
            inputs=dict(item.inputs),
            expected=None if item.expected is None else dict(item.expected),
            label=item.label,
            active_domains=tuple(item.active_domains),
        )
    if isinstance(item, StepVector):
        return PythonUvmSequenceItem(inputs=dict(item.inputs), expected=dict(item.expected))
    if isinstance(item, Mapping):
        if any(key in item for key in ("inputs", "expected", "label", "active_domains")):
            inputs_payload = item.get("inputs")
            if not isinstance(inputs_payload, Mapping):
                raise TypeError(
                    "structured Python UVM items must provide an 'inputs' mapping"
                )
            expected_payload = item.get("expected")
            if expected_payload is not None and not isinstance(expected_payload, Mapping):
                raise TypeError(
                    "structured Python UVM items must provide an 'expected' mapping when present"
                )
            label_payload = item.get("label")
            active_domains = _normalize_active_domains_payload(item.get("active_domains", ()))
            return PythonUvmSequenceItem(
                inputs=dict(inputs_payload),
                expected=None if expected_payload is None else dict(expected_payload),
                label=None if label_payload is None else str(label_payload),
                active_domains=active_domains,
            )
        return PythonUvmSequenceItem(inputs=dict(item))
    raise TypeError(f"unsupported sequence item type: {type(item)!r}")
