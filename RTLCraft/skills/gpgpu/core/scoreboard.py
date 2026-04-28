"""
GPGPU Scoreboard — Register dependency tracking

MVP simplification: always ready (no hazard tracking).
Full scoreboard would track in-flight writes per warp.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If

from skills.gpgpu.common.params import GPGPUParams


class Scoreboard(Module):
    """In-flight instruction tracker for hazard detection (MVP: passthrough)."""

    def __init__(self, params: GPGPUParams = None, name: str = "Scoreboard"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.num_warps = params.num_warps
        self.num_regs = params.num_regs
        self.entries = params.scoreboard_entries
        self.addr_width = max((self.num_regs - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Issue interface
        self.issue_valid = Input(1, "issue_valid")
        self.issue_warp = Input(max((self.num_warps - 1).bit_length(), 1), "issue_warp")
        self.issue_dst = Input(self.addr_width, "issue_dst")
        self.issue_src_a = Input(self.addr_width, "issue_src_a")
        self.issue_src_b = Input(self.addr_width, "issue_src_b")
        self.issue_src_c = Input(self.addr_width, "issue_src_c")
        self.issue_ready = Output(1, "issue_ready")

        # Writeback interface
        self.wb_valid = Input(1, "wb_valid")
        self.wb_warp = Input(max((self.num_warps - 1).bit_length(), 1), "wb_warp")
        self.wb_dst = Input(self.addr_width, "wb_dst")

        # MVP: always ready, no hazard tracking
        self.issue_ready <<= 1

        # Minimal entry tracking for potential debug (single entry, round-robin)
        self.entry_valid = [Reg(1, f"entry_valid_{i}") for i in range(min(self.entries, 4))]
        self.entry_warp = [Reg(max((self.num_warps - 1).bit_length(), 1), f"entry_warp_{i}") for i in range(min(self.entries, 4))]
        self.entry_reg = [Reg(self.addr_width, f"entry_reg_{i}") for i in range(min(self.entries, 4))]
        self.alloc_ptr = Reg(2, "alloc_ptr")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _manage():
            # Clear on writeback
            for i in range(len(self.entry_valid)):
                with If(self.wb_valid & self.entry_valid[i] &
                        (self.entry_warp[i] == self.wb_warp) &
                        (self.entry_reg[i] == self.wb_dst)):
                    self.entry_valid[i] <<= 0

            # Allocate on issue (round-robin among 4 entries)
            with If(self.issue_valid):
                idx = self.alloc_ptr % len(self.entry_valid)
                for i in range(len(self.entry_valid)):
                    with If(idx == i):
                        self.entry_valid[i] <<= 1
                        self.entry_warp[i] <<= self.issue_warp
                        self.entry_reg[i] <<= self.issue_dst
                self.alloc_ptr <<= self.alloc_ptr + 1
