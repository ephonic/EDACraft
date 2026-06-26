"""L2 CycleIR model for the ThorCluster."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from rtlgen import CycleContext

from thor_gpu.modules.gpu_cluster.layer_L1_behavior.src.behavior import cluster_functional


def cluster_cycle_model(imems: List[List[int]]) -> Callable[[CycleContext], None]:
    """Cycle-level cluster model: lazily evaluates the functional model on start."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["done"] = 0
            ctx.set_output("all_done", 0)
            return

        start = ctx.get_input("start", 0)
        if start and not ctx.state.get("done", 0):
            res = cluster_functional(imems)
            ctx.state["warp_acc"] = res["warp_acc"]
            ctx.state["done"] = 1 if res["all_done"] else 0

        ctx.set_output("all_done", ctx.state.get("done", 0))
        acc = ctx.state.get("warp_acc", [[0] * 4, [0] * 4])
        ctx.set_output("sm0_w0_acc0", acc[0][0] if acc and acc[0] else 0)
        ctx.set_output("sm1_w0_acc0", acc[1][0] if len(acc) > 1 and acc[1] else 0)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorCluster",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-level 2-SM cluster model delegating to the L1 functional model.",
        "latency_cycles": 1,
        "pipeline_stages": ["dispatch", "execute"],
    }


__all__ = ["cluster_cycle_model", "describe"]
