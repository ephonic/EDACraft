"""Behavior-level lightweight architecture simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from rtlgen_x.archsim.model import ArchitectureModel, Workload


@dataclass(frozen=True)
class BehaviorFlowMetrics:
    name: str
    pipeline_latency: int
    steady_state_ii: float
    throughput_tokens_per_cycle: float
    total_cycles: float
    bytes_moved: int
    bottleneck_stage: str


@dataclass(frozen=True)
class BehaviorStageMetrics:
    name: str
    kind: str
    tokens: int
    busy_cycles: float
    bytes_moved: int
    flows: List[str]


@dataclass(frozen=True)
class BehaviorReport:
    makespan_cycles: float
    total_tokens: int
    flow_metrics: Dict[str, BehaviorFlowMetrics]
    stage_metrics: Dict[str, BehaviorStageMetrics]


class BehaviorSimulator:
    """Fast architecture exploration without cycle-by-cycle execution."""

    def run(self, model: ArchitectureModel, workload: Workload) -> BehaviorReport:
        model.validate_workload(workload)
        flow_metrics: Dict[str, BehaviorFlowMetrics] = {}
        stage_acc: Dict[str, Dict[str, object]] = {}
        makespan = 0.0
        total_tokens = 0

        for flow in workload.flows:
            per_stage_ii = []
            pipeline_latency = 0
            bytes_moved = 0
            for stage_name in flow.path:
                stage = model.stage(stage_name)
                pipeline_latency += stage.latency
                per_stage_ii.append((stage_name, stage.initiation_interval / stage.capacity))
                stage_bytes = 0
                if flow.bytes_per_token and stage.kind in {"memory", "interconnect", "datapath"}:
                    stage_bytes = flow.bytes_per_token * flow.tokens
                    bytes_moved += stage_bytes
                acc = stage_acc.setdefault(stage_name, {
                    "kind": stage.kind,
                    "tokens": 0,
                    "busy_cycles": 0.0,
                    "bytes_moved": 0,
                    "flows": [],
                })
                acc["tokens"] = int(acc["tokens"]) + flow.tokens
                acc["busy_cycles"] = float(acc["busy_cycles"]) + (flow.tokens * stage.initiation_interval / stage.capacity)
                acc["bytes_moved"] = int(acc["bytes_moved"]) + stage_bytes
                if flow.name not in acc["flows"]:
                    acc["flows"].append(flow.name)

            bottleneck_stage, steady_state_ii = max(per_stage_ii, key=lambda item: item[1])
            throughput = 1.0 / steady_state_ii
            total_cycles = flow.start_cycle + pipeline_latency + max(0, flow.tokens - 1) * steady_state_ii
            flow_metrics[flow.name] = BehaviorFlowMetrics(
                name=flow.name,
                pipeline_latency=pipeline_latency,
                steady_state_ii=steady_state_ii,
                throughput_tokens_per_cycle=throughput,
                total_cycles=total_cycles,
                bytes_moved=bytes_moved,
                bottleneck_stage=bottleneck_stage,
            )
            makespan = max(makespan, total_cycles)
            total_tokens += flow.tokens

        stage_metrics = {
            name: BehaviorStageMetrics(
                name=name,
                kind=str(values["kind"]),
                tokens=int(values["tokens"]),
                busy_cycles=float(values["busy_cycles"]),
                bytes_moved=int(values["bytes_moved"]),
                flows=list(values["flows"]),
            )
            for name, values in stage_acc.items()
        }
        return BehaviorReport(
            makespan_cycles=makespan,
            total_tokens=total_tokens,
            flow_metrics=flow_metrics,
            stage_metrics=stage_metrics,
        )
