#!/usr/bin/env python3
"""
ForGen 在 always 块内使用示例。
演示 @comb 与 @seq 中均可使用 ForGen，生成 for (integer i = ...) 语句。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, VerilogEmitter
from rtlgen.logic import ForGen


class ShiftReg(Module):
    def __init__(self, width: int = 4):
        super().__init__("ShiftReg")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.din = Input(width, "din")
        self.dout = Output(width, "dout")

        self.q = Reg(width, "q")

        @self.comb
        def _comb():
            # 组合逻辑中的 ForGen
            with ForGen("i", 0, width) as i:
                self.dout[i] <<= self.q[i]

        @self.seq(self.clk, self.rst)
        def _seq():
            # 时序逻辑中的 ForGen
            with ForGen("i", 0, width) as i:
                self.q[i] <<= self.din[i]


if __name__ == "__main__":
    top = ShiftReg(width=4)
    print(VerilogEmitter().emit(top))
