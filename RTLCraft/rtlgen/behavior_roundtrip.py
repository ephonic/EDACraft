"""
rtlgen.behavior_roundtrip — DSL-to-Behavior Model Roundtrip Comparison

Allows generated DSL modules to be substituted back into ArchSimulator
for behavioral verification against the original ProcessingElement behavior.

Flow:
  1. DSL Module → Simulator wrapper (full comb + seq cycle-accurate)
  2. Run original PE behavior through CycleContext loop (golden trace)
  3. Run DSL through Simulator step() (RTL trace)
  4. Compare traces at event level

Reference: skills/plan_0525.md Sections 8, 10
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.arch_def import CycleContext, ProcessingElement
from rtlgen.core import Module


@dataclass
class RoundtripResult:
    """Result of a behavior roundtrip comparison."""

    module_name: str = ""
    passed: bool = False
    total_rtl_events: int = 0
    total_beh_events: int = 0
    matched_events: int = 0
    missing_events: int = 0
    extra_events: int = 0
    diffs: List[str] = field(default_factory=list)
    rtl_trace: Optional[List[Dict[str, Any]]] = None
    beh_trace: Optional[List[Dict[str, Any]]] = None


def dsl_to_behavior_adapter(module: Module) -> Callable[[CycleContext], None]:
    """Wrap a DSL Module as a CycleContext behavior function with full comb+seq.

    This adapter maintains state across calls and properly handles both
    combinational and sequential logic:
    - On first call: initializes Simulator wrapper, runs reset sequence
    - On subsequent calls: drives inputs, steps one full clock cycle, reads outputs

    Args:
        module: DSL Module to wrap

    Returns:
        A callable matching the CycleContext behavior signature:
        fn(ctx: CycleContext) -> None
    """
    from rtlgen.sim import Simulator

    input_names = [n for n in getattr(module, "_inputs", {}) if n not in ("clk", "rst_n")]
    output_names = list(getattr(module, "_outputs", {}).keys())

    # Build a Simulator once, lazily
    sim_holder: Dict[str, Any] = {"sim": None}

    def adapter_behavior(ctx: CycleContext):
        if sim_holder["sim"] is None:
            sim_holder["sim"] = Simulator(module)
            sim_holder["sim"].reset(cycles=2)

        sim = sim_holder["sim"]

        # Drive inputs from context — set directly in Simulator state
        for name in input_names:
            val = ctx.get_input(name, 0)
            if name in sim.state:
                sim.state[name] = val

        # Step one full clock cycle (comb → seq → commit → comb)
        sim.step(do_trace=False)

        # Read outputs from Simulator state
        for name in output_names:
            val = sim.get_int(name)
            ctx.set_output(name, val)

    return adapter_behavior


def dsl_to_behavior_adapter_simple(module: Module) -> Callable[[CycleContext], None]:
    """Simplified behavioral adapter for modules without full logic.

    Uses the module's port declarations to create a pass-through
    behavior that maps inputs to outputs by name. Useful for
    skeleton modules that don't have full logic yet.
    """
    input_names = [n for n in getattr(module, "_inputs", {}) if n not in ("clk", "rst_n")]
    output_names = list(getattr(module, "_outputs", {}).keys())

    def adapter_behavior(ctx: CycleContext):
        input_values = {}
        for name in input_names:
            input_values[name] = ctx.get_input(name, 0)

        for name in output_names:
            sig = getattr(module, name, None)
            if sig is not None and hasattr(sig, "_value"):
                ctx.set_output(name, sig._value)
            elif name in input_values:
                ctx.set_output(name, input_values[name])
            else:
                ctx.set_output(name, 0)

    return adapter_behavior


def run_roundtrip_comparison(
    pe: ProcessingElement,
    generated_module: Module,
    test_vectors: Optional[List[Dict[str, Any]]] = None,
    max_cycles: int = 100,
    key_signals: Optional[List[str]] = None,
) -> RoundtripResult:
    """Compare behavior model vs generated DSL for the same inputs.

    Runs both the original PE behavior and the adapted DSL behavior
    through the same execution loop and compares traces at the event level.

    Args:
        pe: Original ProcessingElement with behavior function
        generated_module: Generated DSL Module to compare against
        test_vectors: List of input dicts; auto-generated if None
        max_cycles: Maximum simulation cycles per test
        key_signals: Specific signals to track; auto-inferred if None

    Returns:
        RoundtripResult with comparison details
    """
    result = RoundtripResult(module_name=pe.name)

    # Generate test vectors if not provided
    if test_vectors is None:
        test_vectors = _generate_roundtrip_tests(pe, num_tests=5)

    if not test_vectors:
        result.diffs.append("No test vectors available for roundtrip comparison")
        return result

    # Create behavioral adapter for the generated module (full comb+seq)
    dsl_behavior = dsl_to_behavior_adapter(generated_module)

    # Run comparison for each test vector
    rtl_traces = []
    beh_traces = []

    for test in test_vectors:
        inputs = test.get("inputs", {})

        # Run original behavior model
        beh_trace = _run_behavior_trace(pe, inputs, max_cycles)
        beh_traces.append(beh_trace)

        # Run DSL adapter
        dsl_trace = _run_dsl_trace(dsl_behavior, inputs, max_cycles)
        rtl_traces.append(dsl_trace)

    # Compare traces
    all_diffs = []
    total_rtl = 0
    total_beh = 0
    total_matched = 0

    for rtl_trace, beh_trace in zip(rtl_traces, beh_traces):
        total_rtl += len(rtl_trace)
        total_beh += len(beh_trace)

        # Event-level comparison
        rtl_events = _extract_roundtrip_events(rtl_trace, key_signals)
        beh_events = _extract_roundtrip_events(beh_trace, key_signals)

        # Count matched events
        matched = 0
        rtl_idx = 0
        for beh_event in beh_events:
            found = False
            while rtl_idx < len(rtl_events):
                if _roundtrip_events_match(beh_event, rtl_events[rtl_idx]):
                    found = True
                    matched += 1
                    rtl_idx += 1
                    break
                rtl_idx += 1
            if not found:
                all_diffs.append(f"[EventMissing] {beh_event}")

        total_matched += matched

    result.total_rtl_events = total_rtl
    result.total_beh_events = total_beh
    result.matched_events = total_matched
    result.missing_events = total_beh - total_matched
    result.extra_events = max(0, total_rtl - total_beh)
    result.diffs = all_diffs
    result.passed = len(all_diffs) == 0

    # Store traces for debugging
    if rtl_traces:
        result.rtl_trace = rtl_traces[0]
    if beh_traces:
        result.beh_trace = beh_traces[0]

    return result


def _generate_roundtrip_tests(
    pe: ProcessingElement, num_tests: int = 5
) -> List[Dict[str, Any]]:
    """Generate test vectors for roundtrip comparison."""
    import random

    tests = []

    # Always include reset case
    reset_inputs = {}
    for port in pe.inputs:
        if port.name.lower() in ("rst_n", "reset", "rst"):
            reset_inputs[port.name] = 0
        else:
            reset_inputs[port.name] = 0
    tests.append({"inputs": reset_inputs})

    # Random patterns
    rng = random.Random(42)
    for _ in range(num_tests - 1):
        inputs = {}
        for port in pe.inputs:
            if port.name.lower() in ("rst_n", "reset", "rst"):
                inputs[port.name] = 1
            elif port.width <= 1:
                inputs[port.name] = rng.randint(0, 1)
            elif port.width <= 8:
                inputs[port.name] = rng.randint(0, 255)
            else:
                inputs[port.name] = rng.randint(0, min(0xFFFF, (1 << port.width) - 1))
        tests.append({"inputs": inputs})

    return tests


def _run_behavior_trace(
    pe: ProcessingElement,
    inputs: Dict[str, Any],
    max_cycles: int,
) -> List[Dict[str, Any]]:
    """Run original PE behavior for multiple cycles, collecting trace."""
    trace = []

    if pe.behavior is None:
        return trace

    state = {}
    for s in pe.state:
        state[s.name] = s.default if s.default is not None else 0

    for cycle in range(max_cycles):
        ctx = CycleContext(
            cycle=cycle,
            inputs=dict(inputs),
            state=dict(state),
        )

        try:
            pe.behavior(ctx)
        except Exception:
            break

        # Record cycle output
        frame = {"_cycle": cycle}
        frame.update(ctx.outputs)
        frame.update(ctx.next_state)
        trace.append(frame)

        # Update state
        for k, v in ctx.next_state.items():
            state[k] = v

        # Check for done signal
        if ctx.outputs.get("done", 0):
            break

    return trace


def _run_dsl_trace(
    dsl_behavior: Callable[[CycleContext], None],
    inputs: Dict[str, Any],
    max_cycles: int,
) -> List[Dict[str, Any]]:
    """Run DSL adapter behavior for multiple cycles, collecting trace."""
    trace = []
    state = {}

    for cycle in range(max_cycles):
        ctx = CycleContext(
            cycle=cycle,
            inputs=dict(inputs),
            state=dict(state),
        )

        try:
            dsl_behavior(ctx)
        except Exception:
            break

        frame = {"_cycle": cycle}
        frame.update(ctx.outputs)
        frame.update(ctx.next_state)
        trace.append(frame)

        for k, v in ctx.next_state.items():
            state[k] = v

        if ctx.outputs.get("done", 0):
            break

    return trace


def _extract_roundtrip_events(
    trace: List[Dict[str, Any]],
    key_signals: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract events from a roundtrip trace."""
    if not trace:
        return []

    if key_signals is None:
        # Infer key signals from first frame
        sample = trace[0] if trace else {}
        key_signals = [
            n for n in sample
            if n not in ("_cycle",)
            and any(kw in n.lower() for kw in [
                "valid", "ready", "fire", "done", "retire",
                "issue", "dispatch", "writeback",
                "req", "rsp", "hit", "miss",
            ])
        ]
        if not key_signals:
            key_signals = [n for n in sample if n != "_cycle"][:8]

    events = []
    prev = {}

    for cycle_idx, frame in enumerate(trace):
        cycle_events = {"_cycle": cycle_idx}
        has_event = True  # Always record if there's data

        for sig in key_signals:
            val = frame.get(sig, 0)
            prev_val = prev.get(sig, 0)

            if val != prev_val and val != 0:
                cycle_events[sig] = val

            prev[sig] = val

        events.append(cycle_events)

    return events


def _roundtrip_events_match(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
) -> bool:
    """Check if an actual event matches the expected event."""
    for key, val in expected.items():
        if key == "_cycle":
            continue
        if key not in actual:
            return False
        if actual[key] != val:
            return False
    return True
