"""Architecture-side helpers for the GPU SM seed program.

These helpers define the canonical lightweight ``archsim`` view used when the
seed program is evaluated as an architecture candidate rather than as detailed
RTL/DSL.
"""

from __future__ import annotations

from rtlgen_x.archsim import ArchitectureModel, FlowSpec, StageSpec, Workload

from .reference import GpuSmRef, LANES


GPU_SM_FLOW_PATHS: dict[str, tuple[str, ...]] = {
    "warp_compute": ("dispatch", "simd_alu", "writeback"),
    "warp_memory": ("dispatch", "shared_mem", "writeback"),
    "warp_sfu": ("dispatch", "sfu_pipe", "writeback"),
    "warp_gemm": ("dispatch", "gemm_pipe", "writeback"),
}


def build_gpu_sm_cluster_flow_paths(sm_index: int) -> dict[str, tuple[str, ...]]:
    """Build the canonical cluster-side flow paths for one SM slot."""

    if sm_index < 0:
        raise ValueError("sm_index must be >= 0")
    prefix = f"sm{sm_index}"
    return {
        "warp_compute": (
            "cluster_frontend",
            f"{prefix}_dispatch",
            f"{prefix}_simd_alu",
            f"{prefix}_writeback",
            "cluster_commit",
        ),
        "warp_memory": (
            "cluster_frontend",
            f"{prefix}_dispatch",
            "cluster_mem_fabric",
            f"{prefix}_shared_mem",
            f"{prefix}_writeback",
            "cluster_commit",
        ),
        "warp_sfu": (
            "cluster_frontend",
            f"{prefix}_dispatch",
            f"{prefix}_sfu_pipe",
            f"{prefix}_writeback",
            "cluster_commit",
        ),
        "warp_gemm": (
            "cluster_frontend",
            f"{prefix}_dispatch",
            f"{prefix}_gemm_pipe",
            f"{prefix}_writeback",
            "cluster_commit",
        ),
    }


def _build_prefixed_gpu_sm_stage_specs(
    sm_index: int,
    *,
    dispatch_queue_depth: int,
    shared_mem_latency: int,
    shared_mem_bandwidth_bytes_per_cycle: int,
    shared_mem_queue_depth: int,
    simd_latency: int,
    simd_lanes: int,
    simd_queue_depth: int,
    sfu_latency: int,
    sfu_bandwidth_bytes_per_cycle: int,
    sfu_queue_depth: int,
    gemm_latency: int,
    gemm_queue_depth: int,
    writeback_bandwidth_bytes_per_cycle: int,
    writeback_queue_depth: int,
) -> tuple[StageSpec, ...]:
    prefix = f"sm{sm_index}"
    return (
        StageSpec(
            f"{prefix}_dispatch",
            kind="control",
            latency=1,
            initiation_interval=1,
            capacity=1,
            queue_depth=dispatch_queue_depth,
            metadata={"component": "issue", "sm": sm_index},
        ),
        StageSpec(
            f"{prefix}_shared_mem",
            kind="memory",
            latency=shared_mem_latency,
            initiation_interval=1,
            capacity=1,
            queue_depth=shared_mem_queue_depth,
            bandwidth_bytes_per_cycle=shared_mem_bandwidth_bytes_per_cycle,
            metadata={
                "component": "shared_mem",
                "shared_resource": f"{prefix}_mem_pipe",
                "sm": sm_index,
            },
        ),
        StageSpec(
            f"{prefix}_simd_alu",
            kind="compute",
            latency=simd_latency,
            initiation_interval=1,
            capacity=simd_lanes,
            queue_depth=simd_queue_depth,
            metadata={"component": "simd", "lanes": simd_lanes, "sm": sm_index},
        ),
        StageSpec(
            f"{prefix}_sfu_pipe",
            kind="datapath",
            latency=sfu_latency,
            initiation_interval=1,
            capacity=1,
            queue_depth=sfu_queue_depth,
            bandwidth_bytes_per_cycle=sfu_bandwidth_bytes_per_cycle,
            metadata={
                "component": "sfu",
                "shared_resource": f"{prefix}_writeback_cluster",
                "sm": sm_index,
            },
        ),
        StageSpec(
            f"{prefix}_gemm_pipe",
            kind="compute",
            latency=gemm_latency,
            initiation_interval=1,
            capacity=1,
            queue_depth=gemm_queue_depth,
            metadata={
                "component": "gemm",
                "shared_resource": f"{prefix}_writeback_cluster",
                "sm": sm_index,
            },
        ),
        StageSpec(
            f"{prefix}_writeback",
            kind="datapath",
            latency=1,
            initiation_interval=1,
            capacity=1,
            queue_depth=writeback_queue_depth,
            bandwidth_bytes_per_cycle=writeback_bandwidth_bytes_per_cycle,
            metadata={
                "component": "writeback",
                "shared_resource": f"{prefix}_writeback_cluster",
                "sm": sm_index,
            },
        ),
    )


