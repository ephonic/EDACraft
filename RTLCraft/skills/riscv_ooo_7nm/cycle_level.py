"""Layer 2 — Cycle-accurate models with timing.

Uses CycleContext for pipeline stage modeling.
These models are structurally close to the final RTL but remain
in pure Python for fast simulation and verification.
"""

from __future__ import annotations

from typing import Callable, Dict

from rtlgen.arch_def import CycleContext


def fetch_stage_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """3-stage fetch pipeline: PCGen → I-Cache → Instruction Buffer.

    Stage 1: PC generation (with branch redirect)
    Stage 2: I-cache access
    Stage 3: Instruction alignment and buffer write
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("pc", 0x1000)
            ctx.set_state("stall", 0)
            ctx.set_state("branch_redirect", 0)
            ctx.set_output("fetch_valid", 0)
            ctx.set_output("fetch_pc", 0)
            ctx.set_output("ibuf_write", 0)
            ctx.set_output("ibuf_data", 0)
            return

        redirect = ctx.get_input("branch_redirect", 0)
        redirect_pc = ctx.get_input("branch_target", 0)
        stall = ctx.get_state("stall", 0)
        icache_ready = ctx.get_input("icache_ready", 1)

        pc = ctx.get_state("pc", 0x1000)

        if redirect:
            pc = redirect_pc
            ctx.set_state("branch_redirect", 1)
        elif not stall and icache_ready:
            pc = pc + 16  # 8-wide = 4 instructions
            ctx.set_state("branch_redirect", 0)

        ctx.set_state("pc", pc)
        ctx.set_output("fetch_valid", 1 if not stall else 0)
        ctx.set_output("fetch_pc", pc)
        ctx.set_output("fetch_instr", 0x0)  # placeholder, icache fills this

        # Instruction buffer write (stage 3)
        ctx.set_output("ibuf_write", 1 if not stall else 0)
        ctx.set_output("ibuf_data", 0x00000000)
    return behavior


def decode_stage_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """2-stage decode: instruction decode → register rename.

    Stage 1: Decode (opcode, funct3, funct7, register addresses)
    Stage 2: Rename (architectural regs → physical regs)
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("decode_valid", 0)
            ctx.set_output("rename_valid", 0)
            ctx.set_output("dispatch_valid", 0)
            return

        valid = ctx.get_input("fetch_valid", 0)
        instr = ctx.get_input("instr", 0x13)
        stall = ctx.get_input("pipeline_stall", 0)

        decoded_valid = 0
        if valid and not stall:
            decoded_valid = 1

        ctx.set_state("decode_valid", decoded_valid)
        ctx.set_output("rename_valid", decoded_valid)

        if decoded_valid:
            opcode = instr & 0x7f
            rd = (instr >> 7) & 0x1f
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1f
            rs2 = (instr >> 20) & 0x1f

            ctx.set_state("opcode", opcode)
            ctx.set_output("rd", rd)
            ctx.set_output("rs1", rs1)
            ctx.set_output("rs2", rs2)
            ctx.set_output("funct3", funct3)
            ctx.set_output("opcode_out", opcode)

            # Determine instruction type for issue queue dispatch
            is_alu = 1 if opcode in (0x13, 0x33, 0x1b, 0x3b) else 0
            is_branch = 1 if opcode == 0x63 else 0
            is_load = 1 if opcode == 0x03 else 0
            is_store = 1 if opcode == 0x23 else 0
            is_mul = 1 if opcode == 0x33 and (instr >> 25) & 0x7f >= 1 else 0
            is_fpu = 1 if opcode in (0x53, 0xd3) else 0

            ctx.set_output("is_alu", is_alu)
            ctx.set_output("is_branch", is_branch)
            ctx.set_output("is_load", is_load)
            ctx.set_output("is_store", is_store)
            ctx.set_output("is_mul", is_mul)
            ctx.set_output("is_fpu", is_fpu)
        else:
            ctx.set_output("rd", 0)
            ctx.set_output("rs1", 0)
            ctx.set_output("rs2", 0)
            ctx.set_output("rename_valid", 0)
    return behavior


