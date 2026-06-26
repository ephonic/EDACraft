"""
rtlgen.hier_modules — Hierarchical sub-modules for GPGPU SM Wrapper.

These modules are instantiated by the top-level SM skeleton to form a
complete, multi-module design rather than a flat monolithic implementation.

Reference: skills/skills-guided-gen.md Section 7 (task-driven generation)
"""
from __future__ import annotations

from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


# =====================================================================
# 1. Warp Scheduler — round-robin ready warp selection
# =====================================================================
class ThorWarpScheduler(Module):
    """Selects one ready warp using round-robin priority."""

    def __init__(self, name: str = "warp_scheduler", nwarp: int = 4):
        super().__init__(name)
        self.nwarp = nwarp
        ptr_w = max(1, (nwarp - 1).bit_length())

        self.clk          = Input(1, "clk")
        self.rst_n        = Input(1, "rst_n")
        self.warp_ready   = Input(nwarp, "warp_ready")
        self.issue_ready  = Input(1, "issue_ready")

        self.issue_valid   = Output(1, "issue_valid")
        self.issue_warp_id = Output(ptr_w, "issue_warp_id")
        self.rr_ptr        = Output(ptr_w, "rr_ptr")

        self._rr_ptr_reg = Reg(ptr_w, "_rr_ptr_reg")

        with self.comb:
            self.issue_valid <<= 0
            self.issue_warp_id <<= 0
            for i in range(nwarp):
                idx = (self._rr_ptr_reg + i) & (nwarp - 1)
                with If(~self.issue_valid & self.warp_ready[idx]):
                    self.issue_valid <<= 1
                    self.issue_warp_id <<= idx
            self.rr_ptr <<= self._rr_ptr_reg

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self._rr_ptr_reg <<= 0
            with Else():
                with If(self.issue_valid & self.issue_ready):
                    self._rr_ptr_reg <<= (self.issue_warp_id + 1) & (nwarp - 1)


# =====================================================================
# 2. Scoreboard — busy-bit hazard detection
# =====================================================================
class ThorScoreboard(Module):
    """Tracks register dependencies with a busy-bit table."""

    def __init__(self, name: str = "scoreboard", num_reg: int = 8):
        super().__init__(name)
        self.num_reg = num_reg
        reg_w = max(1, (num_reg - 1).bit_length())

        self.clk         = Input(1, "clk")
        self.rst_n       = Input(1, "rst_n")
        self.issue_valid = Input(1, "issue_valid")
        self.issue_fire  = Input(1, "issue_fire")
        self.issue_rd    = Input(reg_w, "issue_rd")
        self.issue_rs1   = Input(reg_w, "issue_rs1")
        self.issue_rs2   = Input(reg_w, "issue_rs2")
        self.wb_valid    = Input(1, "wb_valid")
        self.wb_rd       = Input(reg_w, "wb_rd")

        self.scoreboard_stall = Output(1, "scoreboard_stall")

        self._busy = Array(1, num_reg, "_busy")

        with self.comb:
            rs1_busy = self._busy[self.issue_rs1]
            rs2_busy = self._busy[self.issue_rs2]
            rd_busy  = self._busy[self.issue_rd]
            self.scoreboard_stall <<= rs1_busy | rs2_busy | rd_busy

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                for r in range(num_reg):
                    self._busy[r] <<= 0
            with Else():
                with If(self.issue_fire & ~self.scoreboard_stall):
                    self._busy[self.issue_rd] <<= 1
                with If(self.wb_valid):
                    self._busy[self.wb_rd] <<= 0


