"""
L3 DSL — AXI-Stream FIFO with almost-full threshold.

Extracted from ref_rtl/interfaces/axis/rtl/axis_fifo.v
Micro-architecture: synchronous FIFO with AXI-Stream handshake.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory
from rtlgen.logic import If, Else, Elif


class AXISFIFO(Module):
    """AXI-Stream FIFO with configurable depth and almost-full."""

    def __init__(self, width=32, depth=16, afull_thresh=None, name="axis_fifo"):
        super().__init__(name)
        if afull_thresh is None:
            afull_thresh = depth - 1
        aw = max((depth - 1).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        self.s_tdata = Input(width, "s_tdata"); self.s_tvalid = Input(1, "s_tvalid")
        self.s_tready = Output(1, "s_tready")
        self.m_tdata = Output(width, "m_tdata"); self.m_tvalid = Output(1, "m_tvalid")
        self.m_tready = Input(1, "m_tready")
        self.afull = Output(1, "afull")

        self._mem = Memory(width, depth, "axis_fifo_mem")
        self._wr = Reg(aw, "wr_ptr"); self._rd = Reg(aw, "rd_ptr")
        self._cnt = Reg(aw + 1, "cnt")

        with self.comb:
            self.s_tready <<= (self._cnt < depth)
            self.m_tvalid <<= (self._cnt > 0)
            self.m_tdata <<= self._mem[self._rd]
            self.afull <<= (self._cnt >= afull_thresh)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._wr <<= 0; self._rd <<= 0; self._cnt <<= 0
            with Else():
                push = self.s_tvalid & self.s_tready
                pop = self.m_tvalid & self.m_tready
                with If(push):
                    self._mem[self._wr] <<= self.s_tdata
                    self._wr <<= self._wr + 1
                with If(pop):
                    self._rd <<= self._rd + 1
                with If(push & (pop == 0)):
                    self._cnt <<= self._cnt + 1
                with Elif((push == 0) & pop):
                    self._cnt <<= self._cnt - 1
