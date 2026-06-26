"""dsl_modules — DSL Reference Implementations

Extracted from design_interfaces.py.
"""
from __future__ import annotations

from rtlgen import (
    Input, Output, Wire, Reg, Module, Vector, Array, VerilogEmitter,
    ArchDefinition, ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, HandshakeSpec, QueueSpec,
    ArchSimulator, ArchSkeletonGenerator,
    BehavioralSpec, StrategySpec, DecompositionResult,
    Memory, Parameter, LocalParam,
)
from rtlgen.logic import If, Else, Elif, When, Otherwise, Const, Cat, Mux, Switch, Rep, ForGen
from rtlgen.lib import SyncFIFO
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template



class AXIL_RAM(Module):
    """AXI-Lite RAM with word-level read/write.

    Reference: ref_rtl/interfaces/axi/rtl/axil_ram.v
    Simplified: no byte-level write enable (full word writes only).
    - Write: AW handshake + W handshake → B response
    - Read: AR handshake → R response with data
    - Zero-initialized memory
    """

    def __init__(self, data_width=32, addr_width=16):
        super().__init__("axil_ram")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Lite Write Address
        self.s_axil_awaddr = Input(addr_width, "s_axil_awaddr")
        self.s_axil_awvalid = Input(1, "s_axil_awvalid")
        self.s_axil_awready = Output(1, "s_axil_awready")

        # AXI-Lite Write Data
        self.s_axil_wdata = Input(data_width, "s_axil_wdata")
        self.s_axil_wvalid = Input(1, "s_axil_wvalid")
        self.s_axil_wready = Output(1, "s_axil_wready")

        # AXI-Lite Write Response
        self.s_axil_bresp = Output(2, "s_axil_bresp")
        self.s_axil_bvalid = Output(1, "s_axil_bvalid")
        self.s_axil_bready = Input(1, "s_axil_bready")

        # AXI-Lite Read Address
        self.s_axil_araddr = Input(addr_width, "s_axil_araddr")
        self.s_axil_arvalid = Input(1, "s_axil_arvalid")
        self.s_axil_arready = Output(1, "s_axil_arready")

        # AXI-Lite Read Data
        self.s_axil_rdata = Output(data_width, "s_axil_rdata")
        self.s_axil_rresp = Output(2, "s_axil_rresp")
        self.s_axil_rvalid = Output(1, "s_axil_rvalid")
        self.s_axil_rready = Input(1, "s_axil_rready")

        # Memory (word-addressable, depth = 2^addr_width)
        depth = 2 ** addr_width
        self._mem = Memory(data_width, depth, "mem", init_zero=True)

        # Write channel registers
        self._awready_reg = Reg(1, "awready_reg", init_value=0)
        self._wready_reg = Reg(1, "wready_reg", init_value=0)
        self._bvalid_reg = Reg(1, "bvalid_reg", init_value=0)

        # Read channel registers
        self._arready_reg = Reg(1, "arready_reg", init_value=0)
        self._rvalid_reg = Reg(1, "rvalid_reg", init_value=0)
        self._rdata_reg = Reg(data_width, "rdata_reg", init_value=0)

        # Address latches
        self._awaddr_reg = Reg(addr_width, "awaddr_reg", init_value=0)
        self._araddr_reg = Reg(addr_width, "araddr_reg", init_value=0)

        with self.comb:
            self.s_axil_awready <<= self._awready_reg
            self.s_axil_wready <<= self._wready_reg
            self.s_axil_bresp <<= 0
            self.s_axil_bvalid <<= self._bvalid_reg
            self.s_axil_arready <<= self._arready_reg
            self.s_axil_rdata <<= self._rdata_reg
            self.s_axil_rresp <<= 0
            self.s_axil_rvalid <<= self._rvalid_reg

        with self.seq(self.clk):
            # Write response clear
            with If((self.s_axil_bready == 1) & (self._bvalid_reg == 1)):
                self._bvalid_reg <<= 0

            # Read response clear
            with If((self.s_axil_rready == 1) & (self._rvalid_reg == 1)):
                self._rvalid_reg <<= 0

            # Write transaction
            with If((self.s_axil_awvalid == 1) & (self.s_axil_wvalid == 1)
                    & (self._bvalid_reg == 0)):
                self._awready_reg <<= 1
                self._wready_reg <<= 1
                self._bvalid_reg <<= 1
                self._awaddr_reg <<= self.s_axil_awaddr
                self._mem[self.s_axil_awaddr] <<= self.s_axil_wdata
            with Else():
                self._awready_reg <<= 0
                self._wready_reg <<= 0

            # Read transaction
            with If((self.s_axil_arvalid == 1)
                    & ((self._rvalid_reg == 0) | (self.s_axil_rready == 1))):
                self._arready_reg <<= 1
                self._rvalid_reg <<= 1
                self._araddr_reg <<= self.s_axil_araddr
                self._rdata_reg <<= self._mem[self.s_axil_araddr]
            with Else():
                self._arready_reg <<= 0

            with If(self.rst == 1):
                self._awready_reg <<= 0
                self._wready_reg <<= 0
                self._bvalid_reg <<= 0
                self._arready_reg <<= 0
                self._rvalid_reg <<= 0
                self._rdata_reg <<= 0

        tpl = ModuleDocTemplate(
            source="AXIL_RAM — ref_rtl/interfaces/axi/rtl/axil_ram.v",
            description=f"AXI-Lite RAM: {data_width}-bit words, {depth} entries. "
                        "Word-level read/write with zero init.",
            author="rtlgen agent", version="1.0",
            timing="Write: 1-cycle ready + response. Read: 1-cycle latency.",
        )
        fill_doc_template(tpl, self)


