"""
rtlgen.ram — RAM 封装器

提供单口/双口 RAM 的标准封装，生成可综合的 Verilog memory 数组。
"""
from __future__ import annotations

from rtlgen.core import Input, Memory, Module, Output, Reg
from rtlgen.logic import If


class SinglePortRAM(Module):
    """单口同步 RAM（读写共用时钟与地址）。

    读为组合逻辑（异步读），写为时序逻辑。
    """

    def __init__(self, width: int, depth: int, name: str = "SinglePortRAM", init_file: str = ""):
        super().__init__(name)
        addr_w = max(depth.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.addr = Input(addr_w, "addr")
        self.din = Input(width, "din")
        self.dout = Output(width, "dout")
        self.we = Input(1, "we")
        self.en = Input(1, "en")

        mem = self.add_memory(Memory(width=width, depth=depth, name="mem", init_file=init_file or ""))

        @self.comb
        def _read():
            self.dout <<= mem[self.addr]

        @self.seq(self.clk)
        def _write():
            with If(self.en & self.we):
                mem[self.addr] <<= self.din


class SimpleDualPortRAM(Module):
    """简单双口 RAM（一个写端口 + 一个读端口）。

    读为组合逻辑，写为时序逻辑。两个端口共享同一时钟。
    """

    def __init__(self, width: int, depth: int, name: str = "SimpleDualPortRAM", init_file: str = ""):
        super().__init__(name)
        addr_w = max(depth.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.wr_addr = Input(addr_w, "wr_addr")
        self.rd_addr = Input(addr_w, "rd_addr")
        self.din = Input(width, "din")
        self.dout = Output(width, "dout")
        self.we = Input(1, "we")
        self.wr_en = Input(1, "wr_en")
        self.rd_en = Input(1, "rd_en")

        mem = self.add_memory(Memory(width=width, depth=depth, name="mem", init_file=init_file or ""))

        @self.comb
        def _read():
            with If(self.rd_en):
                self.dout <<= mem[self.rd_addr]

        @self.seq(self.clk)
        def _write():
            with If(self.wr_en & self.we):
                mem[self.wr_addr] <<= self.din
