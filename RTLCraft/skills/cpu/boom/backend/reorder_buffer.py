"""
BOOM Reorder Buffer (ROB)

Circular buffer that tracks in-flight instructions in program order.
Instructions commit in order. Supports exception/mispredict flush.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


class ReorderBuffer(Module):
    """Reorder buffer with commit and exception handling.

    Parameters
    ----------
    num_entries : int
        ROB capacity
    num_enq : int
        Dispatch width (instructions enqueued per cycle)
    preg_bits : int
        Width of physical register index
    xlen : int
        XLEN
    """

    def __init__(
        self,
        num_entries: int = 16,
        num_enq: int = 2,
        preg_bits: int = 6,
        xlen: int = 32,
        name: str = "ReorderBuffer",
    ):
        super().__init__(name)
        self.num_entries = num_entries
        self.entry_bits = max(num_entries.bit_length(), 1)
        self.num_enq = num_enq
        self.preg_bits = preg_bits
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Enqueue from dispatch
        self.enq_valid = Input(num_enq, "enq_valid")
        self.enq_prd = Vector(preg_bits, num_enq, "enq_prd", vtype=Input)
        self.enq_prd_old = Vector(preg_bits, num_enq, "enq_prd_old", vtype=Input)
        self.enq_pc = Vector(xlen, num_enq, "enq_pc", vtype=Input)
        self.enq_is_branch = Input(num_enq, "enq_is_branch")
        self.enq_ready = Output(1, "enq_ready")

        # Writeback notification
        self.wb_valid = Input(num_enq, "wb_valid")
        self.wb_rob_idx = Vector(self.entry_bits, num_enq, "wb_rob_idx", vtype=Input)

        # Commit
        self.commit_valid = Output(num_enq, "commit_valid")
        self.commit_prd = Vector(preg_bits, num_enq, "commit_prd", vtype=Output)
        self.commit_prd_old = Vector(preg_bits, num_enq, "commit_prd_old", vtype=Output)
        self.commit_pc = Vector(xlen, num_enq, "commit_pc", vtype=Output)

        # Exception / redirect
        self.exception_valid = Input(1, "exception_valid")
        self.exception_rob_idx = Input(self.entry_bits, "exception_rob_idx")
        self.redirect_pc = Output(xlen, "redirect_pc")
        self.redirect_valid = Output(1, "redirect_valid")

        # ROB state
        self.head = Reg(self.entry_bits, "head")
        self.tail = Reg(self.entry_bits, "tail")
        self.count = Reg(self.entry_bits + 1, "count")

        self.entry_valid = [Reg(1, f"evalid_{i}") for i in range(num_entries)]
        self.entry_busy = [Reg(1, f"ebusy_{i}") for i in range(num_entries)]
        self.entry_prd = [Reg(preg_bits, f"eprd_{i}") for i in range(num_entries)]
        self.entry_prd_old = [Reg(preg_bits, f"eprd_old_{i}") for i in range(num_entries)]
        self.entry_pc = [Reg(xlen, f"epc_{i}") for i in range(num_entries)]
        self.entry_is_br = [Reg(1, f"eisbr_{i}") for i in range(num_entries)]

        # Check space
        self.enq_num = Wire(self.entry_bits + 1, "enq_num")

        @self.comb
        def _space():
            self.enq_num <<= 0
            for i in range(num_enq):
                with If(self.enq_valid[i]):
                    self.enq_num <<= self.enq_num + 1
            self.enq_ready <<= (self.count + self.enq_num) <= num_entries

        # Commit logic
        @self.comb
        def _commit():
            for i in range(num_enq):
                self.commit_valid[i] <<= 0
                self.commit_prd[i] <<= 0
                self.commit_prd_old[i] <<= 0
                self.commit_pc[i] <<= 0
                for j in range(num_entries):
                    with If((self.head + i) % num_entries == j):
                        self.commit_valid[i] <<= self.entry_valid[j] & ~self.entry_busy[j]
                        self.commit_prd[i] <<= self.entry_prd[j]
                        self.commit_prd_old[i] <<= self.entry_prd_old[j]
                        self.commit_pc[i] <<= self.entry_pc[j]

        # Redirect
        @self.comb
        def _redirect():
            self.redirect_valid <<= self.exception_valid
            self.redirect_pc <<= 0
            for j in range(num_entries):
                with If(self.exception_rob_idx == j):
                    self.redirect_pc <<= self.entry_pc[j]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.head <<= 0
                self.tail <<= 0
                self.count <<= 0
                for i in range(num_entries):
                    self.entry_valid[i] <<= 0
                    self.entry_busy[i] <<= 0
            with Else():
                with If(self.exception_valid):
                    # Flush: clear all entries
                    for i in range(num_entries):
                        self.entry_valid[i] <<= 0
                    self.tail <<= self.exception_rob_idx
                    self.count <<= (self.exception_rob_idx - self.head) % num_entries
                with Else():
                    # Enqueue
                    enq_ptr = self.tail
                    for i in range(num_enq):
                        with If(self.enq_valid[i] & self.enq_ready):
                            for j in range(num_entries):
                                with If(enq_ptr == j):
                                    self.entry_valid[j] <<= 1
                                    self.entry_busy[j] <<= 1
                                    self.entry_prd[j] <<= self.enq_prd[i]
                                    self.entry_prd_old[j] <<= self.enq_prd_old[i]
                                    self.entry_pc[j] <<= self.enq_pc[i]
                                    self.entry_is_br[j] <<= self.enq_is_branch[i]
                            enq_ptr <<= (enq_ptr + 1) % num_entries
                    self.tail <<= enq_ptr
                    self.count <<= self.count + self.enq_num

                    # Writeback clear busy
                    for i in range(num_enq):
                        with If(self.wb_valid[i]):
                            for j in range(num_entries):
                                with If(self.wb_rob_idx[i] == j):
                                    self.entry_busy[j] <<= 0

                    # Commit advance head
                    self.commit_num = Wire(self.entry_bits + 1, "commit_num")
                    self.commit_num <<= 0
                    for i in range(num_enq):
                        with If(self.commit_valid[i]):
                            self.commit_num <<= self.commit_num + 1
                            idx = (self.head + i) % num_entries
                            for j in range(num_entries):
                                with If(idx == j):
                                    self.entry_valid[j] <<= 0
                    self.head <<= (self.head + self.commit_num) % num_entries
                    self.count <<= self.count - self.commit_num
