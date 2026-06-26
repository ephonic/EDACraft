from rtlgen_x.archsim import BehaviorSimulator

from gpu_sm.arch import (
    GPU_SM_FLOW_PATHS,
    build_gpu_sm_cluster_architecture_model,
    build_gpu_sm_cluster_flow_paths,
    build_gpu_sm_cluster_reference_workload,
    build_gpu_sm_architecture_model,
    build_gpu_sm_reference_workload,
)
from gpu_sm.reference import GpuSmRef, LANES


def test_gpu_sm_architecture_model_matches_seed_structure():
    model = build_gpu_sm_architecture_model()

    assert tuple(model.stages) == (
        "dispatch",
        "shared_mem",
        "simd_alu",
        "sfu_pipe",
        "gemm_pipe",
        "writeback",
    )
    assert model.stage("simd_alu").capacity == LANES
    assert model.stage("sfu_pipe").latency == GpuSmRef.SFU_LATENCY
    assert model.stage("gemm_pipe").latency == GpuSmRef.GEMM_LATENCY
    assert model.stage("sfu_pipe").metadata["shared_resource"] == "writeback_cluster"
    assert model.stage("gemm_pipe").metadata["shared_resource"] == "writeback_cluster"
    assert model.stage("writeback").metadata["shared_resource"] == "writeback_cluster"
    assert model.shared_resource_groups()["writeback_cluster"] == ("sfu_pipe", "gemm_pipe", "writeback")
    assert model.stage("writeback").bandwidth_bytes_per_cycle == 16


def test_gpu_sm_reference_workload_validates_and_exposes_expected_paths():
    model = build_gpu_sm_architecture_model()
    workload = build_gpu_sm_reference_workload()

    model.validate_workload(workload)
    assert tuple(flow.name for flow in workload.flows) == (
        "warp_compute",
        "warp_memory",
        "warp_sfu",
        "warp_gemm",
    )
    assert workload.flows[1].path == GPU_SM_FLOW_PATHS["warp_memory"]
    assert workload.flows[1].bytes_per_token == 64

    behavior = BehaviorSimulator().run(model, workload)
    assert behavior.flow_metrics["warp_sfu"].pipeline_latency == 1 + GpuSmRef.SFU_LATENCY + 1
    assert behavior.flow_metrics["warp_memory"].bottleneck_stage == "shared_mem"


def test_gpu_sm_cluster_architecture_model_exposes_cluster_and_sm_boundaries():
    model = build_gpu_sm_cluster_architecture_model(sm_count=2)

    assert tuple(model.stages)[:3] == (
        "cluster_frontend",
        "cluster_mem_fabric",
        "cluster_commit",
    )
    assert model.stage("cluster_frontend").capacity == 2
    assert model.stage("cluster_mem_fabric").bandwidth_bytes_per_cycle == 32
    assert model.stage("cluster_commit").capacity == 2
    assert model.stage("sm0_sfu_pipe").metadata["shared_resource"] == "sm0_writeback_cluster"
    assert model.stage("sm1_writeback").metadata["shared_resource"] == "sm1_writeback_cluster"
    assert model.shared_resource_groups()["sm0_writeback_cluster"] == (
        "sm0_sfu_pipe",
        "sm0_gemm_pipe",
        "sm0_writeback",
    )


def test_gpu_sm_cluster_flow_paths_and_workload_validate():
    model = build_gpu_sm_cluster_architecture_model(sm_count=2)
    workload = build_gpu_sm_cluster_reference_workload(
        sm_count=2,
        compute_tokens_per_sm=16,
        memory_tokens_per_sm=8,
        sfu_tokens_per_sm=4,
        gemm_tokens_per_sm=0,
    )

    flow_paths = build_gpu_sm_cluster_flow_paths(1)
    model.validate_workload(workload)
    assert flow_paths["warp_memory"] == (
        "cluster_frontend",
        "sm1_dispatch",
        "cluster_mem_fabric",
        "sm1_shared_mem",
        "sm1_writeback",
        "cluster_commit",
    )
    assert tuple(flow.name for flow in workload.flows) == (
        "sm0_warp_compute",
        "sm0_warp_memory",
        "sm0_warp_sfu",
        "sm1_warp_compute",
        "sm1_warp_memory",
        "sm1_warp_sfu",
    )
    behavior = BehaviorSimulator().run(model, workload)
    assert behavior.flow_metrics["sm0_warp_memory"].bottleneck_stage in {"cluster_mem_fabric", "sm0_shared_mem"}
