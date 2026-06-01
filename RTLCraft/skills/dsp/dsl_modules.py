"""
Spec2RTL Design Flow: Digital Signal Processor (DSP) Suite
==========================================================

Reference: ref_rtl/dsp/rtl/ (Alex Forencich open-source DSP library)

Modules implemented:
  1. dsp_mult              — Signed scalar multiplier (4-stage pipeline)
  2. iq_join               — Two-channel AXI-Stream synchronizer
  3. iq_split              — Two-channel AXI-Stream demultiplexer
  4. i2s_ctrl              — I2S bus clock generator
  5. phase_accumulator     — NCO phase accumulator
  6. dsp_iq_mult           — Complex IQ multiplier (4-stage pipeline)
  7. i2s_rx                — I2S serial receiver
  8. i2s_tx                — I2S serial transmitter
  9. sine_dds_lut          — Sine/cosine LUT with fine/coarse decomposition
  10. sine_dds             — Top-level DDS (phase_accumulator + sine_dds_lut)
  11. cic_decimator        — CIC decimator (N integrators + decimate + N combs)
  12. cic_interpolator     — CIC interpolator (N combs + upconvert + N integrators)
"""

from __future__ import annotations
import os, sys, math
_sys = sys
_sys.setrecursionlimit(10000)

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc, CycleContext,
    InterconnectSpec, ArchDefinition,
    ArchSimulator, ArchSkeletonGenerator,
    Algorithm_Model, datapath_template,
)
from rtlgen.core import (
    Module, Input, Output, Wire, Reg, Array, Const,
    Memory, Parameter, LocalParam,
)
from rtlgen import Cat, Rep, Mux
from rtlgen.logic import If, Else, Switch, ForGen, GenIf, GenElse
from rtlgen.codegen import VerilogEmitter, EmitProfile, ModuleDocTemplate, fill_doc_template
from rtlgen.ppa_optimizer import PPAOptimizer, SpecIR

try:
    from rtlgen.lint import VerilogLinter
except ImportError:
    VerilogLinter = None

print("=" * 70)
print("DSP Suite — DSL Module Definitions")
print("=" * 70)


# ============================================================================
# Module 1: DSP_MULT — Signed Scalar Multiplier (4-stage pipeline)
# ============================================================================
class DSP_MULT(Module):
    """Signed scalar multiplier with 4-stage pipeline for DSP slice mapping.

    Pipeline: input_reg_0 → input_reg_1 → multiply → output_reg_0 → output_reg_1
    AXI-Stream backpressure on both inputs and output.
    """

    def __init__(self, width=16):
        super().__init__("dsp_mult")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_a_tdata = Input(width, "input_a_tdata")
        self.input_a_tvalid = Input(1, "input_a_tvalid")
        self.input_a_tready = Output(1, "input_a_tready")

        self.input_b_tdata = Input(width, "input_b_tdata")
        self.input_b_tvalid = Input(1, "input_b_tvalid")
        self.input_b_tready = Output(1, "input_b_tready")

        self.output_tdata = Output(width * 2, "output_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        self._input_a_reg_0 = Reg(width, "input_a_reg_0", init_value=0, signed=True)
        self._input_a_reg_1 = Reg(width, "input_a_reg_1", init_value=0, signed=True)
        self._input_b_reg_0 = Reg(width, "input_b_reg_0", init_value=0, signed=True)
        self._input_b_reg_1 = Reg(width, "input_b_reg_1", init_value=0, signed=True)
        self._output_reg_0 = Reg(width * 2, "output_reg_0", init_value=0, signed=True)
        self._output_reg_1 = Reg(width * 2, "output_reg_1", init_value=0, signed=True)

        # 4-stage valid pipeline to track output validity
        self._valid_reg_0 = Reg(1, "valid_reg_0", init_value=0)
        self._valid_reg_1 = Reg(1, "valid_reg_1", init_value=0)
        self._valid_reg_2 = Reg(1, "valid_reg_2", init_value=0)
        self._valid_reg_3 = Reg(1, "valid_reg_3", init_value=0)

        with self.comb:
            self.input_a_tready <<= self.input_b_tvalid & self.output_tready
            self.input_b_tready <<= self.input_a_tvalid & self.output_tready
            self.output_tdata <<= self._output_reg_1
            self.output_tvalid <<= self._valid_reg_3

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._input_a_reg_0 <<= 0
                self._input_a_reg_1 <<= 0
                self._input_b_reg_0 <<= 0
                self._input_b_reg_1 <<= 0
                self._output_reg_0 <<= 0
                self._output_reg_1 <<= 0
                self._valid_reg_0 <<= 0
                self._valid_reg_1 <<= 0
                self._valid_reg_2 <<= 0
                self._valid_reg_3 <<= 0
            with Else():
                # Pipeline always advances (data+valid shift)
                self._input_a_reg_1 <<= self._input_a_reg_0
                self._input_b_reg_1 <<= self._input_b_reg_0
                self._output_reg_0 <<= self._input_a_reg_1 * self._input_b_reg_1
                self._output_reg_1 <<= self._output_reg_0
                self._valid_reg_1 <<= self._valid_reg_0
                self._valid_reg_2 <<= self._valid_reg_1
                self._valid_reg_3 <<= self._valid_reg_2

                with If(self.input_a_tvalid & self.input_b_tvalid & self.output_tready):
                    self._input_a_reg_0 <<= self.input_a_tdata
                    self._input_b_reg_0 <<= self.input_b_tdata
                    self._valid_reg_0 <<= 1
                with Else():
                    self._valid_reg_0 <<= 0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/dsp_mult.v",
            description="Signed scalar multiplier with 4-stage pipeline for DSP slice mapping.",
            author="rtlgen agent", version="1.0",
            timing="4-cycle latency: input_reg_0 → input_reg_1 → multiply → output_reg_0 → output_reg_1.",
        )
        fill_doc_template(tpl, self)


