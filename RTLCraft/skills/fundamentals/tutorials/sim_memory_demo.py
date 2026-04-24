#!/usr/bin/env python3
"""
AST 仿真器 + Memory 示例：演示单口 RAM 的读写仿真与 trace 输出。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, VerilogEmitter, Simulator
from rtlgen.logic import If, Else


class SimpleRAM(Module):
    """简单的单口 RAM（仿真器可执行）。"""

    def __init__(self, width: int = 8, depth: int = 16):
        super().__init__("SimpleRAM")
        addr_w = max(depth.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.addr = Input(addr_w, "addr")
        self.din = Input(width, "din")
        self.we = Input(1, "we")
        self.dout = Output(width, "dout")

        # 使用 Memory 对象
        from rtlgen.core import Memory
        self._mem = Memory(width=width, depth=depth, name="ram_mem")
        self.add_memory(self._mem, "ram_mem")

        @self.comb
        def _read():
            self.dout <<= self._mem[self.addr]

        @self.seq(self.clk, self.rst)
        def _write():
            with If(self.we):
                self._mem[self.addr] <<= self.din


if __name__ == "__main__":
    ram = SimpleRAM(width=8, depth=16)

    # 打印 Verilog
    print(VerilogEmitter().emit(ram))
    print()

    # 仿真
    sim = Simulator(ram, trace_signals=["addr", "din", "we", "dout"])
    sim.reset()

    # 写入一些数据
    writes = [(0, 0xAB), (1, 0xCD), (2, 0xEF), (3, 0x12)]
    for addr, data in writes:
        sim.set("addr", addr)
        sim.set("din", data)
        sim.set("we", 1)
        sim.step()

    # 读出数据
    sim.set("we", 0)
    for addr in range(4):
        sim.set("addr", addr)
        sim.step()
        print(f"Read addr={addr}: dout={sim.get('dout'):02x}")

    print("\n=== Trace Table ===")
    sim.dump_trace(fmt="table")
