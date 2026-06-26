"""
L3 DSL — LSUCtrl, LSUCtrl.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class LSUCtrl(Module):
    def __init__(self):
        super().__init__("lsuctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ld_req = Input(1, "ld_req")
        self.st_req = Input(1, "st_req")
        self.ldq_full = Input(1, "ldq_full")
        self.stq_full = Input(1, "stq_full")
        self.dcache_busy = Input(1, "dcache_busy")
        self.ld_grant = Output(1, "ld_grant")
        self.st_grant = Output(1, "st_grant")
        self.stall = Output(1, "stall")

        self.init = Reg(1, "init")
        self.last = Reg(1, "last")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.ld_grant <<= 0
                self.st_grant <<= 0
                self.stall <<= 1
            with Else():
                with If((self.last == 0)):
                    self.st_grant <<= (self.st_req == 1) & (self.stq_full == 0) & (self.dcache_busy == 0)
                    self.ld_grant <<= (self.ld_req == 1) & (self.ldq_full == 0) & (self.dcache_busy == 0) & ~((self.st_req == 1) & (self.stq_full == 0) & (self.dcache_busy == 0))
                with Else():
                    self.ld_grant <<= (self.ld_req == 1) & (self.ldq_full == 0) & (self.dcache_busy == 0)
                    self.st_grant <<= (self.st_req == 1) & (self.stq_full == 0) & (self.dcache_busy == 0) & ~((self.ld_req == 1) & (self.ldq_full == 0) & (self.dcache_busy == 0))
                self.stall <<= (self.ld_req == 1) & (self.ld_grant == 0) | (self.st_req == 1) & (self.st_grant == 0)

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.last <<= 0
            with Else():
                self.init <<= 1
                with If((self.last == 0)):
                    with If(((self.st_req == 1) & (self.stq_full == 0) & (self.dcache_busy == 0)) == 1):
                        self.last <<= 1
                    with Elif(((self.ld_req == 1) & (self.ldq_full == 0) & (self.dcache_busy == 0)) == 1):
                        self.last <<= 0
                with Elif(((self.ld_req == 1) & (self.ldq_full == 0) & (self.dcache_busy == 0)) == 1):
                    self.last <<= 0
                with Elif(((self.st_req == 1) & (self.stq_full == 0) & (self.dcache_busy == 0)) == 1):
                    self.last <<= 1


