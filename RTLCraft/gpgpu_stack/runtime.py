"""Minimal runtime-side stubs for the GPGPU software stack.

The goal here is not to emulate a full runtime/driver environment. It is to
provide a thin, explicit software-side path from:

1. kernel launch intent
2. command descriptor creation
3. workload-trace construction
4. architecture evaluation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from rtlgen_x.archsim import (
    ArchitectureModel,
    StageSweepReport,
    UpgradeCandidate,
)

from gpgpu_stack.abi import CommandDescriptor, KernelLaunch, KernelMetadata, WorkloadTrace
from gpgpu_stack.analysis import TraceArchitectureEvaluation, evaluate_workload_trace
from gpgpu_stack.workloads import build_gpu_sm_cluster_workload_trace, build_gpu_sm_seed_workload_trace


@dataclass(frozen=True)
class GpuSmProfileHint:
    """Software-visible pressure hint for the current GPU SM seed."""

    compute_tokens: int = 32
    memory_tokens: int = 16
    sfu_tokens: int = 8
    gemm_tokens: int = 8
    memory_bytes_per_token: int = 64
    sfu_bytes_per_token: int = 16


def _normalize_metadata(metadata: Optional[Mapping[str, object]]) -> dict[str, object]:
    return dict(metadata or {})


def build_launch_command(
    metadata: KernelMetadata,
    *,
    launch_id: str,
    args: Optional[Mapping[str, int]] = None,
    queue: str = "compute",
    priority: int = 0,
    opcode: str = "launch_kernel",
    metadata_overrides: Optional[Mapping[str, object]] = None,
    descriptor_metadata: Optional[Mapping[str, object]] = None,
) -> CommandDescriptor:
    """Build the minimal command descriptor for one launch."""

    return CommandDescriptor(
        opcode=opcode,
        queue=queue,
        priority=priority,
        launch=KernelLaunch(
            metadata=metadata,
            launch_id=launch_id,
            args=dict(args or {}),
            metadata_overrides=_normalize_metadata(metadata_overrides),
        ),
        metadata=_normalize_metadata(descriptor_metadata),
    )


def command_to_gpu_sm_seed_trace(
    command: CommandDescriptor,
    *,
    profile: GpuSmProfileHint = GpuSmProfileHint(),
) -> WorkloadTrace:
    """Convert a launch command into the canonical GPU-SM seed workload trace."""

    launch = command.launch
    merged_kernel_metadata = _normalize_metadata(launch.metadata.metadata)
    merged_kernel_metadata.update(_normalize_metadata(launch.metadata_overrides))
    merged_kernel_metadata.update(
        {
            "launch_id": launch.launch_id,
            "queue": command.queue,
            "priority": command.priority,
            "opcode": command.opcode,
            "args": dict(launch.args),
        }
    )

    return build_gpu_sm_seed_workload_trace(
        kernel_name=launch.metadata.kernel_name,
        trace_id=f"{launch.launch_id}_trace",
        compute_tokens=profile.compute_tokens,
        memory_tokens=profile.memory_tokens,
        sfu_tokens=profile.sfu_tokens,
        gemm_tokens=profile.gemm_tokens,
        memory_bytes_per_token=profile.memory_bytes_per_token,
        sfu_bytes_per_token=profile.sfu_bytes_per_token,
        grid_dim=launch.metadata.grid_dim,
        block_dim=launch.metadata.block_dim,
        shared_mem_bytes=launch.metadata.shared_mem_bytes,
        register_count=launch.metadata.register_count,
        metadata=merged_kernel_metadata,
    )


@dataclass
class RuntimeQueueStub:
    """Tiny queue/runtime shim that accumulates submitted commands."""

    queue_name: str = "compute"
    _commands: list[CommandDescriptor] = field(default_factory=list)

    def submit(
        self,
        metadata: KernelMetadata,
        *,
        launch_id: Optional[str] = None,
        args: Optional[Mapping[str, int]] = None,
        priority: int = 0,
        opcode: str = "launch_kernel",
        metadata_overrides: Optional[Mapping[str, object]] = None,
        descriptor_metadata: Optional[Mapping[str, object]] = None,
    ) -> CommandDescriptor:
        """Submit one launch into the stub queue."""

        effective_launch_id = launch_id or f"{metadata.kernel_name}_launch_{len(self._commands)}"
        command = build_launch_command(
            metadata,
            launch_id=effective_launch_id,
            args=args,
            queue=self.queue_name,
            priority=priority,
            opcode=opcode,
            metadata_overrides=metadata_overrides,
            descriptor_metadata=descriptor_metadata,
        )
        self._commands.append(command)
        return command

    def commands(self) -> tuple[CommandDescriptor, ...]:
        return tuple(self._commands)


def evaluate_gpu_sm_command(
    command: CommandDescriptor,
    model: ArchitectureModel,
    *,
    profile: GpuSmProfileHint = GpuSmProfileHint(),
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
    title: Optional[str] = None,
) -> TraceArchitectureEvaluation:
    """Build a workload trace from one command and evaluate it on `archsim`."""

    trace = command_to_gpu_sm_seed_trace(command, profile=profile)
    return evaluate_workload_trace(
        trace,
        model,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
        title=title or f"{command.launch.launch_id} Architecture Report",
    )


def command_to_gpu_sm_cluster_trace(
    command: CommandDescriptor,
    *,
    sm_count: int = 2,
    profile: GpuSmProfileHint = GpuSmProfileHint(),
    start_cycle_stride: int = 1,
) -> WorkloadTrace:
    """Convert one launch command into the canonical GPU-SM cluster workload trace."""

    if sm_count < 1:
        raise ValueError("sm_count must be >= 1")
    launch = command.launch
    merged_kernel_metadata = _normalize_metadata(launch.metadata.metadata)
    merged_kernel_metadata.update(_normalize_metadata(launch.metadata_overrides))
    merged_kernel_metadata.update(
        {
            "launch_id": launch.launch_id,
            "queue": command.queue,
            "priority": command.priority,
            "opcode": command.opcode,
            "args": dict(launch.args),
            "sm_count": sm_count,
        }
    )

    return build_gpu_sm_cluster_workload_trace(
        kernel_name=f"{launch.metadata.kernel_name}_cluster",
        trace_id=f"{launch.launch_id}_cluster_trace",
        sm_count=sm_count,
        compute_tokens_per_sm=profile.compute_tokens,
        memory_tokens_per_sm=profile.memory_tokens,
        sfu_tokens_per_sm=profile.sfu_tokens,
        gemm_tokens_per_sm=profile.gemm_tokens,
        memory_bytes_per_token=profile.memory_bytes_per_token,
        sfu_bytes_per_token=profile.sfu_bytes_per_token,
        grid_dim=launch.metadata.grid_dim,
        block_dim=launch.metadata.block_dim,
        shared_mem_bytes_per_sm=launch.metadata.shared_mem_bytes,
        register_count=launch.metadata.register_count,
        start_cycle_stride=start_cycle_stride,
        metadata=merged_kernel_metadata,
    )


def evaluate_gpu_sm_cluster_command(
    command: CommandDescriptor,
    model: ArchitectureModel,
    *,
    sm_count: int = 2,
    profile: GpuSmProfileHint = GpuSmProfileHint(),
    start_cycle_stride: int = 1,
    sweep_reports: Sequence[StageSweepReport] = (),
    upgrade_candidates: Sequence[UpgradeCandidate] = (),
    title: Optional[str] = None,
) -> TraceArchitectureEvaluation:
    """Build a cluster workload trace from one command and evaluate it on `archsim`."""

    trace = command_to_gpu_sm_cluster_trace(
        command,
        sm_count=sm_count,
        profile=profile,
        start_cycle_stride=start_cycle_stride,
    )
    return evaluate_workload_trace(
        trace,
        model,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
        title=title or f"{command.launch.launch_id} Cluster Architecture Report",
    )


__all__ = [
    "GpuSmProfileHint",
    "RuntimeQueueStub",
    "build_launch_command",
    "command_to_gpu_sm_cluster_trace",
    "command_to_gpu_sm_seed_trace",
    "evaluate_gpu_sm_cluster_command",
    "evaluate_gpu_sm_command",
]
