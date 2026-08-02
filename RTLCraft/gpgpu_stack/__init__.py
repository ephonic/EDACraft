"""Minimal software-stack side helpers for the GPGPU flagship effort."""

from gpgpu_stack.analysis import (
    TraceArchitectureEvaluation,
    emit_workload_trace_architecture_report_markdown,
    evaluate_workload_trace,
)
from gpgpu_stack.abi import (
    AddressMap,
    AddressRegion,
    CommandDescriptor,
    KernelLaunch,
    KernelMetadata,
    PerfCounterSchema,
    PerfCounterSpec,
    WorkloadTrace,
    WorkloadTraceEvent,
    workload_trace_to_archsim_workload,
)
from gpgpu_stack.contracts import (
    build_gpu_sm_cluster_address_map,
    build_gpu_sm_cluster_perf_counter_schema,
    build_gpu_sm_seed_address_map,
    build_gpu_sm_seed_perf_counter_schema,
)
from gpgpu_stack.device import (
    DeviceContractBundle,
    build_gpu_sm_cluster_device_contract,
    build_gpu_sm_seed_device_contract,
)
from gpgpu_stack.perf import (
    PerfCounterSample,
    project_trace_evaluation_to_perf_counters,
)
from gpgpu_stack.profiles import (
    GPU_SM_NAMED_PROFILES,
    get_gpu_sm_named_profile,
    gpu_sm_baseline_profile,
    gpu_sm_compute_pressure_profile,
    gpu_sm_memory_pressure_profile,
    gpu_sm_sfu_pressure_profile,
)
from gpgpu_stack.workloads import build_gpu_sm_seed_workload_trace
from gpgpu_stack.runtime import (
    GpuSmProfileHint,
    RuntimeQueueStub,
    build_launch_command,
    command_to_gpu_sm_cluster_trace,
    command_to_gpu_sm_seed_trace,
    evaluate_gpu_sm_cluster_command,
    evaluate_gpu_sm_command,
)
from gpgpu_stack.seed_flow import (
    GpuSmClusterSeedFlowResult,
    GpuSmSeedFlowResult,
    run_gpu_sm_cluster_seed_flow,
    run_gpu_sm_seed_flow,
    write_gpu_sm_seed_artifacts,
)
from gpgpu_stack.workloads import build_gpu_sm_cluster_workload_trace

__all__ = [
    "CommandDescriptor",
    "DeviceContractBundle",
    "GPU_SM_NAMED_PROFILES",
    "GpuSmProfileHint",
    "GpuSmClusterSeedFlowResult",
    "GpuSmSeedFlowResult",
    "AddressMap",
    "AddressRegion",
    "KernelLaunch",
    "KernelMetadata",
    "PerfCounterSample",
    "PerfCounterSchema",
    "PerfCounterSpec",
    "RuntimeQueueStub",
    "TraceArchitectureEvaluation",
    "WorkloadTrace",
    "WorkloadTraceEvent",
    "build_gpu_sm_cluster_address_map",
    "build_gpu_sm_cluster_device_contract",
    "build_gpu_sm_cluster_perf_counter_schema",
    "build_gpu_sm_cluster_workload_trace",
    "build_gpu_sm_seed_address_map",
    "build_gpu_sm_seed_device_contract",
    "build_gpu_sm_seed_perf_counter_schema",
    "build_gpu_sm_seed_workload_trace",
    "build_launch_command",
    "command_to_gpu_sm_cluster_trace",
    "command_to_gpu_sm_seed_trace",
    "emit_workload_trace_architecture_report_markdown",
    "evaluate_gpu_sm_cluster_command",
    "evaluate_gpu_sm_command",
    "evaluate_workload_trace",
    "get_gpu_sm_named_profile",
    "gpu_sm_baseline_profile",
    "gpu_sm_compute_pressure_profile",
    "gpu_sm_memory_pressure_profile",
    "gpu_sm_sfu_pressure_profile",
    "project_trace_evaluation_to_perf_counters",
    "run_gpu_sm_cluster_seed_flow",
    "run_gpu_sm_seed_flow",
    "write_gpu_sm_seed_artifacts",
    "workload_trace_to_archsim_workload",
]
