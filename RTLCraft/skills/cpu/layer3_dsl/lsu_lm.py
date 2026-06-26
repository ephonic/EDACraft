"""
L3 DSL — LoadMiss, LoadMiss.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LoadMiss(Module):
    def __init__(self):
        super().__init__("loadmiss")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.miss_addr = Input(64, "miss_addr")
        self.miss_valid = Input(1, "miss_valid")
        self.refill_data = Input(128, "refill_data")
        self.refill_valid = Input(1, "refill_valid")
        self.req_valid = Output(1, "req_valid")
        self.req_addr = Output(64, "req_addr")
        self.refill_ready = Output(1, "refill_ready")
        self.busy = Output(1, "busy")

        self.addr_r = Reg(64, "addr_r")
        self.init = Reg(1, "init")
        self.state = Reg(2, "state")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.req_valid <<= 0
                self.req_addr <<= 0
                self.refill_ready <<= 0
                self.busy <<= 0
            with Else():
                self.busy <<= (self.state != 0)
                self.req_valid <<= (self.state == 1)
                self.req_addr <<= self.addr_r
                self.refill_ready <<= (self.state == 2)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.state <<= 0
                self.addr_r <<= 0
            with Else():
                self.init <<= 1
                with If((self.state == 0)):
                    with If((self.miss_valid == 1)):
                        self.addr_r <<= self.miss_addr
                        self.state <<= 1
                with Elif((self.state == 1)):
                    self.state <<= 2
                with Elif((self.state == 2)):
                    with If((self.refill_valid == 1)):
                        self.state <<= 3
                with Elif((self.state == 3)):
                    self.state <<= 0


