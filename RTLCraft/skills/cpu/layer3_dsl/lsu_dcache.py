"""
L3 DSL — DCacheIF, DCacheIF.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class DCacheIF(Module):
    def __init__(self):
        super().__init__("dcacheif")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(64, "req_addr")
        self.req_we = Input(1, "req_we")
        self.req_wdata = Input(64, "req_wdata")
        self.req_size = Input(3, "req_size")
        self.cache_rdata = Input(64, "cache_rdata")
        self.cache_ready = Input(1, "cache_ready")
        self.cache_ack = Input(1, "cache_ack")
        self.req_ready = Output(1, "req_ready")
        self.rdata = Output(64, "rdata")
        self.rvalid = Output(1, "rvalid")
        self.miss = Output(1, "miss")
        self.busy = Output(1, "busy")

        self.addr_r = Reg(64, "addr_r")
        self.init = Reg(1, "init")
        self.pending = Reg(1, "pending")
        self.size_r = Reg(3, "size_r")
        self.wdata_r = Reg(64, "wdata_r")
        self.we_r = Reg(1, "we_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.req_ready <<= 0
                self.rdata <<= 0
                self.rvalid <<= 0
                self.miss <<= 0
                self.busy <<= 1
            with Else():
                self.req_ready <<= (self.pending == 0) & self.cache_ready
                self.rdata <<= self.cache_rdata
                self.rvalid <<= self.cache_ack & self.pending
                self.miss <<= 0
                self.busy <<= self.pending

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pending <<= 0
            with Else():
                self.init <<= 1
                with If((self.req_valid == 1) & (self.pending == 0) & (self.cache_ready == 1)):
                    self.pending <<= 1
                    self.addr_r <<= self.req_addr
                    self.we_r <<= self.req_we
                    self.wdata_r <<= self.req_wdata
                    self.size_r <<= self.req_size
                with If((self.cache_ack == 1)):
                    self.pending <<= 0


