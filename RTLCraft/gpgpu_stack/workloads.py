"""Workload-trace builders for the GPGPU software stack."""

from __future__ import annotations

from typing import Mapping, Optional

from gpu_sm.arch import GPU_SM_FLOW_PATHS, build_gpu_sm_cluster_flow_paths
from gpu_sm.reference import LANES, NUM_WARPS, REGS_PER_WARP

from gpgpu_stack.abi import KernelMetadata, WorkloadTrace, WorkloadTraceEvent


def _trace_metadata(
    metadata: Optional[Mapping[str, object]],
    *,
    design: str,
    source: str,
) -> dict[str, object]:
    merged = {"design": design, "source": source}
    if metadata:
        merged.update(dict(metadata))
    return merged


def build_gpu_sm_seed_workload_trace(
    *,
    kernel_name: str = "gpu_sm_seed",
    trace_id: str = "gpu_sm_seed_trace",
    compute_tokens: int = 32,
    memory_tokens: int = 16,
    sfu_tokens: int = 8,
    gemm_tokens: int = 8,
    memory_bytes_per_token: int = 64,
    sfu_bytes_per_token: int = 16,
    grid_dim: tuple[int, int, int] = (1, 1, 1),
    block_dim: tuple[int, int, int] = (LANES * NUM_WARPS, 1, 1),
    shared_mem_bytes: int = 1024,
    register_count: int = REGS_PER_WARP,
    metadata: Optional[Mapping[str, object]] = None,
) -> WorkloadTrace:
    """Build the canonical software-side trace for the GPU SM seed program."""

    events = [WorkloadTraceEvent(
        flow_name="warp_compute",
        path=GPU_SM_FLOW_PATHS["warp_compute"],
        tokens=compute_tokens,
        metadata={"opclass": "simd"},
    )]
    if memory_tokens > 0:
        events.append(
            WorkloadTraceEvent(
                flow_name="warp_memory",
                path=GPU_SM_FLOW_PATHS["warp_memory"],
                tokens=memory_tokens,
                bytes_per_token=memory_bytes_per_token,
                start_cycle=1,
                metadata={"opclass": "memory", "memory_space": "shared"},
            )
        )
    if sfu_tokens > 0:
        events.append(
            WorkloadTraceEvent(
                flow_name="warp_sfu",
                path=GPU_SM_FLOW_PATHS["warp_sfu"],
                tokens=sfu_tokens,
                bytes_per_token=sfu_bytes_per_token,
                start_cycle=2,
                metadata={"opclass": "sfu"},
            )
        )
    if gemm_tokens > 0:
        events.append(
            WorkloadTraceEvent(
                flow_name="warp_gemm",
                path=GPU_SM_FLOW_PATHS["warp_gemm"],
                tokens=gemm_tokens,
                start_cycle=2,
                metadata={"opclass": "gemm"},
            )
        )

    return WorkloadTrace(
        kernel=KernelMetadata(
            kernel_name=kernel_name,
            grid_dim=grid_dim,
            block_dim=block_dim,
            shared_mem_bytes=shared_mem_bytes,
            register_count=register_count,
            metadata=_trace_metadata(metadata, design="gpu_sm", source="seed_trace_builder"),
        ),
        events=tuple(events),
        trace_id=trace_id,
        metadata=_trace_metadata(metadata, design="gpu_sm", source="seed_trace_builder"),
    )


def build_gpu_sm_cluster_workload_trace(
    *,
    kernel_name: str = "gpu_sm_cluster_seed",
    trace_id: str = "gpu_sm_cluster_seed_trace",
    sm_count: int = 2,
    compute_tokens_per_sm: int = 32,
    memory_tokens_per_sm: int = 16,
    sfu_tokens_per_sm: int = 8,
    gemm_tokens_per_sm: int = 8,
    memory_bytes_per_token: int = 64,
    sfu_bytes_per_token: int = 16,
    grid_dim: tuple[int, int, int] = (1, 1, 1),
    block_dim: tuple[int, int, int] = (LANES * NUM_WARPS, 1, 1),
    shared_mem_bytes_per_sm: int = 1024,
    register_count: int = REGS_PER_WARP,
    start_cycle_stride: int = 1,
    metadata: Optional[Mapping[str, object]] = None,
) -> WorkloadTrace:
    """Build the canonical software-side cluster workload trace for the GPU-SM seed line."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")
    if start_cycle_stride < 0:
        raise ValueError("start_cycle_stride must be >= 0")

    events = []
    for sm_index in range(sm_count):
        prefix = f"sm{sm_index}"
        flow_paths = build_gpu_sm_cluster_flow_paths(sm_index)
        start_base = sm_index * start_cycle_stride
        events.append(
            WorkloadTraceEvent(
                flow_name=f"{prefix}_warp_compute",
                path=flow_paths["warp_compute"],
                tokens=compute_tokens_per_sm,
                start_cycle=start_base,
                metadata={"opclass": "simd", "sm": sm_index},
            )
        )
        if memory_tokens_per_sm > 0:
            events.append(
                WorkloadTraceEvent(
                    flow_name=f"{prefix}_warp_memory",
                    path=flow_paths["warp_memory"],
                    tokens=memory_tokens_per_sm,
                    bytes_per_token=memory_bytes_per_token,
                    start_cycle=start_base + 1,
                    metadata={"opclass": "memory", "memory_space": "shared", "sm": sm_index},
                )
            )
        if sfu_tokens_per_sm > 0:
            events.append(
                WorkloadTraceEvent(
                    flow_name=f"{prefix}_warp_sfu",
                    path=flow_paths["warp_sfu"],
                    tokens=sfu_tokens_per_sm,
                    bytes_per_token=sfu_bytes_per_token,
                    start_cycle=start_base + 2,
                    metadata={"opclass": "sfu", "sm": sm_index},
                )
            )
        if gemm_tokens_per_sm > 0:
            events.append(
                WorkloadTraceEvent(
                    flow_name=f"{prefix}_warp_gemm",
                    path=flow_paths["warp_gemm"],
                    tokens=gemm_tokens_per_sm,
                    start_cycle=start_base + 2,
                    metadata={"opclass": "gemm", "sm": sm_index},
                )
            )

    cluster_metadata = _trace_metadata(
        metadata,
        design="gpu_sm_cluster",
        source="cluster_trace_builder",
    )
    cluster_metadata["sm_count"] = sm_count

    return WorkloadTrace(
        kernel=KernelMetadata(
            kernel_name=kernel_name,
            grid_dim=grid_dim,
            block_dim=block_dim,
            shared_mem_bytes=shared_mem_bytes_per_sm * sm_count,
            register_count=register_count,
            metadata=dict(cluster_metadata),
        ),
        events=tuple(events),
        trace_id=trace_id,
        metadata=dict(cluster_metadata),
    )


__all__ = [
    "build_gpu_sm_cluster_workload_trace",
    "build_gpu_sm_seed_workload_trace",
]
