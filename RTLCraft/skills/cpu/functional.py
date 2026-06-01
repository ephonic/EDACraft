"""
rtlgen.c910_models — Behavioral + cycle-level models derived from C910 analysis.

Generated from ref_rtl/cpu/RISC-V reference/ analysis:
  IFU: 50 modules → pcgen, bht, btb, ras, ibuf, icache_if, ...
  IDU: 57 modules → rename, issue queues (aiq/biq/lsiq), ...
  IU:  14 modules → alu, bju, mult, div
  LSU: 70 modules → load/store queues, dcache, snoop
  RTU: 22 modules → rob, pst_preg, retire
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from rtlgen.arch_def import CycleContext


# =====================================================================
# IFU Models (50 sub-modules)
# =====================================================================

def ifu_pcgen_functional(**kwargs) -> Callable:
    """PC generation with L0 BTB fast path.
    
    From ct_ifu_pcgen (11 regs):
      - Sequential: PC+8, branch redirect, L0 BTB hit
      - L0 BTB: 4-entry, single-cycle
    """
    def func(pc: int = 0x1000, branch_redirect: bool = False,
             branch_target: int = 0, l0_btb_hit: bool = False,
             l0_btb_target: int = 0) -> Dict:
        if branch_redirect:
            return {"next_pc": branch_target, "stall": False}
        if l0_btb_hit:
            return {"next_pc": l0_btb_target, "stall": False}
        return {"next_pc": pc + 8, "stall": False}
    return func


def ifu_bht_functional(**kwargs) -> Callable:
    """Branch history table (gshare-like predictor).
    
    From ct_ifu_bht (40 regs):
      - 4096-entry PHT (2-bit saturating counters)
      - History register with XOR hash
    """
    def func(fetch_pc: int, history: int, pht: Dict[int, int]) -> Dict:
        idx = (fetch_pc >> 2) ^ history
        counter = pht.get(idx & 0xFFF, 2)  # default: weakly taken
        return {"pred_taken": counter >= 2, "pht_index": idx & 0xFFF}
    return func


def ifu_btb_functional(**kwargs) -> Callable:
    """Branch target buffer.
    
    From ct_ifu_btb (10 regs):
      - 1024-entry, 4-way set-associative
      - Tag + target + valid
    """
    def func(fetch_pc: int, btb_tags: Dict, btb_targets: Dict,
             btb_valid: Dict) -> Dict:
        idx = (fetch_pc >> 2) & 0x3FF
        tag = fetch_pc >> 12
        hit = btb_valid.get(idx, False) and btb_tags.get(idx) == tag
        return {"btb_hit": hit, "btb_target": btb_targets.get(idx, 0)}
    return func


def ifu_ras_functional(**kwargs) -> Callable:
    """Return address stack.
    
    From ct_ifu_ras (38 regs):
      - 8-entry stack
      - Push on JAL, pop on JALR
    """
    def func(ras_stack: List[int], ras_ptr: int,
             is_call: bool, is_return: bool, return_pc: int) -> Dict:
        stack = list(ras_stack)
        ptr = ras_ptr
        if is_call:
            stack[ptr] = return_pc
            ptr = (ptr + 1) % 8
        pred_target = stack[(ptr - 1) % 8] if is_return and ptr > 0 else 0
        return {"ras_target": pred_target, "ras_ptr": ptr, "ras_stack": stack}
    return func


# =====================================================================
# IU Models (14 sub-modules)
# =====================================================================

def iu_alu_functional(**kwargs) -> Callable:
    """Integer ALU.
    
    From ct_iu_alu (8 regs):
      - 2-stage pipelined ALU
      - ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU
    """
    def func(opcode: int, funct3: int, funct7: int,
             src0: int, src1: int) -> Dict:
        result = 0
        if opcode == 0x33:  # R-type
            if funct3 == 0 and funct7 == 0:
                result = src0 + src1
            elif funct3 == 0 and funct7 == 0x20:
                result = src0 - src1
            elif funct3 == 4:
                result = src0 ^ src1
            elif funct3 == 6:
                result = src0 | src1
            elif funct3 == 7:
                result = src0 & src1
        return {"result": result, "ready": True}
    return func


def iu_bju_functional(**kwargs) -> Callable:
    """Branch execution unit.
    
    From ct_iu_bju (40 regs):
      - Branch resolution: compare operands
      - PC target calculation
      - Branch prediction update
    """
    def func(opcode: int, funct3: int, src0: int, src1: int,
             pc: int, imm: int) -> Dict:
        taken = False
        target = pc + 4
        if opcode == 0x63:  # BRANCH
            if funct3 == 0: taken = src0 == src1       # BEQ
            elif funct3 == 1: taken = src0 != src1     # BNE
            elif funct3 == 4: taken = src0 < src1       # BLT (signed)
            elif funct3 == 5: taken = src0 >= src1      # BGE
            elif funct3 == 6: taken = (src0 & 0xFFFFFFFFFFFFFFFF) < (src1 & 0xFFFFFFFFFFFFFFFF)  # BLTU
            elif funct3 == 7: taken = src0 >= src1      # unsigned compare
            if taken:
                target = pc + imm
        elif opcode == 0x6F:  # JAL
            target = pc + imm
            taken = True
        return {"branch_taken": taken, "branch_target": target}
    return func


# =====================================================================
# RTU Models (22 sub-modules)
# =====================================================================

def rtu_rob_functional(**kwargs) -> Callable:
    """Reorder buffer.
    
    From ct_rtu_rob (24 regs):
      - 128-entry ROB
      - 4-wide allocate + 4-wide retire
    """
    def func(rob_head: int, rob_tail: int, allocate: int = 0,
             retire: int = 0, depth: int = 128) -> Dict:
        head = (rob_head + retire) % depth
        tail = (rob_tail + allocate) % depth
        full = ((tail + 1) % depth) == head
        empty = head == tail
        return {"rob_head": head, "rob_tail": tail,
                "full": full, "empty": empty,
                "entries": (tail - head) % depth}
    return func


def rtu_pst_preg_functional(**kwargs) -> Callable:
    """Physical register status.
    
    From ct_rtu_pst_preg (698 regs!):
      - Tracks 256 physical registers
      - Bitmasks for: free, busy, ready
    """
    def func(free_mask: int, busy_mask: int, ready_mask: int,
             alloc_reg: int = 0, free_reg: int = 0) -> Dict:
        return {"free_mask": free_mask, "busy_mask": busy_mask,
                "ready_mask": ready_mask}
    return func


# =====================================================================
# Cycle-level models
# =====================================================================

def ifu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IFU model (RISC-V IFU).
    
    3-stage fetch pipeline:
      IF1: PC generation (pcgen + L0 BTB)
      IF2: I-cache access (icache_if + line buffer)
      IF3: Instruction buffer (ibuf) → decode
    """
    XLEN = 64
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["pc"] = 0x1000
            ctx.state["if1_valid"] = 0; ctx.state["if2_valid"] = 0
            ctx.state["if3_valid"] = 0
            return

        pc = ctx.state.setdefault("pc", 0x1000)
        icache_rdata = ctx.get_input("icache_rdata", 0)
        icache_valid = ctx.get_input("icache_valid", 0)

        # IF1: PC generation
        ctx.set_output("icache_req", 1)
        ctx.set_output("icache_addr", pc)

        # IF2: I-cache read
        if icache_valid:
            ctx.state["if2_instr"] = icache_rdata

        # IF3: Instruction buffer
        ctx.state["if3_valid"] = ctx.state.get("if2_valid", 0)

        # PC increment (2-wide)
        ctx.state["pc"] = pc + 8
        ctx.state["if1_valid"] = 1
        ctx.state["if2_valid"] = ctx.state["if1_valid"]

        ctx.set_output("fetch_valid", ctx.state["if3_valid"])
        ctx.set_output("fetch_instr", ctx.state.get("if2_instr", 0))
    return behavior


def iu_alu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ALU (RISC-V ALU, 2-stage)."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            ctx.state["pipe"] = 0
            return
        opcode = ctx.get_input("opcode", 0)
        src0 = ctx.get_input("src0", 0); src1 = ctx.get_input("src1", 0)
        result = src0 + src1  # default ADD
        ctx.state["pipe"] = result
        ctx.set_output("result", ctx.state.get("pipe", 0))
    return behavior


# =====================================================================
# Model registry
# =====================================================================

FUNCTIONAL_MODELS = {
    "ifu_pcgen": ifu_pcgen_functional,
    "ifu_bht": ifu_bht_functional,
    "ifu_btb": ifu_btb_functional,
    "ifu_ras": ifu_ras_functional,
    "iu_alu": iu_alu_functional,
    "iu_bju": iu_bju_functional,
    "rtu_rob": rtu_rob_functional,
}

CYCLE_MODELS = {
    "ifu": ifu_cycle,
    "iu_alu": iu_alu_cycle,
}
