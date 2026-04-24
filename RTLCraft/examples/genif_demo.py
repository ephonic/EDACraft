#!/usr/bin/env python3
"""
Generate-if 示例：使用 GenIf/GenElse 在模块顶层条件生成逻辑。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Parameter, VerilogEmitter
from rtlgen.logic import GenIf, GenElse, ForGen


class CondGen(Module):
    def __init__(self):
        super().__init__("CondGen")
        self.USE_AND = Parameter(1, "USE_AND")
        self.a = Input(4, "a")
        self.b = Input(4, "b")
        self.y = Output(4, "y")

        with GenIf(self.USE_AND == 1):
            with ForGen("i", 0, 4) as i:
                self.y[i] <<= self.a[i] & self.b[i]
        with GenElse():
            with ForGen("i", 0, 4) as i:
                self.y[i] <<= self.a[i] | self.b[i]


if __name__ == "__main__":
    top = CondGen()
    print(VerilogEmitter().emit(top))
