#!/usr/bin/env python3
"""
X/Z 四态仿真示例：演示未初始化寄存器为 X，复位后变 0。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, Simulator


class XZDemo(Module):
    def __init__(self):
        super().__init__("XZDemo")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.q = Output(4, "q")
        self._reg = Reg(4, "reg")

        @self.comb
        def _out():
            self.q <<= self._reg

        @self.seq(self.clk, self.rst)
        def _seq():
            from rtlgen.logic import If, Else
            with If(self.rst == 1):
                self._reg <<= 0
            with Else():
                self._reg <<= self._reg + 1


if __name__ == "__main__":
    dut = XZDemo()
    sim = Simulator(dut, trace_signals=["q"], use_xz=True)

    print("Before reset:")
    reg = sim.get("reg")
    q = sim.get("q")
    print(f"  reg = {reg}")
    print(f"  q   = {q}")

    sim.reset()
    print("After reset:")
    reg = sim.get("reg")
    q = sim.get("q")
    print(f"  reg = {reg}")
    print(f"  q   = {q}")

    for i in range(3):
        sim.step()
        q = sim.get("q")
        print(f"Cycle {i}: q = {q}")

    print("\nTrace:")
    sim.dump_trace(fmt="table")
