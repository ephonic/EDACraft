"""L2 CycleIR model for the ThorTensorCore.

Cycle-accurate model: the MMA is treated as a 1-cycle pipelined operation.
A start strobe latches the operands; done is asserted the cycle the result
becomes available.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from thor_gpu.modules.tensor_core.layer_L1_behavior.src.behavior import tc_mma_reference


def tc_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of the 8x8x8 INT8 MMA (1-cycle registered result)."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["busy"] = 0
            ctx.state["result"] = 0
            ctx.set_output("result", 0)
            ctx.set_output("done", 0)
            return

        start = ctx.get_input("start", 0)
        a = ctx.get_input("a", 0)
        b = ctx.get_input("b", 0)
        c = ctx.get_input("c", 0)
        acc_en = ctx.get_input("acc_en", 1)

        done = 0
        if start:
            res = tc_mma_reference(a, b, c, acc_en)["result"]
            ctx.state["result"] = res
            done = 1

        ctx.set_output("result", ctx.state.get("result", 0))
        ctx.set_output("done", done)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorTensorCore",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "1-cycle registered 8x8x8 INT8->INT32 MMA.",
        "latency_cycles": 1,
        "pipeline_stages": ["mac_array", "result_register"],
    }


__all__ = ["tc_cycle_model", "describe"]
