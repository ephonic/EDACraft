from rtlgen_x.archsim import (
    FlowSpec,
    Workload,
    compute_stage,
    controller_stage,
    datapath_stage,
    interconnect_stage,
    linear_model,
    memory_stage,
    queue_stage,
    rank_bandwidth_upgrades,
    rank_capacity_upgrades,
    rank_initiation_interval_upgrades,
    rank_latency_upgrades,
    rank_queue_depth_upgrades,
    run_stage_bandwidth_sweep,
    run_stage_capacity_sweep,
    run_stage_initiation_interval_sweep,
    run_stage_latency_sweep,
    run_stage_queue_depth_sweep,
)


def _shared_resource_model():
    model = linear_model(
        [
            controller_stage("dispatch", latency=1, initiation_interval=1, slots=1, queue_depth=4),
            memory_stage(
                "shared_mem",
                latency=3,
                initiation_interval=3,
                banks=1,
                queue_depth=2,
                bandwidth_bytes_per_cycle=16,
            ),
            compute_stage("alu", latency=1, initiation_interval=1, lanes=2, queue_depth=2),
            datapath_stage("commit", latency=1, initiation_interval=1, lanes=2, queue_depth=2),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("cpu", path=("dispatch", "shared_mem", "alu", "commit"), tokens=6, bytes_per_token=16),
        FlowSpec(
            "gpu",
            path=("dispatch", "shared_mem", "alu", "commit"),
            tokens=10,
            bytes_per_token=16,
            start_cycle=1,
        ),
    )
    return model, workload


def _wide_frontend_model():
    model = linear_model(
        [
            controller_stage("dispatch", latency=2, initiation_interval=1, slots=4, queue_depth=1),
            compute_stage("vector_alu", latency=1, initiation_interval=1, lanes=4, queue_depth=4),
            datapath_stage("commit", latency=1, initiation_interval=1, lanes=4, queue_depth=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("vector_stream", path=("dispatch", "vector_alu", "commit"), tokens=16),
    )
    return model, workload


def _bandwidth_bound_model():
    model = linear_model(
        [
            controller_stage("dispatch", latency=1, initiation_interval=1, slots=1, queue_depth=4),
            memory_stage(
                "dram",
                latency=2,
                initiation_interval=1,
                banks=1,
                queue_depth=4,
                bandwidth_bytes_per_cycle=16,
            ),
            datapath_stage("commit", latency=1, initiation_interval=1, lanes=1, queue_depth=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("tensor_load", path=("dispatch", "dram", "commit"), tokens=8, bytes_per_token=64),
    )
    return model, workload


def test_archsim_primitives_capture_expected_stage_shapes():
    model = linear_model(
        [
            queue_stage("q", depth=8),
            controller_stage("sched", latency=2, slots=2, queue_depth=2),
            memory_stage("sram", latency=3, banks=4, bandwidth_bytes_per_cycle=64),
            interconnect_stage("noc", latency=2, links=2, bandwidth_bytes_per_cycle=32),
            compute_stage("mac", latency=4, lanes=8),
            datapath_stage("pack", latency=1, lanes=2, bandwidth_bytes_per_cycle=16),
        ]
    )

    assert model.stage("q").queue_depth == 8
    assert model.stage("sched").capacity == 2
    assert model.stage("sram").capacity == 4
    assert model.stage("sram").bandwidth_bytes_per_cycle == 64
    assert model.stage("noc").kind == "interconnect"
    assert model.stage("mac").metadata["lanes"] == 8
    assert model.stage("pack").kind == "datapath"


def test_capacity_sweep_reduces_cycles_for_memory_bottleneck():
    model, workload = _shared_resource_model()

    report = run_stage_capacity_sweep(model, workload, "shared_mem", capacities=(1, 2, 4))

    assert report.stage_name == "shared_mem"
    assert report.knob == "capacity"
    assert report.points[0].capacity == 1
    assert report.points[0].cycle_total_cycles == report.baseline_cycles
    assert report.best_point.capacity in {2, 4}
    assert report.best_point.cycle_total_cycles < report.baseline_cycles
    assert report.best_point.aggregate_throughput_tokens_per_cycle > report.baseline_throughput_tokens_per_cycle


def test_initiation_interval_sweep_reduces_cycles_for_slow_stage():
    model, workload = _shared_resource_model()

    report = run_stage_initiation_interval_sweep(model, workload, "shared_mem", initiation_intervals=(3, 2, 1))

    assert report.knob == "initiation_interval"
    assert report.points[0].initiation_interval == 3
    assert report.best_point.initiation_interval == 1
    assert report.best_point.cycle_total_cycles < report.baseline_cycles


def test_latency_sweep_reduces_cycles_for_slow_stage():
    model, workload = _shared_resource_model()

    report = run_stage_latency_sweep(model, workload, "shared_mem", latencies=(3, 2, 1))

    assert report.knob == "latency"
    assert report.points[0].latency == 3
    assert report.best_point.latency == 1
    assert report.best_point.cycle_total_cycles < report.baseline_cycles


def test_queue_depth_sweep_reduces_cycles_for_underbuffered_frontend():
    model, workload = _wide_frontend_model()

    report = run_stage_queue_depth_sweep(model, workload, "dispatch", queue_depths=(1, 2, 4))

    assert report.knob == "queue_depth"
    assert report.points[0].queue_depth == 1
    assert report.best_point.queue_depth == 4
    assert report.best_point.cycle_total_cycles < report.baseline_cycles


def test_bandwidth_sweep_reduces_cycles_for_bandwidth_bound_stage():
    model, workload = _bandwidth_bound_model()

    report = run_stage_bandwidth_sweep(model, workload, "dram", bandwidths=(16, 32, 64))

    assert report.knob == "bandwidth_bytes_per_cycle"
    assert report.points[0].bandwidth_bytes_per_cycle == 16
    assert report.best_point.bandwidth_bytes_per_cycle == 64
    assert report.best_point.cycle_total_cycles < report.baseline_cycles


def test_upgrade_ranking_highlights_shared_memory_first():
    model, workload = _shared_resource_model()

    capacity_candidates = rank_capacity_upgrades(model, workload, candidate_capacities=(2, 4))
    ii_candidates = rank_initiation_interval_upgrades(model, workload, candidate_initiation_intervals=(2, 1))
    latency_candidates = rank_latency_upgrades(model, workload, candidate_latencies=(2, 1))

    assert capacity_candidates
    assert ii_candidates
    assert latency_candidates
    assert capacity_candidates[0].stage_name == "shared_mem"
    assert ii_candidates[0].stage_name == "shared_mem"
    assert latency_candidates[0].stage_name == "shared_mem"
    assert capacity_candidates[0].cycle_reduction > 0
    assert ii_candidates[0].cycle_reduction > 0
    assert latency_candidates[0].cycle_reduction > 0


def test_queue_depth_and_bandwidth_rankings_surface_the_right_stage():
    queue_model, queue_workload = _wide_frontend_model()
    bandwidth_model, bandwidth_workload = _bandwidth_bound_model()

    queue_candidates = rank_queue_depth_upgrades(queue_model, queue_workload, candidate_queue_depths=(2, 4, 8))
    bandwidth_candidates = rank_bandwidth_upgrades(
        bandwidth_model,
        bandwidth_workload,
        candidate_bandwidths=(32, 64, 128),
    )

    assert queue_candidates
    assert bandwidth_candidates
    assert queue_candidates[0].stage_name == "dispatch"
    assert queue_candidates[0].recommended_value >= 4
    assert bandwidth_candidates[0].stage_name == "dram"
    assert bandwidth_candidates[0].recommended_value >= 64
    assert bandwidth_candidates[0].cycle_reduction > 0
