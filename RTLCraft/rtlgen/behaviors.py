"""
rtlgen.behaviors — Base Template Registry + Generic Behavior Templates

rtlgen/ keeps only:
  1. TemplateRegistry — extensible registration for skills
  2. Generic templates (fifo, datapath, axi_handshake, pipeline_connect,
     circular_queue, writeback_arbiter)

Domain-specific templates live in skills/:
  - skills/cpu/behaviors.py: ifu, idu, alu, lsu, rob, regfile, bpu, issue_queue
  - skills/gpgpu/behaviors.py: cta_scheduler, warp_scheduler
  - skills/mem/behaviors.py: memory_controller, dfi_sequencer

Skills register their templates at import time:
    from rtlgen.behaviors import TemplateRegistry
    TemplateRegistry.register("my_type", my_template)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from rtlgen.arch_def import CycleContext


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

    Supported operations:
      - 'pass_through': output = input
      - 'add': output = a + b
      - 'mul': output = a * b
      - 'accumulate': output += input
      - 'counter': output = counter (increments each cycle)
      - 'fsm': simple 2-state FSM (idle → active → done)
    """
    init = init_values or {}

    def behavior(ctx: CycleContext):
        if operation == "pass_through":
            for key, val in ctx.inputs.items():
                ctx.set_output(key, val)

        elif operation == "add":
            a = ctx.get_input("a", 0)
            b = ctx.get_input("b", 0)
            ctx.set_output("result", a + b)

        elif operation == "mul":
            a = ctx.get_input("a", 0)
            b = ctx.get_input("b", 0)
            ctx.set_output("result", a * b)

        elif operation == "accumulate":
            acc = ctx.get_state("acc", init.get("acc", 0))
            inp = ctx.get_input("input", 0)
            acc = acc + inp
            ctx.set_output("output", acc)
            ctx.set_state("acc", acc)

        elif operation == "counter":
            cnt = ctx.get_state("cnt", init.get("cnt", 0))
            enable = ctx.get_input("enable", 1)
            if enable:
                cnt = cnt + 1
            ctx.set_output("count", cnt)
            ctx.set_state("cnt", cnt)

        elif operation == "fsm":
            state = ctx.get_state("state", init.get("state", 0))
            start = ctx.get_input("start", 0)
            if state == 0 and start:
                state = 1
                ctx.set_output("busy", 1)
                ctx.set_output("done", 0)
            elif state == 1:
                state = 0
                ctx.set_output("busy", 0)
                ctx.set_output("done", 1)
            else:
                ctx.set_output("busy", 0)
                ctx.set_output("done", 0)
            ctx.set_state("state", state)

    return behavior


def fifo_template(
    depth: int = 16,
    data_width: int = 32,
) -> Callable[[CycleContext], None]:
    """Generic FIFO queue behavior.

    Supports simultaneous read and write (when not full/empty).
    """
    def behavior(ctx: CycleContext):
        wr_en = ctx.get_input("wr_en", 0)
        rd_en = ctx.get_input("rd_en", 0)
        wr_data = ctx.get_input("wr_data", 0)

        head = ctx.get_state("head", 0)
        tail = ctx.get_state("tail", 0)
        count = ctx.get_state("count", 0)

        if wr_en and count < depth:
            ctx.set_state(f"mem_{tail}", wr_data)
            tail = (tail + 1) % depth
            count = count + 1

        rd_data = ctx.get_state(f"mem_{head}", 0)
        if rd_en and count > 0:
            head = (head + 1) % depth
            count = count - 1

        ctx.set_output("rd_data", rd_data)
        ctx.set_output("full", 1 if count >= depth else 0)
        ctx.set_output("empty", 1 if count <= 0 else 1)
        ctx.set_output("count", count)

        ctx.set_state("head", head)
        ctx.set_state("tail", tail)
        ctx.set_state("count", count)

    return behavior


