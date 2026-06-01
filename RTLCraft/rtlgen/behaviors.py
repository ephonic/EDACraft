"""
rtlgen.behaviors — Generic Behavior Templates

Keeps only:
  1. Generic templates (fifo, datapath, axi_handshake, pipeline_connect,
     circular_queue, writeback_arbiter)
  2. TemplateRegistry imported from rtlgen.registry

Domain-specific templates live in skills/ and register via TemplateRegistry.

Usage:
    from rtlgen.registry import TemplateRegistry
    TemplateRegistry.register("my_type", my_template)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry


# =====================================================================
# Generic Templates (always available in rtlgen)
# =====================================================================


def datapath_template(
    operation: str = "pass_through",
    pipeline_stages: int = 1,
    init_values: Optional[Dict[str, int]] = None,
) -> Callable[[CycleContext], None]:
    """Generic datapath for non-CPU components (protocol controllers,
    stream processors, algorithm blocks).

    Args:
        operation: "pass_through" | "increment" | "decrement" | "accumulate"
        pipeline_stages: number of pipeline register stages
        init_values: initial values for state registers

    Returns a CycleContext-based behavior function.
    """
    def behavior(ctx: CycleContext) -> None:
        if operation == "pass_through":
            for name, val in ctx.inputs.items():
                if name not in ("clk", "rst_n", "rst"):
                    ctx.set_output(name, val)
        elif operation == "increment":
            for name, val in ctx.inputs.items():
                if name not in ("clk", "rst_n", "rst"):
                    ctx.set_output(name, (val or 0) + 1)
        elif operation == "accumulate":
            acc = ctx.state.get("acc", 0)
            for name, val in ctx.inputs.items():
                if name not in ("clk", "rst_n", "rst") and val:
                    acc += val
            ctx.state["acc"] = acc
            for name in ctx.inputs:
                if name not in ("clk", "rst_n", "rst"):
                    ctx.set_output(name, acc)
    return behavior


def fifo_template(depth: int = 8, width: int = 32) -> Callable[[CycleContext], None]:
    """Generic FIFO queue behavior.

    Args:
        depth: maximum number of entries
        width: data width in bits

    Ports: data_in, valid_in, ready_out, data_out, valid_out, empty, full
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["queue"] = []
            ctx.set_output("ready_out", 1)
            ctx.set_output("valid_out", 0)
            ctx.set_output("data_out", 0)
            ctx.set_output("empty", 1)
            ctx.set_output("full", 0)
            return

        q = ctx.state.setdefault("queue", [])
        data_in = ctx.get_input("data_in", 0)
        valid_in = ctx.get_input("valid_in", 0)
        pop = ctx.get_input("pop", 0)

        if valid_in and len(q) < depth:
            q.append(data_in)
        if pop and q:
            q.pop(0)

        ctx.set_output("ready_out", 1 if len(q) < depth else 0)
        ctx.set_output("valid_out", 1 if q else 0)
        ctx.set_output("data_out", q[0] if q else 0)
        ctx.set_output("empty", 1 if not q else 0)
        ctx.set_output("full", 1 if len(q) >= depth else 0)
    return behavior


def axi_handshake_template(**kwargs) -> Callable[[CycleContext], None]:
    """Generic AXI-style valid/ready handshake.

    Fire condition: valid & ready → data transfers.
    Stalls when ready=0.
    """
    def behavior(ctx: CycleContext) -> None:
        valid = ctx.get_input("valid", 0)
        ready = ctx.get_input("ready", 0)
        fire = valid and ready
        ctx.set_output("fire", fire)
        ctx.set_output("stall", valid and not ready)
    return behavior


def pipeline_connect_template(**kwargs) -> Callable[[CycleContext], None]:
    """Generic pipeline stage connect with valid/ready handshake.

    Transfers data from input register to output register on fire.
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["pipe_reg"] = 0
            ctx.set_output("data_out", 0)
            ctx.set_output("valid_out", 0)
            return
        data_in = ctx.get_input("data_in", 0)
        valid_in = ctx.get_input("valid_in", 0)
        ready_out = ctx.get_input("ready_out", 1)
        fire = valid_in and ready_out
        if fire:
            ctx.state["pipe_reg"] = data_in
        ctx.set_output("data_out", ctx.state.get("pipe_reg", 0))
        ctx.set_output("valid_out", 1 if fire else 0)
    return behavior


def circular_queue_template(depth: int = 16) -> Callable[[CycleContext], None]:
    """Circular buffer / queue with head/tail pointers."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["head"] = 0
            ctx.state["tail"] = 0
            ctx.state["count"] = 0
            ctx.state["buffer"] = [0] * depth
            for o in ["full", "empty", "data_out", "valid_out"]:
                ctx.set_output(o, 0)
            ctx.set_output("ready_out", 1)
            return
        push = ctx.get_input("push", 0)
        pop = ctx.get_input("pop", 0)
        data_in = ctx.get_input("data_in", 0)
        head = ctx.state["head"]
        tail = ctx.state["tail"]
        count = ctx.state["count"]
        buf = ctx.state["buffer"]
        if push and count < depth:
            buf[head] = data_in
            head = (head + 1) % depth
            count += 1
        if pop and count > 0:
            tail = (tail + 1) % depth
            count -= 1
        ctx.state["head"] = head
        ctx.state["tail"] = tail
        ctx.state["count"] = count
        ctx.set_output("data_out", buf[tail] if count > 0 else 0)
        ctx.set_output("valid_out", 1 if count > 0 else 0)
        ctx.set_output("ready_out", 1 if count < depth else 0)
        ctx.set_output("full", 1 if count >= depth else 0)
        ctx.set_output("empty", 1 if count == 0 else 0)
    return behavior


def writeback_arbiter_template(**kwargs) -> Callable[[CycleContext], None]:
    """Writeback arbiter: arbitrates between multiple completion ports."""
    def behavior(ctx: CycleContext) -> None:
        n_ports = kwargs.get("num_ports", 4)
        for i in range(n_ports):
            valid = ctx.get_input(f"port{i}_valid", 0)
            if valid:
                data = ctx.get_input(f"port{i}_data", 0)
                ctx.set_output("wb_valid", 1)
                ctx.set_output("wb_data", data)
                ctx.set_output(f"port{i}_ready", 1)
                return
        ctx.set_output("wb_valid", 0)
        for i in range(n_ports):
            ctx.set_output(f"port{i}_ready", 0)
    return behavior


# =====================================================================
# TemplateRegistry registration for built-in generic templates
# =====================================================================

TemplateRegistry.register("fifo", fifo_template)
TemplateRegistry.register("datapath", datapath_template)
TemplateRegistry.register("axi_handshake", axi_handshake_template)
TemplateRegistry.register("pipeline_connect", pipeline_connect_template)
TemplateRegistry.register("circular_queue", circular_queue_template)
TemplateRegistry.register("writeback_arbiter", writeback_arbiter_template)
