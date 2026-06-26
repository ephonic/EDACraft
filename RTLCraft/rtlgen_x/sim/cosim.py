"""Differential cosimulation helpers between compiled simulators and emitted RTL."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import os
import subprocess
import shutil
import tarfile
import tempfile
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
    rtl_backend: str
    vector_count: int
    dsl_matches_rtl: bool
    compiled_matches_rtl: bool
    mismatches: Tuple[CosimMismatch, ...]
    rtl_trace: Tuple[Mapping[str, int], ...]
    compiled_trace: Tuple[Mapping[str, int], ...]
    skipped_reason: Optional[str] = None
    cache_enabled: bool = False
    cache_hit: bool = False
    cache_key: Optional[str] = None
    cache_dir: Optional[str] = None


class CosimUnknownValueError(RuntimeError):
    """Raised when emitted RTL exposes X/Z values that the structured trace cannot compare."""


@dataclass(frozen=True)
class _DslClockDomainInfo:
    name: str
    reset_signal: Optional[str] = None
    reset_async: bool = False
    reset_active_low: bool = False


@dataclass(frozen=True)
class _ExternalSimRunResult:
    stdout: str
    cache_enabled: bool
    cache_hit: bool
    cache_key: Optional[str]
    cache_dir: Optional[str]


def run_dsl_rtl_cosim(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str = "auto",
    rtl_backend: str = "auto",
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
    resolved_backend = _resolve_rtl_backend(rtl_backend)
    drive_vectors = _extend_vectors(vectors, flush_cycles=flush_cycles, flush_inputs=flush_inputs)
    try:
        dsl_trace = _run_reference_trace(
            module,
            drive_vectors,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domains[0] if clock_domains else None,
        )
        rtl_trace, rtl_run = _run_rtl_trace(
            module,
            drive_vectors,
            backend=resolved_backend,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domains[0] if clock_domains else None,
            build_dir=build_dir,
        )
    except FileNotFoundError as exc:
        return DslRtlCosimReport(
            module_name=module.name,
            mode=resolved_mode,
            rtl_backend=resolved_backend,
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
        rtl_backend=resolved_backend,
        vector_count=len(drive_vectors),
        dsl_matches_rtl=dsl_matches_rtl,
        compiled_matches_rtl=not mismatches,
        mismatches=tuple(mismatches),
        rtl_trace=tuple(dict(step) for step in filtered_rtl_trace),
        compiled_trace=tuple(dict(step) for step in filtered_compiled_trace),
        skipped_reason=None,
        cache_enabled=rtl_run.cache_enabled,
        cache_hit=rtl_run.cache_hit,
        cache_key=rtl_run.cache_key,
        cache_dir=rtl_run.cache_dir,
    )


def run_dsl_multiclock_rtl_cosim(
    module,
    vectors: Sequence[object],
    *,
    rtl_backend: str = "auto",
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
    resolved_backend = _resolve_rtl_backend(rtl_backend)
    try:
        dsl_trace = _run_multiclock_reference_trace(module, normalized_vectors)
        rtl_trace, rtl_run = _run_multiclock_rtl_trace(
            module,
            normalized_vectors,
            backend=resolved_backend,
            build_dir=build_dir,
        )
    except FileNotFoundError as exc:
        return DslRtlCosimReport(
            module_name=module.name,
            mode="multi_clock",
            rtl_backend=resolved_backend,
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
        rtl_backend=resolved_backend,
        vector_count=len(normalized_vectors),
        dsl_matches_rtl=dsl_matches_rtl,
        compiled_matches_rtl=not mismatches,
        mismatches=tuple(mismatches),
        rtl_trace=tuple(dict(step) for step in filtered_rtl_trace),
        compiled_trace=tuple(dict(step) for step in filtered_compiled_trace),
        skipped_reason=None,
        cache_enabled=rtl_run.cache_enabled,
        cache_hit=rtl_run.cache_hit,
        cache_key=rtl_run.cache_key,
        cache_dir=rtl_run.cache_dir,
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
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
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
    return (
        tuple(dict(step) for step in rtl_cosim._parse_sv_output(stdout)),
        _ExternalSimRunResult(
            stdout=stdout,
            cache_enabled=False,
            cache_hit=False,
            cache_key=None,
            cache_dir=None,
        ),
    )


def _run_rtl_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    backend: str,
    mode: str,
    clock_period_ns: int,
    clock_domain: Optional[_DslClockDomainInfo],
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    if backend == "verilator":
        return _run_verilator_trace(
            module,
            vectors,
            mode=mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domain,
            build_dir=build_dir,
        )
    if backend == "vcs":
        return _run_vcs_trace(
            module,
            vectors,
            mode=mode,
            clock_period_ns=clock_period_ns,
            clock_domain=clock_domain,
            build_dir=build_dir,
        )
    return _run_iverilog_trace(
        module,
        vectors,
        mode=mode,
        clock_period_ns=clock_period_ns,
        clock_domain=clock_domain,
    )


def _run_verilator_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    clock_period_ns: int,
    clock_domain: Optional[_DslClockDomainInfo],
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    verilator = _find_local_verilator()
    if verilator is None:
        raise FileNotFoundError("verilator")
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_sv_tb_runtime_vectors(
        module,
        module_name,
        mode,
        clock_period_ns,
        clock_domain=clock_domain,
    )
    vector_text = _encode_single_clock_vectors(
        module,
        vectors,
        mode=mode,
        clock_domain=clock_domain,
    )
    run_result = _compile_and_run_with_verilator(
        verilator,
        tb_sv=tb_sv,
        dut_src=dut_src,
        top_module="tb_top",
        vectors_text=vector_text,
        build_dir=_derive_rtl_build_dir(build_dir, backend="verilator", mode=mode),
    )
    stdout = run_result.stdout
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"verilator simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return _parse_sv_output_with_unknowns(stdout), run_result


def _run_vcs_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    clock_period_ns: int,
    clock_domain: Optional[_DslClockDomainInfo],
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    vcs = _find_local_vcs()
    if vcs is None and _remote_vcs_host() is None:
        raise FileNotFoundError("vcs")
    vcs = vcs or "vcs"
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_sv_tb_runtime_vectors(
        module,
        module_name,
        mode,
        clock_period_ns,
        clock_domain=clock_domain,
    )
    vector_text = _encode_single_clock_vectors(
        module,
        vectors,
        mode=mode,
        clock_domain=clock_domain,
    )
    run_result = _compile_and_run_with_vcs(
        vcs,
        tb_sv=tb_sv,
        dut_src=dut_src,
        top_module="tb_top",
        vectors_text=vector_text,
        build_dir=_derive_rtl_build_dir(build_dir, backend="vcs", mode=mode),
    )
    stdout = run_result.stdout
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"vcs simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return _parse_sv_output_with_unknowns(stdout), run_result


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


def _generate_sv_tb_runtime_vectors(
    module,
    module_name: str,
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
    lines.append('    string vector_path;')
    lines.append("    integer fd;")
    lines.append("    integer rc;")
    lines.append("    integer cycle;")
    lines.append("    integer event_count;")
    lines.append("    integer active_mask;")
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
    lines.append('        if (!$value$plusargs("VECTOR_FILE=%s", vector_path)) begin')
    lines.append('            $display("VECTOR_FILE plusarg missing");')
    lines.append("            $finish;")
    lines.append("        end")
    lines.append("        fd = $fopen(vector_path, \"r\");")
    lines.append("        if (fd == 0) begin")
    lines.append('            $display("failed to open vector file: %0s", vector_path);')
    lines.append("            $finish;")
    lines.append("        end")
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
            lines.append(f"        @(negedge {clock_name});")
        elif "rst" in input_names:
            lines.append("        rst = 1;")
            lines.append(f"        @(posedge {clock_name});")
            lines.append(f"        @(posedge {clock_name});")
            lines.append("        rst = 0;")
            lines.append(f"        @(negedge {clock_name});")
        elif "rst_n" in input_names:
            lines.append("        rst_n = 0;")
            lines.append(f"        @(posedge {clock_name});")
            lines.append(f"        @(posedge {clock_name});")
            lines.append("        rst_n = 1;")
            lines.append(f"        @(negedge {clock_name});")
        scan_items = ["cycle"]
        for sig in inputs:
            if sig.name == clock_name and is_seq:
                continue
            scan_items.append(sig.name)
        scan_fmt = "%d " * len(scan_items)
        lines.append(f'        while ($fscanf(fd, "{scan_fmt.strip()}\\n", {", ".join(scan_items)}) == {len(scan_items)}) begin')
        lines.append(f"            @(posedge {clock_name});")
        lines.append("            #1;")
    else:
        scan_items = ["cycle"]
        for sig in inputs:
            scan_items.append(sig.name)
        scan_fmt = "%d " * len(scan_items)
        lines.append(f'        while ($fscanf(fd, "{scan_fmt.strip()}\\n", {", ".join(scan_items)}) == {len(scan_items)}) begin')
        lines.append(f"            #{clock_period_ns};")
    out_parts = [f"{sig.name}=%0d" for sig in outputs]
    out_vars = [sig.name for sig in outputs]
    lines.append(
        f"            $display(\"CYCLE %0d {' '.join(out_parts)}\", cycle, {', '.join(out_vars)});"
    )
    if is_seq and has_clk:
        lines.append(f"            @(negedge {clock_name});")
    lines.append("        end")
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
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
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
    return (
        _parse_sv_output_with_unknowns(stdout),
        _ExternalSimRunResult(
            stdout=stdout,
            cache_enabled=False,
            cache_hit=False,
            cache_key=None,
            cache_dir=None,
        ),
    )


def _run_multiclock_rtl_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    backend: str,
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    if backend == "verilator":
        return _run_multiclock_verilator_trace(module, vectors, build_dir=build_dir)
    if backend == "vcs":
        return _run_multiclock_vcs_trace(module, vectors, build_dir=build_dir)
    return _run_multiclock_iverilog_trace(module, vectors)


def _run_multiclock_verilator_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    verilator = _find_local_verilator()
    if verilator is None:
        raise FileNotFoundError("verilator")
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    clock_domains = _dsl_clock_domains(module)
    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_multiclock_sv_tb_runtime_vectors(
        module,
        module_name,
        clock_domains=clock_domains,
    )
    vector_text = _encode_multiclock_vectors(module, vectors, clock_domains=clock_domains)
    run_result = _compile_and_run_with_verilator(
        verilator,
        tb_sv=tb_sv,
        dut_src=dut_src,
        top_module="tb_top",
        vectors_text=vector_text,
        build_dir=_derive_rtl_build_dir(build_dir, backend="verilator", mode="multi_clock"),
    )
    stdout = run_result.stdout
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"verilator simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return _parse_sv_output_with_unknowns(stdout), run_result


def _run_multiclock_vcs_trace(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    build_dir: Optional[Path | str],
) -> tuple[Tuple[Mapping[str, int], ...], _ExternalSimRunResult]:
    vcs = _find_local_vcs()
    if vcs is None and _remote_vcs_host() is None:
        raise FileNotFoundError("vcs")
    vcs = vcs or "vcs"
    if _use_dsl_module(module):
        from rtlgen_x.dsl import VerilogEmitter
    else:
        from rtlgen import VerilogEmitter

    clock_domains = _dsl_clock_domains(module)
    emitter = VerilogEmitter()
    dut_src = emitter.emit_design(module)
    module_name = _infer_top_sv_module_name(dut_src, module)
    tb_sv = _generate_multiclock_sv_tb_runtime_vectors(
        module,
        module_name,
        clock_domains=clock_domains,
    )
    vector_text = _encode_multiclock_vectors(module, vectors, clock_domains=clock_domains)
    run_result = _compile_and_run_with_vcs(
        vcs,
        tb_sv=tb_sv,
        dut_src=dut_src,
        top_module="tb_top",
        vectors_text=vector_text,
        build_dir=_derive_rtl_build_dir(build_dir, backend="vcs", mode="multi_clock"),
    )
    stdout = run_result.stdout
    if "COSIM_DONE" not in stdout:
        raise rtl_cosim.CosimError(f"vcs simulation did not reach COSIM_DONE. stdout:\n{stdout}")
    return _parse_sv_output_with_unknowns(stdout), run_result


def _resolve_rtl_backend(requested: str) -> str:
    normalized = (requested or "auto").strip().lower()
    if normalized not in {"auto", "iverilog", "verilator", "vcs"}:
        raise ValueError(
            "rtl_backend must be one of 'auto', 'iverilog', 'verilator', or 'vcs'"
        )
    if normalized == "auto":
        if _find_local_verilator() is not None:
            return "verilator"
        if _find_local_vcs() is not None or _remote_vcs_host() is not None:
            return "vcs"
        return "iverilog"
    return normalized


def _remote_vcs_host() -> Optional[str]:
    host = os.environ.get("RTLGEN_X_REMOTE_VCS_HOST")
    return host.strip() if host and host.strip() else None


def _find_local_verilator() -> Optional[str]:
    env_override = os.environ.get("VERILATOR_BIN")
    if env_override:
        return env_override
    discovered = shutil.which("verilator")
    if discovered:
        return discovered
    workspace_candidates = (
        Path.cwd() / "build" / "verilator-local" / "src" / "verilator_bin",
        Path.cwd() / "verilator-master" / "bin" / "verilator",
    )
    for candidate in workspace_candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _find_local_vcs() -> Optional[str]:
    env_override = os.environ.get("VCS_BIN")
    if env_override:
        return env_override
    return shutil.which("vcs")


def _compile_and_run_with_verilator(
    verilator: str,
    *,
    tb_sv: str,
    dut_src: str,
    top_module: str,
    vectors_text: str,
    build_dir: Optional[Path | str] = None,
) -> _ExternalSimRunResult:
    wrapper_path = Path(verilator)
    env = dict(os.environ)
    root = _resolve_verilator_root(wrapper_path)
    wrapper_cmd = str(wrapper_path)
    if root is not None:
        env["VERILATOR_ROOT"] = str(root)
        include_dir = root / "include"
        build_include_dir = Path.cwd() / "build" / "verilator-local" / "include"
        _link_verilator_runtime_files(include_dir, build_include_dir)
        bin_dir = root / "bin"
        if wrapper_path.name == "verilator_bin":
            wrapper_candidate = bin_dir / "verilator"
            if wrapper_candidate.exists():
                wrapper_cmd = str(wrapper_candidate)
                env["VERILATOR_BIN"] = str(wrapper_path)

    sysroot = _macos_sdk_path()
    cxxflags = _verilator_cxxflags(sysroot)
    ldflags = _verilator_ldflags(sysroot)
    material = "\n".join((wrapper_cmd, top_module, cxxflags, ldflags, tb_sv, dut_src))
    return _compile_and_run_cached_external_sim(
        backend="verilator",
        compile_key=_hash_text(material),
        build_dir=build_dir,
        source_files={"dut.sv": dut_src, "tb_top.sv": tb_sv},
        vector_filename="vectors.txt",
        vectors_text=vectors_text,
        compile_runner=lambda root_path: _run_verilator_compile(
            root_path,
            wrapper_cmd=wrapper_cmd,
            top_module=top_module,
            cxxflags=cxxflags,
            ldflags=ldflags,
            env=env,
        ),
        executable_locator=lambda root_path: root_path / "obj_dir" / f"V{top_module}",
        run_plusargs=("+VECTOR_FILE=vectors.txt",),
        env=env,
    )


def _compile_and_run_with_vcs(
    vcs: str,
    *,
    tb_sv: str,
    dut_src: str,
    top_module: str,
    vectors_text: str,
    build_dir: Optional[Path | str] = None,
) -> _ExternalSimRunResult:
    remote_host = _remote_vcs_host()
    if remote_host:
        return _compile_and_run_with_remote_vcs(
            host=remote_host,
            source_script=os.environ.get("RTLGEN_X_REMOTE_VCS_SOURCE_SCRIPT", "/apps/EDAs/syn.bash"),
            remote_root=os.environ.get("RTLGEN_X_REMOTE_VCS_ROOT"),
            tb_sv=tb_sv,
            dut_src=dut_src,
            top_module=top_module,
            vectors_text=vectors_text,
            build_dir=build_dir,
        )
    env = dict(os.environ)
    material = "\n".join((vcs, top_module, tb_sv, dut_src))
    return _compile_and_run_cached_external_sim(
        backend="vcs",
        compile_key=_hash_text(material),
        build_dir=build_dir,
        source_files={"dut.sv": dut_src, "tb_top.sv": tb_sv},
        vector_filename="vectors.txt",
        vectors_text=vectors_text,
        compile_runner=lambda root_path: _run_vcs_compile(
            root_path,
            vcs=vcs,
            top_module=top_module,
            env=env,
        ),
        executable_locator=lambda root_path: root_path / "simv",
        run_plusargs=("+VECTOR_FILE=vectors.txt",),
        env=env,
    )


def _compile_and_run_with_remote_vcs(
    *,
    host: str,
    source_script: str,
    remote_root: Optional[str],
    tb_sv: str,
    dut_src: str,
    top_module: str,
    vectors_text: str,
    build_dir: Optional[Path | str] = None,
) -> _ExternalSimRunResult:
    material = "\n".join((host, source_script, remote_root or "", top_module, tb_sv, dut_src))
    compile_key = _hash_text(material)
    root_path, tempdir = _prepare_external_sim_root("vcs", compile_key, build_dir)
    remote_base = remote_root or "$HOME/rtlgen_x/cosim_vcs"
    remote_dir = f"{remote_base.rstrip('/')}/{compile_key}"
    try:
        source_files = {"dut.sv": dut_src, "tb_top.sv": tb_sv, "vectors.txt": vectors_text}
        for filename, contents in source_files.items():
            (root_path / filename).write_text(contents, encoding="utf-8")
        stamp_path = root_path / ".compile_stamp"
        cache_hit = stamp_path.exists()
        if not cache_hit:
            archive = _tar_paths(
                (
                    (root_path / "dut.sv", "dut.sv"),
                    (root_path / "tb_top.sv", "tb_top.sv"),
                    (root_path / "vectors.txt", "vectors.txt"),
                )
            )
            _run_remote_ssh(
                host,
                f"mkdir -p {remote_dir} && tar xzf - -C {remote_dir}",
                step="prepare remote VCS work directory and upload sources",
                input_data=archive,
                text=False,
            )
            compile_cmd = (
                f"source {source_script} >/dev/null 2>&1 && "
                f"cd {remote_dir} && "
                "vcs -full64 -sverilog -timescale=1ns/1ps -q "
                f"-top {top_module} tb_top.sv dut.sv -o simv"
            )
            compile_result = _run_remote_ssh(
                host,
                f"bash -lc '{compile_cmd}'",
                step="compile remote VCS simulation",
                text=True,
                check=False,
            )
            if compile_result.returncode != 0:
                raise rtl_cosim.CosimError(
                    "remote vcs compilation failed:\n"
                    f"stdout={_decode_subprocess_stream(compile_result.stdout)}\n"
                    f"stderr={_decode_subprocess_stream(compile_result.stderr)}"
                )
            stamp_path.write_text(compile_key, encoding="utf-8")
        else:
            vector_archive = _tar_paths(((root_path / "vectors.txt", "vectors.txt"),))
            _run_remote_ssh(
                host,
                f"tar xzf - -C {remote_dir}",
                step="upload remote VCS vectors",
                input_data=vector_archive,
                text=False,
            )
        run_cmd = (
            f"source {source_script} >/dev/null 2>&1 && "
            f"cd {remote_dir} && "
            "./simv +VECTOR_FILE=vectors.txt"
        )
        run_result = _run_remote_ssh(
            host,
            f"bash -lc '{run_cmd}'",
            step="run remote VCS simulation",
            text=True,
            check=False,
        )
        stdout = _decode_subprocess_stream(run_result.stdout)
        stderr = _decode_subprocess_stream(run_result.stderr)
        if run_result.returncode != 0:
            raise rtl_cosim.CosimError(
                f"remote vcs execution failed:\nstdout={stdout}\nstderr={stderr}"
            )
        return _ExternalSimRunResult(
            stdout=stdout,
            cache_enabled=build_dir is not None,
            cache_hit=cache_hit,
            cache_key=compile_key if build_dir is not None else None,
            cache_dir=str(root_path) if build_dir is not None else None,
        )
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def _derive_rtl_build_dir(
    build_dir: Optional[Path | str],
    *,
    backend: str,
    mode: str,
) -> Optional[Path]:
    if build_dir is None:
        return None
    return Path(build_dir) / "rtl_cosim" / backend / mode


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _prepare_external_sim_root(
    backend: str,
    compile_key: str,
    build_dir: Optional[Path | str],
) -> tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    if build_dir is not None:
        root_path = Path(build_dir).resolve() / compile_key
        root_path.mkdir(parents=True, exist_ok=True)
        return root_path, None
    tempdir = tempfile.TemporaryDirectory(prefix=f"rtlgen_x_{backend}_cosim_")
    return Path(tempdir.name), tempdir


def _compile_and_run_cached_external_sim(
    *,
    backend: str,
    compile_key: str,
    build_dir: Optional[Path | str],
    source_files: Mapping[str, str],
    vector_filename: str,
    vectors_text: str,
    compile_runner,
    executable_locator,
    run_plusargs: Sequence[str],
    env: Mapping[str, str],
) -> _ExternalSimRunResult:
    root_path, tempdir = _prepare_external_sim_root(backend, compile_key, build_dir)
    try:
        for filename, contents in source_files.items():
            (root_path / filename).write_text(contents, encoding="utf-8")
        vector_path = root_path / vector_filename
        vector_path.write_text(vectors_text, encoding="utf-8")
        stamp_path = root_path / ".compile_stamp"
        cache_hit = stamp_path.exists()
        if not cache_hit:
            compile_runner(root_path)
            stamp_path.write_text(compile_key, encoding="utf-8")
        exe = executable_locator(root_path)
        run_result = subprocess.run(
            [str(exe), *run_plusargs],
            cwd=root_path,
            capture_output=True,
            text=True,
            env=dict(env),
        )
        if run_result.returncode != 0:
            raise rtl_cosim.CosimError(
                f"{backend} execution failed:\n"
                f"stdout={run_result.stdout}\n"
                f"stderr={run_result.stderr}"
            )
        return _ExternalSimRunResult(
            stdout=run_result.stdout,
            cache_enabled=build_dir is not None,
            cache_hit=cache_hit,
            cache_key=compile_key if build_dir is not None else None,
            cache_dir=str(root_path) if build_dir is not None else None,
        )
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def _run_verilator_compile(
    root_path: Path,
    *,
    wrapper_cmd: str,
    top_module: str,
    cxxflags: str,
    ldflags: str,
    env: Mapping[str, str],
) -> None:
    cmd = [
        wrapper_cmd,
        "--binary",
        "--timing",
        "-Wno-fatal",
        "--top-module",
        top_module,
        "-CFLAGS",
        cxxflags,
        "-LDFLAGS",
        ldflags,
        str(root_path / "tb_top.sv"),
        str(root_path / "dut.sv"),
    ]
    compile_result = subprocess.run(
        cmd,
        cwd=root_path,
        capture_output=True,
        text=True,
        env=dict(env),
    )
    if compile_result.returncode != 0:
        raise rtl_cosim.CosimError(
            "verilator compilation failed:\n"
            f"stdout={compile_result.stdout}\n"
            f"stderr={compile_result.stderr}"
        )


def _run_vcs_compile(
    root_path: Path,
    *,
    vcs: str,
    top_module: str,
    env: Mapping[str, str],
) -> None:
    cmd = [
        vcs,
        "-full64",
        "-sverilog",
        "-timescale=1ns/1ps",
        "-q",
        "-top",
        top_module,
        str(root_path / "tb_top.sv"),
        str(root_path / "dut.sv"),
        "-o",
        str(root_path / "simv"),
    ]
    compile_result = subprocess.run(
        cmd,
        cwd=root_path,
        capture_output=True,
        text=True,
        env=dict(env),
    )
    if compile_result.returncode != 0:
        raise rtl_cosim.CosimError(
            "vcs compilation failed:\n"
            f"stdout={compile_result.stdout}\n"
            f"stderr={compile_result.stderr}"
        )


def _tar_paths(paths: Sequence[tuple[Path, str]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for src_path, arcname in paths:
            archive.add(src_path, arcname=arcname)
    return buffer.getvalue()


def _run_remote_ssh(
    host: str,
    command: str,
    *,
    step: str,
    input_data: bytes | None = None,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["ssh", host, command],
        input=input_data,
        capture_output=True,
        text=text,
    )
    if check and completed.returncode != 0:
        raise rtl_cosim.CosimError(
            f"remote vcs ssh step failed: {step}\n"
            f"host={host}\n"
            f"command={command}\n"
            f"returncode={completed.returncode}\n"
            f"stdout={_decode_subprocess_stream(completed.stdout)}\n"
            f"stderr={_decode_subprocess_stream(completed.stderr)}"
        )
    return completed


def _decode_subprocess_stream(stream: object) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return str(stream)


def _resolve_verilator_root(verilator_path: Path) -> Optional[Path]:
    env_root = os.environ.get("VERILATOR_ROOT")
    if env_root:
        root = Path(env_root)
        if root.exists():
            return root
    if verilator_path.name == "verilator_bin":
        candidate = Path.cwd() / "verilator-master"
        if candidate.exists():
            return candidate
    parent = verilator_path.parent
    if parent.name == "bin" and parent.parent.exists():
        return parent.parent
    return None


def _link_verilator_runtime_files(include_dir: Path, build_include_dir: Path) -> None:
    include_dir.mkdir(parents=True, exist_ok=True)
    for name in ("verilated.mk", "verilated_config.h"):
        dst = include_dir / name
        src = build_include_dir / name
        if not src.exists():
            continue
        if dst.exists() or dst.is_symlink():
            continue
        dst.symlink_to(src)


def _macos_sdk_path() -> Optional[str]:
    if os.name != "posix":
        return None
    try:
        result = subprocess.run(
            ["xcrun", "--show-sdk-path"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    path = result.stdout.strip()
    return path or None


def _verilator_cxxflags(sysroot: Optional[str]) -> str:
    flags = ["-std=c++20"]
    if sysroot:
        flags.extend(["-isysroot", sysroot])
    llvm_include = Path("/opt/homebrew/opt/llvm/include/c++/v1")
    if llvm_include.exists():
        flags.extend(["-stdlib=libc++", f"-I{llvm_include}"])
    return " ".join(flags)


def _verilator_ldflags(sysroot: Optional[str]) -> str:
    flags: List[str] = []
    if sysroot:
        flags.extend(["-isysroot", sysroot])
    llvm_include = Path("/opt/homebrew/opt/llvm/include/c++/v1")
    if llvm_include.exists():
        flags.append("-stdlib=libc++")
    return " ".join(flags)


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


def _generate_multiclock_sv_tb_runtime_vectors(
    module,
    module_name: str,
    *,
    clock_domains: Sequence[_DslClockDomainInfo],
) -> str:
    inputs = list(module._inputs.values())
    outputs = list(module._outputs.values())
    managed_clocks = {domain.name for domain in clock_domains}

    lines: List[str] = ["`timescale 1ns/1ps", "module tb_top;"]
    lines.append('    string vector_path;')
    lines.append("    integer fd;")
    lines.append("    integer cycle;")
    lines.append("    integer active_mask;")
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
    lines.append('        if (!$value$plusargs("VECTOR_FILE=%s", vector_path)) begin')
    lines.append('            $display("VECTOR_FILE plusarg missing");')
    lines.append("            $finish;")
    lines.append("        end")
    lines.append("        fd = $fopen(vector_path, \"r\");")
    lines.append("        if (fd == 0) begin")
    lines.append('            $display("failed to open vector file: %0s", vector_path);')
    lines.append("            $finish;")
    lines.append("        end")
    for sig in inputs:
        if sig.name in managed_clocks:
            continue
        lines.append(f"        {sig.name} = 0;")
    scan_items = ["cycle", "active_mask"]
    for sig in inputs:
        if sig.name in managed_clocks:
            continue
        scan_items.append(sig.name)
    scan_fmt = "%d " * len(scan_items)
    lines.append(f'        while ($fscanf(fd, "{scan_fmt.strip()}\\n", {", ".join(scan_items)}) == {len(scan_items)}) begin')
    for index, domain in enumerate(clock_domains):
        lines.append(f"            if (active_mask & {1 << index}) {domain.name} = 1'b1;")
    lines.append("            #1;")
    out_parts = [f"{sig.name}=%0d" for sig in outputs]
    out_vars = [sig.name for sig in outputs]
    lines.append(
        f"            $display(\"CYCLE %0d {' '.join(out_parts)}\", cycle, {', '.join(out_vars)});"
    )
    for domain in clock_domains:
        lines.append(f"            {domain.name} = 1'b0;")
    lines.append("            #1;")
    lines.append("        end")
    lines.append('        $display("COSIM_DONE");')
    lines.append("        $finish;")
    lines.append("    end")
    lines.append("endmodule")
    return "\n".join(lines)


def _encode_single_clock_vectors(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    clock_domain: Optional[_DslClockDomainInfo],
) -> str:
    inputs = list(module._inputs.values())
    clock_name = clock_domain.name if clock_domain is not None else None
    include_inputs = [sig.name for sig in inputs if not (mode == "seq" and sig.name == clock_name)]
    last_vals: Dict[str, int] = {name: 0 for name in include_inputs}
    rows: List[str] = []
    for cycle, vector in enumerate(vectors):
        values = []
        for name in include_inputs:
            value = int(vector.get(name, last_vals.get(name, 0)))
            values.append(str(value))
            last_vals[name] = value
        rows.append(f"{cycle} {' '.join(values)}")
    return "\n".join(rows) + ("\n" if rows else "")


def _encode_multiclock_vectors(
    module,
    vectors: Sequence[tuple[Mapping[str, int], tuple[str, ...]]],
    *,
    clock_domains: Sequence[_DslClockDomainInfo],
) -> str:
    managed_clocks = {domain.name for domain in clock_domains}
    domain_index = {domain.name: idx for idx, domain in enumerate(clock_domains)}
    inputs = [sig.name for sig in module._inputs.values() if sig.name not in managed_clocks]
    last_vals: Dict[str, int] = {name: 0 for name in inputs}
    rows: List[str] = []
    for cycle, (vector, active_domains) in enumerate(vectors):
        active_mask = 0
        for domain in active_domains:
            active_mask |= 1 << domain_index[domain]
        values = []
        for name in inputs:
            value = int(vector.get(name, last_vals.get(name, 0)))
            values.append(str(value))
            last_vals[name] = value
        rows.append(f"{cycle} {active_mask} {' '.join(values)}")
    return "\n".join(rows) + ("\n" if rows else "")


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