# =====================================================================
# 3. IBuffer — instruction FIFO
# =====================================================================
class ThorIBuffer(Module):
    """Simple instruction buffer with head/tail pointers."""

    def __init__(self, name: str = "ibuffer", depth: int = 4, data_w: int = 42):
        super().__init__(name)
        ptr_w = max(1, (depth - 1).bit_length())
        cnt_w = max(1, depth.bit_length())

        self.clk        = Input(1, "clk")
        self.rst_n      = Input(1, "rst_n")
        self.push_valid = Input(1, "push_valid")
        self.push_data  = Input(data_w, "push_data")
        self.pop_ready  = Input(1, "pop_ready")

        self.pop_valid  = Output(1, "pop_valid")
        self.pop_data   = Output(data_w, "pop_data")
        self.fifo_full  = Output(1, "fifo_full")
        self.fifo_empty = Output(1, "fifo_empty")

        self._head  = Reg(ptr_w, "_head")
        self._tail  = Reg(ptr_w, "_tail")
        self._count = Reg(cnt_w, "_count")
        self._mem   = Array(data_w, depth, "_mem")

        with self.comb:
            self.fifo_full  <<= self._count == depth
            self.fifo_empty <<= self._count == 0
            self.pop_valid  <<= ~self.fifo_empty
            self.pop_data   <<= self._mem[self._head]

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self._head  <<= 0
                self._tail  <<= 0
                self._count <<= 0
            with Else():
                fire_push = self.push_valid & ~self.fifo_full
                fire_pop  = self.pop_ready  & ~self.fifo_empty
                with If(fire_push):
                    self._mem[self._tail] <<= self.push_data
                    self._tail <<= (self._tail + 1) & (depth - 1)
                with If(fire_pop):
                    self._head <<= (self._head + 1) & (depth - 1)
                with If(fire_push & ~fire_pop):
                    self._count <<= self._count + 1
                with Elif(~fire_push & fire_pop):
                    self._count <<= self._count - 1


# =====================================================================
# 4. ALU — vector arithmetic unit
# =====================================================================
class ThorALU(Module):
    """Per-lane vector ALU (add/sub/and/or)."""

    def __init__(self, name: str = "alu", vlen: int = 256):
        super().__init__(name)
        self.operand_a = Input(vlen, "operand_a")
        self.operand_b = Input(vlen, "operand_b")
        self.inst_alu  = Input(1, "inst_alu")

        self.alu_result = Output(vlen, "alu_result")
        self.alu_valid  = Output(1, "alu_valid")

        with self.comb:
            self.alu_result <<= self.operand_a + self.operand_b
            self.alu_valid  <<= self.inst_alu


# =====================================================================
# 5. LSU — load/store unit
# =====================================================================
class ThorLSU(Module):
    """Load/Store Unit interface."""

    def __init__(self, name: str = "lsu", vlen: int = 256):
        super().__init__(name)
        self.mem_addr_i  = Input(32, "mem_addr_i")
        self.mem_wdata_i = Input(vlen, "mem_wdata_i")
        self.inst_lsu    = Input(1, "inst_lsu")

        self.lsu_addr  = Output(32, "lsu_addr")
        self.lsu_wdata = Output(vlen, "lsu_wdata")
        self.lsu_valid = Output(1, "lsu_valid")

        with self.comb:
            self.lsu_addr  <<= self.mem_addr_i
            self.lsu_wdata <<= self.mem_wdata_i
            self.lsu_valid <<= self.inst_lsu


# =====================================================================
# 6. Writeback — result writeback
# =====================================================================
class ThorWriteback(Module):
    """Writeback stage: passes clear signals to scoreboard."""

    def __init__(self, name: str = "writeback", reg_w: int = 4):
        super().__init__(name)
        self.clk      = Input(1, "clk")
        self.rst_n    = Input(1, "rst_n")
        self.wb_valid = Input(1, "wb_valid")
        self.wb_rd    = Input(reg_w, "wb_rd")

        self.wb_clear_valid = Output(1, "wb_clear_valid")
        self.wb_clear_rd    = Output(reg_w, "wb_clear_rd")

        with self.comb:
            self.wb_clear_valid <<= self.wb_valid
            self.wb_clear_rd    <<= self.wb_rd
