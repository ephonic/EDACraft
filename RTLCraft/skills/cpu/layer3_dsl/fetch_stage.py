"""
L3 DSL — FetchStage, FetchStage.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class FetchStage(Module):
    def __init__(self):
        super().__init__("fetchstage")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.stall = Input(1, "stall")
        self.redirect = Input(1, "redirect")
        self.redirect_pc = Input(39, "redirect_pc")
        self.instr = Output(32, "instr")
        self.instr_valid = Output(1, "instr_valid")

        self.init = Reg(1, "init")
        self.u_ibuf_pop_ready = Wire(1, "u_ibuf_pop_ready")
        self.u_ibuf_push_data = Wire(32, "u_ibuf_push_data")
        self.u_ibuf_push_valid = Wire(1, "u_ibuf_push_valid")
        self.u_pcgen_rpc = Wire(351, "u_pcgen_rpc")
        self.u_pcgen_rv = Wire(9, "u_pcgen_rv")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.instr <<= 0
                self.instr_valid <<= 0
                self.u_pcgen_rv <<= 0
                self.u_pcgen_rpc <<= 0
                self.u_pcgen_stall <<= 0
                self.u_ibuf_push_valid <<= 0
                self.u_ibuf_push_data <<= 0
                self.u_ibuf_pop_ready <<= 0
            with Else():
                self.u_pcgen_rv <<= 0
                self.u_pcgen_rpc <<= 0
                self.u_pcgen_stall <<= self.stall
                self.u_ibuf_push_valid <<= 1
                self.u_ibuf_push_data <<= 19
                self.u_ibuf_pop_ready <<= ~self.stall
                self.instr <<= self.u_ibuf_data
                self.instr_valid <<= self.u_ibuf_valid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
            with Else():
                self.init <<= 1