def build_gpu_sm_architecture_model(
    *,
    dispatch_queue_depth: int = 2,
    shared_mem_latency: int = 2,
    shared_mem_bandwidth_bytes_per_cycle: int = 16,
    shared_mem_queue_depth: int = 2,
    simd_latency: int = 1,
    simd_lanes: int = LANES,
    simd_queue_depth: int = 2,
    sfu_latency: int = GpuSmRef.SFU_LATENCY,
    sfu_bandwidth_bytes_per_cycle: int = 16,
    sfu_queue_depth: int = 2,
    gemm_latency: int = GpuSmRef.GEMM_LATENCY,
    gemm_queue_depth: int = 2,
    writeback_bandwidth_bytes_per_cycle: int = 16,
    writeback_queue_depth: int = 2,
) -> ArchitectureModel:
    """Build the canonical architecture model for the GPU SM seed program."""

    return ArchitectureModel(
        (
            StageSpec(
                "dispatch",
                kind="control",
                latency=1,
                initiation_interval=1,
                capacity=1,
                queue_depth=dispatch_queue_depth,
                metadata={"component": "issue"},
            ),
            StageSpec(
                "shared_mem",
                kind="memory",
                latency=shared_mem_latency,
                initiation_interval=1,
                capacity=1,
                queue_depth=shared_mem_queue_depth,
                bandwidth_bytes_per_cycle=shared_mem_bandwidth_bytes_per_cycle,
                metadata={"component": "shared_mem", "shared_resource": "mem_pipe"},
            ),
            StageSpec(
                "simd_alu",
                kind="compute",
                latency=simd_latency,
                initiation_interval=1,
                capacity=simd_lanes,
                queue_depth=simd_queue_depth,
                metadata={"component": "simd", "lanes": simd_lanes},
            ),
            StageSpec(
                "sfu_pipe",
                kind="datapath",
                latency=sfu_latency,
                initiation_interval=1,
                capacity=1,
                queue_depth=sfu_queue_depth,
                bandwidth_bytes_per_cycle=sfu_bandwidth_bytes_per_cycle,
                metadata={"component": "sfu", "shared_resource": "writeback_cluster"},
            ),
            StageSpec(
                "gemm_pipe",
                kind="compute",
                latency=gemm_latency,
                initiation_interval=1,
                capacity=1,
                queue_depth=gemm_queue_depth,
                metadata={"component": "gemm", "shared_resource": "writeback_cluster"},
            ),
            StageSpec(
                "writeback",
                kind="datapath",
                latency=1,
                initiation_interval=1,
                capacity=1,
                queue_depth=writeback_queue_depth,
                bandwidth_bytes_per_cycle=writeback_bandwidth_bytes_per_cycle,
                metadata={"component": "writeback", "shared_resource": "writeback_cluster"},
            ),
        )
    )


