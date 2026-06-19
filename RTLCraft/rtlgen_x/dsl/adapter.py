"""Adapters from the imported legacy DSL into rtlgen_x executable models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from rtlgen_x.dsl.legacy.core import (
    ArrayRead,
    ArrayWrite,
    Assign as LegacyAssign,
    BinOp,
    BitSelect,
    Concat,
    Const,
    Expr,
    IfNode,
    IndexedAssign,
    MemRead,
    MemWrite,
    Mux,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SwitchNode,
    UnaryOp,
    WhenNode,
    flatten_module,
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
    RtlgenMux = ()
    RtlgenPartSelect = ()
    RtlgenRef = ()
    RtlgenSignal = ()
    RtlgenSlice = ()
    RtlgenSwitchNode = ()
    RtlgenUnaryOp = ()
    RtlgenWhenNode = ()
    rtlgen_flatten_module = None
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
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


class LegacyLoweringError(ValueError):
    """Raised when a legacy DSL construct is outside the supported lowering subset."""


@dataclass(frozen=True)
class LegacyLoweringReport:
    """Summary of a legacy DSL lowering step."""

    source_module: str
    flattened_module: str
    signal_count: int
    assignment_count: int
    outputs_post_state: bool


@dataclass(frozen=True)
class LoweredLegacyModule:
    """Pair the lowered executable module with a small lowering report."""

    module: SimModule
    report: LegacyLoweringReport


def lower_legacy_module_to_sim(
    module,
    *,
    flatten: bool = True,
    outputs_post_state: bool = True,
) -> LoweredLegacyModule:
    """Lower a legacy DSL ``Module`` into the compiled-simulator executable model.

    The current bridge intentionally supports a focused subset:

    - flattened modules only
    - no behavioral/black-box callbacks
    - expressions expressible as ``Const``/``Ref``/``UnaryOp``/``BinOp``/``Mux`` and
      constant ``Slice``/single-bit ``BitSelect`` plus storage reads
    - sequential logic represented as explicit condition trees inside ``seq`` bodies
    - comb-read / seq-write ``Memory`` and ``Array`` storage
    """

    flatten_fn = _select_flatten_module(module)
    lowered_source = flatten_fn(module) if flatten else module
    _reject_unsupported_module_features(lowered_source)
    _register_implicit_signals(lowered_source)

    signals: List[SimSignal] = []
    signal_map: Dict[str, SimSignal] = {}

    def add_signal(source_signal, kind: str) -> None:
        sim_signal = SimSignal(
            name=source_signal.name,
            width=source_signal.width,
            kind=kind,
            signed=getattr(source_signal, "signed", False),
            init=(source_signal.init_value or 0),
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
        init = ()
        if getattr(source_memory, "init_data", None):
            init = tuple(int(value) for value in source_memory.init_data[: source_memory.depth])
            if len(init) < source_memory.depth:
                init = init + (0,) * (source_memory.depth - len(init))
        elif getattr(source_memory, "init_zero", False):
            init = tuple(0 for _ in range(source_memory.depth))
        sim_memory = Memory(
            name=source_memory.name,
            width=source_memory.width,
            depth=source_memory.depth,
            init=init,
        )
        memories.append(sim_memory)
        memory_names[source_memory.name] = sim_memory
    for source_array in lowered_source._arrays.values():
        sim_memory = Memory(
            name=source_array.name,
            width=source_array.width,
            depth=source_array.depth,
        )
        memories.append(sim_memory)
        memory_names[source_array.name] = sim_memory

    assignments: List[Assignment] = []
    memory_writes: List[MemoryWrite] = []
    for body in lowered_source._comb_blocks:
        env = _LoweringEnv(signal_map, memory_names)
        _lower_stmt_list(body, phase="comb", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())

    for index, seq_item in enumerate(lowered_source._seq_blocks):
        clk, rst, reset_async, reset_active_low, body = seq_item
        if reset_async:
            raise LegacyLoweringError("async reset seq blocks are not yet supported")
        if reset_active_low:
            raise LegacyLoweringError("active-low reset seq blocks are not yet supported")
        if clk is None:
            raise LegacyLoweringError("sequential block is missing clock")
        env = _LoweringEnv(signal_map, memory_names)
        _lower_stmt_list(body, phase="seq", env=env)
        assignments.extend(env.finalize_phase())
        memory_writes.extend(env.finalize_memory_writes())

    sim_module = SimModule(
        name=lowered_source.name,
        signals=tuple(signals),
        assignments=tuple(assignments),
        outputs=tuple(lowered_source._outputs.keys()),
        memories=tuple(memories),
        memory_writes=tuple(memory_writes),
        reset_signal=None,
        outputs_post_state=outputs_post_state,
    )
    report = LegacyLoweringReport(
        source_module=module.name,
        flattened_module=lowered_source.name,
        signal_count=len(signals),
        assignment_count=len(assignments) + len(memory_writes),
        outputs_post_state=outputs_post_state,
    )
    return LoweredLegacyModule(module=sim_module, report=report)


def build_compiled_simulator_from_legacy(
    module,
    *,
    flatten: bool = True,
    outputs_post_state: bool = True,
    builder: Optional[CppBackendScaffold] = None,
    build_dir: Optional[Path | str] = None,
) -> CompiledSimulator:
    """Lower a legacy DSL module and build the compiled simulator runtime."""

    lowered = lower_legacy_module_to_sim(
        module,
        flatten=flatten,
        outputs_post_state=outputs_post_state,
    )
    runtime_builder = builder if builder is not None else CppBackendScaffold()
    return runtime_builder.build(lowered.module, build_dir=build_dir)


def _reject_unsupported_module_features(module) -> None:
    if module._submodules:
        raise LegacyLoweringError("legacy lowering expects a flattened module")
    if getattr(module, "_beh_func", None) is not None:
        raise LegacyLoweringError("behavioral callback modules are not supported")
    if module._top_level:
        raise LegacyLoweringError("top-level statements are not yet supported")
    if module._latch_blocks:
        raise LegacyLoweringError("latch blocks are not yet supported")
    if module._init_blocks:
        raise LegacyLoweringError("initial blocks are not yet supported")


class _LoweringEnv:
    def __init__(self, signal_map: Mapping[str, SimSignal], memory_map: Mapping[str, Memory]):
        self._signal_map = signal_map
        self._memory_map = memory_map
        self._assigned: MutableMapping[str, object] = {}
        self._memory_writes: List[MemoryWrite] = []
        self._phase: Optional[str] = None
        self._path_guard = ConstExpr(1, 1)

    def read(self, signal_name: str):
        signal = self._signal_map[signal_name]
        if self._phase == "comb" and signal.kind in {"wire", "output"} and signal_name in self._assigned:
            return self._assigned[signal_name]
        return SignalRef(signal_name)

    def read_memory(self, memory_name: str, addr_expr):
        memory = self._memory_map.get(memory_name)
        if memory is None:
            raise LegacyLoweringError(f"expression references unknown memory '{memory_name}'")
        return MemoryReadExpr(memory_name, addr_expr)

    def assign(self, target, expr, *, phase: str) -> None:
        signal = self._signal_map.get(target.name)
        if signal is None:
            raise LegacyLoweringError(f"assignment targets unknown signal '{target.name}'")
        if phase == "comb" and signal.kind not in {"wire", "output"}:
            raise LegacyLoweringError(
                f"combinational lowering only supports wire/output targets, got '{target.name}'"
            )
        if phase == "seq" and signal.kind != "state":
            raise LegacyLoweringError(
                f"sequential lowering only supports reg targets, got '{target.name}'"
            )
        self._assigned[target.name] = expr
        self._phase = phase

    def write_memory(self, memory_name: str, addr_expr, value_expr, *, phase: str) -> None:
        memory = self._memory_map.get(memory_name)
        if memory is None:
            raise LegacyLoweringError(f"memory write targets unknown memory '{memory_name}'")
        if phase != "seq":
            raise LegacyLoweringError(
                f"storage write lowering only supports sequential phase, got write to '{memory_name}' in {phase}"
            )
        enable = self._path_enable()
        self._memory_writes.append(
            MemoryWrite(memory_name, addr_expr, value_expr, enable=enable)
        )
        self._phase = phase

    def branch(self) -> "_LoweringEnv":
        child = _LoweringEnv(self._signal_map, self._memory_map)
        child._assigned = dict(self._assigned)
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
            if _expr_equal_compiled(then_value, else_value):
                self._assigned[name] = then_value
            else:
                self._assigned[name] = MuxExpr(cond, then_value, else_value)
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
            Assignment(target=name, expr=expr, phase=self._phase)
            for name, expr in self._assigned.items()
        ]

    def finalize_memory_writes(self) -> List[MemoryWrite]:
        return list(self._memory_writes)

    def _path_enable(self):
        return self._path_guard


def _lower_stmt_list(stmts: Iterable[object], *, phase: str, env: _LoweringEnv) -> None:
    env._phase = phase
    for stmt in stmts:
        if isinstance(stmt, _ASSIGN_TYPES):
            _lower_assign(stmt.target, stmt.value, phase=phase, env=env)
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
        raise LegacyLoweringError(f"unsupported statement type '{stmt_name}'")


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
        raise LegacyLoweringError(f"unsupported switch kind '{stmt.kind}'")
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
            raise LegacyLoweringError(f"unsupported unary op '{expr.op}'")
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
            raise LegacyLoweringError(f"unsupported binary op '{expr.op}'")
        return BinaryExpr(expr.op, _lower_expr(expr.lhs, env), _lower_expr(expr.rhs, env))
    if isinstance(expr, _MUX_TYPES):
        return MuxExpr(
            _lower_expr(expr.cond, env),
            _lower_expr(expr.true_expr, env),
            _lower_expr(expr.false_expr, env),
        )
    if isinstance(expr, _SLICE_TYPES):
        if not isinstance(expr.hi, int) or not isinstance(expr.lo, int):
            raise LegacyLoweringError("dynamic slices are not yet supported")
        operand = _lower_expr(expr.operand, env)
        if expr.hi == expr.lo:
            return BinaryExpr(
                "&",
                BinaryExpr(">>", operand, ConstExpr(expr.lo, max(expr.lo.bit_length(), 1))),
                ConstExpr(1, 1),
            )
        width = expr.hi - expr.lo + 1
        return BinaryExpr(
            "&",
            BinaryExpr(">>", operand, ConstExpr(expr.lo, max(expr.lo.bit_length(), 1))),
            ConstExpr((1 << width) - 1, width),
        )
    if isinstance(expr, _BITSELECT_TYPES):
        operand = _lower_expr(expr.operand, env)
        index = _lower_expr(expr.index, env)
        return BinaryExpr("&", BinaryExpr(">>", operand, index), ConstExpr(1, 1))
    if isinstance(expr, _CONCAT_TYPES):
        operands = list(expr.operands)
        if not operands:
            raise LegacyLoweringError("empty concat is not supported")
        acc = _lower_expr(operands[0], env)
        running_width = operands[0].width
        for operand in operands[1:]:
            part = _lower_expr(operand, env)
            acc = BinaryExpr(
                "|",
                BinaryExpr("<<", acc, ConstExpr(operand.width, max(operand.width.bit_length(), 1))),
                part,
            )
            running_width += operand.width
        return acc
    raise LegacyLoweringError(f"unsupported expression type '{type(expr).__name__}'")


def _lower_assign(target, value, *, phase: str, env: _LoweringEnv) -> None:
    if isinstance(target, _SIGNAL_TYPES):
        env.assign(target, _lower_expr(value, env), phase=phase)
        return
    if isinstance(target, _SLICE_TYPES):
        _lower_slice_assign(target, value, phase=phase, env=env)
        return
    if isinstance(target, _BITSELECT_TYPES):
        _lower_bitselect_assign(target, value, phase=phase, env=env)
        return
    if isinstance(target, _PARTSELECT_TYPES):
        _lower_partselect_assign(target, value, phase=phase, env=env)
        return
    raise LegacyLoweringError(
        f"lowering only supports signal and bit-range assignment targets, got {type(target).__name__}"
    )


def _lower_indexed_assign(stmt: IndexedAssign, *, phase: str, env: _LoweringEnv) -> None:
    target_expr = BitSelect(Ref(stmt.target_signal), stmt.index)
    _lower_bitselect_assign(target_expr, stmt.value, phase=phase, env=env)


def _lower_memory_write(stmt: MemWrite, *, phase: str, env: _LoweringEnv) -> None:
    env.write_memory(
        stmt.mem_name,
        _lower_expr(stmt.addr, env),
        _lower_expr(stmt.value, env),
        phase=phase,
    )


def _lower_array_write(stmt: ArrayWrite, *, phase: str, env: _LoweringEnv) -> None:
    env.write_memory(
        stmt.array_name,
        _lower_expr(stmt.index, env),
        _lower_expr(stmt.value, env),
        phase=phase,
    )


def _lower_slice_assign(target: Slice, value, *, phase: str, env: _LoweringEnv) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise LegacyLoweringError("slice assignment must target a signal")
    if not isinstance(target.hi, int) or not isinstance(target.lo, int):
        raise LegacyLoweringError("dynamic slice assignment is not yet supported")
    base_signal = target.operand.signal
    replacement = _replace_bit_range_expr(
        env.read(base_signal.name),
        target.lo,
        target.width,
        _lower_expr(value, env),
        base_signal.width,
    )
    env.assign(base_signal, replacement, phase=phase)


def _lower_bitselect_assign(target: BitSelect, value, *, phase: str, env: _LoweringEnv) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise LegacyLoweringError("bit-select assignment must target a signal")
    base_signal = target.operand.signal
    index = _const_int(target.index)
    if index is None:
        replacement = _replace_dynamic_bit_expr(
            env.read(base_signal.name),
            _lower_expr(target.index, env),
            _lower_expr(value, env),
            base_signal.width,
        )
    else:
        replacement = _replace_bit_range_expr(
            env.read(base_signal.name),
            index,
            1,
            _lower_expr(value, env),
            base_signal.width,
        )
    env.assign(base_signal, replacement, phase=phase)


def _lower_partselect_assign(target: PartSelect, value, *, phase: str, env: _LoweringEnv) -> None:
    if not isinstance(target.operand, _REF_TYPES):
        raise LegacyLoweringError("part-select assignment must target a signal")
    base_signal = target.operand.signal
    offset = _const_int(target.offset)
    if offset is None:
        raise LegacyLoweringError("dynamic part-select assignment is not yet supported")
    replacement = _replace_bit_range_expr(
        env.read(base_signal.name),
        offset,
        target.width,
        _lower_expr(value, env),
        base_signal.width,
    )
    env.assign(base_signal, replacement, phase=phase)


def _replace_bit_range_expr(base, lo: int, width: int, value, base_width: int):
    if width < 1:
        raise LegacyLoweringError("bit range width must be positive")
    if lo < 0 or lo + width > base_width:
        raise LegacyLoweringError("bit range assignment is outside the target signal width")
    range_mask = ((1 << width) - 1) << lo
    keep_mask = ((1 << base_width) - 1) ^ range_mask
    cleared = BinaryExpr("&", base, ConstExpr(keep_mask, base_width))
    shifted = BinaryExpr("<<", MaskExpr(value, width), ConstExpr(lo, max(lo.bit_length(), 1)))
    return MaskExpr(BinaryExpr("|", cleared, shifted), base_width)


def _replace_dynamic_bit_expr(base, index, value, base_width: int):
    one = ConstExpr(1, 1)
    dynamic_mask = BinaryExpr("<<", one, index)
    keep_mask = BinaryExpr("^", ConstExpr((1 << base_width) - 1, base_width), dynamic_mask)
    cleared = BinaryExpr("&", base, keep_mask)
    shifted = BinaryExpr("<<", MaskExpr(value, 1), index)
    return MaskExpr(BinaryExpr("|", cleared, shifted), base_width)


def _const_int(expr) -> Optional[int]:
    if isinstance(expr, int):
        return expr
    if isinstance(expr, _CONST_TYPES):
        return int(expr.value)
    return None


def _expr_equal_compiled(lhs, rhs) -> bool:
    return repr(lhs) == repr(rhs)


_ASSIGN_TYPES = (LegacyAssign,) + ((RtlgenAssign,) if RtlgenAssign else ())
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
    module_name = module.__class__.__module__
    if module_name.startswith("rtlgen.") and rtlgen_flatten_module is not None:
        return rtlgen_flatten_module
    return flatten_module


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
    for _, _, _, _, body in module._seq_blocks:
        for stmt in body:
            visit_stmt(stmt)
