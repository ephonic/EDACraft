"""Reusable architecture-simulation presets for common hardware domains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from rtlgen_x.archsim.model import ArchitectureModel, FlowSpec, StageSpec, Workload
from rtlgen_x.archsim.primitives import (
    cache_hierarchy,
    compose_stage_groups,
    controller_stage,
    dataflow_array,
    dma_engine,
    linear_model,
    warp_cluster,
)


@dataclass(frozen=True)
class ArchitectureScenario:
    """One ready-to-run architecture exploration scenario."""

    name: str
    model: ArchitectureModel
    workload: Workload


def build_cpu_in_order_scenario(
    *,
    alu_tokens: int = 12,
    load_tokens: int = 6,
) -> ArchitectureScenario:
    """Return a small in-order CPU pipeline with ALU and load traffic."""

    model = ArchitectureModel(
        [
            StageSpec("fetch", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
            StageSpec("decode", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
            StageSpec("execute", kind="compute", latency=2, initiation_interval=1, capacity=1, queue_depth=1),
            StageSpec("lsu", kind="memory", latency=3, initiation_interval=2, capacity=1, queue_depth=2),
            StageSpec("writeback", kind="datapath", latency=1, initiation_interval=1, capacity=1),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec("alu_ops", path=("fetch", "decode", "execute", "writeback"), tokens=alu_tokens),
        FlowSpec(
            "load_ops",
            path=("fetch", "decode", "execute", "lsu", "writeback"),
            tokens=load_tokens,
            bytes_per_token=8,
            start_cycle=1,
        ),
    )
    return ArchitectureScenario(name="cpu_in_order", model=model, workload=workload)


def build_gpu_throughput_scenario(
    *,
    warp_tokens: int = 16,
    memory_tokens: int = 8,
) -> ArchitectureScenario:
    """Return a simplified GPU SM-style throughput machine."""

    model = ArchitectureModel(
        [
            StageSpec("warp_sched", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=4),
            StageSpec("coalescer", kind="interconnect", latency=2, initiation_interval=1, capacity=1, queue_depth=4),
            StageSpec("vector_alu", kind="compute", latency=4, initiation_interval=1, capacity=8, queue_depth=8),
            StageSpec("shared_mem", kind="memory", latency=3, initiation_interval=1, capacity=2, queue_depth=4),
            StageSpec("commit", kind="datapath", latency=1, initiation_interval=1, capacity=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec(
            "warp_compute",
            path=("warp_sched", "coalescer", "vector_alu", "commit"),
            tokens=warp_tokens,
            bytes_per_token=16,
        ),
        FlowSpec(
            "warp_memory",
            path=("warp_sched", "coalescer", "shared_mem", "commit"),
            tokens=memory_tokens,
            bytes_per_token=32,
            start_cycle=2,
        ),
    )
    return ArchitectureScenario(name="gpu_throughput", model=model, workload=workload)


def build_npu_systolic_scenario(
    *,
    tiles: int = 16,
    bytes_per_tile: int = 64,
) -> ArchitectureScenario:
    """Return a lightweight NPU tile/load/compute/store scenario."""

    model = ArchitectureModel(
        [
            StageSpec("dma_in", kind="interconnect", latency=2, initiation_interval=1, capacity=1, queue_depth=4),
            StageSpec("activation_sram", kind="memory", latency=2, initiation_interval=1, capacity=2, queue_depth=8),
            StageSpec("weight_sram", kind="memory", latency=2, initiation_interval=1, capacity=2, queue_depth=8),
            StageSpec("mac_array", kind="compute", latency=6, initiation_interval=1, capacity=16, queue_depth=16),
            StageSpec("dma_out", kind="interconnect", latency=2, initiation_interval=1, capacity=1, queue_depth=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec(
            "activation_tiles",
            path=("dma_in", "activation_sram", "mac_array", "dma_out"),
            tokens=tiles,
            bytes_per_token=bytes_per_tile,
        ),
        FlowSpec(
            "weight_tiles",
            path=("dma_in", "weight_sram", "mac_array"),
            tokens=tiles,
            bytes_per_token=bytes_per_tile,
        ),
    )
    return ArchitectureScenario(name="npu_systolic", model=model, workload=workload)


def build_controller_scenario(
    *,
    transactions: int = 12,
) -> ArchitectureScenario:
    """Return a control-dominated controller/protocol scenario."""

    model = ArchitectureModel(
        [
            StageSpec("request_q", kind="control", latency=1, initiation_interval=1, capacity=1, queue_depth=4),
            StageSpec("fsm", kind="control", latency=2, initiation_interval=1, capacity=1, queue_depth=2),
            StageSpec("arbiter", kind="interconnect", latency=1, initiation_interval=1, capacity=1, queue_depth=2),
            StageSpec("response_q", kind="datapath", latency=1, initiation_interval=1, capacity=1, queue_depth=4),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec(
            "control_path",
            path=("request_q", "fsm", "arbiter", "response_q"),
            tokens=transactions,
            start_cycle=0,
        ),
    )
    return ArchitectureScenario(name="controller", model=model, workload=workload)


def build_streaming_datapath_scenario(
    *,
    tokens: int = 32,
    bytes_per_token: int = 16,
) -> ArchitectureScenario:
    """Return a generic streaming datapath scenario."""

    model = ArchitectureModel(
        [
            StageSpec("ingress_fifo", kind="datapath", latency=1, initiation_interval=1, capacity=1, queue_depth=8),
            StageSpec("unpack", kind="datapath", latency=1, initiation_interval=1, capacity=2, queue_depth=4),
            StageSpec("transform", kind="compute", latency=3, initiation_interval=1, capacity=2, queue_depth=4),
            StageSpec("pack", kind="datapath", latency=1, initiation_interval=1, capacity=2, queue_depth=4),
            StageSpec("egress_link", kind="interconnect", latency=2, initiation_interval=1, capacity=1, queue_depth=8),
        ]
    )
    workload = Workload.from_flows(
        FlowSpec(
            "stream_burst",
            path=("ingress_fifo", "unpack", "transform", "pack", "egress_link"),
            tokens=tokens,
            bytes_per_token=bytes_per_token,
        ),
    )
    return ArchitectureScenario(name="streaming_datapath", model=model, workload=workload)


def build_all_reference_scenarios() -> Tuple[ArchitectureScenario, ...]:
    """Return one preset scenario per target architecture family."""

    return (
        build_cpu_in_order_scenario(),
        build_gpu_throughput_scenario(),
        build_npu_systolic_scenario(),
        build_controller_scenario(),
        build_streaming_datapath_scenario(),
    )


def build_cache_hierarchy_scenario(
    *,
    l1_hits: int = 24,
    l2_hits: int = 8,
    dram_misses: int = 4,
    line_bytes: int = 64,
) -> ArchitectureScenario:
    """Return a lightweight cache/L2/DRAM hierarchy exploration scenario."""

    model = linear_model(
        cache_hierarchy(
            "cpu_cache",
            l1_ports=2,
            mshrs=8,
            fabric_links=1,
            l2_banks=2,
            dram_links=1,
            line_bytes=line_bytes,
        )
    )
    workload = Workload.from_flows(
        FlowSpec(
            "l1_hit",
            path=("cpu_cache_l1", "cpu_cache_fill"),
            tokens=l1_hits,
            bytes_per_token=line_bytes,
        ),
        FlowSpec(
            "l2_hit",
            path=("cpu_cache_l1", "cpu_cache_missq", "cpu_cache_fabric", "cpu_cache_l2", "cpu_cache_fill"),
            tokens=l2_hits,
            bytes_per_token=line_bytes,
            start_cycle=1,
        ),
        FlowSpec(
            "dram_miss",
            path=(
                "cpu_cache_l1",
                "cpu_cache_missq",
                "cpu_cache_fabric",
                "cpu_cache_l2",
                "cpu_cache_dram",
                "cpu_cache_fill",
            ),
            tokens=dram_misses,
            bytes_per_token=line_bytes,
            start_cycle=2,
        ),
    )
    return ArchitectureScenario(name="cache_hierarchy", model=model, workload=workload)


def build_dma_copy_scenario(
    *,
    transfers: int = 16,
    burst_bytes: int = 64,
) -> ArchitectureScenario:
    """Return a DMA copy/move scenario with descriptor, read, and write traffic."""

    model = linear_model(
        dma_engine(
            "dma0",
            descriptor_slots=1,
            read_channels=1,
            source_banks=2,
            write_channels=1,
            sink_banks=2,
            burst_bytes=burst_bytes,
            queue_depth=4,
        )
    )
    workload = Workload.from_flows(
        FlowSpec(
            "dma_copy",
            path=("dma0_desc", "dma0_read_link", "dma0_source", "dma0_write_link", "dma0_sink", "dma0_complete"),
            tokens=transfers,
            bytes_per_token=burst_bytes,
        ),
    )
    return ArchitectureScenario(name="dma_copy", model=model, workload=workload)


def build_gpu_warp_cluster_scenario(
    *,
    warp_compute: int = 20,
    warp_memory: int = 10,
    bytes_per_access: int = 32,
) -> ArchitectureScenario:
    """Return a more realistic warp-scheduler/shared-memory GPU cluster scenario."""

    model = linear_model(
        warp_cluster(
            "sm0",
            schedulers=2,
            scoreboard_slots=2,
            coalescer_links=1,
            simd_lanes=16,
            shared_banks=4,
            queue_depth=8,
            bytes_per_access=bytes_per_access,
        )
    )
    workload = Workload.from_flows(
        FlowSpec(
            "warp_compute",
            path=("sm0_warp_sched", "sm0_scoreboard", "sm0_vector_alu", "sm0_commit"),
            tokens=warp_compute,
            bytes_per_token=bytes_per_access,
        ),
        FlowSpec(
            "warp_shared",
            path=("sm0_warp_sched", "sm0_scoreboard", "sm0_coalescer", "sm0_shared_mem", "sm0_commit"),
            tokens=warp_memory,
            bytes_per_token=bytes_per_access,
            start_cycle=1,
        ),
    )
    return ArchitectureScenario(name="gpu_warp_cluster", model=model, workload=workload)


def build_npu_dataflow_scenario(
    *,
    tiles: int = 16,
    bytes_per_tile: int = 64,
) -> ArchitectureScenario:
    """Return a buffered accelerator dataflow scenario."""

    model = linear_model(
        dataflow_array(
            "npu0",
            ingress_links=1,
            activation_banks=4,
            weight_banks=4,
            compute_tiles=16,
            reduction_lanes=4,
            egress_links=1,
            bytes_per_tile=bytes_per_tile,
            queue_depth=8,
        )
    )
    workload = Workload.from_flows(
        FlowSpec(
            "activation_wave",
            path=("npu0_ingress", "npu0_activation", "npu0_array", "npu0_reduce", "npu0_egress"),
            tokens=tiles,
            bytes_per_token=bytes_per_tile,
        ),
        FlowSpec(
            "weight_wave",
            path=("npu0_ingress", "npu0_weight", "npu0_array", "npu0_reduce", "npu0_egress"),
            tokens=tiles,
            bytes_per_token=bytes_per_tile,
            start_cycle=1,
        ),
    )
    return ArchitectureScenario(name="npu_dataflow", model=model, workload=workload)


def build_all_advanced_scenarios() -> Tuple[ArchitectureScenario, ...]:
    """Return more detailed reference scenarios for advanced exploration."""

    return (
        build_cache_hierarchy_scenario(),
        build_dma_copy_scenario(),
        build_gpu_warp_cluster_scenario(),
        build_npu_dataflow_scenario(),
    )
