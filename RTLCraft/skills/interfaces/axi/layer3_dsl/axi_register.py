"""
L3 DSL — AXI4 Register (pipeline register for all 5 channels).

Extracted from ref_rtl/interfaces/axi/rtl/axi_register.v
Micro-architecture: configurable buffer type per channel.
  REG_TYPE=0: bypass, REG_TYPE=1: simple buffer, REG_TYPE=2: skid buffer
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif


class AXI4Register(Module):
    """AXI4 pipeline register with per-channel buffer type."""

    def __init__(self, data_width=32, addr_width=32, id_width=8,
                 aw_reg=1, w_reg=2, b_reg=1, ar_reg=1, r_reg=2,
                 name="axi_register"):
        super().__init__(name)
        DW = data_width; AW = addr_width; IW = id_width
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        # -- AW channel --
        self.s_awvalid = Input(1, "s_awvalid"); self.s_awready = Output(1, "s_awready")
        self.s_awaddr = Input(AW, "s_awaddr"); self.s_awid = Input(IW, "s_awid")
        self.m_awvalid = Output(1, "m_awvalid"); self.m_awready = Input(1, "m_awready")
        self.m_awaddr = Output(AW, "m_awaddr"); self.m_awid = Output(IW, "m_awid")

        # -- W channel --
        self.s_wvalid = Input(1, "s_wvalid"); self.s_wready = Output(1, "s_wready")
        self.s_wdata = Input(DW, "s_wdata"); self.s_wlast = Input(1, "s_wlast")
        self.m_wvalid = Output(1, "m_wvalid"); self.m_wready = Input(1, "m_wready")
        self.m_wdata = Output(DW, "m_wdata"); self.m_wlast = Output(1, "m_wlast")

        # -- B channel --
        self.s_bvalid = Input(1, "s_bvalid"); self.s_bready = Output(1, "s_bready")
        self.s_bid = Input(IW, "s_bid"); self.s_bresp = Input(2, "s_bresp")
        self.m_bvalid = Output(1, "m_bvalid"); self.m_bready = Input(1, "m_bready")
        self.m_bid = Output(IW, "m_bid"); self.m_bresp = Output(2, "m_bresp")

        # -- AR channel --
        self.s_arvalid = Input(1, "s_arvalid"); self.s_arready = Output(1, "s_arready")
        self.s_araddr = Input(AW, "s_araddr"); self.s_arid = Input(IW, "s_arid")
        self.m_arvalid = Output(1, "m_arvalid"); self.m_arready = Input(1, "m_arready")
        self.m_araddr = Output(AW, "m_araddr"); self.m_arid = Output(IW, "m_arid")

        # -- R channel --
        self.s_rvalid = Input(1, "s_rvalid"); self.s_rready = Output(1, "s_rready")
        self.s_rdata = Input(DW, "s_rdata"); self.s_rid = Input(IW, "s_rid")
        self.s_rlast = Input(1, "s_rlast")
        self.m_rvalid = Output(1, "m_rvalid"); self.m_rready = Input(1, "m_rready")
        self.m_rdata = Output(DW, "m_rdata"); self.m_rid = Output(IW, "m_rid")
        self.m_rlast = Output(1, "m_rlast")

        def _skid_buffer(in_vld, in_rdy, in_dat, out_vld, out_rdy, out_dat, width):
            """Internal skid buffer for one channel."""
            setattr(self, f"_sk_{in_dat}_v", Reg(1, f"sk_{in_dat}_v"))
            setattr(self, f"_sk_{in_dat}_d", Reg(width, f"sk_{in_dat}_d"))
            sv = getattr(self, f"_sk_{in_dat}_v")
            sd = getattr(self, f"_sk_{in_dat}_d")
            with self.comb:
                in_rdy <<= (sv == 0) | (out_rdy & out_vld)
                out_vld <<= sv | (in_vld & (out_rdy | ~out_vld))
                out_dat <<= sd if sv else in_dat
            with self.seq(self.clk, self.rst):
                with If(self.rst == 1):
                    sv <<= 0
                with Else():
                    with If(sv):
                        with If(out_rdy & out_vld):
                            sv <<= 0
                    with Elif(in_vld & in_rdy):
                        sd <<= in_dat; sv <<= 1

        def _simple_buf(in_vld, in_rdy, out_vld, out_rdy):
            """Simple pipeline buffer (one-cycle delay)."""
            with self.comb:
                in_rdy <<= ~out_vld | out_rdy
            with self.seq(self.clk, self.rst):
                with If(self.rst == 1):
                    out_vld <<= 0
                with Else():
                    with If(in_vld & in_rdy):
                        out_vld <<= 1
                    with Elif(out_rdy & out_vld):
                        out_vld <<= 0

        # Instantiate per-channel buffers based on reg_type
        if aw_reg == 0:  # bypass
            self.m_awvalid <<= self.s_awvalid; self.s_awready <<= self.m_awready
            self.m_awaddr <<= self.s_awaddr; self.m_awid <<= self.s_awid
        elif aw_reg == 1:
            _simple_buf(self.s_awvalid, self.s_awready, self.m_awvalid, self.m_awready)
        else:
            _skid_buffer(self.s_awvalid, self.s_awready, self.s_awaddr,
                         self.m_awvalid, self.m_awready, self.m_awaddr, AW)

        with self.comb:
            self.m_awaddr <<= self.s_awaddr if aw_reg == 0 else self.s_awaddr
            self.m_awid <<= self.s_awid

        # W channel
        if w_reg == 0:
            self.m_wvalid <<= self.s_wvalid; self.s_wready <<= self.m_wready
            self.m_wdata <<= self.s_wdata; self.m_wlast <<= self.s_wlast
        elif w_reg == 1:
            _simple_buf(self.s_wvalid, self.s_wready, self.m_wvalid, self.m_wready)
        else:
            _skid_buffer(self.s_wvalid, self.s_wready, self.s_wdata,
                         self.m_wvalid, self.m_wready, self.m_wdata, DW)
        with self.comb:
            self.m_wlast <<= self.s_wlast

        # B channel
        if b_reg == 0:
            self.m_bvalid <<= self.s_bvalid; self.s_bready <<= self.m_bready
        elif b_reg == 1:
            _simple_buf(self.s_bvalid, self.s_bready, self.m_bvalid, self.m_bready)
        with self.comb:
            self.m_bid <<= self.s_bid; self.m_bresp <<= self.s_bresp

        # AR channel
        if ar_reg == 0:
            self.m_arvalid <<= self.s_arvalid; self.s_arready <<= self.m_arready
        elif ar_reg == 1:
            _simple_buf(self.s_arvalid, self.s_arready, self.m_arvalid, self.m_arready)
        with self.comb:
            self.m_araddr <<= self.s_araddr; self.m_arid <<= self.s_arid

        # R channel
        if r_reg == 0:
            self.m_rvalid <<= self.s_rvalid; self.s_rready <<= self.m_rready
        elif r_reg == 1:
            _simple_buf(self.s_rvalid, self.s_rready, self.m_rvalid, self.m_rready)
        with self.comb:
            self.m_rdata <<= self.s_rdata; self.m_rid <<= self.s_rid
            self.m_rlast <<= self.s_rlast