def issue_queue_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Issue queue: wakeup + select logic.

    Tracks ready state of up to 16 entries.
    Wakes up entries when their source physical registers are written.
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("q_ready", 0)
            ctx.set_state("q_valid", 0)
            ctx.set_output("issue_valid", 0)
            ctx.set_output("issue_pdst", 0)
            return

        enqueue = ctx.get_input("enqueue", 0)
        wakeup_pdst = ctx.get_input("wakeup_pdst", 0)
        wakeup_valid = ctx.get_input("wakeup_valid", 0)
        q_valid = ctx.get_state("q_valid", 0)
        q_ready = ctx.get_state("q_ready", 0)
        issue_valid = 0

        if enqueue:
            ctx.set_state("q_valid", q_valid | (1 << ctx.get_input("q_idx", 0)))
            ctx.set_state("q_pdst", ctx.get_input("pdst", 0))

        if wakeup_valid:
            # Wake up all entries waiting on this PDST
            ctx.set_state("q_ready", q_ready | wakeup_pdst)
            ctx.set_state("q_ready_count", 0)

        # Select: pick oldest ready entry
        if q_valid and q_ready:
            issue_valid = 1
            ctx.set_state("q_valid", q_valid & ~1)

        ctx.set_output("issue_valid", issue_valid)
        ctx.set_output("issue_pdst", ctx.get_state("q_pdst", 0))
    return behavior


