"""L5 DSL module for the EarphoneSRAM256K memory.

RTL-ready rtlgen description of the 256 KB on-chip APB4 SRAM.
"""

from __future__ import annotations

from rtlgen.core import Module, Input, Output, Memory, Reg, Wire
from rtlgen import Cat, Mux
from rtlgen.logic import If, Else
from rtlgen.codegen import VerilogEmitter, ModuleDocTemplate, fill_doc_template


class EarphoneSRAM256K(Module):
    """256 KB on-chip SRAM, APB4 slave, byte write enable."""

    def __init__(self):
        super().__init__("earphone_sram256k")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # APB slave
        self.paddr = Input(32, "paddr")
        self.pwdata = Input(32, "pwdata")
        self.prdata = Output(32, "prdata")
        self.pwrite = Input(1, "pwrite")
        self.psel = Input(1, "psel")
        self.penable = Input(1, "penable")
        self.pready = Output(1, "pready")
        self.pslverr = Output(1, "pslverr")
        self.pstrb = Input(4, "pstrb")

        # Memory: 64K x 32 = 256 KB
        self.mem = Memory(32, 64 * 1024, "mem", init_zero=True)
        self.rdata_reg = Reg(32, "rdata_reg", init_value=0)

        addr_word = self.paddr[17:2]
        self.mem_rdata = Wire(32, "mem_rdata")
        self.mem_wdata = Wire(32, "mem_wdata")
        self.sram_ce = Wire(1, "sram_ce")

        with self.comb:
            self.prdata <<= self.rdata_reg
            self.pready <<= self.psel & self.penable
            self.pslverr <<= 0
            self.sram_ce <<= self.psel & self.penable
            self.mem_rdata <<= self.mem[addr_word]
            self.mem_wdata <<= Cat(
                Mux(self.pstrb[3], self.pwdata[31:24], self.mem_rdata[31:24]),
                Mux(self.pstrb[2], self.pwdata[23:16], self.mem_rdata[23:16]),
                Mux(self.pstrb[1], self.pwdata[15:8], self.mem_rdata[15:8]),
                Mux(self.pstrb[0], self.pwdata[7:0], self.mem_rdata[7:0]),
            )

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.rdata_reg <<= 0
            with Else():
                # Clock-gated SRAM access: only update on active APB transfers
                with If(self.sram_ce):
                    with If(self.pwrite):
                        self.mem[addr_word] <<= self.mem_wdata
                    with Else():
                        self.rdata_reg <<= self.mem_rdata

        tpl = ModuleDocTemplate(
            source="earphone/modules/sram256k/layer_L5_dsl/src/dsl.py",
            description="256 KB on-chip SRAM with APB4 slave port and transfer-gated clock.",
            author="RTLCraft Agent", version="0.1",
            timing="Single-cycle read/write; memory clock gated between APB transfers.",
        )
        fill_doc_template(tpl, self)


__all__ = ["EarphoneSRAM256K"]
