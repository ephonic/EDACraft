"""Named workload profiles for the current GPGPU seed line."""

from __future__ import annotations

from gpgpu_stack.runtime import GpuSmProfileHint


def gpu_sm_baseline_profile() -> GpuSmProfileHint:
    return GpuSmProfileHint(
        compute_tokens=32,
        memory_tokens=16,
        sfu_tokens=8,
        gemm_tokens=8,
        memory_bytes_per_token=64,
        sfu_bytes_per_token=16,
    )


def gpu_sm_memory_pressure_profile() -> GpuSmProfileHint:
    return GpuSmProfileHint(
        compute_tokens=24,
        memory_tokens=24,
        sfu_tokens=6,
        gemm_tokens=4,
        memory_bytes_per_token=128,
        sfu_bytes_per_token=16,
    )


def gpu_sm_compute_pressure_profile() -> GpuSmProfileHint:
    return GpuSmProfileHint(
        compute_tokens=48,
        memory_tokens=4,
        sfu_tokens=8,
        gemm_tokens=12,
        memory_bytes_per_token=32,
        sfu_bytes_per_token=16,
    )


def gpu_sm_sfu_pressure_profile() -> GpuSmProfileHint:
    return GpuSmProfileHint(
        compute_tokens=16,
        memory_tokens=8,
        sfu_tokens=24,
        gemm_tokens=4,
        memory_bytes_per_token=32,
        sfu_bytes_per_token=32,
    )


GPU_SM_NAMED_PROFILES: dict[str, GpuSmProfileHint] = {
    "baseline": gpu_sm_baseline_profile(),
    "memory_pressure": gpu_sm_memory_pressure_profile(),
    "compute_pressure": gpu_sm_compute_pressure_profile(),
    "sfu_pressure": gpu_sm_sfu_pressure_profile(),
}


def get_gpu_sm_named_profile(name: str) -> GpuSmProfileHint:
    try:
        return GPU_SM_NAMED_PROFILES[name]
    except KeyError as exc:
        known = ", ".join(sorted(GPU_SM_NAMED_PROFILES))
        raise KeyError(f"unknown gpu_sm profile '{name}'; known profiles: {known}") from exc


__all__ = [
    "GPU_SM_NAMED_PROFILES",
    "get_gpu_sm_named_profile",
    "gpu_sm_baseline_profile",
    "gpu_sm_compute_pressure_profile",
    "gpu_sm_memory_pressure_profile",
    "gpu_sm_sfu_pressure_profile",
]
