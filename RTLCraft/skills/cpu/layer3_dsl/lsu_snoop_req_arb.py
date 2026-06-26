"""
L3 DSL — SnoopReqArb, SnoopReqArb.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SnoopReqArb(Module):
    def __init__(self):
        super().__init__("snoopreqarb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req0 = Input(1, "req0")
        self.req1 = Input(1, "req1")
        self.req2 = Input(1, "req2")
        self.req0_addr = Input(64, "req0_addr")
        self.req1_addr = Input(64, "req1_addr")
        self.req2_addr = Input(64, "req2_addr")
        self.gnt_ack = Input(1, "gnt_ack")
        self.grant = Output(3, "grant")
        self.grant_addr = Output(64, "grant_addr")
        self.grant_valid = Output(1, "grant_valid")
        self.busy = Output(1, "busy")

        self.grant_sel = Reg(2, "grant_sel")
        self.init = Reg(1, "init")
        self.state = Reg(1, "state")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.grant <<= 0
                self.grant_addr <<= 0
                self.grant_valid <<= 0
                self.busy <<= 0
            with Else():
                self.grant_valid <<= (self.state == 1)
                self.busy <<= (self.state == 1)
                with If((self.grant_sel == 0)):
                    self.grant <<= 1
                    self.grant_addr <<= self.req0_addr
                with Elif((self.grant_sel == 1)):
                    self.grant <<= 2
                    self.grant_addr <<= self.req1_addr
                with Else():
                    self.grant <<= 4
                    self.grant_addr <<= self.req2_addr

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.state <<= 0
                self.grant_sel <<= 0
            with Else():
                self.init <<= 1
                with If((self.gnt_ack == 1)):
                    self.state <<= 0
                    self.grant_sel <<= 0
                with If((self.state == 0) & (self.gnt_ack == 0)):
                    with If((self.req0 == 1)):
                        self.state <<= 1
                        self.grant_sel <<= 0
                    with Elif((self.req1 == 1)):
                        self.state <<= 1
                        self.grant_sel <<= 1
                    with Elif((self.req2 == 1)):
                        self.state <<= 1
                        self.grant_sel <<= 2


