from rtlgen.archsim import (
    ArchitectureModel,
    BehaviorSimulator,
    CycleSimulator,
    FlowSpec,
    StageSpec,
    Workload,
    build_all_advanced_scenarios,
    build_cache_hierarchy_scenario,
    build_dma_copy_scenario,
    build_gpu_warp_cluster_scenario,
    build_npu_dataflow_scenario,
    cache_hierarchy,
    compose_stage_groups,
    dataflow_array,
    dma_engine,
    linear_model,
    run_stage_capacity_sweep,
    run_stage_latency_sweep,
    warp_cluster,
)


def test_advanced_stage_groups_expose_expected_shapes_and_roles():
    stages = compose_stage_groups(
        cache_hierarchy("cache0", l1_ports=2, l2_banks=4, dram_links=2),
        dma_engine("dma0", read_channels=2, write_channels=2, source_banks=4, sink_banks=4),
        warp_cluster("sm0", schedulers=2, simd_lanes=16, shared_banks=8),
        dataflow_array("npu0", activation_banks=4, weight_banks=4, compute_tiles=32),
    )
    model = linear_model(stages)

    assert model.stage("cache0_l1").metadata["level"] == "L1"
    assert model.stage("cache0_dram").capacity == 2
    assert model.stage("dma0_read_link").metadata["role"] == "dma_read"
    assert model.stage("dma0_sink").metadata["role"] == "sink_memory"
    assert model.stage("sm0_vector_alu").metadata["lanes"] == 16
    assert model.stage("sm0_shared_mem").capacity == 8
    assert model.stage("npu0_array").metadata["lanes"] == 32
    assert model.stage("npu0_reduce").metadata["role"] == "reduction"


def test_all_advanced_reference_scenarios_run_to_completion():
    behavior_sim = BehaviorSimulator()
    cycle_sim = CycleSimulator()

    for scenario in build_all_advanced_scenarios():
        behavior = behavior_sim.run(scenario.model, scenario.workload)
        cycle = cycle_sim.run(scenario.model, scenario.workload)
        total_tokens = sum(flow.tokens for flow in scenario.workload.flows)

        assert behavior.total_tokens == total_tokens
        assert sum(flow.completed_tokens for flow in cycle.flow_metrics.values()) == total_tokens
        assert cycle.total_cycles >= 1


def test_cache_hierarchy_l1_capacity_sweep_improves_total_cycles():
    scenario = build_cache_hierarchy_scenario(l1_hits=12, l2_hits=8, dram_misses=10, line_bytes=64)

    report = run_stage_capacity_sweep(
        scenario.model,
        scenario.workload,
        "cpu_cache_l1",
        capacities=(2, 4, 8),
    )

    assert report.best_point.capacity in {4, 8}
    assert report.best_point.cycle_total_cycles < report.baseline_cycles


def test_dma_copy_source_latency_sweep_improves_throughput():
    scenario = build_dma_copy_scenario(transfers=24, burst_bytes=64)

    report = run_stage_latency_sweep(
        scenario.model,
        scenario.workload,
        "dma0_source",
        latencies=(4, 3, 2, 1),
    )

    assert report.best_point.cycle_total_cycles < report.baseline_cycles
    assert report.best_point.aggregate_throughput_tokens_per_cycle > report.baseline_throughput_tokens_per_cycle


def test_gpu_and_npu_advanced_scenarios_respond_to_upgrade_sweeps():
    gpu = build_gpu_warp_cluster_scenario(warp_compute=24, warp_memory=16, bytes_per_access=32)
    npu = build_npu_dataflow_scenario(tiles=20, bytes_per_tile=64)

    gpu_report = run_stage_capacity_sweep(gpu.model, gpu.workload, "sm0_coalescer", capacities=(1, 2, 4))
    npu_report = run_stage_latency_sweep(npu.model, npu.workload, "npu0_array", latencies=(6, 4, 2, 1))

    assert gpu_report.best_point.cycle_total_cycles < gpu_report.baseline_cycles
    assert npu_report.best_point.cycle_total_cycles < npu_report.baseline_cycles


def test_shared_resource_groups_and_contention_capacity_are_exposed():
    model = ArchitectureModel(
        (
            StageSpec("a", kind="compute", capacity=2, metadata={"shared_resource": "wb"}),
            StageSpec("b", kind="datapath", capacity=1, metadata={"shared_resource": "wb"}),
            StageSpec("c", kind="memory", capacity=4),
        )
    )

    assert model.shared_resource_groups() == {"wb": ("a", "b")}
    assert model.stage_contention_capacity("a") == 3
    assert model.stage_contention_capacity("b") == 3
    assert model.stage_contention_capacity("c") == 4


def test_cycle_simulator_tracks_shared_resource_busy_cycles():
    model = ArchitectureModel(
        (
            StageSpec("issue", kind="control", capacity=1, queue_depth=4),
            StageSpec("pipe0", kind="compute", capacity=1, latency=2, queue_depth=4, metadata={"shared_resource": "exec"}),
            StageSpec("pipe1", kind="compute", capacity=1, latency=2, queue_depth=4, metadata={"shared_resource": "exec"}),
        )
    )
    workload = Workload.from_flows(
        FlowSpec("f0", path=("issue", "pipe0"), tokens=4),
        FlowSpec("f1", path=("issue", "pipe1"), tokens=4, start_cycle=1),
    )

    report = CycleSimulator().run(model, workload)

    assert report.stage_metrics["pipe0"].shared_resource == "exec"
    assert report.stage_metrics["pipe1"].shared_resource == "exec"
    assert report.stage_metrics["pipe0"].shared_resource_busy_cycles >= report.stage_metrics["pipe0"].busy_token_cycles
    assert report.stage_metrics["pipe1"].shared_resource_busy_cycles >= report.stage_metrics["pipe1"].busy_token_cycles
