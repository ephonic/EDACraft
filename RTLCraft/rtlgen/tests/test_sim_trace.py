from rtlgen.sim import (
    Assignment,
    BinaryExpr,
    ClockDomain,
    ConstExpr,
    CppBackendScaffold,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    RandomParityConfig,
    Signal,
    SignalRef,
    SimModule,
    PythonSimulator,
    capture_execution_trace,
    compare_python_and_compiled,
    replay_execution_trace,
    run_random_parity_fuzz,
)
from rtlgen.dsl import Else, If, Input, Module, Output, Reg, build_compiled_simulator_from_dsl, lower_dsl_module_to_sim


def _accum_module():
    return SimModule(
        name="trace_accum",
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


def _dual_clock_fifo_like_module():
    return SimModule(
        name="trace_multi_clock_fifo",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("rd_en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("wr_ptr", width=2, kind="state", init=0),
            Signal("rd_ptr", width=2, kind="state", init=0),
            Signal("rd_data", width=8, kind="state", init=0),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", SignalRef("rd_data")),
            Assignment(
                "wr_ptr",
                MuxExpr(SignalRef("wr_en"), BinaryExpr("+", SignalRef("wr_ptr"), ConstExpr(1, 2)), SignalRef("wr_ptr")),
                phase="seq",
                clock_domain="wr_clk",
            ),
            Assignment(
                "rd_ptr",
                MuxExpr(SignalRef("rd_en"), BinaryExpr("+", SignalRef("rd_ptr"), ConstExpr(1, 2)), SignalRef("rd_ptr")),
                phase="seq",
                clock_domain="rd_clk",
            ),
            Assignment(
                "rd_data",
                MuxExpr(SignalRef("rd_en"), MemoryReadExpr("fifo_mem", SignalRef("rd_ptr")), SignalRef("rd_data")),
                phase="seq",
                clock_domain="rd_clk",
            ),
        ),
        outputs=("out",),
        memories=(Memory("fifo_mem", width=8, depth=4),),
        memory_writes=(
            MemoryWrite("fifo_mem", SignalRef("wr_ptr"), SignalRef("din"), enable=SignalRef("wr_en"), clock_domain="wr_clk"),
        ),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
        outputs_post_state=True,
    )


class DslTraceResetBranchValue(Module):
    def __init__(self):
        super().__init__("dsl_trace_reset_branch_value")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.inp = Input(8, "inp")
        self.out = Output(8, "out")
        self.state = Reg(8, "state")

        @self.comb
        def _comb():
            self.out <<= self.state

        @self.seq(self.clk, self.rst)
        def _seq():
            with If(self.rst == 1):
                self.state <<= 7
            with Else():
                self.state <<= self.inp


def test_capture_and_replay_execution_trace():
    module = _accum_module()
    vectors = ({"inp": 5}, {"inp": 2}, {"inp": 1})
    sim = PythonSimulator(module)
    trace = capture_execution_trace(sim, vectors, module_name=module.name, backend="python")

    replay = PythonSimulator(module)
    mismatches = replay_execution_trace(replay, trace)

    assert trace.module_name == module.name
    assert len(trace.steps) == 3
    assert trace.steps[0].outputs == {"out": 8}
    assert mismatches == ()


def test_compare_python_and_compiled_reports_match(tmp_path):
    report = compare_python_and_compiled(
        _accum_module(),
        ({"inp": 5}, {"inp": 2}, {"inp": 1}),
        builder=CppBackendScaffold(),
        build_dir=tmp_path / "trace_parity",
    )

    assert report.matched is True
    assert report.mismatches == ()
    assert report.python_trace.steps[-1].outputs == {"out": 11}
    assert report.compiled_trace.steps[-1].state["acc"] == 11


def test_random_parity_fuzz_runs_and_matches(tmp_path):
    report = run_random_parity_fuzz(
        _accum_module(),
        config=RandomParityConfig(cycles=32, seed=99),
        builder=CppBackendScaffold(),
        build_dir=tmp_path / "fuzz",
    )

    assert report.cycles == 32
    assert report.seed == 99
    assert len(report.vectors) == 32
    assert report.parity.matched is True


def test_compare_python_and_compiled_reports_match_for_explicit_multi_clock(tmp_path):
    vectors = (
        ({"wr_en": 1, "din": 11}, ("wr_clk",)),
        ({"wr_en": 1, "din": 22}, ("wr_clk",)),
        ({"rd_en": 1}, ("rd_clk",)),
        ({"rd_en": 1}, ("rd_clk",)),
        ({"rd_rst": 1}, ("rd_clk",)),
    )

    report = compare_python_and_compiled(
        _dual_clock_fifo_like_module(),
        vectors,
        builder=CppBackendScaffold(),
        build_dir=tmp_path / "trace_multiclk",
    )

    assert report.matched is True
    assert report.mismatches == ()
    assert report.python_trace.steps[2].active_domains == ("rd_clk",)
    assert report.compiled_trace.steps[3].outputs == {"out": 22}


def test_compare_python_and_compiled_reports_match_for_dsl_reset_branch_value(tmp_path):
    lowered = lower_dsl_module_to_sim(DslTraceResetBranchValue())
    report = compare_python_and_compiled(
        lowered.module,
        (
            {"rst": 1, "inp": 2},
            {"rst": 0, "inp": 9},
            {"rst": 0, "inp": 5},
        ),
        builder=CppBackendScaffold(),
        build_dir=tmp_path / "trace_reset_branch_value",
    )

    assert report.matched is True
    assert report.mismatches == ()
    assert [step.outputs["out"] for step in report.python_trace.steps] == [7, 9, 5]
    assert [step.outputs["out"] for step in report.compiled_trace.steps] == [7, 9, 5]


def test_capture_execution_trace_from_lowered_dsl_preserves_reset_branch_value():
    sim = PythonSimulator(lower_dsl_module_to_sim(DslTraceResetBranchValue()).module)
    trace = capture_execution_trace(
        sim,
        (
            {"rst": 1, "inp": 2},
            {"rst": 0, "inp": 9},
            {"rst": 0, "inp": 5},
        ),
        module_name="dsl_trace_reset_branch_value",
        backend="python",
    )

    assert [step.outputs["out"] for step in trace.steps] == [7, 9, 5]
    assert [step.state["state"] for step in trace.steps] == [7, 9, 5]
