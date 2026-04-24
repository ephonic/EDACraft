#!/usr/bin/env python3
"""
二维 ForGen 嵌套示例：生成 4x4 矩阵的按位与门。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, VerilogEmitter
from rtlgen.logic import ForGen


class MatrixAnd(Module):
    def __init__(self, rows: int = 4, cols: int = 4):
        super().__init__("MatrixAnd")
        self.a = Input(rows * cols, "a")
        self.b = Input(rows * cols, "b")
        self.y = Output(rows * cols, "y")

        with ForGen("i", 0, rows) as i:
            with ForGen("j", 0, cols) as j:
                idx = i * cols + j
                self.y[idx] <<= self.a[idx] & self.b[idx]


if __name__ == "__main__":
    top = MatrixAnd(rows=4, cols=4)
    print(VerilogEmitter().emit(top))
