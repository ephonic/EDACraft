"""Tests for top-level closure orchestration."""

from __future__ import annotations

from earphone.top.src.closure import run_top_level_closure


def test_run_top_level_closure_returns_success_when_all_steps_pass():
    calls = []

    def record(name):
        calls.append(name)

    rc = run_top_level_closure(
        review_bundle_fn=lambda: record("review"),
        l1_tests_fn=lambda: (record("l1"), (True, [("l1", True)]))[1],
        l3_tests_fn=lambda: (record("l3"), (True, [("l3", True)]))[1],
        cross_layer_fn=lambda: (record("xlayer"), (True, [("xlayer", True)]))[1],
        verilog_fn=lambda: (record("verilog"), [("earphone_top", True, 10, 0)])[1],
        intent_tests_fn=lambda: (record("intent"), (True, [("intent", True)]))[1],
        cocotb_gen_fn=lambda: record("cocotb"),
        scaffold_fn=lambda: (record("scaffold"), (True, {"gate": True}, [], []))[1],
    )

    assert rc == 0
    assert calls == ["scaffold", "review", "l1", "l3", "xlayer", "verilog", "intent", "cocotb"]


def test_run_top_level_closure_returns_failure_when_any_step_fails():
    rc = run_top_level_closure(
        review_bundle_fn=lambda: None,
        l1_tests_fn=lambda: (False, [("l1", False)]),
        l3_tests_fn=lambda: (True, [("l3", True)]),
        cross_layer_fn=lambda: (True, [("xlayer", True)]),
        verilog_fn=lambda: [("earphone_top", True, 10, 0)],
        intent_tests_fn=lambda: (True, [("intent", True)]),
        cocotb_gen_fn=lambda: None,
        scaffold_fn=lambda: (True, {"gate": True}, [], []),
    )

    assert rc == 1
