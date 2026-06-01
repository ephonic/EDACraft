"""
L3 DSL — AXI4 FIFO. Separate read/write channels with sync FIFOs.

Extracted from ref_rtl/interfaces/axi/rtl/axi_fifo.v
Micro-architecture: two SyncFIFOs (rd + wr) with AXI channel mapping.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory
from rtlgen.logic import If, Else, Elif


class AXI4FIFO(Module):
    """AXI4 FIFO: write FIFO (AW+W+B) and read FIFO (AR+R)."""

    def __init__(self, data_width=32, addr_width=32, id_width=8, depth=16,
                 name="axi_fifo"):
        super().__init__(name)
        DW = data_width; AW = addr_width; IW = id_width
        aw = max((depth - 1).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        # Slave (input) ports
        self.s_awvalid = Input(1, "s_awvalid"); self.s_awready = Output(1, "s_awready")
        self.s_awaddr = Input(AW, "s_awaddr"); self.s_awid = Input(IW, "s_awid")
        self.s_wvalid = Input(1, "s_wvalid"); self.s_wready = Output(1, "s_wready")
        self.s_wdata = Input(DW, "s_wdata"); self.s_wlast = Input(1, "s_wlast")
        self.s_bvalid = Output(1, "s_bvalid"); self.s_bready = Input(1, "s_bready")
        self.s_bid = Output(IW, "s_bid"); self.s_bresp = Output(2, "s_bresp")
        self.s_arvalid = Input(1, "s_arvalid"); self.s_arready = Output(1, "s_arready")
        self.s_araddr = Input(AW, "s_araddr"); self.s_arid = Input(IW, "s_arid")
        self.s_rvalid = Output(1, "s_rvalid"); self.s_rready = Input(1, "s_rready")
        self.s_rdata = Output(DW, "s_rdata"); self.s_rid = Output(IW, "s_rid")
        self.s_rlast = Output(1, "s_rlast")

        # Master (output) ports
        self.m_awvalid = Output(1, "m_awvalid"); self.m_awready = Input(1, "m_awready")
        self.m_awaddr = Output(AW, "m_awaddr"); self.m_awid = Output(IW, "m_awid")
        self.m_wvalid = Output(1, "m_wvalid"); self.m_wready = Input(1, "m_wready")
        self.m_wdata = Output(DW, "m_wdata"); self.m_wlast = Output(1, "m_wlast")
        self.m_bvalid = Input(1, "m_bvalid"); self.m_bready = Output(1, "m_bready")
        self.m_bid = Input(IW, "m_bid"); self.m_bresp = Input(2, "m_bresp")
        self.m_arvalid = Output(1, "m_arvalid"); self.m_arready = Input(1, "m_arready")
        self.m_araddr = Output(AW, "m_araddr"); self.m_arid = Output(IW, "m_arid")
        self.m_rvalid = Input(1, "m_rvalid"); self.m_rready = Output(1, "m_rready")
        self.m_rdata = Input(DW, "m_rdata"); self.m_rid = Input(IW, "m_rid")
        self.m_rlast = Input(1, "m_rlast")

        # Write address FIFO (AW channel)
        self._aw_mem = Memory(AW + IW, depth, "aw_fifo")
        self._aw_wr = Reg(aw, "aw_wr"); self._aw_rd = Reg(aw, "aw_rd")
        self._aw_cnt = Reg(aw + 1, "aw_cnt")

        # Write data FIFO (W channel)
        self._w_mem = Memory(DW + 1, depth, "w_fifo")
        self._w_wr = Reg(aw, "w_wr"); self._w_rd = Reg(aw, "w_rd")
        self._w_cnt = Reg(aw + 1, "w_cnt")

        # Write response FIFO (B channel)
        self._b_mem = Memory(IW + 2, depth, "b_fifo")
        self._b_wr = Reg(aw, "b_wr"); self._b_rd = Reg(aw, "b_rd")
        self._b_cnt = Reg(aw + 1, "b_cnt")

        # Read address FIFO (AR channel)
        self._ar_mem = Memory(AW + IW, depth, "ar_fifo")
        self._ar_wr = Reg(aw, "ar_wr"); self._ar_rd = Reg(aw, "ar_rd")
        self._ar_cnt = Reg(aw + 1, "ar_cnt")

        # Read data FIFO (R channel)
        self._r_mem = Memory(DW + IW + 1, depth, "r_fifo")
        self._r_wr = Reg(aw, "r_wr"); self._r_rd = Reg(aw, "r_rd")
        self._r_cnt = Reg(aw + 1, "r_cnt")

        def _fifo_common(mem, wr_ptr, rd_ptr, cnt, s_vld, s_rdy,
                         m_vld, m_rdy, s_data, m_data, width, depth):
            """Common FIFO push/pop logic."""
            with self.comb:
                s_rdy <<= (cnt < depth)
                m_vld <<= (cnt > 0)
                m_data <<= mem[rd_ptr]
            with self.seq(self.clk, self.rst):
                with If(self.rst == 1):
                    wr_ptr <<= 0; rd_ptr <<= 0; cnt <<= 0
                with Else():
                    push = s_vld & s_rdy
                    pop = m_vld & m_rdy
                    with If(push):
                        mem[wr_ptr] <<= s_data; wr_ptr <<= wr_ptr + 1
                    with If(pop):
                        rd_ptr <<= rd_ptr + 1
                    with If(push & ~pop):
                        cnt <<= cnt + 1
                    with Elif(~push & pop):
                        cnt <<= cnt - 1

        _fifo_common(self._aw_mem, self._aw_wr, self._aw_rd, self._aw_cnt,
                     self.s_awvalid, self.s_awready,
                     self.m_awvalid, self.m_awready,
                     self.s_awaddr, self.m_awaddr, AW, depth)
        _fifo_common(self._w_mem, self._w_wr, self._w_rd, self._w_cnt,
                     self.s_wvalid, self.s_wready,
                     self.m_wvalid, self.m_wready,
                     self.s_wdata, self.m_wdata, DW, depth)
        _fifo_common(self._b_mem, self._b_wr, self._b_rd, self._b_cnt,
                     self.m_bvalid, self.m_bready,
                     self.s_bvalid, self.s_bready,
                     self.m_bresp, self.s_bresp, 2, depth)
        _fifo_common(self._ar_mem, self._ar_wr, self._ar_rd, self._ar_cnt,
                     self.s_arvalid, self.s_arready,
                     self.m_arvalid, self.m_arready,
                     self.s_araddr, self.m_araddr, AW, depth)
        _fifo_common(self._r_mem, self._r_wr, self._r_rd, self._r_cnt,
                     self.m_rvalid, self.m_rready,
                     self.s_rvalid, self.s_rready,
                     self.m_rdata, self.s_rdata, DW, depth)
