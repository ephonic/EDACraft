"""
L3 DSL — MCIC, MCIC.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class MCIC(Module):
    def __init__(self):
        super().__init__("mcic")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ldq_nonempty = Input(1, "ldq_nonempty")
        self.stq_nonempty = Input(1, "stq_nonempty")
        self.lfb_nonempty = Input(1, "lfb_nonempty")
        self.amo_active = Input(1, "amo_active")
        self.flush = Input(1, "flush")
        self.ld_ordered = Output(1, "ld_ordered")
        self.st_ordered = Output(1, "st_ordered")
        self.pipeline_stall = Output(1, "pipeline_stall")
        self.fence_done = Output(1, "fence_done")

        self.init = Reg(1, "init")
        self.state = Reg(3, "state")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.ld_ordered <<= 0
                self.st_ordered <<= 0
                self.pipeline_stall <<= 1
                self.fence_done <<= 0
            with Else():
                self.fence_done <<= (self.state == 4)
                self.pipeline_stall <<= (self.state != 0) & (self.state != 4)
                self.ld_ordered <<= (self.state == 2) & (self.ldq_nonempty == 0) & (self.lfb_nonempty == 0)
                self.st_ordered <<= (self.state == 1) & (self.stq_nonempty == 0) & (self.amo_active == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.state <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.state <<= 0
                with Elif((self.state == 0)):
                    with If((self.amo_active == 1)):
                        self.state <<= 1
                with Elif((self.state == 1)):
                    with If((self.stq_nonempty == 0) & (self.amo_active == 0)):
                        self.state <<= 2
                with Elif((self.state == 2)):
                    with If((self.ldq_nonempty == 0) & (self.lfb_nonempty == 0)):
                        self.state <<= 3
                with Elif((self.state == 3)):
                    self.state <<= 4
                with Elif((self.state == 4)):
                    self.state <<= 0


