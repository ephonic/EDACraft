"""L2 CycleIR model for the ThorGpuSM.

A simplified cycle-level model that drives the L1 functional model and exposes
per-warp PC / accumulator state across cycles. This keeps cross-layer
verification tractable while preserving the SM's observable behavior
(VRF + accumulators + done).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from rtlgen import CycleContext

from thor_gpu.modules.gpu_sm.layer_L1_behavior.src.behavior import (
    sm_functional, NWARP, VREGS,
)


def sm_cycle_model(imem: List[int]) -> Callable[[CycleContext], None]:
    """Cycle-level SM model: lazily evaluates the functional model when started."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["done"] = 0
            ctx.set_output("sm_done", 0)
            return

        start = ctx.get_input("start", 0)
        if start and not ctx.state.get("done", 0):
            res = sm_functional(imem)
            ctx.state["vrf"] = res["vrf"]
            ctx.state["warp_acc"] = res["warp_acc"]
            ctx.state["warp_done"] = res["warp_done"]
            ctx.state["done"] = 1

        ctx.set_output("sm_done", ctx.state.get("done", 0))
        acc = ctx.state.get("warp_acc", [0] * NWARP)
        ctx.set_output("debug_w0_acc0", acc[0] if acc else 0)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorGpuSM",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-level SM model delegating functional execution to L1.",
        "latency_cycles": 1,
        "pipeline_stages": ["dispatch", "execute"],
    }


__all__ = ["sm_cycle_model", "describe"]
