import time
import json

import pytest

from rtlgen_x.dsl import DslLoweringReport, LoweredDslModule
from rtlgen_x.sim import Assignment, BinaryExpr, ClockDomain, ConstExpr, MuxExpr, Signal, SignalRef, SimModule
from rtlgen_x.verify import StepVector, run_streaming_check, run_streaming_check_adaptive, run_streaming_test
from rtlgen_x.verify.sinks import CsvTraceSink, JsonlTraceSink


def _lowered(module: SimModule) -> LoweredDslModule:
    return LoweredDslModule(
        module=module,
        report=DslLoweringReport(
            source_module=module.name,
            flattened_module=module.name,
            signal_count=len(module.signals),
            assignment_count=len(module.assignments),
            outputs_post_state=module.outputs_post_state,
        ),
    )


def _raw_stream_accum_module() -> SimModule:
    return SimModule(
        name="verify_stream_accum",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )


def _stream_accum_module() -> LoweredDslModule:
    return _lowered(_raw_stream_accum_module())


def _stream_multiclk_module() -> LoweredDslModule:
    return _lowered(SimModule(
        name="verify_stream_multiclk",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("rd_en", width=1, kind="input"),
            Signal("wptr", width=4, kind="state"),
            Signal("rptr", width=4, kind="state"),
            Signal("out", width=4, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("wptr"), SignalRef("rptr"))),
            Assignment(
                "wptr",
                MuxExpr(
                    SignalRef("wr_en"),
                    BinaryExpr("+", SignalRef("wptr"), ConstExpr(1, 4)),
                    SignalRef("wptr"),
                ),
                phase="seq",
                clock_domain="wr_clk",
            ),
            Assignment(
                "rptr",
                MuxExpr(
                    SignalRef("rd_en"),
                    BinaryExpr("+", SignalRef("rptr"), ConstExpr(1, 4)),
                    SignalRef("rptr"),
                ),
                phase="seq",
                clock_domain="rd_clk",
            ),
        ),
        outputs=("out",),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
    ))


def test_streaming_verification_scales_without_trace_materialization(tmp_path):
    module = _stream_accum_module()
    cycles = 4096

    def vectors():
        acc = 3
        for idx in range(cycles):
            inp = (idx * 7 + 5) & 0xFF
            out = (acc + inp) & 0xFF
            yield StepVector(inputs={"inp": inp}, expected={"out": out})
            acc = out

    start = time.perf_counter()
    report = run_streaming_test(
        module,
        vectors(),
        name="stream_pass",
        build_dir=str(tmp_path / "stream_pass"),
        chunk_cycles=256,
    )
    elapsed = time.perf_counter() - start

    assert report.name == "stream_pass"
    assert report.passed is True
    assert report.total_cycles == cycles
    assert report.failures == ()
    assert elapsed > 0.0


def test_streaming_test_rejects_raw_simmodule(tmp_path):
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        run_streaming_test(
            _raw_stream_accum_module(),
            (StepVector(inputs={"inp": 5}, expected={"out": 8}),),
            build_dir=str(tmp_path / "raw_stream"),
            chunk_cycles=8,
        )


def test_streaming_check_supports_online_expected_function(tmp_path):
    module = _stream_accum_module()
    cycles = 1024

    def input_stream():
        for idx in range(cycles):
            yield {"inp": (idx * 13 + 9) & 0xFF}

    acc_state = {"acc": 3}

    def expected_fn(cycle, inputs):
        out = (acc_state["acc"] + inputs["inp"]) & 0xFF
        acc_state["acc"] = out
        return {"out": out}

    report = run_streaming_check(
        module,
        input_stream(),
        expected_fn,
        name="online_check",
        build_dir=str(tmp_path / "online_check"),
        chunk_cycles=128,
    )

    assert report.name == "online_check"
    assert report.passed is True
    assert report.total_cycles == cycles
    assert report.failures == ()


def test_streaming_check_rejects_multi_clock_modules(tmp_path):
    module = _stream_multiclk_module()

    def input_stream():
        yield {"wr_en": 0, "rd_en": 0}

    with pytest.raises(ValueError, match="single-clock executable models"):
        run_streaming_check(
            module,
            input_stream(),
            lambda _cycle, _inputs: {"out": 0},
            build_dir=str(tmp_path / "stream_multiclk"),
        )


def test_streaming_check_adaptive_rejects_multi_clock_modules(tmp_path):
    module = _stream_multiclk_module()

    def input_stream():
        yield {"wr_en": 0, "rd_en": 0}

    with pytest.raises(ValueError, match="single-clock executable models"):
        run_streaming_check_adaptive(
            module,
            input_stream(),
            lambda _cycle, _inputs: {"out": 0},
            build_dir=str(tmp_path / "stream_multiclk_adapt"),
        )


