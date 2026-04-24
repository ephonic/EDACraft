#!/usr/bin/env python3
"""generate-for 例化示例：用 ForGen 生成 4-bit 行波进位加法器（Ripple Carry Adder）。

关键概念：
- ForGen 体内的 Python 代码只执行一次，生成 AST 节点。
- Verilog 后端会将 ForGen 体展开成 `generate for` 块。
- 因此子模块的实例名应为固定字符串（如 "fa"），不要尝试用 Python f-string 拼接 genvar。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Wire, VerilogEmitter
from rtlgen.logic import ForGen

from full_adder import FullAdder


class RippleAdder(Module):
    def __init__(self, width: int = 4):
        super().__init__("RippleAdder")
        self.a = Input(width, "a")
        self.b = Input(width, "b")
        self.cin = Input(1, "cin")
        self.sum = Output(width, "sum")
        self.cout = Output(1, "cout")

        # 内部进位链：carry[0] = cin, carry[width] = cout
        self.carry = Wire(width + 1, "carry")

        @self.comb
        def _conn():
            self.carry[0] <<= self.cin
            self.cout <<= self.carry[width]

        # 使用 generate-for 循环实例化 width 个 FullAdder
        with ForGen("i", 0, width) as i:
            # 实例名固定为 "fa"，Verilog 展开时会自动处理索引
            fa = FullAdder(name="FullAdder")
            self.instantiate(
                fa,
                name="fa",
                port_map={
                    "a": self.a[i],
                    "b": self.b[i],
                    "cin": self.carry[i],
                    "sum": self.sum[i],
                    "cout": self.carry[i + 1],
                },
            )


if __name__ == "__main__":
    top = RippleAdder(width=4)
    emitter = VerilogEmitter()
    print("// ===== FullAdder 定义 =====")
    print(emitter.emit(FullAdder()))
    print()
    print("// ===== RippleAdder 顶层（generate-for 例化） =====")
    print(emitter.emit(top))
