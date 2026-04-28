#!/usr/bin/env python3
"""
AST 仿真器示例：对 Counter 模块进行纯 Python 仿真。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Simulator
from counter import Counter


if __name__ == "__main__":
    dut = Counter(width=4)
    sim = Simulator(dut)

    # 复位
    sim.reset()
    print("After reset, count =", sim.get("count"))

    # 使能计数
    sim.set("en", 1)
    for i in range(10):
        sim.step()
        print(f"Cycle {i:2d}: count = {sim.get('count')}")
