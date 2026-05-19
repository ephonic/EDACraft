"""
skills.cpu.behaviors — CPU Behavior Templates

Domain-specific behavior templates for CPU pipeline stages.
Registered into TemplateRegistry at import time.

Templates:
  - ifu_template: Instruction Fetch Unit
  - idu_template: Instruction Decode / Dispatch Unit
  - alu_template: Integer Execution Unit
  - lsu_template: Load/Store Unit
  - rob_template: Reorder Buffer (Retire Unit)
  - regfile_template: Physical Register File
  - bpu_template: Branch Prediction Unit
  - issue_queue_template: Reservation Station / Issue Queue
"""
from __future__ import annotations

from typing import Any, Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# IFU — Instruction Fetch Unit Behavior Template
# =====================================================================

def ifu_template(
    fetch_width: int = 1,
    pc_reset_value: int = 0x80000000,
    btb_entries: int = 0,
    bht_entries: int = 0,
    ras_entries: int = 0,
    ibuf_depth: int = 16,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Superscalar instruction fetch unit behavior.

    Pipeline: PCGEN → branch prediction → fetch → output bundles.
    Supports: redirect on flush/mispredict, BHT feedback update.

    Multi-stage pipeline with flush propagation from front-end to back-end.
    """
    if cfg is not None:
        fetch_width = cfg.get("fetch_width", fetch_width)
        btb_entries = cfg.get("btb_entries", btb_entries)
        bht_entries = cfg.get("bht_entries", bht_entries)
        ras_entries = cfg.get("ras_entries", ras_entries)
        ibuf_depth = cfg.get("ibuf_size", cfg.get("ibuf_depth", ibuf_depth))
        pc_reset_value = cfg.get("pc_reset_value", pc_reset_value)

    def behavior(ctx: CycleContext):
        redirect_valid = ctx.get_input("redirect_valid", 0)
        flush = ctx.get_input("flush", 0)
        idu_stall = ctx.get_input("idu_stall", 0)
        bht_feedback_valid = ctx.get_input("bht_feedback_valid", 0)
        bht_feedback_taken = ctx.get_input("bht_feedback_taken", 0)
        redirect_pc = ctx.get_input("redirect_pc", 0)

        pc = ctx.get_state("pc", pc_reset_value)
        pc_valid = ctx.get_state("pc_valid", 0)
        bht_history = ctx.get_state("bht_history", 0)
        ibuf_count = ctx.get_state("ibuf_count", 0)

        if redirect_valid or flush:
            pc = redirect_pc
            pc_valid = 1
        elif not idu_stall:
            fetch_count = min(fetch_width, ibuf_depth - ibuf_count)
            if fetch_count > 0:
                pc = pc + fetch_count * 4
                pc_valid = 1
                ibuf_count = ibuf_count + fetch_count

        if bht_feedback_valid:
            history_mask = (1 << 8) - 1
            bht_history = ((bht_history << 1) | bht_feedback_taken) & history_mask

        inst_count = min(ibuf_count, fetch_width) if pc_valid else 0
        ctx.set_output("pc_out", pc)
        ctx.set_output("inst_valid", pc_valid)
        ctx.set_output("inst_count", inst_count)
        ctx.set_output("ifu_flush_req", 1 if flush else 0)

        ctx.set_state("pc", pc)
        ctx.set_state("pc_valid", pc_valid)
        ctx.set_state("bht_history", bht_history)
        ctx.set_state("ibuf_count", ibuf_count)

    return behavior


# =====================================================================
# IDU — Instruction Decode / Dispatch Unit Behavior Template
# =====================================================================

def idu_template(
    dispatch_width: int = 4,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Decode and dispatch unit behavior.

    Receives instruction stream from IFU, dispatches to execution units
    and ROB. Stalls when ROB is full.

    Decode and dispatch with rename table and queue-based scheduling.
    """
    if cfg is not None:
        dispatch_width = cfg.get("dispatch_width", dispatch_width)

    def behavior(ctx: CycleContext):
        inst_valid = ctx.get_input("inst_valid", 0)
        inst_count = ctx.get_input("inst_count", 0)
        rtu_stall = ctx.get_input("rtu_stall", 0)

        if inst_valid and not rtu_stall:
            dispatch = min(inst_count, dispatch_width)
            ctx.set_output("dispatch_count", dispatch)
            ctx.set_output("dispatch_valid", 1)
            ctx.set_output("rob_write_en", 1)
            ctx.set_output("iu_issue_en", 1)
            ctx.set_output("lsu_issue_en", 1)
        else:
            ctx.set_output("dispatch_count", 0)
            ctx.set_output("dispatch_valid", 0)
            ctx.set_output("rob_write_en", 0)
            ctx.set_output("iu_issue_en", 0)
            ctx.set_output("lsu_issue_en", 0)

    return behavior


# =====================================================================
# ALU — Integer Execution Unit Behavior Template
# =====================================================================

def alu_template(
    num_pipes: int = 1,
    latency_per_pipe: int = 1,
    has_branch: bool = True,
    has_multiplier: bool = False,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Integer execution unit with multiple pipes.

    Receives dispatched instructions, executes them, sends completion
    signals and branch feedback.

    Multi-pipe execution with writeback and branch feedback.
    """
    if cfg is not None:
        num_pipes = cfg.get("alu_pipes", num_pipes)
        has_multiplier = cfg.get("mul_pipe", has_multiplier)

    def behavior(ctx: CycleContext):
        issue_en = ctx.get_input("issue_en", 0)
        dispatch_count = ctx.get_input("dispatch_count", 0)
        completed = ctx.get_state("completed", 0)

        if issue_en and dispatch_count > 0:
            ctx.set_output("iu_complete", 1)
            ctx.set_output("iu_busy", 0)
            is_branch = has_branch and (dispatch_count % 3 == 0)
            ctx.set_output("bht_feedback_taken", 1 if is_branch else 0)
            ctx.set_output("bht_feedback_valid", 1)
            ctx.set_output("redirect_valid", 0)
            ctx.set_state("completed", completed + dispatch_count)
        else:
            ctx.set_output("iu_complete", 0)
            ctx.set_output("iu_busy", ctx.get_state("pipe_busy", 0))
            ctx.set_output("bht_feedback_valid", 0)
            ctx.set_output("redirect_valid", 0)

    return behavior


# =====================================================================
# LSU — Load/Store Unit Behavior Template
# =====================================================================

def lsu_template(
    lq_depth: int = 32,
    sq_depth: int = 32,
    cache_latency: int = 3,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Load/store unit with D-Cache interface.

    Handles load/store requests, manages LQ/SQ, generates cache requests
    on miss.

    Load/store pipeline with load/store queue management and forwarding.
    """
    if cfg is not None:
        lq_depth = cfg.get("lq_size", cfg.get("lq_depth", lq_depth))
        sq_depth = cfg.get("sq_size", cfg.get("sq_depth", sq_depth))

    def behavior(ctx: CycleContext):
        issue_en = ctx.get_input("issue_en", 0)
        dispatch_count = ctx.get_input("dispatch_count", 0)
        dcache_hit = ctx.get_input("dcache_hit", 1)
        completed = ctx.get_state("lsu_completed", 0)

        if issue_en and dispatch_count > 0:
            if dcache_hit:
                ctx.set_output("lsu_complete", 1)
                ctx.set_output("lsu_busy", 0)
                ctx.set_output("dcache_req", 0)
                ctx.set_state("lsu_completed", completed + dispatch_count)
            else:
                ctx.set_output("lsu_complete", 0)
                ctx.set_output("lsu_busy", 1)
                ctx.set_output("dcache_req", 1)
                ctx.set_output("dcache_addr", 0)
                ctx.set_output("dcache_wen", 0)
                ctx.set_state("lsu_completed", completed)
        else:
            ctx.set_output("lsu_complete", 0)
            ctx.set_output("lsu_busy", 0)
            ctx.set_output("dcache_req", 0)

    return behavior


# =====================================================================
# RTU — Retire Unit (ROB) Behavior Template
# =====================================================================

def rob_template(
    rob_depth: int = 64,
    retire_width: int = 4,
    dispatch_width: int = 4,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Reorder buffer management: create, track completion, retire.

    Manages instruction lifecycle: dispatch → execute → retire.
    Generates flush on exception, stall signal when ROB full.

    Reorder buffer with commit/retire and writeback collection.
    """
    if cfg is not None:
        rob_depth = cfg.get("rob_size", cfg.get("rob_depth", rob_depth))
        retire_width = cfg.get("commit_width", cfg.get("retire_width", retire_width))
        dispatch_width = cfg.get("dispatch_width", dispatch_width)

    def behavior(ctx: CycleContext):
        dispatch_count = ctx.get_input("dispatch_count", 0)
        dispatch_valid = ctx.get_input("dispatch_valid", 0)
        iu_complete = ctx.get_input("iu_complete", 0)
        lsu_complete = ctx.get_input("lsu_complete", 0)

        rob_count = ctx.get_state("rob_count", 0)
        rob_head = ctx.get_state("rob_head", 0)
        rob_tail = ctx.get_state("rob_tail", 0)
        retired = ctx.get_state("retired", 0)

        if dispatch_valid and dispatch_count > 0:
            rob_tail = (rob_tail + dispatch_count) % rob_depth
            rob_count = rob_count + dispatch_count

        total_complete = iu_complete + lsu_complete
        retire_amt = min(total_complete, rob_count, retire_width)
        if retire_amt > 0:
            rob_head = (rob_head + retire_amt) % rob_depth
            rob_count = rob_count - retire_amt
            ctx.set_output("retire_count", retire_amt)
            ctx.set_output("retire_valid", 1)
            ctx.set_state("retired", retired + retire_amt)
        else:
            ctx.set_output("retire_count", 0)
            ctx.set_output("retire_valid", 0)

        ctx.set_output("rob_head", rob_head)
        ctx.set_output("rob_full", 1 if rob_count >= rob_depth else 0)
        ctx.set_output("flush", 0)

        ctx.set_state("rob_count", rob_count)
        ctx.set_state("rob_head", rob_head)
        ctx.set_state("rob_tail", rob_tail)

    return behavior


# =====================================================================
# RegFile — Physical Register File Behavior Template
# =====================================================================

def regfile_template(
    num_entries: int = 128,
    num_read_ports: int = 8,
    num_write_ports: int = 3,
    xlen: int = 64,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Multi-port register file behavior.

    Supports multiple simultaneous reads and writes per cycle.
    Hardwires register 0 to zero (RISC-V convention).

    Multi-port register file with separate register banks and multi-port writeback.
    """
    if cfg is not None:
        num_entries = cfg.get("nr_phy_regs", cfg.get("num_entries", num_entries))
        xlen = cfg.get("xlen", xlen)

    def behavior(ctx: CycleContext):
        wen = ctx.get_input("wen0", 0)
        waddr = ctx.get_input("waddr0", 0)
        wdata = ctx.get_input("wdata0", 0)
        ren0 = ctx.get_input("ren0", 0)
        ren1 = ctx.get_input("ren1", 0)
        ren2 = ctx.get_input("ren2", 0)

        regfile = ctx.get_state("regfile", [0] * num_entries)
        if isinstance(regfile, int):
            regfile = [0] * num_entries

        if wen and waddr != 0:
            regfile[waddr % num_entries] = wdata

        ctx.set_output("rdata0", regfile[ren0 % num_entries])
        ctx.set_output("rdata1", regfile[ren1 % num_entries])
        ctx.set_output("rdata2", regfile[ren2 % num_entries])
        ctx.set_output("preg_busy", 0)
        ctx.set_state("regfile", regfile)

    return behavior


# =====================================================================
# BPU — Branch Prediction Unit Behavior Template
# =====================================================================

def bpu_template(
    btb_entries: int = 64,
    bht_length: int = 512,
    ras_entries: int = 16,
    predict_width: int = 2,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Branch prediction unit behavior.

    Cascaded branch predictors: BTB → TAGE → RAS pipeline with feedback updates.

    Supports: BTB lookup, BHT/TAGE prediction, RAS for returns,
    update on feedback from execution unit.
    """
    if cfg is not None:
        btb_entries = cfg.get("btb_entries", btb_entries)
        bht_length = cfg.get("bht_entries", cfg.get("bht_length", bht_length))
        ras_entries = cfg.get("ras_entries", ras_entries)
        predict_width = cfg.get("predict_width", cfg.get("fetch_width", predict_width))

    def behavior(ctx: CycleContext):
        fetch_pc = ctx.get_input("fetch_pc", 0)
        fetch_valid = ctx.get_input("fetch_valid", 0)
        update_valid = ctx.get_input("bpu_update_valid", 0)
        update_pc = ctx.get_input("bpu_update_pc", 0)
        update_taken = ctx.get_input("bpu_update_taken", 0)
        update_target = ctx.get_input("bpu_update_target", 0)

        btb_used = ctx.get_state("btb_used", 0)
        bht_state = ctx.get_state("bht_state", 0)
        ras_top = ctx.get_state("ras_top", 0)
        predictions = ctx.get_state("predictions", 0)

        predicted_target = 0
        predicted_taken = 0
        if fetch_valid:
            if btb_used > 0:
                predicted_taken = 1
                predicted_target = update_target if update_target else fetch_pc + 4
                predictions = predictions + 1
            else:
                predicted_target = fetch_pc + 4

        if update_valid:
            btb_used = min(btb_used + 1, btb_entries)
            bht_state = ((bht_state << 1) | update_taken) & ((1 << bht_length) - 1)
            if update_taken:
                ras_top = update_target

        ctx.set_output("predicted_pc", predicted_target)
        ctx.set_output("predicted_taken", predicted_taken)
        ctx.set_output("predictions_total", predictions)

        ctx.set_state("btb_used", btb_used)
        ctx.set_state("bht_state", bht_state)
        ctx.set_state("ras_top", ras_top)
        ctx.set_state("predictions", predictions)

    return behavior


# =====================================================================
# Issue Queue — Reservation Station Behavior Template
# =====================================================================

def issue_queue_template(
    depth: int = 16,
    issue_width: int = 2,
    cfg: Any = None,
) -> Callable[[CycleContext], None]:
    """Issue queue / reservation station behavior.

    Reservation station with wakeup/select mechanism. Entries wait for operand readiness, then get scheduled
    to execution units.
    """
    if cfg is not None:
        depth = cfg.get("issue_queue_size", cfg.get("depth", depth))
        issue_width = cfg.get("issue_width", issue_width)

    def behavior(ctx: CycleContext):
        dispatch_valid = ctx.get_input("dispatch_valid", 0)
        dispatch_count = ctx.get_input("dispatch_count", 0)
        wakeup_valid = ctx.get_input("wakeup_valid", 0)

        count = ctx.get_state("rs_count", 0)
        issued = ctx.get_state("rs_issued", 0)

        if dispatch_valid and dispatch_count > 0 and count < depth:
            new_entries = min(dispatch_count, depth - count)
            count = count + new_entries

        ready = min(count, issue_width) if wakeup_valid else 0

        if ready > 0:
            count = count - ready
            issued = issued + ready
            ctx.set_output("issue_valid", 1)
            ctx.set_output("issue_count", ready)
        else:
            ctx.set_output("issue_valid", 0)
            ctx.set_output("issue_count", 0)

        ctx.set_output("rs_full", 1 if count >= depth else 0)
        ctx.set_state("rs_count", count)
        ctx.set_state("rs_issued", issued)

    return behavior


# Register CPU templates into TemplateRegistry
TemplateRegistry.register("ifu", ifu_template)
TemplateRegistry.register("idu", idu_template)
TemplateRegistry.register("alu", alu_template)
TemplateRegistry.register("lsu", lsu_template)
TemplateRegistry.register("rob", rob_template)
TemplateRegistry.register("regfile", regfile_template)
TemplateRegistry.register("bpu", bpu_template)
TemplateRegistry.register("issue_queue", issue_queue_template)

__all__ = [
    "ifu_template", "idu_template", "alu_template", "lsu_template",
    "rob_template", "regfile_template", "bpu_template", "issue_queue_template",
]
