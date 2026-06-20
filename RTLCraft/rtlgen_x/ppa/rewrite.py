"""Lightweight rewrite proposals derived from PPA results."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from rtlgen_x.ppa.advisor import PpaReport, analyze_module_ppa
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    CppBackendScaffold,
    ConstExpr,
    MaskExpr,
    MemoryReadExpr,
    MuxExpr,
    PythonSimulator,
    Signal,
    SignalRef,
    SimModule,
    SimulatorParityReport,
    TraceMismatch,
    UnaryExpr,
    capture_execution_trace,
    compare_python_and_compiled,
)


@dataclass(frozen=True)
class RewriteEdit:
    kind: str
    target: str
    details: Mapping[str, object]


@dataclass(frozen=True)
class RewriteProposal:
    module_name: str
    summary: str
    rationale: str
    source_assignment: str
    edits: Tuple[RewriteEdit, ...]


@dataclass(frozen=True)
class RewriteEvaluation:
    proposal: RewriteProposal
    original_depth: int
    rewritten_depth: int
    depth_delta: int
    original_stats: object
    rewritten_stats: object


@dataclass(frozen=True)
class RewriteValidationReport:
    proposal: RewriteProposal
    evaluation: RewriteEvaluation
    vectors: Tuple[Mapping[str, int], ...]
    behavior_preserved: bool
    output_mismatches: Tuple[TraceMismatch, ...]
    rewritten_parity: Optional[SimulatorParityReport]


def derive_rewrite_proposals(
    module: SimModule,
    report: PpaReport,
) -> Tuple[RewriteProposal, ...]:
    proposals: List[RewriteProposal] = []
    for candidate in report.transform_candidates:
        if candidate.category != "timing":
            continue
        proposal = _timing_pipeline_proposal(module, candidate.name, candidate.rationale)
        if proposal is not None:
            proposals.append(proposal)
    return tuple(proposals)


def apply_rewrite_proposal(module: SimModule, proposal: RewriteProposal) -> SimModule:
    signals = list(module.signals)
    assignments = list(module.assignments)
    for edit in proposal.edits:
        if edit.kind == "insert_wire":
            if any(signal.name == edit.target for signal in signals):
                continue
            signals.append(
                Signal(
                    name=edit.target,
                    width=int(edit.details["width"]),
                    kind="wire",
                    signed=bool(edit.details.get("signed", False)),
                )
            )
            continue
        if edit.kind == "insert_state":
            if any(signal.name == edit.target for signal in signals):
                continue
            signals.append(
                Signal(
                    name=edit.target,
                    width=int(edit.details["width"]),
                    kind="state",
                    init=int(edit.details.get("init", 0)),
                    signed=bool(edit.details.get("signed", False)),
                )
            )
            continue
        if edit.kind == "append_assignment":
            assignments.append(
                Assignment(
                    target=edit.target,
                    expr=edit.details["expr"],
                    phase=str(edit.details.get("phase", "comb")),
                )
            )
            continue
        if edit.kind == "replace_assignment_expr":
            phase = str(edit.details.get("phase", "comb"))
            original_expr = edit.details["original_expr"]
            replacement_expr = edit.details["replacement_expr"]
            replaced = False
            updated_assignments = []
            for assignment in assignments:
                if (
                    not replaced
                    and assignment.target == edit.target
                    and assignment.phase == phase
                    and assignment.expr == original_expr
                ):
                    updated_assignments.append(
                        Assignment(
                            target=assignment.target,
                            expr=replacement_expr,
                            phase=assignment.phase,
                        )
                    )
                    replaced = True
                else:
                    updated_assignments.append(assignment)
            assignments = updated_assignments
            continue
    return SimModule(
        name=module.name,
        signals=tuple(signals),
        assignments=tuple(assignments),
        outputs=module.outputs,
        memories=module.memories,
        memory_writes=module.memory_writes,
        reset_signal=module.reset_signal,
        outputs_post_state=module.outputs_post_state,
    )


def evaluate_rewrite_proposal(
    module: SimModule,
    proposal: RewriteProposal,
) -> RewriteEvaluation:
    original_stats = analyze_module_ppa(module)
    rewritten = apply_rewrite_proposal(module, proposal)
    rewritten_stats = analyze_module_ppa(rewritten)
    original_assignment = _find_assignment(module.assignments, proposal.source_assignment)
    rewritten_assignment = _find_assignment(rewritten.assignments, proposal.source_assignment)
    if original_assignment is None or rewritten_assignment is None:
        raise ValueError(f"unable to locate rewritten assignment '{proposal.source_assignment}'")
    original_depth = _expr_depth(original_assignment.expr)
    rewritten_depth = _expr_depth(rewritten_assignment.expr)
    return RewriteEvaluation(
        proposal=proposal,
        original_depth=original_depth,
        rewritten_depth=rewritten_depth,
        depth_delta=rewritten_depth - original_depth,
        original_stats=original_stats,
        rewritten_stats=rewritten_stats,
    )


def validate_rewrite_proposal(
    module: SimModule,
    proposal: RewriteProposal,
    *,
    vectors: Optional[Sequence[Mapping[str, int]]] = None,
    validation_cycles: int = 8,
    seed: int = 1234,
    include_compiled_parity: bool = False,
    builder: Optional[CppBackendScaffold] = None,
    build_dir: Optional[str] = None,
) -> RewriteValidationReport:
    evaluation = evaluate_rewrite_proposal(module, proposal)
    rewritten = apply_rewrite_proposal(module, proposal)
    resolved_vectors = _resolve_validation_vectors(
        module,
        vectors=vectors,
        validation_cycles=validation_cycles,
        seed=seed,
    )
    original_trace = capture_execution_trace(
        PythonSimulator(module),
        resolved_vectors,
        module_name=module.name,
        backend="PythonSimulator",
    )
    rewritten_trace = capture_execution_trace(
        PythonSimulator(rewritten),
        resolved_vectors,
        module_name=rewritten.name,
        backend="PythonSimulator",
    )
    output_mismatches = _compare_output_traces(original_trace.steps, rewritten_trace.steps)
    rewritten_parity = None
    if include_compiled_parity:
        rewritten_parity = compare_python_and_compiled(
            rewritten,
            resolved_vectors,
            builder=builder,
            build_dir=build_dir,
        )
    return RewriteValidationReport(
        proposal=proposal,
        evaluation=evaluation,
        vectors=resolved_vectors,
        behavior_preserved=not output_mismatches,
        output_mismatches=output_mismatches,
        rewritten_parity=rewritten_parity,
    )


def _timing_pipeline_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    signal_map = module.signal_map()
    target_assignment = max(
        module.assignments,
        key=lambda assignment: _expr_depth(assignment.expr),
        default=None,
    )
    if target_assignment is None:
        return None
    deepest_expr = _deepest_binary_subexpr(target_assignment.expr)
    if deepest_expr is None:
        return None
    temp_wire = f"{target_assignment.target}_pipe_w"
    temp_state = f"{target_assignment.target}_pipe_q"
    replacement_expr = _replace_expr_once(target_assignment.expr, deepest_expr, SignalRef(temp_state))
    if replacement_expr is None:
        return None
    expr_width = _infer_expr_width(deepest_expr, signal_map)
    expr_signed = _infer_expr_signed(deepest_expr, signal_map)
    state_init = _zero_init_for_width(expr_width)
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment=target_assignment.target,
        edits=(
            RewriteEdit(
                kind="insert_wire",
                target=temp_wire,
                details={"width": expr_width, "signed": expr_signed},
            ),
            RewriteEdit(
                kind="insert_state",
                target=temp_state,
                details={"width": expr_width, "signed": expr_signed, "init": state_init},
            ),
            RewriteEdit(
                kind="append_assignment",
                target=temp_wire,
                details={"expr": deepest_expr, "phase": "comb"},
            ),
            RewriteEdit(
                kind="append_assignment",
                target=temp_state,
                details={"expr": SignalRef(temp_wire), "phase": "seq"},
            ),
            RewriteEdit(
                kind="replace_assignment_expr",
                target=target_assignment.target,
                details={
                    "phase": target_assignment.phase,
                    "original_expr": target_assignment.expr,
                    "replacement_expr": replacement_expr,
                },
            ),
        ),
    )


def _resolve_validation_vectors(
    module: SimModule,
    *,
    vectors: Optional[Sequence[Mapping[str, int]]],
    validation_cycles: int,
    seed: int,
) -> Tuple[Mapping[str, int], ...]:
    if vectors is not None:
        return tuple({name: int(value) for name, value in dict(vector).items()} for vector in vectors)
    if validation_cycles < 1:
        raise ValueError("validation_cycles must be positive")
    rng = random.Random(seed)
    signal_map = module.signal_map()
    input_names = tuple(signal.name for signal in module.signals if signal.kind == "input")
    generated = []
    for _ in range(validation_cycles):
        row = {}
        for name in input_names:
            if module.reset_signal is not None and name == module.reset_signal:
                row[name] = 0
                continue
            if name.startswith("clk"):
                row[name] = 0
                continue
            width = min(signal_map[name].width, 16)
            row[name] = rng.randrange(1 << width)
        generated.append(row)
    return tuple(generated)


def _compare_output_traces(
    original_steps,
    rewritten_steps,
) -> Tuple[TraceMismatch, ...]:
    mismatches = []
    for original_step, rewritten_step in zip(original_steps, rewritten_steps):
        for name, expected in original_step.outputs.items():
            actual = int(rewritten_step.outputs.get(name, 0))
            if actual != int(expected):
                mismatches.append(
                    TraceMismatch(
                        cycle=original_step.cycle,
                        kind="output",
                        name=name,
                        expected=int(expected),
                        actual=actual,
                    )
                )
    return tuple(mismatches)


def _find_assignment(
    assignments: Sequence[Assignment],
    target: str,
) -> Optional[Assignment]:
    for assignment in assignments:
        if assignment.target == target and assignment.phase == "comb":
            return assignment
    for assignment in assignments:
        if assignment.target == target:
            return assignment
    return None


def _deepest_binary_subexpr(expr):
    candidates: List[object] = []

    def visit(node):
        if isinstance(node, BinaryExpr):
            candidates.append(node)
            visit(node.lhs)
            visit(node.rhs)
            return
        if isinstance(node, UnaryExpr):
            visit(node.value)
            return
        if isinstance(node, MaskExpr):
            visit(node.value)
            return
        if isinstance(node, MuxExpr):
            visit(node.cond)
            visit(node.when_true)
            visit(node.when_false)
            return
        if isinstance(node, MemoryReadExpr):
            visit(node.addr)

    visit(expr)
    candidates = [candidate for candidate in candidates if _expr_depth(candidate) > 1]
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: (_expr_depth(candidate), _expr_node_count(candidate)), reverse=True)
    return candidates[0]


def _replace_expr_once(expr, needle, replacement):
    if expr == needle:
        return replacement
    if isinstance(expr, BinaryExpr):
        lhs = _replace_expr_once(expr.lhs, needle, replacement)
        if lhs is not None:
            return BinaryExpr(expr.op, lhs, expr.rhs)
        rhs = _replace_expr_once(expr.rhs, needle, replacement)
        if rhs is not None:
            return BinaryExpr(expr.op, expr.lhs, rhs)
        return None
    if isinstance(expr, UnaryExpr):
        child = _replace_expr_once(expr.value, needle, replacement)
        return None if child is None else UnaryExpr(expr.op, child)
    if isinstance(expr, MaskExpr):
        child = _replace_expr_once(expr.value, needle, replacement)
        return None if child is None else MaskExpr(child, expr.width)
    if isinstance(expr, MuxExpr):
        cond = _replace_expr_once(expr.cond, needle, replacement)
        if cond is not None:
            return MuxExpr(cond, expr.when_true, expr.when_false)
        when_true = _replace_expr_once(expr.when_true, needle, replacement)
        if when_true is not None:
            return MuxExpr(expr.cond, when_true, expr.when_false)
        when_false = _replace_expr_once(expr.when_false, needle, replacement)
        if when_false is not None:
            return MuxExpr(expr.cond, expr.when_true, when_false)
        return None
    if isinstance(expr, MemoryReadExpr):
        addr = _replace_expr_once(expr.addr, needle, replacement)
        return None if addr is None else MemoryReadExpr(expr.memory, addr)
    return None


def _expr_depth(expr) -> int:
    if isinstance(expr, (ConstExpr, SignalRef, MemoryReadExpr)):
        return 1
    if isinstance(expr, MaskExpr):
        return _expr_depth(expr.value) + 1
    if isinstance(expr, UnaryExpr):
        return _expr_depth(expr.value) + 1
    if isinstance(expr, BinaryExpr):
        return max(_expr_depth(expr.lhs), _expr_depth(expr.rhs)) + 1
    if isinstance(expr, MuxExpr):
        return max(_expr_depth(expr.cond), _expr_depth(expr.when_true), _expr_depth(expr.when_false)) + 1
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _expr_node_count(expr) -> int:
    if isinstance(expr, (ConstExpr, SignalRef)):
        return 1
    if isinstance(expr, MemoryReadExpr):
        return 1 + _expr_node_count(expr.addr)
    if isinstance(expr, MaskExpr):
        return 1 + _expr_node_count(expr.value)
    if isinstance(expr, UnaryExpr):
        return 1 + _expr_node_count(expr.value)
    if isinstance(expr, BinaryExpr):
        return 1 + _expr_node_count(expr.lhs) + _expr_node_count(expr.rhs)
    if isinstance(expr, MuxExpr):
        return 1 + _expr_node_count(expr.cond) + _expr_node_count(expr.when_true) + _expr_node_count(expr.when_false)
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _infer_expr_width(expr, signal_map: Mapping[str, Signal]) -> int:
    if isinstance(expr, ConstExpr):
        return expr.width
    if isinstance(expr, SignalRef):
        return signal_map[expr.name].width
    if isinstance(expr, MemoryReadExpr):
        return 64
    if isinstance(expr, MaskExpr):
        return expr.width
    if isinstance(expr, UnaryExpr):
        if expr.op == "!":
            return 1
        return _infer_expr_width(expr.value, signal_map)
    if isinstance(expr, BinaryExpr):
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            return 1
        return max(_infer_expr_width(expr.lhs, signal_map), _infer_expr_width(expr.rhs, signal_map))
    if isinstance(expr, MuxExpr):
        return max(_infer_expr_width(expr.when_true, signal_map), _infer_expr_width(expr.when_false, signal_map))
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _infer_expr_signed(expr, signal_map: Mapping[str, Signal]) -> bool:
    if isinstance(expr, ConstExpr):
        return False
    if isinstance(expr, SignalRef):
        return signal_map[expr.name].signed
    if isinstance(expr, MemoryReadExpr):
        return False
    if isinstance(expr, MaskExpr):
        return False
    if isinstance(expr, UnaryExpr):
        if expr.op == "$signed":
            return True
        if expr.op in {"$unsigned", "!"}:
            return False
        return _infer_expr_signed(expr.value, signal_map)
    if isinstance(expr, BinaryExpr):
        if expr.op in {"==", "!=", "<", "<=", ">", ">="}:
            return False
        return _infer_expr_signed(expr.lhs, signal_map) or _infer_expr_signed(expr.rhs, signal_map)
    if isinstance(expr, MuxExpr):
        return _infer_expr_signed(expr.when_true, signal_map) and _infer_expr_signed(expr.when_false, signal_map)
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _zero_init_for_width(width: int) -> int:
    if width < 1:
        raise ValueError("width must be positive")
    return 0