print("  - DSP_MULT defined")


# ============================================================================
# Module 2: IQ_JOIN — Two-Channel AXI-Stream Synchronizer
# ============================================================================
class IQ_JOIN(Module):
    """IQ joiner. Buffers independent I and Q AXI-Stream inputs and presents
    them as a synchronized IQ pair."""

    def __init__(self, width=16):
        super().__init__("iq_join")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_i_tdata = Input(width, "input_i_tdata")
        self.input_i_tvalid = Input(1, "input_i_tvalid")
        self.input_i_tready = Output(1, "input_i_tready")

        self.input_q_tdata = Input(width, "input_q_tdata")
        self.input_q_tvalid = Input(1, "input_q_tvalid")
        self.input_q_tready = Output(1, "input_q_tready")

        self.output_i_tdata = Output(width, "output_i_tdata")
        self.output_q_tdata = Output(width, "output_q_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        self._i_data_reg = Reg(width, "i_data_reg", init_value=0)
        self._q_data_reg = Reg(width, "q_data_reg", init_value=0)
        self._i_valid_reg = Reg(1, "i_valid_reg", init_value=0)
        self._q_valid_reg = Reg(1, "q_valid_reg", init_value=0)

        with self.comb:
            self.input_i_tready <<= ~self._i_valid_reg | (self.output_tready & self.output_tvalid)
            self.input_q_tready <<= ~self._q_valid_reg | (self.output_tready & self.output_tvalid)
            self.output_i_tdata <<= self._i_data_reg
            self.output_q_tdata <<= self._q_data_reg
            self.output_tvalid <<= self._i_valid_reg & self._q_valid_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._i_data_reg <<= 0
                self._q_data_reg <<= 0
                self._i_valid_reg <<= 0
                self._q_valid_reg <<= 0
            with Else():
                with If(self.input_i_tready & self.input_i_tvalid):
                    self._i_data_reg <<= self.input_i_tdata
                    self._i_valid_reg <<= 1
                with Else():
                    with If(self.output_tready & self.output_tvalid):
                        self._i_valid_reg <<= 0
                with If(self.input_q_tready & self.input_q_tvalid):
                    self._q_data_reg <<= self.input_q_tdata
                    self._q_valid_reg <<= 1
                with Else():
                    with If(self.output_tready & self.output_tvalid):
                        self._q_valid_reg <<= 0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/iq_join.v",
            description="IQ joiner: buffers independent I/Q AXI-Stream inputs into synchronized pair.",
            author="rtlgen agent", version="1.0",
            timing="Variable latency: both channels must arrive before output is valid.",
        )
        fill_doc_template(tpl, self)


print("  - IQ_JOIN defined")


# ============================================================================
# Module 3: IQ_SPLIT — Two-Channel AXI-Stream Demultiplexer
# ============================================================================
class IQ_SPLIT(Module):
    """IQ splitter. Takes a synchronized IQ pair and splits into independent
    I and Q AXI-Stream outputs."""

    def __init__(self, width=16):
        super().__init__("iq_split")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_i_tdata = Input(width, "input_i_tdata")
        self.input_q_tdata = Input(width, "input_q_tdata")
        self.input_tvalid = Input(1, "input_tvalid")
        self.input_tready = Output(1, "input_tready")

        self.output_i_tdata = Output(width, "output_i_tdata")
        self.output_i_tvalid = Output(1, "output_i_tvalid")
        self.output_i_tready = Input(1, "output_i_tready")

        self.output_q_tdata = Output(width, "output_q_tdata")
        self.output_q_tvalid = Output(1, "output_q_tvalid")
        self.output_q_tready = Input(1, "output_q_tready")

        self._i_data_reg = Reg(width, "i_data_reg", init_value=0)
        self._q_data_reg = Reg(width, "q_data_reg", init_value=0)
        self._i_valid_reg = Reg(1, "i_valid_reg", init_value=0)
        self._q_valid_reg = Reg(1, "q_valid_reg", init_value=0)

        with self.comb:
            self.input_tready <<= (~self._i_valid_reg | (self.output_i_tready & self.output_i_tvalid)) & \
                                   (~self._q_valid_reg | (self.output_q_tready & self.output_q_tvalid))
            self.output_i_tdata <<= self._i_data_reg
            self.output_i_tvalid <<= self._i_valid_reg
            self.output_q_tdata <<= self._q_data_reg
            self.output_q_tvalid <<= self._q_valid_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._i_data_reg <<= 0
                self._q_data_reg <<= 0
                self._i_valid_reg <<= 0
                self._q_valid_reg <<= 0
            with Else():
                with If(self.input_tready & self.input_tvalid):
                    self._i_data_reg <<= self.input_i_tdata
                    self._q_data_reg <<= self.input_q_tdata
                    self._i_valid_reg <<= 1
                    self._q_valid_reg <<= 1
                with Else():
                    with If(self.output_i_tready & self.output_i_tvalid):
                        self._i_valid_reg <<= 0
                    with If(self.output_q_tready & self.output_q_tvalid):
                        self._q_valid_reg <<= 0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/iq_split.v",
            description="IQ splitter: splits synchronized IQ pair into independent I/Q AXI-Stream outputs.",
            author="rtlgen agent", version="1.0",
            timing="1-cycle latency for each channel after input handshake.",
        )
        fill_doc_template(tpl, self)


print("  - IQ_SPLIT defined")


