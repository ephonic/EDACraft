#!/usr/bin/env python3
"""子模块例化示例：演示显式与隐式两种例化方式。"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Wire, VerilogEmitter


class AndGate(Module):
    def __init__(self, name: str = "AndGate"):
        super().__init__(name)
        self.a = Input(1, "a")
        self.b = Input(1, "b")
        self.y = Output(1, "y")

        @self.comb
        def _logic():
            self.y <<= self.a & self.b


class XorGate(Module):
    def __init__(self, name: str = "XorGate"):
        super().__init__(name)
        self.a = Input(1, "a")
        self.b = Input(1, "b")
        self.y = Output(1, "y")

        @self.comb
        def _logic():
            self.y <<= self.a ^ self.b


class HalfAdder(Module):
    """半加器：通过显式例化子模块实现。"""

    def __init__(self):
        super().__init__("HalfAdder")
        self.a = Input(1, "a")
        self.b = Input(1, "b")
        self.sum_ = Output(1, "sum")
        self.cout = Output(1, "cout")

        # 显式例化 AndGate -> cout
        and_gate = AndGate()
        self.instantiate(
            and_gate,
            name="u_and",
            port_map={
                "a": self.a,
                "b": self.b,
                "y": self.cout,
            },
        )

        # 显式例化 XorGate -> sum_
        xor_gate = XorGate()
        self.instantiate(
            xor_gate,
            name="u_xor",
            port_map={
                "a": self.a,
                "b": self.b,
                "y": self.sum_,
            },
        )


if __name__ == "__main__":
    top = HalfAdder()
    emitter = VerilogEmitter()
    print(emitter.emit(top))
