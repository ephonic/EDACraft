"""Static CDC analysis helpers for DSL and executable modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from rtlgen_x.dsl import LoweredDslModule, lower_dsl_module_to_sim
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    SignalRef,
    SimModule,
    UnaryExpr,
)


@dataclass(frozen=True)
class CdcEndpoint:
    signal_name: str
    clock_domain: Optional[str]
    width: int
    kind: str
    source_file: Optional[str] = None
    source_line: Optional[int] = None


@dataclass(frozen=True)
class CdcFinding:
    category: str
    severity: str
    message: str
    src: Optional[CdcEndpoint] = None
    dst: Optional[CdcEndpoint] = None
    suggestions: Tuple[str, ...] = ()
    evidence: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CdcReport:
    module_name: str
    clock_domains: Tuple[str, ...]
    findings: Tuple[CdcFinding, ...]

    @property
    def has_issues(self) -> bool:
        return bool(self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "warning")


_SAFE_CDC_TYPES = frozenset({"SyncCell", "PulseSynchronizer", "AsyncFIFO", "AsyncResetRel", "ReadyValidAsyncBridge"})
_SAFE_RESET_TYPES = frozenset({"AsyncResetRel"})


@dataclass(frozen=True)
class _RecognizedCdcStructures:
    safe_first_stage_targets: Tuple[str, ...] = ()
    safe_reset_signals_by_domain: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    reset_builder_block_indices: Tuple[int, ...] = ()


def analyze_cdc(module: Any) -> CdcReport:
    """Analyze one DSL or executable module for common CDC hazards."""

    original_dsl_module = module if hasattr(module, "_seq_blocks") and hasattr(module, "_top_level") else None
    if original_dsl_module is not None:
        dsl_module = _flatten_dsl_if_available(module) or original_dsl_module
        if _is_builtin_safe_cdc_primitive(original_dsl_module):
            return CdcReport(
                module_name=getattr(dsl_module, "name", getattr(original_dsl_module, "name", "dsl_module")),
                clock_domains=_dsl_clock_domains(dsl_module),
                findings=(),
            )
        return _analyze_dsl_cdc(dsl_module, original_dsl_module)

    executable = _normalize_executable_module(module, context="analyze_cdc(...)")
    if _is_builtin_safe_cdc_primitive(executable):
        return CdcReport(
            module_name=executable.name,
            clock_domains=tuple(domain.name for domain in executable.clock_domains),
            findings=(),
        )
    return _analyze_executable_cdc(executable)


def _analyze_dsl_cdc(flat_module: Any, original_module: Any) -> CdcReport:
    clock_domains = _dsl_clock_domains(flat_module)
    primitive_hints = _collect_primitive_hints(original_module)
    safe_cdc_prefixes = _collect_safe_cdc_prefixes(original_module)
    safe_reset_prefixes = _collect_safe_reset_prefixes(original_module)
    source_locs = _collect_source_locations(original_module)
    signal_widths = _dsl_signal_widths(flat_module)
    memory_widths = _dsl_memory_widths(flat_module)
    recognized = _recognize_dsl_cdc_structures(
        flat_module,
        signal_widths=signal_widths,
        safe_reset_prefixes=safe_reset_prefixes,
        primitive_safe_reset_outputs_by_domain=_collect_safe_reset_outputs_by_domain(original_module),
    )
    state_writers = _dsl_state_writers(flat_module)
    memory_writers = _dsl_memory_writers(flat_module)
    comb_domain_map = _dsl_comb_source_domains(
        flat_module,
        state_writers=state_writers,
        memory_writers=memory_writers,
        safe_cdc_prefixes=safe_cdc_prefixes,
    )

    findings: List[CdcFinding] = []
    findings.extend(
        _analyze_dsl_reset_release(
            flat_module,
            safe_reset_prefixes=safe_reset_prefixes,
            safe_reset_signals_by_domain={
                domain_name: set(signal_names)
                for domain_name, signal_names in recognized.safe_reset_signals_by_domain.items()
            },
            reset_builder_block_indices=set(recognized.reset_builder_block_indices),
            source_locs=source_locs,
        )
    )
    if len(clock_domains) <= 1:
        return CdcReport(
            module_name=getattr(flat_module, "name", getattr(original_module, "name", "dsl_module")),
            clock_domains=clock_domains,
            findings=tuple(_dedupe_findings(findings)),
        )

    for clk, _rst, _async, _active_low, body in getattr(flat_module, "_seq_blocks", ()):
        dst_domain = getattr(clk, "name", str(clk))
        findings.extend(
            _dsl_findings_in_stmt_list(
                body,
                dst_domain=dst_domain,
                state_writers=state_writers,
                memory_writers=memory_writers,
                comb_domain_map=comb_domain_map,
                signal_widths=signal_widths,
                memory_widths=memory_widths,
                primitive_hints=primitive_hints,
                safe_cdc_prefixes=safe_cdc_prefixes,
                safe_first_stage_targets=set(recognized.safe_first_stage_targets),
                source_locs=source_locs,
            )
        )

    for body in getattr(flat_module, "_comb_blocks", ()):
        findings.extend(
            _dsl_comb_memory_findings(
                body,
                state_writers=state_writers,
                memory_writers=memory_writers,
                comb_domain_map=comb_domain_map,
                memory_widths=memory_widths,
                primitive_hints=primitive_hints,
                safe_cdc_prefixes=safe_cdc_prefixes,
                source_locs=source_locs,
            )
        )

    findings.extend(
        _analyze_multiwriter_conflicts(
            state_writers=state_writers,
            memory_writers=memory_writers,
            state_widths=signal_widths,
            memory_widths=memory_widths,
            safe_cdc_prefixes=safe_cdc_prefixes,
            source_locs=source_locs,
        )
    )
    return CdcReport(
        module_name=getattr(flat_module, "name", getattr(original_module, "name", "dsl_module")),
        clock_domains=clock_domains,
        findings=tuple(_dedupe_findings(findings)),
    )


def _analyze_executable_cdc(module: SimModule) -> CdcReport:
    clock_domains = tuple(domain.name for domain in module.clock_domains)
    signal_map = module.signal_map()
    memory_map = module.memory_map()
    source_locs = _collect_executable_source_locations(module)
    recognized = _recognize_executable_cdc_structures(module)
    state_writers = _collect_state_writers(module, signal_map)
    memory_writers = _collect_memory_writers(module, memory_map)
    comb_domain_map = _collect_comb_source_domains(
        module,
        state_writers=state_writers,
        memory_writers=memory_writers,
    )
    findings = _analyze_executable_reset_release(
        module,
        safe_reset_signals_by_domain={
            domain_name: set(signal_names)
            for domain_name, signal_names in recognized.safe_reset_signals_by_domain.items()
        },
        source_locs=source_locs,
    )
    if len(clock_domains) <= 1:
        return CdcReport(
            module_name=module.name,
            clock_domains=clock_domains,
            findings=tuple(_dedupe_findings(findings)),
        )

    findings.extend(
        _analyze_assignments(
        module,
        signal_map=signal_map,
        memory_map=memory_map,
        state_writers=state_writers,
        memory_writers=memory_writers,
        comb_domain_map=comb_domain_map,
        primitive_hints={},
        safe_cdc_prefixes=set(),
        safe_first_stage_targets=set(recognized.safe_first_stage_targets),
        source_locs=source_locs,
        )
    )
    findings.extend(
        _analyze_multiwriter_conflicts(
            state_writers=state_writers,
            memory_writers=memory_writers,
            state_widths={name: signal.width for name, signal in signal_map.items()},
            memory_widths={name: memory.width for name, memory in memory_map.items()},
            safe_cdc_prefixes=set(),
            source_locs=source_locs,
        )
    )
    return CdcReport(
        module_name=module.name,
        clock_domains=clock_domains,
        findings=tuple(_dedupe_findings(findings)),
    )


def emit_cdc_report_markdown(report: CdcReport, *, title: Optional[str] = None) -> str:
    """Render a compact markdown CDC report."""

    heading = title or f"{report.module_name} CDC Report"
    lines = [f"# {heading}", ""]
    lines.append(f"- module: `{report.module_name}`")
    lines.append(f"- clock domains: {', '.join(report.clock_domains) or 'none'}")
    lines.append(
        f"- findings: {len(report.findings)} "
        f"({report.error_count} errors, {report.warning_count} warnings)"
    )
    lines.append("")
    if not report.findings:
        lines.append("No CDC issues detected by the current static checks.")
        return "\n".join(lines) + "\n"

    for index, finding in enumerate(report.findings, start=1):
        lines.append(f"## {index}. [{finding.severity}] {finding.category}")
        lines.append("")
        lines.append(finding.message)
        lines.append("")
        if finding.src is not None:
            lines.append(f"- source: {_format_endpoint(finding.src)}")
        if finding.dst is not None:
            lines.append(f"- destination: {_format_endpoint(finding.dst)}")
        signal_sites = _finding_signal_sites(finding)
        if signal_sites:
            lines.append("- source sites:")
            for site in signal_sites:
                lines.append(f"  - {site}")
        affected_sites = _finding_affected_target_sites(finding)
        if affected_sites:
            lines.append("- affected target sites:")
            for site in affected_sites:
                lines.append(f"  - {site}")
        if finding.suggestions:
            lines.append("- suggestions:")
            for suggestion in finding.suggestions:
                lines.append(f"  - {suggestion}")
        if finding.evidence:
            lines.append("- evidence:")
            for key, value in finding.evidence.items():
                if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
                    lines.append(f"  - {key}:")
                    for item in value:
                        lines.append(f"    - {item}")
                else:
                    lines.append(f"  - {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def _normalize_executable_module(module: Any, *, context: str) -> SimModule:
    if isinstance(module, SimModule):
        raise TypeError(
            f"{context} is a DSL-facing API and does not accept raw SimModule. "
            "Pass a rtlgen_x.dsl.Module instance, or pass the LoweredDslModule returned by "
            "lower_dsl_module_to_sim(...), not lowered.module."
        )
    if isinstance(module, LoweredDslModule):
        return module.module
    if hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks"):
        lowered = lower_dsl_module_to_sim(module)
        return lowered.module
    raise TypeError(
        f"{context} expects a rtlgen_x.dsl.Module or LoweredDslModule; "
        f"got {type(module)!r}"
    )


def _flatten_dsl_if_available(module: Any) -> Any:
    if not (hasattr(module, "_seq_blocks") and hasattr(module, "_top_level")):
        return None
    try:
        from rtlgen_x.dsl.core import flatten_module

        return flatten_module(module)
    except Exception:
        return module


def _collect_executable_source_locations(module: SimModule) -> Dict[str, Tuple[Optional[str], Optional[int]]]:
    source_locs: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
    for assignment in module.assignments:
        if assignment.target not in source_locs:
            source_locs[assignment.target] = (assignment.source_file, assignment.source_line)
    for write in module.memory_writes:
        memory_name = getattr(write, "memory", None)
        source_file = getattr(write, "source_file", None)
        source_line = getattr(write, "source_line", None)
        if memory_name and memory_name not in source_locs:
            source_locs[memory_name] = (source_file, source_line)
    return source_locs


def _collect_state_writers(
    module: SimModule,
    signal_map: Mapping[str, object],
) -> Dict[str, Set[Optional[str]]]:
    writers: Dict[str, Set[Optional[str]]] = {}
    for assignment in module.assignments:
        if assignment.phase != "seq":
            continue
        domain = assignment.clock_domain
        writers.setdefault(assignment.target, set()).add(domain)
    return writers


def _collect_memory_writers(
    module: SimModule,
    memory_widths: Mapping[str, int],
) -> Dict[str, Set[Optional[str]]]:
    writers: Dict[str, Set[Optional[str]]] = {}
    for write in module.memory_writes:
        writers.setdefault(write.memory, set()).add(write.clock_domain)
    return writers


def _collect_comb_source_domains(
    module: SimModule,
    *,
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
) -> Dict[str, Set[Optional[str]]]:
    source_domains: Dict[str, Set[Optional[str]]] = {}
    changed = True
    while changed:
        changed = False
        for assignment in module.assignments:
            if assignment.phase != "comb":
                continue
            domains: Set[Optional[str]] = set()
            for signal_name in _expr_signal_refs(assignment.expr):
                domains.update(state_writers.get(signal_name, ()))
                domains.update(source_domains.get(signal_name, ()))
            for memory_name in _expr_memory_reads(assignment.expr):
                domains.update(memory_writers.get(memory_name, ()))
            if not domains:
                continue
            current = source_domains.setdefault(assignment.target, set())
            new_domains = domains - current
            if new_domains:
                current.update(new_domains)
                changed = True
    return source_domains


def _collect_primitive_hints(module: Any) -> Dict[str, Set[str]]:
    hints: Dict[str, Set[str]] = {}
    if module is None:
        return hints
    for _inst_name, submodule in getattr(module, "_submodules", ()):
        type_name = getattr(submodule, "_type_name", getattr(submodule, "name", submodule.__class__.__name__))
        key = str(type_name)
        hints.setdefault(key, set()).add(key)
    return hints


def _module_type_candidates(module: Any) -> Tuple[str, ...]:
    candidates = (
        getattr(module, "_type_name", None),
        getattr(module, "name", None),
        module.__class__.__name__ if module is not None else None,
    )
    return tuple(str(candidate) for candidate in candidates if candidate)


def _is_builtin_safe_cdc_primitive(module: Any) -> bool:
    return any(candidate in _SAFE_CDC_TYPES for candidate in _module_type_candidates(module))


def _collect_safe_primitive_prefixes(
    module: Any,
    *,
    safe_types: Set[str],
    _parent_prefix: str = "",
) -> Set[str]:
    prefixes: Set[str] = set()
    if module is None:
        return prefixes
    for inst_name, submodule in getattr(module, "_submodules", ()):
        flat_prefix = f"{_parent_prefix}{inst_name}_"
        type_name = getattr(submodule, "_type_name", getattr(submodule, "name", submodule.__class__.__name__))
        if str(type_name) in safe_types:
            prefixes.add(flat_prefix)
            prefixes.add(f"u_{flat_prefix}")
            continue
        prefixes.update(_collect_safe_primitive_prefixes(submodule, safe_types=safe_types, _parent_prefix=flat_prefix))
    return prefixes


def _collect_safe_cdc_prefixes(module: Any, *, _parent_prefix: str = "") -> Set[str]:
    return _collect_safe_primitive_prefixes(
        module,
        safe_types=set(_SAFE_CDC_TYPES),
        _parent_prefix=_parent_prefix,
    )


def _collect_safe_reset_prefixes(module: Any, *, _parent_prefix: str = "") -> Set[str]:
    return _collect_safe_primitive_prefixes(
        module,
        safe_types=set(_SAFE_RESET_TYPES),
        _parent_prefix=_parent_prefix,
    )


def _collect_source_locations(module: Any) -> Dict[str, Tuple[Optional[str], Optional[int]]]:
    if module is None:
        return {}
    source_locs: Dict[str, Tuple[Optional[str], Optional[int]]] = {}
    for stmt in getattr(module, "_top_level", ()):
        _collect_stmt_source_locations(stmt, source_locs)
    for body in getattr(module, "_comb_blocks", ()):
        for stmt in body:
            _collect_stmt_source_locations(stmt, source_locs)
    for body in getattr(module, "_latch_blocks", ()):
        for stmt in body:
            _collect_stmt_source_locations(stmt, source_locs)
    for _clk, _rst, _async, _active_low, body in getattr(module, "_seq_blocks", ()):
        for stmt in body:
            _collect_stmt_source_locations(stmt, source_locs)
    return source_locs


def _collect_stmt_source_locations(stmt: object, out: Dict[str, Tuple[Optional[str], Optional[int]]]) -> None:
    loc = getattr(stmt, "source_location", None)
    file_name = getattr(loc, "file", None)
    line_no = getattr(loc, "line", None)
    target_name = None
    if hasattr(stmt, "target") and getattr(stmt, "target", None) is not None:
        target_name = _dsl_target_name(getattr(stmt, "target"))
    elif hasattr(stmt, "target_signal"):
        target = getattr(stmt, "target_signal")
        target_name = getattr(target, "name", None)
    elif hasattr(stmt, "mem_name"):
        target_name = getattr(stmt, "mem_name")
    elif hasattr(stmt, "array_name"):
        target_name = getattr(stmt, "array_name")
    if target_name and target_name not in out:
        out[target_name] = (file_name, line_no)
    for attr in ("then_body", "else_body", "default_body", "body"):
        body = getattr(stmt, attr, None)
        if isinstance(body, list):
            for child in body:
                _collect_stmt_source_locations(child, out)
    for attr in ("elif_bodies", "cases", "branches"):
        entries = getattr(stmt, attr, None)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], list):
                    for child in entry[1]:
                        _collect_stmt_source_locations(child, out)


def _resolve_dsl_reset_signal(
    rst: object,
    *,
    reset_async: bool,
    reset_active_low: bool,
) -> Tuple[Optional[str], bool, bool]:
    if rst is None:
        return None, reset_async, reset_active_low
    rst_name = getattr(rst, "name", None)
    if rst_name:
        return str(rst_name), bool(reset_async), bool(reset_active_low)
    expr = getattr(rst, "_expr", None)
    if expr is None:
        return None, bool(reset_async), bool(reset_active_low)
    if getattr(expr, "op", None) == "~":
        inner = getattr(expr, "operand", None)
        inner_signal = getattr(inner, "signal", None)
        if getattr(inner_signal, "name", None):
            return str(inner_signal.name), True, True
        if getattr(inner, "name", None):
            return str(inner.name), True, True
    return None, bool(reset_async), bool(reset_active_low)


def _dsl_target_name(target: object) -> Optional[str]:
    if target is None:
        return None
    direct_name = getattr(target, "name", None)
    if direct_name:
        return str(direct_name)
    signal = getattr(target, "signal", None)
    if getattr(signal, "name", None):
        return str(signal.name)
    return None


def _dsl_direct_assignments(stmts: Sequence[object]) -> Dict[str, object]:
    assigns: Dict[str, object] = {}
    for stmt in stmts:
        target_name = _dsl_target_name(getattr(stmt, "target", None))
        if target_name:
            assigns[target_name] = getattr(stmt, "value", None)
            continue
        target_signal = getattr(stmt, "target_signal", None)
        if getattr(target_signal, "name", None):
            assigns[str(target_signal.name)] = getattr(stmt, "value", None)
    return assigns


def _dsl_expr_matches_reset_value(expr: object, reset_name: str, active_value: int) -> bool:
    signal_refs = _dsl_expr_signal_refs(expr)
    if signal_refs != {reset_name}:
        return False
    signal = getattr(expr, "signal", None)
    if getattr(signal, "name", None):
        return active_value == 1
    op = getattr(expr, "op", None)
    if op == "~":
        return active_value == 0
    if op in {"==", "!="}:
        lhs = getattr(expr, "lhs", None)
        rhs = getattr(expr, "rhs", None)
        lhs_signal = getattr(getattr(lhs, "signal", None), "name", None)
        rhs_signal = getattr(getattr(rhs, "signal", None), "name", None)
        lhs_const = getattr(lhs, "value", None) if hasattr(lhs, "value") else None
        rhs_const = getattr(rhs, "value", None) if hasattr(rhs, "value") else None
        if lhs_signal == reset_name and rhs_const is not None:
            const_value = int(rhs_const) & 1
        elif rhs_signal == reset_name and lhs_const is not None:
            const_value = int(lhs_const) & 1
        else:
            return False
        if op == "==":
            return const_value == active_value
        return const_value != active_value
    return False


def _dsl_split_reset_guard(
    stmts: Sequence[object],
    *,
    reset_name: Optional[str],
    reset_active_low: bool,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    if not reset_name:
        return {}, {}
    active_value = 0 if reset_active_low else 1
    inactive_value = 1 - active_value
    for stmt in stmts:
        cond = getattr(stmt, "cond", None)
        then_body = getattr(stmt, "then_body", None)
        else_body = getattr(stmt, "else_body", None)
        if cond is None or not isinstance(then_body, list) or not isinstance(else_body, list):
            continue
        if _dsl_expr_matches_reset_value(cond, reset_name, active_value):
            return _dsl_direct_assignments(then_body), _dsl_direct_assignments(else_body)
        if _dsl_expr_matches_reset_value(cond, reset_name, inactive_value):
            return _dsl_direct_assignments(else_body), _dsl_direct_assignments(then_body)
    return {}, {}


def _dsl_expr_is_constant_like(expr: object, target_name: str) -> bool:
    refs = _dsl_expr_signal_refs(expr) - {target_name}
    return not refs and not _dsl_expr_memory_reads(expr)


def _compiled_expr_data_signal_refs(expr: object) -> Set[str]:
    refs: Set[str] = set()
    if isinstance(expr, SignalRef):
        refs.add(expr.name)
        return refs
    if isinstance(expr, MemoryReadExpr):
        return refs
    for attr in ("operand", "lhs", "rhs", "true_expr", "false_expr", "when_true", "when_false", "value"):
        child = getattr(expr, attr, None)
        if child is not None:
            refs.update(_compiled_expr_data_signal_refs(child))
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                refs.update(_compiled_expr_data_signal_refs(child))
    return refs


def _compiled_expr_is_constant_like(expr: object, target_name: str) -> bool:
    refs = _compiled_expr_data_signal_refs(expr) - {target_name}
    return not refs and not _expr_memory_reads(expr)


def _compiled_expr_has_constant_like_branch(expr: object, target_name: str) -> bool:
    if isinstance(expr, MuxExpr):
        return _compiled_expr_is_constant_like(expr.when_true, target_name) or _compiled_expr_is_constant_like(
            expr.when_false,
            target_name,
        )
    return _compiled_expr_is_constant_like(expr, target_name)


def _compiled_expr_is_strict_constant(expr: object) -> bool:
    return not _compiled_expr_data_signal_refs(expr) and not _expr_memory_reads(expr)


def _compiled_expr_matches_reset_value(expr: object, reset_name: str, active_value: int) -> bool:
    if isinstance(expr, SignalRef):
        return expr.name == reset_name and active_value == 1
    if isinstance(expr, UnaryExpr):
        if expr.op not in {"!", "~"}:
            return False
        inner = getattr(expr, "value", None)
        return isinstance(inner, SignalRef) and inner.name == reset_name and active_value == 0
    if isinstance(expr, BinaryExpr) and expr.op in {"==", "!="}:
        lhs = getattr(expr, "lhs", None)
        rhs = getattr(expr, "rhs", None)
        if isinstance(lhs, SignalRef) and isinstance(rhs, ConstExpr) and lhs.name == reset_name:
            const_value = int(rhs.value) & 1
        elif isinstance(rhs, SignalRef) and isinstance(lhs, ConstExpr) and rhs.name == reset_name:
            const_value = int(lhs.value) & 1
        else:
            return False
        if expr.op == "==":
            return const_value == active_value
        return const_value != active_value
    return False


def _compiled_split_reset_guard(
    expr: object,
    *,
    reset_name: Optional[str],
    reset_active_low: bool,
) -> Tuple[Optional[object], Optional[object]]:
    if not reset_name or not isinstance(expr, MuxExpr):
        return None, None
    active_value = 0 if reset_active_low else 1
    inactive_value = 1 - active_value
    if _compiled_expr_matches_reset_value(expr.cond, reset_name, active_value):
        return expr.when_true, expr.when_false
    if _compiled_expr_matches_reset_value(expr.cond, reset_name, inactive_value):
        return expr.when_false, expr.when_true
    return None, None


def _infer_safe_reset_chain_targets(
    *,
    transfer_sources: Mapping[str, Optional[str]],
    active_constant_like_targets: Set[str],
    reset_constant_like_targets: Set[str],
    widths: Mapping[str, int],
) -> Set[str]:
    safe_targets: Set[str] = set()
    for target_name, source_name in transfer_sources.items():
        if not source_name:
            continue
        if widths.get(source_name, 1) != 1 or widths.get(target_name, 1) != 1:
            continue
        if (
            source_name in active_constant_like_targets
            and source_name in reset_constant_like_targets
            and target_name in reset_constant_like_targets
        ):
            safe_targets.add(target_name)

    changed = True
    while changed:
        changed = False
        for target_name, source_name in transfer_sources.items():
            if not source_name:
                continue
            if widths.get(source_name, 1) != 1 or widths.get(target_name, 1) != 1:
                continue
            if source_name not in safe_targets or target_name in safe_targets:
                continue
            if target_name not in reset_constant_like_targets:
                continue
            safe_targets.add(target_name)
            changed = True
    return safe_targets


def _dsl_expr_is_target_slice(expr: object, *, target_name: str, hi: int, lo: int) -> bool:
    if hi < lo:
        return False
    operand = getattr(expr, "operand", None)
    signal = getattr(operand, "signal", None)
    return (
        getattr(signal, "name", None) == target_name
        and getattr(expr, "hi", None) == hi
        and getattr(expr, "lo", None) == lo
    )


def _dsl_expr_is_shift_register_update(expr: object, *, target_name: str, width: int) -> bool:
    if width < 2 or not hasattr(expr, "operands"):
        return False
    operands = list(getattr(expr, "operands", ()) or ())
    if len(operands) != 2:
        return False
    lhs, rhs = operands
    return (
        _dsl_expr_is_target_slice(lhs, target_name=target_name, hi=width - 2, lo=0)
        and _dsl_expr_is_constant_like(rhs, target_name)
        and getattr(rhs, "width", None) == 1
    ) or (
        _dsl_expr_is_constant_like(lhs, target_name)
        and getattr(lhs, "width", None) == 1
        and _dsl_expr_is_target_slice(rhs, target_name=target_name, hi=width - 1, lo=1)
    )


def _compiled_expr_contains_shift(expr: object) -> bool:
    if isinstance(expr, BinaryExpr) and expr.op in {"<<", ">>"}:
        return True
    for attr in ("value", "lhs", "rhs", "when_true", "when_false"):
        child = getattr(expr, attr, None)
        if child is not None and _compiled_expr_contains_shift(child):
            return True
    return False


def _compiled_expr_is_shift_register_update(expr: object, *, target_name: str, width: int) -> bool:
    if width < 2:
        return False
    if isinstance(expr, MuxExpr):
        return (
            _compiled_expr_is_strict_constant(expr.when_true)
            and _compiled_expr_is_shift_register_update(
                expr.when_false,
                target_name=target_name,
                width=width,
            )
        ) or (
            _compiled_expr_is_strict_constant(expr.when_false)
            and _compiled_expr_is_shift_register_update(
                expr.when_true,
                target_name=target_name,
                width=width,
            )
        )
    refs = _compiled_expr_data_signal_refs(expr)
    if refs != {target_name} or _expr_memory_reads(expr):
        return False
    return _compiled_expr_contains_shift(expr)


def _extract_dsl_transfer_source(expr: object, target_name: str) -> Optional[str]:
    refs = _dsl_expr_signal_refs(expr) - {target_name}
    if len(refs) == 1 and not _dsl_expr_memory_reads(expr):
        return next(iter(refs))
    return None


def _extract_compiled_transfer_source(expr: object, target_name: str) -> Optional[str]:
    refs = _compiled_expr_data_signal_refs(expr) - {target_name}
    if len(refs) == 1 and not _expr_memory_reads(expr):
        return next(iter(refs))
    return None


def _collect_dsl_signal_consumers(module: Any) -> Dict[str, Set[str]]:
    consumers: Dict[str, Set[str]] = {}
    for stmt in getattr(module, "_top_level", ()):
        _collect_dsl_stmt_signal_consumers(stmt, consumers)
    for body in getattr(module, "_comb_blocks", ()):
        for stmt in body:
            _collect_dsl_stmt_signal_consumers(stmt, consumers)
    for body in getattr(module, "_latch_blocks", ()):
        for stmt in body:
            _collect_dsl_stmt_signal_consumers(stmt, consumers)
    for _clk, _rst, _async, _active_low, body in getattr(module, "_seq_blocks", ()):
        for stmt in body:
            _collect_dsl_stmt_signal_consumers(stmt, consumers)
    return consumers


def _collect_dsl_comb_aliases(module: Any) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for target_name, expr in _iter_dsl_comb_assignments(module):
        if not target_name:
            continue
        source_name = _extract_dsl_transfer_source(expr, target_name)
        if source_name:
            aliases[target_name] = source_name
    return aliases


def _collect_dsl_stmt_signal_consumers(stmt: object, out: Dict[str, Set[str]]) -> None:
    consumer_name = _dsl_stmt_target_name(stmt)
    for attr in ("value", "cond", "addr", "index"):
        expr = getattr(stmt, attr, None)
        if expr is None:
            continue
        for signal_name in _dsl_expr_signal_refs(expr):
            out.setdefault(signal_name, set()).add(consumer_name)
    for attr in ("then_body", "else_body", "default_body", "body"):
        body = getattr(stmt, attr, None)
        if isinstance(body, list):
            for child in body:
                _collect_dsl_stmt_signal_consumers(child, out)
    for attr in ("elif_bodies", "cases", "branches"):
        entries = getattr(stmt, attr, None)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], list):
                    for child in entry[1]:
                        _collect_dsl_stmt_signal_consumers(child, out)


def _collect_executable_signal_consumers(module: SimModule) -> Dict[str, Set[str]]:
    consumers: Dict[str, Set[str]] = {}
    for assignment in module.assignments:
        for signal_name in _expr_signal_refs(assignment.expr):
            consumers.setdefault(signal_name, set()).add(str(assignment.target))
    for memory_write in module.memory_writes:
        for expr in (memory_write.addr, memory_write.value, memory_write.enable):
            for signal_name in _expr_signal_refs(expr):
                consumers.setdefault(signal_name, set()).add(str(memory_write.memory))
    return consumers


def _collect_executable_comb_aliases(module: SimModule) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for assignment in module.assignments:
        if assignment.phase != "comb":
            continue
        source_name = _extract_compiled_transfer_source(assignment.expr, assignment.target)
        if source_name:
            aliases[str(assignment.target)] = source_name
    return aliases


def _normalize_consumer_targets(
    consumers: Optional[Iterable[str]],
    aliases: Mapping[str, str],
) -> Set[str]:
    normalized: Set[str] = set()
    if not consumers:
        return normalized
    for consumer in consumers:
        target = str(consumer)
        seen: Set[str] = set()
        while target in aliases and target not in seen:
            seen.add(target)
            target = aliases[target]
        normalized.add(target)
    return normalized


def _dsl_declared_signal_names(module: Any) -> Set[str]:
    names: Set[str] = set()
    for group_name in ("_inputs", "_outputs", "_wires", "_regs"):
        names.update(str(name) for name in getattr(module, group_name, {}).keys())
    return names


def _iter_dsl_comb_assignments(module: Any) -> Iterable[Tuple[str, object]]:
    for stmt in getattr(module, "_top_level", ()):
        yield from _iter_dsl_comb_assignments_in_stmt(stmt)
    for body in getattr(module, "_comb_blocks", ()):
        for stmt in body:
            yield from _iter_dsl_comb_assignments_in_stmt(stmt)


def _iter_dsl_comb_assignments_in_stmt(stmt: object) -> Iterable[Tuple[str, object]]:
    target_name = _dsl_target_name(getattr(stmt, "target", None))
    if target_name:
        yield target_name, getattr(stmt, "value", None)
    target_signal = getattr(stmt, "target_signal", None)
    if getattr(target_signal, "name", None):
        yield str(target_signal.name), getattr(stmt, "value", None)
    for attr in ("then_body", "else_body", "default_body", "body"):
        body = getattr(stmt, attr, None)
        if isinstance(body, list):
            for child in body:
                yield from _iter_dsl_comb_assignments_in_stmt(child)
    for attr in ("elif_bodies", "cases", "branches"):
        entries = getattr(stmt, attr, None)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], list):
                    for child in entry[1]:
                        yield from _iter_dsl_comb_assignments_in_stmt(child)


def _propagate_safe_reset_signals_dsl(
    module: Any,
    *,
    safe_reset_prefixes: Set[str],
    reset_base_signals: Set[str],
) -> Set[str]:
    safe_signals = set(reset_base_signals)
    safe_signals.update(
        name for name in _dsl_declared_signal_names(module) if _belongs_to_safe_cdc_primitive(name, safe_reset_prefixes)
    )
    changed = True
    while changed:
        changed = False
        for target_name, expr in _iter_dsl_comb_assignments(module):
            refs = _dsl_expr_signal_refs(expr)
            if not refs or not refs.issubset(safe_signals):
                continue
            if target_name in safe_signals:
                continue
            safe_signals.add(target_name)
            changed = True
    return safe_signals


def _propagate_safe_reset_signals_executable(
    module: SimModule,
    *,
    reset_base_signals: Set[str],
) -> Set[str]:
    safe_signals = set(reset_base_signals)
    changed = True
    while changed:
        changed = False
        for assignment in module.assignments:
            if assignment.phase != "comb":
                continue
            refs = _expr_signal_refs(assignment.expr)
            if not refs or not refs.issubset(safe_signals):
                continue
            if assignment.target in safe_signals:
                continue
            safe_signals.add(assignment.target)
            changed = True
    return safe_signals


def _collect_safe_reset_outputs_by_domain(module: Any) -> Dict[str, Set[str]]:
    outputs_by_domain: Dict[str, Set[str]] = {}
    for stmt in getattr(module, "_top_level", ()):
        if not hasattr(stmt, "module") or not hasattr(stmt, "port_map"):
            continue
        submodule = getattr(stmt, "module", None)
        type_name = getattr(submodule, "_type_name", getattr(submodule, "name", submodule.__class__.__name__))
        if str(type_name) not in _SAFE_RESET_TYPES:
            continue
        port_map = getattr(stmt, "port_map", {}) or {}
        clk_expr = port_map.get("clk")
        rst_sync_expr = port_map.get("rst_sync")
        clk_name = _extract_dsl_expr_single_ref(clk_expr)
        rst_sync_name = _extract_dsl_expr_single_ref(rst_sync_expr)
        if not clk_name or not rst_sync_name:
            continue
        outputs_by_domain.setdefault(clk_name, set()).add(rst_sync_name)
    return outputs_by_domain


def _extract_dsl_expr_single_ref(expr: object) -> Optional[str]:
    refs = _dsl_expr_signal_refs(expr)
    if len(refs) != 1:
        return None
    return next(iter(refs))


def _recognize_dsl_cdc_structures(
    module: Any,
    *,
    signal_widths: Mapping[str, int],
    safe_reset_prefixes: Set[str],
    primitive_safe_reset_outputs_by_domain: Optional[Mapping[str, Set[str]]] = None,
) -> _RecognizedCdcStructures:
    consumers = _collect_dsl_signal_consumers(module)
    comb_aliases = _collect_dsl_comb_aliases(module)
    safe_first_stages: Set[str] = set()
    reset_base_signals_by_domain = {
        domain_name: set(signal_names)
        for domain_name, signal_names in (primitive_safe_reset_outputs_by_domain or {}).items()
    }
    reset_builder_candidates: Dict[int, str] = {}

    for index, (clk, rst, reset_async, reset_active_low, body) in enumerate(getattr(module, "_seq_blocks", ())):
        clk_name = getattr(clk, "name", str(clk)) if clk is not None else None
        reset_name, resolved_async, resolved_active_low = _resolve_dsl_reset_signal(
            rst,
            reset_async=bool(reset_async),
            reset_active_low=bool(reset_active_low),
        )
        reset_assigns, active_assigns = _dsl_split_reset_guard(
            body,
            reset_name=reset_name,
            reset_active_low=resolved_active_low,
        )
        if not active_assigns:
            active_assigns = _dsl_direct_assignments(body)
        transfer_sources = {
            target_name: _extract_dsl_transfer_source(expr, target_name)
            for target_name, expr in active_assigns.items()
        }
        constant_like_targets = {
            target_name
            for target_name, expr in active_assigns.items()
            if _dsl_expr_is_constant_like(expr, target_name)
        }
        reset_constant_like_targets = {
            target_name
            for target_name, expr in reset_assigns.items()
            if _dsl_expr_is_constant_like(expr, target_name)
        }
        for stage2, stage1 in transfer_sources.items():
            if not stage1:
                continue
            if signal_widths.get(stage1, 1) != 1 or signal_widths.get(stage2, 1) != 1:
                continue
            source_name = transfer_sources.get(stage1)
            consumer_targets = _normalize_consumer_targets(consumers.get(stage1, set()), comb_aliases)
            if source_name and consumer_targets == {stage2}:
                safe_first_stages.add(stage1)
        if resolved_async:
            safe_reset_chain_targets = _infer_safe_reset_chain_targets(
                transfer_sources=transfer_sources,
                active_constant_like_targets=constant_like_targets,
                reset_constant_like_targets=reset_constant_like_targets,
                widths=signal_widths,
            )
            safe_reset_chain_targets.update(
                target_name
                for target_name, expr in active_assigns.items()
                if target_name in reset_constant_like_targets
                and _dsl_expr_is_shift_register_update(
                    expr,
                    target_name=target_name,
                    width=signal_widths.get(target_name, 1),
                )
            )
            if safe_reset_chain_targets and clk_name:
                reset_base_signals_by_domain.setdefault(clk_name, set()).update(safe_reset_chain_targets)
                reset_builder_candidates[index] = clk_name

    safe_reset_signals_by_domain = {
        domain_name: tuple(
            sorted(
                _propagate_safe_reset_signals_dsl(
                    module,
                    safe_reset_prefixes=safe_reset_prefixes,
                    reset_base_signals=set(reset_base_signals),
                )
            )
        )
        for domain_name, reset_base_signals in reset_base_signals_by_domain.items()
    }
    reset_builder_blocks: Set[int] = set()
    for index, domain_name in reset_builder_candidates.items():
        safe_resets = set(safe_reset_signals_by_domain.get(domain_name, ()))
        if not safe_resets:
            continue
        for other_index, (other_clk, other_rst, other_async, other_active_low, _other_body) in enumerate(
            getattr(module, "_seq_blocks", ())
        ):
            if other_index == index:
                continue
            other_domain = getattr(other_clk, "name", str(other_clk)) if other_clk is not None else None
            if other_domain != domain_name:
                continue
            other_reset_name, other_resolved_async, _ = _resolve_dsl_reset_signal(
                other_rst,
                reset_async=bool(other_async),
                reset_active_low=bool(other_active_low),
            )
            if other_resolved_async and other_reset_name in safe_resets:
                reset_builder_blocks.add(index)
                break
    return _RecognizedCdcStructures(
        safe_first_stage_targets=tuple(sorted(safe_first_stages)),
        safe_reset_signals_by_domain=safe_reset_signals_by_domain,
        reset_builder_block_indices=tuple(sorted(reset_builder_blocks)),
    )


def _recognize_executable_cdc_structures(module: SimModule) -> _RecognizedCdcStructures:
    signal_map = module.signal_map()
    signal_widths = {
        name: int(getattr(signal, "width", 1))
        for name, signal in signal_map.items()
    }
    consumers = _collect_executable_signal_consumers(module)
    comb_aliases = _collect_executable_comb_aliases(module)
    state_domain_by_target: Dict[str, str] = {}
    for assignment in module.assignments:
        if assignment.phase != "seq" or assignment.clock_domain is None:
            continue
        if assignment.target in state_domain_by_target and state_domain_by_target[assignment.target] != assignment.clock_domain:
            state_domain_by_target.pop(assignment.target, None)
            continue
        state_domain_by_target.setdefault(assignment.target, assignment.clock_domain)
    domain_map = {domain.name: domain for domain in module.clock_domains}
    safe_first_stages: Set[str] = set()
    reset_base_signals_by_domain: Dict[str, Set[str]] = {}
    seq_assignments = {assignment.target: assignment for assignment in module.assignments if assignment.phase == "seq"}
    transfer_sources = {
        target_name: _extract_compiled_transfer_source(assignment.expr, target_name)
        for target_name, assignment in seq_assignments.items()
    }
    constant_like_targets = {
        target_name
        for target_name, assignment in seq_assignments.items()
        if _compiled_expr_is_constant_like(assignment.expr, target_name)
    }
    for stage2, stage1 in transfer_sources.items():
        if not stage1:
            continue
        if int(getattr(signal_map.get(stage1), "width", 1)) != 1 or int(getattr(signal_map.get(stage2), "width", 1)) != 1:
            continue
        domain_name = state_domain_by_target.get(stage2)
        if domain_name is None or state_domain_by_target.get(stage1) != domain_name:
            continue
        source_name = transfer_sources.get(stage1)
        consumer_targets = _normalize_consumer_targets(consumers.get(stage1, set()), comb_aliases)
        if source_name and consumer_targets == {stage2}:
            safe_first_stages.add(stage1)
    assignments_by_domain: Dict[str, Dict[str, Assignment]] = {}
    for assignment in module.assignments:
        if assignment.phase != "seq" or assignment.clock_domain is None:
            continue
        assignments_by_domain.setdefault(assignment.clock_domain, {})[assignment.target] = assignment
    for domain_name, domain_assignments in assignments_by_domain.items():
        domain = domain_map.get(domain_name)
        if domain is None or not domain.reset_async:
            continue
        active_constant_like_targets: Set[str] = set()
        reset_constant_like_targets: Set[str] = set()
        active_transfer_sources: Dict[str, Optional[str]] = {}
        for target_name, assignment in domain_assignments.items():
            if _compiled_expr_is_constant_like(assignment.expr, target_name):
                active_constant_like_targets.add(target_name)
            if _compiled_expr_has_constant_like_branch(assignment.expr, target_name):
                reset_constant_like_targets.add(target_name)
            active_transfer_sources[target_name] = _extract_compiled_transfer_source(assignment.expr, target_name)
        reset_base_signals_by_domain.setdefault(domain_name, set()).update(
            _infer_safe_reset_chain_targets(
                transfer_sources=active_transfer_sources,
                active_constant_like_targets=active_constant_like_targets,
                reset_constant_like_targets=reset_constant_like_targets,
                widths=signal_widths,
            )
        )
        reset_base_signals_by_domain.setdefault(domain_name, set()).update(
            target_name
            for target_name, assignment in domain_assignments.items()
            if target_name in reset_constant_like_targets
            and _compiled_expr_is_shift_register_update(
                assignment.expr,
                target_name=target_name,
                width=signal_widths.get(target_name, 1),
            )
        )
    safe_reset_signals_by_domain = {
        domain_name: tuple(
            sorted(
                _propagate_safe_reset_signals_executable(
                    module,
                    reset_base_signals=set(reset_base_signals),
                )
            )
        )
        for domain_name, reset_base_signals in reset_base_signals_by_domain.items()
    }
    return _RecognizedCdcStructures(
        safe_first_stage_targets=tuple(sorted(safe_first_stages)),
        safe_reset_signals_by_domain=safe_reset_signals_by_domain,
        reset_builder_block_indices=(),
    )


def _dsl_clock_domains(module: Any) -> Tuple[str, ...]:
    ordered: List[str] = []
    seen: Set[str] = set()
    for clk, _rst, _async, _active_low, _body in getattr(module, "_seq_blocks", ()):
        if clk is None:
            continue
        name = getattr(clk, "name", str(clk))
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return tuple(ordered)


def _dsl_signal_widths(module: Any) -> Dict[str, int]:
    widths: Dict[str, int] = {}
    for group_name in ("_inputs", "_outputs", "_wires", "_regs"):
        for name, signal in getattr(module, group_name, {}).items():
            widths[name] = int(getattr(signal, "width", 1))
    return widths


def _dsl_memory_widths(module: Any) -> Dict[str, int]:
    widths: Dict[str, int] = {}
    for name, memory in getattr(module, "_memories", {}).items():
        widths[name] = int(getattr(memory, "width", 1))
    for name, array in getattr(module, "_arrays", {}).items():
        widths[name] = int(getattr(array, "width", 1))
    return widths


def _dsl_state_writers(module: Any) -> Dict[str, Set[Optional[str]]]:
    writers: Dict[str, Set[Optional[str]]] = {}
    for clk, _rst, _async, _active_low, body in getattr(module, "_seq_blocks", ()):
        domain = getattr(clk, "name", str(clk))
        _record_dsl_stmt_writers(body, domain, writers, kind="state")
    return writers


def _dsl_memory_writers(module: Any) -> Dict[str, Set[Optional[str]]]:
    writers: Dict[str, Set[Optional[str]]] = {}
    for clk, _rst, _async, _active_low, body in getattr(module, "_seq_blocks", ()):
        domain = getattr(clk, "name", str(clk))
        _record_dsl_stmt_writers(body, domain, writers, kind="memory")
    return writers


def _record_dsl_stmt_writers(
    stmts: Sequence[object],
    domain: str,
    out: Dict[str, Set[Optional[str]]],
    *,
    kind: str,
) -> None:
    for stmt in stmts:
        if kind == "state":
            target_signal = getattr(stmt, "target_signal", None)
            target_name = _dsl_target_name(getattr(stmt, "target", None))
            if target_name:
                out.setdefault(target_name, set()).add(domain)
            if getattr(target_signal, "name", None):
                out.setdefault(target_signal.name, set()).add(domain)
        if kind == "memory":
            mem_name = getattr(stmt, "mem_name", None) or getattr(stmt, "array_name", None)
            if mem_name:
                out.setdefault(mem_name, set()).add(domain)
        for attr in ("then_body", "else_body", "default_body", "body"):
            body = getattr(stmt, attr, None)
            if isinstance(body, list):
                _record_dsl_stmt_writers(body, domain, out, kind=kind)
        for attr in ("elif_bodies", "cases", "branches"):
            entries = getattr(stmt, attr, None)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], list):
                        _record_dsl_stmt_writers(entry[1], domain, out, kind=kind)


def _dsl_comb_source_domains(
    module: Any,
    *,
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
    safe_cdc_prefixes: Set[str],
) -> Dict[str, Set[Optional[str]]]:
    source_domains: Dict[str, Set[Optional[str]]] = {}
    for body in getattr(module, "_comb_blocks", ()):
        for stmt in body:
            if hasattr(stmt, "target"):
                target = getattr(stmt, "target")
                target_name = getattr(target, "name", None)
                if not target_name or _belongs_to_safe_cdc_primitive(target_name, safe_cdc_prefixes):
                    continue
                refs = _dsl_expr_signal_refs(getattr(stmt, "value", None))
                mems = _dsl_expr_memory_reads(getattr(stmt, "value", None))
                domains: Set[Optional[str]] = set()
                for name in refs:
                    domains.update(state_writers.get(name, ()))
                for name in mems:
                    domains.update(memory_writers.get(name, ()))
                if domains:
                    source_domains.setdefault(target_name, set()).update(domains)
    return source_domains


def _dsl_findings_in_stmt_list(
    stmts: Sequence[object],
    *,
    dst_domain: str,
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
    comb_domain_map: Mapping[str, Set[Optional[str]]],
    signal_widths: Mapping[str, int],
    memory_widths: Mapping[str, int],
    primitive_hints: Mapping[str, Set[str]],
    safe_cdc_prefixes: Set[str],
    safe_first_stage_targets: Set[str],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for stmt in stmts:
        value_expr = getattr(stmt, "value", None)
        if value_expr is not None:
            refs = _dsl_expr_signal_refs(value_expr)
            mems = _dsl_expr_memory_reads(value_expr)
            target_name = _dsl_stmt_target_name(stmt)
            for signal_name in refs:
                if target_name in safe_first_stage_targets:
                    continue
                if _belongs_to_safe_cdc_primitive(signal_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                    target_name,
                    safe_cdc_prefixes,
                ):
                    continue
                producer_domains = set(state_writers.get(signal_name, ()))
                producer_domains.update(comb_domain_map.get(signal_name, ()))
                for src_domain in sorted(domain for domain in producer_domains if domain is not None):
                    if src_domain == dst_domain:
                        continue
                    findings.append(
                        _make_signal_crossing_finding(
                            signal_name=signal_name,
                            width=signal_widths.get(signal_name, 1),
                            src_domain=src_domain,
                            dst_domain=dst_domain,
                            dst_target=target_name,
                            primitive_hints=primitive_hints,
                            source_locs=source_locs,
                        )
                    )
            for memory_name in mems:
                if _belongs_to_safe_cdc_primitive(memory_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                    target_name,
                    safe_cdc_prefixes,
                ):
                    continue
                producer_domains = memory_writers.get(memory_name, ())
                for src_domain in sorted(domain for domain in producer_domains if domain is not None):
                    if src_domain == dst_domain:
                        continue
                    findings.append(
                        _make_memory_crossing_finding(
                            memory_name=memory_name,
                            width=memory_widths.get(memory_name, 1),
                            src_domain=src_domain,
                            dst_domain=dst_domain,
                            dst_target=target_name,
                            primitive_hints=primitive_hints,
                            source_locs=source_locs,
                        )
                    )
        for attr in ("then_body", "else_body", "default_body", "body"):
            body = getattr(stmt, attr, None)
            if isinstance(body, list):
                findings.extend(
                    _dsl_findings_in_stmt_list(
                        body,
                        dst_domain=dst_domain,
                        state_writers=state_writers,
                        memory_writers=memory_writers,
                        comb_domain_map=comb_domain_map,
                        signal_widths=signal_widths,
                        memory_widths=memory_widths,
                        primitive_hints=primitive_hints,
                        safe_cdc_prefixes=safe_cdc_prefixes,
                        safe_first_stage_targets=safe_first_stage_targets,
                        source_locs=source_locs,
                    )
                )
        for attr in ("elif_bodies", "cases", "branches"):
            entries = getattr(stmt, attr, None)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], list):
                        findings.extend(
                            _dsl_findings_in_stmt_list(
                                entry[1],
                                dst_domain=dst_domain,
                                state_writers=state_writers,
                                memory_writers=memory_writers,
                                comb_domain_map=comb_domain_map,
                                signal_widths=signal_widths,
                                memory_widths=memory_widths,
                                primitive_hints=primitive_hints,
                                safe_cdc_prefixes=safe_cdc_prefixes,
                                safe_first_stage_targets=safe_first_stage_targets,
                                source_locs=source_locs,
                            )
                        )
    return findings


def _dsl_comb_memory_findings(
    comb_body: Sequence[object],
    *,
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
    comb_domain_map: Mapping[str, Set[Optional[str]]],
    memory_widths: Mapping[str, int],
    primitive_hints: Mapping[str, Set[str]],
    safe_cdc_prefixes: Set[str],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for stmt in comb_body:
        value_expr = getattr(stmt, "value", None)
        if value_expr is None:
            continue
        target_name = _dsl_stmt_target_name(stmt)
        for memory_name in _dsl_expr_memory_reads(value_expr):
            if _belongs_to_safe_cdc_primitive(memory_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                target_name,
                safe_cdc_prefixes,
            ):
                continue
            producer_domains = tuple(sorted(domain for domain in memory_writers.get(memory_name, ()) if domain is not None))
            if len(producer_domains) <= 1:
                src_domain = producer_domains[0] if producer_domains else None
                findings.append(
                    _make_memory_crossing_finding(
                        memory_name=memory_name,
                        width=memory_widths.get(memory_name, 1),
                        src_domain=src_domain,
                        dst_domain=None,
                        dst_target=target_name,
                        primitive_hints=primitive_hints,
                        source_locs=source_locs,
                    )
                )
                continue
            dst_domains = comb_domain_map.get(target_name, ())
            if len(dst_domains) != 1:
                continue
            dst_domain = next(iter(dst_domains))
            for src_domain in producer_domains:
                if src_domain == dst_domain:
                    continue
                findings.append(
                    _make_memory_crossing_finding(
                        memory_name=memory_name,
                        width=memory_widths.get(memory_name, 1),
                        src_domain=src_domain,
                        dst_domain=dst_domain,
                        dst_target=target_name,
                        primitive_hints=primitive_hints,
                        source_locs=source_locs,
                    )
                )
    return findings


def _dsl_stmt_target_name(stmt: object) -> str:
    target_name = _dsl_target_name(getattr(stmt, "target", None))
    if target_name:
        return target_name
    target_signal = getattr(stmt, "target_signal", None)
    if getattr(target_signal, "name", None):
        return str(target_signal.name)
    mem_name = getattr(stmt, "mem_name", None)
    if mem_name:
        return str(mem_name)
    array_name = getattr(stmt, "array_name", None)
    if array_name:
        return str(array_name)
    return "<unknown>"


def _analyze_assignments(
    module: SimModule,
    *,
    signal_map: Mapping[str, object],
    memory_map: Mapping[str, object],
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
    comb_domain_map: Mapping[str, Set[Optional[str]]],
    primitive_hints: Mapping[str, Set[str]],
    safe_cdc_prefixes: Set[str],
    safe_first_stage_targets: Set[str],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for assignment in module.assignments:
        target_signal = signal_map.get(assignment.target)
        if assignment.phase == "comb" and getattr(target_signal, "kind", None) == "wire":
            continue
        dst_domain = assignment.clock_domain if assignment.phase == "seq" else None
        src_names = _expr_signal_refs(assignment.expr)
        mem_reads = _expr_memory_reads(assignment.expr)

        if assignment.phase != "comb":
            for signal_name in src_names:
                if str(assignment.target) in safe_first_stage_targets:
                    continue
                producer_domains = set(state_writers.get(signal_name, ()))
                producer_domains.update(comb_domain_map.get(signal_name, ()))
                if not producer_domains:
                    continue
                for src_domain in sorted(_normalize_domains(producer_domains)):
                    if src_domain is None or src_domain == dst_domain:
                        continue
                    if _belongs_to_safe_cdc_primitive(signal_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                        str(assignment.target),
                        safe_cdc_prefixes,
                    ):
                        continue
                    width = int(getattr(signal_map.get(signal_name), "width", 1))
                    findings.append(
                        _make_signal_crossing_finding(
                            signal_name=signal_name,
                            width=width,
                            src_domain=src_domain,
                            dst_domain=dst_domain,
                            dst_target=assignment.target,
                            primitive_hints=primitive_hints,
                            source_locs=source_locs,
                        )
                    )

        for memory_name in mem_reads:
            written_domains = memory_writers.get(memory_name)
            if not written_domains:
                continue
            for src_domain in sorted(_normalize_domains(written_domains)):
                if src_domain is None or src_domain == dst_domain:
                    continue
                if _belongs_to_safe_cdc_primitive(memory_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                    str(assignment.target),
                    safe_cdc_prefixes,
                ):
                    continue
                width = _memory_read_width(assignment.expr, memory_name)
                findings.append(
                    _make_memory_crossing_finding(
                        memory_name=memory_name,
                        width=width or int(getattr(memory_map.get(memory_name), "width", 1)),
                        src_domain=src_domain,
                        dst_domain=dst_domain,
                        dst_target=assignment.target,
                        primitive_hints=primitive_hints,
                        source_locs=source_locs,
                    )
                )

    for memory_write in module.memory_writes:
        dst_domain = memory_write.clock_domain
        for expr in (memory_write.addr, memory_write.value, memory_write.enable):
            for signal_name in _expr_signal_refs(expr):
                producer_domains = set(state_writers.get(signal_name, ()))
                producer_domains.update(comb_domain_map.get(signal_name, ()))
                if not producer_domains:
                    continue
                for src_domain in sorted(_normalize_domains(producer_domains)):
                    if src_domain is None or src_domain == dst_domain:
                        continue
                    if _belongs_to_safe_cdc_primitive(signal_name, safe_cdc_prefixes) or _belongs_to_safe_cdc_primitive(
                        memory_write.memory,
                        safe_cdc_prefixes,
                    ):
                        continue
                    width = int(getattr(signal_map.get(signal_name), "width", 1))
                    findings.append(
                        _make_signal_crossing_finding(
                            signal_name=signal_name,
                            width=width,
                            src_domain=src_domain,
                            dst_domain=dst_domain,
                            dst_target=memory_write.memory,
                            primitive_hints=primitive_hints,
                            source_locs=source_locs,
                            dst_kind="memory_write",
                        )
                    )
    return _dedupe_findings(findings)


def _analyze_multiwriter_conflicts(
    *,
    state_writers: Mapping[str, Set[Optional[str]]],
    memory_writers: Mapping[str, Set[Optional[str]]],
    state_widths: Mapping[str, int],
    memory_widths: Mapping[str, int],
    safe_cdc_prefixes: Set[str],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for signal_name, domains in state_writers.items():
        if _belongs_to_safe_cdc_primitive(signal_name, safe_cdc_prefixes):
            continue
        normalized = tuple(sorted(domain for domain in domains if domain is not None))
        if len(normalized) <= 1:
            continue
        findings.append(
            CdcFinding(
                category="multi_writer_state",
                severity="error",
                message=(
                    f"State '{signal_name}' is written from multiple clock domains "
                    f"({', '.join(normalized)}). This is a hard CDC hazard."
                ),
                src=CdcEndpoint(
                    signal_name=signal_name,
                    clock_domain=normalized[0],
                    width=state_widths.get(signal_name, 1),
                    kind="state",
                    source_file=source_locs.get(signal_name, (None, None))[0],
                    source_line=source_locs.get(signal_name, (None, None))[1],
                ),
                suggestions=(
                    "Partition ownership so only one domain updates this state.",
                    "Use AsyncFIFO or an explicit request/ack protocol instead of shared multi-domain state.",
                ),
                evidence={"domains": normalized},
            )
        )
    for memory_name, domains in memory_writers.items():
        if _belongs_to_safe_cdc_primitive(memory_name, safe_cdc_prefixes):
            continue
        normalized = tuple(sorted(domain for domain in domains if domain is not None))
        if len(normalized) <= 1:
            continue
        findings.append(
            CdcFinding(
                category="multi_writer_memory",
                severity="error",
                message=(
                    f"Memory '{memory_name}' is written from multiple clock domains "
                    f"({', '.join(normalized)}). Treat this as an async buffer or redesign ownership."
                ),
                src=CdcEndpoint(
                    signal_name=memory_name,
                    clock_domain=normalized[0],
                    width=memory_widths.get(memory_name, 1),
                    kind="memory",
                    source_file=source_locs.get(memory_name, (None, None))[0],
                    source_line=source_locs.get(memory_name, (None, None))[1],
                ),
                suggestions=(
                    "Replace shared cross-domain memory ownership with AsyncFIFO or dual-port CDC-safe storage.",
                    "If the memory is logically single-writer, move all writes into one domain and synchronize requests.",
                ),
                evidence={"domains": normalized},
            )
        )
    return findings


def _analyze_dsl_reset_release(
    module: Any,
    *,
    safe_reset_prefixes: Set[str],
    safe_reset_signals_by_domain: Mapping[str, Set[str]],
    reset_builder_block_indices: Set[int],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for index, (clk, rst, reset_async, reset_active_low, body) in enumerate(getattr(module, "_seq_blocks", ())):
        reset_name, resolved_async, resolved_active_low = _resolve_dsl_reset_signal(
            rst,
            reset_async=bool(reset_async),
            reset_active_low=bool(reset_active_low),
        )
        if not resolved_async or not reset_name:
            continue
        if index in reset_builder_block_indices:
            continue
        domain_name = getattr(clk, "name", str(clk)) if clk is not None else None
        reset_assigns, active_assigns = _dsl_split_reset_guard(
            body,
            reset_name=reset_name,
            reset_active_low=resolved_active_low,
        )
        state_targets = {
            name
            for name in set(reset_assigns) | set(active_assigns) | set(_dsl_direct_assignments(body))
            if name != "<unknown>"
        }
        if state_targets and all(_belongs_to_safe_cdc_primitive(name, safe_reset_prefixes) for name in state_targets):
            continue
        domain_safe_resets = safe_reset_signals_by_domain.get(domain_name or "", set())
        if reset_name in domain_safe_resets or _belongs_to_safe_cdc_primitive(reset_name, safe_reset_prefixes):
            continue
        findings.append(
            _make_reset_release_finding(
                reset_signal=reset_name,
                dst_domain=domain_name,
                reset_active_low=resolved_active_low,
                affected_targets=tuple(sorted(state_targets)),
                source_locs=source_locs,
            )
        )
    return findings


def _analyze_executable_reset_release(
    module: SimModule,
    *,
    safe_reset_signals_by_domain: Mapping[str, Set[str]],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> List[CdcFinding]:
    findings: List[CdcFinding] = []
    for domain in module.clock_domains:
        if not domain.reset_async or not domain.reset_signal:
            continue
        if domain.reset_signal in safe_reset_signals_by_domain.get(domain.name, set()):
            continue
        findings.append(
            _make_reset_release_finding(
                reset_signal=domain.reset_signal,
                dst_domain=domain.name,
                reset_active_low=domain.reset_active_low,
                affected_targets=tuple(
                    sorted(
                        assignment.target
                        for assignment in module.assignments
                        if assignment.phase == "seq" and assignment.clock_domain == domain.name
                    )
                ),
                source_locs=source_locs,
            )
        )
    return findings


def _make_reset_release_finding(
    *,
    reset_signal: str,
    dst_domain: Optional[str],
    reset_active_low: bool,
    affected_targets: Sequence[str],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> CdcFinding:
    file_name, line_no = source_locs.get(reset_signal, (None, None))
    polarity = "active-low" if reset_active_low else "active-high"
    affected = tuple(target for target in affected_targets if target and target != "<unknown>")
    affected_target_sites = tuple(
        (target, source_locs.get(target, (None, None))[0], source_locs.get(target, (None, None))[1])
        for target in affected
        if source_locs.get(target, (None, None))[0] is not None
    )
    affected_text = _summarize_affected_targets(affected)
    target_hint = (
        f" Affected sequential targets: {affected_text}."
        if affected_text
        else ""
    )
    sync_instance = _recommended_reset_release_instance_name(reset_signal=reset_signal, dst_domain=dst_domain)
    sync_reset_name = _recommended_synchronized_reset_name(reset_signal=reset_signal, dst_domain=dst_domain)
    domain_label = dst_domain or "unknown"
    remediation_steps = [
        (
            f"Instantiate `AsyncResetRel` as `{sync_instance}` for destination domain "
            f"`{domain_label}`, with `clk={domain_label}` and `rst_async={reset_signal}`."
        ),
        (
            f"Drive functional sequential logic in `{domain_label}` from `{sync_reset_name}` "
            f"instead of raw `{reset_signal}`."
        ),
    ]
    if affected_text:
        remediation_steps.append(
            f"Reconnect the reset of affected state first: {affected_text}."
        )
    return CdcFinding(
        category="reset_release_crossing",
        severity="warning",
        message=(
            f"Asynchronous reset '{reset_signal}' drives clock domain '{dst_domain or 'unknown'}' "
            f"without a recognized sync-release stage. Reset deassertion can violate recovery/removal timing."
            f"{target_hint}"
        ),
        src=CdcEndpoint(
            signal_name=reset_signal,
            clock_domain=None,
            width=1,
            kind="reset",
            source_file=file_name,
            source_line=line_no,
        ),
        dst=CdcEndpoint(
            signal_name=dst_domain or "<domain>",
            clock_domain=dst_domain,
            width=1,
            kind="clock_domain",
        ),
        suggestions=(
            remediation_steps[0],
            remediation_steps[1],
            (
                "Keep the raw async reset only on the synchronizer itself, and use the synchronized "
                "reset on functional sequential logic."
            ),
            *(tuple(remediation_steps[2:]) or ()),
        ),
        evidence={
            "polarity": polarity,
            "destination_domain": dst_domain or "unknown",
            "affected_targets": affected,
            "affected_target_sites": affected_target_sites,
            "recommended_sync_primitive": "AsyncResetRel",
            "recommended_sync_instance": sync_instance,
            "recommended_synchronized_reset": sync_reset_name,
            "remediation_steps": tuple(remediation_steps),
        },
    )


def _summarize_affected_targets(affected_targets: Sequence[str]) -> str:
    affected = tuple(target for target in affected_targets if target and target != "<unknown>")
    if not affected:
        return ""
    text = ", ".join(affected[:4])
    if len(affected) > 4:
        text = f"{text}, +{len(affected) - 4} more"
    return text


def _recommended_reset_release_instance_name(*, reset_signal: str, dst_domain: Optional[str]) -> str:
    base = dst_domain or reset_signal or "reset"
    return f"u_{_sanitize_identifier_fragment(base)}_reset_rel"


def _recommended_synchronized_reset_name(*, reset_signal: str, dst_domain: Optional[str]) -> str:
    base = dst_domain or reset_signal or "reset"
    return f"{_sanitize_identifier_fragment(base)}_rst_sync"


def _sanitize_identifier_fragment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in str(value))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = "sig"
    if cleaned[0].isdigit():
        cleaned = f"sig_{cleaned}"
    return cleaned.lower()


def _make_signal_crossing_finding(
    *,
    signal_name: str,
    width: int,
    src_domain: Optional[str],
    dst_domain: Optional[str],
    dst_target: str,
    primitive_hints: Mapping[str, Set[str]],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
    dst_kind: str = "state",
) -> CdcFinding:
    severity, category, suggestions = _classify_crossing(
        width=width,
        primitive_hints=primitive_hints,
        signal_name=signal_name,
    )
    file_name, line_no = source_locs.get(signal_name, (None, None))
    message = (
        f"Signal '{signal_name}' written in domain '{src_domain}' is consumed in "
        f"domain '{dst_domain or 'comb/output'}' via '{dst_target}'."
    )
    return CdcFinding(
        category=category,
        severity=severity,
        message=message,
        src=CdcEndpoint(
            signal_name=signal_name,
            clock_domain=src_domain,
            width=width,
            kind="state",
            source_file=file_name,
            source_line=line_no,
        ),
        dst=CdcEndpoint(
            signal_name=str(dst_target),
            clock_domain=dst_domain,
            width=width,
            kind=dst_kind,
            source_file=source_locs.get(str(dst_target), (None, None))[0],
            source_line=source_locs.get(str(dst_target), (None, None))[1],
        ),
        suggestions=suggestions,
        evidence={"crossing_width": width},
    )


def _make_memory_crossing_finding(
    *,
    memory_name: str,
    width: int,
    src_domain: Optional[str],
    dst_domain: Optional[str],
    dst_target: str,
    primitive_hints: Mapping[str, Set[str]],
    source_locs: Mapping[str, Tuple[Optional[str], Optional[int]]],
) -> CdcFinding:
    file_name, line_no = source_locs.get(memory_name, (None, None))
    suggestions = (
        "Prefer AsyncFIFO when data is streamed from one domain into another.",
        "If random access is required, use an explicit CDC-safe dual-port memory protocol and synchronize control/status separately.",
    )
    if "AsyncFIFO" in primitive_hints:
        suggestions = suggestions + (
            "This design already instantiates AsyncFIFO primitives elsewhere; check whether this crossing should use the same pattern.",
        )
    return CdcFinding(
        category="memory_crossing",
        severity="error",
        message=(
            f"Memory '{memory_name}' is written in domain '{src_domain}' and read from "
            f"domain '{dst_domain or 'comb/output'}' via '{dst_target}'."
        ),
        src=CdcEndpoint(
            signal_name=memory_name,
            clock_domain=src_domain,
            width=width,
            kind="memory",
            source_file=file_name,
            source_line=line_no,
        ),
        dst=CdcEndpoint(
            signal_name=str(dst_target),
            clock_domain=dst_domain,
            width=width,
            kind="memory_read",
            source_file=source_locs.get(str(dst_target), (None, None))[0],
            source_line=source_locs.get(str(dst_target), (None, None))[1],
        ),
        suggestions=suggestions,
        evidence={"read_width": width},
    )


def _classify_crossing(
    *,
    width: int,
    primitive_hints: Mapping[str, Set[str]],
    signal_name: str,
) -> Tuple[str, str, Tuple[str, ...]]:
    lower_name = signal_name.lower()
    if width == 1 and ("pulse" in lower_name or "event" in lower_name or "toggle" in lower_name):
        return (
            "warning",
            "pulse_crossing",
            (
                "Use PulseSynchronizer or a toggle-plus-edge-detect scheme for one-shot event crossings.",
                "Do not feed a single-cycle pulse directly into the destination clock domain.",
            ),
        )
    if width == 1:
        return (
            "warning",
            "single_bit_crossing",
            (
                "Use SyncCell or a two-flop synchronizer for stable level crossings.",
                "If this is actually a pulse/event, switch to PulseSynchronizer instead of level sync.",
            ),
        )
    return (
        "error",
        "multi_bit_crossing",
        (
            "Do not independently synchronize multi-bit payload buses.",
            "Use AsyncFIFO, a valid/ready handshake with synchronized control, or encode the transfer as a destination-sampled protocol.",
        ),
    )


def _normalize_domains(domains: Iterable[Optional[str]]) -> Set[Optional[str]]:
    return {domain for domain in domains}


def _belongs_to_safe_cdc_primitive(name: str, safe_cdc_prefixes: Set[str]) -> bool:
    return any(name.startswith(prefix) for prefix in safe_cdc_prefixes)


def _expr_signal_refs(expr: object) -> Set[str]:
    refs: Set[str] = set()
    if isinstance(expr, SignalRef):
        refs.add(expr.name)
        return refs
    if isinstance(expr, MemoryReadExpr):
        refs.update(_expr_signal_refs(expr.addr))
        return refs
    for attr in (
        "operand",
        "lhs",
        "rhs",
        "cond",
        "true_expr",
        "false_expr",
        "when_true",
        "when_false",
        "index",
        "addr",
        "value",
        "enable",
    ):
        child = getattr(expr, attr, None)
        if child is not None:
            refs.update(_expr_signal_refs(child))
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                refs.update(_expr_signal_refs(child))
    return refs


def _expr_memory_reads(expr: object) -> Set[str]:
    reads: Set[str] = set()
    if isinstance(expr, MemoryReadExpr):
        reads.add(expr.memory)
        reads.update(_expr_memory_reads(expr.addr))
        return reads
    for attr in (
        "operand",
        "lhs",
        "rhs",
        "cond",
        "true_expr",
        "false_expr",
        "when_true",
        "when_false",
        "index",
        "addr",
        "value",
        "enable",
    ):
        child = getattr(expr, attr, None)
        if child is not None:
            reads.update(_expr_memory_reads(child))
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                reads.update(_expr_memory_reads(child))
    return reads


def _memory_read_width(expr: object, memory_name: str) -> int:
    if isinstance(expr, MemoryReadExpr) and expr.memory == memory_name:
        return int(getattr(expr, "width", 0))
    for attr in (
        "operand",
        "lhs",
        "rhs",
        "cond",
        "true_expr",
        "false_expr",
        "when_true",
        "when_false",
        "index",
        "addr",
        "value",
        "enable",
    ):
        child = getattr(expr, attr, None)
        if child is not None:
            width = _memory_read_width(child, memory_name)
            if width:
                return width
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                width = _memory_read_width(child, memory_name)
                if width:
                    return width
    return 0


def _dedupe_findings(findings: Sequence[CdcFinding]) -> List[CdcFinding]:
    deduped: List[CdcFinding] = []
    seen: Set[Tuple[str, str, str, str]] = set()
    for finding in findings:
        key = (
            finding.category,
            finding.src.signal_name if finding.src else "",
            finding.dst.signal_name if finding.dst else "",
            finding.dst.clock_domain if finding.dst and finding.dst.clock_domain else "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _format_endpoint(endpoint: CdcEndpoint) -> str:
    parts = [
        f"`{endpoint.signal_name}`",
        f"kind={endpoint.kind}",
        f"domain={endpoint.clock_domain or 'comb/output'}",
        f"width={endpoint.width}",
    ]
    if endpoint.source_file:
        site = f"{Path(endpoint.source_file).name}:{endpoint.source_line}" if endpoint.source_line else Path(endpoint.source_file).name
        parts.append(site)
    return ", ".join(parts)


def _finding_signal_sites(finding: CdcFinding) -> Tuple[str, ...]:
    sites: List[str] = []
    for label, endpoint in (("source", finding.src), ("destination", finding.dst)):
        if endpoint is None or endpoint.source_file is None:
            continue
        path = Path(endpoint.source_file).name
        if endpoint.source_line is not None:
            sites.append(f"{label} `{endpoint.signal_name}` -> {path}:{endpoint.source_line}")
        else:
            sites.append(f"{label} `{endpoint.signal_name}` -> {path}")
    return tuple(sites)


def _finding_affected_target_sites(finding: CdcFinding) -> Tuple[str, ...]:
    evidence = getattr(finding, "evidence", {}) or {}
    raw_entries = evidence.get("affected_target_sites")
    if not raw_entries:
        return ()
    sites: List[str] = []
    for entry in raw_entries:
        if not isinstance(entry, tuple) or len(entry) != 3:
            continue
        signal_name, source_file, source_line = entry
        if not signal_name or not source_file:
            continue
        path = Path(str(source_file)).name
        if source_line is not None:
            sites.append(f"`{signal_name}` -> {path}:{source_line}")
        else:
            sites.append(f"`{signal_name}` -> {path}")
    return tuple(sites)


def _dsl_expr_signal_refs(expr: object) -> Set[str]:
    refs: Set[str] = set()
    if expr is None:
        return refs
    direct_name = getattr(expr, "name", None)
    if direct_name:
        refs.add(str(direct_name))
        return refs
    signal = getattr(expr, "signal", None)
    if getattr(signal, "name", None):
        refs.add(signal.name)
        return refs
    if hasattr(expr, "mem_name") and hasattr(expr, "addr"):
        refs.update(_dsl_expr_signal_refs(getattr(expr, "addr", None)))
        return refs
    if hasattr(expr, "array_name") and hasattr(expr, "index"):
        refs.update(_dsl_expr_signal_refs(getattr(expr, "index", None)))
        return refs
    for attr in ("operand", "lhs", "rhs", "cond", "true_expr", "false_expr", "index", "addr", "value", "offset"):
        child = getattr(expr, attr, None)
        if child is not None:
            refs.update(_dsl_expr_signal_refs(child))
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                refs.update(_dsl_expr_signal_refs(child))
    return refs


def _dsl_expr_memory_reads(expr: object) -> Set[str]:
    reads: Set[str] = set()
    if expr is None:
        return reads
    mem_name = getattr(expr, "mem_name", None)
    array_name = getattr(expr, "array_name", None)
    if mem_name:
        reads.add(mem_name)
        return reads
    if array_name:
        reads.add(array_name)
        return reads
    for attr in ("operand", "lhs", "rhs", "cond", "true_expr", "false_expr", "index", "addr", "value", "offset"):
        child = getattr(expr, attr, None)
        if child is not None:
            reads.update(_dsl_expr_memory_reads(child))
    for attr in ("operands", "args"):
        children = getattr(expr, attr, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                reads.update(_dsl_expr_memory_reads(child))
    return reads