# ============================================================================
# Module 4: I2S_CTRL — I2S Bus Clock Generator
# ============================================================================
class I2S_CTRL(Module):
    """I2S bus clock generator. Produces serial clock (sck) and word-select
    (ws) from a system clock with a programmable prescaler."""

    def __init__(self, width=16):
        super().__init__("i2s_ctrl")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.sck = Output(1, "sck")
        self.ws = Output(1, "ws")

        self.prescale = Input(16, "prescale")

        # $clog2(WIDTH) bits for ws_cnt
        ws_cnt_width = max(1, (width - 1).bit_length())
        self._prescale_cnt = Reg(16, "prescale_cnt", init_value=0)
        self._ws_cnt = Reg(ws_cnt_width, "ws_cnt", init_value=0)
        self._sck_reg = Reg(1, "sck_reg", init_value=0)
        self._ws_reg = Reg(1, "ws_reg", init_value=0)

        with self.comb:
            self.sck <<= self._sck_reg
            self.ws <<= self._ws_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._prescale_cnt <<= 0
                self._ws_cnt <<= 0
                self._sck_reg <<= 0
                self._ws_reg <<= 0
            with Else():
                with If(self._prescale_cnt > 0):
                    self._prescale_cnt <<= self._prescale_cnt - 1
                with Else():
                    self._prescale_cnt <<= self.prescale
                    with If(self._sck_reg == 1):
                        self._sck_reg <<= 0
                        with If(self._ws_cnt > 0):
                            self._ws_cnt <<= self._ws_cnt - 1
                        with Else():
                            self._ws_cnt <<= width - 1
                            self._ws_reg <<= ~self._ws_reg
                    with Else():
                        self._sck_reg <<= 1

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/i2s_ctrl.v",
            description="I2S bus clock generator with programmable prescaler.",
            author="rtlgen agent", version="1.0",
            timing="Free-running: prescale_cnt divides clk, sck toggles at prescale rate, ws toggles every WIDTH bits.",
        )
        fill_doc_template(tpl, self)


print("  - I2S_CTRL defined")


# ============================================================================
# Module 5: PHASE_ACCUMULATOR — NCO Phase Accumulator
# ============================================================================
class PHASE_ACCUMULATOR(Module):
    """Numerically Controlled Oscillator (NCO) phase accumulator.
    Continuously adds a phase step to produce a phase ramp."""

    def __init__(self, width=32, initial_phase=0, initial_phase_step=0):
        super().__init__("phase_accumulator")
        self.WIDTH = Parameter(width, "WIDTH")
        self.INITIAL_PHASE = Parameter(initial_phase, "INITIAL_PHASE")
        self.INITIAL_PHASE_STEP = Parameter(initial_phase_step, "INITIAL_PHASE_STEP")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_phase_tdata = Input(width, "input_phase_tdata")
        self.input_phase_tvalid = Input(1, "input_phase_tvalid")
        self.input_phase_tready = Output(1, "input_phase_tready")

        self.input_phase_step_tdata = Input(width, "input_phase_step_tdata")
        self.input_phase_step_tvalid = Input(1, "input_phase_step_tvalid")
        self.input_phase_step_tready = Output(1, "input_phase_step_tready")

        self.output_phase_tdata = Output(width, "output_phase_tdata")
        self.output_phase_tvalid = Output(1, "output_phase_tvalid")
        self.output_phase_tready = Input(1, "output_phase_tready")

        self._phase_reg = Reg(width, "phase_reg", init_value=initial_phase)
        self._phase_step_reg = Reg(width, "phase_step_reg", init_value=initial_phase_step)

        with self.comb:
            self.input_phase_tready <<= self.output_phase_tready
            self.input_phase_step_tready <<= 1
            self.output_phase_tdata <<= self._phase_reg
            self.output_phase_tvalid <<= 1

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._phase_reg <<= self.INITIAL_PHASE
                self._phase_step_reg <<= self.INITIAL_PHASE_STEP
            with Else():
                with If(self.input_phase_tready & self.input_phase_tvalid):
                    self._phase_reg <<= self.input_phase_tdata
                with Else():
                    with If(self.output_phase_tready):
                        self._phase_reg <<= self._phase_reg + self._phase_step_reg
                with If(self.input_phase_step_tvalid):
                    self._phase_step_reg <<= self.input_phase_step_tdata

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/phase_accumulator.v",
            description="NCO phase accumulator: continuous phase ramp with programmable step.",
            author="rtlgen agent", version="1.0",
            timing="1-cycle latency: phase updates every cycle when output ready.",
        )
        fill_doc_template(tpl, self)


print("  - PHASE_ACCUMULATOR defined")


