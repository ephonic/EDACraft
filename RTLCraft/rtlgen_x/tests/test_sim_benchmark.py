from rtlgen_x.sim import (
    benchmark_compiled_speedup,
    benchmark_streaming_capacity,
    build_stress_module,
    iter_stress_input_rows,
    generate_stress_input_buffer,
)


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
