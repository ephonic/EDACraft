#!/usr/bin/env python3
"""简单计数器示例：演示 Module、@comb、@seq、If/Else 的使用。"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, VerilogEmitter
from rtlgen.logic import If, Else


class Counter(Module):
    def __init__(self, width: int = 8):
        super().__init__("Counter")
        self.width = width

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.count = Output(width, "count")

        self._count_reg = Reg(width, "count_reg")

        @self.comb
        def _output_logic():
            self.count <<= self._count_reg

        @self.seq(self.clk, self.rst)
        def _count_logic():
            with If(self.rst == 1):
                self._count_reg <<= 0
            with Else():
                with If(self.en == 1):
                    self._count_reg <<= self._count_reg + 1
                with Else():
                    self._count_reg <<= self._count_reg


if __name__ == "__main__":
    top = Counter(width=8)
    emitter = VerilogEmitter()
    print(emitter.emit(top))