# ============================================================================
# Module 6: DSP_IQ_MULT — Complex IQ Multiplier (4-stage pipeline)
# ============================================================================
class DSP_IQ_MULT(Module):
    """Complex (IQ) multiplier computing I×I and Q×Q products.
    Pipelined to map to Xilinx DSP slices."""

    def __init__(self, width=16):
        super().__init__("dsp_iq_mult")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_a_i_tdata = Input(width, "input_a_i_tdata")
        self.input_a_q_tdata = Input(width, "input_a_q_tdata")
        self.input_a_tvalid = Input(1, "input_a_tvalid")
        self.input_a_tready = Output(1, "input_a_tready")

        self.input_b_i_tdata = Input(width, "input_b_i_tdata")
        self.input_b_q_tdata = Input(width, "input_b_q_tdata")
        self.input_b_tvalid = Input(1, "input_b_tvalid")
        self.input_b_tready = Output(1, "input_b_tready")

        self.output_i_tdata = Output(width * 2, "output_i_tdata")
        self.output_q_tdata = Output(width * 2, "output_q_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        self._input_a_i_reg_0 = Reg(width, "input_a_i_reg_0", init_value=0)
        self._input_a_q_reg_0 = Reg(width, "input_a_q_reg_0", init_value=0)
        self._input_a_i_reg_1 = Reg(width, "input_a_i_reg_1", init_value=0)
        self._input_a_q_reg_1 = Reg(width, "input_a_q_reg_1", init_value=0)
        self._input_b_i_reg_0 = Reg(width, "input_b_i_reg_0", init_value=0)
        self._input_b_q_reg_0 = Reg(width, "input_b_q_reg_0", init_value=0)
        self._input_b_i_reg_1 = Reg(width, "input_b_i_reg_1", init_value=0)
        self._input_b_q_reg_1 = Reg(width, "input_b_q_reg_1", init_value=0)
        self._output_i_reg_0 = Reg(width * 2, "output_i_reg_0", init_value=0)
        self._output_q_reg_0 = Reg(width * 2, "output_q_reg_0", init_value=0)
        self._output_i_reg_1 = Reg(width * 2, "output_i_reg_1", init_value=0)
        self._output_q_reg_1 = Reg(width * 2, "output_q_reg_1", init_value=0)

        with self.comb:
            self.input_a_tready <<= self.input_b_tvalid & self.output_tready
            self.input_b_tready <<= self.input_a_tvalid & self.output_tready
            self.output_i_tdata <<= self._output_i_reg_1
            self.output_q_tdata <<= self._output_q_reg_1
            self.output_tvalid <<= self.input_a_tvalid & self.input_b_tvalid

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._input_a_i_reg_0 <<= 0
                self._input_a_q_reg_0 <<= 0
                self._input_a_i_reg_1 <<= 0
                self._input_a_q_reg_1 <<= 0
                self._input_b_i_reg_0 <<= 0
                self._input_b_q_reg_0 <<= 0
                self._input_b_i_reg_1 <<= 0
                self._input_b_q_reg_1 <<= 0
                self._output_i_reg_0 <<= 0
                self._output_q_reg_0 <<= 0
                self._output_i_reg_1 <<= 0
                self._output_q_reg_1 <<= 0
            with Else():
                with If(self.input_a_tvalid & self.input_b_tvalid & self.output_tready):
                    self._input_a_i_reg_0 <<= self.input_a_i_tdata
                    self._input_a_q_reg_0 <<= self.input_a_q_tdata
                    self._input_b_i_reg_0 <<= self.input_b_i_tdata
                    self._input_b_q_reg_0 <<= self.input_b_q_tdata
                    self._input_a_i_reg_1 <<= self._input_a_i_reg_0
                    self._input_a_q_reg_1 <<= self._input_a_q_reg_0
                    self._input_b_i_reg_1 <<= self._input_b_i_reg_0
                    self._input_b_q_reg_1 <<= self._input_b_q_reg_0
                    self._output_i_reg_0 <<= self._input_a_i_reg_1 * self._input_b_i_reg_1
                    self._output_q_reg_0 <<= self._input_a_q_reg_1 * self._input_b_q_reg_1
                    self._output_i_reg_1 <<= self._output_i_reg_0
                    self._output_q_reg_1 <<= self._output_q_reg_0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/dsp_iq_mult.v",
            description="Complex IQ multiplier: computes I×I and Q×Q products with 4-stage pipeline.",
            author="rtlgen agent", version="1.0",
            timing="4-cycle latency: pipelined for DSP slice mapping.",
        )
        fill_doc_template(tpl, self)


print("  - DSP_IQ_MULT defined")


# ============================================================================
# Module 7: I2S_RX — I2S Serial Receiver
# ============================================================================
class I2S_RX(Module):
    """I2S receiver. Captures left/right audio data from serial I2S signals.
    Edge-detects sck rising edges, shifts in MSB-first data."""

    def __init__(self, width=16):
        super().__init__("i2s_rx")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.sck = Input(1, "sck")
        self.ws = Input(1, "ws")
        self.sd = Input(1, "sd")

        self.output_l_tdata = Output(width, "output_l_tdata")
        self.output_r_tdata = Output(width, "output_r_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        self._l_data_reg = Reg(width, "l_data_reg", init_value=0)
        self._r_data_reg = Reg(width, "r_data_reg", init_value=0)
        self._l_data_valid_reg = Reg(1, "l_data_valid_reg", init_value=0)
        self._r_data_valid_reg = Reg(1, "r_data_valid_reg", init_value=0)
        self._sreg = Reg(width, "sreg", init_value=0)

        bit_cnt_width = max(1, (width - 1).bit_length())
        self._bit_cnt = Reg(bit_cnt_width, "bit_cnt", init_value=0)
        self._last_sck = Reg(1, "last_sck", init_value=0)
        self._last_ws = Reg(1, "last_ws", init_value=0)
        self._last_ws2 = Reg(1, "last_ws2", init_value=0)

        with self.comb:
            self.output_l_tdata <<= self._l_data_reg
            self.output_r_tdata <<= self._r_data_reg
            self.output_tvalid <<= self._l_data_valid_reg & self._r_data_valid_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._l_data_reg <<= 0
                self._r_data_reg <<= 0
                self._l_data_valid_reg <<= 0
                self._r_data_valid_reg <<= 0
                self._sreg <<= 0
                self._bit_cnt <<= 0
                self._last_sck <<= 0
                self._last_ws <<= 0
                self._last_ws2 <<= 0
            with Else():
                with If(self.output_tready & self.output_tvalid):
                    self._l_data_valid_reg <<= 0
                    self._r_data_valid_reg <<= 0

                self._last_sck <<= self.sck

                with If(~self._last_sck & self.sck):
                    # rising edge of sck
                    self._last_ws <<= self.ws
                    self._last_ws2 <<= self._last_ws

                    with If(self._last_ws2 != self._last_ws):
                        self._bit_cnt <<= width - 1
                        self._sreg <<= Cat(Const(0, width - 1), self.sd)
                    with Else():
                        with If(self._bit_cnt > 0):
                            self._bit_cnt <<= self._bit_cnt - 1
                            with If(self._bit_cnt > 1):
                                self._sreg <<= Cat(self._sreg[width - 2:0], self.sd)
                            with Else():
                                with If(self._last_ws2):
                                    self._r_data_reg <<= Cat(self._sreg[width - 2:0], self.sd)
                                    self._r_data_valid_reg <<= self._l_data_valid_reg
                                with Else():
                                    self._l_data_reg <<= Cat(self._sreg[width - 2:0], self.sd)
                                    self._l_data_valid_reg <<= 1

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/i2s_rx.v",
            description="I2S receiver: captures left/right audio from serial I2S signals.",
            author="rtlgen agent", version="1.0",
            timing="Edge-detects sck rising edges, MSB-first shift register, 1 sample per word.",
        )
        fill_doc_template(tpl, self)


