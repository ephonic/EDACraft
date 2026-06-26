"""Shared software/hardware contract schemas for the GPGPU seed line."""

from __future__ import annotations

from gpgpu_stack.abi import AddressMap, AddressRegion, PerfCounterSchema, PerfCounterSpec


def build_gpu_sm_seed_address_map() -> AddressMap:
    """Build the current software-visible address map for the GPU-SM seed."""

    return AddressMap(
        name="gpu_sm_seed_addr_map",
        metadata={"design": "gpu_sm"},
        regions=(
            AddressRegion(
                "csr",
                base=0x0000_0000,
                size_bytes=0x1000,
                kind="csr",
                metadata={"purpose": "control_status"},
            ),
            AddressRegion(
                "cmdq",
                base=0x0001_0000,
                size_bytes=0x1000,
                kind="descriptor",
                metadata={"purpose": "command_queue"},
            ),
            AddressRegion(
                "shared_mem_window",
                base=0x0010_0000,
                size_bytes=0x4000,
                kind="scratchpad",
                metadata={"purpose": "debug_or_bringup_view"},
            ),
            AddressRegion(
                "perf_counters",
                base=0x0002_0000,
                size_bytes=0x1000,
                kind="mmio",
                metadata={"purpose": "performance_counters"},
            ),
        ),
    )


def build_gpu_sm_seed_perf_counter_schema() -> PerfCounterSchema:
    """Build the current software-visible counter schema for the GPU-SM seed."""

    return PerfCounterSchema(
        schema_id="gpu_sm_seed_perf",
        metadata={"design": "gpu_sm"},
        counters=(
            PerfCounterSpec(
                "issued_warps",
                category="throughput",
                description="Number of warp instructions accepted at dispatch.",
            ),
            PerfCounterSpec(
                "writeback_commits",
                category="throughput",
                description="Number of writeback events committed.",
            ),
            PerfCounterSpec(
                "shared_mem_stall_cycles",
                category="stall",
                description="Cycles where shared-memory pressure blocks progress.",
            ),
            PerfCounterSpec(
                "sfu_busy_cycles",
                category="occupancy",
                description="Cycles with SFU pipeline occupancy above zero.",
            ),
            PerfCounterSpec(
                "gemm_busy_cycles",
                category="occupancy",
                description="Cycles with GEMM pipeline occupancy above zero.",
            ),
        ),
    )


def build_gpu_sm_cluster_address_map(
    *,
    sm_count: int = 2,
    shared_mem_window_bytes_per_sm: int = 0x4000,
) -> AddressMap:
    """Build the software-visible address map for the cluster-side GPU-SM seed."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")
    if shared_mem_window_bytes_per_sm < 1:
        raise ValueError("shared_mem_window_bytes_per_sm must be >= 1")

    regions = [
        AddressRegion(
            "cluster_csr",
            base=0x0000_0000,
            size_bytes=0x2000,
            kind="csr",
            metadata={"purpose": "cluster_control_status", "sm_count": sm_count},
        ),
        AddressRegion(
            "cmdq",
            base=0x0001_0000,
            size_bytes=0x2000,
            kind="descriptor",
            metadata={"purpose": "cluster_command_queue", "sm_count": sm_count},
        ),
        AddressRegion(
            "perf_counters",
            base=0x0002_0000,
            size_bytes=0x2000,
            kind="mmio",
            metadata={"purpose": "cluster_performance_counters", "sm_count": sm_count},
        ),
    ]
    shared_mem_base = 0x0010_0000
    for sm_index in range(sm_count):
        regions.append(
            AddressRegion(
                f"sm{sm_index}_shared_mem_window",
                base=shared_mem_base + sm_index * shared_mem_window_bytes_per_sm,
                size_bytes=shared_mem_window_bytes_per_sm,
                kind="scratchpad",
                metadata={"purpose": "sm_shared_mem_debug_or_bringup_view", "sm": sm_index},
            )
        )
    return AddressMap(
        name="gpu_sm_cluster_seed_addr_map",
        metadata={"design": "gpu_sm", "topology": "cluster", "sm_count": sm_count},
        regions=tuple(regions),
    )


def build_gpu_sm_cluster_perf_counter_schema(
    *,
    sm_count: int = 2,
) -> PerfCounterSchema:
    """Build the software-visible counter schema for the cluster-side GPU-SM seed."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")

    counters = [
        PerfCounterSpec(
            "issued_warps",
            category="throughput",
            description="Total warp instructions accepted across the cluster frontend.",
        ),
        PerfCounterSpec(
            "cluster_commit_commits",
            category="throughput",
            description="Number of results committed at the cluster commit stage.",
        ),
        PerfCounterSpec(
            "cluster_mem_stall_cycles",
            category="stall",
            description="Aggregate stall cycles attributed to cluster memory-side pressure.",
        ),
        PerfCounterSpec(
            "cluster_frontend_busy_cycles",
            category="occupancy",
            description="Cycles with cluster frontend occupancy above zero.",
        ),
        PerfCounterSpec(
            "cluster_commit_busy_cycles",
            category="occupancy",
            description="Cycles with cluster commit occupancy above zero.",
        ),
    ]
    for sm_index in range(sm_count):
        prefix = f"sm{sm_index}"
        counters.extend(
            (
                PerfCounterSpec(
                    f"{prefix}_issued_warps",
                    category="throughput",
                    description=f"Warp instructions attributed to {prefix}.",
                ),
                PerfCounterSpec(
                    f"{prefix}_writeback_commits",
                    category="throughput",
                    description=f"Writeback events committed by {prefix}.",
                ),
                PerfCounterSpec(
                    f"{prefix}_shared_mem_stall_cycles",
                    category="stall",
                    description=f"Shared-memory-related stall cycles attributed to {prefix}.",
                ),
                PerfCounterSpec(
                    f"{prefix}_sfu_busy_cycles",
                    category="occupancy",
                    description=f"Cycles with SFU occupancy above zero in {prefix}.",
                ),
                PerfCounterSpec(
                    f"{prefix}_gemm_busy_cycles",
                    category="occupancy",
                    description=f"Cycles with GEMM occupancy above zero in {prefix}.",
                ),
            )
        )
    return PerfCounterSchema(
        schema_id="gpu_sm_cluster_seed_perf",
        metadata={"design": "gpu_sm", "topology": "cluster", "sm_count": sm_count},
        counters=tuple(counters),
    )


__all__ = [
    "build_gpu_sm_cluster_address_map",
    "build_gpu_sm_cluster_perf_counter_schema",
    "build_gpu_sm_seed_address_map",
    "build_gpu_sm_seed_perf_counter_schema",
]
