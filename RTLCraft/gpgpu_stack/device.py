"""Device-side contract bundle for the current GPU-SM flagship seed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Tuple

from gpgpu_stack.abi import AddressMap, PerfCounterSchema
from gpgpu_stack.contracts import (
    build_gpu_sm_cluster_address_map,
    build_gpu_sm_cluster_perf_counter_schema,
    build_gpu_sm_seed_address_map,
    build_gpu_sm_seed_perf_counter_schema,
)


@dataclass(frozen=True)
class DeviceContractBundle:
    """Small software-visible contract bundle for one hardware seed target."""

    name: str
    address_map: AddressMap
    perf_counters: PerfCounterSchema
    supported_queues: Tuple[str, ...] = ("compute",)
    supported_opcodes: Tuple[str, ...] = ("launch_kernel",)
    metadata: Mapping[str, object] = field(default_factory=dict)


def build_gpu_sm_seed_device_contract() -> DeviceContractBundle:
    """Build the current software-visible contract bundle for `gpu_sm`."""

    return DeviceContractBundle(
        name="gpu_sm_seed",
        address_map=build_gpu_sm_seed_address_map(),
        perf_counters=build_gpu_sm_seed_perf_counter_schema(),
        metadata={
            "design": "gpu_sm",
            "role": "gpgpu_flagship_seed",
        },
    )


def build_gpu_sm_cluster_device_contract(
    *,
    sm_count: int = 2,
    shared_mem_window_bytes_per_sm: int = 0x4000,
) -> DeviceContractBundle:
    """Build the current software-visible contract bundle for the cluster seed."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")
    return DeviceContractBundle(
        name="gpu_sm_cluster_seed",
        address_map=build_gpu_sm_cluster_address_map(
            sm_count=sm_count,
            shared_mem_window_bytes_per_sm=shared_mem_window_bytes_per_sm,
        ),
        perf_counters=build_gpu_sm_cluster_perf_counter_schema(sm_count=sm_count),
        metadata={
            "design": "gpu_sm",
            "role": "gpgpu_flagship_cluster_seed",
            "topology": "cluster",
            "sm_count": sm_count,
        },
    )


__all__ = [
    "DeviceContractBundle",
    "build_gpu_sm_cluster_device_contract",
    "build_gpu_sm_seed_device_contract",
]
