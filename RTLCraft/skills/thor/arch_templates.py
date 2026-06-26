"""
skills/thor/arch_templates — Thor GPGPU Architecture Definition.

Builds ArchDefinition with full GPU hierarchy:
  GPU Top → CTA Scheduler → SM × N_SM → Warp Scheduler × N_SCHED → Pipeline
"""
from __future__ import annotations
from rtlgen.arch_def import (
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, Algorithm_Model,
)
from rtlgen.registry import TemplateRegistry

from skills.thor import (
    XLEN, NLANE, VLEN, VREGS, NWARP, N_SCHED, WARP_PER_SCHED,
    NSM, IMEM_DEPTH, N_ALU, N_FPU, N_SFU, N_TENSOR, N_LSU,
)
import skills.thor.cycle_level


def build_thor_arch() -> ArchDefinition:
    """Build Thor GPGPU architecture with full hierarchy."""
    arch = ArchDefinition(
        name="Thor_B200_GPU",
        description="Blackwell-class GPGPU: CTA Scheduler + %d SMs × %d warps × %d lanes" % (
            NSM, NWARP, NLANE),
        isa="simt",
        ppa_targets={"max_area": 10000000, "target_freq": 2e9},
    )

    # ---- Warp Scheduler (×N_SCHED per SM) ----
    sched_pes = []
    for s in range(N_SCHED):
        sched_pes.append(ProcessingElement(
            name=f"warp_sched_{s}", pe_type="warp_scheduler",
            behavior=TemplateRegistry.get("warp_scheduler")(n_warps=WARP_PER_SCHED),
            inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                    PortDesc("warp_ready_mask","input",WARP_PER_SCHED),
                    PortDesc("warp_stall_mask","input",WARP_PER_SCHED)],
            outputs=[PortDesc("selected_warp","output",2),
                     PortDesc("select_valid","output",1)],
            latency=1,
        ))

    # ---- IBuffer (per scheduler, 8-entry) ----
    ibuf_pes = []
    for s in range(N_SCHED):
        ibuf_pes.append(ProcessingElement(
            name=f"ibuf_{s}", pe_type="ibuffer",
            behavior=TemplateRegistry.get("ibuffer")(depth=8),
            inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                    PortDesc("push_valid","input",1), PortDesc("push_data","input",32),
                    PortDesc("pop_ready","input",1)],
            outputs=[PortDesc("instr","output",32), PortDesc("valid","output",1),
                     PortDesc("stall","output",1), PortDesc("count","output",4)],
            latency=1, can_stall=True,
        ))

    # ---- Scoreboard ----
    score_pe = ProcessingElement(
        name="scoreboard", pe_type="scoreboard",
        behavior=TemplateRegistry.get("scoreboard")(n_regs=VREGS),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("alloc_reg","input",8), PortDesc("alloc_valid","input",1),
                PortDesc("commit_reg","input",8), PortDesc("commit_valid","input",1)],
        outputs=[PortDesc("busy_mask","output",128),
                 PortDesc("ready_bits","output",128)],
        latency=1,
    )

    # ---- Vector ALU ----
    alu_pe = ProcessingElement(
        name="vector_alu", pe_type="vector_alu",
        behavior=TemplateRegistry.get("vector_alu")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("opcode","input",5),
                PortDesc("op1","input",VLEN), PortDesc("op2","input",VLEN),
                PortDesc("pred_mask","input",NLANE)],
        outputs=[PortDesc("result","output",VLEN), PortDesc("valid","output",1)],
        latency=2,
    )

    # ---- LSU ----
    lsu_pe = ProcessingElement(
        name="lsu", pe_type="lsu",
        behavior=TemplateRegistry.get("lsu")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("opcode","input",5),
                PortDesc("base_addr","input",32), PortDesc("offset","input",16),
                PortDesc("vector_data","input",VLEN),
                PortDesc("mem_data_valid","input",1), PortDesc("mem_rdata","input",VLEN)],
        outputs=[PortDesc("mem_req","output",1), PortDesc("mem_wen","output",1),
                 PortDesc("mem_addr","output",32), PortDesc("mem_wdata","output",VLEN),
                 PortDesc("rd_data","output",VLEN), PortDesc("rd_valid","output",1)],
        latency=2, can_stall=True,
    )

    # ---- L1 Cache ----
    l1_pe = ProcessingElement(
        name="l1_cache", pe_type="l1_cache",
        behavior=TemplateRegistry.get("l1_cache")(),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("addr","input",32), PortDesc("req_valid","input",1),
                PortDesc("wen","input",1), PortDesc("wdata","input",VLEN),
                PortDesc("fill_valid","input",1), PortDesc("fill_data","input",VLEN),
                PortDesc("fill_line","input",10)],
        outputs=[PortDesc("hit","output",1), PortDesc("rdata","output",VLEN),
                 PortDesc("miss","output",1), PortDesc("miss_addr","output",32)],
        latency=1, can_stall=True,
    )

    # ---- SM Wrapper (combines all per-SM units) ----
    sm_pes = []
    for i in range(NSM):
        sm_pes.append(ProcessingElement(
            name=f"sm_{i}", pe_type="sm_wrapper",
            behavior=TemplateRegistry.get("sm_wrapper")(),
            inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                    PortDesc("start","input",1), PortDesc("wb_accept","input",1),
                    PortDesc("mem_rdata","input",VLEN),
                    PortDesc("mem_ready","input",1), PortDesc("mem_valid","input",1)],
            outputs=[PortDesc("mem_req","output",1), PortDesc("mem_wen","output",1),
                     PortDesc("mem_addr","output",32), PortDesc("mem_wdata","output",VLEN),
                     PortDesc("sm_done","output",1)],
            latency=1, can_stall=False,
        ))

    # ---- CTA Scheduler ----
    cta_pe = ProcessingElement(
        name="cta_scheduler", pe_type="cta_scheduler",
        behavior=TemplateRegistry.get("cta_scheduler")(nsm=NSM),
        inputs=[PortDesc("clk","input",1), PortDesc("rst","input",1),
                PortDesc("kernel_start","input",1), PortDesc("num_ctas","input",16),
                PortDesc("sm_ready_mask","input",NSM)],
        outputs=[PortDesc("dispatched_sm","output",4),
                 PortDesc("dispatch_valid","output",1),
                 PortDesc("remaining_ctas","output",16)],
        latency=1,
    )

    all_pes = sched_pes + ibuf_pes + [score_pe, alu_pe, lsu_pe, l1_pe] + sm_pes + [cta_pe]
    arch.processing_elements = all_pes
    return arch
