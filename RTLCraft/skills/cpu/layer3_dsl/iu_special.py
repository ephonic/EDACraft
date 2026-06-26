"""
L3 DSL — SpecialUnit, SpecialUnit.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class SpecialUnit(Module):
    def __init__(self):
        super().__init__("specialunit")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.enqueue = Input(1, "enqueue")
        self.csr_addr = Input(12, "csr_addr")
        self.csr_wdata = Input(64, "csr_wdata")
        self.csr_op = Input(2, "csr_op")
        self.csr_rdata = Output(64, "csr_rdata")
        self.valid = Output(1, "valid")
        self.busy = Output(1, "busy")

        self.init = Reg(1, "init")
        self.mcycle = Reg(64, "mcycle")
        self.minstret = Reg(64, "minstret")
        self.rdata_r = Reg(64, "rdata_r")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.csr_rdata <<= 0
                self.valid <<= 0
                self.busy <<= 0
            with Else():
                self.csr_rdata <<= self.rdata_r
                self.busy <<= 0

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.mcycle <<= 0
                self.minstret <<= 0
                self.rdata_r <<= 0
                self.valid <<= 0
            with Else():
                self.init <<= 1
                self.valid <<= 0
                self.mcycle <<= self.mcycle + 1
                with If((self.enqueue == 1)):
                    self.rdata_r <<= 0
                    with If((self.csr_addr == 2816)):
                        with If((self.csr_op == 0)):
                            self.rdata_r <<= self.mcycle
                        with Elif((self.csr_op == 1)):
                            self.mcycle <<= self.csr_wdata
                        with Elif((self.csr_op == 2)):
                            self.mcycle <<= self.mcycle | self.csr_wdata
                        with Elif((self.csr_op == 3)):
                            self.mcycle <<= self.mcycle & ~self.csr_wdata
                    with Elif((self.csr_addr == 2818)):
                        with If((self.csr_op == 0)):
                            self.rdata_r <<= self.minstret
                        with Elif((self.csr_op == 1)):
                            self.minstret <<= self.csr_wdata
                        with Elif((self.csr_op == 2)):
                            self.minstret <<= self.minstret | self.csr_wdata
                        with Elif((self.csr_op == 3)):
                            self.minstret <<= self.minstret & ~self.csr_wdata
                    with Else():
                        self.rdata_r <<= 0
                    self.valid <<= 1


