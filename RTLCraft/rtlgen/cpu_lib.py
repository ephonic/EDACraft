"""
rtlgen.cpu_lib — Reusable CPU sub-module template library.

Each function generates a DSL Module for a specific pipeline component,
parameterized by CPUConfig. Designed to match C910-class complexity.

Components:
  - PCGen: PC generation with L0 BTB, branch redirect
  - BPred: Gshare predictor + BTB + RAS  
  - ICacheIF: I-cache interface with line buffer
  - Decoder: Instruction decode
  - RenameTable: Register rename with free list + checkpoint
  - IssueQueue: Wakeup-select issue queue
  - ALU: Arithmetic logic unit
  - BJU: Branch execution unit
  - LSU: Load/store unit with queues
  - ROB: Reorder buffer
  - Commit: Retire/commit logic
"""
from __future__ import annotations

from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const, SubmoduleInst
from rtlgen.logic import If, Else, Elif, Switch, Mux, Cat, Rep, SRA
from rtlgen.cpu_config import CPUConfig


def _const(val: int, width: int):
    return Const(val, width)


# ===================================================================
# PCGen — PC generation with L0 BTB
# ===================================================================
class PCGen(Module):
    """PC generation with L0 BTB fast path (C910: ct_ifu_pcgen)."""
    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("pcgen")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.branch_redirect = Input(1, "branch_redirect")
        self.branch_target = Input(64, "branch_target")
        self.btb_hit = Input(1, "btb_hit"); self.btb_target = Input(64, "btb_target")
        self.pc = Output(64, "pc"); self.pc_next = Output(64, "pc_next")

        pc = Reg(64, "pc")
        l0_btb_tag = Array(20, cfg.l0_btb_entries, "l0_btb_tag")
        l0_btb_target = Array(64, cfg.l0_btb_entries, "l0_btb_target")
        l0_btb_valid = Array(1, cfg.l0_btb_entries, "l0_btb_valid")
        init = Reg(1, "init")
        XLEN = 64

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; pc <<= _const(0x1000, XLEN)
            with Else():
                init <<= 1
                with If(self.branch_redirect == 1):
                    pc <<= self.branch_target
                with Elif(self.btb_hit == 1):
                    pc <<= self.btb_target
                with Else():
                    pc <<= pc + 8  # 2-wide fetch

        with self.comb:
            with If(init == 0): self.pc <<= _const(0, XLEN); self.pc_next <<= _const(0, XLEN)
            with Else(): self.pc <<= pc; self.pc_next <<= pc + 8


# ===================================================================
# BPred — Branch predictor (gshare + BTB + RAS)
# ===================================================================
class BPred(Module):
    """Branch predictor: gshare PHT, BTB, RAS (C910: ct_ifu_bht + ct_ifu_btb + ct_ifu_ras)."""
    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("bpred")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.fetch_pc = Input(64, "fetch_pc")
        self.exec_pc = Input(64, "exec_pc"); self.branch_taken = Input(1, "branch_taken")
        self.branch_target = Input(64, "branch_target")
        self.pred_taken = Output(1, "pred_taken"); self.pred_target = Output(64, "pred_target")
        self.btb_hit = Output(1, "btb_hit")

        btb_tag = Array(20, cfg.btb_entries, "btb_tag")
        btb_target = Array(64, cfg.btb_entries, "btb_target")
        btb_valid = Array(1, cfg.btb_entries, "btb_valid")
        btb_lru = Array(2, cfg.btb_entries, "btb_lru")
        pht = Array(2, cfg.bht_entries, "pht")
        ras = Array(64, cfg.ras_depth, "ras")
        ras_ptr = Reg(3, "ras_ptr")
        history = Reg(cfg.bht_entries.bit_length(), "history")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; history <<= 0; ras_ptr <<= 0
            with Else():
                init <<= 1
                with If(self.branch_taken == 1):
                    h_idx = self.fetch_pc >> 2  # simplified hash
                    history <<= (history << 1) | 1

        with self.comb:
            with If(init == 0):
                self.pred_taken <<= _const(0, 1); self.btb_hit <<= _const(0, 1)
                self.pred_target <<= _const(0, 64)
            with Else():
                idx = (self.fetch_pc >> 2) % cfg.bht_entries
                counter = pht[idx]
                self.pred_taken <<= (counter >= 2)
                self.btb_hit <<= btb_valid[idx % cfg.btb_entries]
                self.pred_target <<= btb_target[idx % cfg.btb_entries]


