"""
BOOM Physical Register File

Multi-ported register file with read and write ports.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


class PhysicalRegFile(Module):
    """Physical register file with 6 read ports and 3 write ports.

    BOOM needs many read ports to support multiple issue widths
    and bypass networks.
    """

    def __init__(
        self,
        num_pregs: int = 64,
        num_read: int = 6,
        num_write: int = 3,
        xlen: int = 32,
        name: str = "PhysicalRegFile",
    ):
        super().__init__(name)
        self.num_pregs = num_pregs
        self.preg_bits = max(num_pregs.bit_length(), 1)
        self.num_read = num_read
        self.num_write = num_write
        self.xlen = xlen

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Read ports
        self.raddr = Vector(self.preg_bits, num_read, "raddr", vtype=Input)
        self.rdata = Vector(xlen, num_read, "rdata", vtype=Output)

        # Write ports
        self.wen = Input(num_write, "wen")
        self.waddr = Vector(self.preg_bits, num_write, "waddr", vtype=Input)
        self.wdata = Vector(xlen, num_write, "wdata", vtype=Input)

        # Register array
        self.regs = [Reg(xlen, f"preg_{i}") for i in range(num_pregs)]

        @self.comb
        def _read():
            for r in range(num_read):
                self.rdata[r] <<= 0
                for i in range(num_pregs):
                    with If(self.raddr[r] == i):
                        self.rdata[r] <<= self.regs[i]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write():
            with If(self.rst_n == 0):
                for i in range(num_pregs):
                    self.regs[i] <<= 0
            with Else():
                for w in range(num_write):
                    with If(self.wen[w]):
                        for i in range(num_pregs):
                            with If(self.waddr[w] == i):
                                self.regs[i] <<= self.wdata[w]
