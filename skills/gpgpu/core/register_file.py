"""
GPGPU Vector Register File

Per-lane independent register arrays:
  - 32 lanes (one per thread in a warp)
  - Each lane has `num_regs` 32-bit registers
  - 2 combinational read ports + 1 sequential write port per lane
  - Write-enable gated per-lane by predicate mask

This architecture naturally avoids bank conflicts because each lane
has its own physical register array.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Array
from rtlgen.logic import If

from skills.gpgpu.common.params import GPGPUParams


class RegisterFile(Module):
    """Multi-port vector register file with per-lane storage."""

    def __init__(self, params: GPGPUParams = None, name: str = "RegisterFile"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.num_lanes = params.alu_lanes
        self.num_regs = params.num_regs
        self.reg_width = params.reg_width
        self.addr_width = max((self.num_regs - 1).bit_length(), 1)

        # -----------------------------------------------------------------
        # Clock / Reset
        # -----------------------------------------------------------------
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Read port A (combinational)
        # -----------------------------------------------------------------
        self.rd_addr_a = Input(self.addr_width, "rd_addr_a")
        # Per-lane read data A
        self.rd_data_a = [Output(self.reg_width, f"rd_data_a_{i}") for i in range(self.num_lanes)]

        # -----------------------------------------------------------------
        # Read port B (combinational)
        # -----------------------------------------------------------------
        self.rd_addr_b = Input(self.addr_width, "rd_addr_b")
        self.rd_data_b = [Output(self.reg_width, f"rd_data_b_{i}") for i in range(self.num_lanes)]

        # -----------------------------------------------------------------
        # Write port (sequential)
        # -----------------------------------------------------------------
        self.wr_addr = Input(self.addr_width, "wr_addr")
        self.wr_data = [Input(self.reg_width, f"wr_data_{i}") for i in range(self.num_lanes)]
        self.wr_en = Input(self.num_lanes, "wr_en")  # per-lane predicate mask

        # -----------------------------------------------------------------
        # Per-lane register arrays
        # -----------------------------------------------------------------
        self.lane_regs = [
            Array(self.reg_width, self.num_regs, f"lane_regs_{i}")
            for i in range(self.num_lanes)
        ]

        # -----------------------------------------------------------------
        # Combinational read
        # -----------------------------------------------------------------
        @self.comb
        def _read():
            for i in range(self.num_lanes):
                self.rd_data_a[i] <<= self.lane_regs[i][self.rd_addr_a]
                self.rd_data_b[i] <<= self.lane_regs[i][self.rd_addr_b]

        # -----------------------------------------------------------------
        # Sequential write (gated by per-lane predicate)
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write():
            for i in range(self.num_lanes):
                with If(self.wr_en[i]):
                    self.lane_regs[i][self.wr_addr] <<= self.wr_data[i]