print("  - I2S_RX defined")


# ============================================================================
# Module 8: I2S_TX — I2S Serial Transmitter
# ============================================================================
class I2S_TX(Module):
    """I2S transmitter. Converts parallel left/right audio samples to serial
    I2S stream. Dual-edge logic on sck for bit-stuffing."""

    def __init__(self, width=16):
        super().__init__("i2s_tx")
        self.WIDTH = Parameter(width, "WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_l_tdata = Input(width, "input_l_tdata")
        self.input_r_tdata = Input(width, "input_r_tdata")
        self.input_tvalid = Input(1, "input_tvalid")
        self.input_tready = Output(1, "input_tready")

        self.sck = Input(1, "sck")
        self.ws = Input(1, "ws")
        self.sd = Output(1, "sd")

        self._l_data_reg = Reg(width, "l_data_reg", init_value=0)
        self._r_data_reg = Reg(width, "r_data_reg", init_value=0)
        self._l_data_valid_reg = Reg(1, "l_data_valid_reg", init_value=0)
        self._r_data_valid_reg = Reg(1, "r_data_valid_reg", init_value=0)
        self._sreg = Reg(width, "sreg", init_value=0)

        bit_cnt_width = max(1, (width).bit_length())
        self._bit_cnt = Reg(bit_cnt_width, "bit_cnt", init_value=0)
        self._last_sck = Reg(1, "last_sck", init_value=0)
        self._last_ws = Reg(1, "last_ws", init_value=0)
        self._sd_reg = Reg(1, "sd_reg", init_value=0)

        with self.comb:
            self.input_tready <<= ~self._l_data_valid_reg & ~self._r_data_valid_reg
            self.sd <<= self._sd_reg

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._l_data_reg <<= 0
                self._r_data_reg <<= 0
                self._l_data_valid_reg <<= 0
                self._r_data_valid_reg <<= 0
                self._sreg <<= 0
                self._bit_cnt <<= 0
                self._last_sck <<= 0
                self._last_ws <<= 0
                self._sd_reg <<= 0
            with Else():
                with If(self.input_tready & self.input_tvalid):
                    self._l_data_reg <<= self.input_l_tdata
                    self._r_data_reg <<= self.input_r_tdata
                    self._l_data_valid_reg <<= 1
                    self._r_data_valid_reg <<= 1

                self._last_sck <<= self.sck

                with If(~self._last_sck & self.sck):
                    # rising edge of sck
                    self._last_ws <<= self.ws
                    with If(self._last_ws != self.ws):
                        self._bit_cnt <<= width
                        with If(self.ws):
                            self._sreg <<= self._r_data_reg
                            self._r_data_valid_reg <<= 0
                        with Else():
                            self._sreg <<= self._l_data_reg
                            self._l_data_valid_reg <<= 0

                with If(self._last_sck & ~self.sck):
                    # falling edge of sck
                    with If(self._bit_cnt > 0):
                        self._bit_cnt <<= self._bit_cnt - 1
                        self._sd_reg <<= self._sreg[width - 1]
                        self._sreg <<= Cat(self._sreg[width - 2:0], Const(0, 1))

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/i2s_tx.v",
            description="I2S transmitter: converts parallel L/R samples to serial I2S stream.",
            author="rtlgen agent", version="1.0",
            timing="Dual-edge sck logic: rising loads new word, falling shifts out MSB.",
        )
        fill_doc_template(tpl, self)


print("  - I2S_TX defined")


