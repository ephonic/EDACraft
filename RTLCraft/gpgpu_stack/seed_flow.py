"""End-to-end seed-flow helpers for the current GPGPU flagship slice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from gpu_sm.arch import build_gpu_sm_architecture_model, build_gpu_sm_cluster_architecture_model
from gpu_sm.dsl import GpuSm
from rtlgen_x.archsim import (
    ArchitectureModel,
    StageSweepReport,
    UpgradeCandidate,
    rank_bandwidth_upgrades,
    run_stage_bandwidth_sweep,
)
from rtlgen_x.ppa import PpaGoals, PpaReport, emit_ppa_report_markdown
from rtlgen_x.verify import (
    FoundationContractReport,
    analyze_foundation_contract,
    emit_foundation_contract_markdown,
    foundation_contract_report_to_json,
)

from gpgpu_stack.abi import AddressMap, CommandDescriptor, KernelMetadata, PerfCounterSchema
from gpgpu_stack.analysis import TraceArchitectureEvaluation
from gpgpu_stack.device import build_gpu_sm_cluster_device_contract, build_gpu_sm_seed_device_contract
from gpgpu_stack.perf import PerfCounterSample, project_trace_evaluation_to_perf_counters
from gpgpu_stack.profiles import gpu_sm_baseline_profile
from gpgpu_stack.runtime import (
    GpuSmProfileHint,
    RuntimeQueueStub,
    command_to_gpu_sm_cluster_trace,
    command_to_gpu_sm_seed_trace,
    evaluate_gpu_sm_cluster_command,
    evaluate_gpu_sm_command,
)


@dataclass(frozen=True)
class GpuSmSeedFlowResult:
    """Completed seed-flow artifact bundle for one GPU-SM launch study."""

    command: CommandDescriptor
    model: ArchitectureModel
    address_map: AddressMap
    perf_counters: PerfCounterSchema
    perf_counter_sample: PerfCounterSample
    trace_evaluation: TraceArchitectureEvaluation
    ppa_report: PpaReport
    foundation_report: FoundationContractReport
    architecture_markdown: str
    ppa_markdown: str
    foundation_markdown: str


@dataclass(frozen=True)
class GpuSmClusterSeedFlowResult:
    """Completed cluster-level architecture artifact bundle for the GPU-SM seed line."""

    command: CommandDescriptor
    model: ArchitectureModel
    address_map: AddressMap
    perf_counters: PerfCounterSchema
    perf_counter_sample: PerfCounterSample
    trace_evaluation: TraceArchitectureEvaluation
    architecture_markdown: str


def run_gpu_sm_seed_flow(
    *,
    kernel_metadata: Optional[KernelMetadata] = None,
    launch_id: str = "gpu_sm_seed_launch",
    queue_name: str = "compute",
    shared_mem_bandwidth_bytes_per_cycle: int = 8,
    profile: GpuSmProfileHint = gpu_sm_baseline_profile(),
    ppa_goals: Optional[PpaGoals] = None,
    architecture_title: str = "GPU SM Seed Architecture Report",
    ppa_title: str = "GPU SM Seed PPA Report",
) -> GpuSmSeedFlowResult:
    """Run the current minimal software+architecture+PPA seed flow."""

    device_contract = build_gpu_sm_seed_device_contract()
    metadata = kernel_metadata or KernelMetadata(kernel_name="gpu_sm_seed")
    queue = RuntimeQueueStub(queue_name=queue_name)
    command = queue.submit(
        metadata,
        launch_id=launch_id,
        metadata_overrides={"scenario": "seed_flow"},
    )
    model = build_gpu_sm_architecture_model(
        shared_mem_bandwidth_bytes_per_cycle=shared_mem_bandwidth_bytes_per_cycle
    )
    trace = command_to_gpu_sm_seed_trace(command, profile=profile)

    sweep_reports: Sequence[StageSweepReport] = ()
    upgrade_candidates: Sequence[UpgradeCandidate] = ()
    if profile.memory_tokens > 0:
        from gpgpu_stack.abi import workload_trace_to_archsim_workload

        bridged = workload_trace_to_archsim_workload(trace)
        sweep_reports = (
            run_stage_bandwidth_sweep(
                model,
                bridged,
                "shared_mem",
                bandwidths=(
                    shared_mem_bandwidth_bytes_per_cycle,
                    max(shared_mem_bandwidth_bytes_per_cycle * 2, 16),
                    max(shared_mem_bandwidth_bytes_per_cycle * 4, 32),
                ),
            ),
        )
        upgrade_candidates = rank_bandwidth_upgrades(
            model,
            bridged,
            candidate_bandwidths=(
                max(shared_mem_bandwidth_bytes_per_cycle * 2, 16),
                max(shared_mem_bandwidth_bytes_per_cycle * 4, 32),
            ),
        )

    trace_evaluation = evaluate_gpu_sm_command(
        command,
        model,
        profile=profile,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
        title=architecture_title,
    )
    ppa_report = _advise_gpu_sm_seed_ppa(
        model,
        trace_evaluation,
        goals=ppa_goals,
    )
    foundation_report = analyze_foundation_contract(GpuSm())
    perf_counter_sample = project_trace_evaluation_to_perf_counters(
        trace_evaluation,
        device_contract.perf_counters,
    )
    return GpuSmSeedFlowResult(
        command=command,
        model=model,
        address_map=device_contract.address_map,
        perf_counters=device_contract.perf_counters,
        perf_counter_sample=perf_counter_sample,
        trace_evaluation=trace_evaluation,
        ppa_report=ppa_report,
        foundation_report=foundation_report,
        architecture_markdown=trace_evaluation.markdown,
        ppa_markdown=emit_ppa_report_markdown(ppa_report, title=ppa_title),
        foundation_markdown=emit_foundation_contract_markdown(foundation_report),
    )


def run_gpu_sm_cluster_seed_flow(
    *,
    kernel_metadata: Optional[KernelMetadata] = None,
    launch_id: str = "gpu_sm_cluster_seed_launch",
    queue_name: str = "compute",
    sm_count: int = 2,
    cluster_mem_fabric_bandwidth_bytes_per_cycle: int = 16,
    cluster_commit_bandwidth_bytes_per_cycle: int = 16,
    shared_mem_bandwidth_bytes_per_cycle: int = 16,
    profile: GpuSmProfileHint = gpu_sm_baseline_profile(),
    architecture_title: str = "GPU SM Cluster Seed Architecture Report",
) -> GpuSmClusterSeedFlowResult:
    """Run the current cluster-level software+architecture seed flow."""

    device_contract = build_gpu_sm_cluster_device_contract(sm_count=sm_count)
    metadata = kernel_metadata or KernelMetadata(kernel_name="gpu_sm_seed")
    queue = RuntimeQueueStub(queue_name=queue_name)
    command = queue.submit(
        metadata,
        launch_id=launch_id,
        metadata_overrides={"scenario": "cluster_seed_flow", "sm_count": sm_count},
    )
    model = build_gpu_sm_cluster_architecture_model(
        sm_count=sm_count,
        cluster_mem_fabric_bandwidth_bytes_per_cycle=cluster_mem_fabric_bandwidth_bytes_per_cycle,
        cluster_commit_bandwidth_bytes_per_cycle=cluster_commit_bandwidth_bytes_per_cycle,
        shared_mem_bandwidth_bytes_per_cycle=shared_mem_bandwidth_bytes_per_cycle,
    )
    trace = command_to_gpu_sm_cluster_trace(command, sm_count=sm_count, profile=profile)

    sweep_reports: Sequence[StageSweepReport] = ()
    upgrade_candidates: Sequence[UpgradeCandidate] = ()
    if profile.memory_tokens > 0:
        from gpgpu_stack.abi import workload_trace_to_archsim_workload

        bridged = workload_trace_to_archsim_workload(trace)
        sweep_reports = (
            run_stage_bandwidth_sweep(
                model,
                bridged,
                "cluster_mem_fabric",
                bandwidths=(
                    cluster_mem_fabric_bandwidth_bytes_per_cycle,
                    max(cluster_mem_fabric_bandwidth_bytes_per_cycle * 2, 32),
                    max(cluster_mem_fabric_bandwidth_bytes_per_cycle * 4, 64),
                ),
            ),
        )
        upgrade_candidates = rank_bandwidth_upgrades(
            model,
            bridged,
            candidate_bandwidths=(
                max(cluster_mem_fabric_bandwidth_bytes_per_cycle * 2, 32),
                max(cluster_mem_fabric_bandwidth_bytes_per_cycle * 4, 64),
            ),
        )

    trace_evaluation = evaluate_gpu_sm_cluster_command(
        command,
        model,
        sm_count=sm_count,
        profile=profile,
        sweep_reports=sweep_reports,
        upgrade_candidates=upgrade_candidates,
        title=architecture_title,
    )
    perf_counter_sample = project_trace_evaluation_to_perf_counters(
        trace_evaluation,
        device_contract.perf_counters,
    )
    return GpuSmClusterSeedFlowResult(
        command=command,
        model=model,
        address_map=device_contract.address_map,
        perf_counters=device_contract.perf_counters,
        perf_counter_sample=perf_counter_sample,
        trace_evaluation=trace_evaluation,
        architecture_markdown=trace_evaluation.markdown,
    )


def write_gpu_sm_seed_artifacts(
    result: GpuSmSeedFlowResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Persist the markdown/json artifacts from one GPU-SM seed-flow result."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "architecture": target_dir / "architecture.md",
        "ppa": target_dir / "ppa.md",
        "foundation": target_dir / "foundation.md",
        "foundation_json": target_dir / "foundation.json",
    }
    paths["architecture"].write_text(result.architecture_markdown, encoding="utf-8")
    paths["ppa"].write_text(result.ppa_markdown, encoding="utf-8")
    paths["foundation"].write_text(result.foundation_markdown, encoding="utf-8")
    paths["foundation_json"].write_text(
        foundation_contract_report_to_json(result.foundation_report),
        encoding="utf-8",
    )
    return paths


def _advise_gpu_sm_seed_ppa(
    model: ArchitectureModel,
    trace_evaluation: TraceArchitectureEvaluation,
    *,
    goals: Optional[PpaGoals],
) -> PpaReport:
    from rtlgen_x.ppa import advise_ppa

    return advise_ppa(
        module=GpuSm(),
        model=model,
        workload=trace_evaluation.workload,
        goals=goals or PpaGoals(priority="balanced", max_logic_depth=12, max_state_bits=4096),
    )


__all__ = [
    "GpuSmClusterSeedFlowResult",
    "GpuSmSeedFlowResult",
    "run_gpu_sm_cluster_seed_flow",
    "run_gpu_sm_seed_flow",
    "write_gpu_sm_seed_artifacts",
]
