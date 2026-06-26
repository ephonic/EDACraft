"""
L3 DSL — IndirectBranchBTB, IndirectBranchBTB.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class IndirectBranchBTB(Module):
    def __init__(self):
        super().__init__("indirectbranchbtb")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_pc = Input(39, "req_pc")
        self.req_valid = Input(1, "req_valid")
        self.upd_pc = Input(39, "upd_pc")
        self.upd_target = Input(39, "upd_target")
        self.upd_valid = Input(1, "upd_valid")
        self.pred_target = Output(39, "pred_target")
        self.pred_valid = Output(1, "pred_valid")

        self.hit = Wire(1, "hit")
        self.init = Reg(1, "init")
        self.rd_idx = Wire(3, "rd_idx")
        self.rd_tag = Wire(16, "rd_tag")

        self.ind_btb_tag = Array(16, 8, "ind_btb_tag")
        self.ind_btb_vld = Array(1, 8, "ind_btb_vld")
        self.ind_btb_tgt = Array(39, 8, "ind_btb_tgt")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pred_target <<= 0
                self.pred_valid <<= 0
            with Else():
                self.rd_idx <<= self.req_pc[4:2]
                self.rd_tag <<= self.ind_btb_tag[self.rd_idx]
                self.hit <<= self.ind_btb_vld[self.rd_idx] & (self.rd_tag == self.req_pc) >> 5
                self.pred_target <<= self.ind_btb_tgt[self.rd_idx]
                self.pred_valid <<= self.hit & self.req_valid

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.ind_btb_vld[0] <<= 0
                self.ind_btb_vld[1] <<= 0
                self.ind_btb_vld[2] <<= 0
                self.ind_btb_vld[3] <<= 0
                self.ind_btb_vld[4] <<= 0
                self.ind_btb_vld[5] <<= 0
                self.ind_btb_vld[6] <<= 0
                self.ind_btb_vld[7] <<= 0
            with Else():
                self.init <<= 1
                with If((self.upd_valid == 1)):
                    self.ind_btb_tag[self.upd_pc[4:2]] <<= self.upd_pc >> 5
                    self.ind_btb_tgt[self.upd_pc[4:2]] <<= self.upd_target
                    self.ind_btb_vld[self.upd_pc[4:2]] <<= 1


