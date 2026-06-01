"""
L3 DSL — ISCtrl, ISCtrl.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class ISCtrl(Module):
    def __init__(self):
        super().__init__("isctrl")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.ready_mask = Input(4, "ready_mask")
        self.grant_any = Input(1, "grant_any")
        self.grant_idx = Output(2, "grant_idx")
        self.grant_valid = Output(1, "grant_valid")

        self.grant_idx_r = Reg(2, "grant_idx_r")
        self.grant_valid_r = Reg(1, "grant_valid_r")
        self.init = Reg(1, "init")
        self.next_grant_idx = Wire(2, "next_grant_idx")
        self.next_grant_valid = Wire(1, "next_grant_valid")
        self.pointer = Reg(2, "pointer")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.next_grant_idx <<= 0
                self.next_grant_valid <<= 0
                self.grant_idx <<= 0
                self.grant_valid <<= 0
            with Else():
                with If((self.pointer == 0)):
                    with If((self.ready_mask[0] == 1)):
                        self.next_grant_idx <<= 0
                    with Elif((self.ready_mask[1] == 1)):
                        self.next_grant_idx <<= 1
                    with Elif((self.ready_mask[2] == 1)):
                        self.next_grant_idx <<= 2
                    with Else():
                        self.next_grant_idx <<= 3
                with Elif((self.pointer == 1)):
                    with If((self.ready_mask[1] == 1)):
                        self.next_grant_idx <<= 1
                    with Elif((self.ready_mask[2] == 1)):
                        self.next_grant_idx <<= 2
                    with Elif((self.ready_mask[3] == 1)):
                        self.next_grant_idx <<= 3
                    with Else():
                        self.next_grant_idx <<= 0
                with Elif((self.pointer == 2)):
                    with If((self.ready_mask[2] == 1)):
                        self.next_grant_idx <<= 2
                    with Elif((self.ready_mask[3] == 1)):
                        self.next_grant_idx <<= 3
                    with Elif((self.ready_mask[0] == 1)):
                        self.next_grant_idx <<= 0
                    with Else():
                        self.next_grant_idx <<= 1
                with Elif((self.ready_mask[3] == 1)):
                    self.next_grant_idx <<= 3
                with Elif((self.ready_mask[0] == 1)):
                    self.next_grant_idx <<= 0
                with Elif((self.ready_mask[1] == 1)):
                    self.next_grant_idx <<= 1
                with Else():
                    self.next_grant_idx <<= 2
                self.next_grant_valid <<= (self.grant_any == 1) & ((self.ready_mask[0] == 1) | (self.ready_mask[1] == 1) | (self.ready_mask[2] == 1) | (self.ready_mask[3] == 1))
                self.grant_idx <<= self.grant_idx_r
                self.grant_valid <<= self.grant_valid_r

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.pointer <<= 0
                self.grant_idx_r <<= 0
                self.grant_valid_r <<= 0
            with Else():
                self.init <<= 1
                self.grant_idx_r <<= self.next_grant_idx
                self.grant_valid_r <<= self.next_grant_valid
                with If((self.next_grant_valid == 1) & (self.grant_any == 1) & (self.init == 1)):
                    self.pointer <<= self.pointer + 1


