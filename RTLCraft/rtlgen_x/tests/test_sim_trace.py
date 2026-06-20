from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    CppBackendScaffold,
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