def alu_exec_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """ALU execution: single-cycle arithmetic/logic operations.

    Handles ADD, SUB, XOR, OR, AND, SLL, SRL, SRA, SLT, SLTU.
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("busy", 0)
            ctx.set_output("result_valid", 0)
            ctx.set_output("result", 0)
            return

        issue_valid = ctx.get_input("issue_valid", 0)
        opcode = ctx.get_input("opcode", 0)
        funct3 = ctx.get_input("funct3", 0)
        funct7 = ctx.get_input("funct7", 0)
        src0 = ctx.get_input("src0", 0)
        src1 = ctx.get_input("src1", 0)
        busy = ctx.get_state("busy", 0)
        result = 0
        result_valid = 0

        if issue_valid and not busy:
            if opcode in (0x13, 0x33, 0x1b, 0x3b):
                if funct3 == 0:
                    if opcode in (0x33, 0x3b) and (funct7 >> 6):
                        result = src0 - src1
                    else:
                        result = src0 + src1
                elif funct3 == 1: result = src0 << (src1 & 0x3f)
                elif funct3 == 2: result = 1 if (src0 >> 63) < (src1 >> 63) else 0
                elif funct3 == 3: result = 1 if (src0 & 0xffffffffffffffff) < (src1 & 0xffffffffffffffff) else 0
                elif funct3 == 4: result = src0 ^ src1
                elif funct3 == 5:
                    if funct7 >> 6: result = src0 >> (src1 & 0x3f)
                    else: result = src0 >> (src1 & 0x3f)
                elif funct3 == 6: result = src0 | src1
                elif funct3 == 7: result = src0 & src1
                result_valid = 1
                ctx.set_state("busy", 1)
        else:
            ctx.set_state("busy", 0) if not issue_valid else None

        ctx.set_output("result_valid", result_valid)
        ctx.set_output("result", result)
        ctx.set_state("busy", busy and not result_valid)
    return behavior


def lsu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Load/store unit: address generation → cache access.

    Handles LW, LH, LB, LHU, LBU, SW, SH, SB.
    2-stage pipeline: address gen → cache access.
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("st_addr", 0)
            ctx.set_output("ld_result_valid", 0)
            ctx.set_output("st_done", 0)
            return

        ld_req = ctx.get_input("ld_req", 0)
        st_req = ctx.get_input("st_req", 0)
        addr = ctx.get_input("addr", 0)
        st_data = ctx.get_input("st_data", 0)
        funct3 = ctx.get_input("funct3", 0)  # width encoding
        ld_result = 0
        ld_valid = 0
        st_done = 0

        if ld_req:
            addr_aligned = addr & ~0x3
            byte_offset = addr & 0x3
            mem_word = ctx.get_input("mem_rdata", 0)
            if funct3 == 0:  # LB
                byte_val = (mem_word >> (byte_offset * 8)) & 0xff
                ld_result = byte_val if not (byte_val & 0x80) else byte_val | -0x100
            elif funct3 == 1:  # LH
                half_val = (mem_word >> (byte_offset * 8)) & 0xffff
                ld_result = half_val if not (half_val & 0x8000) else half_val | -0x10000
            elif funct3 == 2:  # LW
                word_val = (mem_word >> (byte_offset * 8)) & 0xffffffff
                ld_result = word_val if not (word_val & 0x80000000) else word_val | -0x100000000
            elif funct3 == 3:  # LD
                ld_result = mem_word
            elif funct3 == 4:  # LBU
                ld_result = (mem_word >> (byte_offset * 8)) & 0xff
            elif funct3 == 5:  # LHU
                ld_result = (mem_word >> (byte_offset * 8)) & 0xffff
            elif funct3 == 6:  # LWU
                ld_result = (mem_word >> (byte_offset * 8)) & 0xffffffff
            ld_valid = 1

        if st_req:
            ctx.set_state("st_addr", addr)
            ctx.set_output("st_addr_out", addr)
            ctx.set_output("st_data_out", st_data)
            ctx.set_output("st_funct3", funct3)
            st_done = 1

        ctx.set_output("ld_result", ld_result)
        ctx.set_output("ld_result_valid", ld_valid)
        ctx.set_output("st_done", st_done)
    return behavior


def rob_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Reorder buffer: completion tracking and retirement.

    256-entry circular buffer. Tracks:
    - Instruction PC, rd, pdst
    - Completion status (exception, branch_mispredict)
    - Retirement to architectural state
    """
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if not rst_n:
            ctx.set_state("rob_head", 0)
            ctx.set_state("rob_tail", 0)
            ctx.set_state("rob_count", 0)
            ctx.set_output("commit_valid", 0)
            ctx.set_output("full", 0)
            ctx.set_output("empty", 1)
            ctx.set_state("rob_pc", [0] * 256)
            ctx.set_state("rob_rd", [0] * 256)
            ctx.set_state("rob_pdst", [0] * 256)
            ctx.set_state("rob_completed", [0] * 256)
            ctx.set_state("rob_exception", [0] * 256)
            return

        head = ctx.get_state("rob_head", 0)
        tail = ctx.get_state("rob_tail", 0)
        count = ctx.get_state("rob_count", 0)
        full = (count >= 256)
        empty = (count == 0)

        dispatch_valid = ctx.get_input("dispatch_valid", 0)
        dispatch_pc = ctx.get_input("dispatch_pc", 0)
        dispatch_rd = ctx.get_input("dispatch_rd", 0)
        dispatch_pdst = ctx.get_input("dispatch_pdst", 0)

        complete_valid = ctx.get_input("complete_valid", 0)
        complete_pdst = ctx.get_input("complete_pdst", 0)
        complete_exc = ctx.get_input("complete_exception", 0)

        commit_valid = 0
        commit_pc = 0
        commit_rd = 0
        commit_pdst = 0

        # Dispatch: allocate ROB entry
        if dispatch_valid and not full:
            rob_pc = ctx.get_state("rob_pc", [0] * 256)
            rob_rd = ctx.get_state("rob_rd", [0] * 256)
            rob_pdst = ctx.get_state("rob_pdst", [0] * 256)
            rob_completed = ctx.get_state("rob_completed", [0] * 256)
            rob_exception = ctx.get_state("rob_exception", [0] * 256)

            rob_pc[tail] = dispatch_pc
            rob_rd[tail] = dispatch_rd
            rob_pdst[tail] = dispatch_pdst
            rob_completed[tail] = 0
            rob_exception[tail] = 0

            ctx.set_state("rob_pc", rob_pc)
            ctx.set_state("rob_rd", rob_rd)
            ctx.set_state("rob_pdst", rob_pdst)
            ctx.set_state("rob_completed", rob_completed)
            ctx.set_state("rob_exception", rob_exception)
            tail = (tail + 1) & 0xff
            count += 1

        # Completion: mark ROB entry as done
        if complete_valid:
            rob_completed = ctx.get_state("rob_completed", [0] * 256)
            rob_exception = ctx.get_state("rob_exception", [0] * 256)
            for i in range(256):
                if rob_completed[i] == 0:
                    rob_completed[i] = 1
                    break
            ctx.set_state("rob_completed", rob_completed)
            ctx.set_state("rob_exception", rob_exception)

        # Commit: retire head if completed and no exception
        rob_completed = ctx.get_state("rob_completed", [0] * 256)
        rob_exception = ctx.get_state("rob_exception", [0] * 256)
        rob_pc = ctx.get_state("rob_pc", [0] * 256)
        rob_rd = ctx.get_state("rob_rd", [0] * 256)
        rob_pdst = ctx.get_state("rob_pdst", [0] * 256)

        if not empty and rob_completed[head]:
            commit_valid = 1
            commit_pc = rob_pc[head]
            commit_rd = rob_rd[head]
            commit_pdst = rob_pdst[head]
            rob_completed[head] = 0
            ctx.set_state("rob_completed", rob_completed)
            head = (head + 1) & 0xff
            count -= 1

        ctx.set_state("rob_head", head)
        ctx.set_state("rob_tail", tail)
        ctx.set_state("rob_count", count)
        ctx.set_output("commit_valid", commit_valid)
        ctx.set_output("commit_pc", commit_pc)
        ctx.set_output("commit_rd", commit_rd)
        ctx.set_output("commit_pdst", commit_pdst)
        ctx.set_output("full", full)
        ctx.set_output("empty", empty)
        ctx.set_output("rob_count_out", count)
    return behavior
