"""
L3 DSL — TageTable, StatisticalCorrector, TageSC.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array
from rtlgen.logic import If, Else, Elif


class TageTable(Module):
    def __init__(self):
        super().__init__("tagetable")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.wr_en = Input(1, "wr_en"); self.wr_idx = Input(9, "wr_idx")
        self.wr_tag = Input(10, "wr_tag"); self.wr_ctr = Input(3, "wr_ctr")
        self.wr_ubit = Input(1, "wr_ubit")
        self.rd0_idx = Input(9, "rd0_idx"); self.rd1_idx = Input(9, "rd1_idx")
        self.rd0_ctr = Output(3, "rd0_ctr"); self.rd1_ctr = Output(3, "rd1_ctr")
        self.rd0_tag = Output(10, "rd0_tag"); self.rd1_tag = Output(10, "rd1_tag")
        self.rd0_ubit = Output(1, "rd0_ubit"); self.rd1_ubit = Output(1, "rd1_ubit")
        self.init = Reg(1, "init")
        self.ctr = Array(3, 512, "ctr"); self.tag = Array(10, 512, "tag")
        self.ubit = Array(1, 512, "ubit")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.rd0_ctr <<= 0; self.rd1_ctr <<= 0
                self.rd0_tag <<= 0; self.rd1_tag <<= 0
                self.rd0_ubit <<= 0; self.rd1_ubit <<= 0
            with Else():
                self.rd0_ctr <<= self.ctr[self.rd0_idx]
                self.rd1_ctr <<= self.ctr[self.rd1_idx]
                self.rd0_tag <<= self.tag[self.rd0_idx]
                self.rd1_tag <<= self.tag[self.rd1_idx]
                self.rd0_ubit <<= self.ubit[self.rd0_idx]
                self.rd1_ubit <<= self.ubit[self.rd1_idx]

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                for i in range(512): self.ctr[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.wr_en == 1):
                    self.ctr[self.wr_idx] <<= self.wr_ctr
                    self.tag[self.wr_idx] <<= self.wr_tag
                    self.ubit[self.wr_idx] <<= self.wr_ubit


class StatisticalCorrector(Module):
    def __init__(self):
        super().__init__("statcorr")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.wr_en = Input(1, "wr_en"); self.wr_idx = Input(9, "wr_idx")
        self.wr_ctr = Input(4, "wr_ctr")
        self.rd0_idx = Input(9, "rd0_idx"); self.rd1_idx = Input(9, "rd1_idx")
        self.rd0_ctr = Output(4, "rd0_ctr"); self.rd1_ctr = Output(4, "rd1_ctr")
        self.init = Reg(1, "init")
        self.ctr = Array(4, 512, "ctr")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.rd0_ctr <<= 0; self.rd1_ctr <<= 0
            with Else():
                self.rd0_ctr <<= self.ctr[self.rd0_idx]
                self.rd1_ctr <<= self.ctr[self.rd1_idx]

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0
                for i in range(512): self.ctr[i] <<= 0
            with Else():
                self.init <<= 1
                with If(self.wr_en == 1):
                    self.ctr[self.wr_idx] <<= self.wr_ctr


class TageSC(Module):
    def __init__(self):
        super().__init__("tagesc")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.req_pc = Input(64, "req_pc"); self.req_valid = Input(1, "req_valid")
        self.global_hist_in = Input(64, "global_hist_in")
        self.upd_valid = Input(1, "upd_valid")
        self.pred_taken = Output(1, "pred_taken")
        self.pred_target = Output(64, "pred_target")
        self.pred_valid = Output(1, "pred_valid")
        self.init = Reg(1, "init"); self.ghr = Reg(64, "ghr")

        @self.comb
        def _comb():
            with If(self.init == 0):
                self.pred_taken <<= 0; self.pred_target <<= 0; self.pred_valid <<= 0
            with Else():
                self.pred_taken <<= 0; self.pred_target <<= 0
                self.pred_valid <<= self.req_valid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(self.rst_n == 0):
                self.init <<= 0; self.ghr <<= 0
            with Else():
                self.init <<= 1
                with If(self.upd_valid == 1):
                    self.ghr <<= (self.ghr << 1) | 1
