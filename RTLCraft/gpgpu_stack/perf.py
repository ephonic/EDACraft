"""Projection helpers from architecture studies into software-visible counters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from gpgpu_stack.analysis import TraceArchitectureEvaluation
from gpgpu_stack.abi import PerfCounterSchema


@dataclass(frozen=True)
class PerfCounterSample:
    """One sampled set of projected counter values."""

    schema: PerfCounterSchema
    values: Mapping[str, int]
    metadata: Mapping[str, object]


def _flow_metric(summary, name: str):
    for flow in summary.flow_summaries:
        if flow.name == name:
            return flow
    return None


def _stage_metric(summary, name: str):
    for stage in summary.stage_summaries:
        if stage.name == name:
            return stage
    return None


def project_trace_evaluation_to_perf_counters(
    evaluation: TraceArchitectureEvaluation,
    schema: PerfCounterSchema,
) -> PerfCounterSample:
    """Project current `archsim` evidence onto the software-visible counter schema."""

    summary = evaluation.summary
    values = {}
    for counter in schema.counters:
        if counter.name == "issued_warps":
            values[counter.name] = sum(flow.tokens for flow in summary.flow_summaries)
        elif counter.name == "writeback_commits":
            writeback = _stage_metric(summary, "writeback")
            values[counter.name] = int(writeback.cycle_completed_tokens if writeback is not None else 0)
        elif counter.name == "shared_mem_stall_cycles":
            memory_flow = _flow_metric(summary, "warp_memory")
            values[counter.name] = int(memory_flow.stall_ratio * memory_flow.cycle_total_cycles) if memory_flow else 0
        elif counter.name == "sfu_busy_cycles":
            sfu = _stage_metric(summary, "sfu_pipe")
            values[counter.name] = int(sfu.busy_token_cycles) if sfu is not None else 0
        elif counter.name == "gemm_busy_cycles":
            gemm = _stage_metric(summary, "gemm_pipe")
            values[counter.name] = int(gemm.busy_token_cycles) if gemm is not None else 0
        elif counter.name == "cluster_commit_commits":
            commit = _stage_metric(summary, "cluster_commit")
            values[counter.name] = int(commit.cycle_completed_tokens if commit is not None else 0)
        elif counter.name == "cluster_mem_stall_cycles":
            total = 0
            for flow in summary.flow_summaries:
                if flow.name.endswith("_warp_memory"):
                    total += int(flow.stall_ratio * flow.cycle_total_cycles)
            values[counter.name] = total
        elif counter.name == "cluster_frontend_busy_cycles":
            frontend = _stage_metric(summary, "cluster_frontend")
            values[counter.name] = int(frontend.busy_token_cycles) if frontend is not None else 0
        elif counter.name == "cluster_commit_busy_cycles":
            commit = _stage_metric(summary, "cluster_commit")
            values[counter.name] = int(commit.busy_token_cycles) if commit is not None else 0
        elif counter.name.startswith("sm") and counter.name.endswith("_issued_warps"):
            prefix = counter.name[: counter.name.index("_issued_warps")]
            total = 0
            for flow in summary.flow_summaries:
                if flow.name.startswith(prefix + "_"):
                    total += flow.tokens
            values[counter.name] = total
        elif counter.name.startswith("sm") and counter.name.endswith("_writeback_commits"):
            prefix = counter.name[: counter.name.index("_writeback_commits")]
            writeback = _stage_metric(summary, f"{prefix}_writeback")
            values[counter.name] = int(writeback.cycle_completed_tokens if writeback is not None else 0)
        elif counter.name.startswith("sm") and counter.name.endswith("_shared_mem_stall_cycles"):
            prefix = counter.name[: counter.name.index("_shared_mem_stall_cycles")]
            memory_flow = _flow_metric(summary, f"{prefix}_warp_memory")
            values[counter.name] = int(memory_flow.stall_ratio * memory_flow.cycle_total_cycles) if memory_flow else 0
        elif counter.name.startswith("sm") and counter.name.endswith("_sfu_busy_cycles"):
            prefix = counter.name[: counter.name.index("_sfu_busy_cycles")]
            sfu = _stage_metric(summary, f"{prefix}_sfu_pipe")
            values[counter.name] = int(sfu.busy_token_cycles) if sfu is not None else 0
        elif counter.name.startswith("sm") and counter.name.endswith("_gemm_busy_cycles"):
            prefix = counter.name[: counter.name.index("_gemm_busy_cycles")]
            gemm = _stage_metric(summary, f"{prefix}_gemm_pipe")
            values[counter.name] = int(gemm.busy_token_cycles) if gemm is not None else 0
        else:
            values[counter.name] = 0

    return PerfCounterSample(
        schema=schema,
        values=values,
        metadata={
            "trace_id": evaluation.trace.trace_id,
            "kernel_name": evaluation.trace.kernel.kernel_name,
        },
    )


__all__ = [
    "PerfCounterSample",
    "project_trace_evaluation_to_perf_counters",
]
