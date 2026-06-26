"""L2 CycleIR model for the ThorWarpScheduler."""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from thor_gpu.modules.warp_scheduler.layer_L1_behavior.src.behavior import scheduler_step, NWARP


def scheduler_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model: warp_sel is a registered output advancing by the sticky rule."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["warp_sel"] = 0
            ctx.set_output("warp_sel", 0)
            ctx.set_output("barrier_release", 0)
            ctx.set_output("sm_done", 0)
            return

        warp_idle = ctx.get_input("warp_idle", 0)
        warp_done = ctx.get_input("warp_done", 0)
        warp_at_barrier = ctx.get_input("warp_at_barrier", 0)

        cur_sel = ctx.state.get("warp_sel", 0)
        res = scheduler_step(cur_sel, warp_idle, warp_done, warp_at_barrier)
        ctx.state["warp_sel"] = res["warp_sel"]

        ctx.set_output("warp_sel", res["warp_sel"])
        ctx.set_output("barrier_release", res["barrier_release"])
        ctx.set_output("sm_done", res["sm_done"])

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorWarpScheduler",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-level sticky-RR warp scheduler with registered warp_sel.",
        "latency_cycles": 1,
        "pipeline_stages": ["decision", "warp_sel_register"],
    }


__all__ = ["scheduler_cycle_model", "describe"]