def build_gpu_sm_reference_workload(
    *,
    compute_tokens: int = 32,
    memory_tokens: int = 16,
    sfu_tokens: int = 8,
    gemm_tokens: int = 8,
    memory_bytes_per_token: int = 64,
    sfu_bytes_per_token: int = 16,
) -> Workload:
    """Build the canonical architecture-side workload for the GPU SM seed."""

    flows = [FlowSpec("warp_compute", path=GPU_SM_FLOW_PATHS["warp_compute"], tokens=compute_tokens)]
    if memory_tokens > 0:
        flows.append(
            FlowSpec(
                "warp_memory",
                path=GPU_SM_FLOW_PATHS["warp_memory"],
                tokens=memory_tokens,
                bytes_per_token=memory_bytes_per_token,
                start_cycle=1,
            )
        )
    if sfu_tokens > 0:
        flows.append(
            FlowSpec(
                "warp_sfu",
                path=GPU_SM_FLOW_PATHS["warp_sfu"],
                tokens=sfu_tokens,
                bytes_per_token=sfu_bytes_per_token,
                start_cycle=2,
            )
        )
    if gemm_tokens > 0:
        flows.append(
            FlowSpec(
                "warp_gemm",
                path=GPU_SM_FLOW_PATHS["warp_gemm"],
                tokens=gemm_tokens,
                start_cycle=2,
            )
        )
    return Workload.from_flows(*flows)


