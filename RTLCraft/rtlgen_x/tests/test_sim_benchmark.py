from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    benchmark_cosim_backends,
    benchmark_cosim_cache,
    benchmark_compiled_speedup,
    benchmark_streaming_capacity,
    build_stress_module,
    emit_cosim_backend_sweep_markdown,
    iter_stress_input_rows,
    generate_stress_input_buffer,
    run_stress_sweep,
    write_cosim_backend_sweep_report,
    write_stress_sweep_report,
    Signal,
    SignalRef,
    SimModule,
)
import json
import time


def test_benchmark_report_has_positive_timings(tmp_path):
    module = build_stress_module()
    cycles = 256
    inputs = generate_stress_input_buffer(module, cycles, seed=7)
    report = benchmark_compiled_speedup(
        module,
        inputs,
        cycles,
        repeats=1,
        warmup=0,
        build_dir=str(tmp_path / "bench"),
    )

    assert report.module_name == module.name
    assert report.cycles == cycles
    assert report.compile_seconds > 0.0
    assert report.python_step_seconds > 0.0
    assert report.cpp_step_seconds > 0.0
    assert report.python_batch_seconds > 0.0
    assert report.cpp_batch_seconds > 0.0
    assert report.step_speedup > 0.0
    assert report.batch_speedup > 0.0


def test_streaming_benchmark_report_has_positive_timings(tmp_path):
    module = build_stress_module()
    cycles = 512
    report = benchmark_streaming_capacity(
        module,
        lambda: iter_stress_input_rows(module, cycles, seed=11),
        cycles,
        chunk_cycles=64,
        repeats=1,
        warmup=0,
        build_dir=str(tmp_path / "stream"),
    )

    assert report.module_name == module.name
    assert report.cycles == cycles
    assert report.chunk_cycles == 64
    assert report.compile_seconds > 0.0
    assert report.chunk_input_bytes > 0
    assert report.chunk_output_bytes > 0
    assert report.python_stream_seconds > 0.0
    assert report.cpp_stream_seconds > 0.0
    assert report.stream_speedup > 0.0


