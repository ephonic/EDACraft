"""
NeuralAccel Instruction Memory

Simple single-port SRAM for storing 32-bit NPU instructions.
Supports:
  - External program loading (write-only from host)
  - Internal instruction fetch (read-only by NPU controller)

The read port is combinational (addressed by PC) so that
FETCH and DECODE can occur in the same cycle.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Memory
from rtlgen.logic import If


class InstructionMemory(Module):
    """Single-port instruction SRAM with external load + internal fetch."""

    def __init__(self, depth: int = 1024, name: str = "InstructionMemory"):
        super().__init__(name)
        self.depth = depth
        self.addr_width = max((depth - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # External Program Load Interface (host -> inst memory)
        # -----------------------------------------------------------------
        self.load_valid = Input(1, "load_valid")
        self.load_addr = Input(self.addr_width, "load_addr")
        self.load_data = Input(32, "load_data")
        self.load_we = Input(1, "load_we")

        # -----------------------------------------------------------------
        # Internal Instruction Fetch Interface (NPU controller -> decode)
        # -----------------------------------------------------------------
        self.fetch_addr = Input(self.addr_width, "fetch_addr")
        self.fetch_data = Output(32, "fetch_data")
        self.fetch_valid = Output(1, "fetch_valid")

        # -----------------------------------------------------------------
        # Storage
        # -----------------------------------------------------------------
        self.mem = Memory(32, depth, "mem")
        self.add_memory(self.mem, "mem")

        # Combinational read for instruction fetch
        @self.comb
        def _fetch():
            self.fetch_data <<= self.mem[self.fetch_addr]

        # fetch_valid is asserted when fetch_addr is within program range
        self.fetch_valid <<= 1  # always valid for now

        # Sequential write for program loading
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write():
            with If(self.rst_n != 0):
                with If(self.load_valid & self.load_we):
                    self.mem[self.load_addr] <<= self.load_data
