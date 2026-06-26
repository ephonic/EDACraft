from gpgpu_stack import (
    GpuSmProfileHint,
    RuntimeQueueStub,
    command_to_gpu_sm_cluster_trace,
    command_to_gpu_sm_seed_trace,
    evaluate_gpu_sm_cluster_command,
    evaluate_gpu_sm_command,
)
from gpu_sm.arch import build_gpu_sm_architecture_model, build_gpu_sm_cluster_architecture_model
from rtlgen_x.archsim import rank_bandwidth_upgrades, run_stage_bandwidth_sweep
from gpgpu_stack.abi import KernelMetadata, workload_trace_to_archsim_workload


def test_runtime_queue_stub_builds_stable_launch_command():
    queue = RuntimeQueueStub(queue_name="compute")
    metadata = KernelMetadata(
        kernel_name="gpu_sm_seed",
        grid_dim=(4, 1, 1),
        block_dim=(128, 1, 1),
        shared_mem_bytes=2048,
        register_count=48,
        metadata={"kernel_class": "seed"},
    )

    command = queue.submit(
        metadata,
        args={"src": 4096, "dst": 8192},
        priority=2,
        metadata_overrides={"variant": "wide"},
        descriptor_metadata={"stream": 1},
    )

    assert command.launch.launch_id == "gpu_sm_seed_launch_0"
    assert command.queue == "compute"
    assert command.priority == 2
    assert command.launch.args["dst"] == 8192
    assert command.launch.metadata_overrides["variant"] == "wide"
    assert queue.commands() == (command,)


def test_command_to_gpu_sm_seed_trace_preserves_launch_context():
    queue = RuntimeQueueStub(queue_name="compute")
    command = queue.submit(
        KernelMetadata(kernel_name="gpu_sm_seed", metadata={"kernel_class": "seed"}),
        launch_id="launch7",
        args={"base": 16384},
        metadata_overrides={"variant": "memory_stress"},
    )

    trace = command_to_gpu_sm_seed_trace(
        command,
        profile=GpuSmProfileHint(memory_tokens=24, gemm_tokens=0),
    )

    assert trace.trace_id == "launch7_trace"
    assert trace.kernel.kernel_name == "gpu_sm_seed"
    assert trace.kernel.metadata["launch_id"] == "launch7"
    assert trace.kernel.metadata["variant"] == "memory_stress"
    assert trace.kernel.metadata["args"]["base"] == 16384
    assert tuple(event.flow_name for event in trace.events) == (
        "warp_compute",
        "warp_memory",
        "warp_sfu",
    )


def test_runtime_queue_stub_can_drive_architecture_evaluation():
    queue = RuntimeQueueStub(queue_name="compute")
    command = queue.submit(
        KernelMetadata(kernel_name="gpu_sm_seed"),
        launch_id="launch_eval",
        metadata_overrides={"scenario": "memory_pressure"},
    )
    model = build_gpu_sm_architecture_model(shared_mem_bandwidth_bytes_per_cycle=8)
    trace = command_to_gpu_sm_seed_trace(command)
    workload = workload_trace_to_archsim_workload(trace)
    sweep = run_stage_bandwidth_sweep(model, workload, "shared_mem", bandwidths=(8, 16, 32, 64))
    upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))

    evaluation = evaluate_gpu_sm_command(
        command,
        model,
        sweep_reports=(sweep,),
        upgrade_candidates=upgrades,
    )

    assert evaluation.trace.trace_id == "launch_eval_trace"
    assert evaluation.summary.flow_count == 4
    assert evaluation.summary.sweep_summaries[0].stage_name == "shared_mem"
    assert "launch_eval Architecture Report" in evaluation.markdown


def test_command_to_gpu_sm_cluster_trace_preserves_cluster_context():
    queue = RuntimeQueueStub(queue_name="compute")
    command = queue.submit(
        KernelMetadata(kernel_name="gpu_sm_seed", metadata={"kernel_class": "seed"}),
        launch_id="cluster7",
        args={"base": 4096},
        metadata_overrides={"variant": "cluster_memory_stress"},
    )

    trace = command_to_gpu_sm_cluster_trace(
        command,
        sm_count=2,
        profile=GpuSmProfileHint(memory_tokens=24, gemm_tokens=0),
    )

    assert trace.trace_id == "cluster7_cluster_trace"
    assert trace.kernel.kernel_name == "gpu_sm_seed_cluster"
    assert trace.kernel.metadata["launch_id"] == "cluster7"
    assert trace.kernel.metadata["sm_count"] == 2
    assert tuple(event.flow_name for event in trace.events) == (
        "sm0_warp_compute",
        "sm0_warp_memory",
        "sm0_warp_sfu",
        "sm1_warp_compute",
        "sm1_warp_memory",
        "sm1_warp_sfu",
    )


def test_runtime_queue_stub_can_drive_cluster_architecture_evaluation():
    queue = RuntimeQueueStub(queue_name="compute")
    command = queue.submit(
        KernelMetadata(kernel_name="gpu_sm_seed"),
        launch_id="cluster_eval",
        metadata_overrides={"scenario": "cluster_memory_pressure"},
    )
    model = build_gpu_sm_cluster_architecture_model(
        sm_count=2,
        cluster_mem_fabric_bandwidth_bytes_per_cycle=16,
    )
    trace = command_to_gpu_sm_cluster_trace(command, sm_count=2)
    workload = workload_trace_to_archsim_workload(trace)
    sweep = run_stage_bandwidth_sweep(model, workload, "cluster_mem_fabric", bandwidths=(16, 32, 64))
    upgrades = rank_bandwidth_upgrades(model, workload, candidate_bandwidths=(32, 64))

    evaluation = evaluate_gpu_sm_cluster_command(
        command,
        model,
        sm_count=2,
        sweep_reports=(sweep,),
        upgrade_candidates=upgrades,
    )

    assert evaluation.trace.trace_id == "cluster_eval_cluster_trace"
    assert evaluation.summary.flow_count == 8
    assert evaluation.summary.sweep_summaries[0].stage_name == "cluster_mem_fabric"
    assert "cluster_eval Cluster Architecture Report" in evaluation.markdown
