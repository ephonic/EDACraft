"""
skills.npu.behaviors — NPU Behavior Templates

Generic, parameterized behavior templates for neural processing unit
pipeline stages. Registered into TemplateRegistry at import time.

Template categories:
  - Schedulers: instruction fetch/decode + dispatch (generic FSM pattern)
  - Datapaths: compute units with configurable operations
  - Control: top-level dispatch to multiple pipeline stages

All templates follow the pattern: parameterize widths/depths/counts,
use abstract state machines, and support cfg object overrides.
"""
from __future__ import annotations

from typing import Any, Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry, fifo_template, datapath_template


# =====================================================================
# Scheduler Templates — Generic instruction decode + dispatch
# =====================================================================


def scheduler_template(
    miw: int = 32,
    uiw: int = 24,
    loop_depth: int = 8,
    unroll_factor: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Generic scheduler behavior for macro→micro instruction decode.

    Parameterized scheduler that handles:
      - Macro instruction write + ack
      - Micro instruction decode with loop unrolling
      - Ready/valid handshake for instruction stream

    This template is reusable across MVU, eVRF, MFU, and LD schedulers
    by varying the instruction width, loop depth, and unroll factor.
    """
    if cfg is not None:
        miw = cfg.get("macro_inst_width", cfg.get("miw", miw))
        uiw = cfg.get("micro_inst_width", cfg.get("uiw", uiw))
        loop_depth = cfg.get("loop_depth", loop_depth)
        unroll_factor = cfg.get("unroll_factor", unroll_factor)

    def behavior(ctx: CycleContext):
        minst_wr_en = ctx.get_input("minst_wr_en", 0)
        uinst_rd_en = ctx.get_input("uinst_rd_en", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=DECODE, 2=LOOP
        loop_cnt = ctx.get_state("loop_cnt", 0)
        uinst_ptr = ctx.get_state("uinst_ptr", 0)

        if state == 0 and minst_wr_en:
            ctx.set_state("state", 1)
            ctx.set_state("loop_cnt", 0)
            ctx.set_state("uinst_ptr", 0)
        elif state == 1:
            ctx.set_state("state", 2)  # Done decode → start loop
        elif state == 2 and uinst_rd_en:
            uinst_ptr = uinst_ptr + unroll_factor
            loop_cnt = loop_cnt + 1
            if loop_cnt >= loop_depth:
                ctx.set_state("state", 0)
            else:
                ctx.set_state("state", 1)
                ctx.set_state("loop_cnt", loop_cnt)
                ctx.set_state("uinst_ptr", uinst_ptr)

        ctx.set_output("minst_wr_rdy", 1 if state == 0 else 0)
        ctx.set_output("uinst_rd_rdy", 1)
        ctx.set_output("uinst_rd_dout", uinst_ptr)
        ctx.set_state("state", state)
        ctx.set_state("loop_cnt", loop_cnt)
        ctx.set_state("uinst_ptr", uinst_ptr)

    return behavior


# Convenience aliases for common scheduler instances
# These are factory wrappers that preset parameters for specific uses.

def mvu_scheduler_template(
    miw: int = 30,
    uiw: int = 25,
    loop_depth: int = 8,
    unroll_factor: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """MVU scheduler: macro→micro decode with loop unrolling for matrix tiles."""
    return scheduler_template(
        miw=miw, uiw=uiw, loop_depth=loop_depth,
        unroll_factor=unroll_factor, cfg=cfg,
    )


def evrf_scheduler_template(
    miw: int = 15,
    uiw: int = 14,
    loop_depth: int = 4,
    unroll_factor: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """eVRF scheduler: macro→micro decode for external VRF access."""
    return scheduler_template(
        miw=miw, uiw=uiw, loop_depth=loop_depth,
        unroll_factor=unroll_factor, cfg=cfg,
    )


def mfu_scheduler_template(
    miw: int = 25,
    uiw: int = 24,
    loop_depth: int = 4,
    unroll_factor: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """MFU scheduler: macro→micro decode for multi-function unit."""
    return scheduler_template(
        miw=miw, uiw=uiw, loop_depth=loop_depth,
        unroll_factor=unroll_factor, cfg=cfg,
    )


def ld_scheduler_template(
    miw: int = 35,
    uiw: int = 34,
    loop_depth: int = 4,
    unroll_factor: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """LD scheduler: macro→micro decode for load/store unit."""
    return scheduler_template(
        miw=miw, uiw=uiw, loop_depth=loop_depth,
        unroll_factor=unroll_factor, cfg=cfg,
    )


# =====================================================================
# Top Scheduler — Multi-unit dispatch controller
# =====================================================================


def top_scheduler_template(
    num_units: int = 5,
    inst_depth: int = 512,
    unit_names: tuple = ("unit0", "unit1", "unit2", "unit3", "unit4"),
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Top-level dispatch controller.

    Manages instruction chain memory and dispatches to multiple
    downstream unit schedulers via ready/valid handshakes.
    """
    if cfg is not None:
        num_units = cfg.get("num_units", num_units)
        inst_depth = cfg.get("inst_depth", inst_depth)
        if "unit_names" in cfg:
            unit_names = cfg["unit_names"]

    def behavior(ctx: CycleContext):
        i_start = ctx.get_input("i_start", 0)
        minst_chain_wr_en = ctx.get_input("minst_chain_wr_en", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=RUNNING, 2=DONE
        pc = ctx.get_state("pc", 0)

        # Instruction memory write
        if minst_chain_wr_en:
            wr_addr = ctx.get_input("minst_chain_wr_addr", 0)
            wr_din = ctx.get_input("minst_chain_wr_din", 0)
            ctx.set_state(f"inst_mem_{wr_addr}", wr_din)

        # FSM
        if state == 0 and i_start:
            pc_start = ctx.get_input("pc_start_offset", 0)
            ctx.set_state("pc", pc_start)
            ctx.set_state("state", 1)
        elif state == 1:
            # Check all unit FIFOs have room
            all_rdy = True
            for prefix in unit_names:
                rd_rdy = ctx.get_input(f"i_{prefix}_minst_rd_rdy", 0)
                if not rd_rdy:
                    all_rdy = False

            if all_rdy:
                pc = pc + 1
                ctx.set_state("pc", pc)

        # Ready outputs
        for prefix in unit_names:
            ctx.set_output(f"o_{prefix}_minst_rd_rdy", 1)
            ctx.set_output(f"o_{prefix}_minst_rd_dout", 0)

        ctx.set_output("o_done", 1 if state == 2 else 0)
        ctx.set_state("state", state)

    return behavior


# =====================================================================
# Datapath Templates — Generic compute unit behaviors
# =====================================================================


def mac_datapath_template(
    ew: int = 8,
    accw: int = 32,
    dotw: int = 40,
    ntile: int = 7,
    ndpe: int = 40,
    vrf_depth: int = 512,
    nvrf: int = 12,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Matrix-vector multiply datapath (MAC array).

    Parameterized NTILE × NDPE multiply-accumulate array with
    VRF register file. Supports configurable element width,
    accumulator width, and dot-product width.
    """
    if cfg is not None:
        ew = cfg.get("element_width", cfg.get("ew", ew))
        accw = cfg.get("acc_width", cfg.get("accw", accw))
        dotw = cfg.get("dot_width", cfg.get("dotw", dotw))
        ntile = cfg.get("num_tiles", cfg.get("ntile", ntile))
        ndpe = cfg.get("num_dpes", cfg.get("ndpe", ndpe))
        vrf_depth = cfg.get("vrf_depth", cfg.get("vrf_depth", vrf_depth))
        nvrf = cfg.get("num_vrfs", cfg.get("nvrf", nvrf))

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start", 0)
        vrf_wr_en = ctx.get_input("vrf_wr_en", 0)
        vrf_wr_addr = ctx.get_input("vrf_wr_addr", 0)
        vrf_wr_data = ctx.get_input("vrf_wr_data", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=COMPUTE, 2=DONE
        cycle_cnt = ctx.get_state("cycle_cnt", 0)
        tile_ptr = ctx.get_state("tile_ptr", 0)

        if start and state == 0:
            ctx.set_state("state", 1)
            ctx.set_state("cycle_cnt", 0)
            ctx.set_state("tile_ptr", 0)
        elif state == 1:
            cycle_cnt = cycle_cnt + 1
            if cycle_cnt >= ntile:
                ctx.set_state("state", 2)
                ctx.set_state("tile_ptr", tile_ptr + 1)
            else:
                ctx.set_state("cycle_cnt", cycle_cnt)

        # VRF write (external)
        if vrf_wr_en:
            ctx.set_state(f"vrf_{vrf_wr_addr}", vrf_wr_data)

        ctx.set_output("busy", 1 if state == 1 else 0)
        ctx.set_output("done", 1 if state == 2 else 0)
        ctx.set_output("tile_done", tile_ptr)
        ctx.set_state("state", state)
        ctx.set_state("cycle_cnt", cycle_cnt)
        ctx.set_state("tile_ptr", tile_ptr)

    return behavior


def func_datapath_template(
    num_funcs: int = 8,
    ew: int = 8,
    accw: int = 32,
    pipeline_stages: int = 1,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Multi-function unit datapath.

    Generic function unit supporting configurable operations
    (e.g., ReLU, Sigmoid, Tanh, Add, Sub, Mul, Max).
    Parameterized by number of functions, element width,
    accumulator width, and pipeline depth.
    """
    if cfg is not None:
        num_funcs = cfg.get("num_functions", cfg.get("num_funcs", num_funcs))
        ew = cfg.get("element_width", cfg.get("ew", ew))
        accw = cfg.get("acc_width", cfg.get("accw", accw))
        pipeline_stages = cfg.get("pipeline_stages", pipeline_stages)

    def behavior(ctx: CycleContext):
        data_wr_en = ctx.get_input("data_wr_en", 0)
        data_wr_din = ctx.get_input("data_wr_din", 0)
        func_op = ctx.get_input("func_op", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=COMPUTE, 2=DONE
        pipe_stage = ctx.get_state("pipe_stage", 0)

        if data_wr_en and state == 0:
            ctx.set_state("func_op_reg", func_op)
            ctx.set_state("data_reg", data_wr_din)
            ctx.set_state("state", 1)
            ctx.set_state("pipe_stage", 0)
        elif state == 1:
            pipe_stage = pipe_stage + 1
            if pipe_stage >= pipeline_stages:
                ctx.set_state("state", 2)
            else:
                ctx.set_state("pipe_stage", pipe_stage)

        ctx.set_output("busy", 1 if state == 1 else 0)
        ctx.set_output("done", 1 if state == 2 else 0)
        ctx.set_output("data_rd_dout", ctx.get_state("data_reg", 0))
        ctx.set_state("state", state)
        ctx.set_state("pipe_stage", pipe_stage)

    return behavior


def ext_vrf_datapath_template(
    accw: int = 32,
    ndpe: int = 40,
    num_banks: int = 4,
    bank_latency: int = 2,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """External VRF with banked pipeline.

    Banked register file with configurable bank count, access
    latency, and data width. Models element-wise VRF pipeline.
    """
    if cfg is not None:
        accw = cfg.get("acc_width", cfg.get("accw", accw))
        ndpe = cfg.get("num_dpes", cfg.get("ndpe", ndpe))
        num_banks = cfg.get("num_banks", num_banks)
        bank_latency = cfg.get("bank_latency", bank_latency)

    def behavior(ctx: CycleContext):
        data_wr_en = ctx.get_input("data_wr_en", 0)
        data_wr_din = ctx.get_input("data_wr_din", 0)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=ACCESS, 2=DONE
        access_cnt = ctx.get_state("access_cnt", 0)
        bank_sel = ctx.get_state("bank_sel", 0)

        if data_wr_en and state == 0:
            ctx.set_state("state", 1)
            ctx.set_state("access_cnt", 0)
            ctx.set_state("bank_sel", 0)
        elif state == 1:
            access_cnt = access_cnt + 1
            if access_cnt >= bank_latency:
                ctx.set_state("state", 2)
            else:
                ctx.set_state("access_cnt", access_cnt)

        ctx.set_output("busy", 1 if state == 1 else 0)
        ctx.set_output("done", 1 if state == 2 else 0)
        ctx.set_output("data_rd_dout", data_wr_din)
        ctx.set_state("state", state)
        ctx.set_state("access_cnt", access_cnt)
        ctx.set_state("bank_sel", bank_sel)

    return behavior


def ld_datapath_template(
    ew: int = 8,
    accw: int = 32,
    in_fifo_depth: int = 16,
    out_fifo_depth: int = 16,
    wb_fifo_depth: int = 16,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Load/store datapath with input/output/writeback FIFOs.

    Generic load/store unit with three FIFO stages:
      input FIFO → processing → writeback FIFO → output FIFO → VRF writeback
    """
    if cfg is not None:
        ew = cfg.get("element_width", cfg.get("ew", ew))
        accw = cfg.get("acc_width", cfg.get("accw", accw))
        in_fifo_depth = cfg.get("in_fifo_depth", in_fifo_depth)
        out_fifo_depth = cfg.get("out_fifo_depth", out_fifo_depth)
        wb_fifo_depth = cfg.get("wb_fifo_depth", wb_fifo_depth)

    def behavior(ctx: CycleContext):
        in_wr_en = ctx.get_input("in_wr_en", 0)
        out_rd_en = ctx.get_input("out_rd_en", 0)

        in_count = ctx.get_state("in_count", 0)
        out_count = ctx.get_state("out_count", 0)
        result_cnt = ctx.get_state("result_cnt", 0)

        if in_wr_en and in_count < in_fifo_depth:
            in_count = in_count + 1
        if out_rd_en and out_count > 0:
            out_count = out_count - 1

        # Flow from input to result
        if in_count > 0:
            in_count = in_count - 1
            result_cnt = result_cnt + 1

        ctx.set_output("in_wr_rdy", 1 if in_count < in_fifo_depth else 0)
        ctx.set_output("out_rd_rdy", 1 if out_count > 0 else 0)
        ctx.set_output("out_rd_dout", 0)
        ctx.set_output("result_count", result_cnt)
        ctx.set_output("vrf_wr_en", 0)
        ctx.set_output("vrf_wr_data", 0)

        ctx.set_state("in_count", in_count)
        ctx.set_state("out_count", out_count)
        ctx.set_state("result_cnt", result_cnt)

    return behavior


# =====================================================================
# Register NPU templates
# =====================================================================

TemplateRegistry.register("npu_scheduler", scheduler_template)
TemplateRegistry.register("npu_top_scheduler", top_scheduler_template)
TemplateRegistry.register("npu_mac_datapath", mac_datapath_template)
TemplateRegistry.register("npu_func_datapath", func_datapath_template)
TemplateRegistry.register("npu_ext_vrf", ext_vrf_datapath_template)
TemplateRegistry.register("npu_ld_datapath", ld_datapath_template)

# Convenience aliases (specific scheduler presets)
TemplateRegistry.register("mvu_scheduler", mvu_scheduler_template)
TemplateRegistry.register("evrf_scheduler", evrf_scheduler_template)
TemplateRegistry.register("mfu_scheduler", mfu_scheduler_template)
TemplateRegistry.register("ld_scheduler", ld_scheduler_template)
TemplateRegistry.register("mvu_datapath", mac_datapath_template)
TemplateRegistry.register("mfu_datapath", func_datapath_template)
TemplateRegistry.register("evrf_datapath", ext_vrf_datapath_template)
TemplateRegistry.register("ld_datapath", ld_datapath_template)

__all__ = [
    "scheduler_template",
    "top_scheduler_template",
    "mac_datapath_template",
    "func_datapath_template",
    "ext_vrf_datapath_template",
    "ld_datapath_template",
    "mvu_scheduler_template",
    "evrf_scheduler_template",
    "mfu_scheduler_template",
    "ld_scheduler_template",
    "mvu_datapath_template",
    "mfu_datapath_template",
    "evrf_datapath_template",
    "ld_datapath_template",
]
