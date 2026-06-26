from rtlgen.archsim import (
    ArchitectureModel,
    build_all_reference_scenarios,
    build_controller_scenario,
    build_cpu_in_order_scenario,
    build_gpu_throughput_scenario,
    build_npu_systolic_scenario,
    build_streaming_datapath_scenario,
    BehaviorSimulator,
    CycleSimulator,
    FlowSpec,
    StageSpec,
    Workload,
)
import json


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


def test_archsim_reference_presets_cover_all_target_domains():
    scenario_names = [scenario.name for scenario in build_all_reference_scenarios()]
    assert scenario_names == [
        "cpu_in_order",
        "gpu_throughput",
        "npu_systolic",
        "controller",
        "streaming_datapath",
    ]


def test_cpu_preset_exposes_memory_contention_and_loads():
    scenario = build_cpu_in_order_scenario(alu_tokens=10, load_tokens=4)

    behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
    cycle = CycleSimulator().run(scenario.model, scenario.workload)

    assert behavior.flow_metrics["load_ops"].bottleneck_stage == "lsu"
    assert cycle.flow_metrics["load_ops"].completed_tokens == 4
    assert cycle.stage_metrics["lsu"].started_tokens == 4


def test_gpu_preset_moves_bytes_through_compute_and_memory_paths():
    scenario = build_gpu_throughput_scenario(warp_tokens=12, memory_tokens=6)

    behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
    cycle = CycleSimulator().run(scenario.model, scenario.workload)

    assert behavior.stage_metrics["coalescer"].bytes_moved > 0
    assert behavior.stage_metrics["shared_mem"].tokens == 6
    assert cycle.flow_metrics["warp_compute"].completed_tokens == 12
    assert cycle.flow_metrics["warp_memory"].completed_tokens == 6


def test_npu_preset_models_activation_and_weight_feeds():
    scenario = build_npu_systolic_scenario(tiles=8, bytes_per_tile=128)

    behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
    cycle = CycleSimulator().run(scenario.model, scenario.workload)

    assert behavior.stage_metrics["mac_array"].tokens == 16
    assert behavior.flow_metrics["activation_tiles"].bytes_moved == 8 * 128 * 3
    assert cycle.stage_metrics["mac_array"].started_tokens == 16


def test_controller_preset_stays_control_dominated():
    scenario = build_controller_scenario(transactions=9)

    behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
    cycle = CycleSimulator().run(scenario.model, scenario.workload)

    assert behavior.stage_metrics["fsm"].kind == "control"
    assert cycle.flow_metrics["control_path"].completed_tokens == 9
    assert cycle.stage_metrics["arbiter"].max_ready_depth >= 1


def test_streaming_datapath_preset_finishes_full_burst():
    scenario = build_streaming_datapath_scenario(tokens=20, bytes_per_token=24)

    behavior = BehaviorSimulator().run(scenario.model, scenario.workload)
    cycle = CycleSimulator().run(scenario.model, scenario.workload)

    assert behavior.flow_metrics["stream_burst"].bytes_moved == 20 * 24 * 4
    assert cycle.flow_metrics["stream_burst"].completed_tokens == 20
    assert cycle.stage_metrics["egress_link"].busy_token_cycles >= 20


def test_archsim_model_and_workload_round_trip_json(tmp_path):
    model = ArchitectureModel([
        StageSpec("dispatch", kind="control", latency=1, initiation_interval=1, capacity=2, queue_depth=4),
        StageSpec("dram", kind="memory", latency=6, initiation_interval=2, capacity=1, queue_depth=8, bandwidth_bytes_per_cycle=32),
    ])
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "dram"), tokens=8, bytes_per_token=64, start_cycle=1, metadata={"class": "cpu"}),
    )

    model_path = model.to_json_file(tmp_path / "model.json")
    workload_path = workload.to_json_file(tmp_path / "workload.json")

    loaded_model = ArchitectureModel.from_json_file(model_path)
    loaded_workload = Workload.from_json_file(workload_path)

    assert json.loads(model_path.read_text(encoding="utf-8"))["stages"][1]["bandwidth_bytes_per_cycle"] == 32
    assert json.loads(workload_path.read_text(encoding="utf-8"))["flows"][0]["metadata"]["class"] == "cpu"
    assert loaded_model.stage("dram").latency == 6
    assert loaded_workload.flows[0].bytes_per_token == 64
