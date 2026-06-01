"""
L3 DSL — ICC, ICC.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ICC(Module):
    def __init__(self):
        super().__init__("icc")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.snoop_req = Input(1, "snoop_req")
        self.ls_req = Input(1, "ls_req")
        self.flush = Input(1, "flush")
        self.snoop_grant = Output(1, "snoop_grant")
        self.ls_grant = Output(1, "ls_grant")
        self.busy = Output(1, "busy")

        self.init = Reg(1, "init")
        self.turn = Reg(1, "turn")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.snoop_grant <<= 0
                self.ls_grant <<= 0
                self.busy <<= 0
            with Else():
                with If((self.turn == 0)):
                    self.snoop_grant <<= self.snoop_req
                    self.ls_grant <<= self.ls_req & ~self.snoop_req
                with Else():
                    self.ls_grant <<= self.ls_req
                    self.snoop_grant <<= self.snoop_req & ~self.ls_req
                self.busy <<= (self.snoop_req == 1) | (self.ls_req == 1)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.turn <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.turn <<= 0
                with Elif((self.turn == 0)):
                    with If((self.snoop_req == 1)):
                        self.turn <<= 1
                    with Elif((self.ls_req == 1)):
                        self.turn <<= 0
                with Elif((self.ls_req == 1)):
                    self.turn <<= 0
                with Elif((self.snoop_req == 1)):
                    self.turn <<= 1


