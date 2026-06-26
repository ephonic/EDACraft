"""
L3 DSL — AXI-Lite Register Interface (control register bank).

Extracted from ref_rtl/interfaces/axi/rtl/axil_reg_if.v
Micro-architecture: address decode → register read/write with AXI-Lite response.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Elif


class AXILiteRegIF(Module):
    """AXI-Lite register interface with N registers."""

    def __init__(self, n_regs=32, data_width=32, addr_width=32, name="axil_reg_if"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")

        # AXI-Lite slave interface
        self.s_awaddr = Input(addr_width, "s_awaddr")
        self.s_awvalid = Input(1, "s_awvalid"); self.s_awready = Output(1, "s_awready")
        self.s_wdata = Input(data_width, "s_wdata"); self.s_wstrb = Input(data_width // 8, "s_wstrb")
        self.s_wvalid = Input(1, "s_wvalid"); self.s_wready = Output(1, "s_wready")
        self.s_bresp = Output(2, "s_bresp"); self.s_bvalid = Output(1, "s_bvalid")
        self.s_bready = Input(1, "s_bready")
        self.s_araddr = Input(addr_width, "s_araddr")
        self.s_arvalid = Input(1, "s_arvalid"); self.s_arready = Output(1, "s_arready")
        self.s_rdata = Output(data_width, "s_rdata"); self.s_rresp = Output(2, "s_rresp")
        self.s_rvalid = Output(1, "s_rvalid"); self.s_rready = Input(1, "s_rready")

        # Register file
        self._regfile = [Reg(data_width, f"reg_{i}") for i in range(n_regs)]
        aw = max((n_regs - 1).bit_length(), 1)

        wr_addr = Wire(aw, "wr_addr"); rd_addr = Wire(aw, "rd_addr")
        with self.comb:
            wr_addr <<= self.s_awaddr[aw + 1:2]
            rd_addr <<= self.s_araddr[aw + 1:2]

        # Write handshake (single-cycle AW+W → B)
        w_fire = Wire(1, "w_fire")
        with self.comb:
            w_fire <<= self.s_awvalid & self.s_awready
            self.s_awready <<= (self.s_bvalid == 0) | self.s_bready
            self.s_wready <<= (self.s_bvalid == 0) | self.s_bready

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.s_bvalid <<= 0; self.s_bresp <<= 0
            with Else():
                with If(self.s_bvalid & self.s_bready):
                    self.s_bvalid <<= 0
                with Elif(self.s_awvalid & self.s_wvalid & ((self.s_bvalid == 0) | self.s_bready)):
                    self.s_bvalid <<= 1; self.s_bresp <<= 0  # OKAY
                    with If(wr_addr < n_regs):
                        for i in range(n_regs):
                            with If(wr_addr == i):
                                self._regfile[i] <<= self.s_wdata

        # Read handshake
        with self.comb:
            self.s_arready <<= (self.s_rvalid == 0) | self.s_rready
            self.s_rdata <<= 0
            for i in range(n_regs):
                with If(rd_addr == i):
                    self.s_rdata <<= self._regfile[i]

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.s_rvalid <<= 0; self.s_rresp <<= 0
            with Else():
                with If(self.s_rvalid & self.s_rready):
                    self.s_rvalid <<= 0
                with Elif(self.s_arvalid & ((self.s_rvalid == 0) | self.s_rready)):
                    self.s_rvalid <<= 1; self.s_rresp <<= 0
