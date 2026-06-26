"""Top-level SoC closure orchestration for the document-driven Earphone flow."""

from __future__ import annotations

from typing import Callable


def run_top_level_closure(
    *,
    review_bundle_fn: Callable[[], None],
    l1_tests_fn: Callable[[], tuple[bool, list]],
    l3_tests_fn: Callable[[], tuple[bool, list]],
    cross_layer_fn: Callable[[], tuple[bool, list]],
    verilog_fn: Callable[[], list],
    intent_tests_fn: Callable[[], tuple[bool, list]],
    cocotb_gen_fn: Callable[[], object],
    scaffold_fn: Callable[[], tuple[bool, dict, list, list]],
) -> int:
    """Run the top-level SoC closure after layered docs/tests/approvals pass.

    The legacy monolithic implementation still provides many concrete helpers.
    This orchestrator centralizes the closure sequence under the top-level
    document-driven package so `earphone.flow` owns the supported entry point.
    """
    scaffold_ok, checklist, feedback, resolved_feedback = scaffold_fn()

    review_bundle_fn()

    l1_ok, l1_results = l1_tests_fn()
    l3_ok, l3_results = l3_tests_fn()
    xlayer_ok, xlayer_results = cross_layer_fn()
    gen_results = verilog_fn()
    intent_ok, intent_results = intent_tests_fn()
    cocotb_gen_fn()

    print("\n" + "=" * 70)
    print("SMART EARPHONE SoC — DESIGN SUMMARY")
    print("=" * 70)
    print(f"  Scaffold compliance   : {sum(checklist.values())}/{len(checklist)} OK")
    print(f"  L1 functional tests   : {sum(1 for _, ok in l1_results if ok)}/{len(l1_results)} PASS")
    print(f"  L3 DSL sim tests      : {sum(1 for _, ok in l3_results if ok)}/{len(l3_results)} PASS")
    print(f"  Cross-layer checks    : {sum(1 for _, ok in xlayer_results if ok)}/{len(xlayer_results)} PASS")
    print(f"  Intent-driven tests   : {sum(1 for _, ok in intent_results if ok)}/{len(intent_results)} PASS")
    print(f"  Verilog modules       : {sum(1 for r in gen_results if r[1])}/{len(gen_results)} generated")
    total_lines = sum(r[2] for r in gen_results if r[1])
    total_lint = sum(r[3] for r in gen_results if r[1])
    print(f"  Total Verilog lines   : {total_lines}")
    print(f"  Total lint issues     : {total_lint}")
    print("=" * 70)

    all_ok = (
        scaffold_ok
        and l1_ok
        and l3_ok
        and xlayer_ok
        and intent_ok
        and all(r[1] for r in gen_results)
    )
    print(f"\n  Overall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


__all__ = ["run_top_level_closure"]
