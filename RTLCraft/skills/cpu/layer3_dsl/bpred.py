"""
L3 DSL — BPred, BPred.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class BPred(Module):
    def __init__(self):
        super().__init__("bpred")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.req_pc = Input(64, "req_pc")
        self.req_valid = Input(1, "req_valid")
        self.upd_pc = Input(64, "upd_pc")
        self.upd_taken = Input(1, "upd_taken")
        self.upd_target = Input(64, "upd_target")
        self.upd_valid = Input(1, "upd_valid")
        self.upd_is_call = Input(1, "upd_is_call")
        self.upd_is_return = Input(1, "upd_is_return")
        self.pred_taken = Output(1, "pred_taken")
        self.pred_target = Output(64, "pred_target")
        self.pred_valid = Output(1, "pred_valid")

        self.btb_hit = Wire(1, "btb_hit")
        self.btb_idx = Wire(10, "btb_idx")
        self.counter = Wire(2, "counter")
        self.ghr = Reg(12, "ghr")
        self.init = Reg(1, "init")
        self.pht_idx = Wire(12, "pht_idx")
        self.ras_ptr = Reg(3, "ras_ptr")
        self.ras_target = Wire(64, "ras_target")

        self.pht = Array(2, 4096, "pht")
        self.btb_valid = Array(1, 1024, "btb_valid")
        self.ras_stack = Array(64, 8, "ras_stack")
        self.btb_target = Array(64, 1024, "btb_target")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.pred_taken <<= 0
                self.pred_target <<= 0
                self.pred_valid <<= 0
            with Else():
                self.pht_idx <<= (self.req_pc[14:3] ^ self.ghr) & 4095
                self.counter <<= self.pht[self.pht_idx]
                self.btb_idx <<= self.req_pc[12:3]
                self.btb_hit <<= self.btb_valid[self.btb_idx]
                self.ras_target <<= self.ras_stack[self.ras_ptr - 1]
                self.pred_taken <<= (self.counter >= 2)
                self.pred_target <<= self.btb_target[self.btb_idx]
                self.pred_valid <<= self.btb_hit

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.ghr <<= 0
                self.ras_ptr <<= 0
            with Else():
                self.init <<= 1
                with If((1 & self.upd_taken) == 1):
                    self.ghr <<= self.ghr << 1 | 1
                with Elif((self.upd_valid == 1)):
                    self.ghr <<= self.ghr << 1
                with If((self.upd_is_call == 1)):
                    self.ras_stack[self.ras_ptr] <<= self.upd_pc + 4
                    self.ras_ptr <<= self.ras_ptr + 1
                with Elif((1 & self.ras_ptr) != 0):
                    self.ras_ptr <<= self.ras_ptr - 1