# ============================================================================
# Module 9: SINE_DDS_LUT — Sine/Cosine LUT with Fine/Coarse Decomposition
# ============================================================================
class SINE_DDS_LUT(Module):
    """Pipelined sine/cosine lookup table with fine/coarse angle decomposition.
    Implements angle-addition identity to reduce ROM size:
        sin(A+B) = sin(A) + cos(A)*sin(B)
        cos(A+B) = cos(A) - sin(A)*sin(B)
    """

    def __init__(self, output_width=16, input_width=None):
        if input_width is None:
            input_width = output_width + 2
        super().__init__("sine_dds_lut")
        self.OUTPUT_WIDTH = Parameter(output_width, "OUTPUT_WIDTH")
        self.INPUT_WIDTH = Parameter(input_width, "INPUT_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_phase_tdata = Input(input_width, "input_phase_tdata")
        self.input_phase_tvalid = Input(1, "input_phase_tvalid")
        self.input_phase_tready = Output(1, "input_phase_tready")

        self.output_sample_i_tdata = Output(output_width, "output_sample_i_tdata")
        self.output_sample_q_tdata = Output(output_width, "output_sample_q_tdata")
        self.output_sample_tvalid = Output(1, "output_sample_tvalid")
        self.output_sample_tready = Input(1, "output_sample_tready")

        # W = (INPUT_WIDTH - 2) // 2
        W = (input_width - 2) // 2
        coarse_size = 2 ** (W + 1)
        fine_size = 2 ** W
        scale = (2 ** (output_width - 1)) - 1
        pi = 3.1415926535

        # Coarse cosine and sine LUTs
        coarse_c_init = []
        coarse_s_init = []
        for i in range(coarse_size):
            cval = int(round(math.cos(2 * pi * i / (2 ** (W + 2))) * scale))
            sval = int(round(math.sin(2 * pi * i / (2 ** (W + 2))) * scale))
            # Saturate to output_width signed range
            cval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, cval))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            coarse_c_init.append(cval & ((1 << output_width) - 1))
            coarse_s_init.append(sval & ((1 << output_width) - 1))

        # Fine sine LUT
        fine_s_init = []
        half_fine = 2 ** (W - 1)
        for i in range(fine_size):
            sval = int(round(math.sin(2 * pi * (i - half_fine) / (2 ** input_width)) * scale))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            fine_s_init.append(sval & ((1 << output_width) - 1))

        self._coarse_c_lut = Memory(output_width, coarse_size, "coarse_c_lut", init_data=coarse_c_init)
        self._coarse_s_lut = Memory(output_width, coarse_size, "coarse_s_lut", init_data=coarse_s_init)
        self._fine_s_lut = Memory(output_width, fine_size, "fine_s_lut", init_data=fine_s_init)

        # Pipeline registers
        self._phase_reg = Reg(input_width, "phase_reg", init_value=0)
        self._sample_i_reg = Reg(output_width, "sample_i_reg", init_value=0)
        self._sample_q_reg = Reg(output_width, "sample_q_reg", init_value=0)

        # Stage 1 → 2 pipeline
        self._sign_reg_1 = Reg(1, "sign_reg_1", init_value=0)
        self._sign_reg_2 = Reg(1, "sign_reg_2", init_value=0)
        self._sign_reg_3 = Reg(1, "sign_reg_3", init_value=0)
        self._sign_reg_4 = Reg(1, "sign_reg_4", init_value=0)

        half_out = output_width // 2
        self._ccs_reg_1 = Reg(output_width, "ccs_reg_1", init_value=0)
        self._ccs_reg_2 = Reg(output_width, "ccs_reg_2", init_value=0)
        self._ccs_reg_3 = Reg(output_width, "ccs_reg_3", init_value=0)
        self._css_reg_1 = Reg(output_width, "css_reg_1", init_value=0)
        self._css_reg_2 = Reg(output_width, "css_reg_2", init_value=0)
        self._css_reg_3 = Reg(output_width, "css_reg_3", init_value=0)
        self._fss_reg_1 = Reg(half_out, "fss_reg_1", init_value=0)
        self._fss_reg_2 = Reg(half_out, "fss_reg_2", init_value=0)

        self._cp_reg_1 = Reg(output_width * 2, "cp_reg_1", init_value=0)
        self._sp_reg_1 = Reg(output_width * 2, "sp_reg_1", init_value=0)

        self._cs_reg_1 = Reg(output_width, "cs_reg_1", init_value=0)
        self._ss_reg_1 = Reg(output_width, "ss_reg_1", init_value=0)

        # Extract phase fields
        # SIGN = phase_reg[INPUT_WIDTH-1]
        # SLOPE = phase_reg[INPUT_WIDTH-2]
        # A = phase_reg[INPUT_WIDTH-2 : W]  (W+1 bits)
        # B = phase_reg[W-1 : 0] (W bits)
        self._SIGN = Wire(1, "SIGN")
        self._A = Wire(W + 1, "A")
        self._B = Wire(W, "B")

        with self.comb:
            self.input_phase_tready <<= self.output_sample_tready
            self.output_sample_i_tdata <<= self._sample_i_reg
            self.output_sample_q_tdata <<= self._sample_q_reg
            self.output_sample_tvalid <<= self.input_phase_tvalid
            self._SIGN <<= self._phase_reg[input_width - 1]
            self._A <<= self._phase_reg[input_width - 2:W]
            self._B <<= self._phase_reg[W - 1:0] if W > 0 else Const(0, 1)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._phase_reg <<= 0
            with Else():
                with If(self.input_phase_tready & self.input_phase_tvalid):
                    self._phase_reg <<= self.input_phase_tdata

            # All pipeline stages gated by input handshake
            with If(self.input_phase_tready & self.input_phase_tvalid):
                # Stage 1: read LUTs
                self._sign_reg_1 <<= self._SIGN
                self._ccs_reg_1 <<= self._coarse_c_lut[self._A]
                self._css_reg_1 <<= self._coarse_s_lut[self._A]
                self._fss_reg_1 <<= self._fine_s_lut[self._B]

                # Stage 2: pipeline
                self._sign_reg_2 <<= self._sign_reg_1
                self._ccs_reg_2 <<= self._ccs_reg_1
                self._css_reg_2 <<= self._css_reg_1
                self._fss_reg_2 <<= self._fss_reg_1

                # Stage 3: multiply
                self._sign_reg_3 <<= self._sign_reg_2
                self._ccs_reg_3 <<= self._ccs_reg_2
                self._css_reg_3 <<= self._css_reg_2
                self._cp_reg_1 <<= self._css_reg_2 * self._fss_reg_2
                self._sp_reg_1 <<= self._ccs_reg_2 * self._fss_reg_2

                # Stage 4: add/subtract with shift
                self._sign_reg_4 <<= self._sign_reg_3
                # (OUTPUT_WIDTH-1) bit right shift
                shift_amt = output_width - 1
                self._cs_reg_1 <<= self._ccs_reg_3 - (self._cp_reg_1 >> shift_amt)
                self._ss_reg_1 <<= self._css_reg_3 + (self._sp_reg_1 >> shift_amt)

                # Stage 5: sign correction
                self._sample_i_reg <<= Mux(self._sign_reg_4, -self._cs_reg_1, self._cs_reg_1)
                self._sample_q_reg <<= Mux(self._sign_reg_4, -self._ss_reg_1, self._ss_reg_1)

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/sine_dds_lut.v",
            description="Pipelined sine/cosine LUT with fine/coarse angle decomposition.",
            author="rtlgen agent", version="1.0",
            timing="5-stage pipeline: LUT read → pipeline → multiply → add/sub → sign correction.",
        )
        fill_doc_template(tpl, self)


print("  - SINE_DDS_LUT defined")


