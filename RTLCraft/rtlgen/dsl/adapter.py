"""Adapters from the DSL surface into rtlgen executable models."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set

from rtlgen.dsl.core import (
    ArrayRead,
    ArrayWrite,
    Assign as DslAssign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    IfNode,
    IndexedAssign,
    MemRead,
    MemWrite,
    Module,
    Mux,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
    Wire,
    WhenNode,
    _clone_signal_shape,
    flatten_module,
    format_diagnostic,
)

try:
    from rtlgen.core import (
        ArrayRead as RtlgenArrayRead,
        ArrayWrite as RtlgenArrayWrite,
        Assign as RtlgenAssign,
        BinOp as RtlgenBinOp,
        BitSelect as RtlgenBitSelect,
        Concat as RtlgenConcat,
        Const as RtlgenConst,
        IfNode as RtlgenIfNode,
        IndexedAssign as RtlgenIndexedAssign,
        MemRead as RtlgenMemRead,
        MemWrite as RtlgenMemWrite,
        Module as RtlgenModule,
        Mux as RtlgenMux,
        PartSelect as RtlgenPartSelect,
        Ref as RtlgenRef,
        Signal as RtlgenSignal,
        Slice as RtlgenSlice,
        SwitchNode as RtlgenSwitchNode,
        UnaryOp as RtlgenUnaryOp,
        WhenNode as RtlgenWhenNode,
        flatten_module as rtlgen_flatten_module,
    )
except ImportError:  # pragma: no cover - rtlgen may be absent in some deployments
    RtlgenArrayRead = ()
    RtlgenArrayWrite = ()
    RtlgenAssign = ()
    RtlgenBinOp = ()
    RtlgenBitSelect = ()
    RtlgenConcat = ()
    RtlgenConst = ()
    RtlgenIfNode = ()
    RtlgenIndexedAssign = ()
    RtlgenMemRead = ()
    RtlgenMemWrite = ()
    RtlgenModule = ()
    RtlgenMux = ()
    RtlgenPartSelect = ()
    RtlgenRef = ()
    RtlgenSignal = ()
    RtlgenSlice = ()
    RtlgenSwitchNode = ()
    RtlgenUnaryOp = ()
    RtlgenWhenNode = ()
    rtlgen_flatten_module = None
from rtlgen.sim import (
    Assignment,
    BinaryExpr,
    ClockDomain,
    CompiledSimulator,
    ConstExpr,
    CppBackendScaffold,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal as SimSignal,
    SignalRef,
    SimModule,
    UnaryExpr,
)


class DslLoweringError(ValueError):
    """Raised when a DSL construct is outside the supported lowering subset."""


_AUTHORING_INTENT_RULES: tuple[str, ...] = (
    "comb_reg_assign",
    "seq_output_assign",
    "hierarchical_write",
    "hierarchical_read",
)


def validate_authoring_intent(module) -> None:
    """Reject DSL authoring patterns that violate the intended public contract."""

    violations = list(module.lint(rules=list(_AUTHORING_INTENT_RULES)))
    violations.extend(_collect_untracked_authoring_object_violations(module))
    violations.extend(_collect_invalid_submodule_port_binding_violations(module))
    if not violations:
        return
    details = "\n".join(f"- {item}" for item in violations)
    raise DslLoweringError(
        "DSL authoring violates the rtlgen intent contract.\n"
        "These patterns are rejected at public lowering / emit boundaries:\n"
        f"{details}"
    )


def _collect_untracked_authoring_object_violations(module) -> List[str]:
    """Reject design-visible objects that were never registered on the module.

    Common user mistake:

    - `tmp = Wire(...)` instead of `self.tmp = Wire(...)`
    - `rf = Array(...)` instead of `self.rf = Array(...)`
    - `mem = Memory(...)` instead of `self.add_memory(...)` / `self.mem = Memory(...)`

    These objects can appear in authored statements, but if they are not
    attached to the module they should fail fast at public boundaries rather
    than being silently repaired later.
    """

    if not hasattr(module, "_inputs"):
        return []

    violations: List[str] = []
    seen: Set[tuple[str, str, str]] = set()

    def record(kind: str, path: str, name: str, message: str) -> None:
        key = (kind, path, name)
        if key in seen:
            return
        seen.add(key)
        violations.append(message)

    def signal_display(signal: Signal) -> str:
        return getattr(signal, "name", "") or "<anonymous>"

    def module_path(parent_path: str, child_name: str) -> str:
        return f"{parent_path}.{child_name}" if parent_path else child_name

    def visit_module(mod, path: str, stack: Set[int]) -> None:
        if id(mod) in stack:
            return
        stack = set(stack)
        stack.add(id(mod))

        known_signal_ids = {
            id(sig)
            for table in (mod._inputs, mod._outputs, mod._wires, mod._regs)
            for sig in table.values()
        }
        known_memory_names = set(mod._memories.keys()) | {
            mem.name for mem in mod._memories.values() if getattr(mem, "name", "")
        }
        known_array_names = set(mod._arrays.keys()) | {
            arr.name for arr in mod._arrays.values() if getattr(arr, "name", "")
        }

        def is_base_declared_signal(sig: Signal) -> bool:
            ref_expr = getattr(sig, "_expr", None)
            return isinstance(ref_expr, Ref) and getattr(ref_expr, "signal", None) is sig

        def maybe_flag_signal(sig: Signal) -> None:
            if id(sig) in known_signal_ids:
                return
            if getattr(sig, "_parent_module", None) is not None:
                return
            if not is_base_declared_signal(sig):
                return

            name = signal_display(sig)
            if name == "<anonymous>":
                guidance = (
                    "Give it a stable name and assign it to self.<name>, or use the "
                    "module helper constructors so lowering and emitted RTL can track it."
                )
            else:
                guidance = (
                    f"Assign it to 'self.{name}' or create it via the module helper "
                    "constructors so lowering and emitted RTL can track it."
                )
            record(
                "signal",
                path,
                name,
                format_diagnostic(
                    "UntrackedSignal",
                    source_location=getattr(sig, "source_location", None),
                    obj=f"{path}.{name}",
                    message=(
                        f"{type(sig).__name__} '{name}' is used in module '{path}' "
                        "but was never registered on self."
                    ),
                    suggested_fix=guidance,
                ),
            )

        def maybe_flag_memory(mem_name: str, source_location: object = None) -> None:
            if mem_name in known_memory_names:
                return
            display = mem_name or "<anonymous>"
            if display == "<anonymous>":
                guidance = "Register it on self or via self.add_memory(...)."
            else:
                guidance = (
                    f"Assign it to 'self.{display}' or register it with self.add_memory(...)."
                )
            record(
                "memory",
                path,
                display,
                format_diagnostic(
                    "UntrackedMemory",
                    source_location=source_location,
                    obj=f"{path}.{display}",
                    message=(
                        f"Memory '{display}' is used in module '{path}' but was never "
                        "registered on self."
                    ),
                    suggested_fix=guidance,
                ),
            )

        def maybe_flag_array(array_name: str, source_location: object = None) -> None:
            if array_name in known_array_names:
                return
            display = array_name or "<anonymous>"
            if display == "<anonymous>":
                guidance = "Register it on self before using it in authored logic."
            else:
                guidance = f"Assign it to 'self.{display}' before using it in authored logic."
            record(
                "array",
                path,
                display,
                format_diagnostic(
                    "UntrackedArray",
                    source_location=source_location,
                    obj=f"{path}.{display}",
                    message=(
                        f"Array '{display}' is used in module '{path}' but was never "
                        "registered on self."
                    ),
                    suggested_fix=guidance,
                ),
            )

        def visit_expr(expr) -> None:
            if expr is None or isinstance(expr, int):
                return
            if isinstance(expr, Signal):
                maybe_flag_signal(expr)
                ref_expr = getattr(expr, "_expr", None)
                if ref_expr is not None and not (
                    isinstance(ref_expr, Ref) and getattr(ref_expr, "signal", None) is expr
                ):
                    visit_expr(ref_expr)
                return
            if isinstance(expr, Ref):
                maybe_flag_signal(expr.signal)
                return
            if isinstance(expr, BinOp):
                visit_expr(expr.lhs)
                visit_expr(expr.rhs)
                return
            if isinstance(expr, UnaryOp):
                visit_expr(expr.operand)
                return
            if isinstance(expr, Slice):
                visit_expr(expr.operand)
                if not isinstance(expr.hi, int):
                    visit_expr(expr.hi)
                if not isinstance(expr.lo, int):
                    visit_expr(expr.lo)
                return
            if isinstance(expr, PartSelect):
                visit_expr(expr.operand)
                visit_expr(expr.offset)
                return
            if isinstance(expr, BitSelect):
                visit_expr(expr.operand)
                visit_expr(expr.index)
                return
            if isinstance(expr, Concat):
                for operand in expr.operands:
                    visit_expr(operand)
                return
            if isinstance(expr, Mux):
                visit_expr(expr.cond)
                visit_expr(expr.true_expr)
                visit_expr(expr.false_expr)
                return
            if isinstance(expr, MemRead):
                maybe_flag_memory(expr.mem_name, getattr(expr, "source_location", None))
                visit_expr(expr.addr)
                return
            if isinstance(expr, ArrayRead):
                maybe_flag_array(expr.array_name, getattr(expr, "source_location", None))
                visit_expr(expr.index)
                return

        explicit_children: List[tuple[str, object]] = []

        def visit_stmt(stmt) -> None:
            if isinstance(stmt, DslAssign):
                visit_expr(stmt.target)
                visit_expr(stmt.value)
                return
            if isinstance(stmt, IndexedAssign):
                maybe_flag_signal(stmt.target_signal)
                visit_expr(stmt.index)
                visit_expr(stmt.value)
                return
            if isinstance(stmt, ArrayWrite):
                maybe_flag_array(stmt.array_name, getattr(stmt, "source_location", None))
                visit_expr(stmt.index)
                visit_expr(stmt.value)
                return
            if isinstance(stmt, MemWrite):
                maybe_flag_memory(stmt.mem_name, getattr(stmt, "source_location", None))
                visit_expr(stmt.addr)
                visit_expr(stmt.value)
                if stmt.byte_enable is not None:
                    visit_expr(stmt.byte_enable)
                return
            if isinstance(stmt, IfNode):
                visit_expr(stmt.cond)
                for body_stmt in stmt.then_body:
                    visit_stmt(body_stmt)
                for _, body in stmt.elif_bodies:
                    for body_stmt in body:
                        visit_stmt(body_stmt)
                for body_stmt in stmt.else_body:
                    visit_stmt(body_stmt)
                return
            if isinstance(stmt, SwitchNode):
                visit_expr(stmt.expr)
                for case_value, body in stmt.cases:
                    visit_expr(case_value)
                    for body_stmt in body:
                        visit_stmt(body_stmt)
                for body_stmt in stmt.default_body:
                    visit_stmt(body_stmt)
                return
            if isinstance(stmt, WhenNode):
                for cond, body in stmt.branches:
                    if cond is not None:
                        visit_expr(cond)
                    for body_stmt in body:
                        visit_stmt(body_stmt)
                return
            if stmt.__class__.__name__ == "SubmoduleInst":
                explicit_children.append((stmt.name, stmt.module))
                for expr in getattr(stmt, "port_map", {}).values():
                    visit_expr(expr)
                for param in getattr(stmt, "params", {}).values():
                    if isinstance(param, (Signal, Expr)):
                        visit_expr(param)

        for stmt in mod._top_level:
            visit_stmt(stmt)
        for body in mod._comb_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for body in mod._latch_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for body in mod._init_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for _, _, _, _, body in mod._seq_blocks:
            for stmt in body:
                visit_stmt(stmt)

        for child_name, child_module in mod._submodules:
            visit_module(child_module, module_path(path, child_name), stack)
        for child_name, child_module in explicit_children:
            visit_module(child_module, module_path(path, child_name), stack)

    visit_module(module, getattr(module, "name", module.__class__.__name__), set())
    return violations


def _collect_invalid_submodule_port_binding_violations(module) -> List[str]:
    """Reject explicit submodule port_map keys that do not exist on the child.

    Historically some downstream paths silently ignored unknown port names
    during flattening, which made simple typos behave like missing wiring.
    That is too error-prone for the public DSL contract, so we fail fast at
    authoring boundaries instead.
    """

    if not hasattr(module, "_top_level"):
        return []

    violations: List[str] = []
    seen: Set[tuple[str, str, str]] = set()

    def module_path(parent_path: str, child_name: str) -> str:
        return f"{parent_path}.{child_name}" if parent_path else child_name

    def record(
        path: str,
        inst_name: str,
        port_name: str,
        module_name: str,
        valid_ports: Sequence[str],
        *,
        source_location: object = None,
    ) -> None:
        key = (path, inst_name, port_name)
        if key in seen:
            return
        seen.add(key)
        valid_display = ", ".join(valid_ports) if valid_ports else "<no ports>"
        violations.append(
            format_diagnostic(
                "UnknownSubmodulePort",
                source_location=source_location,
                obj=f"{path}.{port_name}",
                message=(
                    f"Instance '{path}' maps unknown port '{port_name}' on submodule "
                    f"'{module_name}'. Valid ports: {valid_display}."
                ),
                suggested_fix=(
                    "Fix the port_map key or rename the child port to match the "
                    "authored connection."
                ),
            )
        )

    def visit_module(mod, path: str, stack: Set[int]) -> None:
        if id(mod) in stack:
            return
        stack = set(stack)
        stack.add(id(mod))

        explicit_children = []

        def visit_stmt(stmt) -> None:
            if stmt.__class__.__name__ == "SubmoduleInst":
                explicit_children.append((stmt.name, stmt.module))
                valid_ports = tuple(stmt.module._inputs.keys()) + tuple(stmt.module._outputs.keys())
                valid_set = set(valid_ports)
                for port_name in getattr(stmt, "port_map", {}).keys():
                    if port_name not in valid_set:
                        record(
                            module_path(path, stmt.name),
                            stmt.name,
                            port_name,
                            getattr(stmt.module, "name", stmt.module.__class__.__name__),
                            valid_ports,
                            source_location=getattr(stmt, "source_location", None),
                        )
            for body_name in ("then_body", "else_body", "default_body"):
                body = getattr(stmt, body_name, None)
                if body:
                    for nested in body:
                        visit_stmt(nested)
            for _, body in getattr(stmt, "elif_bodies", []):
                for nested in body:
                    visit_stmt(nested)
            for _, body in getattr(stmt, "cases", []):
                for nested in body:
                    visit_stmt(nested)
            for _, body in getattr(stmt, "branches", []):
                for nested in body:
                    visit_stmt(nested)

        for stmt in mod._top_level:
            visit_stmt(stmt)
        for body in mod._comb_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for body in mod._latch_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for body in mod._init_blocks:
            for stmt in body:
                visit_stmt(stmt)
        for _, _, _, _, body in mod._seq_blocks:
            for stmt in body:
                visit_stmt(stmt)

        for child_name, child_module in mod._submodules:
            visit_module(child_module, module_path(path, child_name), stack)
        for child_name, child_module in explicit_children:
            visit_module(child_module, module_path(path, child_name), stack)

    visit_module(module, getattr(module, "name", module.__class__.__name__), set())
    return violations


@dataclass(frozen=True)
class DslLoweringReport:
    """Summary of a DSL lowering step."""

    source_module: str
    flattened_module: str
    signal_count: int
    assignment_count: int
    outputs_post_state: bool


@dataclass(frozen=True)
class LoweredDslModule:
    """Pair the lowered executable module with a small lowering report."""

    module: SimModule
    report: DslLoweringReport


def lower_dsl_module_to_sim(
    module,
    *,
    flatten: bool = True,
    outputs_post_state: bool = True,
) -> LoweredDslModule:
    """Lower a DSL ``Module`` into the compiled-simulator executable model.

    The current bridge intentionally supports a focused subset:

    - flattened modules only
    - no behavioral/black-box callbacks
    - expressions expressible as ``Const``/``Ref``/``UnaryOp``/``BinOp``/``Mux`` and
      constant ``Slice``/single-bit ``BitSelect`` plus storage reads
    - sequential logic represented as explicit condition trees inside ``seq`` bodies
    - comb-read / seq-write ``Memory`` and ``Array`` storage
    """

    validate_authoring_intent(module)
    module = _normalize_cross_module_assignments(module)
    flatten_fn = _select_flatten_module(module)
    lowered_source = flatten_fn(module) if flatten else module
    lowered_source = copy.deepcopy(lowered_source)
    _reject_unsupported_module_features(lowered_source)
    clock_domains = _collect_clock_domains(lowered_source)
    _register_implicit_signals(lowered_source)
    state_inits, memory_inits = _collect_initial_values(module)
    if lowered_source is not module:
        lowered_state_inits, lowered_memory_inits = _collect_initial_values(lowered_source)
        for name, value in lowered_state_inits.items():
            state_inits.setdefault(name, value)
        for name, values in lowered_memory_inits.items():
            memory_inits.setdefault(name, values)

    signals: List[SimSignal] = []
    signal_map: Dict[str, SimSignal] = {}

    def add_signal(source_signal, kind: str) -> None:
        sim_signal = SimSignal(
            name=source_signal.name,
            width=source_signal.width,
            kind=kind,
            signed=getattr(source_signal, "signed", False),
            init=(
                state_inits.get(source_signal.name, source_signal.init_value or 0)
                if kind == "state"
                else (source_signal.init_value or 0)
            ),
        )
        signals.append(sim_signal)
        signal_map[source_signal.name] = sim_signal

    for source_signal in lowered_source._inputs.values():
        add_signal(source_signal, "input")
    for source_signal in lowered_source._outputs.values():
        add_signal(source_signal, "output")
    for source_signal in lowered_source._wires.values():
        add_signal(source_signal, "wire")
    for source_signal in lowered_source._regs.values():
        add_signal(source_signal, "state")

    memories: List[Memory] = []
    memory_names: Dict[str, Memory] = {}
    for source_memory in lowered_source._memories.values():
        _validate_supported_storage_contract(source_memory)
        init = memory_inits.get(source_memory.name, ())
        sim_memory = Memory(
            name=source_memory.name,
            width=source_memory.width,
            depth=source_memory.depth,
            init=init,
            read_during_write=getattr(source_memory, "read_during_write", "write_first"),
            read_ports=int(getattr(source_memory, "read_ports", 1)),
            write_ports=int(getattr(source_memory, "write_ports", 1)),
            read_style=getattr(source_memory, "read_style", "async"),
            read_latency=int(getattr(source_memory, "read_latency", 0)),
            byte_enable_granularity=getattr(source_memory, "byte_enable_granularity", None),
        )
        memories.append(sim_memory)
        memory_names[source_memory.name] = sim_memory
    for source_array in lowered_source._arrays.values():
        sim_memory = Memory(
            name=source_array.name,
            width=source_array.width,
            depth=source_array.depth,
            init=memory_inits.get(source_array.name, ()),
            read_during_write="write_first",
            read_ports=1,
            write_ports=1,
            read_style="async",
            read_latency=0,
            byte_enable_granularity=None,
        )
        memories.append(sim_memory)
        memory_names[source_array.name] = sim_memory

    assignments: List[Assignment] = []
    memory_writes: List[MemoryWrite] = []
    if lowered_source._top_level:
        env = _LoweringEnv(signal_map, memory_names)
        _lower_stmt_list(lowered_source._top_level, phase="comb", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())
    for body in lowered_source._comb_blocks:
        env = _LoweringEnv(signal_map, memory_names)
        _lower_stmt_list(body, phase="comb", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())
    for body in lowered_source._latch_blocks:
        env = _LoweringEnv(signal_map, memory_names)
        _lower_stmt_list(body, phase="latch", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())

    for index, seq_item in enumerate(lowered_source._seq_blocks):
        clk, rst, reset_async, reset_active_low, body = seq_item
        if clk is None:
            raise DslLoweringError("sequential block is missing clock")
        clock_signal_name = getattr(clk, "name", str(clk))
        clock_domain_name = None
        if clock_domains:
            for domain in clock_domains:
                if (domain.clock_signal or domain.name) == clock_signal_name:
                    clock_domain_name = domain.name
                    break
        if clock_domain_name is None:
            clock_domain_name = clock_signal_name if clock_domains else None
        env = _LoweringEnv(signal_map, memory_names, clock_domain=clock_domain_name)
        _lower_stmt_list(body, phase="seq", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())

    signals, memories, assignments = _lower_sync_read_memories_into_executable_subset(
        lowered_source,
        signals,
        signal_map,
        memories,
        assignments,
        memory_writes,
        clock_domains,
    )
    assignments = _topologically_order_comb_assignments(assignments, signal_map)

    sim_module = SimModule(
        name=lowered_source.name,
        signals=tuple(signals),
        assignments=tuple(assignments),
        outputs=tuple(lowered_source._outputs.keys()),
        memories=tuple(memories),
        memory_writes=tuple(memory_writes),
        clock_domains=clock_domains,
        reset_signal=None,
        outputs_post_state=outputs_post_state,
    )
    report = DslLoweringReport(
        source_module=module.name,
        flattened_module=lowered_source.name,
        signal_count=len(signals),
        assignment_count=len(assignments) + len(memory_writes),
        outputs_post_state=outputs_post_state,
    )
    return LoweredDslModule(module=sim_module, report=report)


def build_compiled_simulator_from_dsl(
    module,
    *,
    flatten: bool = True,
    outputs_post_state: bool = True,
    builder: Optional[CppBackendScaffold] = None,
    build_dir: Optional[Path | str] = None,
) -> CompiledSimulator:
    """Lower a DSL module and build the compiled simulator runtime."""

    lowered = lower_dsl_module_to_sim(
        module,
        flatten=flatten,
        outputs_post_state=outputs_post_state,
    )
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    return runtime_builder.build(lowered.module, build_dir=build_dir)


def _validate_supported_storage_contract(source_memory) -> None:
    read_ports = int(getattr(source_memory, "read_ports", 1))
    write_ports = int(getattr(source_memory, "write_ports", 1))
    read_style = getattr(source_memory, "read_style", "async")
    read_latency = int(getattr(source_memory, "read_latency", 0))
    byte_enable_granularity = getattr(source_memory, "byte_enable_granularity", None)

    problems: List[str] = []
    if read_ports != 1:
        problems.append(f"read_ports={read_ports}")
    if write_ports != 1:
        problems.append(f"write_ports={write_ports}")
    if read_style not in {"async", "sync"}:
        problems.append(f"read_style={read_style!r}")
    if read_style == "async" and read_latency != 0:
        problems.append(f"read_latency={read_latency}")
    if read_style == "sync" and read_latency != 1:
        problems.append(f"read_latency={read_latency}")
    if not problems:
        return
    details = ", ".join(problems)
    raise DslLoweringError(
        format_diagnostic(
            "UnsupportedStorageContract",
            source_location=getattr(source_memory, "source_location", None),
            obj=f"memory.{getattr(source_memory, 'name', '<memory>')}",
            message=(
                f"memory '{getattr(source_memory, 'name', '<memory>')}' uses unsupported "
                f"storage contract for executable lowering ({details}); current executable "
                "subset requires read_ports=1, write_ports=1, plus either "
                "read_style='async'/read_latency=0 or read_style='sync'/read_latency=1."
            ),
            suggested_fix=(
                "Use executable lowering/cosim for this subset, or narrow the authored "
                "storage contract."
            ),
        )
    )


def _collect_initial_values(module) -> tuple[Dict[str, int], Dict[str, tuple[int, ...]]]:
    signal_defs = dict(module._regs)
    signal_values = {
        name: int(signal.init_value or 0) & _mask_for_width(signal.width)
        for name, signal in signal_defs.items()
    }
    memory_defs = {}
    memory_values: Dict[str, List[int]] = {}
    for source_memory in module._memories.values():
        memory_defs[source_memory.name] = source_memory
        init = [0] * source_memory.depth
        if getattr(source_memory, "init_file", None):
            init = _load_memory_init_file(
                source_memory.init_file,
                width=source_memory.width,
                depth=source_memory.depth,
            )
        elif getattr(source_memory, "init_data", None):
            for idx, value in enumerate(source_memory.init_data[: source_memory.depth]):
                init[idx] = int(value) & _mask_for_width(source_memory.width)
        memory_values[source_memory.name] = init
    for source_array in module._arrays.values():
        memory_defs[source_array.name] = source_array
        memory_values[source_array.name] = [0] * source_array.depth
    for body in module._init_blocks:
        _eval_initial_stmt_list(body, signal_defs, signal_values, memory_defs, memory_values)
    return signal_values, {name: tuple(values) for name, values in memory_values.items()}


def _load_memory_init_file(path: str, *, width: int, depth: int) -> List[int]:
    file_path = Path(path)
    if not file_path.is_file():
        raise DslLoweringError(f"memory init_file '{path}' does not exist")

    mask = _mask_for_width(width)
    values: List[int] = []
    for raw_line in file_path.read_text().splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        for token in line.split():
            token = token.replace("_", "")
            if not token:
                continue
            try:
                value = int(token, 16)
            except ValueError as exc:
                raise DslLoweringError(
                    f"memory init_file '{path}' contains non-hex token '{token}'"
                ) from exc
            values.append(value & mask)
            if len(values) >= depth:
                return values[:depth]
    if len(values) < depth:
        values.extend([0] * (depth - len(values)))
    return values


def _collect_clock_domains(module) -> tuple[ClockDomain, ...]:
    declared_specs_by_clock: Dict[str, tuple[Optional[str], bool, bool, str]] = {}
    for domain_spec in getattr(module, "_clock_domain_specs", {}).values():
        clk_name = getattr(domain_spec.clock, "name", str(domain_spec.clock))
        rst_signal = getattr(domain_spec, "reset_signal", None)
        rst_name = _normalize_optional_signal_name(
            getattr(rst_signal, "name", str(rst_signal)) if rst_signal is not None else None
        )
        spec = (
            rst_name,
            bool(getattr(domain_spec, "reset_async", False)),
            bool(getattr(domain_spec, "reset_active_low", False)),
            getattr(domain_spec, "name", clk_name),
        )
        previous = declared_specs_by_clock.get(clk_name)
        if previous is not None and previous != spec:
            raise DslLoweringError(
                "declared clock domains cannot assign conflicting reset semantics to "
                f"clock '{clk_name}': previous={previous[:3]}, current={spec[:3]}"
            )
        declared_specs_by_clock[clk_name] = spec

    clock_specs: Dict[str, tuple[Optional[str], bool, bool]] = {}
    ordered_clock_names: List[str] = []
    for clk, rst, reset_async, reset_active_low, _body in getattr(module, "_seq_blocks", ()):
        if clk is None:
            continue
        clk_name = getattr(clk, "name", str(clk))
        rst_name = _normalize_optional_signal_name(getattr(rst, "name", str(rst)) if rst is not None else None)
        spec = (rst_name, bool(reset_async), bool(reset_active_low))
        declared = declared_specs_by_clock.get(clk_name)
        if declared is not None and spec != declared[:3]:
            raise DslLoweringError(
                "lower_dsl_module_to_sim found a sequential block whose reset semantics "
                f"disagree with declared clock domain '{declared[3]}' for clock '{clk_name}': "
                f"declared={declared[:3]}, observed={spec}"
            )
        previous = clock_specs.get(clk_name)
        if previous is None:
            ordered_clock_names.append(clk_name)
            clock_specs[clk_name] = spec
            continue
        if previous != spec:
            raise DslLoweringError(
                "lower_dsl_module_to_sim cannot merge sequential blocks that share "
                f"clock '{clk_name}' but disagree on reset semantics: "
                f"previous={previous}, current={spec}"
            )
    if not ordered_clock_names:
        return ()
    return tuple(
        ClockDomain(
            name=declared_specs_by_clock.get(clock_name, (None, False, False, clock_name))[3],
            clock_signal=clock_name,
            reset_signal=clock_specs[clock_name][0],
            reset_async=clock_specs[clock_name][1],
            reset_active_low=clock_specs[clock_name][2],
            aliases=(clock_name,),
        )
        for clock_name in ordered_clock_names
    )


def _normalize_optional_signal_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    normalized = str(name).strip()
    return normalized or None


def _eval_initial_stmt_list(
    stmts: Iterable[object],
    signal_defs: Mapping[str, object],
    signal_values: MutableMapping[str, int],
    memory_defs: Mapping[str, object],
    memory_values: MutableMapping[str, List[int]],
) -> None:
    for stmt in stmts:
        if isinstance(stmt, _ASSIGN_TYPES):
            _eval_initial_assign(stmt.target, stmt.value, signal_defs, signal_values, memory_defs, memory_values)
            continue
        if isinstance(stmt, _INDEXED_ASSIGN_TYPES):
            target_expr = BitSelect(Ref(stmt.target_signal), stmt.index)
            _eval_initial_assign(target_expr, stmt.value, signal_defs, signal_values, memory_defs, memory_values)
            continue
        if isinstance(stmt, _MEM_WRITE_TYPES):
            _eval_initial_memory_write(
                stmt.mem_name,
                stmt.addr,
                stmt.value,
                signal_defs,
                signal_values,
                memory_defs,
                memory_values,
            )
            continue
        if isinstance(stmt, _ARRAY_WRITE_TYPES):
            _eval_initial_memory_write(
                stmt.array_name,
                stmt.index,
                stmt.value,
                signal_defs,
                signal_values,
                memory_defs,
                memory_values,
            )
            continue
        if isinstance(stmt, _IF_TYPES):
            if _eval_initial_expr(stmt.cond, signal_defs, signal_values, memory_defs, memory_values):
                _eval_initial_stmt_list(stmt.then_body, signal_defs, signal_values, memory_defs, memory_values)
                continue
            branch_taken = False
            for elif_cond, elif_body in stmt.elif_bodies:
                if _eval_initial_expr(elif_cond, signal_defs, signal_values, memory_defs, memory_values):
                    _eval_initial_stmt_list(elif_body, signal_defs, signal_values, memory_defs, memory_values)
                    branch_taken = True
                    break
            if not branch_taken:
                _eval_initial_stmt_list(stmt.else_body, signal_defs, signal_values, memory_defs, memory_values)
            continue
        if isinstance(stmt, _SWITCH_TYPES):
            selector = _eval_initial_expr(stmt.expr, signal_defs, signal_values, memory_defs, memory_values)
            matched = False
            for case_value, case_body in stmt.cases:
                if selector == _eval_initial_expr(case_value, signal_defs, signal_values, memory_defs, memory_values):
                    _eval_initial_stmt_list(case_body, signal_defs, signal_values, memory_defs, memory_values)
                    matched = True
                    break
            if not matched:
                _eval_initial_stmt_list(stmt.default_body, signal_defs, signal_values, memory_defs, memory_values)
            continue
        if isinstance(stmt, _WHEN_TYPES):
            for cond, body in stmt.branches:
                if cond is None or _eval_initial_expr(cond, signal_defs, signal_values, memory_defs, memory_values):
                    _eval_initial_stmt_list(body, signal_defs, signal_values, memory_defs, memory_values)
                    break
            continue
        if type(stmt).__name__ == "Comment":
            continue
        raise DslLoweringError(f"unsupported initial-block statement type '{type(stmt).__name__}'")


def _eval_initial_assign(
    target,
    value,
    signal_defs: Mapping[str, object],
    signal_values: MutableMapping[str, int],
    memory_defs: Mapping[str, object],
    memory_values: MutableMapping[str, List[int]],
) -> None:
    if isinstance(target, _SIGNAL_TYPES):
        signal = signal_defs.get(target.name)
        if signal is None:
            raise DslLoweringError(
                f"initial block assignment only supports register targets, got '{target.name}'"
            )
        signal_values[target.name] = _eval_initial_expr(
            value, signal_defs, signal_values, memory_defs, memory_values
        ) & _mask_for_width(signal.width)
        return
    if isinstance(target, _REF_TYPES):
        _eval_initial_assign(target.signal, value, signal_defs, signal_values, memory_defs, memory_values)
        return
    if isinstance(target, _BITSELECT_TYPES):
        _eval_initial_bit_or_range_assign(target, value, signal_defs, signal_values, memory_defs, memory_values)
        return
    if isinstance(target, _SLICE_TYPES):
        _eval_initial_bit_or_range_assign(target, value, signal_defs, signal_values, memory_defs, memory_values)
        return
    if isinstance(target, _PARTSELECT_TYPES):
        _eval_initial_bit_or_range_assign(target, value, signal_defs, signal_values, memory_defs, memory_values)
        return
    raise DslLoweringError(
        f"unsupported initial-block assignment target '{type(target).__name__}'"
    )


def _eval_initial_bit_or_range_assign(
    target,
    value,
    signal_defs: Mapping[str, object],
    signal_values: MutableMapping[str, int],
    memory_defs: Mapping[str, object],
    memory_values: MutableMapping[str, List[int]],
) -> None:
    operand = getattr(target, "operand", None)
    if not isinstance(operand, _REF_TYPES):
        raise DslLoweringError("initial block bit-range assignment must target a register")
    signal = signal_defs.get(operand.signal.name)
    if signal is None:
        raise DslLoweringError(
            f"initial block bit-range assignment only supports register targets, got '{operand.signal.name}'"
        )
    base_value = signal_values.get(operand.signal.name, 0) & _mask_for_width(signal.width)
    replacement_value = _eval_initial_expr(value, signal_defs, signal_values, memory_defs, memory_values)
    if isinstance(target, _BITSELECT_TYPES):
        index = _eval_initial_expr(target.index, signal_defs, signal_values, memory_defs, memory_values)
        signal_values[operand.signal.name] = _replace_python_bit_range(
            base_value,
            int(index),
            1,
            replacement_value,
            signal.width,
        )
        return
    if isinstance(target, _PARTSELECT_TYPES):
        offset = _eval_initial_expr(target.offset, signal_defs, signal_values, memory_defs, memory_values)
        signal_values[operand.signal.name] = _replace_python_bit_range(
            base_value,
            int(offset),
            target.width,
            replacement_value,
            signal.width,
        )
        return
    lo = target.lo
    hi = target.hi
    if not isinstance(lo, int) or not isinstance(hi, int):
        raise DslLoweringError("unsupported non-static slice target in initial block")
    signal_values[operand.signal.name] = _replace_python_bit_range(
        base_value,
        lo,
        hi - lo + 1,
        replacement_value,
        signal.width,
    )


def _eval_initial_memory_write(
    memory_name: str,
    addr_expr,
    value_expr,
    signal_defs: Mapping[str, object],
    signal_values: MutableMapping[str, int],
    memory_defs: Mapping[str, object],
    memory_values: MutableMapping[str, List[int]],
) -> None:
    memory = memory_defs.get(memory_name)
    if memory is None:
        raise DslLoweringError(f"initial block writes unknown memory '{memory_name}'")
    addr = int(_eval_initial_expr(addr_expr, signal_defs, signal_values, memory_defs, memory_values))
    if addr < 0 or addr >= memory.depth:
        raise DslLoweringError(
            f"initial block write to '{memory_name}' is outside depth {memory.depth}: addr={addr}"
        )
    value = _eval_initial_expr(value_expr, signal_defs, signal_values, memory_defs, memory_values)
    memory_values[memory_name][addr] = int(value) & _mask_for_width(memory.width)


def _eval_initial_expr(
    expr,
    signal_defs: Mapping[str, object],
    signal_values: Mapping[str, int],
    memory_defs: Mapping[str, object],
    memory_values: Mapping[str, List[int]],
) -> int:
    if isinstance(expr, int):
        return int(expr)
    if isinstance(expr, _SIGNAL_TYPES):
        if expr.name not in signal_values:
            raise DslLoweringError(
                f"initial block expression references non-register signal '{expr.name}'"
            )
        return int(signal_values[expr.name]) & _mask_for_width(expr.width)
    if isinstance(expr, _CONST_TYPES):
        return int(expr.value) & _mask_for_width(expr.width)
    if isinstance(expr, _REF_TYPES):
        signal = expr.signal
        if signal.name not in signal_values:
            raise DslLoweringError(
                f"initial block expression references non-register signal '{signal.name}'"
            )
        return int(signal_values[signal.name]) & _mask_for_width(signal.width)
    if isinstance(expr, _MEM_READ_TYPES):
        memory = memory_defs[expr.mem_name]
        addr = int(_eval_initial_expr(expr.addr, signal_defs, signal_values, memory_defs, memory_values))
        return int(memory_values[expr.mem_name][addr % memory.depth]) & _mask_for_width(memory.width)
    if isinstance(expr, _ARRAY_READ_TYPES):
        memory = memory_defs[expr.array_name]
        addr = int(_eval_initial_expr(expr.index, signal_defs, signal_values, memory_defs, memory_values))
        return int(memory_values[expr.array_name][addr % memory.depth]) & _mask_for_width(memory.width)
    if isinstance(expr, _UNARY_TYPES):
        operand = _eval_initial_expr(expr.operand, signal_defs, signal_values, memory_defs, memory_values)
        width = expr.width
        if expr.op == "~":
            return (~operand) & _mask_for_width(width)
        if expr.op == "-":
            return (-operand) & _mask_for_width(width)
        if expr.op == "!":
            return int(not operand)
        if expr.op == "$signed":
            return _to_signed(operand, width)
        if expr.op == "$unsigned":
            return operand & _mask_for_width(width)
        raise DslLoweringError(f"unsupported unary op '{expr.op}' in initial block")
    if isinstance(expr, _BINOP_TYPES):
        lhs = _eval_initial_expr(expr.lhs, signal_defs, signal_values, memory_defs, memory_values)
        rhs = _eval_initial_expr(expr.rhs, signal_defs, signal_values, memory_defs, memory_values)
        width = expr.width
        if expr.op == "+":
            return (lhs + rhs) & _mask_for_width(width)
        if expr.op == "-":
            return (lhs - rhs) & _mask_for_width(width)
        if expr.op == "*":
            return (lhs * rhs) & _mask_for_width(width)
        if expr.op == "&":
            return (lhs & rhs) & _mask_for_width(width)
        if expr.op == "|":
            return (lhs | rhs) & _mask_for_width(width)
        if expr.op == "^":
            return (lhs ^ rhs) & _mask_for_width(width)
        if expr.op == "<<":
            return (lhs << rhs) & _mask_for_width(width)
        if expr.op == ">>":
            return (lhs >> rhs) & _mask_for_width(width)
        if expr.op == ">>>":
            return (_to_signed(lhs, _expr_eval_width(expr.lhs, signal_defs, memory_defs)) >> rhs) & _mask_for_width(width)
        if expr.op == "==":
            return int(lhs == rhs)
        if expr.op == "!=":
            return int(lhs != rhs)
        if expr.op == "<":
            return int(lhs < rhs)
        if expr.op == "<=":
            return int(lhs <= rhs)
        if expr.op == ">":
            return int(lhs > rhs)
        if expr.op == ">=":
            return int(lhs >= rhs)
        raise DslLoweringError(f"unsupported binary op '{expr.op}' in initial block")
    if isinstance(expr, _MUX_TYPES):
        cond = _eval_initial_expr(expr.cond, signal_defs, signal_values, memory_defs, memory_values)
        branch = expr.true_expr if cond else expr.false_expr
        return _eval_initial_expr(branch, signal_defs, signal_values, memory_defs, memory_values)
    if isinstance(expr, _SLICE_TYPES):
        operand = _eval_initial_expr(expr.operand, signal_defs, signal_values, memory_defs, memory_values)
        if isinstance(expr.lo, int) and isinstance(expr.hi, int):
            return (operand >> expr.lo) & _mask_for_width(expr.hi - expr.lo + 1)
        lo = _eval_initial_expr(expr.lo, signal_defs, signal_values, memory_defs, memory_values)
        return (operand >> int(lo)) & _mask_for_width(expr.width)
    if isinstance(expr, _PARTSELECT_TYPES):
        operand = _eval_initial_expr(expr.operand, signal_defs, signal_values, memory_defs, memory_values)
        offset = _eval_initial_expr(expr.offset, signal_defs, signal_values, memory_defs, memory_values)
        return (operand >> int(offset)) & _mask_for_width(expr.width)
    if isinstance(expr, _BITSELECT_TYPES):
        operand = _eval_initial_expr(expr.operand, signal_defs, signal_values, memory_defs, memory_values)
        index = _eval_initial_expr(expr.index, signal_defs, signal_values, memory_defs, memory_values)
        return (operand >> int(index)) & 0x1
    if isinstance(expr, _CONCAT_TYPES):
        value = 0
        for operand in expr.operands:
            part = _eval_initial_expr(operand, signal_defs, signal_values, memory_defs, memory_values)
            value = (value << operand.width) | (part & _mask_for_width(operand.width))
        return value & _mask_for_width(expr.width)
    raise DslLoweringError(f"unsupported initial-block expression type '{type(expr).__name__}'")


def _expr_eval_width(expr, signal_defs: Mapping[str, object], memory_defs: Mapping[str, object]) -> int:
    if isinstance(expr, int):
        return max(expr.bit_length(), 1)
    if isinstance(expr, _SIGNAL_TYPES):
        return expr.width
    if isinstance(expr, _CONST_TYPES):
        return expr.width
    if isinstance(expr, _REF_TYPES):
        return expr.signal.width
    if isinstance(expr, _MEM_READ_TYPES):
        return memory_defs[expr.mem_name].width
    if isinstance(expr, _ARRAY_READ_TYPES):
        return memory_defs[expr.array_name].width
    if hasattr(expr, "width"):
        return int(expr.width)
    raise DslLoweringError(f"cannot derive width for initial-block expression '{type(expr).__name__}'")


def _to_signed(value: int, width: int) -> int:
    mask = _mask_for_width(width)
    masked = int(value) & mask
    sign_bit = 1 << (width - 1)
    return masked - (1 << width) if masked & sign_bit else masked


def _replace_python_bit_range(base_value: int, lo: int, width: int, replacement_value: int, base_width: int) -> int:
    if width < 1:
        raise DslLoweringError("bit range width must be positive")
    if lo < 0 or lo + width > base_width:
        raise DslLoweringError("bit range assignment is outside the target signal width")
    range_mask = ((1 << width) - 1) << lo
    keep_mask = _mask_for_width(base_width) ^ range_mask
    return (
        (base_value & keep_mask)
        | ((int(replacement_value) & _mask_for_width(width)) << lo)
    ) & _mask_for_width(base_width)


def _mask_for_width(width: int) -> int:
    return (1 << width) - 1


def _pick_preferred_assignment_source(
    then_value,
    then_source: tuple[Optional[str], Optional[int]],
    else_value,
    else_source: tuple[Optional[str], Optional[int]],
    fallback_source: tuple[Optional[str], Optional[int]],
) -> tuple[Optional[str], Optional[int]]:
    then_score = _compiled_expr_complexity(then_value)
    else_score = _compiled_expr_complexity(else_value)
    if else_score > then_score and else_source != (None, None):
        return else_source
    if then_source != (None, None):
        return then_source
    if else_source != (None, None):
        return else_source
    return fallback_source


def _compiled_expr_complexity(expr) -> int:
    if isinstance(expr, (ConstExpr, SignalRef, MemoryReadExpr)):
        return 1
    if isinstance(expr, MaskExpr):
        return _compiled_expr_complexity(expr.value)
    if isinstance(expr, UnaryExpr):
        child = _compiled_expr_complexity(expr.value)
        return child if expr.op in {"$signed", "$unsigned"} else child + 1
    if isinstance(expr, BinaryExpr):
        child = max(_compiled_expr_complexity(expr.lhs), _compiled_expr_complexity(expr.rhs))
        return child if expr.op in {"<<", ">>", ">>>"} else child + 1
    if isinstance(expr, MuxExpr):
        return max(
            _compiled_expr_complexity(expr.cond),
            _compiled_expr_complexity(expr.when_true),
            _compiled_expr_complexity(expr.when_false),
        )
    return 1


def _reject_unsupported_module_features(module) -> None:
    if module._submodules:
        raise DslLoweringError("DSL lowering expects a flattened module")
    if getattr(module, "_beh_func", None) is not None:
        raise DslLoweringError("behavioral callback modules are not supported")
    unsupported_top = [
        type(stmt).__name__
        for stmt in module._top_level
        if not isinstance(stmt, _ASSIGN_TYPES) and type(stmt).__name__ != "Comment"
    ]
    if unsupported_top:
        kinds = ", ".join(sorted(set(unsupported_top)))
        raise DslLoweringError(f"unsupported top-level statement types: {kinds}")


class _LoweringEnv:
    def __init__(
        self,
        signal_map: Mapping[str, SimSignal],
        memory_map: Mapping[str, Memory],
        *,
        clock_domain: Optional[str] = None,
    ):
        self._signal_map = signal_map
        self._memory_map = memory_map
        self._clock_domain = clock_domain
        self._assigned: MutableMapping[str, object] = {}
        self._assignment_sources: MutableMapping[str, tuple[Optional[str], Optional[int]]] = {}
        self._memory_writes: List[MemoryWrite] = []
        self._phase: Optional[str] = None
        self._path_guard = ConstExpr(1, 1)

    def read(self, signal_name: str):
        signal = self._signal_map[signal_name]
        if self._phase == "comb" and signal.kind in {"wire", "output"} and signal_name in self._assigned:
            return self._assigned[signal_name]
        if self._phase == "latch" and signal.kind == "state" and signal_name in self._assigned:
            return self._assigned[signal_name]
        return SignalRef(signal_name)

    def read_memory(self, memory_name: str, addr_expr):
        memory = self._memory_map.get(memory_name)
        if memory is None:
            raise DslLoweringError(f"expression references unknown memory '{memory_name}'")
        return MemoryReadExpr(memory_name, addr_expr)

    def assign(self, target, expr, *, phase: str, source_file: Optional[str] = None, source_line: Optional[int] = None) -> None:
        signal = self._signal_map.get(target.name)
        if signal is None:
            raise DslLoweringError(f"assignment targets unknown signal '{target.name}'")
        if phase == "comb" and signal.kind not in {"wire", "output"}:
            raise DslLoweringError(
                f"combinational lowering only supports wire/output targets, got {signal.kind} '{target.name}'. "
                "Register updates belong in a sequential ('seq') block, not a combinational ('comb') block."
            )
        if phase == "latch" and signal.kind != "state":
            raise DslLoweringError(
                f"latch lowering only supports reg targets, got {signal.kind} '{target.name}'. "
                "Latch blocks may only hold state in registers."
            )
        if phase == "seq" and signal.kind != "state":
            if signal.kind == "output":
                raise DslLoweringError(
                    f"sequential lowering only supports reg targets, got output '{target.name}'. "
                    "Drive an Output by registering it first: assign the value to a Reg inside the seq block, "
                    "then assign the Output from that Reg in a comb block "
                    "(e.g. self.out_reg <<= value inside seq; self.out <<= self.out_reg inside comb)."
                )
            raise DslLoweringError(
                f"sequential lowering only supports reg targets, got {signal.kind} '{target.name}'. "
                "Sequential blocks may only update registers."
            )
        self._assigned[target.name] = expr
        self._assignment_sources[target.name] = (source_file, source_line)
        self._phase = phase

    def write_memory(
        self,
        memory_name: str,
        addr_expr,
        value_expr,
        *,
        phase: str,
        byte_enable_expr=None,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None,
    ) -> None:
        memory = self._memory_map.get(memory_name)
        if memory is None:
            raise DslLoweringError(f"memory write targets unknown memory '{memory_name}'")
        if phase != "seq":
            raise DslLoweringError(
                f"storage write lowering only supports sequential phase, got write to '{memory_name}' in {phase}"
            )
        enable = self._path_enable()
        self._memory_writes.append(
            MemoryWrite(
                memory_name,
                addr_expr,
                value_expr,
                enable=enable,
                clock_domain=self._clock_domain,
                byte_enable=byte_enable_expr,
                source_file=source_file,
                source_line=source_line,
            )
        )
        self._phase = phase

    def branch(self) -> "_LoweringEnv":
        child = _LoweringEnv(self._signal_map, self._memory_map, clock_domain=self._clock_domain)
        child._assigned = dict(self._assigned)
        child._assignment_sources = dict(self._assignment_sources)
        child._memory_writes = list(self._memory_writes)
        child._phase = self._phase
        child._path_guard = self._path_guard
        return child

    def branch_with_guard(self, guard) -> "_LoweringEnv":
        child = self.branch()
        child._path_guard = _logic_and(self._path_guard, guard)
        return child

    def merge_if(self, cond, then_env: "_LoweringEnv", else_env: "_LoweringEnv", *, phase: str) -> None:
        changed_names = set(then_env._assigned) | set(else_env._assigned)
        for name in changed_names:
            signal = self._signal_map[name]
            base = self._assigned.get(name)
            if base is None:
                base = SignalRef(name) if phase == "seq" or signal.kind == "state" else SignalRef(name)
            then_value = then_env._assigned.get(name, base)
            else_value = else_env._assigned.get(name, base)
            preferred_source = _pick_preferred_assignment_source(
                then_value,
                then_env._assignment_sources.get(name, (None, None)),
                else_value,
                else_env._assignment_sources.get(name, (None, None)),
                self._assignment_sources.get(name, (None, None)),
            )
            if _expr_equal_compiled(then_value, else_value):
                self._assigned[name] = then_value
                self._assignment_sources[name] = preferred_source
            else:
                self._assigned[name] = MuxExpr(cond, then_value, else_value)
                self._assignment_sources[name] = preferred_source
        self._phase = phase

    def merge_switch(self, selector, cases: Sequence[tuple], default_env: "_LoweringEnv", *, phase: str) -> None:
        current = default_env
        result = self.branch()
        result._assigned = dict(default_env._assigned)
        result._phase = phase
        for case_value, case_env in reversed(cases):
            cond = BinaryExpr("==", selector, case_value)
            merged = self.branch()
            merged._assigned = dict(result._assigned)
            merged._phase = phase
            merged.merge_if(cond, case_env, result, phase=phase)
            result = merged
        self._assigned = dict(result._assigned)
        self._phase = phase

    def finalize_phase(self) -> List[Assignment]:
        if self._phase is None:
            return []
        return [
            Assignment(
                target=name,
                expr=expr,
                phase=self._phase,
                clock_domain=self._clock_domain if self._phase == "seq" else None,
                source_file=self._assignment_sources.get(name, (None, None))[0],
                source_line=self._assignment_sources.get(name, (None, None))[1],
            )
            for name, expr in self._assigned.items()
        ]

    def finalize_memory_writes(self) -> List[MemoryWrite]:
        return list(self._memory_writes)

    def _path_enable(self):
        return self._path_guard


def _compiled_expr_signal_refs(expr) -> Set[str]:
    if isinstance(expr, SignalRef):
        return {expr.name}
    if isinstance(expr, MemoryReadExpr):
        return _compiled_expr_signal_refs(expr.addr)
    if isinstance(expr, MaskExpr):
        return _compiled_expr_signal_refs(expr.value)
    if isinstance(expr, UnaryExpr):
        return _compiled_expr_signal_refs(expr.value)
    if isinstance(expr, BinaryExpr):
        return _compiled_expr_signal_refs(expr.lhs) | _compiled_expr_signal_refs(expr.rhs)
    if isinstance(expr, MuxExpr):
        return (
            _compiled_expr_signal_refs(expr.cond)
            | _compiled_expr_signal_refs(expr.when_true)
            | _compiled_expr_signal_refs(expr.when_false)
        )
    return set()


def _topologically_order_comb_assignments(
    assignments: Sequence[Assignment],
    signal_map: Mapping[str, SimSignal],
) -> List[Assignment]:
    comb_items: List[tuple[int, Assignment]] = []
    other_items: List[tuple[int, Assignment]] = []
    for index, assignment in enumerate(assignments):
        if assignment.phase == "comb":
            comb_items.append((index, assignment))
        else:
            other_items.append((index, assignment))

    if len(comb_items) < 2:
        return list(assignments)

    comb_targets = {assignment.target for _, assignment in comb_items}
    outgoing: Dict[str, Set[str]] = {assignment.target: set() for _, assignment in comb_items}
    indegree: Dict[str, int] = {assignment.target: 0 for _, assignment in comb_items}
    original_index = {assignment.target: index for index, assignment in comb_items}
    target_to_assignment = {assignment.target: assignment for _, assignment in comb_items}

    for _, assignment in comb_items:
        deps = {
            name
            for name in _compiled_expr_signal_refs(assignment.expr)
            if name in comb_targets and name != assignment.target
        }
        for dep in deps:
            if assignment.target not in outgoing[dep]:
                outgoing[dep].add(assignment.target)
                indegree[assignment.target] += 1

    ready = sorted(
        [target for target, degree in indegree.items() if degree == 0],
        key=original_index.__getitem__,
    )
    ordered_targets: List[str] = []
    while ready:
        target = ready.pop(0)
        ordered_targets.append(target)
        newly_ready: List[str] = []
        for succ in sorted(outgoing[target], key=original_index.__getitem__):
            indegree[succ] -= 1
            if indegree[succ] == 0:
                newly_ready.append(succ)
        if newly_ready:
            ready.extend(newly_ready)
            ready.sort(key=original_index.__getitem__)

    if len(ordered_targets) != len(comb_items):
        remaining = [
            target
            for target in sorted(comb_targets, key=original_index.__getitem__)
            if target not in ordered_targets
        ]
        ordered_targets.extend(remaining)

    ordered_comb = [target_to_assignment[target] for target in ordered_targets]
    ordered_by_original_pos: Dict[int, Assignment] = {}
    comb_positions = [index for index, _ in comb_items]
    for position, assignment in zip(comb_positions, ordered_comb):
        ordered_by_original_pos[position] = assignment
    for position, assignment in other_items:
        ordered_by_original_pos[position] = assignment

    ordered_positions = sorted(ordered_by_original_pos.keys())
    return [ordered_by_original_pos[idx] for idx in ordered_positions]


def _lower_sync_read_memories_into_executable_subset(
    source_module,
    signals: List[SimSignal],
    signal_map: Dict[str, SimSignal],
    memories: List[Memory],
    assignments: List[Assignment],
    memory_writes: List[MemoryWrite],
    clock_domains: Sequence[ClockDomain],
) -> tuple[List[SimSignal], List[Memory], List[Assignment]]:
    sync_memories = [memory for memory in memories if memory.read_style == "sync" and memory.read_latency == 1]
    if not sync_memories:
        return signals, memories, assignments

    memory_reads = _collect_dsl_memory_reads(source_module)
    domain_names = {domain.name for domain in clock_domains}
    default_domain = clock_domains[0].name if len(clock_domains) == 1 else None
    new_assignments = list(assignments)
    new_memories: List[Memory] = []

    for memory in memories:
        if memory.read_style == "sync" and memory.read_latency == 1:
            new_memories.append(
                Memory(
                    name=memory.name,
                    width=memory.width,
                    depth=memory.depth,
                    init=memory.init,
                    read_during_write=memory.read_during_write,
                    read_ports=memory.read_ports,
                    write_ports=memory.write_ports,
                    read_style="async",
                    read_latency=0,
                    byte_enable_granularity=memory.byte_enable_granularity,
                )
            )
        else:
            new_memories.append(memory)

    assignment_by_target = {assignment.target: assignment for assignment in assignments}
    memory_write_domains = _memory_write_domains(memory_writes, default_domain=default_domain)
    appended_targets: set[str] = set()

    for memory in sync_memories:
        reads = memory_reads.get(memory.name, ())
        if not reads:
            continue
        write_domain = memory_write_domains.get(memory.name)
        for read in reads:
            output_signal = signal_map.get(read.target_name)
            if output_signal is None:
                raise DslLoweringError(
                    f"sync-read lowering could not resolve target '{read.target_name}'"
                )
            state_name = f"__sync_rd_{memory.name}_{read.target_name}"
            addr_state_name = f"{state_name}_addr"
            if state_name not in signal_map:
                state_signal = SimSignal(
                    name=state_name,
                    width=memory.width,
                    kind="state",
                    init=memory.init[0] if memory.init else 0,
                )
                addr_signal = SimSignal(
                    name=addr_state_name,
                    width=memory.addr_width,
                    kind="state",
                    init=0,
                )
                signals.append(state_signal)
                signals.append(addr_signal)
                signal_map[state_name] = state_signal
                signal_map[addr_state_name] = addr_signal

            original = assignment_by_target.get(read.target_name)
            if original is None:
                raise DslLoweringError(
                    f"sync-read lowering expected a comb assignment driving '{read.target_name}'"
                )
            new_assignments = [a for a in new_assignments if a is not original]
            new_assignments.append(
                Assignment(
                    target=read.target_name,
                    expr=SignalRef(state_name),
                    phase="comb",
                    source_file=original.source_file,
                    source_line=original.source_line,
                )
            )
            if state_name in appended_targets:
                continue
            read_domain = _resolve_sync_read_domain(
                source_module,
                read.target_name,
                write_domain=write_domain,
                domain_names=domain_names,
                default_domain=default_domain,
            )
            new_assignments.append(
                Assignment(
                    target=addr_state_name,
                    expr=MaskExpr(read.addr_expr, memory.addr_width),
                    phase="seq",
                    clock_domain=read_domain,
                    source_file=original.source_file,
                    source_line=original.source_line,
                )
            )
            new_assignments.append(
                Assignment(
                    target=state_name,
                    expr=MemoryReadExpr(memory.name, SignalRef(addr_state_name)),
                    phase="seq",
                    clock_domain=read_domain,
                    source_file=original.source_file,
                    source_line=original.source_line,
                )
            )
            appended_targets.add(state_name)

    return signals, new_memories, new_assignments


@dataclass(frozen=True)
class _SyncMemoryReadUse:
    memory_name: str
    target_name: str
    addr_expr: object


def _collect_dsl_memory_reads(module) -> Dict[str, tuple[_SyncMemoryReadUse, ...]]:
    uses: Dict[str, List[_SyncMemoryReadUse]] = {}

    def visit_expr(expr, target_name: Optional[str]) -> None:
        if expr is None or isinstance(expr, int):
            return
        if isinstance(expr, _MEM_READ_TYPES):
            if target_name is None:
                raise DslLoweringError(
                    f"sync-read lowering requires memory read '{expr.mem_name}[...]' to drive a named signal"
                )
            uses.setdefault(expr.mem_name, []).append(
                _SyncMemoryReadUse(expr.mem_name, target_name, _lower_ast_expr_no_env(expr.addr))
            )
            visit_expr(expr.addr, None)
            return
        if isinstance(expr, _ARRAY_READ_TYPES):
            visit_expr(expr.index, None)
            return
        if isinstance(expr, _REF_TYPES):
            return
        if isinstance(expr, _SIGNAL_TYPES):
            inner = getattr(expr, "_expr", None)
            if inner is not None and inner is not expr:
                visit_expr(inner, target_name)
            return
        if isinstance(expr, _BINOP_TYPES):
            visit_expr(expr.lhs, None)
            visit_expr(expr.rhs, None)
            return
        if isinstance(expr, _UNARY_TYPES):
            visit_expr(expr.operand, None)
            return
        if isinstance(expr, _MUX_TYPES):
            visit_expr(expr.cond, None)
            visit_expr(expr.true_expr, target_name)
            visit_expr(expr.false_expr, target_name)
            return
        if isinstance(expr, _SLICE_TYPES):
            visit_expr(expr.operand, target_name)
            if not isinstance(expr.lo, int):
                visit_expr(expr.lo, None)
            return
        if isinstance(expr, _PARTSELECT_TYPES):
            visit_expr(expr.operand, target_name)
            visit_expr(expr.offset, None)
            return
        if isinstance(expr, _BITSELECT_TYPES):
            visit_expr(expr.operand, target_name)
            visit_expr(expr.index, None)
            return
        if isinstance(expr, _CONCAT_TYPES):
            for operand in expr.operands:
                visit_expr(operand, target_name)

    def visit_stmt(stmt) -> None:
        if isinstance(stmt, _ASSIGN_TYPES):
            target_name = None
            if isinstance(stmt.target, _SIGNAL_TYPES):
                target_name = stmt.target.name
            elif isinstance(stmt.target, _REF_TYPES):
                target_name = stmt.target.signal.name
            visit_expr(stmt.value, target_name)
            return
        if isinstance(stmt, _IF_TYPES):
            visit_expr(stmt.cond, None)
            for nested in stmt.then_body:
                visit_stmt(nested)
            for _cond, body in stmt.elif_bodies:
                for nested in body:
                    visit_stmt(nested)
            for nested in stmt.else_body:
                visit_stmt(nested)
            return
        if isinstance(stmt, _SWITCH_TYPES):
            visit_expr(stmt.expr, None)
            for _value, body in stmt.cases:
                for nested in body:
                    visit_stmt(nested)
            for nested in stmt.default_body:
                visit_stmt(nested)
            return
        if isinstance(stmt, _WHEN_TYPES):
            for cond, body in stmt.branches:
                if cond is not None:
                    visit_expr(cond, None)
                for nested in body:
                    visit_stmt(nested)

    for body in getattr(module, "_comb_blocks", ()):
        for stmt in body:
            visit_stmt(stmt)
    for stmt in getattr(module, "_top_level", ()):
        visit_stmt(stmt)
    return {name: tuple(entries) for name, entries in uses.items()}


def _lower_ast_expr_no_env(expr):
    if isinstance(expr, int):
        width = max(expr.bit_length(), 1)
        return ConstExpr(expr, width)
    if isinstance(expr, _SIGNAL_TYPES):
        ref_expr = getattr(expr, "_expr", None)
        if ref_expr is not None and not (
            isinstance(ref_expr, _REF_TYPES) and getattr(ref_expr, "signal", None) is expr
        ):
            return _lower_ast_expr_no_env(ref_expr)
        return SignalRef(expr.name)
    if isinstance(expr, _CONST_TYPES):
        return ConstExpr(expr.value, expr.width)
    if isinstance(expr, _REF_TYPES):
        return SignalRef(expr.signal.name)
    if isinstance(expr, _UNARY_TYPES):
        lowered_operand = _lower_ast_expr_no_env(expr.operand)
        lowered_unary = UnaryExpr(expr.op, lowered_operand)
        if expr.op == "~":
            return MaskExpr(lowered_unary, expr.width)
        return lowered_unary
    if isinstance(expr, _BINOP_TYPES):
        return BinaryExpr(
            expr.op,
            _lower_ast_expr_no_env(expr.lhs),
            _lower_ast_expr_no_env(expr.rhs),
        )
    if isinstance(expr, _MUX_TYPES):
        return MuxExpr(
            _lower_ast_expr_no_env(expr.cond),
            _lower_ast_expr_no_env(expr.true_expr),
            _lower_ast_expr_no_env(expr.false_expr),
        )
    if isinstance(expr, _SLICE_TYPES):
        if not isinstance(expr.hi, int) or not isinstance(expr.lo, int):
            return MaskExpr(
                BinaryExpr(">>", _lower_ast_expr_no_env(expr.operand), _lower_ast_expr_no_env(expr.lo)),
                expr.width,
            )
        return MaskExpr(
            BinaryExpr(
                ">>",
                _lower_ast_expr_no_env(expr.operand),
                ConstExpr(expr.lo, max(expr.lo.bit_length(), 1)),
            ),
            expr.width,
        )
    if isinstance(expr, _PARTSELECT_TYPES):
        return MaskExpr(
            BinaryExpr(">>", _lower_ast_expr_no_env(expr.operand), _lower_ast_expr_no_env(expr.offset)),
            expr.width,
        )
    if isinstance(expr, _BITSELECT_TYPES):
        return MaskExpr(
            BinaryExpr(">>", _lower_ast_expr_no_env(expr.operand), _lower_ast_expr_no_env(expr.index)),
            1,
        )
    raise DslLoweringError(
        f"sync-read lowering does not support address expression type '{type(expr).__name__}'"
    )


def _memory_write_domains(
    memory_writes: Sequence[MemoryWrite],
    *,
    default_domain: Optional[str],
) -> Dict[str, Optional[str]]:
    domains: Dict[str, Optional[str]] = {}
    for write in memory_writes:
        domains[write.memory] = write.clock_domain or default_domain
    return domains


def _resolve_sync_read_domain(
    source_module,
    target_name: str,
    *,
    write_domain: Optional[str],
    domain_names: Set[str],
    default_domain: Optional[str],
) -> Optional[str]:
    if not domain_names:
        return None
    target_domains: Set[str] = set()
    for clk, _rst, _reset_async, _reset_active_low, body in getattr(source_module, "_seq_blocks", ()):
        clk_name = getattr(clk, "name", str(clk)) if clk is not None else None
        if clk_name is None:
            continue
        if _seq_body_writes_target(body, target_name):
            target_domains.add(clk_name)
    if len(target_domains) > 1:
        joined = ", ".join(sorted(target_domains))
        raise DslLoweringError(
            f"sync-read lowering cannot infer a unique sampling clock for target '{target_name}'; "
            f"observed sequential consumers on multiple domains: {joined}"
        )
    if len(target_domains) == 1:
        return next(iter(target_domains))
    return write_domain or default_domain


def _seq_body_writes_target(body: Sequence[object], target_name: str) -> bool:
    for stmt in body:
        if isinstance(stmt, _ASSIGN_TYPES):
            if isinstance(stmt.target, _SIGNAL_TYPES) and stmt.target.name == target_name:
                return True
            if isinstance(stmt.target, _REF_TYPES) and stmt.target.signal.name == target_name:
                return True
            continue
        if isinstance(stmt, _IF_TYPES):
            if _seq_body_writes_target(stmt.then_body, target_name):
                return True
            if _seq_body_writes_target(stmt.else_body, target_name):
                return True
            for _cond, elif_body in stmt.elif_bodies:
                if _seq_body_writes_target(elif_body, target_name):
                    return True
            continue
        if isinstance(stmt, _SWITCH_TYPES):
            for _value, case_body in stmt.cases:
                if _seq_body_writes_target(case_body, target_name):
                    return True
            if _seq_body_writes_target(stmt.default_body, target_name):
                return True
            continue
        if isinstance(stmt, _WHEN_TYPES):
            for _cond, branch_body in stmt.branches:
                if _seq_body_writes_target(branch_body, target_name):
                    return True
    return False


def _lower_stmt_list(stmts: Iterable[object], *, phase: str, env: _LoweringEnv) -> None:
    env._phase = phase
    for stmt in stmts:
        if isinstance(stmt, _ASSIGN_TYPES):
            _lower_assign(
                stmt.target,
                stmt.value,
                phase=phase,
                env=env,
                source_location=getattr(stmt, "source_location", None),
            )
            continue
        if isinstance(stmt, _INDEXED_ASSIGN_TYPES):
            _lower_indexed_assign(stmt, phase=phase, env=env)
            continue
        if isinstance(stmt, _MEM_WRITE_TYPES):
            _lower_memory_write(stmt, phase=phase, env=env)
            continue
        if isinstance(stmt, _ARRAY_WRITE_TYPES):
            _lower_array_write(stmt, phase=phase, env=env)
            continue
        if isinstance(stmt, _IF_TYPES):
            _lower_if(stmt, phase=phase, env=env)
            continue
        if isinstance(stmt, _SWITCH_TYPES):
            _lower_switch(stmt, phase=phase, env=env)
            continue
        if isinstance(stmt, _WHEN_TYPES):
            _lower_when(stmt, phase=phase, env=env)
            continue
        stmt_name = type(stmt).__name__
        if stmt_name == "Comment":
            continue
        raise DslLoweringError(f"unsupported statement type '{stmt_name}'")


def _lower_if(stmt: IfNode, *, phase: str, env: _LoweringEnv) -> None:
    base_write_count = len(env._memory_writes)
    cond_expr = _lower_expr(stmt.cond, env)
    chain_else_env = env.branch_with_guard(_logic_not(cond_expr))
    if stmt.else_body:
        _lower_stmt_list(stmt.else_body, phase=phase, env=chain_else_env)
    for elif_cond, elif_body in reversed(stmt.elif_bodies):
        elif_cond_expr = _lower_expr(elif_cond, env)
        elif_then = env.branch_with_guard(elif_cond_expr)
        _lower_stmt_list(elif_body, phase=phase, env=elif_then)
        merged = env.branch()
        merged.merge_if(elif_cond_expr, elif_then, chain_else_env, phase=phase)
        merged._memory_writes = (
            list(env._memory_writes[:base_write_count])
            + elif_then._memory_writes[base_write_count:]
            + chain_else_env._memory_writes[base_write_count:]
        )
        chain_else_env = merged
    then_env = env.branch_with_guard(cond_expr)
    _lower_stmt_list(stmt.then_body, phase=phase, env=then_env)
    env.merge_if(cond_expr, then_env, chain_else_env, phase=phase)
    env._memory_writes = (
        list(env._memory_writes[:base_write_count])
        + then_env._memory_writes[base_write_count:]
        + chain_else_env._memory_writes[base_write_count:]
    )


def _lower_switch(stmt: SwitchNode, *, phase: str, env: _LoweringEnv) -> None:
    if stmt.kind != "case":
        raise DslLoweringError(f"unsupported switch kind '{stmt.kind}'")
    selector = _lower_expr(stmt.expr, env)
    case_values = [_lower_expr(value, env) for value, _ in stmt.cases]
    case_conds = [BinaryExpr("==", selector, value_expr) for value_expr in case_values]
    default_guard = ConstExpr(1, 1)
    for cond in case_conds:
        default_guard = _logic_and(default_guard, _logic_not(cond))
    base_write_count = len(env._memory_writes)
    default_env = env.branch_with_guard(default_guard)
    _lower_stmt_list(stmt.default_body, phase=phase, env=default_env)
    case_envs = []
    for value_expr, (_, body), case_cond in zip(case_values, stmt.cases, case_conds):
        case_env = env.branch_with_guard(case_cond)
        _lower_stmt_list(body, phase=phase, env=case_env)
        case_envs.append((value_expr, case_env))
    env.merge_switch(selector, case_envs, default_env, phase=phase)
    env._memory_writes = list(env._memory_writes[:base_write_count])
    for _, case_env in case_envs:
        env._memory_writes.extend(case_env._memory_writes[base_write_count:])
    env._memory_writes.extend(default_env._memory_writes[base_write_count:])


def _lower_when(stmt: WhenNode, *, phase: str, env: _LoweringEnv) -> None:
    branches = list(stmt.branches)
    if not branches:
        return
    base_write_count = len(env._memory_writes)
    current_else = env.branch()
    otherwise_seen = False
    seen_guard = ConstExpr(0, 1)
    for cond, body in reversed(branches):
        if cond is None:
            branch_env = env.branch_with_guard(_logic_not(seen_guard))
        else:
            cond_expr = _lower_expr(cond, env)
            branch_env = env.branch_with_guard(cond_expr)
        _lower_stmt_list(body, phase=phase, env=branch_env)
        if cond is None:
            current_else = branch_env
            otherwise_seen = True
            continue
        merged = env.branch()
        merged.merge_if(cond_expr, branch_env, current_else, phase=phase)
        merged._memory_writes = (
            list(env._memory_writes[:base_write_count])
            + branch_env._memory_writes[base_write_count:]
            + current_else._memory_writes[base_write_count:]
        )
        current_else = merged
        seen_guard = _logic_or(seen_guard, cond_expr)
    if not otherwise_seen:
        current_else = current_else
    env._assigned = dict(current_else._assigned)
    env._memory_writes = list(current_else._memory_writes)
    env._phase = phase


def _lower_expr(expr, env: _LoweringEnv):
    if isinstance(expr, int):
        width = max(expr.bit_length(), 1)
        return ConstExpr(expr, width)
    if isinstance(expr, _SIGNAL_TYPES):
        ref_expr = getattr(expr, "_expr", None)
        if ref_expr is not None and not (
            isinstance(ref_expr, _REF_TYPES) and getattr(ref_expr, "signal", None) is expr
        ):
            return _lower_expr(ref_expr, env)
        return env.read(expr.name)
    if isinstance(expr, _CONST_TYPES):
        return ConstExpr(expr.value, expr.width)
    if isinstance(expr, _REF_TYPES):
        return env.read(expr.signal.name)
    if isinstance(expr, _MEM_READ_TYPES):
        return env.read_memory(expr.mem_name, _lower_expr(expr.addr, env))
    if isinstance(expr, _ARRAY_READ_TYPES):
        return env.read_memory(expr.array_name, _lower_expr(expr.index, env))
    if isinstance(expr, _UNARY_TYPES):
        if expr.op not in {"~", "-", "!", "$signed", "$unsigned"}:
            raise DslLoweringError(f"unsupported unary op '{expr.op}'")
        lowered_operand = _lower_expr(expr.operand, env)
        lowered_unary = UnaryExpr(expr.op, lowered_operand)
        if expr.op == "~":
            return MaskExpr(lowered_unary, expr.width)
        return lowered_unary
    if isinstance(expr, _BINOP_TYPES):
        if expr.op not in {
            "+",
            "-",
            "*",
            "&",
            "|",
            "^",
            "<<",
            ">>",
            ">>>",
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
        }:
            raise DslLoweringError(f"unsupported binary op '{expr.op}'")
        return BinaryExpr(expr.op, _lower_expr(expr.lhs, env), _lower_expr(expr.rhs, env))
    if isinstance(expr, _MUX_TYPES):
        return MuxExpr(
            _lower_expr(expr.cond, env),
            _lower_expr(expr.true_expr, env),
            _lower_expr(expr.false_expr, env),
        )
    if isinstance(expr, _SLICE_TYPES):
        if not isinstance(expr.hi, int) or not isinstance(expr.lo, int):
            return MaskExpr(
                BinaryExpr(">>", _lower_expr(expr.operand, env), _lower_expr(expr.lo, env)),
                expr.width,
            )
        operand = _lower_expr(expr.operand, env)
        width = expr.hi - expr.lo + 1
        return MaskExpr(
            BinaryExpr(">>", operand, ConstExpr(expr.lo, max(expr.lo.bit_length(), 1))),
            width,
        )
    if isinstance(expr, _PARTSELECT_TYPES):
        operand = _lower_expr(expr.operand, env)
        offset = _lower_expr(expr.offset, env)
        return MaskExpr(BinaryExpr(">>", operand, offset), expr.width)
    if isinstance(expr, _BITSELECT_TYPES):
        operand = _lower_expr(expr.operand, env)
        index = _lower_expr(expr.index, env)
        return MaskExpr(BinaryExpr(">>", operand, index), 1)
    if isinstance(expr, _CONCAT_TYPES):
        operands = list(expr.operands)
        if not operands:
            raise DslLoweringError("empty concat is not supported")
        acc = _lower_expr(operands[0], env)
        running_width = operands[0].width
        for operand in operands[1:]:
            part = _lower_expr(operand, env)
            running_width += operand.width
            acc = BinaryExpr(
                "|",
                BinaryExpr("<<", acc, ConstExpr(operand.width, max(operand.width.bit_length(), 1))),
                part,
            )
            acc = MaskExpr(acc, running_width)
        return MaskExpr(acc, running_width)
    raise DslLoweringError(f"unsupported expression type '{type(expr).__name__}'")


def _lower_assign(target, value, *, phase: str, env: _LoweringEnv, source_location=None) -> None:
    source_file = getattr(source_location, "file", None)
    source_line = getattr(source_location, "line", None)
    if isinstance(target, _SIGNAL_TYPES):
        env.assign(
            target,
            _lower_expr(value, env),
            phase=phase,
            source_file=source_file,
            source_line=source_line,
        )
        return
    if isinstance(target, _REF_TYPES):
        env.assign(
            target.signal,
            _lower_expr(value, env),
            phase=phase,
            source_file=source_file,
            source_line=source_line,
        )
        return
    if isinstance(target, _SLICE_TYPES):
        _lower_slice_assign(
            target,
            value,
            phase=phase,
            env=env,
            source_file=source_file,
            source_line=source_line,
        )
        return
    if isinstance(target, _BITSELECT_TYPES):
        _lower_bitselect_assign(
            target,
            value,
            phase=phase,
            env=env,
            source_file=source_file,
            source_line=source_line,
        )
        return
    if isinstance(target, _PARTSELECT_TYPES):
        _lower_partselect_assign(
            target,
            value,
            phase=phase,
            env=env,
            source_file=source_file,
            source_line=source_line,
        )
        return
    raise DslLoweringError(
        f"lowering only supports signal and bit-range assignment targets, got {type(target).__name__}"
    )


def _lower_indexed_assign(stmt: IndexedAssign, *, phase: str, env: _LoweringEnv) -> None:
    target_expr = BitSelect(Ref(stmt.target_signal), stmt.index)
    source_location = getattr(stmt, "source_location", None)
    _lower_bitselect_assign(
        target_expr,
        stmt.value,
        phase=phase,
        env=env,
        source_file=getattr(source_location, "file", None),
        source_line=getattr(source_location, "line", None),
    )


def _lower_memory_write(stmt: MemWrite, *, phase: str, env: _LoweringEnv) -> None:
    source_location = getattr(stmt, "source_location", None)
    env.write_memory(
        stmt.mem_name,
        _lower_expr(stmt.addr, env),
        _lower_expr(stmt.value, env),
        phase=phase,
        byte_enable_expr=(
            _lower_expr(stmt.byte_enable, env)
            if getattr(stmt, "byte_enable", None) is not None
            else None
        ),
        source_file=getattr(source_location, "file", None),
        source_line=getattr(source_location, "line", None),
    )


def _lower_array_write(stmt: ArrayWrite, *, phase: str, env: _LoweringEnv) -> None:
    env.write_memory(
        stmt.array_name,
        _lower_expr(stmt.index, env),
        _lower_expr(stmt.value, env),
        phase=phase,
    )


def _lower_slice_assign(
    target: Slice,
    value,
    *,
    phase: str,
    env: _LoweringEnv,
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise DslLoweringError("slice assignment must target a signal")
    base_signal = target.operand.signal
    replacement_value = _lower_expr(value, env)
    base_value = env._assigned.get(base_signal.name, env.read(base_signal.name))
    if isinstance(target.hi, int) and isinstance(target.lo, int):
        replacement = _replace_bit_range_expr(
            base_value,
            target.lo,
            target.width,
            replacement_value,
            base_signal.width,
        )
    else:
        replacement = _replace_dynamic_range_expr(
            base_value,
            _lower_expr(target.lo, env),
            target.width,
            replacement_value,
            base_signal.width,
        )
    env.assign(
        base_signal,
        replacement,
        phase=phase,
        source_file=source_file,
        source_line=source_line,
    )


def _lower_bitselect_assign(
    target: BitSelect,
    value,
    *,
    phase: str,
    env: _LoweringEnv,
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise DslLoweringError("bit-select assignment must target a signal")
    base_signal = target.operand.signal
    base_value = env._assigned.get(base_signal.name, env.read(base_signal.name))
    index = _const_int(target.index)
    if index is None:
        replacement = _replace_dynamic_bit_expr(
            base_value,
            _lower_expr(target.index, env),
            _lower_expr(value, env),
            base_signal.width,
        )
    else:
        replacement = _replace_bit_range_expr(
            base_value,
            index,
            1,
            _lower_expr(value, env),
            base_signal.width,
        )
    env.assign(
        base_signal,
        replacement,
        phase=phase,
        source_file=source_file,
        source_line=source_line,
    )


def _lower_partselect_assign(
    target: PartSelect,
    value,
    *,
    phase: str,
    env: _LoweringEnv,
    source_file: Optional[str] = None,
    source_line: Optional[int] = None,
) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise DslLoweringError("part-select assignment must target a signal")
    base_signal = target.operand.signal
    base_value = env._assigned.get(base_signal.name, env.read(base_signal.name))
    offset = _const_int(target.offset)
    if offset is None:
        replacement = _replace_dynamic_range_expr(
            base_value,
            _lower_expr(target.offset, env),
            target.width,
            _lower_expr(value, env),
            base_signal.width,
        )
    else:
        replacement = _replace_bit_range_expr(
            base_value,
            offset,
            target.width,
            _lower_expr(value, env),
            base_signal.width,
        )
    env.assign(
        base_signal,
        replacement,
        phase=phase,
        source_file=source_file,
        source_line=source_line,
    )


def _replace_bit_range_expr(base, lo: int, width: int, value, base_width: int):
    if width < 1:
        raise DslLoweringError("bit range width must be positive")
    if lo < 0 or lo + width > base_width:
        raise DslLoweringError("bit range assignment is outside the target signal width")
    range_mask = ((1 << width) - 1) << lo
    keep_mask = ((1 << base_width) - 1) ^ range_mask
    cleared = BinaryExpr("&", base, ConstExpr(keep_mask, base_width))
    shifted = BinaryExpr("<<", MaskExpr(value, width), ConstExpr(lo, max(lo.bit_length(), 1)))
    return MaskExpr(BinaryExpr("|", cleared, shifted), base_width)


def _replace_dynamic_bit_expr(base, index, value, base_width: int):
    return _replace_dynamic_range_expr(base, index, 1, value, base_width)


def _replace_dynamic_range_expr(base, offset, width: int, value, base_width: int):
    dynamic_mask = BinaryExpr("<<", ConstExpr((1 << width) - 1, width), offset)
    keep_mask = BinaryExpr("^", ConstExpr((1 << base_width) - 1, base_width), dynamic_mask)
    cleared = BinaryExpr("&", base, keep_mask)
    shifted = BinaryExpr("<<", MaskExpr(value, width), offset)
    return MaskExpr(BinaryExpr("|", cleared, shifted), base_width)


def _const_int(expr) -> Optional[int]:
    if isinstance(expr, int):
        return expr
    if isinstance(expr, _CONST_TYPES):
        return int(expr.value)
    return None


def _expr_equal_compiled(lhs, rhs) -> bool:
    return repr(lhs) == repr(rhs)


_ASSIGN_TYPES = (DslAssign,) + ((RtlgenAssign,) if RtlgenAssign else ())
_ARRAY_READ_TYPES = (ArrayRead,) + ((RtlgenArrayRead,) if RtlgenArrayRead else ())
_ARRAY_WRITE_TYPES = (ArrayWrite,) + ((RtlgenArrayWrite,) if RtlgenArrayWrite else ())
_BINOP_TYPES = (BinOp,) + ((RtlgenBinOp,) if RtlgenBinOp else ())
_BITSELECT_TYPES = (BitSelect,) + ((RtlgenBitSelect,) if RtlgenBitSelect else ())
_CONCAT_TYPES = (Concat,) + ((RtlgenConcat,) if RtlgenConcat else ())
_CONST_TYPES = (Const,) + ((RtlgenConst,) if RtlgenConst else ())
_IF_TYPES = (IfNode,) + ((RtlgenIfNode,) if RtlgenIfNode else ())
_INDEXED_ASSIGN_TYPES = (IndexedAssign,) + ((RtlgenIndexedAssign,) if RtlgenIndexedAssign else ())
_MEM_READ_TYPES = (MemRead,) + ((RtlgenMemRead,) if RtlgenMemRead else ())
_MEM_WRITE_TYPES = (MemWrite,) + ((RtlgenMemWrite,) if RtlgenMemWrite else ())
_MUX_TYPES = (Mux,) + ((RtlgenMux,) if RtlgenMux else ())
_PARTSELECT_TYPES = (PartSelect,) + ((RtlgenPartSelect,) if RtlgenPartSelect else ())
_REF_TYPES = (Ref,) + ((RtlgenRef,) if RtlgenRef else ())
_SIGNAL_TYPES = (Signal,) + ((RtlgenSignal,) if RtlgenSignal else ())
_SLICE_TYPES = (Slice,) + ((RtlgenSlice,) if RtlgenSlice else ())
_SWITCH_TYPES = (SwitchNode,) + ((RtlgenSwitchNode,) if RtlgenSwitchNode else ())
_UNARY_TYPES = (UnaryOp,) + ((RtlgenUnaryOp,) if RtlgenUnaryOp else ())
_WHEN_TYPES = (WhenNode,) + ((RtlgenWhenNode,) if RtlgenWhenNode else ())


def _select_flatten_module(module):
    if RtlgenModule and isinstance(module, RtlgenModule) and rtlgen_flatten_module is not None:
        return rtlgen_flatten_module
    return flatten_module


def _normalize_cross_module_assignments(module):
    """Return a copy with parent<->child port assigns folded into port_map.

    This mirrors the authoring-time cleanup already used by Verilog emission so
    that lowering/flattening sees the same intended structural hierarchy for
    patterns like:

    - ``self.u_leaf = Child()``
    - ``self.u_leaf.clk <<= self.clk``
    - ``self.mid <<= self.u_leaf.y``

    Without this step, legal parent-owned interconnect patterns can survive as
    plain combinational assignments that target child input ports directly,
    which later lowering correctly rejects as non-local combinational writes.
    """

    normalized = copy.deepcopy(module)

    def direct_signal(expr):
        if isinstance(expr, Signal):
            ref_expr = getattr(expr, "_expr", None)
            if isinstance(ref_expr, Ref) and getattr(ref_expr, "signal", None) is not None:
                return ref_expr.signal
            return expr
        if isinstance(expr, Ref):
            return expr.signal
        return None

    def infer_param_overrides(parent_module: Module, submodule: Module) -> Dict[str, object]:
        params: Dict[str, object] = {}
        for pname, param in submodule._params.items():
            if hasattr(parent_module, pname):
                val = getattr(parent_module, pname)
                if isinstance(val, (Signal, int, str)):
                    params[pname] = val
                elif hasattr(val, "value") and isinstance(getattr(val, "value"), (int, str)):
                    params[pname] = val
        for pname, val in getattr(submodule, "_param_bindings", {}).items():
            params[pname] = val
        return params

    def alloc_instance_name(parent_module: Module, submodule: Module, reserved: Set[str]) -> str:
        base_name = getattr(submodule, "_type_name", submodule.name)
        inst_name = base_name
        if inst_name in reserved:
            suffix = 1
            while f"{inst_name}_{suffix}" in reserved:
                suffix += 1
            inst_name = f"{inst_name}_{suffix}"
        reserved.add(inst_name)
        return inst_name

    def find_port_name(submodule: Module, signal: Signal) -> Optional[str]:
        for pname, psig in list(submodule._inputs.items()) + list(submodule._outputs.items()):
            if psig is signal:
                return pname
        return None

    def ensure_helper_wire(parent_module: Module, wire_name: str, source_signal: Signal) -> Wire:
        existing = parent_module._wires.get(wire_name)
        if existing is not None:
            return existing
        helper = _clone_signal_shape(source_signal, wire_name, cls=Wire)
        helper._parent_module = parent_module
        parent_module._wires[wire_name] = helper
        object.__setattr__(parent_module, wire_name, helper)
        return helper

    def visit_module(mod: Module, stack: Set[int]) -> None:
        if id(mod) in stack:
            return
        stack = set(stack)
        stack.add(id(mod))

        explicit_by_submod: Dict[int, SubmoduleInst] = {
            id(stmt.module): stmt for stmt in mod._top_level if isinstance(stmt, SubmoduleInst)
        }
        registered_names = {id(sub): name for name, sub in mod._submodules}
        reserved_names = {name for name, _ in mod._submodules}
        reserved_names.update(
            stmt.name for stmt in mod._top_level if isinstance(stmt, SubmoduleInst)
        )

        submodule_infos: Dict[int, Dict[str, object]] = {}

        def ensure_submodule_info(submodule: Module) -> Dict[str, object]:
            submod_id = id(submodule)
            if submod_id in submodule_infos:
                return submodule_infos[submod_id]
            inst_name = registered_names.get(submod_id)
            if inst_name is None:
                inst_name = alloc_instance_name(mod, submodule, reserved_names)
            info = {
                "submod": submodule,
                "inst_name": inst_name,
                "inputs": {},
                "outputs": {},
            }
            submodule_infos[submod_id] = info
            return info

        def rewrite_child_output_expr(expr, owner_module: Module):
            if expr is None or isinstance(expr, int):
                return expr

            signal = direct_signal(expr)
            signal_owner = getattr(signal, "_parent_module", None) if signal is not None else None
            if (
                signal is not None
                and isinstance(signal_owner, Module)
                and signal_owner is not owner_module
            ):
                port_name = find_port_name(signal_owner, signal)
                if port_name is not None and port_name in signal_owner._outputs:
                    info = ensure_submodule_info(signal_owner)
                    helper_name = f"{info['inst_name']}_{port_name}"
                    helper = ensure_helper_wire(owner_module, helper_name, signal)
                    info["outputs"][port_name] = helper
                    return helper if isinstance(expr, Signal) else Ref(helper)

            if isinstance(expr, Signal):
                ref_expr = getattr(expr, "_expr", None)
                if isinstance(ref_expr, Ref):
                    return expr
            if isinstance(expr, Ref):
                return expr
            if isinstance(expr, BinOp):
                return BinOp(
                    expr.op,
                    rewrite_child_output_expr(expr.lhs, owner_module),
                    rewrite_child_output_expr(expr.rhs, owner_module),
                    expr.width,
                )
            if isinstance(expr, UnaryOp):
                return UnaryOp(expr.op, rewrite_child_output_expr(expr.operand, owner_module), expr.width)
            if isinstance(expr, Slice):
                return Slice(rewrite_child_output_expr(expr.operand, owner_module), expr.hi, expr.lo)
            if isinstance(expr, PartSelect):
                return PartSelect(
                    rewrite_child_output_expr(expr.operand, owner_module),
                    rewrite_child_output_expr(expr.offset, owner_module),
                    expr.width,
                )
            if isinstance(expr, BitSelect):
                return BitSelect(
                    rewrite_child_output_expr(expr.operand, owner_module),
                    rewrite_child_output_expr(expr.index, owner_module),
                )
            if isinstance(expr, Concat):
                return Concat([rewrite_child_output_expr(op, owner_module) for op in expr.operands], expr.width)
            if isinstance(expr, Mux):
                return Mux(
                    rewrite_child_output_expr(expr.cond, owner_module),
                    rewrite_child_output_expr(expr.true_expr, owner_module),
                    rewrite_child_output_expr(expr.false_expr, owner_module),
                    expr.width,
                )
            if isinstance(expr, MemRead):
                return MemRead(
                    expr.mem_name,
                    rewrite_child_output_expr(expr.addr, owner_module),
                    expr.width,
                )
            if isinstance(expr, ArrayRead):
                return ArrayRead(
                    expr.array_name,
                    rewrite_child_output_expr(expr.index, owner_module),
                    expr.width,
                )
            return expr

        def direct_external_output_passthrough(stmt: DslAssign, owner_module: Module) -> bool:
            target_signal = direct_signal(getattr(stmt, "target", None))
            value_signal = direct_signal(getattr(stmt, "value", None))
            if target_signal is None or value_signal is None:
                return False
            if getattr(target_signal, "_parent_module", None) is not owner_module:
                return False
            if not any(target_signal is output for output in owner_module._outputs.values()):
                return False
            signal_owner = getattr(value_signal, "_parent_module", None)
            if not isinstance(signal_owner, Module) or signal_owner is owner_module:
                return False
            if not getattr(signal_owner, "_external_verilog", False):
                return False
            port_name = find_port_name(signal_owner, value_signal)
            if port_name is None or port_name not in signal_owner._outputs:
                return False
            if getattr(target_signal, "width", None) != getattr(value_signal, "width", None):
                return False
            info = ensure_submodule_info(signal_owner)
            info["outputs"][port_name] = target_signal
            return True

        def normalize_body(body: List[object]) -> None:
            to_remove: List[int] = []
            for i, stmt in enumerate(body):
                if not isinstance(stmt, DslAssign):
                    continue

                target_expr = getattr(stmt, "target", None)
                value_expr = getattr(stmt, "value", None)
                target_signal = direct_signal(target_expr)
                value_signal = direct_signal(value_expr)

                target_owner = getattr(target_signal, "_parent_module", None) if target_signal is not None else None
                value_owner = getattr(value_signal, "_parent_module", None) if value_signal is not None else None

                # Parent drives child input port.
                if (
                    target_signal is not None
                    and isinstance(target_owner, Module)
                    and target_owner is not mod
                ):
                    port_name = find_port_name(target_owner, target_signal)
                    if port_name is not None and port_name in target_owner._inputs:
                        info = ensure_submodule_info(target_owner)
                        info["inputs"][port_name] = value_expr
                        to_remove.append(i)
                        continue

                if direct_external_output_passthrough(stmt, mod):
                    to_remove.append(i)
                    continue

                # Parent consumes child output port.
                rewritten_value = rewrite_child_output_expr(value_expr, mod)
                if rewritten_value is not value_expr:
                    stmt.value = rewritten_value

            for i in reversed(to_remove):
                body.pop(i)

        normalize_body(mod._top_level)
        for body in mod._comb_blocks:
            normalize_body(body)

        for info in submodule_infos.values():
            submod = info["submod"]
            inst_name = info["inst_name"]
            if not any(id(existing) == id(submod) for _, existing in mod._submodules):
                mod._submodules.append((inst_name, submod))

            inst = explicit_by_submod.get(id(submod))
            if inst is None:
                port_map: Dict[str, object] = {}
                for pname in submod._inputs.keys():
                    if pname in info["inputs"]:
                        port_map[pname] = info["inputs"][pname]
                    elif hasattr(mod, pname):
                        val = getattr(mod, pname)
                        if isinstance(val, Signal):
                            port_map[pname] = val
                        elif isinstance(val, (int, Const)):
                            port_map[pname] = Const(int(val), 1) if isinstance(val, int) else val
                port_map.update(info["outputs"])
                mod._top_level.append(
                    SubmoduleInst(
                        inst_name,
                        submod,
                        infer_param_overrides(mod, submod),
                        port_map,
                    )
                )
            else:
                inst.port_map.update(info["inputs"])
                inst.port_map.update(info["outputs"])

        explicit_children = [stmt.module for stmt in mod._top_level if isinstance(stmt, SubmoduleInst)]
        for _, child in mod._submodules:
            visit_module(child, stack)
        for child in explicit_children:
            visit_module(child, stack)

    visit_module(normalized, set())
    return normalized


def _logic_not(expr):
    return UnaryExpr("!", expr)


def _logic_and(lhs, rhs):
    return BinaryExpr("&", lhs, rhs)


def _logic_or(lhs, rhs):
    return BinaryExpr("|", lhs, rhs)


def _register_implicit_signals(module) -> None:
    known = {}
    for table in (module._inputs, module._outputs, module._wires, module._regs):
        known.update({signal.name: signal for signal in table.values()})

    def register_signal(signal) -> None:
        name = getattr(signal, "name", "")
        if not name or name in known:
            return
        if getattr(signal, "_parent_module", None) is None:
            signal._parent_module = module
        if signal.__class__.__name__ == "Reg":
            module._regs[name] = signal
        else:
            module._wires[name] = signal
        known[name] = signal

    def visit_expr(expr) -> None:
        if expr is None or isinstance(expr, int):
            return
        if isinstance(expr, _SIGNAL_TYPES):
            register_signal(expr)
            ref_expr = getattr(expr, "_expr", None)
            if ref_expr is not None and ref_expr is not expr:
                visit_expr(ref_expr)
            return
        if isinstance(expr, _REF_TYPES):
            register_signal(expr.signal)
            return
        if isinstance(expr, _BINOP_TYPES):
            visit_expr(expr.lhs)
            visit_expr(expr.rhs)
            return
        if isinstance(expr, _UNARY_TYPES):
            visit_expr(expr.operand)
            return
        if isinstance(expr, _SLICE_TYPES):
            visit_expr(expr.operand)
            return
        if isinstance(expr, _PARTSELECT_TYPES):
            visit_expr(expr.operand)
            visit_expr(expr.offset)
            return
        if isinstance(expr, _BITSELECT_TYPES):
            visit_expr(expr.operand)
            visit_expr(expr.index)
            return
        if isinstance(expr, _CONCAT_TYPES):
            for operand in expr.operands:
                visit_expr(operand)
            return
        if isinstance(expr, _MUX_TYPES):
            visit_expr(expr.cond)
            visit_expr(expr.true_expr)
            visit_expr(expr.false_expr)
            return
        if isinstance(expr, _MEM_READ_TYPES):
            visit_expr(expr.addr)
            return
        if isinstance(expr, _ARRAY_READ_TYPES):
            visit_expr(expr.index)
            return

    def visit_stmt(stmt) -> None:
        if isinstance(stmt, _ASSIGN_TYPES):
            visit_expr(stmt.target)
            visit_expr(stmt.value)
            return
        if isinstance(stmt, _INDEXED_ASSIGN_TYPES):
            register_signal(stmt.target_signal)
            visit_expr(stmt.index)
            visit_expr(stmt.value)
            return
        if isinstance(stmt, _MEM_WRITE_TYPES):
            visit_expr(stmt.addr)
            visit_expr(stmt.value)
            return
        if isinstance(stmt, _ARRAY_WRITE_TYPES):
            visit_expr(stmt.index)
            visit_expr(stmt.value)
            return
        if isinstance(stmt, _IF_TYPES):
            visit_expr(stmt.cond)
            for body_stmt in stmt.then_body:
                visit_stmt(body_stmt)
            for body_stmt in stmt.else_body:
                visit_stmt(body_stmt)
            for elif_cond, elif_body in stmt.elif_bodies:
                visit_expr(elif_cond)
                for body_stmt in elif_body:
                    visit_stmt(body_stmt)
            return
        if isinstance(stmt, _SWITCH_TYPES):
            visit_expr(stmt.expr)
            for case_value, body in stmt.cases:
                visit_expr(case_value)
                for body_stmt in body:
                    visit_stmt(body_stmt)
            for body_stmt in stmt.default_body:
                visit_stmt(body_stmt)
            return
        if isinstance(stmt, _WHEN_TYPES):
            for cond, body in stmt.branches:
                if cond is not None:
                    visit_expr(cond)
                for body_stmt in body:
                    visit_stmt(body_stmt)

    for body in module._comb_blocks:
        for stmt in body:
            visit_stmt(stmt)
    for stmt in module._top_level:
        visit_stmt(stmt)
    for _, _, _, _, body in module._seq_blocks:
        for stmt in body:
            visit_stmt(stmt)