def build_gpu_sm_cluster_architecture_model(
    *,
    sm_count: int = 2,
    cluster_frontend_queue_depth: int = 4,
    cluster_frontend_capacity: int | None = None,
    cluster_mem_fabric_latency: int = 1,
    cluster_mem_fabric_bandwidth_bytes_per_cycle: int = 32,
    cluster_mem_fabric_queue_depth: int = 4,
    cluster_commit_bandwidth_bytes_per_cycle: int = 32,
    cluster_commit_queue_depth: int = 4,
    cluster_commit_capacity: int | None = None,
    dispatch_queue_depth: int = 2,
    shared_mem_latency: int = 2,
    shared_mem_bandwidth_bytes_per_cycle: int = 16,
    shared_mem_queue_depth: int = 2,
    simd_latency: int = 1,
    simd_lanes: int = LANES,
    simd_queue_depth: int = 2,
    sfu_latency: int = GpuSmRef.SFU_LATENCY,
    sfu_bandwidth_bytes_per_cycle: int = 16,
    sfu_queue_depth: int = 2,
    gemm_latency: int = GpuSmRef.GEMM_LATENCY,
    gemm_queue_depth: int = 2,
    writeback_bandwidth_bytes_per_cycle: int = 16,
    writeback_queue_depth: int = 2,
) -> ArchitectureModel:
    """Build the canonical cluster-side architecture model for the GPU-SM seed line."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")

    frontend_capacity = cluster_frontend_capacity or sm_count
    commit_capacity = cluster_commit_capacity or sm_count
    stages = [
        StageSpec(
            "cluster_frontend",
            kind="control",
            latency=1,
            initiation_interval=1,
            capacity=frontend_capacity,
            queue_depth=cluster_frontend_queue_depth,
            metadata={"component": "cluster_frontend", "sm_count": sm_count},
        ),
        StageSpec(
            "cluster_mem_fabric",
            kind="interconnect",
            latency=cluster_mem_fabric_latency,
            initiation_interval=1,
            capacity=1,
            queue_depth=cluster_mem_fabric_queue_depth,
            bandwidth_bytes_per_cycle=cluster_mem_fabric_bandwidth_bytes_per_cycle,
            metadata={"component": "cluster_mem_fabric", "sm_count": sm_count},
        ),
        StageSpec(
            "cluster_commit",
            kind="datapath",
            latency=1,
            initiation_interval=1,
            capacity=commit_capacity,
            queue_depth=cluster_commit_queue_depth,
            bandwidth_bytes_per_cycle=cluster_commit_bandwidth_bytes_per_cycle,
            metadata={"component": "cluster_commit", "sm_count": sm_count},
        ),
    ]
    for sm_index in range(sm_count):
        stages.extend(
            _build_prefixed_gpu_sm_stage_specs(
                sm_index,
                dispatch_queue_depth=dispatch_queue_depth,
                shared_mem_latency=shared_mem_latency,
                shared_mem_bandwidth_bytes_per_cycle=shared_mem_bandwidth_bytes_per_cycle,
                shared_mem_queue_depth=shared_mem_queue_depth,
                simd_latency=simd_latency,
                simd_lanes=simd_lanes,
                simd_queue_depth=simd_queue_depth,
                sfu_latency=sfu_latency,
                sfu_bandwidth_bytes_per_cycle=sfu_bandwidth_bytes_per_cycle,
                sfu_queue_depth=sfu_queue_depth,
                gemm_latency=gemm_latency,
                gemm_queue_depth=gemm_queue_depth,
                writeback_bandwidth_bytes_per_cycle=writeback_bandwidth_bytes_per_cycle,
                writeback_queue_depth=writeback_queue_depth,
            )
        )
    return ArchitectureModel(tuple(stages))


def build_gpu_sm_cluster_reference_workload(
    *,
    sm_count: int = 2,
    compute_tokens_per_sm: int = 32,
    memory_tokens_per_sm: int = 16,
    sfu_tokens_per_sm: int = 8,
    gemm_tokens_per_sm: int = 8,
    memory_bytes_per_token: int = 64,
    sfu_bytes_per_token: int = 16,
    start_cycle_stride: int = 1,
) -> Workload:
    """Build the canonical cluster-side workload for the GPU-SM seed line."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")
    if start_cycle_stride < 0:
        raise ValueError("start_cycle_stride must be >= 0")

    flows = []
    for sm_index in range(sm_count):
        prefix = f"sm{sm_index}"
        flow_paths = build_gpu_sm_cluster_flow_paths(sm_index)
        start_base = sm_index * start_cycle_stride
        flows.append(
            FlowSpec(
                f"{prefix}_warp_compute",
                path=flow_paths["warp_compute"],
                tokens=compute_tokens_per_sm,
                start_cycle=start_base,
                metadata={"sm": sm_index, "opclass": "simd"},
            )
        )
        if memory_tokens_per_sm > 0:
            flows.append(
                FlowSpec(
                    f"{prefix}_warp_memory",
                    path=flow_paths["warp_memory"],
                    tokens=memory_tokens_per_sm,
                    bytes_per_token=memory_bytes_per_token,
                    start_cycle=start_base + 1,
                    metadata={"sm": sm_index, "opclass": "memory", "memory_space": "shared"},
                )
            )
        if sfu_tokens_per_sm > 0:
            flows.append(
                FlowSpec(
                    f"{prefix}_warp_sfu",
                    path=flow_paths["warp_sfu"],
                    tokens=sfu_tokens_per_sm,
                    bytes_per_token=sfu_bytes_per_token,
                    start_cycle=start_base + 2,
                    metadata={"sm": sm_index, "opclass": "sfu"},
                )
            )
        if gemm_tokens_per_sm > 0:
            flows.append(
                FlowSpec(
                    f"{prefix}_warp_gemm",
                    path=flow_paths["warp_gemm"],
                    tokens=gemm_tokens_per_sm,
                    start_cycle=start_base + 2,
                    metadata={"sm": sm_index, "opclass": "gemm"},
                )
            )
    return Workload.from_flows(*flows)


__all__ = [
    "GPU_SM_FLOW_PATHS",
    "build_gpu_sm_cluster_architecture_model",
    "build_gpu_sm_cluster_flow_paths",
    "build_gpu_sm_cluster_reference_workload",
    "build_gpu_sm_architecture_model",
    "build_gpu_sm_reference_workload",
]
