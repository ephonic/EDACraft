"""
NeuralAccel Scratchpad SRAM

Simple single-port SRAM for general-purpose on-chip storage.
Used as temporary workspace between compute stages.

Ports:
  - req_valid, req_addr, req_wdata, req_we : read/write request
  - resp_valid, resp_data                    : read response (combinational)
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Memory
from rtlgen.logic import If


class Scratchpad(Module):
    """Single-port scratchpad SRAM."""

    def __init__(self, width: int = 16, depth: int = 256, name: str = "Scratchpad"):
        super().__init__(name)
        self.width = width
        self.depth = depth
        self.addr_width = max((depth - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Access interface
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(self.addr_width, "req_addr")
        self.req_wdata = Input(width, "req_wdata")
        self.req_we = Input(1, "req_we")
        self.resp_valid = Output(1, "resp_valid")
        self.resp_data = Output(width, "resp_data")

        # Single SRAM
        self.mem = Memory(width, depth, "mem")
        self.add_memory(self.mem, "mem")

        # Combinational read
        @self.comb
        def _read():
            self.resp_data <<= self.mem[self.req_addr]

        self.resp_valid <<= self.req_valid & ~self.req_we

        # Sequential write
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write():
            with If(self.rst_n != 0):
                with If(self.req_valid & self.req_we):
                    self.mem[self.req_addr] <<= self.req_wdata
