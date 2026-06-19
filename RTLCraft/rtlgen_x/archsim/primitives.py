"""Reusable architecture-simulation stage primitives."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence, Tuple

from rtlgen_x.archsim.model import ArchitectureModel, StageSpec


def queue_stage(
    name: str,
    *,
    depth: int,
    latency: int = 1,
    initiation_interval: int = 1,
    kind: str = "control",
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return a queue or FIFO-like buffering stage."""

    return StageSpec(
        name=name,
        kind=kind,
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=1,
        queue_depth=depth,
        metadata=dict(metadata or {}),
    )


def controller_stage(
    name: str,
    *,
    latency: int = 1,
    initiation_interval: int = 1,
    slots: int = 1,
    queue_depth: int = 0,
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return a control/FSM/scheduler stage."""

    return StageSpec(
        name=name,
        kind="control",
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=slots,
        queue_depth=queue_depth,
        metadata=dict(metadata or {}),
    )


def compute_stage(
    name: str,
    *,
    latency: int = 1,
    initiation_interval: int = 1,
    lanes: int = 1,
    queue_depth: int = 0,
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return a compute or ALU-array stage."""

    stage_metadata = {"lanes": lanes}
    if metadata:
        stage_metadata.update(metadata)
    return StageSpec(
        name=name,
        kind="compute",
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=lanes,
        queue_depth=queue_depth,
        metadata=stage_metadata,
    )


def memory_stage(
    name: str,
    *,
    latency: int = 1,
    initiation_interval: int = 1,
    banks: int = 1,
    queue_depth: int = 0,
    bandwidth_bytes_per_cycle: int = 0,
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return a memory, SRAM, cache, or DMA-access stage."""

    stage_metadata = {"banks": banks}
    if metadata:
        stage_metadata.update(metadata)
    return StageSpec(
        name=name,
        kind="memory",
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=banks,
        queue_depth=queue_depth,
        bandwidth_bytes_per_cycle=bandwidth_bytes_per_cycle,
        metadata=stage_metadata,
    )


def interconnect_stage(
    name: str,
    *,
    latency: int = 1,
    initiation_interval: int = 1,
    links: int = 1,
    queue_depth: int = 0,
    bandwidth_bytes_per_cycle: int = 0,
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return an interconnect, router, DMA-link, or coalescer stage."""

    stage_metadata = {"links": links}
    if metadata:
        stage_metadata.update(metadata)
    return StageSpec(
        name=name,
        kind="interconnect",
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=links,
        queue_depth=queue_depth,
        bandwidth_bytes_per_cycle=bandwidth_bytes_per_cycle,
        metadata=stage_metadata,
    )


def datapath_stage(
    name: str,
    *,
    latency: int = 1,
    initiation_interval: int = 1,
    lanes: int = 1,
    queue_depth: int = 0,
    bandwidth_bytes_per_cycle: int = 0,
    metadata: Optional[Mapping[str, object]] = None,
) -> StageSpec:
    """Return a generic datapath packing/unpacking/shuffling stage."""

    stage_metadata = {"lanes": lanes}
    if metadata:
        stage_metadata.update(metadata)
    return StageSpec(
        name=name,
        kind="datapath",
        latency=latency,
        initiation_interval=initiation_interval,
        capacity=lanes,
        queue_depth=queue_depth,
        bandwidth_bytes_per_cycle=bandwidth_bytes_per_cycle,
        metadata=stage_metadata,
    )


def linear_model(stages: Iterable[StageSpec]) -> ArchitectureModel:
    """Build a simple linear architecture model from a stage iterable."""

    return ArchitectureModel(list(stages))


def compose_stage_groups(*groups: Iterable[StageSpec]) -> Tuple[StageSpec, ...]:
    """Flatten multiple stage groups into one ordered stage tuple."""

    stages = []
    for group in groups:
        stages.extend(group)
    return tuple(stages)


def cache_hierarchy(
    prefix: str,
    *,
    l1_ports: int = 1,
    l1_latency: int = 1,
    mshrs: int = 4,
    fabric_links: int = 1,
    l2_banks: int = 2,
    l2_latency: int = 6,
    dram_links: int = 1,
    dram_latency: int = 20,
    line_bytes: int = 64,
) -> Tuple[StageSpec, ...]:
    """Return a lightweight cache/memory hierarchy stage group."""

    missq_depth = max(mshrs, 1)
    return (
        memory_stage(
            f"{prefix}_l1",
            latency=l1_latency,
            initiation_interval=1,
            banks=l1_ports,
            queue_depth=max(l1_ports, missq_depth),
            bandwidth_bytes_per_cycle=max(l1_ports, 1) * line_bytes,
            metadata={"level": "L1", "line_bytes": line_bytes, "mshrs": mshrs},
        ),
        queue_stage(
            f"{prefix}_missq",
            depth=missq_depth,
            latency=1,
            kind="control",
            metadata={"role": "miss_queue"},
        ),
        interconnect_stage(
            f"{prefix}_fabric",
            latency=2,
            initiation_interval=1,
            links=fabric_links,
            queue_depth=max(fabric_links, missq_depth),
            bandwidth_bytes_per_cycle=max(fabric_links, 1) * line_bytes,
            metadata={"role": "cache_fabric", "line_bytes": line_bytes},
        ),
        memory_stage(
            f"{prefix}_l2",
            latency=l2_latency,
            initiation_interval=1,
            banks=l2_banks,
            queue_depth=max(l2_banks, missq_depth),
            bandwidth_bytes_per_cycle=max(l2_banks, 1) * line_bytes,
            metadata={"level": "L2", "line_bytes": line_bytes},
        ),
        memory_stage(
            f"{prefix}_dram",
            latency=dram_latency,
            initiation_interval=max(dram_links, 1),
            banks=dram_links,
            queue_depth=max(dram_links, missq_depth),
            bandwidth_bytes_per_cycle=max(dram_links, 1) * line_bytes,
            metadata={"level": "DRAM", "line_bytes": line_bytes},
        ),
        datapath_stage(
            f"{prefix}_fill",
            latency=1,
            initiation_interval=1,
            lanes=max(l1_ports, 1),
            queue_depth=max(l1_ports, missq_depth),
            bandwidth_bytes_per_cycle=max(l1_ports, 1) * line_bytes,
            metadata={"role": "fill_return", "line_bytes": line_bytes},
        ),
    )


def dma_engine(
    prefix: str,
    *,
    descriptor_slots: int = 1,
    read_channels: int = 1,
    source_banks: int = 1,
    write_channels: int = 1,
    sink_banks: int = 1,
    burst_bytes: int = 64,
    queue_depth: int = 4,
) -> Tuple[StageSpec, ...]:
    """Return a lightweight DMA read/write pipeline stage group."""

    return (
        controller_stage(
            f"{prefix}_desc",
            latency=2,
            initiation_interval=1,
            slots=descriptor_slots,
            queue_depth=queue_depth,
            metadata={"role": "descriptor"},
        ),
        interconnect_stage(
            f"{prefix}_read_link",
            latency=2,
            initiation_interval=1,
            links=read_channels,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(read_channels, 1) * burst_bytes,
            metadata={"role": "dma_read"},
        ),
        memory_stage(
            f"{prefix}_source",
            latency=4,
            initiation_interval=1,
            banks=source_banks,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(source_banks, 1) * burst_bytes,
            metadata={"role": "source_memory"},
        ),
        interconnect_stage(
            f"{prefix}_write_link",
            latency=2,
            initiation_interval=1,
            links=write_channels,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(write_channels, 1) * burst_bytes,
            metadata={"role": "dma_write"},
        ),
        memory_stage(
            f"{prefix}_sink",
            latency=4,
            initiation_interval=1,
            banks=sink_banks,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(sink_banks, 1) * burst_bytes,
            metadata={"role": "sink_memory"},
        ),
        controller_stage(
            f"{prefix}_complete",
            latency=1,
            initiation_interval=1,
            slots=descriptor_slots,
            queue_depth=queue_depth,
            metadata={"role": "completion"},
        ),
    )


def warp_cluster(
    prefix: str,
    *,
    schedulers: int = 1,
    scoreboard_slots: int = 2,
    coalescer_links: int = 1,
    simd_lanes: int = 8,
    shared_banks: int = 4,
    queue_depth: int = 4,
    bytes_per_access: int = 32,
) -> Tuple[StageSpec, ...]:
    """Return a GPU warp scheduler / vector / shared-memory stage group."""

    return (
        controller_stage(
            f"{prefix}_warp_sched",
            latency=1,
            initiation_interval=1,
            slots=schedulers,
            queue_depth=queue_depth,
            metadata={"role": "warp_scheduler"},
        ),
        controller_stage(
            f"{prefix}_scoreboard",
            latency=1,
            initiation_interval=1,
            slots=scoreboard_slots,
            queue_depth=queue_depth,
            metadata={"role": "scoreboard"},
        ),
        interconnect_stage(
            f"{prefix}_coalescer",
            latency=2,
            initiation_interval=1,
            links=coalescer_links,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(coalescer_links, 1) * bytes_per_access,
            metadata={"role": "coalescer"},
        ),
        compute_stage(
            f"{prefix}_vector_alu",
            latency=4,
            initiation_interval=1,
            lanes=simd_lanes,
            queue_depth=max(queue_depth, simd_lanes),
            metadata={"role": "vector_alu"},
        ),
        memory_stage(
            f"{prefix}_shared_mem",
            latency=3,
            initiation_interval=1,
            banks=shared_banks,
            queue_depth=max(queue_depth, shared_banks),
            bandwidth_bytes_per_cycle=max(shared_banks, 1) * bytes_per_access,
            metadata={"role": "shared_memory"},
        ),
        datapath_stage(
            f"{prefix}_commit",
            latency=1,
            initiation_interval=1,
            lanes=max(1, simd_lanes // 2),
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(1, simd_lanes // 2) * bytes_per_access,
            metadata={"role": "warp_commit"},
        ),
    )


def dataflow_array(
    prefix: str,
    *,
    ingress_links: int = 1,
    activation_banks: int = 2,
    weight_banks: int = 2,
    compute_tiles: int = 16,
    reduction_lanes: int = 4,
    egress_links: int = 1,
    bytes_per_tile: int = 64,
    queue_depth: int = 8,
) -> Tuple[StageSpec, ...]:
    """Return a lightweight accelerator dataflow array stage group."""

    return (
        interconnect_stage(
            f"{prefix}_ingress",
            latency=2,
            initiation_interval=1,
            links=ingress_links,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(ingress_links, 1) * bytes_per_tile,
            metadata={"role": "ingress"},
        ),
        memory_stage(
            f"{prefix}_activation",
            latency=2,
            initiation_interval=1,
            banks=activation_banks,
            queue_depth=max(queue_depth, activation_banks),
            bandwidth_bytes_per_cycle=max(activation_banks, 1) * bytes_per_tile,
            metadata={"role": "activation_buffer"},
        ),
        memory_stage(
            f"{prefix}_weight",
            latency=2,
            initiation_interval=1,
            banks=weight_banks,
            queue_depth=max(queue_depth, weight_banks),
            bandwidth_bytes_per_cycle=max(weight_banks, 1) * bytes_per_tile,
            metadata={"role": "weight_buffer"},
        ),
        compute_stage(
            f"{prefix}_array",
            latency=6,
            initiation_interval=1,
            lanes=compute_tiles,
            queue_depth=max(queue_depth, compute_tiles),
            metadata={"role": "compute_array"},
        ),
        datapath_stage(
            f"{prefix}_reduce",
            latency=2,
            initiation_interval=1,
            lanes=reduction_lanes,
            queue_depth=max(queue_depth, reduction_lanes),
            bandwidth_bytes_per_cycle=max(reduction_lanes, 1) * bytes_per_tile,
            metadata={"role": "reduction"},
        ),
        interconnect_stage(
            f"{prefix}_egress",
            latency=2,
            initiation_interval=1,
            links=egress_links,
            queue_depth=queue_depth,
            bandwidth_bytes_per_cycle=max(egress_links, 1) * bytes_per_tile,
            metadata={"role": "egress"},
        ),
    )
