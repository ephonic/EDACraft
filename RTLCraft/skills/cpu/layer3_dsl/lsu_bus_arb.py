"""
L3 DSL — BusArb, BusArb.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class BusArb(Module):
    def __init__(self):
        super().__init__("busarb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req = Input(4, "req")
        self.gnt_ack = Input(1, "gnt_ack")
        self.grant = Output(4, "grant")
        self.grant_valid = Output(1, "grant_valid")
        self.busy = Output(1, "busy")

        self.grant_r = Reg(4, "grant_r")
        self.grant_v = Reg(1, "grant_v")
        self.init = Reg(1, "init")
        self.last = Reg(3, "last")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.grant <<= 0
                self.grant_valid <<= 0
                self.busy <<= 0
            with Else():
                self.grant <<= self.grant_r
                self.grant_valid <<= self.grant_v
                self.busy <<= self.grant_v | (self.req[0] | self.req[1] | self.req[2] | self.req[3]) & ~self.grant_v

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.last <<= 0
                self.grant_r <<= 0
                self.grant_v <<= 0
            with Else():
                self.init <<= 1
                with If((self.gnt_ack == 1)):
                    self.grant_v <<= 0
                    self.grant_r <<= 0
                with If((self.gnt_ack == 0) & (self.grant_v == 0)):
                    with If((self.last == 0)):
                        with If((self.req[0] == 1)):
                            self.grant_r <<= 1
                            self.grant_v <<= 1
                            self.last <<= 1
                        with Elif((self.req[1] == 1)):
                            self.grant_r <<= 2
                            self.grant_v <<= 1
                            self.last <<= 2
                        with Elif((self.req[2] == 1)):
                            self.grant_r <<= 4
                            self.grant_v <<= 1
                            self.last <<= 3
                        with Elif((self.req[3] == 1)):
                            self.grant_r <<= 8
                            self.grant_v <<= 1
                            self.last <<= 0
                    with Elif((self.last == 1)):
                        with If((self.req[1] == 1)):
                            self.grant_r <<= 2
                            self.grant_v <<= 1
                            self.last <<= 2
                        with Elif((self.req[2] == 1)):
                            self.grant_r <<= 4
                            self.grant_v <<= 1
                            self.last <<= 3
                        with Elif((self.req[3] == 1)):
                            self.grant_r <<= 8
                            self.grant_v <<= 1
                            self.last <<= 0
                        with Elif((self.req[0] == 1)):
                            self.grant_r <<= 1
                            self.grant_v <<= 1
                            self.last <<= 1
                    with Elif((self.last == 2)):
                        with If((self.req[2] == 1)):
                            self.grant_r <<= 4
                            self.grant_v <<= 1
                            self.last <<= 3
                        with Elif((self.req[3] == 1)):
                            self.grant_r <<= 8
                            self.grant_v <<= 1
                            self.last <<= 0
                        with Elif((self.req[0] == 1)):
                            self.grant_r <<= 1
                            self.grant_v <<= 1
                            self.last <<= 1
                        with Elif((self.req[1] == 1)):
                            self.grant_r <<= 2
                            self.grant_v <<= 1
                            self.last <<= 2
                    with Elif((self.req[3] == 1)):
                        self.grant_r <<= 8
                        self.grant_v <<= 1
                        self.last <<= 0
                    with Elif((self.req[0] == 1)):
                        self.grant_r <<= 1
                        self.grant_v <<= 1
                        self.last <<= 1
                    with Elif((self.req[1] == 1)):
                        self.grant_r <<= 2
                        self.grant_v <<= 1
                        self.last <<= 2
                    with Elif((self.req[2] == 1)):
                        self.grant_r <<= 4
                        self.grant_v <<= 1
                        self.last <<= 3


