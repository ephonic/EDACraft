"""
L3 DSL — AXI-Stream Async FIFO (CDC FIFO for AXI-Stream).

Extracted from ref_rtl/interfaces/axis/rtl/axis_async_fifo.v
Micro-architecture: dual-clock FIFO with Gray-code pointers, AXI-Stream wrapper.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory
from rtlgen.logic import If, Else


class AXISAsyncFIFO(Module):
    """AXI-Stream async FIFO for clock domain crossing."""

    def __init__(self, width=32, depth=8, name="axis_async_fifo"):
        super().__init__(name)
        aw = max((depth - 1).bit_length(), 1)
        self.s_clk = Input(1, "s_clk"); self.s_rst = Input(1, "s_rst")
        self.m_clk = Input(1, "m_clk"); self.m_rst = Input(1, "m_rst")

        self.s_tdata = Input(width, "s_tdata"); self.s_tvalid = Input(1, "s_tvalid")
        self.s_tready = Output(1, "s_tready")
        self.m_tdata = Output(width, "m_tdata"); self.m_tvalid = Output(1, "m_tvalid")
        self.m_tready = Input(1, "m_tready")

        self._mem = Memory(width, depth, "async_fifo_mem")

        # Write domain
        self._wr_ptr = Reg(aw + 1, "wr_ptr"); self._wr_gray = Reg(aw + 1, "wr_gray")
        self._rd_sync = [Reg(aw + 1, f"rd_sync_{i}") for i in range(2)]

        # Read domain
        self._rd_ptr = Reg(aw + 1, "rd_ptr"); self._rd_gray = Reg(aw + 1, "rd_gray")
        self._wr_sync = [Reg(aw + 1, f"wr_sync_{i}") for i in range(2)]

        wr_next = Wire(aw + 1, "wr_nxt"); rd_next = Wire(aw + 1, "rd_nxt")
        with self.comb:
            wr_next <<= self._wr_ptr + 1
            rd_next <<= self._rd_ptr + 1
            self.s_tready <<= (wr_next[aw:0] != self._rd_sync[1][aw:0]) | \
                             (wr_next[aw] == self._rd_sync[1][aw])
            self.m_tvalid <<= (self._rd_ptr[aw:0] != self._wr_sync[1][aw:0]) | \
                             (self._rd_ptr[aw] != self._wr_sync[1][aw])
            self.m_tdata <<= self._mem[self._rd_ptr[aw - 1:0]]

        # Write clock domain
        with self.seq(self.s_clk, self.s_rst):
            with If(self.s_rst == 1):
                self._wr_ptr <<= 0; self._wr_gray <<= 0
                for i in range(2): self._rd_sync[i] <<= 0
            with Else():
                self._rd_sync[0] <<= self._rd_gray
                self._rd_sync[1] <<= self._rd_sync[0]
                push = self.s_tvalid & self.s_tready
                with If(push):
                    self._mem[self._wr_ptr[aw - 1:0]] <<= self.s_tdata
                    self._wr_ptr <<= wr_next
                    self._wr_gray <<= wr_next ^ (wr_next >> 1)

        # Read clock domain
        with self.seq(self.m_clk, self.m_rst):
            with If(self.m_rst == 1):
                self._rd_ptr <<= 0; self._rd_gray <<= 0
                for i in range(2): self._wr_sync[i] <<= 0
            with Else():
                self._wr_sync[0] <<= self._wr_gray
                self._wr_sync[1] <<= self._wr_sync[0]
                pop = self.m_tvalid & self.m_tready
                with If(pop):
                    self._rd_ptr <<= rd_next
                    self._rd_gray <<= rd_next ^ (rd_next >> 1)
