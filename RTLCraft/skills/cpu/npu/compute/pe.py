"""
NeuralAccel Processing Element (PE)

A single MAC unit for the systolic array.
- Weight-stationary: weight is loaded once and held in a register
- Activation flows left-to-right (registered)
- Partial sum flows top-to-bottom (registered, accumulated)

On each compute cycle:
  a_reg   <= a_in
  psum_reg <= a_reg * weight_reg + psum_in

Ports:
  - load_en, weight_in  : weight loading interface
  - a_in, psum_in, valid: compute inputs
  - a_out, psum_out     : compute outputs (registered)
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg
from rtlgen.logic import If, Else


class ProcessingElement(Module):
    """Single MAC processing element for systolic array."""

    def __init__(self, data_width: int = 16, acc_width: int = 32, name: str = "PE"):
        super().__init__(name)
        self.data_width = data_width
        self.acc_width = acc_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Weight loading
        self.load_en = Input(1, "load_en")
        self.weight_in = Input(data_width, "weight_in")

        # Compute inputs
        self.a_in = Input(data_width, "a_in")
        self.psum_in = Input(acc_width, "psum_in")
        self.valid = Input(1, "valid")

        # Compute outputs
        self.a_out = Output(data_width, "a_out")
        self.psum_out = Output(acc_width, "psum_out")

        # Internal state
        self.weight_reg = Reg(data_width, "weight_reg")
        self.a_reg = Reg(data_width, "a_reg")
        self.psum_reg = Reg(acc_width, "psum_reg")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.weight_reg <<= 0
                self.a_reg <<= 0
                self.psum_reg <<= 0
            with Else():
                # Weight loading takes priority
                with If(self.load_en):
                    self.weight_reg <<= self.weight_in

                # Compute pipeline
                with If(self.valid):
                    self.a_reg <<= self.a_in
                    self.psum_reg <<= (self.a_reg * self.weight_reg) + self.psum_in

        # Outputs are registered values from previous cycle
        self.a_out <<= self.a_reg
        self.psum_out <<= self.psum_reg
