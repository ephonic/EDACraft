"""
NeuralAccel Ping-Pong SRAM Buffer

Dual-bank SRAM that allows one bank to be accessed while the other
is swapped / reconfigured.  Used for double-buffering activations,
weights, and outputs in the compute pipeline.

Ports:
  - req_valid, req_addr, req_wdata, req_we : read/write request
  - resp_valid, resp_data                    : read response (1-cycle latency)
  - bank_swap                                : pulse to toggle active bank
  - active_bank                              : output showing which bank is active
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Memory, Wire
from rtlgen.logic import If, Else, Mux


class PingPongSRAM(Module):
    """Dual-bank SRAM with ping-pong switching."""

    def __init__(self, width: int = 16, depth: int = 256, name: str = "PingPongSRAM"):
        super().__init__(name)
        self.width = width
        self.depth = depth
        self.addr_width = max((depth - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Access interface (to active bank)
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(self.addr_width, "req_addr")
        self.req_wdata = Input(width, "req_wdata")
        self.req_we = Input(1, "req_we")
        self.resp_valid = Output(1, "resp_valid")
        self.resp_data = Output(width, "resp_data")

        # Bank control
        self.bank_swap = Input(1, "bank_swap")
        self.active_bank = Output(1, "active_bank")

        # Two SRAM banks
        self.bank0 = Memory(width, depth, "bank0")
        self.bank1 = Memory(width, depth, "bank1")
        self.add_memory(self.bank0, "bank0")
        self.add_memory(self.bank1, "bank1")

        # Active bank selector
        self.bank_sel = Reg(1, "bank_sel")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _bank_sel_seq():
            with If(self.rst_n == 0):
                self.bank_sel <<= 0
            with Else():
                with If(self.bank_swap):
                    self.bank_sel <<= ~self.bank_sel

        self.active_bank <<= self.bank_sel

        # Read data from both banks (combinational)
        self.rdata0 = Wire(width, "rdata0")
        self.rdata1 = Wire(width, "rdata1")

        @self.comb
        def _read():
            self.rdata0 <<= self.bank0[self.req_addr]
            self.rdata1 <<= self.bank1[self.req_addr]
            self.resp_data <<= Mux(self.bank_sel, self.rdata1, self.rdata0)

        self.resp_valid <<= self.req_valid & ~self.req_we

        # Write to active bank (sequential)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write():
            with If(self.rst_n != 0):
                with If(self.req_valid & self.req_we):
                    with If(self.bank_sel == 0):
                        self.bank0[self.req_addr] <<= self.req_wdata
                    with Else():
                        self.bank1[self.req_addr] <<= self.req_wdata