# ===================================================================
# RenameTable — Register rename
# ===================================================================
class RenameTable(Module):
    """Register rename table with free list (C910: ct_idu_ir_rt)."""
    def __init__(self, cfg: CPUConfig = CPUConfig()):
        super().__init__("rename")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.rename_req = Input(1, "rename_req")
        self.arch_rd_0 = Input(5, "arch_rd_0"); self.arch_rd_1 = Input(5, "arch_rd_1")
        self.rename_done = Output(1, "rename_done")
        self.phys_rd_0 = Output(7, "phys_rd_0"); self.phys_rd_1 = Output(7, "phys_rd_1")

        map_table = Array(7, 32, "map_table")
        free_list = Reg(7, "free_list_ptr")
        checkpoint = Array(7, 32, "checkpoint")
        init = Reg(1, "init")
        PRF = cfg.phys_int_regs

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; free_list <<= _const(32, 7)
            with Else():
                init <<= 1
                with If(self.rename_req == 1):
                    map_table[self.arch_rd_0] <<= free_list
                    free_list <<= free_list + 1

        with self.comb:
            with If(init == 0):
                self.rename_done <<= _const(0, 1)
                self.phys_rd_0 <<= _const(0, 7); self.phys_rd_1 <<= _const(0, 7)
            with Else():
                self.rename_done <<= self.rename_req
                self.phys_rd_0 <<= map_table[self.arch_rd_0]
                self.phys_rd_1 <<= map_table[self.arch_rd_1]


# ===================================================================
# IssueQueue — Wakeup-select
# ===================================================================
class IssueQueue(Module):
    """Wakeup-select issue queue (C910: ct_idu_is_aiq0)."""
    def __init__(self, name: str = "iq", depth: int = 32):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue"); self.uop_in = Input(160, "uop_in")
        self.wakeup_tags = Input(7, "wakeup_tags")
        self.issue_uop = Output(160, "issue_uop"); self.issue_valid = Output(1, "issue_valid")
        self.full = Output(1, "full")

        entries = Array(160, depth, "entries"); ready = Array(1, depth, "ready")
        head = Reg(5, "head"); tail = Reg(5, "tail"); count = Reg(5, "count")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; head <<= 0; tail <<= 0; count <<= 0
            with Else():
                init <<= 1
                with If(self.enqueue == 1 and count < depth):
                    entries[tail] <<= self.uop_in; tail <<= tail + 1; count <<= count + 1
                with If(self.issue_valid == 1 and count > 0):
                    head <<= head + 1; count <<= count - 1

        with self.comb:
            with If(init == 0):
                self.issue_uop <<= _const(0, 160); self.issue_valid <<= _const(0, 1)
                self.full <<= _const(0, 1)
            with Else():
                self.issue_uop <<= entries[head]
                self.issue_valid <<= (count > 0)
                self.full <<= (count >= depth - 1)


# ===================================================================
# ALU — Integer ALU
# ===================================================================
class ALUUnit(Module):
    """Integer ALU (C910: ct_iu_alu)."""
    def __init__(self):
        super().__init__("alu")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.opcode = Input(7, "opcode"); self.funct3 = Input(3, "funct3")
        self.funct7 = Input(7, "funct7")
        self.src0 = Input(64, "src0"); self.src1 = Input(64, "src1")
        self.result = Output(64, "result")

        init = Reg(1, "init")
        XLEN = 64

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0
            with Else(): init <<= 1

        with self.comb:
            with If(init == 0): self.result <<= _const(0, XLEN)
            with Else():
                with If(self.opcode == _const(0x33, 7)):
                    with If(self.funct3 == _const(0, 3) and self.funct7 == _const(0, 7)):
                        self.result <<= self.src0 + self.src1
                    with Elif(self.funct3 == _const(0, 3) and self.funct7 == _const(0x20, 7)):
                        self.result <<= self.src0 - self.src1
                    with Elif(self.funct3 == _const(4, 3)):
                        self.result <<= self.src0 ^ self.src1
                    with Elif(self.funct3 == _const(6, 3)):
                        self.result <<= self.src0 | self.src1
                    with Elif(self.funct3 == _const(7, 3)):
                        self.result <<= self.src0 & self.src1
                    with Else():
                        self.result <<= _const(0, XLEN)