class AXI_DP_RAM_SIMPLE(Module):
    """Simplified AXI dual-port RAM (word-level, no byte enables).

    Reference: ref_rtl/interfaces/axi/rtl/axi_dp_ram.v (simplified)
    - Port A: read/write
    - Port B: read/write
    - Word-level access only (no byte strobes)
    - Zero-initialized memory
    """

    def __init__(self, data_width=32, addr_width=16):
        super().__init__("axi_dp_ram_simple")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")

        self.a_clk = Input(1, "a_clk")
        self.a_rst = Input(1, "a_rst")
        self.b_clk = Input(1, "b_clk")
        self.b_rst = Input(1, "b_rst")

        # Port A AXI-Lite simplified interface
        self.a_awaddr = Input(addr_width, "a_awaddr")
        self.a_awvalid = Input(1, "a_awvalid")
        self.a_awready = Output(1, "a_awready")
        self.a_wdata = Input(data_width, "a_wdata")
        self.a_wvalid = Input(1, "a_wvalid")
        self.a_wready = Output(1, "a_wready")
        self.a_bresp = Output(2, "a_bresp")
        self.a_bvalid = Output(1, "a_bvalid")
        self.a_bready = Input(1, "a_bready")
        self.a_araddr = Input(addr_width, "a_araddr")
        self.a_arvalid = Input(1, "a_arvalid")
        self.a_arready = Output(1, "a_arready")
        self.a_rdata = Output(data_width, "a_rdata")
        self.a_rresp = Output(2, "a_rresp")
        self.a_rvalid = Output(1, "a_rvalid")
        self.a_rready = Input(1, "a_rready")

        # Port B AXI-Lite simplified interface
        self.b_awaddr = Input(addr_width, "b_awaddr")
        self.b_awvalid = Input(1, "b_awvalid")
        self.b_awready = Output(1, "b_awready")
        self.b_wdata = Input(data_width, "b_wdata")
        self.b_wvalid = Input(1, "b_wvalid")
        self.b_wready = Output(1, "b_wready")
        self.b_bresp = Output(2, "b_bresp")
        self.b_bvalid = Output(1, "b_bvalid")
        self.b_bready = Input(1, "b_bready")
        self.b_araddr = Input(addr_width, "b_araddr")
        self.b_arvalid = Input(1, "b_arvalid")
        self.b_arready = Output(1, "b_arready")
        self.b_rdata = Output(data_width, "b_rdata")
        self.b_rresp = Output(2, "b_rresp")
        self.b_rvalid = Output(1, "b_rvalid")
        self.b_rready = Input(1, "b_rready")

        depth = 2 ** addr_width
        self._mem = Memory(data_width, depth, "mem", init_zero=True)

        # Port A regs
        self._a_awready_reg = Reg(1, "a_awready_reg", init_value=0)
        self._a_wready_reg = Reg(1, "a_wready_reg", init_value=0)
        self._a_bvalid_reg = Reg(1, "a_bvalid_reg", init_value=0)
        self._a_arready_reg = Reg(1, "a_arready_reg", init_value=0)
        self._a_rdata_reg = Reg(data_width, "a_rdata_reg", init_value=0)
        self._a_rvalid_reg = Reg(1, "a_rvalid_reg", init_value=0)

        # Port B regs
        self._b_awready_reg = Reg(1, "b_awready_reg", init_value=0)
        self._b_wready_reg = Reg(1, "b_wready_reg", init_value=0)
        self._b_bvalid_reg = Reg(1, "b_bvalid_reg", init_value=0)
        self._b_arready_reg = Reg(1, "b_arready_reg", init_value=0)
        self._b_rdata_reg = Reg(data_width, "b_rdata_reg", init_value=0)
        self._b_rvalid_reg = Reg(1, "b_rvalid_reg", init_value=0)

        with self.comb:
            self.a_awready <<= self._a_awready_reg
            self.a_wready <<= self._a_wready_reg
            self.a_bresp <<= 0
            self.a_bvalid <<= self._a_bvalid_reg
            self.a_arready <<= self._a_arready_reg
            self.a_rdata <<= self._a_rdata_reg
            self.a_rresp <<= 0
            self.a_rvalid <<= self._a_rvalid_reg

            self.b_awready <<= self._b_awready_reg
            self.b_wready <<= self._b_wready_reg
            self.b_bresp <<= 0
            self.b_bvalid <<= self._b_bvalid_reg
            self.b_arready <<= self._b_arready_reg
            self.b_rdata <<= self._b_rdata_reg
            self.b_rresp <<= 0
            self.b_rvalid <<= self._b_rvalid_reg

        # Port A sequential
        with self.seq(self.a_clk, self.a_rst):
            with If(self.a_rst == 1):
                self._a_awready_reg <<= 0
                self._a_wready_reg <<= 0
                self._a_bvalid_reg <<= 0
                self._a_arready_reg <<= 0
                self._a_rvalid_reg <<= 0
                self._a_rdata_reg <<= 0
            with Else():
                with If(self.a_bready == 1 and self._a_bvalid_reg == 1):
                    self._a_bvalid_reg <<= 0
                with If(self.a_rready == 1 and self._a_rvalid_reg == 1):
                    self._a_rvalid_reg <<= 0

                with If((self.a_awvalid == 1) & (self.a_wvalid == 1) & (self._a_bvalid_reg == 0)):
                    self._a_awready_reg <<= 1
                    self._a_wready_reg <<= 1
                    self._a_bvalid_reg <<= 1
                    self._mem[self.a_awaddr] <<= self.a_wdata
                with Else():
                    self._a_awready_reg <<= 0
                    self._a_wready_reg <<= 0

                with If((self.a_arvalid == 1) & ((self._a_rvalid_reg == 0) | (self.a_rready == 1))):
                    self._a_arready_reg <<= 1
                    self._a_rvalid_reg <<= 1
                    self._a_rdata_reg <<= self._mem[self.a_araddr]
                with Else():
                    self._a_arready_reg <<= 0

        # Port B sequential
        with self.seq(self.b_clk, self.b_rst):
            with If(self.b_rst == 1):
                self._b_awready_reg <<= 0
                self._b_wready_reg <<= 0
                self._b_bvalid_reg <<= 0
                self._b_arready_reg <<= 0
                self._b_rvalid_reg <<= 0
                self._b_rdata_reg <<= 0
            with Else():
                with If(self.b_bready == 1 and self._b_bvalid_reg == 1):
                    self._b_bvalid_reg <<= 0
                with If(self.b_rready == 1 and self._b_rvalid_reg == 1):
                    self._b_rvalid_reg <<= 0

                with If((self.b_awvalid == 1) & (self.b_wvalid == 1) & (self._b_bvalid_reg == 0)):
                    self._b_awready_reg <<= 1
                    self._b_wready_reg <<= 1
                    self._b_bvalid_reg <<= 1
                    self._mem[self.b_awaddr] <<= self.b_wdata
                with Else():
                    self._b_awready_reg <<= 0
                    self._b_wready_reg <<= 0

                with If((self.b_arvalid == 1) & ((self._b_rvalid_reg == 0) | (self.b_rready == 1))):
                    self._b_arready_reg <<= 1
                    self._b_rvalid_reg <<= 1
                    self._b_rdata_reg <<= self._mem[self.b_araddr]
                with Else():
                    self._b_arready_reg <<= 0

        tpl = ModuleDocTemplate(
            source="AXI_DP_RAM_SIMPLE — ref_rtl/interfaces/axi/rtl/axi_dp_ram.v",
            description=f"Simplified AXI dual-port RAM: {data_width}-bit words, {depth} entries. "
                        "Word-level read/write, zero init.",
            author="rtlgen agent", version="1.0",
            timing="Write: 1-cycle. Read: 1-cycle latency.",
        )
        fill_doc_template(tpl, self)