# ============================================================================
# Module 10: SINE_DDS — Top-Level Direct Digital Synthesizer
# ============================================================================
class SINE_DDS(Module):
    """Top-level DDS. Instantiates phase_accumulator and sine_dds_lut."""

    def __init__(self, phase_width=32, output_width=16, initial_phase=0, initial_phase_step=0):
        super().__init__("sine_dds")
        self.PHASE_WIDTH = Parameter(phase_width, "PHASE_WIDTH")
        self.OUTPUT_WIDTH = Parameter(output_width, "OUTPUT_WIDTH")
        self.INITIAL_PHASE = Parameter(initial_phase, "INITIAL_PHASE")
        self.INITIAL_PHASE_STEP = Parameter(initial_phase_step, "INITIAL_PHASE_STEP")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_phase_tdata = Input(phase_width, "input_phase_tdata")
        self.input_phase_tvalid = Input(1, "input_phase_tvalid")
        self.input_phase_tready = Output(1, "input_phase_tready")

        self.input_phase_step_tdata = Input(phase_width, "input_phase_step_tdata")
        self.input_phase_step_tvalid = Input(1, "input_phase_step_tvalid")
        self.input_phase_step_tready = Output(1, "input_phase_step_tready")

        self.output_sample_i_tdata = Output(output_width, "output_sample_i_tdata")
        self.output_sample_q_tdata = Output(output_width, "output_sample_q_tdata")
        self.output_sample_tvalid = Output(1, "output_sample_tvalid")
        self.output_sample_tready = Input(1, "output_sample_tready")

        # Internal wires for connecting phase_accumulator to sine_dds_lut
        self._phase_tdata = Wire(phase_width, "phase_tdata")
        self._phase_tvalid = Wire(1, "phase_tvalid")
        self._phase_tready = Wire(1, "phase_tready")

        # Internal phase accumulator instance
        pa = PHASE_ACCUMULATOR(
            width=phase_width,
            initial_phase=initial_phase,
            initial_phase_step=initial_phase_step,
        )
        self.instantiate(pa, "phase_accumulator_inst", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "input_phase_tdata": self.input_phase_tdata,
            "input_phase_tvalid": self.input_phase_tvalid,
            "input_phase_tready": self.input_phase_tready,
            "input_phase_step_tdata": self.input_phase_step_tdata,
            "input_phase_step_tvalid": self.input_phase_step_tvalid,
            "input_phase_step_tready": self.input_phase_step_tready,
            "output_phase_tdata": self._phase_tdata,
            "output_phase_tvalid": self._phase_tvalid,
            "output_phase_tready": self._phase_tready,
        })

        # LUT instance
        lut_input_width = output_width + 2
        lut = SINE_DDS_LUT(output_width=output_width, input_width=lut_input_width)
        self.instantiate(lut, "sine_dds_lut_inst", port_map={
            "clk": self.clk,
            "rst": self.rst,
            "input_phase_tdata": self._phase_tdata[phase_width - 1:phase_width - lut_input_width],
            "input_phase_tvalid": self._phase_tvalid,
            "input_phase_tready": self._phase_tready,
            "output_sample_i_tdata": self.output_sample_i_tdata,
            "output_sample_q_tdata": self.output_sample_q_tdata,
            "output_sample_tvalid": self.output_sample_tvalid,
            "output_sample_tready": self.output_sample_tready,
        })

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/sine_dds.v",
            description="Top-level DDS: phase_accumulator + sine_dds_lut for I/Q sine/cosine generation.",
            author="rtlgen agent", version="1.0",
            timing="Phase accumulator free-running, LUT adds 5-cycle pipeline latency.",
        )
        fill_doc_template(tpl, self)


print("  - SINE_DDS defined")


