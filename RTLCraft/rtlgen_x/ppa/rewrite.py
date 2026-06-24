"""Lightweight rewrite proposals derived from PPA results."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from rtlgen_x.ppa.advisor import PpaReport, _analyze_executable_module_ppa
from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    CppBackendScaffold,
    ConstExpr,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
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
    applicability: str
    applicability_reason: Optional[str]
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
    seen_keys = set()
    for candidate in report.transform_candidates:
        proposal = None
        if candidate.suggested_knob in {"storage_impl", "table_layout", "metadata_layout", "payload_gating"}:
            proposal = _storage_rewrite_proposal(module, candidate)
        elif candidate.suggested_knob == "control_partition":
            proposal = _control_partition_rewrite_proposal(module, candidate)
        elif candidate.category == "timing":
            preferred_target = None
            preferred_ops = None
            if candidate.suggested_value in {
                "split_operands_product_accumulate",
                "retime_product_stages_keep_valid_shell",
                "tile_or_share_wide_multipliers",
            }:
                preferred_target = _candidate_target_assignment(candidate.target, module.name)
                preferred_ops = ("*",)
            proposal = _timing_pipeline_proposal(
                module,
                candidate.name,
                candidate.rationale,
                preferred_target=preferred_target,
                preferred_ops=preferred_ops,
            )
        if proposal is not None:
            key = (proposal.summary, proposal.source_assignment)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            proposals.append(proposal)
    return tuple(proposals)


def apply_rewrite_proposal(module: SimModule, proposal: RewriteProposal) -> SimModule:
    if proposal.applicability != "direct_apply":
        reason = proposal.applicability_reason or "proposal requires manual completion"
        raise ValueError(
            f"rewrite proposal '{proposal.summary}' is '{proposal.applicability}' and cannot be "
            f"applied directly: {reason}"
        )
    signals = list(module.signals)
    assignments = list(module.assignments)
    memories = list(module.memories)
    memory_writes = list(module.memory_writes)
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
        if edit.kind == "insert_memory":
            if any(memory.name == edit.target for memory in memories):
                continue
            memories.append(
                Memory(
                    name=edit.target,
                    width=int(edit.details["width"]),
                    depth=int(edit.details["depth"]),
                    init=tuple(int(value) for value in edit.details.get("init", ())),
                    read_during_write=str(edit.details.get("read_during_write", "write_first")),
                    read_ports=int(edit.details.get("read_ports", 1)),
                    write_ports=int(edit.details.get("write_ports", 1)),
                    read_style=str(edit.details.get("read_style", "async")),
                    read_latency=int(edit.details.get("read_latency", 0)),
                    byte_enable_granularity=edit.details.get("byte_enable_granularity"),
                )
            )
            continue
        if edit.kind == "append_memory_write":
            memory_writes.append(
                MemoryWrite(
                    memory=edit.target,
                    addr=edit.details["addr"],
                    value=edit.details["value"],
                    enable=edit.details.get("enable", ConstExpr(1, 1)),
                    clock_domain=edit.details.get("clock_domain"),
                    byte_enable=edit.details.get("byte_enable"),
                )
            )
            continue
    return SimModule(
        name=module.name,
        signals=tuple(signals),
        assignments=tuple(assignments),
        outputs=module.outputs,
        memories=tuple(memories),
        memory_writes=tuple(memory_writes),
        reset_signal=module.reset_signal,
        outputs_post_state=module.outputs_post_state,
    )


def evaluate_rewrite_proposal(
    module: SimModule,
    proposal: RewriteProposal,
) -> RewriteEvaluation:
    original_stats = _analyze_executable_module_ppa(module)
    rewritten = apply_rewrite_proposal(module, proposal)
    rewritten_stats = _analyze_executable_module_ppa(rewritten)
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
    if proposal.applicability != "direct_apply":
        reason = proposal.applicability_reason or "proposal requires manual completion"
        raise ValueError(
            f"rewrite proposal '{proposal.summary}' is '{proposal.applicability}' and cannot be "
            f"validated directly: {reason}"
        )
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
    *,
    preferred_target: Optional[str] = None,
    preferred_ops: Optional[Sequence[str]] = None,
) -> Optional[RewriteProposal]:
    signal_map = module.signal_map()
    target_assignment = _find_assignment(module.assignments, preferred_target) if preferred_target else None
    if target_assignment is None:
        target_assignment = max(
            module.assignments,
            key=lambda assignment: _expr_depth(assignment.expr),
            default=None,
        )
    if target_assignment is None:
        return None
    deepest_expr = _deepest_binary_subexpr(target_assignment.expr, preferred_ops=preferred_ops)
    if deepest_expr is None and preferred_ops is not None:
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
        applicability="direct_apply",
        applicability_reason=None,
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


def _storage_rewrite_proposal(
    module: SimModule,
    candidate,
) -> Optional[RewriteProposal]:
    suggested_value = getattr(candidate, "suggested_value", None)
    if suggested_value == "register_file_to_ram_wrapper":
        return _register_file_wrapper_proposal(module, candidate.name, candidate.rationale)
    if suggested_value == "compare_ram_wrapper_vs_flops":
        return _dual_port_ram_banking_proposal(module, candidate.name, candidate.rationale)
    if suggested_value == "pack_rows_or_share_banks":
        return _lut_packed_rows_proposal(module, candidate.name, candidate.rationale)
    if suggested_value == "update_payload_only_on_handshake":
        return _handshake_payload_gating_proposal(module, candidate.name, candidate.rationale)
    if suggested_value == "bundle_queue_sideband_fields":
        return _queue_sideband_bundle_proposal(module, candidate.name, candidate.rationale)
    return None


def _control_partition_rewrite_proposal(
    module: SimModule,
    candidate,
) -> Optional[RewriteProposal]:
    suggested_value = getattr(candidate, "suggested_value", None)
    if suggested_value == "split_capture_and_response_state":
        return _register_bank_control_partition_proposal(module, candidate.name, candidate.rationale)
    return None


def _register_file_wrapper_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    row_states = sorted(
        (signal for signal in module.signals if signal.kind == "state" and signal.name.startswith("rf_")),
        key=lambda signal: int(signal.name.split("_")[-1]),
    )
    if not row_states:
        return None
    read_addr_names = _sorted_indexed_names(module.signals, prefix="rd_addr_", kind="input")
    read_data_names = _sorted_indexed_names(module.signals, prefix="rd_data_", kind="output")
    wr_addr_names = _sorted_indexed_names(module.signals, prefix="wr_addr_", kind="input")
    wr_data_names = _sorted_indexed_names(module.signals, prefix="wr_data_", kind="input")
    wr_en_names = _sorted_indexed_names(module.signals, prefix="wr_en_", kind="input")
    if not read_addr_names or not read_data_names or not wr_addr_names:
        return None
    depth = len(row_states)
    width = row_states[0].width
    mem_name = "rf_wrap"
    edits = [
        RewriteEdit(
            kind="insert_memory",
            target=mem_name,
            details={
                "width": width,
                "depth": depth,
                "init": tuple(int(signal.init) for signal in row_states),
                "read_ports": len(read_addr_names),
                "write_ports": len(wr_addr_names),
                "read_style": "async",
                "read_latency": 0,
            },
        )
    ]
    for rd_addr, rd_data in zip(read_addr_names, read_data_names):
        assignment = _find_assignment(module.assignments, rd_data)
        if assignment is None:
            continue
        edits.append(
            RewriteEdit(
                kind="replace_assignment_expr",
                target=rd_data,
                details={
                    "phase": assignment.phase,
                    "original_expr": assignment.expr,
                    "replacement_expr": MemoryReadExpr(mem_name, SignalRef(rd_addr)),
                },
            )
        )
    for wr_addr, wr_data, wr_en in zip(wr_addr_names, wr_data_names, wr_en_names):
        edits.append(
            RewriteEdit(
                kind="append_memory_write",
                target=mem_name,
                details={
                    "addr": SignalRef(wr_addr),
                    "value": SignalRef(wr_data),
                    "enable": SignalRef(wr_en),
                },
            )
        )
    if len(edits) == 1:
        return None
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment=read_data_names[0],
        applicability="scaffold_only",
        applicability_reason=(
            "current executable memory subset does not model this multi-read or multi-write "
            "register-file wrapper directly; complete the wrapper manually before simulation"
        ),
        edits=tuple(edits),
    )


def _dual_port_ram_banking_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    memory = module.memories[0] if module.memories else None
    if memory is None or memory.depth < 2:
        return None
    bank_depth = max((memory.depth + 1) // 2, 1)
    local_width = max((bank_depth - 1).bit_length(), 1)
    bank0_name = f"{memory.name}_bank0"
    bank1_name = f"{memory.name}_bank1"
    bank0_init, bank1_init = _split_memory_init(memory.init, bank_depth)
    edits = [
        RewriteEdit(
            kind="insert_memory",
            target=bank0_name,
            details={
                "width": memory.width,
                "depth": bank_depth,
                "init": bank0_init,
                "read_ports": memory.read_ports,
                "write_ports": memory.write_ports,
                "read_style": memory.read_style,
                "read_latency": memory.read_latency,
                "byte_enable_granularity": memory.byte_enable_granularity,
            },
        ),
        RewriteEdit(
            kind="insert_memory",
            target=bank1_name,
            details={
                "width": memory.width,
                "depth": bank_depth,
                "init": bank1_init,
                "read_ports": memory.read_ports,
                "write_ports": memory.write_ports,
                "read_style": memory.read_style,
                "read_latency": memory.read_latency,
                "byte_enable_granularity": memory.byte_enable_granularity,
            },
        ),
    ]
    for output_name, addr_name in (("a_rdata", "a_addr"), ("b_rdata", "b_addr")):
        assignment = _find_assignment(module.assignments, output_name)
        if assignment is None or not _signal_exists(module, addr_name):
            continue
        edits.append(
            RewriteEdit(
                kind="replace_assignment_expr",
                target=output_name,
                details={
                    "phase": assignment.phase,
                    "original_expr": assignment.expr,
                    "replacement_expr": _banked_read_expr(
                        bank0_name=bank0_name,
                        bank1_name=bank1_name,
                        addr_name=addr_name,
                        local_width=local_width,
                    ),
                },
            )
        )
    if _signal_exists(module, "a_addr") and _signal_exists(module, "a_wdata") and _signal_exists(module, "a_wen"):
        for bank_value, bank_name in ((0, bank0_name), (1, bank1_name)):
            edits.append(
                RewriteEdit(
                    kind="append_memory_write",
                    target=bank_name,
                    details={
                        "addr": _shifted_addr_expr("a_addr", local_width),
                        "value": SignalRef("a_wdata"),
                        "enable": BinaryExpr("&", SignalRef("a_wen"), _addr_bank_eq("a_addr", bank_value)),
                    },
                )
            )
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment="a_rdata",
        applicability="direct_apply",
        applicability_reason=None,
        edits=tuple(edits),
    )


def _lut_packed_rows_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    memory = module.memories[0] if module.memories else None
    assignment = _find_assignment(module.assignments, "dout")
    if memory is None or assignment is None or memory.depth < 2 or not _signal_exists(module, "addr"):
        return None
    packed_depth = max((memory.depth + 1) // 2, 1)
    packed_width = memory.width * 2
    local_width = max((packed_depth - 1).bit_length(), 1)
    packed_name = f"{memory.name}_packed"
    edits = [
        RewriteEdit(
            kind="insert_memory",
            target=packed_name,
            details={
                "width": packed_width,
                "depth": packed_depth,
                "init": _pack_memory_rows(memory.init, memory.width, packed_depth),
                "read_ports": 1,
                "write_ports": 1,
                "read_style": memory.read_style,
                "read_latency": memory.read_latency,
            },
        ),
        RewriteEdit(
            kind="replace_assignment_expr",
            target="dout",
            details={
                "phase": assignment.phase,
                "original_expr": assignment.expr,
                "replacement_expr": _packed_row_read_expr(
                    packed_name=packed_name,
                    addr_name="addr",
                    elem_width=memory.width,
                    local_width=local_width,
                ),
            },
        ),
    ]
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment="dout",
        applicability="direct_apply",
        applicability_reason=None,
        edits=tuple(edits),
    )


def _handshake_payload_gating_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    state_name = None
    if _signal_exists(module, "buf_data"):
        state_name = "buf_data"
    elif _signal_exists(module, "data_reg"):
        state_name = "data_reg"
    if state_name is None:
        return None
    assignment = _find_assignment(module.assignments, state_name)
    if assignment is None or assignment.phase != "seq":
        return None
    helper_name = f"{state_name}_hold_en"
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment=state_name,
        applicability="scaffold_only",
        applicability_reason=(
            "introduce an explicit handshake-fire enable and rewrite the payload state update "
            "to hold by default; this proposal points at the payload register but does not "
            "mechanically rewrite the surrounding control semantics"
        ),
        edits=(
            RewriteEdit(
                kind="insert_wire",
                target=helper_name,
                details={"width": 1, "signed": False},
            ),
            RewriteEdit(
                kind="append_assignment",
                target=helper_name,
                details={"expr": ConstExpr(0, 1), "phase": "comb"},
            ),
        ),
    )


def _queue_sideband_bundle_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    memory_names = {memory.name for memory in module.memories}
    if "req_storage" not in memory_names:
        return None
    helper_name = "entry_bundle"
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment="req_storage",
        applicability="scaffold_only",
        applicability_reason=(
            "replace lock-step sideband memories with one packed per-entry payload bundle; this "
            "requires a coordinated queue storage rewrite across enqueue, dequeue, and readback"
        ),
        edits=(
            RewriteEdit(
                kind="insert_wire",
                target=helper_name,
                details={"width": 1, "signed": False},
            ),
        ),
    )


def _register_bank_control_partition_proposal(
    module: SimModule,
    summary: str,
    rationale: str,
) -> Optional[RewriteProposal]:
    target_name = None
    for name in ("w_data_latched", "wdata_latched", "read_data_state", "rdata_state"):
        if _signal_exists(module, name):
            target_name = name
            break
    if target_name is None:
        return None
    helper_name = "capture_fire"
    return RewriteProposal(
        module_name=module.name,
        summary=summary,
        rationale=rationale,
        source_assignment=target_name,
        applicability="scaffold_only",
        applicability_reason=(
            "split protocol capture and response bookkeeping into smaller state groups; this "
            "proposal marks the hot latched state but leaves the actual sequential repartition "
            "to the designer or agent"
        ),
        edits=(
            RewriteEdit(
                kind="insert_wire",
                target=helper_name,
                details={"width": 1, "signed": False},
            ),
            RewriteEdit(
                kind="append_assignment",
                target=helper_name,
                details={"expr": ConstExpr(0, 1), "phase": "comb"},
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


def _deepest_binary_subexpr(expr, *, preferred_ops: Optional[Sequence[str]] = None):
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
    if preferred_ops is not None:
        preferred = [candidate for candidate in candidates if getattr(candidate, "op", None) in set(preferred_ops)]
        if preferred:
            candidates = preferred
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: (_expr_depth(candidate), _expr_node_count(candidate)), reverse=True)
    return candidates[0]


def _candidate_target_assignment(target: str, module_name: str) -> Optional[str]:
    raw = str(target or "").strip()
    if not raw:
        return None
    if " @" in raw:
        raw = raw.split(" @", 1)[0]
    prefix = f"{module_name}."
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    return raw or None


def _sorted_indexed_names(
    signals: Sequence[Signal],
    *,
    prefix: str,
    kind: str,
) -> Tuple[str, ...]:
    names = [signal.name for signal in signals if signal.kind == kind and signal.name.startswith(prefix)]
    return tuple(sorted(names, key=lambda name: int(name[len(prefix):])))


def _signal_exists(module: SimModule, name: str) -> bool:
    return any(signal.name == name for signal in module.signals)


def _shifted_addr_expr(addr_name: str, local_width: int):
    if local_width <= 0:
        return ConstExpr(0, 1)
    return BinaryExpr(">>", SignalRef(addr_name), ConstExpr(1, max(local_width + 1, 1)))


def _addr_bank_eq(addr_name: str, bank_value: int):
    return BinaryExpr(
        "==",
        BinaryExpr("&", SignalRef(addr_name), ConstExpr(1, 1)),
        ConstExpr(bank_value, 1),
    )


def _banked_read_expr(
    *,
    bank0_name: str,
    bank1_name: str,
    addr_name: str,
    local_width: int,
):
    local_addr = _shifted_addr_expr(addr_name, local_width)
    return MuxExpr(
        _addr_bank_eq(addr_name, 0),
        MemoryReadExpr(bank0_name, local_addr),
        MemoryReadExpr(bank1_name, local_addr),
    )


def _split_memory_init(init: Sequence[int], bank_depth: int) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    if not init:
        return (), ()
    bank0 = [0] * bank_depth
    bank1 = [0] * bank_depth
    for index, value in enumerate(init):
        bank_index = index & 1
        local_index = index >> 1
        if local_index >= bank_depth:
            continue
        if bank_index == 0:
            bank0[local_index] = int(value)
        else:
            bank1[local_index] = int(value)
    return tuple(bank0), tuple(bank1)


def _pack_memory_rows(
    init: Sequence[int],
    elem_width: int,
    packed_depth: int,
) -> Tuple[int, ...]:
    if not init:
        return ()
    mask = (1 << elem_width) - 1
    packed = [0] * packed_depth
    for pair_index in range(packed_depth):
        lo_index = pair_index * 2
        hi_index = lo_index + 1
        lo = int(init[lo_index]) & mask if lo_index < len(init) else 0
        hi = int(init[hi_index]) & mask if hi_index < len(init) else 0
        packed[pair_index] = lo | (hi << elem_width)
    return tuple(packed)


def _packed_row_read_expr(
    *,
    packed_name: str,
    addr_name: str,
    elem_width: int,
    local_width: int,
):
    packed_row = MemoryReadExpr(packed_name, _shifted_addr_expr(addr_name, local_width))
    low_half = MaskExpr(packed_row, elem_width)
    high_half = BinaryExpr(">>", packed_row, ConstExpr(elem_width, max(elem_width.bit_length(), 1)))
    return MuxExpr(
        _addr_bank_eq(addr_name, 0),
        low_half,
        MaskExpr(high_half, elem_width),
    )


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
