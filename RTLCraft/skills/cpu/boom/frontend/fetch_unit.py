"""
BOOM Fetch Unit

Fetches aligned fetch-packets from the I-cache interface.
Interacts with the Branch Predictor to redirect on predicted taken branches.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Vector
from rtlgen.logic import If, Else, Mux


class FetchUnit(Module):
    """Instruction fetch unit with branch-predictor interface.

    Parameters
    ----------
    xlen : int
        XLEN (32 or 64)
    fetch_width : int
        Number of instructions fetched per cycle
    """

    def __init__(self, xlen: int = 32, fetch_width: int = 2, name: str = "FetchUnit"):
        super().__init__(name)
        self.xlen = xlen
        self.fetch_width = fetch_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # I-cache interface
        self.icache_req_valid = Output(1, "icache_req_valid")
        self.icache_req_addr = Output(xlen, "icache_req_addr")
        self.icache_resp_valid = Input(1, "icache_resp_valid")
        self.icache_resp_data = Input(xlen * fetch_width, "icache_resp_data")

        # Branch predictor interface
        self.bp_taken = Input(1, "bp_taken")
        self.bp_target = Input(xlen, "bp_target")
        self.bp_valid = Output(1, "bp_valid")
        self.bp_pc = Output(xlen, "bp_pc")

        # To decode
        self.fetch_valid = Output(1, "fetch_valid")
        self.fetch_ready = Input(1, "fetch_ready")
        self.fetch_pc = Output(xlen, "fetch_pc")
        self.fetch_instrs = Vector(32, fetch_width, "fetch_instrs", vtype=Output)
        self.fetch_mask = Output(fetch_width, "fetch_mask")

        # Redirect from backend (branch mispredict / exception)
        self.redirect_valid = Input(1, "redirect_valid")
        self.redirect_pc = Input(xlen, "redirect_pc")

        # State
        self.pc = Reg(xlen, "pc")
        self.fetch_buffer_valid = Reg(1, "fetch_buffer_valid")
        self.fetch_buffer_pc = Reg(xlen, "fetch_buffer_pc")
        self.fetch_buffer_data = Reg(xlen * fetch_width, "fetch_buffer_data")

        @self.comb
        def _bp():
            self.bp_valid <<= self.fetch_ready
            self.bp_pc <<= self.pc

        @self.comb
        def _icache():
            self.icache_req_valid <<= self.fetch_ready & ~self.fetch_buffer_valid
            self.icache_req_addr <<= self.pc

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.pc <<= 0
                self.fetch_buffer_valid <<= 0
            with Else():
                with If(self.redirect_valid):
                    self.pc <<= self.redirect_pc
                    self.fetch_buffer_valid <<= 0
                with Else():
                    with If(self.fetch_ready):
                        with If(self.bp_taken):
                            self.pc <<= self.bp_target
                        with Else():
                            self.pc <<= self.pc + (4 * fetch_width)

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _buffer():
            with If(self.rst_n == 0):
                self.fetch_buffer_valid <<= 0
            with Else():
                with If(self.icache_resp_valid & self.fetch_ready):
                    self.fetch_buffer_valid <<= 1
                    self.fetch_buffer_pc <<= self.pc
                    self.fetch_buffer_data <<= self.icache_resp_data
                with Else():
                    with If(self.fetch_ready & self.fetch_buffer_valid):
                        self.fetch_buffer_valid <<= 0

        @self.comb
        def _output():
            self.fetch_valid <<= self.fetch_buffer_valid | self.icache_resp_valid
            self.fetch_pc <<= Mux(self.fetch_buffer_valid, self.fetch_buffer_pc, self.pc)
            self.fetch_data = Wire(xlen * fetch_width, "fetch_data")
            self.fetch_data <<= Mux(self.fetch_buffer_valid, self.fetch_buffer_data, self.icache_resp_data)
            for i in range(fetch_width):
                self.fetch_instrs[i] <<= self.fetch_data[(i + 1) * 32 - 1:i * 32]
            self.fetch_mask <<= (1 << fetch_width) - 1
