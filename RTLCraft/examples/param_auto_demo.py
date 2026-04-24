#!/usr/bin/env python3
"""
参数自动映射示例：子模块隐式实例化时，自动传递同名的 Parameter。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Wire, Parameter, VerilogEmitter


class ParamAdder(Module):
    """带 WIDTH 参数的可配置加法器。"""

    def __init__(self, name: str = "ParamAdder"):
        super().__init__(name)
        self.WIDTH = Parameter(8, "WIDTH")
        self.a = Input(self.WIDTH.value, "a")
        self.b = Input(self.WIDTH.value, "b")
        self.y = Output(self.WIDTH.value, "y")

        @self.comb
        def _logic():
            self.y <<= self.a + self.b


class Top(Module):
    def __init__(self):
        super().__init__("Top")
        self.WIDTH = Parameter(16, "WIDTH")
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.y = Output(16, "y")

        # 隐式实例化：自动映射 WIDTH 参数与同名端口
        self.adder = ParamAdder()


if __name__ == "__main__":
    top = Top()
    print(VerilogEmitter().emit(top))
