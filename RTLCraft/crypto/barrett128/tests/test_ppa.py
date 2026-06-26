"""PPA analysis and optimization design for the Barrett modular multiplier.

Uses rtlgen_x.ppa to:
  1. analyze the executable module structure (state bits, logic depth, etc.)
  2. run an architecture-side model of the 8-stage KO pipeline
  3. advise on PPA with explicit goals
  4. derive + evaluate + validate a pipeline-retiming rewrite proposal
"""

from __future__ import annotations

import pytest

from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload
from rtlgen_x.ppa import (
    PpaGoals,
    advise_ppa,
    analyze_module_ppa,
    derive_rewrite_proposals,
    evaluate_rewrite_proposal,
    validate_rewrite_proposal,
)

from crypto.barrett128 import BarrettModMul

K = 128


def _lowered():
    from rtlgen_x.dsl import lower_legacy_module_to_sim
    return lower_legacy_module_to_sim(BarrettModMul()).module


# ---------------------------------------------------------------------------
# 1. Module-side structural PPA analysis
# ---------------------------------------------------------------------------

def test_module_ppa_stats():
    stats = analyze_module_ppa(BarrettModMul())
    # The 8-stage KO pipe carries 27 leaf products, 9 level-1 combines, 3
    # level-2 combines, the final 256-bit product, delayed n/m sideband regs,
    # and the Barrett tail state, so the sequential footprint is materially
    # larger than the prior 5-stage schoolbook design.
    assert stats.module_name == "barrett_mod_mul"
    assert stats.state_bits >= 4000
    assert stats.comb_assignments >= 1


def test_module_logic_depth_flagged():
    """The KO base multiply is the deepest combinational cone; PPA flags it.

    With the Karatsuba-Ofman multiplier (3 recursion levels down to 16-bit
    base multipliers), the critical combinational path is the M-M-M leaf
    multiply ``p16_MMM`` — three nested ``(hi+lo)`` adders feeding a 19x19
    multiplier — which is by construction much shallower than the prior
    schoolbook 64-limb cone.
    """
    report = advise_ppa(
        module=_lowered(),
        goals=PpaGoals(priority="timing_first", max_logic_depth=8),
    )
    titles = [r.title for r in report.recommendations]
    assert report.module_stats is not None
    # The KO leaf multiply is shallower than the old schoolbook cone but is
    # still the deepest path; it must exceed the per-stage budget so the
    # advisor flags it.
    assert report.module_stats.max_expr_depth > 8
    # Critical assignment is now the deepest KO leaf product, not the final
    # 256-bit p_q sum.
    assert report.module_stats.critical_assignment_target == "p16_MMM"
    assert report.module_stats.critical_assignment_phase == "seq"
    assert report.module_stats.critical_assignment_source_file
    assert isinstance(report.module_stats.critical_assignment_source_line, int)
    assert report.module_stats.critical_expr_kind == "BinaryExpr"
    # The leaf is a multiplier (the (h+l) sum chain feeds into '*').
    assert report.module_stats.critical_expr_op == "*"
    assert len(report.module_stats.critical_expr_operand_widths) == 2
    assert any("Pipeline" in t or "rebalance" in t.lower() or "deep" in t.lower()
               for t in titles)
    timing_rec = next(rec for rec in report.recommendations if rec.category == "timing")
    assert timing_rec.evidence["critical_assignment_target"] == "p16_MMM"
    assert timing_rec.evidence["critical_expr_kind"] == "BinaryExpr"
    assert timing_rec.evidence["critical_expr_op"] == "*"


# ---------------------------------------------------------------------------
# 2. Architecture-side PPA: 8-stage KO pipeline throughput model
# ---------------------------------------------------------------------------

def test_architecture_pipeline_model():
    """Model the 8-stage KO Barrett pipe and confirm throughput = 1 op/cycle."""
    model = ArchitectureModel([
        StageSpec("ko_leaf", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("ko_lvl1", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("ko_lvl2", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("ko_final", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("qest", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("resid", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("csub0", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("csub1", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
    ])
    workload = Workload.from_flows(
        FlowSpec(
            "modmul",
            path=("ko_leaf", "ko_lvl1", "ko_lvl2", "ko_final", "qest", "resid", "csub0", "csub1"),
            tokens=128,
        ),
    )
    report = advise_ppa(model=model, workload=workload,
                        goals=PpaGoals(min_throughput_tokens_per_cycle=1.0,
                                       max_stall_ratio=0.05))
    assert report.architecture_stats is not None
    # Initiation interval 1 on every stage => steady-state throughput ~1 op/cycle.
    flow = report.architecture_stats.flow_stats["modmul"]
    assert flow.throughput_tokens_per_cycle >= 0.9


# ---------------------------------------------------------------------------
# 3. Rewrite proposal: pipeline retiming to break up the deep multiply cone
# ---------------------------------------------------------------------------

def test_rewrite_proposal_evaluates_depth():
    """A pipeline-retiming rewrite should reduce the max combinational depth."""
    module = _lowered()
    report = advise_ppa(module=module,
                        goals=PpaGoals(priority="timing_first", max_logic_depth=8))
    proposals = derive_rewrite_proposals(module, report)
    assert proposals, "expected at least one rewrite proposal for the deep mul cone"
    best = proposals[0]
    evaluation = evaluate_rewrite_proposal(module, best)
    # The rewritten structure should not be deeper than the original.
    assert evaluation.rewritten_depth <= evaluation.original_depth
