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



class PULSE_MERGE(Module):
    """Pulse merge: counts pulses across multiple inputs, outputs one pulse per count.

    Reference: ref_rtl/interfaces/pcie/rtl/pulse_merge.v
    - Accumulates input pulses into a counter
    - Outputs one pulse per count decrement
    - Saturating behavior (new pulses add to counter)
    """

    def __init__(self, input_width=2, count_width=4):
        super().__init__("pulse_merge")
        self.INPUT_WIDTH = Parameter(input_width, "INPUT_WIDTH")
        self.COUNT_WIDTH = Parameter(count_width, "COUNT_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.pulse_in = Input(input_width, "pulse_in")
        self.count_out = Output(count_width, "count_out")
        self.pulse_out = Output(1, "pulse_out")

        self._count_reg = Reg(count_width, "count_reg", init_value=0)
        self._pulse_reg = Reg(1, "pulse_reg", init_value=0)

        self._count_next = Wire(count_width, "count_next")
        self._pulse_next = Wire(1, "pulse_next")

        with self.comb:
            self.count_out <<= self._count_reg
            self.pulse_out <<= self._pulse_reg

            # Decrement if count > 0, else hold
            count_base = Mux(self._count_reg > 0, self._count_reg - 1, self._count_reg)

            # Sum all input pulses
            pulse_sum = self.pulse_in[0]
            for i in range(1, input_width):
                pulse_sum = pulse_sum + self.pulse_in[i]

            self._count_next <<= count_base + pulse_sum
            self._pulse_next <<= self._count_reg > 0

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._count_reg <<= 0
                self._pulse_reg <<= 0
            with Else():
                self._count_reg <<= self._count_next
                self._pulse_reg <<= self._pulse_next

        tpl = ModuleDocTemplate(
            source="PULSE_MERGE — ref_rtl/interfaces/pcie/rtl/pulse_merge.v",
            description=f"Pulse merge: {input_width} inputs, {count_width}-bit counter. "
                        "Accumulates pulses, outputs one per cycle while count > 0.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle latency",
        )
        fill_doc_template(tpl, self)


class PCIE_PTILE_FC_COUNTER(Module):
    """PCIe P-Tile flow control counter.

    Reference: ref_rtl/interfaces/pcie/rtl/pcie_ptile_fc_counter.v
    - Tracks available credits (fc_av)
    - Increments on limit update, decrements on fc_dec
    - Saturating arithmetic (0 <= fc_av <= fc_cap)
    """

    def __init__(self, width=16, index=0):
        super().__init__("pcie_ptile_fc_counter")
        self.WIDTH = Parameter(width, "WIDTH")
        self.INDEX = Parameter(index, "INDEX")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.tx_cdts_limit = Input(width, "tx_cdts_limit")
        self.tx_cdts_limit_tdm_idx = Input(3, "tx_cdts_limit_tdm_idx")
        self.fc_dec = Input(width, "fc_dec")
        self.fc_av = Output(width, "fc_av")

        self._fc_cap_reg = Reg(width, "fc_cap_reg", init_value=0)
        self._fc_limit_reg = Reg(width, "fc_limit_reg", init_value=0)
        self._fc_inc_reg = Reg(width, "fc_inc_reg", init_value=0)
        self._fc_av_reg = Reg(width, "fc_av_reg", init_value=0)

        self._fc_new = Wire(width, "fc_new")

        with self.comb:
            self.fc_av <<= self._fc_av_reg
            # Saturating arithmetic: fc_av = clamp(fc_av - fc_dec + fc_inc, 0, fc_cap)
            add_result = self._fc_av_reg + self._fc_inc_reg
            self._fc_new <<= 0
            with If(add_result >= self.fc_dec):
                sub_result = add_result - self.fc_dec
                with If(sub_result > self._fc_cap_reg):
                    self._fc_new <<= self._fc_cap_reg
                with Else():
                    self._fc_new <<= sub_result

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._fc_cap_reg <<= 0
                self._fc_limit_reg <<= 0
                self._fc_inc_reg <<= 0
                self._fc_av_reg <<= 0
            with Else():
                with If(self.tx_cdts_limit_tdm_idx == index):
                    with If(self._fc_cap_reg == 0):
                        self._fc_cap_reg <<= self.tx_cdts_limit
                    self._fc_inc_reg <<= self.tx_cdts_limit - self._fc_limit_reg
                    self._fc_limit_reg <<= self.tx_cdts_limit

                self._fc_av_reg <<= self._fc_new

        tpl = ModuleDocTemplate(
            source="PCIE_PTILE_FC_COUNTER — ref_rtl/interfaces/pcie/rtl/pcie_ptile_fc_counter.v",
            description=f"PCIe P-Tile flow control counter: {width}-bit credits, index={index}. "
                        "Saturating arithmetic.",
            author="rtlgen agent", version="1.0",
            timing="Registered: 1-cycle credit update latency",
        )
        fill_doc_template(tpl, self)


class PTP_TS_EXTRACT(Module):
    """PTP timestamp extract from AXI-Stream tuser.

    Reference: ref_rtl/interfaces/ethernet/rtl/ptp_ts_extract.v
    - Extracts timestamp from tuser[TS_OFFSET+TS_WIDTH-1 : TS_OFFSET]
    - Outputs valid on first beat of each frame
    """

    def __init__(self, ts_width=96, ts_offset=1):
        super().__init__("ptp_ts_extract")
        self.TS_WIDTH = Parameter(ts_width, "TS_WIDTH")
        self.TS_OFFSET = Parameter(ts_offset, "TS_OFFSET")
        user_width = ts_width + ts_offset

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        # AXI-Stream input
        self.s_axis_tvalid = Input(1, "s_axis_tvalid")
        self.s_axis_tlast = Input(1, "s_axis_tlast")
        self.s_axis_tuser = Input(user_width, "s_axis_tuser")

        # Timestamp output
        self.m_axis_ts = Output(ts_width, "m_axis_ts")
        self.m_axis_ts_valid = Output(1, "m_axis_ts_valid")

        self._frame_reg = Reg(1, "frame_reg", init_value=0)

        with self.comb:
            self.m_axis_ts <<= self.s_axis_tuser[ts_width + ts_offset - 1 : ts_offset]
            self.m_axis_ts_valid <<= self.s_axis_tvalid & ~self._frame_reg

        with self.seq(self.clk, self.rst):
            with If(self.s_axis_tvalid == 1):
                self._frame_reg <<= ~self.s_axis_tlast
            with If(self.rst == 1):
                self._frame_reg <<= 0

        tpl = ModuleDocTemplate(
            source="PTP_TS_EXTRACT — ref_rtl/interfaces/ethernet/rtl/ptp_ts_extract.v",
            description=f"PTP timestamp extract: {ts_width}-bit ts from tuser[{ts_offset}+:{ts_width}]. "
                        "Valid on first beat of each frame.",
            author="rtlgen agent", version="1.0",
            timing="Combinational: zero-cycle latency",
        )
        fill_doc_template(tpl, self)
