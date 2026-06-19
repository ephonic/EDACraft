from rtlgen_x.archsim import (
    ArchitectureModel,
    BehaviorSimulator,
    CycleSimulator,
    FlowSpec,
    StageSpec,
    Workload,
)


def test_behavior_level_reports_bottleneck_for_cpu_like_pipeline():
    model = ArchitectureModel([
        StageSpec("fetch", kind="control", latency=1, initiation_interval=1, capacity=1),
        StageSpec("execute", kind="compute", latency=2, initiation_interval=2, capacity=1),
        StageSpec("writeback", kind="datapath", latency=1, initiation_interval=1, capacity=1),
    ])
    workload = Workload.from_flows(
        FlowSpec("cpu_pipe", path=("fetch", "execute", "writeback"), tokens=8),
    )

    report = BehaviorSimulator().run(model, workload)

    metrics = report.flow_metrics["cpu_pipe"]
    assert metrics.bottleneck_stage == "execute"
    assert metrics.pipeline_latency == 4
    assert metrics.steady_state_ii == 2.0
    assert metrics.throughput_tokens_per_cycle == 0.5
    assert metrics.total_cycles == 18.0


def test_behavior_level_supports_mixed_npu_and_controller_flows():
    model = ArchitectureModel([
        StageSpec("load", kind="memory", latency=3, initiation_interval=1, capacity=1, bandwidth_bytes_per_cycle=16),
        StageSpec("mac_array", kind="compute", latency=4, initiation_interval=1, capacity=4),
        StageSpec("store", kind="interconnect", latency=2, initiation_interval=1, capacity=1, bandwidth_bytes_per_cycle=16),
        StageSpec("fsm", kind="control", latency=2, initiation_interval=1, capacity=1),
    ])
    workload = Workload.from_flows(
        FlowSpec("npu_tile", path=("load", "mac_array", "store"), tokens=16, bytes_per_token=32),
        FlowSpec("controller", path=("fsm",), tokens=4),
    )

    report = BehaviorSimulator().run(model, workload)

    assert "npu_tile" in report.flow_metrics
    assert "controller" in report.flow_metrics
    assert report.stage_metrics["load"].bytes_moved == 16 * 32
    assert report.stage_metrics["fsm"].kind == "control"
    assert report.makespan_cycles >= report.flow_metrics["npu_tile"].total_cycles


def test_cycle_level_tracks_lightweight_timing_for_datapath_flow():
    model = ArchitectureModel([
        StageSpec("ingress", kind="datapath", latency=1, initiation_interval=1, capacity=1),
        StageSpec("pipe", kind="compute", latency=2, initiation_interval=2, capacity=1),
        StageSpec("egress", kind="datapath", latency=1, initiation_interval=1, capacity=1),
    ])
    workload = Workload.from_flows(
        FlowSpec("stream", path=("ingress", "pipe", "egress"), tokens=4),
    )

    report = CycleSimulator().run(model, workload)

    flow = report.flow_metrics["stream"]
    assert flow.issued_tokens == 4
    assert flow.completed_tokens == 4
    assert flow.first_issue_cycle == 0
    assert flow.last_completion_cycle == 10
    assert flow.total_cycles == 11
    assert report.stage_metrics["pipe"].busy_token_cycles >= 8


def test_cycle_level_handles_shared_resources_for_cpu_and_gpu_style_flows():
    model = ArchitectureModel([
        StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
        StageSpec("shared_mem", kind="memory", latency=2, initiation_interval=1, capacity=1, queue_depth=1),
        StageSpec("alu", kind="compute", latency=1, initiation_interval=1, capacity=2),
    ])
    workload = Workload.from_flows(
        FlowSpec("cpu_ctrl", path=("dispatch", "shared_mem", "alu"), tokens=3),
        FlowSpec("gpu_wave", path=("dispatch", "shared_mem", "alu"), tokens=5, start_cycle=1),
    )

    report = CycleSimulator().run(model, workload)

    assert report.flow_metrics["cpu_ctrl"].completed_tokens == 3
    assert report.flow_metrics["gpu_wave"].completed_tokens == 5
    assert report.stage_metrics["shared_mem"].max_ready_depth >= 1
