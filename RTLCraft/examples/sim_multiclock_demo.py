#!/usr/bin/env python3
"""
多时钟域仿真示例：演示两个不同时钟域的独立推进。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, Simulator


class DualClock(Module):
    def __init__(self):
        super().__init__("DualClock")
        self.clk_a = Input(1, "clk_a")
        self.clk_b = Input(1, "clk_b")
        self.rst = Input(1, "rst")
        self.en_a = Input(1, "en_a")
        self.en_b = Input(1, "en_b")
        self.count_a = Output(4, "count_a")
        self.count_b = Output(4, "count_b")

        self._cnt_a = Reg(4, "cnt_a")
        self._cnt_b = Reg(4, "cnt_b")

        @self.comb
        def _out():
            self.count_a <<= self._cnt_a
            self.count_b <<= self._cnt_b

        @self.seq(self.clk_a, self.rst)
        def _seq_a():
            self._cnt_a <<= self._cnt_a + self.en_a

        @self.seq(self.clk_b, self.rst)
        def _seq_b():
            self._cnt_b <<= self._cnt_b + self.en_b


if __name__ == "__main__":
    dut = DualClock()
    sim = Simulator(dut, trace_signals=["count_a", "count_b"])

    sim.reset()
    sim.set("en_a", 1)
    sim.set("en_b", 1)

    print("Dual-clock simulation:")
    for i in range(5):
        sim.step(clk="clk_a")
        a = sim.get_int("count_a")
        b = sim.get_int("count_b")
        print(f"  Step clk_a -> count_a={a}, count_b={b}")
        sim.step(clk="clk_b")
        a = sim.get_int("count_a")
        b = sim.get_int("count_b")
        print(f"  Step clk_b -> count_a={a}, count_b={b}")

    print("\nTrace:")
    sim.dump_trace(fmt="table")