def test_streaming_check_supports_failure_budget_and_trace_sampling(tmp_path):
    module = _stream_accum_module()
    cycles = 16

    def input_stream():
        for idx in range(cycles):
            yield {"inp": idx + 1}

    acc_state = {"acc": 3}

    def expected_fn(cycle, inputs):
        out = (acc_state["acc"] + inputs["inp"]) & 0xFF
        acc_state["acc"] = out
        if cycle in {2, 5, 9}:
            return {"out": (out + 1) & 0xFF}
        return {"out": out}

    collected = []

    report = run_streaming_check(
        module,
        input_stream(),
        expected_fn,
        name="budgeted_check",
        build_dir=str(tmp_path / "budgeted_check"),
        chunk_cycles=8,
        max_failures=2,
        failure_block_cycles=1,
        trace_stride=3,
        trace_sink=collected.append,
    )

    assert report.name == "budgeted_check"
    assert report.passed is False
    assert report.total_cycles >= report.executed_cycles
    assert report.executed_cycles < cycles
    assert report.stopped_early is True
    assert report.max_failures == 2
    assert len(report.failures) == 2
    assert report.failures[0].cycle == 2
    assert report.failures[1].cycle == 5
    assert len(report.sampled_traces) >= 1
    assert len(collected) == len(report.sampled_traces)
    assert collected[0].cycle == report.sampled_traces[0].cycle


def test_streaming_check_adaptive_continues_until_failure_budget(tmp_path):
    module = _stream_accum_module()
    cycles = 64

    def input_stream():
        for idx in range(cycles):
            yield {"inp": idx + 1}

    acc_state = {"acc": 3}

    def expected_fn(cycle, inputs):
        out = (acc_state["acc"] + inputs["inp"]) & 0xFF
        acc_state["acc"] = out
        if cycle in {2, 5, 9}:
            return {"out": (out + 1) & 0xFF}
        return {"out": out}

    report = run_streaming_check_adaptive(
        module,
        input_stream(),
        expected_fn,
        name="adaptive_budget",
        build_dir=str(tmp_path / "adaptive_budget"),
        chunk_cycles=16,
        max_failures=2,
        trace_stride=2,
    )

    assert report.passed is False
    assert report.stopped_early is True
    assert report.executed_cycles == 6
    assert len(report.failures) == 2
    assert report.failures[0].cycle == 2
    assert report.failures[1].cycle == 5


def test_streaming_check_adaptive_finishes_chunk_when_budget_not_reached(tmp_path):
    module = _stream_accum_module()
    cycles = 32

    def input_stream():
        for idx in range(cycles):
            yield {"inp": (idx * 5 + 1) & 0xFF}

    acc_state = {"acc": 3}

    def expected_fn(cycle, inputs):
        out = (acc_state["acc"] + inputs["inp"]) & 0xFF
        acc_state["acc"] = out
        if cycle == 9:
            return {"out": (out + 1) & 0xFF}
        return {"out": out}

    report = run_streaming_check_adaptive(
        module,
        input_stream(),
        expected_fn,
        name="adaptive_single_failure",
        build_dir=str(tmp_path / "adaptive_single_failure"),
        chunk_cycles=16,
        max_failures=2,
        trace_stride=4,
    )

    assert report.passed is False
    assert report.stopped_early is False
    assert report.executed_cycles == cycles
    assert len(report.failures) == 1
    assert report.failures[0].cycle == 9


def test_trace_sinks_write_jsonl_and_csv(tmp_path):
    samples = []
    jsonl_path = tmp_path / "trace.jsonl"
    csv_path = tmp_path / "trace.csv"
    jsonl_sink = JsonlTraceSink(jsonl_path)
    csv_sink = CsvTraceSink(csv_path)
    try:
        module = _stream_accum_module()
        report = run_streaming_check(
            module,
            ({"inp": idx + 1} for idx in range(8)),
            lambda cycle, inputs: {"out": ((sum(range(1, cycle + 2)) + 3) & 0xFF)},
            name="sink_run",
            build_dir=str(tmp_path / "sink_run"),
            chunk_cycles=4,
            trace_stride=2,
            trace_sink=lambda sample: (samples.append(sample), jsonl_sink(sample), csv_sink(sample)),
        )
    finally:
        jsonl_sink.close()
        csv_sink.close()

    assert report.executed_cycles == 8
    assert len(samples) == len(report.sampled_traces)
    jsonl_lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == len(samples)
    assert len(csv_lines) == len(samples) + 1
    parsed = json.loads(jsonl_lines[0])
    assert "cycle" in parsed and "inputs" in parsed and "outputs" in parsed and "expected" in parsed
