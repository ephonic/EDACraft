"""
BOOM Rename Unit

Renames architectural registers to physical registers using a Free List.
Manages the Rename Map Table (RMT) and Busy Table.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else


class RenameUnit(Module):
    """Register rename unit.

    Ports
    -----
    dec_valid[0:width-1]     : decode bundle valid bits
    dec_rs1[0:width-1]       : source 1 arch register
    dec_rs2[0:width-1]       : source 2 arch register
    dec_rd[0:width-1]        : destination arch register
    dec_need_rs1/2           : whether inst needs source operand
    dec_need_rd              : whether inst writes destination

    ren_valid[0:width-1]     : renamed bundle valid
    prs1[0:width-1]          : physical source 1
    prs2[0:width-1]          : physical source 2
    prd[0:width-1]           : physical destination
    prd_old[0:width-1]       : old physical dest (for rollback)
    ready_out                : rename stage has resources

    commit_valid[0:width-1]  : ROB commit (free old PPD)
    commit_prd_old[0:width-1]: old physical reg to free
    rollback_valid           : exception / mispredict flush
    """

    def __init__(
        self,
        num_pregs: int = 64,
        width: int = 2,
        name: str = "RenameUnit",
    ):
        super().__init__(name)
        self.num_pregs = num_pregs
        self.preg_bits = max(num_pregs.bit_length(), 1)
        self.width = width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Decode input
        self.dec_valid = Input(width, "dec_valid")
        self.dec_rs1 = Vector(5, width, "dec_rs1", vtype=Input)
        self.dec_rs2 = Vector(5, width, "dec_rs2", vtype=Input)
        self.dec_rd = Vector(5, width, "dec_rd", vtype=Input)
        self.dec_need_rs1 = Input(width, "dec_need_rs1")
        self.dec_need_rs2 = Input(width, "dec_need_rs2")
        self.dec_need_rd = Input(width, "dec_need_rd")

        # Renamed output
        self.ren_valid = Output(width, "ren_valid")
        self.prs1 = Vector(self.preg_bits, width, "prs1", vtype=Output)
        self.prs2 = Vector(self.preg_bits, width, "prs2", vtype=Output)
        self.prd = Vector(self.preg_bits, width, "prd", vtype=Output)
        self.prd_old = Vector(self.preg_bits, width, "prd_old", vtype=Output)
        self.ready_out = Output(1, "ready_out")

        # Commit / rollback
        self.commit_valid = Input(width, "commit_valid")
        self.commit_prd_old = Vector(self.preg_bits, width, "commit_prd_old", vtype=Input)
        self.rollback_valid = Input(1, "rollback_valid")

        # Rename Map Table (RMT): arch -> phys
        self.rmt = [Reg(self.preg_bits, f"rmt_{i}") for i in range(32)]

        # Free List: simple bit-vector free list
        self.free_list = [Reg(1, f"free_{i}") for i in range(num_pregs)]

        # Busy Table: which pregs are not yet ready
        self.busy_table = [Reg(1, f"busy_{i}") for i in range(num_pregs)]

        @self.comb
        def _rename():
            self.ren_valid <<= self.dec_valid
            self.ready_out <<= 1  # simplified: always ready

            for w in range(width):
                self.prs1[w] <<= self.rmt[0]
                self.prs2[w] <<= self.rmt[0]
                self.prd[w] <<= 0
                self.prd_old[w] <<= 0

                for a in range(32):
                    with If(self.dec_rs1[w] == a):
                        self.prs1[w] <<= self.rmt[a]
                    with If(self.dec_rs2[w] == a):
                        self.prs2[w] <<= self.rmt[a]

                # Allocate new PREG from free list (simplified: sequential scan)
                with If(self.dec_need_rd[w]):
                    for p in range(num_pregs):
                        with If(self.free_list[p] == 1):
                            self.prd[w] <<= p
                            self.prd_old[w] <<= self.rmt[0]
                            for a in range(32):
                                with If(self.dec_rd[w] == a):
                                    self.prd_old[w] <<= self.rmt[a]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _update():
            with If(self.rst_n == 0):
                for i in range(32):
                    self.rmt[i] <<= i  # identity map for first 32 pregs
                for i in range(num_pregs):
                    self.free_list[i] <<= 1 if i >= 32 else 0
                    self.busy_table[i] <<= 0
            with Else():
                with If(self.rollback_valid):
                    # Simplified rollback: restore RMT from ROB checkpoint
                    pass
                with Else():
                    for w in range(width):
                        with If(self.dec_valid[w] & self.dec_need_rd[w]):
                            # Update RMT and mark busy
                            for a in range(32):
                                with If(self.dec_rd[w] == a):
                                    self.rmt[a] <<= self.prd[w]
                            # Mark new preg busy
                            for p in range(num_pregs):
                                with If(self.prd[w] == p):
                                    self.busy_table[p] <<= 1
                                    self.free_list[p] <<= 0

                    # Commit: free old pregs
                    for w in range(width):
                        with If(self.commit_valid[w]):
                            for p in range(num_pregs):
                                with If(self.commit_prd_old[w] == p):
                                    self.free_list[p] <<= 1
