#!/usr/bin/env python3
"""generate-for 示例：演示 ForGen 生成多位宽按位与门。

注意：ForGen 生成 Verilog 的 genvar + for 结构，建议在模块顶层使用，
      以保证生成合法的 `assign` 或模块实例化代码。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, VerilogEmitter
from rtlgen.logic import ForGen


class BitwiseAnd(Module):
    def __init__(self, width: int = 8):
        super().__init__("BitwiseAnd")
        self.a = Input(width, "a")
        self.b = Input(width, "b")
        self.y = Output(width, "y")

        # ForGen 在模块顶层使用，生成 generate-for 块
        with ForGen("i", 0, width) as i:
            self.y[i] <<= self.a[i] & self.b[i]


if __name__ == "__main__":
    top = BitwiseAnd(width=8)
    emitter = VerilogEmitter()
    print(emitter.emit(top))
