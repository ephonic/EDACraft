from gpgpu_stack import (
    GpuSmProfileHint,
    get_gpu_sm_named_profile,
    run_gpu_sm_cluster_seed_flow,
    run_gpu_sm_seed_flow,
)


def test_seed_flow_returns_architecture_and_ppa_reports():
    result = run_gpu_sm_seed_flow(
        launch_id="seed0",
        profile=GpuSmProfileHint(memory_tokens=16, sfu_tokens=8, gemm_tokens=8),
    )

    assert result.command.launch.launch_id == "seed0"
    assert result.address_map.region("perf_counters").kind == "mmio"
    assert result.perf_counters.counter("shared_mem_stall_cycles").category == "stall"
    assert result.perf_counter_sample.values["issued_warps"] > 0
    assert result.trace_evaluation.trace.trace_id == "seed0_trace"
    assert result.trace_evaluation.summary.stage_count == 6
    assert result.trace_evaluation.summary.flow_count == 4
    assert result.ppa_report.module_stats is not None
    assert result.ppa_report.module_stats.module_name == "gpu_sm"
    assert result.ppa_report.architecture_stats is not None
    assert result.architecture_markdown.startswith("# GPU SM Seed Architecture Report\n")
    assert result.ppa_markdown.startswith("# GPU SM Seed PPA Report\n")
    assert "shared_mem" in result.architecture_markdown
    assert "module name: gpu_sm" in result.ppa_markdown


def test_seed_flow_can_study_compute_heavier_profile():
    result = run_gpu_sm_seed_flow(
        launch_id="seed_compute",
        shared_mem_bandwidth_bytes_per_cycle=16,
        profile=get_gpu_sm_named_profile("compute_pressure"),
    )

    assert tuple(flow.name for flow in result.trace_evaluation.workload.flows) == (
        "warp_compute",
        "warp_memory",
        "warp_sfu",
        "warp_gemm",
    )
    assert result.trace_evaluation.summary.flow_count == 4
    assert result.ppa_report.recommendations


def test_cluster_seed_flow_returns_cluster_architecture_report():
    result = run_gpu_sm_cluster_seed_flow(
        launch_id="cluster0",
        sm_count=2,
        cluster_mem_fabric_bandwidth_bytes_per_cycle=16,
        profile=GpuSmProfileHint(memory_tokens=16, sfu_tokens=8, gemm_tokens=8),
    )

    assert result.command.launch.launch_id == "cluster0"
    assert result.address_map.name == "gpu_sm_cluster_seed_addr_map"
    assert result.perf_counters.schema_id == "gpu_sm_cluster_seed_perf"
    assert result.perf_counter_sample.values["cluster_commit_commits"] >= 0
    assert result.perf_counter_sample.values["sm0_issued_warps"] > 0
    assert result.trace_evaluation.trace.trace_id == "cluster0_cluster_trace"
    assert result.trace_evaluation.summary.stage_count == 15
    assert result.trace_evaluation.summary.flow_count == 8
    assert result.architecture_markdown.startswith("# GPU SM Cluster Seed Architecture Report\n")
    assert "cluster_mem_fabric" in result.architecture_markdown