# ============================================================================
# Module 11: CIC_DECIMATOR — Cascaded Integrator-Comb Decimator
# ============================================================================
class CIC_DECIMATOR(Module):
    """CIC decimator for sample-rate reduction.
    N integrator stages → programmable decimator → N comb stages.
    Uses generate loops for parameterizable N and M.
    """

    def __init__(self, width=16, rmax=2, m=1, n=2):
        super().__init__("cic_decimator")
        self.WIDTH = Parameter(width, "WIDTH")
        self.RMAX = Parameter(rmax, "RMAX")
        self.M = Parameter(m, "M")
        self.N = Parameter(n, "N")
        # REG_WIDTH = WIDTH + $clog2((RMAX*M)**N)
        reg_width = width + ((rmax * m) ** n - 1).bit_length()
        self.REG_WIDTH = Parameter(reg_width, "REG_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_tdata = Input(width, "input_tdata")
        self.input_tvalid = Input(1, "input_tvalid")
        self.input_tready = Output(1, "input_tready")

        self.output_tdata = Output(reg_width, "output_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        rate_width = max(1, rmax.bit_length())
        self.rate = Input(rate_width, "rate")

        self._cycle_reg = Reg(rate_width, "cycle_reg", init_value=0)

        # Integrator registers (N stages)
        self._int_regs = []
        for k in range(n):
            self._int_regs.append(Reg(reg_width, f"int_reg_{k}", init_value=0))

        # Comb registers (N stages) and delay registers (M per stage)
        self._comb_regs = []
        self._delay_regs = []
        for k in range(n):
            self._comb_regs.append(Reg(reg_width, f"comb_reg_{k}", init_value=0))
            stage_delays = []
            for i in range(m):
                stage_delays.append(Reg(reg_width, f"delay_reg_{k}_{i}", init_value=0))
            self._delay_regs.append(stage_delays)

        with self.comb:
            self.input_tready <<= self.output_tready | (self._cycle_reg != 0)
            self.output_tdata <<= self._comb_regs[n - 1]
            self.output_tvalid <<= self.input_tvalid & (self._cycle_reg == 0)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._cycle_reg <<= 0
                for k in range(n):
                    self._int_regs[k] <<= 0
                    self._comb_regs[k] <<= 0
                    for i in range(m):
                        self._delay_regs[k][i] <<= 0
            with Else():
                # Integrator stages: update on input handshake
                with If(self.input_tready & self.input_tvalid):
                    for k in range(n):
                        if k == 0:
                            self._int_regs[k] <<= self._int_regs[k] + self.input_tdata
                        else:
                            self._int_regs[k] <<= self._int_regs[k] + self._int_regs[k - 1]

                # Comb stages: update on output handshake
                with If(self.output_tready & self.output_tvalid):
                    for k in range(n):
                        if k == 0:
                            self._delay_regs[k][0] <<= self._int_regs[n - 1]
                            self._comb_regs[k] <<= self._int_regs[n - 1] - self._delay_regs[k][m - 1]
                        else:
                            self._delay_regs[k][0] <<= self._comb_regs[k - 1]
                            self._comb_regs[k] <<= self._comb_regs[k - 1] - self._delay_regs[k][m - 1]
                        for i in range(m - 1):
                            self._delay_regs[k][i + 1] <<= self._delay_regs[k][i]

                # Cycle counter
                with If(self.input_tready & self.input_tvalid):
                    with If((self._cycle_reg < (self.RMAX - 1)) & (self._cycle_reg < (self.rate - 1))):
                        self._cycle_reg <<= self._cycle_reg + 1
                    with Else():
                        self._cycle_reg <<= 0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/cic_decimator.v",
            description="CIC decimator: N integrator stages + programmable decimator + N comb stages.",
            author="rtlgen agent", version="1.0",
            timing="Variable latency: output valid every R cycles where R is the decimation ratio.",
        )
        fill_doc_template(tpl, self)


print("  - CIC_DECIMATOR defined")


# ============================================================================
# Module 12: CIC_INTERPOLATOR — Cascaded Integrator-Comb Interpolator
# ============================================================================
class CIC_INTERPOLATOR(Module):
    """CIC interpolator for sample-rate increase.
    N comb stages → programmable up-converter → N integrator stages.
    """

    def __init__(self, width=16, rmax=2, m=1, n=2):
        super().__init__("cic_interpolator")
        self.WIDTH = Parameter(width, "WIDTH")
        self.RMAX = Parameter(rmax, "RMAX")
        self.M = Parameter(m, "M")
        self.N = Parameter(n, "N")
        # REG_WIDTH = WIDTH + $max(N, $clog2(((RMAX*M)**N)/RMAX))
        gain_bits = ((rmax * m) ** n // rmax - 1).bit_length() if rmax > 0 else 0
        reg_width = width + max(n, gain_bits)
        self.REG_WIDTH = Parameter(reg_width, "REG_WIDTH")

        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")

        self.input_tdata = Input(width, "input_tdata")
        self.input_tvalid = Input(1, "input_tvalid")
        self.input_tready = Output(1, "input_tready")

        self.output_tdata = Output(reg_width, "output_tdata")
        self.output_tvalid = Output(1, "output_tvalid")
        self.output_tready = Input(1, "output_tready")

        rate_width = max(1, rmax.bit_length())
        self.rate = Input(rate_width, "rate")

        self._cycle_reg = Reg(rate_width, "cycle_reg", init_value=0)

        # Comb registers (N stages) and delay registers (M per stage)
        self._comb_regs = []
        self._delay_regs = []
        for k in range(n):
            self._comb_regs.append(Reg(reg_width, f"comb_reg_{k}", init_value=0))
            stage_delays = []
            for i in range(m):
                stage_delays.append(Reg(reg_width, f"delay_reg_{k}_{i}", init_value=0))
            self._delay_regs.append(stage_delays)

        # Integrator registers (N stages)
        self._int_regs = []
        for k in range(n):
            self._int_regs.append(Reg(reg_width, f"int_reg_{k}", init_value=0))

        with self.comb:
            self.input_tready <<= self.output_tready & (self._cycle_reg == 0)
            self.output_tdata <<= self._int_regs[n - 1]
            self.output_tvalid <<= self.input_tvalid | (self._cycle_reg != 0)

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._cycle_reg <<= 0
                for k in range(n):
                    self._comb_regs[k] <<= 0
                    self._int_regs[k] <<= 0
                    for i in range(m):
                        self._delay_regs[k][i] <<= 0
            with Else():
                # Comb stages: update on input handshake
                with If(self.input_tready & self.input_tvalid):
                    for k in range(n):
                        if k == 0:
                            self._delay_regs[k][0] <<= self.input_tdata
                            self._comb_regs[k] <<= self.input_tdata - self._delay_regs[k][m - 1]
                        else:
                            self._delay_regs[k][0] <<= self._comb_regs[k - 1]
                            self._comb_regs[k] <<= self._comb_regs[k - 1] - self._delay_regs[k][m - 1]
                        for i in range(m - 1):
                            self._delay_regs[k][i + 1] <<= self._delay_regs[k][i]

                # Integrator stages: update on output handshake
                with If(self.output_tready & self.output_tvalid):
                    for k in range(n):
                        if k == 0:
                            with If(self._cycle_reg == 0):
                                self._int_regs[k] <<= self._int_regs[k] + self._comb_regs[n - 1]
                        else:
                            self._int_regs[k] <<= self._int_regs[k] + self._int_regs[k - 1]

                # Cycle counter
                with If(self.output_tready & self.output_tvalid):
                    with If((self._cycle_reg < (self.RMAX - 1)) & (self._cycle_reg < (self.rate - 1))):
                        self._cycle_reg <<= self._cycle_reg + 1
                    with Else():
                        self._cycle_reg <<= 0

        tpl = ModuleDocTemplate(
            source="ref_rtl/dsp/rtl/cic_interpolator.v",
            description="CIC interpolator: N comb stages + programmable up-converter + N integrator stages.",
            author="rtlgen agent", version="1.0",
            timing="Output valid every cycle; comb input updated at input sample rate.",
        )
        fill_doc_template(tpl, self)
