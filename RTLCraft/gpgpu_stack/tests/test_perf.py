from gpgpu_stack import (
    build_gpu_sm_cluster_device_contract,
    build_gpu_sm_seed_device_contract,
    get_gpu_sm_named_profile,
    project_trace_evaluation_to_perf_counters,
    run_gpu_sm_cluster_seed_flow,
    run_gpu_sm_seed_flow,
)


def test_perf_projection_maps_seed_flow_into_declared_schema():
    result = run_gpu_sm_seed_flow(
        launch_id="perf0",
        profile=get_gpu_sm_named_profile("memory_pressure"),
    )
    sample = project_trace_evaluation_to_perf_counters(
        result.trace_evaluation,
        result.perf_counters,
    )

    assert sample.schema.schema_id == "gpu_sm_seed_perf"
    assert sample.values["issued_warps"] > 0
    assert sample.values["writeback_commits"] > 0
    assert sample.values["shared_mem_stall_cycles"] >= 0
    assert sample.metadata["trace_id"] == "perf0_trace"


def test_perf_projection_works_with_device_contract_schema():
    contract = build_gpu_sm_seed_device_contract()
    result = run_gpu_sm_seed_flow(launch_id="perf1")
    sample = project_trace_evaluation_to_perf_counters(
        result.trace_evaluation,
        contract.perf_counters,
    )

    assert set(sample.values) == {counter.name for counter in contract.perf_counters.counters}


def test_cluster_perf_projection_maps_cluster_seed_flow_into_declared_schema():
    result = run_gpu_sm_cluster_seed_flow(
        launch_id="cluster_perf0",
        sm_count=2,
        profile=get_gpu_sm_named_profile("memory_pressure"),
    )
    sample = project_trace_evaluation_to_perf_counters(
        result.trace_evaluation,
        result.perf_counters,
    )

    assert sample.schema.schema_id == "gpu_sm_cluster_seed_perf"
    assert sample.values["issued_warps"] > 0
    assert sample.values["cluster_commit_commits"] >= 0
    assert sample.values["cluster_mem_stall_cycles"] >= 0
    assert sample.values["sm0_issued_warps"] > 0
    assert sample.values["sm1_issued_warps"] > 0
    assert sample.metadata["trace_id"] == "cluster_perf0_cluster_trace"


def test_cluster_perf_projection_works_with_cluster_device_contract_schema():
    contract = build_gpu_sm_cluster_device_contract(sm_count=2)
    result = run_gpu_sm_cluster_seed_flow(launch_id="cluster_perf1", sm_count=2)
    sample = project_trace_evaluation_to_perf_counters(
        result.trace_evaluation,
        contract.perf_counters,
    )

    assert set(sample.values) == {counter.name for counter in contract.perf_counters.counters}