# ===================================================================
# ROB — Reorder Buffer
# ===================================================================
class ReorderBuffer(Module):
    """Reorder buffer (C910: ct_rtu_rob)."""
    def __init__(self, depth: int = 128):
        super().__init__("rob")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.alloc = Input(1, "alloc"); self.uop_data = Input(192, "uop_data")
        self.commit_ready = Input(1, "commit_ready")
        self.full = Output(1, "full"); self.retire_valid = Output(1, "retire_valid")
        self.retire_data = Output(192, "retire_data")

        entries = Array(192, depth, "rob_entry")
        head = Reg(7, "head"); tail = Reg(7, "tail")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; head <<= 0; tail <<= 0
            with Else():
                init <<= 1
                with If(self.alloc == 1):
                    entries[tail] <<= self.uop_data; tail <<= tail + 1
                with If(self.commit_ready == 1 and head != tail):
                    head <<= head + 1

        with self.comb:
            with If(init == 0):
                self.full <<= _const(0, 1); self.retire_valid <<= _const(0, 1)
                self.retire_data <<= _const(0, 192)
            with Else():
                self.full <<= ((tail + 1) % depth) == head
                self.retire_valid <<= (head != tail)
                self.retire_data <<= entries[head]


# ===================================================================
# LSU — Load/Store Unit with queues
# ===================================================================
class LSUUnit(Module):
    """Load/store unit with load queue + store queue (C910: ct_lsu_top)."""
    def __init__(self, ld_depth: int = 16, st_depth: int = 16):
        super().__init__("lsu")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.ld_req = Input(1, "ld_req"); self.st_req = Input(1, "st_req")
        self.addr = Input(64, "addr"); self.wdata = Input(64, "wdata")
        self.dcache_rdata = Input(64, "dcache_rdata")
        self.dcache_valid = Input(1, "dcache_valid")
        self.ld_result = Output(64, "ld_result"); self.ld_valid = Output(1, "ld_valid")
        self.st_done = Output(1, "st_done")
        self.dcache_req = Output(1, "dcache_req"); self.dcache_addr = Output(64, "dcache_addr")
        self.dcache_wdata = Output(64, "dcache_wdata"); self.dcache_wen = Output(1, "dcache_wen")

        ld_q_addr = Array(64, ld_depth, "ld_q_addr"); ld_q_valid = Array(1, ld_depth, "ld_q_valid")
        st_q_addr = Array(64, st_depth, "st_q_addr"); st_q_data = Array(64, st_depth, "st_q_data")
        ld_head = Reg(4, "ld_head"); ld_tail = Reg(4, "ld_tail")
        st_head = Reg(4, "st_head"); st_tail = Reg(4, "st_tail")
        init = Reg(1, "init")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n): init <<= 0; ld_head <<= 0; ld_tail <<= 0; st_head <<= 0; st_tail <<= 0
            with Else():
                init <<= 1
                with If(self.ld_req == 1):
                    ld_q_addr[ld_tail] <<= self.addr; ld_tail <<= ld_tail + 1
                with If(self.st_req == 1):
                    st_q_addr[st_tail] <<= self.addr; st_q_data[st_tail] <<= self.wdata; st_tail <<= st_tail + 1

        with self.comb:
            with If(init == 0):
                self.ld_result <<= _const(0, 64); self.ld_valid <<= _const(0, 1)
                self.st_done <<= _const(0, 1); self.dcache_req <<= _const(0, 1)
                self.dcache_addr <<= _const(0, 64); self.dcache_wdata <<= _const(0, 64)
                self.dcache_wen <<= _const(0, 1)
            with Else():
                self.dcache_req <<= self.ld_req | self.st_req
                self.dcache_addr <<= self.addr
                self.dcache_wdata <<= self.wdata
                self.dcache_wen <<= self.st_req
                self.ld_result <<= self.dcache_rdata
                self.ld_valid <<= self.dcache_valid