def test_wide_streaming_benchmark_handles_multiword_buffers(tmp_path):
    module = SimModule(
        name="bench_wide",
        signals=(
            Signal("inp", width=128, kind="input"),
            Signal("acc", width=128, kind="state", init=1),
            Signal("out", width=128, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )
    cycles = 128

    def row_factory():
        for idx in range(cycles):
            yield ((1 << 96) + idx,)

    report = benchmark_streaming_capacity(
        module,
        row_factory,
        cycles,
        chunk_cycles=16,
        repeats=1,
        warmup=0,
        build_dir=str(tmp_path / "wide_stream"),
    )

    assert report.module_name == module.name
    assert report.cycles == cycles
    assert report.chunk_input_bytes == 16 * 2 * 8
    assert report.chunk_output_bytes == 16 * 2 * 8
    assert report.cpp_stream_seconds > 0.0
    assert report.stream_speedup > 0.0


def test_stress_sweep_reports_capacity_summary(tmp_path):
    report = run_stress_sweep(
        widths=(16, 32),
        cycles_list=(32, 64),
        chunk_cycles=16,
        repeats=1,
        warmup=0,
        build_root=str(tmp_path / "stress_sweep"),
    )

    assert len(report.points) == 4
    assert report.widths == (16, 32)
    assert report.max_cycles == 64
    assert report.max_step_speedup > 0.0
    assert report.max_batch_speedup > 0.0
    assert report.max_stream_speedup > 0.0
    assert all(point.simulator.cycles == point.cycles for point in report.points)
    assert all(point.streaming.cycles == point.cycles for point in report.points)

    out_path = write_stress_sweep_report(report, tmp_path / "stress_sweep.json")
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["point_count"] == 4
    assert payload["widths"] == [16, 32]


def test_cosim_cache_benchmark_reports_warm_rerun(monkeypatch, tmp_path):
    class FakeSingleClockModule:
        name = "fake_cosim_cache"
        _seq_blocks = ((type("Clk", (), {"name": "clk"})(), None, False, False, None),)

    build_root = tmp_path / "cosim_bench"

    def fake_single_clock_run(module, vectors, *, rtl_backend, build_dir, valid_signal=None, **_kwargs):
        cache_root = build_dir / "rtl_cosim" / rtl_backend / "seq" / "cache_key"
        cache_root.mkdir(parents=True, exist_ok=True)
        stamp_path = cache_root / ".compile_stamp"
        cache_hit = stamp_path.exists()
        if not stamp_path.exists():
            time.sleep(0.02)
            stamp_path.write_text("cache_key", encoding="utf-8")
        else:
            time.sleep(0.001)
        return type(
            "Report",
            (),
            {
                "skipped_reason": None,
                "dsl_matches_rtl": True,
                "compiled_matches_rtl": True,
                "cache_enabled": True,
                "cache_hit": cache_hit,
                "cache_key": "cache_key",
                "cache_dir": str(cache_root),
            },
        )()

    monkeypatch.setattr("rtlgen_x.sim.benchmark.run_dsl_rtl_cosim", fake_single_clock_run)

    report = benchmark_cosim_cache(
        FakeSingleClockModule(),
        ({"inp": 1}, {"inp": 2}),
        rtl_backend="verilator",
        build_dir=build_root,
    )

    assert report.module_name == "fake_cosim_cache"
    assert report.backend == "verilator"
    assert report.mode == "seq"
    assert report.vector_count == 2
    assert report.compile_cache_enabled is True
    assert report.first_cache_hit is False
    assert report.second_cache_hit is True
    assert report.cache_key == "cache_key"
    assert report.cache_dir is not None
    assert report.cache_artifact_present is True
    assert report.first_report_passed is True
    assert report.second_report_passed is True
    assert report.first_run_seconds > 0.0
    assert report.second_run_seconds > 0.0
    assert report.warm_speedup > 1.0


def test_cosim_backend_sweep_reports_backend_matrix(monkeypatch, tmp_path):
    class FakeSingleClockModule:
        name = "fake_backend_sweep"
        _seq_blocks = ((type("Clk", (), {"name": "clk"})(), None, False, False, None),)

    def fake_benchmark(module, vectors, *, rtl_backend, valid_signal=None, build_dir=None):
        skipped_reason = "missing_tool" if rtl_backend == "vcs" else None
        return type(
            "CosimBench",
            (),
            {
                "module_name": module.name,
                "backend": rtl_backend,
                "mode": "seq",
                "vector_count": len(vectors),
                "compile_cache_enabled": rtl_backend != "iverilog",
                "first_cache_hit": False,
                "second_cache_hit": rtl_backend != "iverilog",
                "cache_key": f"{rtl_backend}_key",
                "cache_dir": None if skipped_reason else str(build_dir / "artifact"),
                "first_run_seconds": 0.02,
                "second_run_seconds": 0.01,
                "warm_speedup": 2.0,
                "cache_artifact_present": skipped_reason is None,
                "first_report_passed": skipped_reason is None,
                "second_report_passed": skipped_reason is None,
                "skipped_reason": skipped_reason,
            },
        )()

    monkeypatch.setattr("rtlgen_x.sim.benchmark.benchmark_cosim_cache", fake_benchmark)

    report = benchmark_cosim_backends(
        FakeSingleClockModule(),
        ({"inp": 1}, {"inp": 2}),
        rtl_backends=("iverilog", "verilator", "vcs"),
        build_dir=tmp_path / "backend_sweep",
    )

    assert report.module_name == "fake_backend_sweep"
    assert report.mode == "seq"
    assert report.vector_count == 2
    assert tuple(item.backend for item in report.backends) == ("iverilog", "verilator", "vcs")
    assert report.available_backends == ("iverilog", "verilator")
    assert report.skipped_backends == ("vcs",)
    assert report.backends[2].skipped_reason == "missing_tool"

    out_path = write_cosim_backend_sweep_report(report, tmp_path / "backend_sweep.json")
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["module_name"] == "fake_backend_sweep"
    assert payload["available_backends"] == ["iverilog", "verilator"]
    assert payload["skipped_backends"] == ["vcs"]
    assert payload["backends"][2]["skipped_reason"] == "missing_tool"

    markdown = emit_cosim_backend_sweep_markdown(report, title="Backend Sweep")
    assert "# Backend Sweep" in markdown
    assert "| `iverilog` | ok |" in markdown
    assert "| `vcs` | skipped |" in markdown
