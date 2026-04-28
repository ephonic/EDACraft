#!/usr/bin/env python3
"""1-bit 全加器子模块。"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, VerilogEmitter


class FullAdder(Module):
    def __init__(self, name: str = "FullAdder"):
        super().__init__(name)
        self.a = Input(1, "a")
        self.b = Input(1, "b")
        self.cin = Input(1, "cin")
        self.sum = Output(1, "sum")
        self.cout = Output(1, "cout")

        @self.comb
        def _logic():
            self.sum <<= self.a ^ self.b ^ self.cin
            self.cout <<= (self.a & self.b) | (self.cin & (self.a ^ self.b))


if __name__ == "__main__":
    fa = FullAdder()
    emitter = VerilogEmitter()
    print(emitter.emit(fa))
