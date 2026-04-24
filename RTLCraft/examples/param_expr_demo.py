#!/usr/bin/env python3
"""
复杂参数表达式自动映射示例：
子模块隐式实例化时传递派生参数表达式（如 WIDTH + 4）。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Parameter, VerilogEmitter


class ParamAdder(Module):
    def __init__(self, **kwargs):
        super().__init__("ParamAdder", **kwargs)
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
        self.a = Input(20, "a")
        self.b = Input(20, "b")
        self.y = Output(20, "y")

        # 隐式实例化，但传递派生参数表达式
        self.adder = ParamAdder(param_bindings={"WIDTH": self.WIDTH + 4})


if __name__ == "__main__":
    top = Top()
    print(VerilogEmitter().emit(top))