def axi_handshake_template(
    direction: str = "master",
) -> Callable[[CycleContext], None]:
    """AXI-like ready/valid handshake behavior.

    For master: drives valid, waits for ready.
    For slave: drives ready, accepts valid.
    """
    def behavior(ctx: CycleContext):
        if direction == "master":
            valid = ctx.get_state("pending", 0)
            ready = ctx.get_input("ready", 0)

            if valid and ready:
                ctx.set_output("valid", 0)
                ctx.set_state("pending", 0)
                ctx.set_output("done", 1)
            elif not valid:
                new_valid = ctx.get_input("new_valid", 0)
                if new_valid:
                    ctx.set_output("valid", 1)
                    ctx.set_output("data", ctx.get_input("new_data", 0))
                    ctx.set_state("pending", 1)
                    ctx.set_output("done", 0)
                else:
                    ctx.set_output("done", 0)
            else:
                ctx.set_output("done", 0)
        else:
            ctx.set_output("ready", 1)
            valid = ctx.get_input("valid", 0)
            ctx.set_output("accepted", valid)

    return behavior


def pipeline_connect_template(
    num_stages: int = 2,
    has_backpressure: bool = True,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Generic pipeline stage connection behavior.

    Stage-to-stage data propagation with valid/ready handshake.
    """
    if cfg is not None:
        num_stages = cfg.get("num_stages", num_stages)
        has_backpressure = cfg.get("has_backpressure", has_backpressure)

    def behavior(ctx: CycleContext):
        input_valid = ctx.get_input("input_valid", 0)
        input_data = ctx.get_input("input_data", 0)
        output_ready = ctx.get_input("output_ready", 1)

        stage_valid = ctx.get_state("pipe_valid", 0)
        stage_data = ctx.get_state("pipe_data", 0)

        if has_backpressure:
            if output_ready and stage_valid:
                ctx.set_output("output_valid", 1)
                ctx.set_output("output_data", stage_data)
                stage_valid = input_valid
                stage_data = input_data
                ctx.set_output("input_ready", 1)
            elif not stage_valid:
                stage_valid = input_valid
                stage_data = input_data
                ctx.set_output("input_ready", 1)
                ctx.set_output("output_valid", 0)
                ctx.set_output("output_data", 0)
            else:
                ctx.set_output("input_ready", 0)
                ctx.set_output("output_valid", 0)
                ctx.set_output("output_data", 0)
        else:
            stage_valid = input_valid
            stage_data = input_data
            ctx.set_output("output_valid", stage_valid)
            ctx.set_output("output_data", stage_data)
            ctx.set_output("input_ready", 1)

        ctx.set_state("pipe_valid", stage_valid)
        ctx.set_state("pipe_data", stage_data)

    return behavior


def circular_queue_template(
    depth: int = 16,
    data_width: int = 32,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Circular queue with head/tail pointers.

    Modeled after standard CircularQueuePtr patterns, used for FTQ, LQ, SQ,
    ROB, and other circular buffers.
    """
    if cfg is not None:
        depth = cfg.get("depth", depth)

    def behavior(ctx: CycleContext):
        enq_valid = ctx.get_input("enq_valid", 0)
        enq_data = ctx.get_input("enq_data", 0)
        deq_ready = ctx.get_input("deq_ready", 0)

        head = ctx.get_state("head", 0)
        tail = ctx.get_state("tail", 0)
        count = ctx.get_state("count", 0)

        if enq_valid and count < depth:
            ctx.set_state(f"mem_{tail}", enq_data)
            tail = (tail + 1) % depth
            count = count + 1

        if deq_ready and count > 0:
            deq_data = ctx.get_state(f"mem_{head}", 0)
            head = (head + 1) % depth
            count = count - 1
            ctx.set_output("deq_valid", 1)
            ctx.set_output("deq_data", deq_data)
        else:
            ctx.set_output("deq_valid", 0)
            ctx.set_output("deq_data", 0)

        ctx.set_output("full", 1 if count >= depth else 0)
        ctx.set_output("empty", 1 if count <= 0 else 0)
        ctx.set_output("count", count)

        ctx.set_state("head", head)
        ctx.set_state("tail", tail)
        ctx.set_state("count", count)

    return behavior


def writeback_arbiter_template(
    num_sources: int = 4,
    priority_policy: str = "round_robin",
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Writeback arbiter for collecting results from multiple execution units.

    Arbitrates writeback from ALU, MUL, LSU, FPU units to the
    register file and ROB.
    """
    if cfg is not None:
        num_sources = cfg.get("num_sources", num_sources)
        priority_policy = cfg.get("priority_policy", priority_policy)

    def behavior(ctx: CycleContext):
        rr_ptr = ctx.get_state("rr_ptr", 0)

        selected = -1
        valid_mask = 0
        for i in range(num_sources):
            src_valid = ctx.get_input(f"src{i}_valid", 0)
            if src_valid:
                valid_mask |= (1 << i)

        if valid_mask > 0:
            if priority_policy == "round_robin":
                for offset in range(num_sources):
                    idx = (rr_ptr + offset) % num_sources
                    if valid_mask & (1 << idx):
                        selected = idx
                        rr_ptr = (idx + 1) % num_sources
                        break
            else:
                for i in range(num_sources):
                    if valid_mask & (1 << i):
                        selected = i
                        break

            if selected >= 0:
                ctx.set_output("out_valid", 1)
                ctx.set_output("out_data", ctx.get_input(f"src{selected}_data", 0))
                ctx.set_output("out_source", selected)
            else:
                ctx.set_output("out_valid", 0)
                ctx.set_output("out_data", 0)
                ctx.set_output("out_source", 0)
        else:
            ctx.set_output("out_valid", 0)
            ctx.set_output("out_data", 0)
            ctx.set_output("out_source", 0)

        ctx.set_state("rr_ptr", rr_ptr)

    return behavior


# =====================================================================
# TemplateRegistry — Extensible template registration for skills
# =====================================================================

class TemplateRegistry:
    """Central registry for behavior templates, extensible by skills.

    Built-in generic templates are auto-registered.
    Domain-specific skills register their templates at import time:

        # skills/cpu/behaviors.py
        from rtlgen.behaviors import TemplateRegistry
        TemplateRegistry.register("ifu", ifu_template)
    """
    _templates: Dict[str, Callable] = {}
    _registered: bool = False

    @classmethod
    def register(cls, name: str, fn: Callable):
        cls._templates[name] = fn

    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        return cls._templates.get(name)

    @classmethod
    def list(cls) -> List[str]:
        return list(cls._templates.keys())

    @classmethod
    def ensure_registered(cls):
        """Ensure built-in generic templates are registered (idempotent)."""
        if cls._registered:
            return
        cls._registered = True
        cls.register("fifo", fifo_template)
        cls.register("datapath", datapath_template)
        cls.register("axi_handshake", axi_handshake_template)
        cls.register("pipeline_connect", pipeline_connect_template)
        cls.register("circular_queue", circular_queue_template)
        cls.register("writeback_arbiter", writeback_arbiter_template)


# Auto-register built-in generic templates
TemplateRegistry.ensure_registered()


# =====================================================================
# Backward-compatible re-exports from skills
# =====================================================================
# These import from skills/ where the actual implementations live,
# making `from rtlgen import ifu_template` etc. still work.

from skills.cpu.behaviors import (
    ifu_template,
    idu_template,
    alu_template,
    lsu_template,
    rob_template,
    regfile_template,
    bpu_template,
    issue_queue_template,
)

# Memory controller templates — loaded lazily via __getattr__ to avoid circular
# import (skills/mem/ddr3/behaviors.py → rtlgen.arch_def → rtlgen/__init__ → rtlgen/behaviors).
# The templates are registered into TemplateRegistry at import time of skills/mem/ddr3/behaviors.py,
# so we can use TemplateRegistry.get() after the import cycle resolves.
_memory_mod = None


def __getattr__(name: str):
    """Lazy-load memory templates on first access."""
    global _memory_mod
    if name in ("memory_controller_template", "dfi_sequencer_template"):
        if _memory_mod is None:
            import importlib
            try:
                _memory_mod = importlib.import_module("skills.mem.ddr3.behaviors")
            except ModuleNotFoundError:
                pass
        if _memory_mod is not None:
            return getattr(_memory_mod, name, None)
        # Fallback: try TemplateRegistry
        from rtlgen.behaviors import TemplateRegistry
        key = name.replace("_template", "")
        return TemplateRegistry.get(key)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
