"""
BOOM Reservation Station (Issue Queue)

Collects renamed instructions and issues them to execution units when
all source operands are ready.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


class ReservationStation(Module):
    """Simple unified reservation station.

    Parameters
    ----------
    num_entries : int
        Number of RS entries
    num_wakeup : int
        Number of wakeup ports (writeback -> RS)
    preg_bits : int
        Width of physical register index
    xlen : int
        XLEN
    """

    def __init__(
        self,
        num_entries: int = 8,
        num_wakeup: int = 2,
        preg_bits: int = 6,
        xlen: int = 32,
        name: str = "ReservationStation",
    ):
        super().__init__(name)
        self.num_entries = num_entries
        self.entry_bits = max(num_entries.bit_length(), 1)
        self.num_wakeup = num_wakeup
        self.preg_bits = preg_bits
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Enqueue from rename
        self.enq_valid = Input(1, "enq_valid")
        self.enq_prs1 = Input(preg_bits, "enq_prs1")
        self.enq_prs2 = Input(preg_bits, "enq_prs2")
        self.enq_prd = Input(preg_bits, "enq_prd")
        self.enq_prs1_busy = Input(1, "enq_prs1_busy")
        self.enq_prs2_busy = Input(1, "enq_prs2_busy")
        self.enq_op = Input(4, "enq_op")           # ALU opcode
        self.enq_fu_type = Input(2, "enq_fu_type")  # 0=ALU, 1=MUL, 2=LSU
        self.enq_ready = Output(1, "enq_ready")

        # Issue to FU
        self.issue_valid = Output(1, "issue_valid")
        self.issue_prs1 = Output(preg_bits, "issue_prs1")
        self.issue_prs2 = Output(preg_bits, "issue_prs2")
        self.issue_prd = Output(preg_bits, "issue_prd")
        self.issue_op = Output(4, "issue_op")
        self.issue_fu_type = Output(2, "issue_fu_type")
        self.issue_ready = Input(1, "issue_ready")

        # Wakeup from writeback
        self.wakeup_valid = Input(num_wakeup, "wakeup_valid")
        self.wakeup_prd = Vector(preg_bits, num_wakeup, "wakeup_prd", vtype=Input)

        # Entry state
        self.valid = [Reg(1, f"valid_{i}") for i in range(num_entries)]
        self.busy1 = [Reg(1, f"busy1_{i}") for i in range(num_entries)]
        self.busy2 = [Reg(1, f"busy2_{i}") for i in range(num_entries)]
        self.entry_prs1 = [Reg(preg_bits, f"prs1_{i}") for i in range(num_entries)]
        self.entry_prs2 = [Reg(preg_bits, f"prs2_{i}") for i in range(num_entries)]
        self.entry_prd = [Reg(preg_bits, f"prd_{i}") for i in range(num_entries)]
        self.entry_op = [Reg(4, f"op_{i}") for i in range(num_entries)]
        self.entry_fu = [Reg(2, f"fu_{i}") for i in range(num_entries)]

        # Find first free entry for enqueue
        self.free_entry = Wire(self.entry_bits, "free_entry")
        self.has_free = Wire(1, "has_free")

        @self.comb
        def _find_free():
            self.has_free <<= 0
            self.free_entry <<= 0
            for i in range(num_entries):
                with If(~self.valid[i] & ~self.has_free):
                    self.has_free <<= 1
                    self.free_entry <<= i

        self.enq_ready <<= self.has_free

        # Find first ready entry for issue
        self.issue_entry = Wire(self.entry_bits, "issue_entry")
        self.has_ready = Wire(1, "has_ready")

        @self.comb
        def _find_ready():
            self.has_ready <<= 0
            self.issue_entry <<= 0
            for i in range(num_entries):
                with If(self.valid[i] & ~self.busy1[i] & ~self.busy2[i] & ~self.has_ready):
                    self.has_ready <<= 1
                    self.issue_entry <<= i

        self.issue_valid <<= self.has_ready & self.issue_ready
        self.issue_prs1 <<= Mux(self.has_ready, self.entry_prs1[0], 0)
        self.issue_prs2 <<= Mux(self.has_ready, self.entry_prs2[0], 0)
        self.issue_prd <<= Mux(self.has_ready, self.entry_prd[0], 0)
        self.issue_op <<= Mux(self.has_ready, self.entry_op[0], 0)
        self.issue_fu_type <<= Mux(self.has_ready, self.entry_fu[0], 0)

        for i in range(num_entries):
            with If(self.has_ready & (self.issue_entry == i)):
                self.issue_prs1 <<= self.entry_prs1[i]
                self.issue_prs2 <<= self.entry_prs2[i]
                self.issue_prd <<= self.entry_prd[i]
                self.issue_op <<= self.entry_op[i]
                self.issue_fu_type <<= self.entry_fu[i]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                for i in range(num_entries):
                    self.valid[i] <<= 0
            with Else():
                # Enqueue
                with If(self.enq_valid & self.has_free):
                    for i in range(num_entries):
                        with If(self.free_entry == i):
                            self.valid[i] <<= 1
                            self.busy1[i] <<= self.enq_prs1_busy
                            self.busy2[i] <<= self.enq_prs2_busy
                            self.entry_prs1[i] <<= self.enq_prs1
                            self.entry_prs2[i] <<= self.enq_prs2
                            self.entry_prd[i] <<= self.enq_prd
                            self.entry_op[i] <<= self.enq_op
                            self.entry_fu[i] <<= self.enq_fu_type

                # Issue (clear entry)
                with If(self.issue_valid & self.issue_ready & self.has_ready):
                    for i in range(num_entries):
                        with If(self.issue_entry == i):
                            self.valid[i] <<= 0

                # Wakeup
                for w in range(num_wakeup):
                    with If(self.wakeup_valid[w]):
                        for i in range(num_entries):
                            with If(self.entry_prs1[i] == self.wakeup_prd[w]):
                                self.busy1[i] <<= 0
                            with If(self.entry_prs2[i] == self.wakeup_prd[w]):
                                self.busy2[i] <<= 0
