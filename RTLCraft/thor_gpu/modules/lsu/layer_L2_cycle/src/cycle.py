"""L2 CycleIR model for the ThorLSU."""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext


def lsu_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model: issue request when valid_in; capture response when mem_valid."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["pending"] = 0
            ctx.state["rdata"] = 0
            ctx.set_output("mem_req", 0)
            ctx.set_output("done", 0)
            ctx.set_output("rdata", 0)
            return

        valid_in = ctx.get_input("valid_in", 0)
        op = ctx.get_input("op", 0)
        addr = ctx.get_input("addr", 0)
        wdata = ctx.get_input("wdata", 0)
        mem_valid = ctx.get_input("mem_valid", 0)
        mem_rdata = ctx.get_input("mem_rdata", 0)
        mem_ready = ctx.get_input("mem_ready", 1)

        # Issue request this cycle when a new op is presented.
        mem_req = valid_in & mem_ready
        ctx.set_output("mem_req", mem_req)
        ctx.set_output("mem_wen", op)
        ctx.set_output("mem_addr", addr)
        ctx.set_output("mem_wdata", wdata)

        if mem_valid:
            ctx.state["rdata"] = mem_rdata
            ctx.set_output("done", 1)
        else:
            ctx.set_output("done", 0)
        ctx.set_output("rdata", ctx.state.get("rdata", 0))

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorLSU",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-level vector LSU with request/response handshake.",
        "latency_cycles": 1,
        "pipeline_stages": ["request", "response"],
    }


__all__ = ["lsu_cycle_model", "describe"]
