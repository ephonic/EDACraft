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
class LegacyRtlCosimReport:
    module_name: str
    mode: str
    vector_count: int
    legacy_matches_rtl: bool
    compiled_matches_rtl: bool
    mismatches: Tuple[CosimMismatch, ...]
    rtl_trace: Tuple[Mapping[str, int], ...]
    compiled_trace: Tuple[Mapping[str, int], ...]
    skipped_reason: Optional[str] = None


def run_legacy_rtl_cosim(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str = "auto",
    clock_period_ns: int = 10,
    build_dir: Optional[Path | str] = None,
) -> LegacyRtlCosimReport:
    """Compare a compiled simulator built from a legacy DSL module against emitted RTL."""

    resolved_mode = _resolve_mode(module, mode)
    try:
        legacy_trace = _run_reference_trace(
            module,
            vectors,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
        )
        rtl_trace = _run_iverilog_trace(
            module,
            vectors,
            mode=resolved_mode,
            clock_period_ns=clock_period_ns,
        )
    except FileNotFoundError as exc:
        return LegacyRtlCosimReport(
            module_name=module.name,
            mode=resolved_mode,
            vector_count=len(vectors),
            legacy_matches_rtl=False,
            compiled_matches_rtl=False,
            mismatches=(),
            rtl_trace=(),
            compiled_trace=(),
            skipped_reason=str(exc),
        )

    compiled_trace = _run_compiled_trace(
        module,
        vectors,
        mode=resolved_mode,
        build_dir=build_dir,
    )
    outputs = [sig.name for sig in module._outputs.values()]
    legacy_matches_rtl = not _collect_mismatches(outputs, legacy_trace, rtl_trace)
    mismatches = _collect_mismatches(outputs, compiled_trace, rtl_trace)

    return LegacyRtlCosimReport(
        module_name=module.name,
        mode=resolved_mode,
        vector_count=len(vectors),
        legacy_matches_rtl=legacy_matches_rtl,
        compiled_matches_rtl=not mismatches,
        mismatches=tuple(mismatches),
        rtl_trace=tuple(dict(step) for step in rtl_trace),
        compiled_trace=tuple(dict(step) for step in compiled_trace),
        skipped_reason=None,
    )


def _run_compiled_trace(
    module,
    vectors: Sequence[Mapping[str, int]],
    *,
    mode: str,
    build_dir: Optional[Path | str],
) -> Tuple[Mapping[str, int], ...]:
    from rtlgen_x.dsl import build_compiled_simulator_from_legacy

    compiled = build_compiled_simulator_from_legacy(module, build_dir=build_dir)
    try:
        current_inputs: Dict[str, int] = {name: 0 for name in compiled.input_names}
        if mode == "seq":
            _apply_reset_preamble(compiled, current_inputs)
        trace: List[Mapping[str, int]] = []
        for vector in vectors:
            for name, value in vector.items():
                if name in current_inputs:
                    current_inputs[name] = int(value)
            trace.append(dict(compiled.step(current_inputs)))
        return tuple(trace)
    finally:
        compiled.close()


def _apply_reset_preamble(compiled, current_inputs: Dict[str, int]) -> None:
    if "rst" in current_inputs:
        current_inputs["rst"] = 1
        compiled.step(current_inputs)
        compiled.step(current_inputs)
        current_inputs["rst"] = 0
        compiled.step(current_inputs)
        return
    if "rst_n" in current_inputs:
        current_inputs["rst_n"] = 0
        compiled.step(current_inputs)
        compiled.step(current_inputs)
        current_inputs["rst_n"] = 1
        compiled.step(current_inputs)


def _resolve_mode(module, mode: str) -> str:
    input_names = {sig.name for sig in module._inputs.values()}
    if mode == "auto":
        return "seq" if "clk" in input_names else "comb"
    return mode


def _use_rtlgen_x_legacy(module) -> bool:
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
) -> Tuple[Mapping[str, int], ...]:
    if _use_rtlgen_x_legacy(module):
        from rtlgen_x.dsl import Simulator
    else:
        from rtlgen import Simulator

    sim = Simulator(module, clock_period_ns=clock_period_ns)
    outputs = [sig.name for sig in module._outputs.values()]
    input_names = {sig.name for sig in module._inputs.values()}
    if mode == "seq":
        if "rst" in input_names:
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
) -> Tuple[Mapping[str, int], ...]:
    if _use_rtlgen_x_legacy(module):
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


def _generate_sv_tb(
    module,
    module_name: str,
    vectors: Sequence[Mapping[str, int]],
    mode: str,
    clock_period_ns: int,
) -> str:
    inputs = list(module._inputs.values())
    outputs = list(module._outputs.values())
    has_clk = any(sig.name == "clk" for sig in inputs)
    is_seq = mode == "seq"

    lines: List[str] = ["`timescale 1ns/1ps", "module tb_top;"]
    if is_seq and has_clk:
        lines.append("    reg clk = 0;")
    for sig in inputs:
        if sig.name == "clk" and is_seq:
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
        lines.append(f"    always #{clock_period_ns // 2} clk = ~clk;")
        lines.append("")
    lines.append("    initial begin")
    for sig in inputs:
        if sig.name == "clk" and is_seq:
            continue
        lines.append(f"        {sig.name} = 0;")
    lines.append("        #0;")
    input_names = {sig.name for sig in inputs}
    if is_seq and has_clk:
        if "rst" in input_names:
            lines.append("        rst = 1;")
            lines.append("        @(posedge clk);")
            lines.append("        @(posedge clk);")
            lines.append("        rst = 0;")
        elif "rst_n" in input_names:
            lines.append("        rst_n = 0;")
            lines.append("        @(posedge clk);")
            lines.append("        @(posedge clk);")
            lines.append("        rst_n = 1;")
        lines.append("        @(negedge clk);")
    last_vals: Dict[str, int] = {name: 0 for name in input_names if name != "clk"}
    for cycle, vector in enumerate(vectors):
        for sig in inputs:
            if sig.name == "clk" and is_seq:
                continue
            value = int(vector.get(sig.name, last_vals.get(sig.name, 0)))
            if last_vals.get(sig.name) != value:
                lines.append(f"        {sig.name} = {rtl_cosim._to_sv_literal(value)};")
            last_vals[sig.name] = value
        if is_seq and has_clk:
            lines.append("        @(posedge clk);")
            lines.append("        #1;")
        else:
            lines.append(f"        #{clock_period_ns};")
        out_parts = [f"{sig.name}=%0d" for sig in outputs]
        out_vars = [sig.name for sig in outputs]
        lines.append(
            f"        $display(\"CYCLE %0d {' '.join(out_parts)}\", {cycle}, {', '.join(out_vars)});"
        )
        if is_seq and has_clk and cycle != len(vectors) - 1:
            lines.append("        @(negedge clk);")
    lines.append('        $display("COSIM_DONE");')
    lines.append("        $finish;")
    lines.append("    end")
    lines.append("endmodule")
    return "\n".join(lines)


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
