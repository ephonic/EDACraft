"""Differential cosimulation helpers between compiled simulators and emitted RTL."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import rtlgen.cosim as rtl_cosim


@dataclass(frozen=True)
class CosimMismatch:
    cycle: int
    signal: str
    expected: int
    actual: int


@dataclass(frozen=True)
class DslRtlCosimReport:
    module_name: str
    mode: str
    vector_count: int
    dsl_matches_rtl: bool
    compiled_matches_rtl: bool
    mismatches: Tuple[CosimMismatch, ...]
    rtl_trace: Tuple[Mapping[str, int], ...]
    compiled_trace: Tuple[Mapping[str, int], ...]
    skipped_reason: Optional[str] = None


class CosimUnknownValueError(RuntimeError):
    """Raised when emitted RTL exposes X/Z values that the structured trace cannot compare."""


@dataclass(frozen=True)
class _DslClockDomainInfo:
    name: str
    reset_signal: Optional[str] = None
    reset_async: bool = False
    reset_active_low: bool = False


def run_dsl_rtl_cosim(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str = "auto",
    clock_period_ns: int = 10,
    build_dir: Optional[Path | str] = None,
    valid_signal: Optional[str] = None,
    flush_cycles: int = 0,
    flush_inputs: Optional[Mapping[str, int]] = None,
) -> DslRtlCosimReport:
    """Compare a compiled simulator built from a DSL module against emitted RTL."""

    clock_domains = _dsl_clock_domains(module)
    if len(clock_domains) > 1:
        domains = ", ".join(domain.name for domain in clock_domains)
        raise ValueError(
            "run_dsl_rtl_cosim(...) is intended for single-clock modules; "
            f"found multi-clock domains: {domains}. "
            "Use run_dsl_multiclock_rtl_cosim(...) for explicit domain-step cosim."
        )
    resolved_mode = _resolve_mode(module, mode, clock_domains=clock_domains)
    drive_vectors = _extend_vectors(vectors, flush_cycles=flush_cycles, flush_inputs=flush_inputs)
    try:
        dsl_trace = _run_reference_trace(
            module,
            drive_vectors,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domains[0] if clock_domains else None,
        )
        rtl_trace = _run_iverilog_trace(
            module,
            drive_vectors,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domains[0] if clock_domains else None,
        )
    except FileNotFoundError as exc:
        return DslRtlCosimReport(
            module_name=module.name,
            mode=resolved_mode,
            vector_count=len(drive_vectors),
            dsl_matches_rtl=False,
            compiled_matches_rtl=False,
            mismatches=(),
            rtl_trace=(),
            compiled_trace=(),
            skipped_reason=str(exc),
        )

    compiled_trace = _run_compiled_trace(
        module,
        drive_vectors,
        mode=resolved_mode,
        build_dir=build_dir,
        clock_domain=clock_domains[0] if clock_domains else None,
    )
    outputs = [sig.name for sig in module._outputs.values()]
    filtered_dsl_trace = _filter_trace_by_valid(dsl_trace, valid_signal)
    filtered_rtl_trace = _filter_trace_by_valid(rtl_trace, valid_signal)
    filtered_compiled_trace = _filter_trace_by_valid(compiled_trace, valid_signal)
    dsl_matches_rtl = not _collect_mismatches(outputs, filtered_dsl_trace, filtered_rtl_trace)
    mismatches = _collect_mismatches(outputs, filtered_compiled_trace, filtered_rtl_trace)

    return DslRtlCosimReport(
        module_name=module.name,
        mode=resolved_mode,
        vector_count=len(drive_vectors),
        dsl_matches_rtl=dsl_matches_rtl,
        compiled_matches_rtl=not mismatches,
        mismatches=tuple(mismatches),
        rtl_trace=tuple(dict(step) for step in filtered_rtl_trace),
        compiled_trace=tuple(dict(step) for step in filtered_compiled_trace),
        skipped_reason=None,
    )


def run_dsl_multiclock_rtl_cosim(
    module,
    vectors: Sequence[object],
    *,
    build_dir: Optional[Path | str] = None,
    valid_signal: Optional[str] = None,
) -> DslRtlCosimReport:
    """Compare lowered Python, compiled, and emitted RTL on explicit multi-clock events."""

    clock_domains = _dsl_clock_domains(module)
    if len(clock_domains) < 2:
        raise ValueError(
            "run_dsl_multiclock_rtl_cosim(...) requires a DSL module with multiple clock domains"
        )
    normalized_vectors = _normalize_multiclock_vectors(vectors, clock_domains)
    try:
        dsl_trace = _run_multiclock_reference_trace(module, normalized_vectors)
        rtl_trace = _run_multiclock_iverilog_trace(module, normalized_vectors)
    except FileNotFoundError as exc:
        return DslRtlCosimReport(
            module_name=module.name,
            mode="multi_clock",
            vector_count=len(normalized_vectors),
            dsl_matches_rtl=False,
            compiled_matches_rtl=False,
            mismatches=(),
            rtl_trace=(),
            compiled_trace=(),
            skipped_reason=str(exc),
        )

    compiled_trace = _run_multiclock_compiled_trace(
        module,
        normalized_vectors,
        build_dir=build_dir,
    )
    outputs = [sig.name for sig in module._outputs.values()]
    filtered_dsl_trace = _filter_trace_by_valid(dsl_trace, valid_signal)
    filtered_rtl_trace = _filter_trace_by_valid(rtl_trace, valid_signal)
    filtered_compiled_trace = _filter_trace_by_valid(compiled_trace, valid_signal)
    dsl_matches_rtl = not _collect_mismatches(outputs, filtered_dsl_trace, filtered_rtl_trace)
    mismatches = _collect_mismatches(outputs, filtered_compiled_trace, filtered_rtl_trace)

    return DslRtlCosimReport(
        module_name=module.name,
        mode="multi_clock",
        vector_count=len(normalized_vectors),
        dsl_matches_rtl=dsl_matches_rtl,
        compiled_matches_rtl=not mismatches,
        mismatches=tuple(mismatches),
        rtl_trace=tuple(dict(step) for step in filtered_rtl_trace),
        compiled_trace=tuple(dict(step) for step in filtered_compiled_trace),
        skipped_reason=None,
    )


def _extend_vectors(
    vectors: Sequence[Mapping[str, int]],
    *,
    flush_cycles: int,
    flush_inputs: Optional[Mapping[str, int]],
) -> Tuple[Mapping[str, int], ...]:
    base = tuple(dict(vector) for vector in vectors)
    if flush_cycles <= 0:
        return base
    flush_vector = dict(flush_inputs or {})
    return base + tuple(dict(flush_vector) for _ in range(flush_cycles))


def _filter_trace_by_valid(
    trace: Sequence[Mapping[str, int]],
    valid_signal: Optional[str],
) -> Tuple[Mapping[str, int], ...]:
    if valid_signal is None:
        return tuple(dict(step) for step in trace)
    return tuple(dict(step) for step in trace if int(step.get(valid_signal, 0)) == 1)


def _run_compiled_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    build_dir: Optional[Path | str],
    clock_domain: Optional[_DslClockDomainInfo],
) -> Tuple[Mapping[str, int], ...]:
    from rtlgen_x.dsl import build_compiled_simulator_from_dsl

    compiled = build_compiled_simulator_from_dsl(module, build_dir=build_dir)
    try:
        current_inputs: Dict[str, int] = {name: 0 for name in compiled.input_names}
        if mode == "seq":
            _apply_reset_preamble(compiled, current_inputs, clock_domain=clock_domain)
        trace: List[Mapping[str, int]] = []
        for vector in vectors:
            for name, value in vector.items():
                if name in current_inputs:
                    current_inputs[name] = int(value)
            trace.append(dict(compiled.step(current_inputs)))
        return tuple(trace)
    finally:
        compiled.close()


def _apply_reset_preamble(
    compiled,
    current_inputs: Dict[str, int],
    *,
    clock_domain: Optional[_DslClockDomainInfo],
) -> None:
    if clock_domain is not None and clock_domain.reset_signal in current_inputs:
        active_value = 0 if clock_domain.reset_active_low else 1
        inactive_value = 1 - active_value
        current_inputs[clock_domain.reset_signal] = active_value
        compiled.step(current_inputs)
        compiled.step(current_inputs)
        current_inputs[clock_domain.reset_signal] = inactive_value
        return
    if "rst" in current_inputs:
        current_inputs["rst"] = 1
        compiled.step(current_inputs)
        compiled.step(current_inputs)
        current_inputs["rst"] = 0
        return
    if "rst_n" in current_inputs:
        current_inputs["rst_n"] = 0
        compiled.step(current_inputs)
        compiled.step(current_inputs)
        current_inputs["rst_n"] = 1


def _resolve_mode(
    module,
    mode: str,
    *,
    clock_domains: Sequence[_DslClockDomainInfo] = (),
) -> str:
    if mode == "auto":
        return "seq" if clock_domains else "comb"
    return mode


def _use_dsl_module(module) -> bool:
    if getattr(module, "_inputs", None):
        first_input = next(iter(module._inputs.values()))
        return type(first_input).__module__.startswith("rtlgen_x.")
    if getattr(module, "_outputs", None):
        first_output = next(iter(module._outputs.values()))
        return type(first_output).__module__.startswith("rtlgen_x.")
    return False


def _run_reference_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    clock_period_ns: int,
    clock_domain: Optional[_DslClockDomainInfo],
) -> Tuple[Mapping[str, int], ...]:
    if _use_dsl_module(module):
        from rtlgen_x.dsl import lower_dsl_module_to_sim
        from rtlgen_x.sim.python_runtime import PythonSimulator

        sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
        outputs = [sig.name for sig in module._outputs.values()]
        input_names = {sig.name for sig in module._inputs.values()}
        current_inputs = {name: 0 for name in input_names}
        if mode == "seq":
            _apply_reset_preamble(sim, current_inputs, clock_domain=clock_domain)
        trace = []
        for cycle, vector in enumerate(vectors):
            for name, value in vector.items():
                if name in current_inputs:
                    current_inputs[name] = int(value)
            outputs_step = sim.step(current_inputs)
            trace.append({"_cycle": cycle, **{name: int(outputs_step[name]) for name in outputs}})
        return tuple(trace)

    from rtlgen import Simulator

    sim = Simulator(module, clock_period_ns=clock_period_ns)
    outputs = [sig.name for sig in module._outputs.values()]
    input_names = {sig.name for sig in module._inputs.values()}
    if mode == "seq":
        if clock_domain is not None and clock_domain.reset_signal in input_names:
            if clock_domain.reset_active_low:
                sim.set(clock_domain.reset_signal, 0)
                for _ in range(2):
                    sim.step(do_trace=False)
                sim.set(clock_domain.reset_signal, 1)
            else:
                sim.reset(clock_domain.reset_signal, cycles=2)
        elif "rst" in input_names:
            sim.reset("rst", cycles=2)
        elif "rst_n" in input_names:
            sim.reset("rst_n", cycles=2)
    trace = []
    for cycle, vector in enumerate(vectors):
        for name, value in vector.items():
            if name in input_names:
                sim.set(name, value)
        if mode == "seq":
            sim.step(do_trace=False)
        else:
            sim._eval_comb()
            sim.time_ns += clock_period_ns
        trace.append({"_cycle": cycle, **{name: sim.get_int(name) for name in outputs}})
    return tuple(trace)


def _run_iverilog_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    clock_period_ns: int,
    clock_domain: Optional[_DslClockDomainInfo],
) -> Tuple[Mapping[str, int], ...]:
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_sv_tb(
        module,
        module_name,
        [dict(vector) for vector in vectors],
        mode,
        clock_period_ns,
        clock_domain=clock_domain,
    )
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="rtlgen_x_cosim_dut_") as tmpdir:
        dut_path = Path(tmpdir) / f"{module.name}.sv"
        dut_path.write_text(dut_src, encoding="utf-8")
        stdout = rtl_cosim._compile_and_run(tb_sv, [str(dut_path)])
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"iverilog simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return tuple(dict(step) for step in rtl_cosim._parse_sv_output(stdout))


def _collect_mismatches(
    outputs: Sequence[str],
    actual_trace: Sequence[Mapping[str, int]],
    expected_trace: Sequence[Mapping[str, int]],
) -> Tuple[CosimMismatch, ...]:
    mismatches: List[CosimMismatch] = []
    for cycle, (actual_step, expected_step) in enumerate(zip(actual_trace, expected_trace)):
        for signal in outputs:
            _raise_on_unknown_trace_value("actual", signal, cycle, actual_step.get(f"{signal}__raw"))
            _raise_on_unknown_trace_value("expected", signal, cycle, expected_step.get(f"{signal}__raw"))
            if signal not in actual_step or signal not in expected_step:
                available_actual = ", ".join(sorted(actual_step.keys()))
                available_expected = ", ".join(sorted(expected_step.keys()))
                raise KeyError(
                    "cosim trace is missing expected output signal "
                    f"'{signal}' at cycle {cycle}; "
                    f"actual keys: [{available_actual}], expected keys: [{available_expected}]"
                )
            actual = int(actual_step[signal])
            expected = int(expected_step[signal])
            if actual != expected:
                mismatches.append(
                    CosimMismatch(
                        cycle=cycle,
                        signal=signal,
                        expected=expected,
                        actual=actual,
                    )
                )
    return tuple(mismatches)


def _raise_on_unknown_trace_value(trace_role: str, signal: str, cycle: int, raw_value: object) -> None:
    if not (isinstance(raw_value, str) and any(ch in raw_value.lower() for ch in ("x", "z"))):
        return
    trace_label = "emitted RTL trace" if trace_role == "expected" else "compiled/reference trace"
    raise CosimUnknownValueError(
        f"{trace_label} observed unknown value for '{signal}' at cycle {cycle}: {raw_value!r}. "
        "This usually means the emitted RTL left state or array storage uninitialized "
        "while the Python/compiled simulator assumed a concrete initial value."
    )


def _generate_sv_tb(
    module,
    module_name: str,
    vectors: Sequence[Mapping[str, int]],
    mode: str,
    clock_period_ns: int,
    *,
    clock_domain: Optional[_DslClockDomainInfo],
) -> str:
    inputs = list(module._inputs.values())
    outputs = list(module._outputs.values())
    clock_name = clock_domain.name if clock_domain is not None else None
    has_clk = bool(clock_name)
    is_seq = mode == "seq"

    lines: List[str] = ["`timescale 1ns/1ps", "module tb_top;"]
    if is_seq and has_clk:
        lines.append(f"    reg {clock_name} = 0;")
    for sig in inputs:
        if sig.name == clock_name and is_seq:
            continue
        width = f"[{sig.width - 1}:0] " if sig.width > 1 else ""
        lines.append(f"    reg {width}{sig.name};")
    for sig in outputs:
        width = f"[{sig.width - 1}:0] " if sig.width > 1 else ""
        lines.append(f"    wire {width}{sig.name};")
    lines.append("")
    lines.append(f"    {module_name} u_dut (")
    port_items = [f"        .{sig.name}({sig.name})" for sig in inputs + outputs]
    for idx, item in enumerate(port_items):
        suffix = "," if idx < len(port_items) - 1 else ""
        lines.append(f"{item}{suffix}")
    lines.append("    );")
    lines.append("")
    if is_seq and has_clk:
        lines.append(f"    always #{clock_period_ns // 2} {clock_name} = ~{clock_name};")
        lines.append("")
    lines.append("    initial begin")
    for sig in inputs:
        if sig.name == clock_name and is_seq:
            continue
        lines.append(f"        {sig.name} = 0;")
    lines.append("        #0;")
    input_names = {sig.name for sig in inputs}
    if is_seq and has_clk:
        if clock_domain is not None and clock_domain.reset_signal in input_names:
            active_value = 0 if clock_domain.reset_active_low else 1
            inactive_value = 1 - active_value
            lines.append(
                f"        {clock_domain.reset_signal} = {rtl_cosim._to_sv_literal(active_value)};"
            )
            lines.append(f"        @(posedge {clock_name});")
            lines.append(f"        @(posedge {clock_name});")
            lines.append(
                f"        {clock_domain.reset_signal} = {rtl_cosim._to_sv_literal(inactive_value)};"
            )
        elif "rst" in input_names:
            lines.append("        rst = 1;")
            lines.append(f"        @(posedge {clock_name});")
            lines.append(f"        @(posedge {clock_name});")
            lines.append("        rst = 0;")
        elif "rst_n" in input_names:
            lines.append("        rst_n = 0;")
            lines.append(f"        @(posedge {clock_name});")
            lines.append(f"        @(posedge {clock_name});")
            lines.append("        rst_n = 1;")
        lines.append(f"        @(negedge {clock_name});")
    last_vals: Dict[str, int] = {name: 0 for name in input_names if name != "clk"}
    for cycle, vector in enumerate(vectors):
        for sig in inputs:
            if sig.name == clock_name and is_seq:
                continue
            value = int(vector.get(sig.name, last_vals.get(sig.name, 0)))
            if last_vals.get(sig.name) != value:
                lines.append(f"        {sig.name} = {rtl_cosim._to_sv_literal(value)};")
            last_vals[sig.name] = value
        if is_seq and has_clk:
            lines.append(f"        @(posedge {clock_name});")
            lines.append("        #1;")
        else:
            lines.append(f"        #{clock_period_ns};")
        out_parts = [f"{sig.name}=%0d" for sig in outputs]
        out_vars = [sig.name for sig in outputs]
        lines.append(
            f"        $display(\"CYCLE %0d {' '.join(out_parts)}\", {cycle}, {', '.join(out_vars)});"
        )
        if is_seq and has_clk and cycle != len(vectors) - 1:
            lines.append(f"        @(negedge {clock_name});")
    lines.append('        $display("COSIM_DONE");')
    lines.append("        $finish;")
    lines.append("    end")
    lines.append("endmodule")
    return "\n".join(lines)


def _run_multiclock_reference_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
) -> Tuple[Mapping[str, int], ...]:
    from rtlgen_x.dsl import lower_dsl_module_to_sim
    from rtlgen_x.sim.python_runtime import PythonSimulator

    sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
    outputs = [sig.name for sig in module._outputs.values()]
    input_names = {sig.name for sig in module._inputs.values()}
    current_inputs = {name: 0 for name in input_names}
    trace = []
    for cycle, (vector, active_domains) in enumerate(vectors):
        for name, value in vector.items():
            if name in current_inputs:
                current_inputs[name] = int(value)
        outputs_step = sim.step_clocks(current_inputs, active_domains)
        trace.append({"_cycle": cycle, **{name: int(outputs_step[name]) for name in outputs}})
    return tuple(trace)


def _run_multiclock_compiled_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    build_dir: Optional[Path | str],
) -> Tuple[Mapping[str, int], ...]:
    from rtlgen_x.dsl import build_compiled_simulator_from_dsl

    compiled = build_compiled_simulator_from_dsl(module, build_dir=build_dir)
    try:
        outputs = [sig.name for sig in module._outputs.values()]
        current_inputs: Dict[str, int] = {name: 0 for name in compiled.input_names}
        trace: List[Mapping[str, int]] = []
        for cycle, (vector, active_domains) in enumerate(vectors):
            for name, value in vector.items():
                if name in current_inputs:
                    current_inputs[name] = int(value)
            outputs_step = compiled.step_clocks(current_inputs, active_domains)
            trace.append({"_cycle": cycle, **{name: int(outputs_step[name]) for name in outputs}})
        return tuple(trace)
    finally:
        compiled.close()


def _run_multiclock_iverilog_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
) -> Tuple[Mapping[str, int], ...]:
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    clock_domains = _dsl_clock_domains(module)
    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_multiclock_sv_tb(
        module,
        module_name,
        vectors,
        clock_domains=clock_domains,
    )
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="rtlgen_x_cosim_multiclk_") as tmpdir:
        dut_path = Path(tmpdir) / f"{module.name}.sv"
        dut_path.write_text(dut_src, encoding="utf-8")
        stdout = rtl_cosim._compile_and_run(tb_sv, [str(dut_path)])
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"iverilog simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return _parse_sv_output_with_unknowns(stdout)


def _generate_multiclock_sv_tb(
    module,
    module_name: str,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    clock_domains: Sequence[_DslClockDomainInfo],
) -> str:
    inputs = list(module._inputs.values())
    outputs = list(module._outputs.values())
    managed_clocks = {domain.name for domain in clock_domains}

    lines: List[str] = ["`timescale 1ns/1ps", "module tb_top;"]
    for sig in inputs:
        width = f"[{sig.width - 1}:0] " if sig.width > 1 else ""
        init = " = 0" if sig.name in managed_clocks else ""
        lines.append(f"    reg {width}{sig.name}{init};")
    for sig in outputs:
        width = f"[{sig.width - 1}:0] " if sig.width > 1 else ""
        lines.append(f"    wire {width}{sig.name};")
    lines.append("")
    lines.append(f"    {module_name} u_dut (")
    port_items = [f"        .{sig.name}({sig.name})" for sig in inputs + outputs]
    for idx, item in enumerate(port_items):
        suffix = "," if idx < len(port_items) - 1 else ""
        lines.append(f"{item}{suffix}")
    lines.append("    );")
    lines.append("")
    lines.append("    initial begin")
    for sig in inputs:
        if sig.name in managed_clocks:
            continue
        lines.append(f"        {sig.name} = 0;")
    lines.append("        #0;")
    last_vals: Dict[str, int] = {sig.name: 0 for sig in inputs if sig.name not in managed_clocks}
    for cycle, (vector, active_domains) in enumerate(vectors):
        for sig in inputs:
            if sig.name in managed_clocks:
                continue
            value = int(vector.get(sig.name, last_vals.get(sig.name, 0)))
            if last_vals.get(sig.name) != value:
                lines.append(f"        {sig.name} = {rtl_cosim._to_sv_literal(value)};")
            last_vals[sig.name] = value
        for domain_name in active_domains:
            lines.append(f"        {domain_name} = 1'b1;")
        lines.append("        #1;")
        out_parts = [f"{sig.name}=%0d" for sig in outputs]
        out_vars = [sig.name for sig in outputs]
        lines.append(
            f"        $display(\"CYCLE %0d {' '.join(out_parts)}\", {cycle}, {', '.join(out_vars)});"
        )
        for domain_name in active_domains:
            lines.append(f"        {domain_name} = 1'b0;")
        if cycle != len(vectors) - 1:
            lines.append("        #1;")
    lines.append('        $display("COSIM_DONE");')
    lines.append("        $finish;")
    lines.append("    end")
    lines.append("endmodule")
    return "\n".join(lines)


def _parse_sv_output_with_unknowns(stdout: str) -> Tuple[Mapping[str, int], ...]:
    trace = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("CYCLE "):
            continue
        prefix, _, rest = line.partition(" ")
        if prefix != "CYCLE":
            continue
        cycle_text, _, payload = rest.partition(" ")
        if not cycle_text.isdigit():
            continue
        snap: Dict[str, object] = {"_cycle": int(cycle_text)}
        for token in payload.split():
            if "=" not in token:
                continue
            name, raw_value = token.split("=", 1)
            if raw_value.isdigit():
                snap[name] = int(raw_value)
            else:
                snap[f"{name}__raw"] = raw_value
        trace.append(snap)
    return tuple(trace)


def _normalize_multiclock_vectors(
    vectors: Sequence[object],
    clock_domains: Sequence[_DslClockDomainInfo],
) -> Tuple[tuple[Mapping[str, int], tuple[str, ...]], ...]:
    allowed_domains = tuple(domain.name for domain in clock_domains)
    managed_clocks = set(allowed_domains)
    normalized = []
    for vector in vectors:
        inputs, active_domains = _decode_multiclock_vector(vector, allowed_domains)
        driven_clocks = sorted(set(inputs) & managed_clocks)
        if driven_clocks:
            joined = ", ".join(driven_clocks)
            raise ValueError(
                "multi-clock cosim vectors must not drive managed clock signals directly; "
                f"use active_domains instead (found: {joined})"
            )
        normalized.append((inputs, active_domains))
    return tuple(normalized)


def _decode_multiclock_vector(
    vector: object,
    allowed_domains: Sequence[str],
) -> tuple[Mapping[str, int], tuple[str, ...]]:
    if isinstance(vector, Mapping):
        if any(key in vector for key in ("inputs", "active_domains")):
            inputs_payload = vector.get("inputs")
            if not isinstance(inputs_payload, Mapping):
                raise TypeError(
                    "structured multi-clock cosim vectors must provide an 'inputs' mapping"
                )
            return dict(inputs_payload), _normalize_active_domains(
                vector.get("active_domains", ()),
                allowed_domains,
            )
        return dict(vector), ()
    if (
        isinstance(vector, tuple)
        and len(vector) == 2
        and isinstance(vector[0], Mapping)
    ):
        return dict(vector[0]), _normalize_active_domains(vector[1], allowed_domains)
    raise TypeError(
        "multi-clock cosim vectors must be input mappings, structured step mappings, "
        "or (inputs, active_domains) tuples"
    )


def _normalize_active_domains(
    active_domains: Mapping[str, bool] | Sequence[str],
    allowed_domains: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(active_domains, Mapping):
        selected = [name for name, enabled in active_domains.items() if enabled]
    else:
        selected = list(active_domains)
    ordered = tuple(dict.fromkeys(selected))
    unknown = sorted(set(ordered) - set(allowed_domains))
    if unknown:
        joined = ", ".join(unknown)
        raise KeyError(f"unknown clock domains: {joined}")
    return ordered


def _dsl_clock_domains(module) -> Tuple[_DslClockDomainInfo, ...]:
    clock_specs: Dict[str, _DslClockDomainInfo] = {}
    ordered_clock_names: List[str] = []
    for clk, rst, reset_async, reset_active_low, _body in getattr(module, "_seq_blocks", ()):
        if clk is None:
            continue
        clk_name = getattr(clk, "name", str(clk))
        rst_name, rst_async, rst_active_low = _resolve_dsl_reset(rst, reset_async, reset_active_low)
        info = _DslClockDomainInfo(
            name=clk_name,
            reset_signal=rst_name,
            reset_async=bool(rst_async),
            reset_active_low=bool(rst_active_low),
        )
        previous = clock_specs.get(clk_name)
        if previous is None:
            ordered_clock_names.append(clk_name)
            clock_specs[clk_name] = info
            continue
        if previous != info:
            raise ValueError(
                "DSL cosim clock analysis found conflicting reset semantics on the same "
                f"clock '{clk_name}': previous={previous}, current={info}"
            )
    return tuple(clock_specs[name] for name in ordered_clock_names)


def _resolve_dsl_reset(
    rst,
    reset_async: bool,
    reset_active_low: bool,
) -> tuple[Optional[str], bool, bool]:
    if rst is None:
        return None, reset_async, reset_active_low
    rst_name = getattr(rst, "name", None)
    if rst_name:
        return rst_name, reset_async, reset_active_low
    expr = getattr(rst, "_expr", None)
    if expr is None:
        return None, reset_async, reset_active_low
    if getattr(expr, "op", None) == "~":
        inner = getattr(expr, "operand", None)
        if hasattr(inner, "signal") and getattr(inner.signal, "name", None):
            return inner.signal.name, True, True
        if getattr(inner, "name", None):
            return inner.name, True, True
    return None, reset_async, reset_active_low


def _infer_top_sv_module_name(source: str, module) -> str:
    module_names = [
        line.strip()[len("module ") :].strip().split("(", 1)[0].strip()
        for line in source.splitlines()
        if line.strip().startswith("module ")
    ]
    for candidate in (
        getattr(module, "name", None),
        getattr(module, "_type_name", None),
        module.__class__.__name__,
    ):
        if candidate and candidate in module_names:
            return candidate
    if module_names:
        return module_names[-1]
    return getattr(module, "name", None) or getattr(module, "_type_name", "dut")
