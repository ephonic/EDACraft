import pytest

from rtlgen.dsl import DslLoweringReport, Else, If, Input, LoweredDslModule, Module, Output, Reg
from rtlgen.sim import Assignment, BinaryExpr, ClockDomain, ConstExpr, MuxExpr, Signal, SignalRef, SimModule
from rtlgen.verify import StepVector, run_directed_test, run_streaming_test


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


def _raw_accum_module() -> SimModule:
    return SimModule(
        name="verify_accum",
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


def _accum_module() -> LoweredDslModule:
    return _lowered(_raw_accum_module())


def _multi_clock_verify_module() -> LoweredDslModule:
    return _lowered(SimModule(
        name="verify_multiclk",
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


class DslDirectedAccum(Module):
    def __init__(self):
        super().__init__("dsl_directed_accum")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.acc = Reg(8, "acc")

        @self.comb
        def _comb():
            self.out <<= self.acc

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                self.acc <<= self.acc + self.inp


def test_run_directed_test_reports_success(tmp_path):
    report = run_directed_test(
        _accum_module(),
        (
            StepVector(inputs={"inp": 5}, expected={"out": 8}),
            StepVector(inputs={"inp": 2}, expected={"out": 10}),
        ),
        name="accum_pass",
        build_dir=str(tmp_path / "pass_case"),
    )

    assert report.name == "accum_pass"
    assert report.passed is True
    assert report.failures == ()
    assert report.traces == ({"out": 8}, {"out": 10})


def test_run_directed_test_rejects_raw_simmodule(tmp_path):
    with pytest.raises(TypeError, match="does not accept raw SimModule"):
        run_directed_test(
            _raw_accum_module(),
            (StepVector(inputs={"inp": 5}, expected={"out": 8}),),
            build_dir=str(tmp_path / "raw_pass_case"),
        )


def test_run_directed_test_reports_failure_details(tmp_path):
    report = run_directed_test(
        _accum_module(),
        (
            StepVector(inputs={"inp": 5}, expected={"out": 8}),
            StepVector(inputs={"inp": 2}, expected={"out": 9}),
        ),
        name="accum_fail",
        build_dir=str(tmp_path / "fail_case"),
    )

    assert report.name == "accum_fail"
    assert report.passed is False
    assert len(report.failures) == 1
    failure = report.failures[0]
    assert failure.cycle == 1
    assert failure.signal == "out"
    assert failure.expected == 9
    assert failure.actual == 10
    assert failure.inputs == {"inp": 2}


def test_run_streaming_test_reports_failure_details(tmp_path):
    report = run_streaming_test(
        _accum_module(),
        (
            StepVector(inputs={"inp": 5}, expected={"out": 8}),
            StepVector(inputs={"inp": 2}, expected={"out": 9}),
            StepVector(inputs={"inp": 1}, expected={"out": 11}),
        ),
        name="accum_stream_fail",
        build_dir=str(tmp_path / "stream_case"),
        chunk_cycles=2,
    )

    assert report.name == "accum_stream_fail"
    assert report.total_cycles == 3
    assert report.checked_signals == ("out",)
    assert report.passed is False
    assert len(report.failures) == 1
    failure = report.failures[0]
    assert failure.cycle == 1
    assert failure.signal == "out"
    assert failure.expected == 9
    assert failure.actual == 10
    assert failure.inputs == {"inp": 2}


def test_run_directed_test_accepts_dsl_module(tmp_path):
    report = run_directed_test(
        DslDirectedAccum(),
        (
            StepVector(inputs={"clk": 0, "rst": 1, "inp": 0}, expected={"out": 0}),
            StepVector(inputs={"clk": 0, "rst": 0, "inp": 5}, expected={"out": 5}),
            StepVector(inputs={"clk": 0, "rst": 0, "inp": 2}, expected={"out": 7}),
        ),
        name="dsl_directed_pass",
        build_dir=str(tmp_path / "dsl_directed"),
    )

    assert report.passed is True
    assert report.traces[-1] == {"out": 7}


def test_run_directed_test_rejects_multi_clock_modules(tmp_path):
    with pytest.raises(ValueError, match="single-clock executable models"):
        run_directed_test(
            _multi_clock_verify_module(),
            (StepVector(inputs={"wr_en": 0, "rd_en": 0}, expected={"out": 0}),),
            build_dir=str(tmp_path / "multiclk_directed"),
        )


def test_run_streaming_test_rejects_multi_clock_modules(tmp_path):
    with pytest.raises(ValueError, match="single-clock executable models"):
        run_streaming_test(
            _multi_clock_verify_module(),
            (StepVector(inputs={"wr_en": 0, "rd_en": 0}, expected={"out": 0}),),
            build_dir=str(tmp_path / "multiclk_stream"),
            chunk_cycles=2,
        )
