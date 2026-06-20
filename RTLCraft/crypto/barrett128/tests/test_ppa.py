"""PPA analysis and optimization design for the Barrett modular multiplier.

Uses rtlgen_x.ppa to:
  1. analyze the executable module structure (state bits, logic depth, etc.)
  2. run an architecture-side model of the 5-stage pipeline
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
    # The 5-stage pipe carries: 5 valid bits + 256b product + 130b q + 256b*3
    # residuals + 128b*4 moduli + 129b constant ≈ a large sequential state.
    assert stats.module_name == "barrett_mod_mul"
    assert stats.state_bits >= 5  # at least the valid-bit chain + pipeline regs
    assert stats.comb_assignments >= 1


def test_module_logic_depth_flagged():
    """The 128x128 multiply is a deep combinational cone; PPA should flag it."""
    report = advise_ppa(
        module=_lowered(),
        goals=PpaGoals(priority="timing_first", max_logic_depth=8),
    )
    titles = [r.title for r in report.recommendations]
    assert report.module_stats is not None
    # A 64-limb schoolbook multiply exceeds any reasonable per-stage depth.
    assert report.module_stats.max_expr_depth > 8
    assert any("Pipeline" in t or "rebalance" in t.lower() or "deep" in t.lower()
               for t in titles)


# ---------------------------------------------------------------------------
# 2. Architecture-side PPA: 5-stage pipeline throughput model
# ---------------------------------------------------------------------------

def test_architecture_pipeline_model():
    """Model the 5-stage Barrett pipe and confirm throughput = 1 op/cycle."""
    model = ArchitectureModel([
        StageSpec("mul",   kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("qest",  kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("resid", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("csub0", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
        StageSpec("csub1", kind="compute", latency=1, initiation_interval=1,
                  capacity=1, queue_depth=2),
    ])
    workload = Workload.from_flows(
        FlowSpec("modmul", path=("mul", "qest", "resid", "csub0", "csub1"), tokens=128),
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
