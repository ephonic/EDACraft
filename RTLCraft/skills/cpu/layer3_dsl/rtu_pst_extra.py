"""
L3 DSL — PSTExtra, PSTExtra.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
from rtlgen.logic import If, Else, Elif


class PSTExtra(Module):
    def __init__(self):
        super().__init__("pstextra")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.complete_fpr = Input(6, "complete_fpr")
        self.complete_fen = Input(1, "complete_fen")
        self.retire_fpr = Input(6, "retire_fpr")
        self.retire_fen = Input(1, "retire_fen")
        self.complete_vpr = Input(6, "complete_vpr")
        self.complete_ven = Input(1, "complete_ven")
        self.retire_vpr = Input(6, "retire_vpr")
        self.retire_ven = Input(1, "retire_ven")
        self.flush = Input(1, "flush")
        self.f_ready = Output(32, "f_ready")
        self.v_ready = Output(32, "v_ready")

        self.f_bitmap = Reg(32, "f_bitmap")
        self.init = Reg(1, "init")
        self.v_bitmap = Reg(32, "v_bitmap")

        @self.comb
        def _comb():
            with If((self.init == 0)):
                self.f_ready <<= 0
                self.v_ready <<= 0
            with Else():
                self.f_ready <<= self.f_bitmap
                self.v_ready <<= self.v_bitmap

        @self.seq(self.clk, self.rst_n)
        def _seq():
            with If(~self.rst_n):
                self.init <<= 0
                self.f_bitmap <<= 0
                self.v_bitmap <<= 0
            with Else():
                self.init <<= 1
                with If((self.flush == 1)):
                    self.f_bitmap <<= 0
                    self.v_bitmap <<= 0
                with Else():
                    with If((self.complete_fen == 1)):
                        self.f_bitmap <<= self.f_bitmap | 1 << self.complete_fpr
                    with If((self.retire_fen == 1)):
                        self.f_bitmap <<= self.f_bitmap & ~(1 << self.retire_fpr)
                    with If((self.complete_ven == 1)):
                        self.v_bitmap <<= self.v_bitmap | 1 << self.complete_vpr
                    with If((self.retire_ven == 1)):
                        self.v_bitmap <<= self.v_bitmap & ~(1 << self.retire_vpr)


