from rtlgen_x.dsl import Else, If, Input, Module, Output, Reg
from rtlgen_x.sim import Assignment, BinaryExpr, Signal, SignalRef, SimModule
from rtlgen_x.verify import StepVector, run_directed_test, run_streaming_test


def _accum_module() -> SimModule:
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


class LegacyDirectedAccum(Module):
    def __init__(self):
        super().__init__("legacy_directed_accum")
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


def test_run_directed_test_accepts_legacy_dsl_module(tmp_path):
    report = run_directed_test(
        LegacyDirectedAccum(),
        (
            StepVector(inputs={"clk": 0, "rst": 1, "inp": 0}, expected={"out": 0}),
            StepVector(inputs={"clk": 0, "rst": 0, "inp": 5}, expected={"out": 5}),
            StepVector(inputs={"clk": 0, "rst": 0, "inp": 2}, expected={"out": 7}),
        ),
        name="legacy_directed_pass",
        build_dir=str(tmp_path / "legacy_directed"),
    )

    assert report.passed is True
    assert report.traces[-1] == {"out": 7}
