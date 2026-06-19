"""Cycle-level lightweight architecture simulation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from rtlgen_x.archsim.model import ArchitectureModel, FlowSpec, Workload


@dataclass
class _Token:
    flow_name: str
    token_index: int
    stage_index: int = 0


@dataclass
class _StageRuntime:
    ready: Deque[_Token] = field(default_factory=deque)
    active: List[Tuple[int, int, _Token]] = field(default_factory=list)
    completed: Deque[_Token] = field(default_factory=deque)
    lane_ready_times: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class CycleFlowMetrics:
    name: str
    issued_tokens: int
    completed_tokens: int
    first_issue_cycle: Optional[int]
    last_completion_cycle: Optional[int]
    total_cycles: int
    stalled_cycles: int


@dataclass(frozen=True)
class CycleStageMetrics:
    name: str
    started_tokens: int
    completed_tokens: int
    busy_token_cycles: int
    max_ready_depth: int


@dataclass(frozen=True)
class CycleReport:
    total_cycles: int
    flow_metrics: Dict[str, CycleFlowMetrics]
    stage_metrics: Dict[str, CycleStageMetrics]


class CycleSimulator:
    """Lightweight cycle-accurate architecture timing simulator."""

    def run(self, model: ArchitectureModel, workload: Workload, *, max_cycles: int = 100_000) -> CycleReport:
        model.validate_workload(workload)

        runtimes = {
            stage_name: _StageRuntime(
                lane_ready_times=[0] * stage.capacity,
            )
            for stage_name, stage in model.stages.items()
        }
        flow_by_name: Dict[str, FlowSpec] = {flow.name: flow for flow in workload.flows}
        pending = {flow.name: flow.tokens for flow in workload.flows}
        completions_needed = sum(flow.tokens for flow in workload.flows)
        completions_seen = 0
        rr_index = 0

        flow_stats = {
            flow.name: {
                "issued_tokens": 0,
                "completed_tokens": 0,
                "first_issue_cycle": None,
                "last_completion_cycle": None,
                "stalled_cycles": 0,
            }
            for flow in workload.flows
        }
        stage_stats = {
            stage_name: {
                "started_tokens": 0,
                "completed_tokens": 0,
                "busy_token_cycles": 0,
                "max_ready_depth": 0,
            }
            for stage_name in model.stages
        }

        cycle = 0
        ordered_flows = list(workload.flows)
        while completions_seen < completions_needed:
            if cycle > max_cycles:
                raise RuntimeError(f"cycle simulation exceeded max_cycles={max_cycles}")

            # Retire active work whose latency expires this cycle.
            for stage_name, runtime in runtimes.items():
                remaining: List[Tuple[int, int, _Token]] = []
                for finish_cycle, lane_idx, token in runtime.active:
                    if finish_cycle <= cycle:
                        runtime.completed.append(token)
                        stage_stats[stage_name]["completed_tokens"] += 1
                    else:
                        remaining.append((finish_cycle, lane_idx, token))
                runtime.active = remaining

            # Move tokens forward, from sink backward to source.
            for stage_name in reversed(list(model.stages)):
                runtime = runtimes[stage_name]
                while runtime.completed:
                    token = runtime.completed[0]
                    flow = flow_by_name[token.flow_name]
                    if token.stage_index == len(flow.path) - 1:
                        runtime.completed.popleft()
                        completions_seen += 1
                        stats = flow_stats[flow.name]
                        stats["completed_tokens"] += 1
                        stats["last_completion_cycle"] = cycle
                        continue

                    next_stage_name = flow.path[token.stage_index + 1]
                    next_runtime = runtimes[next_stage_name]
                    next_capacity = model.queue_capacity(next_stage_name)
                    if len(next_runtime.ready) >= next_capacity:
                        break
                    runtime.completed.popleft()
                    token.stage_index += 1
                    next_runtime.ready.append(token)
                    stage_stats[next_stage_name]["max_ready_depth"] = max(
                        stage_stats[next_stage_name]["max_ready_depth"],
                        len(next_runtime.ready),
                    )

            # Inject as many tokens as the source queues can accept this cycle.
            injection_progress = True
            while injection_progress:
                injection_progress = False
                for offset in range(len(ordered_flows)):
                    flow = ordered_flows[(rr_index + offset) % len(ordered_flows)]
                    if pending[flow.name] == 0 or flow.start_cycle > cycle:
                        continue
                    first_stage_name = flow.path[0]
                    first_runtime = runtimes[first_stage_name]
                    first_capacity = model.queue_capacity(first_stage_name)
                    if len(first_runtime.ready) >= first_capacity:
                        flow_stats[flow.name]["stalled_cycles"] += 1
                        continue
                    token_index = flow.tokens - pending[flow.name]
                    first_runtime.ready.append(_Token(flow_name=flow.name, token_index=token_index))
                    pending[flow.name] -= 1
                    flow_stats[flow.name]["issued_tokens"] += 1
                    if flow_stats[flow.name]["first_issue_cycle"] is None:
                        flow_stats[flow.name]["first_issue_cycle"] = cycle
                    stage_stats[first_stage_name]["max_ready_depth"] = max(
                        stage_stats[first_stage_name]["max_ready_depth"],
                        len(first_runtime.ready),
                    )
                    rr_index = (rr_index + offset + 1) % len(ordered_flows)
                    injection_progress = True

            # Launch ready tokens onto stage lanes.
            for stage_name, stage in model.stages.items():
                runtime = runtimes[stage_name]
                for lane_idx, lane_ready_cycle in enumerate(runtime.lane_ready_times):
                    if lane_ready_cycle > cycle or not runtime.ready:
                        continue
                    token = runtime.ready.popleft()
                    runtime.lane_ready_times[lane_idx] = cycle + stage.initiation_interval
                    runtime.active.append((cycle + stage.latency, lane_idx, token))
                    stage_stats[stage_name]["started_tokens"] += 1
                stage_stats[stage_name]["busy_token_cycles"] += len(runtime.active)

            cycle += 1

        flow_metrics = {}
        for flow_name, stats in flow_stats.items():
            last_completion = stats["last_completion_cycle"]
            total_cycles = (last_completion + 1) if last_completion is not None else 0
            flow_metrics[flow_name] = CycleFlowMetrics(
                name=flow_name,
                issued_tokens=int(stats["issued_tokens"]),
                completed_tokens=int(stats["completed_tokens"]),
                first_issue_cycle=stats["first_issue_cycle"],
                last_completion_cycle=last_completion,
                total_cycles=total_cycles,
                stalled_cycles=int(stats["stalled_cycles"]),
            )

        stage_metrics = {
            stage_name: CycleStageMetrics(
                name=stage_name,
                started_tokens=int(stats["started_tokens"]),
                completed_tokens=int(stats["completed_tokens"]),
                busy_token_cycles=int(stats["busy_token_cycles"]),
                max_ready_depth=int(stats["max_ready_depth"]),
            )
            for stage_name, stats in stage_stats.items()
        }
        return CycleReport(
            total_cycles=cycle,
            flow_metrics=flow_metrics,
            stage_metrics=stage_metrics,
        )
