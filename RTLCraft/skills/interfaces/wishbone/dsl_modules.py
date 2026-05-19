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



class WB_REG(Module):
    """Wishbone register slice — inserts one cycle latency on bus transactions.

    Reference: ref_rtl/interfaces/wishbone/rtl/wb_reg.v
    - Idle: pass master→slave
    - Cycle: hold values until slave responds (ack/err/rty)
    - Response: pass slave→master, then return to idle
    """

    def __init__(self, data_width=32, addr_width=32):
        super().__init__("wb_reg")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")
        select_width = data_width // 8
        self.SELECT_WIDTH = Parameter(select_width, "SELECT_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # Master side (input)
        self.wbm_adr_i = Input(addr_width, "wbm_adr_i")
        self.wbm_dat_i = Input(data_width, "wbm_dat_i")
        self.wbm_dat_o = Output(data_width, "wbm_dat_o")
        self.wbm_we_i = Input(1, "wbm_we_i")
        self.wbm_sel_i = Input(select_width, "wbm_sel_i")
        self.wbm_stb_i = Input(1, "wbm_stb_i")
        self.wbm_ack_o = Output(1, "wbm_ack_o")
        self.wbm_err_o = Output(1, "wbm_err_o")
        self.wbm_rty_o = Output(1, "wbm_rty_o")
        self.wbm_cyc_i = Input(1, "wbm_cyc_i")

        # Slave side (output)
        self.wbs_adr_o = Output(addr_width, "wbs_adr_o")
        self.wbs_dat_i = Input(data_width, "wbs_dat_i")
        self.wbs_dat_o = Output(data_width, "wbs_dat_o")
        self.wbs_we_o = Output(1, "wbs_we_o")
        self.wbs_sel_o = Output(select_width, "wbs_sel_o")
        self.wbs_stb_o = Output(1, "wbs_stb_o")
        self.wbs_ack_i = Input(1, "wbs_ack_i")
        self.wbs_err_i = Input(1, "wbs_err_i")
        self.wbs_rty_i = Input(1, "wbs_rty_i")
        self.wbs_cyc_o = Output(1, "wbs_cyc_o")

        # Registers
        self._wbm_dat_o_reg = Reg(data_width, "wbm_dat_o_reg", init_value=0)
        self._wbm_ack_o_reg = Reg(1, "wbm_ack_o_reg", init_value=0)
        self._wbm_err_o_reg = Reg(1, "wbm_err_o_reg", init_value=0)
        self._wbm_rty_o_reg = Reg(1, "wbm_rty_o_reg", init_value=0)

        self._wbs_adr_o_reg = Reg(addr_width, "wbs_adr_o_reg", init_value=0)
        self._wbs_dat_o_reg = Reg(data_width, "wbs_dat_o_reg", init_value=0)
        self._wbs_we_o_reg = Reg(1, "wbs_we_o_reg", init_value=0)
        self._wbs_sel_o_reg = Reg(select_width, "wbs_sel_o_reg", init_value=0)
        self._wbs_stb_o_reg = Reg(1, "wbs_stb_o_reg", init_value=0)
        self._wbs_cyc_o_reg = Reg(1, "wbs_cyc_o_reg", init_value=0)

        with self.comb:
            self.wbm_dat_o <<= self._wbm_dat_o_reg
            self.wbm_ack_o <<= self._wbm_ack_o_reg
            self.wbm_err_o <<= self._wbm_err_o_reg
            self.wbm_rty_o <<= self._wbm_rty_o_reg

            self.wbs_adr_o <<= self._wbs_adr_o_reg
            self.wbs_dat_o <<= self._wbs_dat_o_reg
            self.wbs_we_o <<= self._wbs_we_o_reg
            self.wbs_sel_o <<= self._wbs_sel_o_reg
            self.wbs_stb_o <<= self._wbs_stb_o_reg
            self.wbs_cyc_o <<= self._wbs_cyc_o_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._wbm_dat_o_reg <<= 0
                self._wbm_ack_o_reg <<= 0
                self._wbm_err_o_reg <<= 0
                self._wbm_rty_o_reg <<= 0
                self._wbs_adr_o_reg <<= 0
                self._wbs_dat_o_reg <<= 0
                self._wbs_we_o_reg <<= 0
                self._wbs_sel_o_reg <<= 0
                self._wbs_stb_o_reg <<= 0
                self._wbs_cyc_o_reg <<= 0
            with Else():
                with If(self._wbs_cyc_o_reg == 1 and self._wbs_stb_o_reg == 1):
                    # Active cycle — hold values
                    with If((self.wbs_ack_i == 1) | (self.wbs_err_i == 1) | (self.wbs_rty_i == 1)):
                        # End of cycle: pass slave response to master
                        self._wbm_dat_o_reg <<= self.wbs_dat_i
                        self._wbm_ack_o_reg <<= self.wbs_ack_i
                        self._wbm_err_o_reg <<= self.wbs_err_i
                        self._wbm_rty_o_reg <<= self.wbs_rty_i
                        self._wbs_we_o_reg <<= 0
                        self._wbs_stb_o_reg <<= 0
                with Else():
                    # Idle: pass master to slave
                    self._wbm_dat_o_reg <<= 0
                    self._wbm_ack_o_reg <<= 0
                    self._wbm_err_o_reg <<= 0
                    self._wbm_rty_o_reg <<= 0
                    self._wbs_adr_o_reg <<= self.wbm_adr_i
                    self._wbs_dat_o_reg <<= self.wbm_dat_i
                    self._wbs_we_o_reg <<= self.wbm_we_i & ~(self._wbm_ack_o_reg | self._wbm_err_o_reg | self._wbm_rty_o_reg)
                    self._wbs_sel_o_reg <<= self.wbm_sel_i
                    self._wbs_stb_o_reg <<= self.wbm_stb_i & ~(self._wbm_ack_o_reg | self._wbm_err_o_reg | self._wbm_rty_o_reg)
                    self._wbs_cyc_o_reg <<= self.wbm_cyc_i

        tpl = ModuleDocTemplate(
            source="WB_REG — ref_rtl/interfaces/wishbone/rtl/wb_reg.v",
            description=f"Wishbone register slice: {data_width}-bit data, {addr_width}-bit addr. "
                        "One-cycle latency, cycle-hold behavior.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency per transaction",
        )
        fill_doc_template(tpl, self)


class WB_MUX_2(Module):
    """Wishbone 2-to-1 address decoder multiplexer.

    Reference: ref_rtl/interfaces/wishbone/rtl/wb_mux_2.v
    - Address decode: match = ~|((adr ^ slave_addr) & slave_addr_msk)
    - Priority: slave0 has priority over slave1
    - Pure combinational (no registers)
    """

    def __init__(self, data_width=32, addr_width=32):
        super().__init__("wb_mux_2")
        self.DATA_WIDTH = Parameter(data_width, "DATA_WIDTH")
        self.ADDR_WIDTH = Parameter(addr_width, "ADDR_WIDTH")
        select_width = data_width // 8
        self.SELECT_WIDTH = Parameter(select_width, "SELECT_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # Master input
        self.wbm_adr_i = Input(addr_width, "wbm_adr_i")
        self.wbm_dat_i = Input(data_width, "wbm_dat_i")
        self.wbm_dat_o = Output(data_width, "wbm_dat_o")
        self.wbm_we_i = Input(1, "wbm_we_i")
        self.wbm_sel_i = Input(select_width, "wbm_sel_i")
        self.wbm_stb_i = Input(1, "wbm_stb_i")
        self.wbm_ack_o = Output(1, "wbm_ack_o")
        self.wbm_err_o = Output(1, "wbm_err_o")
        self.wbm_rty_o = Output(1, "wbm_rty_o")
        self.wbm_cyc_i = Input(1, "wbm_cyc_i")

        # Slave 0
        self.wbs0_adr_o = Output(addr_width, "wbs0_adr_o")
        self.wbs0_dat_i = Input(data_width, "wbs0_dat_i")
        self.wbs0_dat_o = Output(data_width, "wbs0_dat_o")
        self.wbs0_we_o = Output(1, "wbs0_we_o")
        self.wbs0_sel_o = Output(select_width, "wbs0_sel_o")
        self.wbs0_stb_o = Output(1, "wbs0_stb_o")
        self.wbs0_ack_i = Input(1, "wbs0_ack_i")
        self.wbs0_err_i = Input(1, "wbs0_err_i")
        self.wbs0_rty_i = Input(1, "wbs0_rty_i")
        self.wbs0_cyc_o = Output(1, "wbs0_cyc_o")
        self.wbs0_addr = Input(addr_width, "wbs0_addr")
        self.wbs0_addr_msk = Input(addr_width, "wbs0_addr_msk")

        # Slave 1
        self.wbs1_adr_o = Output(addr_width, "wbs1_adr_o")
        self.wbs1_dat_i = Input(data_width, "wbs1_dat_i")
        self.wbs1_dat_o = Output(data_width, "wbs1_dat_o")
        self.wbs1_we_o = Output(1, "wbs1_we_o")
        self.wbs1_sel_o = Output(select_width, "wbs1_sel_o")
        self.wbs1_stb_o = Output(1, "wbs1_stb_o")
        self.wbs1_ack_i = Input(1, "wbs1_ack_i")
        self.wbs1_err_i = Input(1, "wbs1_err_i")
        self.wbs1_rty_i = Input(1, "wbs1_rty_i")
        self.wbs1_cyc_o = Output(1, "wbs1_cyc_o")
        self.wbs1_addr = Input(addr_width, "wbs1_addr")
        self.wbs1_addr_msk = Input(addr_width, "wbs1_addr_msk")

        # Address match logic
        self._wbs0_match = Wire(1, "wbs0_match")
        self._wbs1_match = Wire(1, "wbs1_match")
        self._wbs0_sel = Wire(1, "wbs0_sel")
        self._wbs1_sel = Wire(1, "wbs1_sel")
        self._master_cycle = Wire(1, "master_cycle")
        self._select_error = Wire(1, "select_error")

        with self.comb:
            self._wbs0_match <<= ((self.wbm_adr_i ^ self.wbs0_addr) & self.wbs0_addr_msk) == 0
            self._wbs1_match <<= ((self.wbm_adr_i ^ self.wbs1_addr) & self.wbs1_addr_msk) == 0
            self._wbs0_sel <<= self._wbs0_match
            self._wbs1_sel <<= self._wbs1_match & ~self._wbs0_match
            self._master_cycle <<= self.wbm_cyc_i & self.wbm_stb_i
            self._select_error <<= ~(self._wbs0_sel | self._wbs1_sel) & self._master_cycle

            # Master outputs
            self.wbm_dat_o <<= Mux(self._wbs0_sel, self.wbs0_dat_i,
                                   Mux(self._wbs1_sel, self.wbs1_dat_i, Const(0, data_width)))
            self.wbm_ack_o <<= self.wbs0_ack_i | self.wbs1_ack_i
            self.wbm_err_o <<= self.wbs0_err_i | self.wbs1_err_i | self._select_error
            self.wbm_rty_o <<= self.wbs0_rty_i | self.wbs1_rty_i

            # Slave 0 outputs
            self.wbs0_adr_o <<= self.wbm_adr_i
            self.wbs0_dat_o <<= self.wbm_dat_i
            self.wbs0_we_o <<= self.wbm_we_i & self._wbs0_sel
            self.wbs0_sel_o <<= self.wbm_sel_i
            self.wbs0_stb_o <<= self.wbm_stb_i & self._wbs0_sel
            self.wbs0_cyc_o <<= self.wbm_cyc_i & self._wbs0_sel

            # Slave 1 outputs
            self.wbs1_adr_o <<= self.wbm_adr_i
            self.wbs1_dat_o <<= self.wbm_dat_i
            self.wbs1_we_o <<= self.wbm_we_i & self._wbs1_sel
            self.wbs1_sel_o <<= self.wbm_sel_i
            self.wbs1_stb_o <<= self.wbm_stb_i & self._wbs1_sel
            self.wbs1_cyc_o <<= self.wbm_cyc_i & self._wbs1_sel

        tpl = ModuleDocTemplate(
            source="WB_MUX_2 — ref_rtl/interfaces/wishbone/rtl/wb_mux_2.v",
            description=f"Wishbone 2-to-1 MUX: {data_width}-bit data, {addr_width}-bit addr. "
                        "Address-decoded with slave0 priority.",
            author="rtlgen agent", version="1.0",
            timing="Combinational: no latency",
        )
        fill_doc_template(tpl, self)
