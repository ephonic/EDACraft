"""
L3 DSL — IFUDebug, IFUDebug.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class IFUDebug(Module):
    def __init__(self):
        super().__init__("ifudebug")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.fetch_valid = Input(1, "fetch_valid")
        self.icache_miss = Input(1, "icache_miss")
        self.branch_taken = Input(1, "branch_taken")
        self.flush = Input(1, "flush")
        self.fetched_instrs = Output(32, "fetched_instrs")
        self.icache_misses = Output(32, "icache_misses")
        self.branches = Output(32, "branches")
        self.flushes = Output(32, "flushes")

        self.c_branch = Reg(32, "c_branch")
        self.c_fetch = Reg(32, "c_fetch")
        self.c_flush = Reg(32, "c_flush")
        self.c_icache = Reg(32, "c_icache")
        self.init = Reg(1, "init")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.fetched_instrs <<= 0
                self.icache_misses <<= 0
                self.branches <<= 0
                self.flushes <<= 0
            with Else():
                self.fetched_instrs <<= self.c_fetch
                self.icache_misses <<= self.c_icache
                self.branches <<= self.c_branch
                self.flushes <<= self.c_flush

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.c_fetch <<= 0
                self.c_icache <<= 0
                self.c_branch <<= 0
                self.c_flush <<= 0
            with Else():
                self.init <<= 1
                with If((self.fetch_valid == 1)):
                    self.c_fetch <<= self.c_fetch + 1
                with If((self.icache_miss == 1)):
                    self.c_icache <<= self.c_icache + 1
                with If((self.branch_taken == 1)):
                    self.c_branch <<= self.c_branch + 1
                with If((self.flush == 1)):
                    self.c_flush <<= self.c_flush + 1


