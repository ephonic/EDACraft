"""L2 CycleIR model for the ThorSIMTStack."""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from thor_gpu.modules.simt_stack.layer_L1_behavior.src.behavior import simt_functional


def simt_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model: push/pop update the stack state each cycle."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["stack"] = []
            ctx.set_output("next_pc", 0)
            ctx.set_output("next_mask", 0)
            ctx.set_output("stack_depth", 0)
            return

        push = ctx.get_input("push", 0)
        pop = ctx.get_input("pop", 0)
        branch_pc = ctx.get_input("branch_pc", 0)
        reconverge_pc = ctx.get_input("reconverge_pc", 0)
        taken_mask = ctx.get_input("taken_mask", 0)
        active_mask = ctx.get_input("active_mask", 0xFF)

        stack = ctx.state.setdefault("stack", [])
        res = simt_functional(stack, push, pop, branch_pc, reconverge_pc,
                              taken_mask, active_mask)
        ctx.set_output("next_pc", res["next_pc"])
        ctx.set_output("next_mask", res["next_mask"])
        ctx.set_output("stack_depth", res["stack_depth"])

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorSIMTStack",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-level SIMT divergence/reconvergence stack.",
        "latency_cycles": 1,
        "pipeline_stages": ["stack_update", "output"],
    }


__all__ = ["simt_cycle_model", "describe"]
