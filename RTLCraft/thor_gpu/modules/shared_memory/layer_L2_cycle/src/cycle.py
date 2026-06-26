"""L2 CycleIR model for the ThorSharedMemory."""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext


def shmem_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model: registered read; write has priority over read."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            mem = ctx.state.setdefault("mem", {})
            mem.clear()
            ctx.state["rdata_reg"] = 0
            ctx.set_output("rdata", 0)
            return

        we = ctx.get_input("we", 0)
        re = ctx.get_input("re", 0)
        addr = ctx.get_input("addr", 0) & 0xFFF
        wdata = ctx.get_input("wdata", 0)

        mem = ctx.state.setdefault("mem", {})
        if we:
            mem[addr] = wdata & ((1 << 256) - 1)
        # Registered read: latch the addressed word this cycle.
        ctx.state["rdata_reg"] = mem.get(addr, 0) if re else 0
        ctx.set_output("rdata", ctx.state.get("rdata_reg", 0))

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorSharedMemory",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Registered-read shared SRAM (write priority).",
        "latency_cycles": 1,
        "pipeline_stages": ["array_read", "read_register"],
    }


__all__ = ["shmem_cycle_model", "describe"]
