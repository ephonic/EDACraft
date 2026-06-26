"""L2 CycleIR model for the ThorVectorFPU."""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from thor_gpu.modules.vector_fpu.layer_L1_behavior.src.behavior import vfpu_functional


def vfpu_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of the 8-lane FP32 FPU (1-cycle registered result)."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["result"] = 0
            ctx.state["result_mask"] = 0
            ctx.set_output("result", 0)
            ctx.set_output("result_mask", 0)
            ctx.set_output("valid", 0)
            return

        valid_in = ctx.get_input("valid_in", 0)
        fn = ctx.get_input("fpu_fn", 0)
        src1 = ctx.get_input("src1", 0)
        src2 = ctx.get_input("src2", 0)
        src3 = ctx.get_input("src3", 0)
        active_mask = ctx.get_input("active_mask", 0xFF)

        if valid_in:
            res = vfpu_functional(fn, src1, src2, src3, active_mask)
            ctx.state["result"] = res["result"]
            ctx.state["result_mask"] = res["result_mask"]

        ctx.set_output("result", ctx.state.get("result", 0))
        ctx.set_output("result_mask", ctx.state.get("result_mask", 0))
        ctx.set_output("valid", valid_in)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorVectorFPU",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "1-cycle registered 8-lane IEEE-754 FP32 FPU.",
        "latency_cycles": 1,
        "pipeline_stages": ["fp_compute", "result_register"],
    }


__all__ = ["vfpu_cycle_model", "describe"]
