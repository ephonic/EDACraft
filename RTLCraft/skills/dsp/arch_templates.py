"""
skills.dsp.arch_templates — DSP Architecture Templates

Builds ArchDefinition for a DSP suite with 12 processing elements:
  DSP_MULT, IQ_JOIN, IQ_SPLIT, I2S_CTRL, PHASE_ACCUMULATOR,
  DSP_IQ_MULT, I2S_RX, I2S_TX, SINE_DDS_LUT, SINE_DDS,
  CIC_DECIMATOR, CIC_INTERPOLATOR

Usage:
    from skills.dsp.arch_templates import build_dsp_arch
    arch = build_dsp_arch()
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    InterconnectSpec, ArchDefinition, Algorithm_Model,
)
from rtlgen.behaviors import TemplateRegistry

# Import behaviors to register DSP templates in TemplateRegistry
import skills.dsp.behaviors  # noqa: F401


def build_dsp_arch(
    mult_width: int = 16,
    phase_width: int = 32,
    cic_width: int = 16,
    cic_rmax: int = 2,
    cic_m: int = 1,
    cic_n: int = 2,
    dds_output_width: int = 16,
    i2s_width: int = 16,
) -> ArchDefinition:
    """Build ArchDefinition for DSP suite.

    Args:
        mult_width: Multiplier data width (default 16)
        phase_width: Phase accumulator width (default 32)
        cic_width: CIC filter data width (default 16)
        cic_rmax: CIC max decimation ratio (default 2)
        cic_m: CIC differential delay (default 1)
        cic_n: CIC filter order (default 2)
        dds_output_width: DDS output sample width (default 16)
        i2s_width: I2S audio sample width (default 16)
    """
    # 1. DSP_MULT — 4-stage pipelined signed multiplier
    dsp_mult_pe = ProcessingElement(
        name="DSP_MULT", pe_type="dsp_mult",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_a_tdata", "input", mult_width),
            PortDesc("input_a_tvalid", "input", 1),
            PortDesc("input_b_tdata", "input", mult_width),
            PortDesc("input_b_tvalid", "input", 1),
            PortDesc("output_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_a_tready", "output", 1),
            PortDesc("input_b_tready", "output", 1),
            PortDesc("output_tdata", "output", mult_width * 2),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("input_a_reg_0", "int", "Input A stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_a_reg_1", "int", "Input A stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_reg_0", "int", "Input B stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_reg_1", "int", "Input B stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("output_reg_0", "int", "Output stage 0", rtl_type="reg", rtl_width=mult_width * 2),
            StateDesc("output_reg_1", "int", "Output stage 1", rtl_type="reg", rtl_width=mult_width * 2),
        ],
        behavior=TemplateRegistry.get("dsp_mult"),
        can_stall=False, latency=4,
    )

    # 2. IQ_JOIN — Two-channel AXI-Stream synchronizer
    iq_join_pe = ProcessingElement(
        name="IQ_JOIN", pe_type="iq_join",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_i_tdata", "input", mult_width),
            PortDesc("input_i_tvalid", "input", 1),
            PortDesc("input_q_tdata", "input", mult_width),
            PortDesc("input_q_tvalid", "input", 1),
            PortDesc("output_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_i_tready", "output", 1),
            PortDesc("input_q_tready", "output", 1),
            PortDesc("output_i_tdata", "output", mult_width),
            PortDesc("output_q_tdata", "output", mult_width),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("i_data_reg", "int", "I channel buffer", rtl_type="reg", rtl_width=mult_width),
            StateDesc("q_data_reg", "int", "Q channel buffer", rtl_type="reg", rtl_width=mult_width),
            StateDesc("i_valid_reg", "int", "I valid flag", rtl_type="reg", rtl_width=1),
            StateDesc("q_valid_reg", "int", "Q valid flag", rtl_type="reg", rtl_width=1),
        ],
        behavior=TemplateRegistry.get("iq_join"),
        can_stall=False, latency=1,
    )

    # 3. IQ_SPLIT — Two-channel AXI-Stream demultiplexer
    iq_split_pe = ProcessingElement(
        name="IQ_SPLIT", pe_type="iq_split",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_i_tdata", "input", mult_width),
            PortDesc("input_q_tdata", "input", mult_width),
            PortDesc("input_tvalid", "input", 1),
            PortDesc("output_i_tready", "input", 1),
            PortDesc("output_q_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_tready", "output", 1),
            PortDesc("output_i_tdata", "output", mult_width),
            PortDesc("output_i_tvalid", "output", 1),
            PortDesc("output_q_tdata", "output", mult_width),
            PortDesc("output_q_tvalid", "output", 1),
        ],
        state=[
            StateDesc("i_data_reg", "int", "I channel buffer", rtl_type="reg", rtl_width=mult_width),
            StateDesc("q_data_reg", "int", "Q channel buffer", rtl_type="reg", rtl_width=mult_width),
            StateDesc("i_valid_reg", "int", "I valid flag", rtl_type="reg", rtl_width=1),
            StateDesc("q_valid_reg", "int", "Q valid flag", rtl_type="reg", rtl_width=1),
        ],
        behavior=TemplateRegistry.get("iq_split"),
        can_stall=False, latency=1,
    )

    # 4. I2S_CTRL — I2S bus clock generator
    i2s_ctrl_pe = ProcessingElement(
        name="I2S_CTRL", pe_type="i2s_ctrl",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("prescale", "input", 16),
        ],
        outputs=[
            PortDesc("sck", "output", 1),
            PortDesc("ws", "output", 1),
        ],
        state=[
            StateDesc("prescale_cnt", "int", "Prescaler counter", rtl_type="reg", rtl_width=16),
            StateDesc("ws_cnt", "int", "Word select counter", rtl_type="reg", rtl_width=max(1, (i2s_width - 1).bit_length())),
            StateDesc("sck_reg", "int", "Serial clock", rtl_type="reg", rtl_width=1),
            StateDesc("ws_reg", "int", "Word select", rtl_type="reg", rtl_width=1),
        ],
        behavior=TemplateRegistry.get("i2s_ctrl"),
        can_stall=False, latency=1,
    )

    # 5. PHASE_ACCUMULATOR — NCO phase accumulator
    phase_acc_pe = ProcessingElement(
        name="PHASE_ACCUMULATOR", pe_type="phase_accumulator",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_phase_tdata", "input", phase_width),
            PortDesc("input_phase_tvalid", "input", 1),
            PortDesc("input_phase_step_tdata", "input", phase_width),
            PortDesc("input_phase_step_tvalid", "input", 1),
            PortDesc("output_phase_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_phase_tready", "output", 1),
            PortDesc("input_phase_step_tready", "output", 1),
            PortDesc("output_phase_tdata", "output", phase_width),
            PortDesc("output_phase_tvalid", "output", 1),
        ],
        state=[
            StateDesc("phase_reg", "int", "Phase accumulator", rtl_type="reg", rtl_width=phase_width),
            StateDesc("phase_step_reg", "int", "Phase step", rtl_type="reg", rtl_width=phase_width),
        ],
        behavior=TemplateRegistry.get("phase_accumulator"),
        can_stall=False, latency=1,
    )

    # 6. DSP_IQ_MULT — Complex IQ multiplier
    dsp_iq_mult_pe = ProcessingElement(
        name="DSP_IQ_MULT", pe_type="dsp_iq_mult",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_a_i_tdata", "input", mult_width),
            PortDesc("input_a_q_tdata", "input", mult_width),
            PortDesc("input_a_tvalid", "input", 1),
            PortDesc("input_b_i_tdata", "input", mult_width),
            PortDesc("input_b_q_tdata", "input", mult_width),
            PortDesc("input_b_tvalid", "input", 1),
            PortDesc("output_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_a_tready", "output", 1),
            PortDesc("input_b_tready", "output", 1),
            PortDesc("output_i_tdata", "output", mult_width * 2),
            PortDesc("output_q_tdata", "output", mult_width * 2),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("input_a_i_reg_0", "int", "A_I stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_a_q_reg_0", "int", "A_Q stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_a_i_reg_1", "int", "A_I stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_a_q_reg_1", "int", "A_Q stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_i_reg_0", "int", "B_I stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_q_reg_0", "int", "B_Q stage 0", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_i_reg_1", "int", "B_I stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("input_b_q_reg_1", "int", "B_Q stage 1", rtl_type="reg", rtl_width=mult_width),
            StateDesc("output_i_reg_0", "int", "Output I stage 0", rtl_type="reg", rtl_width=mult_width * 2),
            StateDesc("output_q_reg_0", "int", "Output Q stage 0", rtl_type="reg", rtl_width=mult_width * 2),
            StateDesc("output_i_reg_1", "int", "Output I stage 1", rtl_type="reg", rtl_width=mult_width * 2),
            StateDesc("output_q_reg_1", "int", "Output Q stage 1", rtl_type="reg", rtl_width=mult_width * 2),
        ],
        behavior=TemplateRegistry.get("dsp_iq_mult"),
        can_stall=False, latency=4,
    )

    # 7. I2S_RX — I2S serial receiver
    i2s_rx_pe = ProcessingElement(
        name="I2S_RX", pe_type="i2s_rx",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("sck", "input", 1),
            PortDesc("ws", "input", 1),
            PortDesc("sd", "input", 1),
            PortDesc("output_tready", "input", 1),
        ],
        outputs=[
            PortDesc("output_l_tdata", "output", i2s_width),
            PortDesc("output_r_tdata", "output", i2s_width),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("l_data_reg", "int", "Left channel data", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("r_data_reg", "int", "Right channel data", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("l_data_valid_reg", "int", "Left valid", rtl_type="reg", rtl_width=1),
            StateDesc("r_data_valid_reg", "int", "Right valid", rtl_type="reg", rtl_width=1),
            StateDesc("sreg", "int", "Shift register", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("bit_cnt", "int", "Bit counter", rtl_type="reg", rtl_width=max(1, (i2s_width - 1).bit_length())),
            StateDesc("last_sck", "int", "SCK delay", rtl_type="reg", rtl_width=1),
            StateDesc("last_ws", "int", "WS delay", rtl_type="reg", rtl_width=1),
            StateDesc("last_ws2", "int", "WS delay 2", rtl_type="reg", rtl_width=1),
        ],
        behavior=TemplateRegistry.get("i2s_rx"),
        can_stall=False, latency=1,
    )

    # 8. I2S_TX — I2S serial transmitter
    i2s_tx_pe = ProcessingElement(
        name="I2S_TX", pe_type="i2s_tx",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_l_tdata", "input", i2s_width),
            PortDesc("input_r_tdata", "input", i2s_width),
            PortDesc("input_tvalid", "input", 1),
            PortDesc("sck", "input", 1),
            PortDesc("ws", "input", 1),
        ],
        outputs=[
            PortDesc("input_tready", "output", 1),
            PortDesc("sd", "output", 1),
        ],
        state=[
            StateDesc("l_data_reg", "int", "Left channel data", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("r_data_reg", "int", "Right channel data", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("l_data_valid_reg", "int", "Left valid", rtl_type="reg", rtl_width=1),
            StateDesc("r_data_valid_reg", "int", "Right valid", rtl_type="reg", rtl_width=1),
            StateDesc("sreg", "int", "Shift register", rtl_type="reg", rtl_width=i2s_width),
            StateDesc("bit_cnt", "int", "Bit counter", rtl_type="reg", rtl_width=max(1, i2s_width.bit_length())),
            StateDesc("last_sck", "int", "SCK delay", rtl_type="reg", rtl_width=1),
            StateDesc("last_ws", "int", "WS delay", rtl_type="reg", rtl_width=1),
            StateDesc("sd_reg", "int", "Serial data output", rtl_type="reg", rtl_width=1),
        ],
        behavior=TemplateRegistry.get("i2s_tx"),
        can_stall=False, latency=1,
    )

    # 9. SINE_DDS_LUT — Sine/cosine LUT
    lut_input_width = dds_output_width + 2
    sine_dds_lut_pe = ProcessingElement(
        name="SINE_DDS_LUT", pe_type="sine_dds_lut",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_phase_tdata", "input", lut_input_width),
            PortDesc("input_phase_tvalid", "input", 1),
            PortDesc("output_sample_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_phase_tready", "output", 1),
            PortDesc("output_sample_i_tdata", "output", dds_output_width),
            PortDesc("output_sample_q_tdata", "output", dds_output_width),
            PortDesc("output_sample_tvalid", "output", 1),
        ],
        state=[
            StateDesc("phase_reg", "int", "Phase register", rtl_type="reg", rtl_width=lut_input_width),
            StateDesc("sign_reg_1", "int", "Sign pipeline 1", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_2", "int", "Sign pipeline 2", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_3", "int", "Sign pipeline 3", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_4", "int", "Sign pipeline 4", rtl_type="reg", rtl_width=1),
            StateDesc("ccs_reg_1", "int", "Coarse cos pipeline 1", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ccs_reg_2", "int", "Coarse cos pipeline 2", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ccs_reg_3", "int", "Coarse cos pipeline 3", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_1", "int", "Coarse sin pipeline 1", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_2", "int", "Coarse sin pipeline 2", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_3", "int", "Coarse sin pipeline 3", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("fss_reg_1", "int", "Fine sin pipeline 1", rtl_type="reg", rtl_width=dds_output_width // 2),
            StateDesc("fss_reg_2", "int", "Fine sin pipeline 2", rtl_type="reg", rtl_width=dds_output_width // 2),
            StateDesc("cp_reg_1", "int", "Cos*fine product", rtl_type="reg", rtl_width=dds_output_width * 2),
            StateDesc("sp_reg_1", "int", "Sin*fine product", rtl_type="reg", rtl_width=dds_output_width * 2),
            StateDesc("cs_reg_1", "int", "Cosine result", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ss_reg_1", "int", "Sine result", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("sample_i_reg", "int", "I sample output", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("sample_q_reg", "int", "Q sample output", rtl_type="reg", rtl_width=dds_output_width),
        ],
        behavior=TemplateRegistry.get("sine_dds_lut"),
        can_stall=False, latency=5,
    )

    # 10. SINE_DDS — Top-level DDS
    sine_dds_pe = ProcessingElement(
        name="SINE_DDS", pe_type="sine_dds",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_phase_tdata", "input", phase_width),
            PortDesc("input_phase_tvalid", "input", 1),
            PortDesc("input_phase_step_tdata", "input", phase_width),
            PortDesc("input_phase_step_tvalid", "input", 1),
            PortDesc("output_sample_tready", "input", 1),
        ],
        outputs=[
            PortDesc("input_phase_tready", "output", 1),
            PortDesc("input_phase_step_tready", "output", 1),
            PortDesc("output_sample_i_tdata", "output", dds_output_width),
            PortDesc("output_sample_q_tdata", "output", dds_output_width),
            PortDesc("output_sample_tvalid", "output", 1),
        ],
        state=[
            StateDesc("phase_reg", "int", "Phase accumulator", rtl_type="reg", rtl_width=phase_width),
            StateDesc("phase_step_reg", "int", "Phase step", rtl_type="reg", rtl_width=phase_width),
            StateDesc("sign_reg_1", "int", "Sign pipeline 1", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_2", "int", "Sign pipeline 2", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_3", "int", "Sign pipeline 3", rtl_type="reg", rtl_width=1),
            StateDesc("sign_reg_4", "int", "Sign pipeline 4", rtl_type="reg", rtl_width=1),
            StateDesc("ccs_reg_1", "int", "Coarse cos pipeline 1", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ccs_reg_2", "int", "Coarse cos pipeline 2", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ccs_reg_3", "int", "Coarse cos pipeline 3", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_1", "int", "Coarse sin pipeline 1", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_2", "int", "Coarse sin pipeline 2", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("css_reg_3", "int", "Coarse sin pipeline 3", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("fss_reg_1", "int", "Fine sin pipeline 1", rtl_type="reg", rtl_width=dds_output_width // 2),
            StateDesc("fss_reg_2", "int", "Fine sin pipeline 2", rtl_type="reg", rtl_width=dds_output_width // 2),
            StateDesc("cp_reg_1", "int", "Cos*fine product", rtl_type="reg", rtl_width=dds_output_width * 2),
            StateDesc("sp_reg_1", "int", "Sin*fine product", rtl_type="reg", rtl_width=dds_output_width * 2),
            StateDesc("cs_reg_1", "int", "Cosine result", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("ss_reg_1", "int", "Sine result", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("sample_i_reg", "int", "I sample output", rtl_type="reg", rtl_width=dds_output_width),
            StateDesc("sample_q_reg", "int", "Q sample output", rtl_type="reg", rtl_width=dds_output_width),
        ],
        behavior=TemplateRegistry.get("sine_dds"),
        can_stall=False, latency=5,
    )

    # 11. CIC_DECIMATOR
    cic_reg_width = cic_width + ((cic_rmax * cic_m) ** cic_n - 1).bit_length()
    cic_dec_pe = ProcessingElement(
        name="CIC_DECIMATOR", pe_type="cic_decimator",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_tdata", "input", cic_width),
            PortDesc("input_tvalid", "input", 1),
            PortDesc("output_tready", "input", 1),
            PortDesc("rate", "input", max(1, cic_rmax.bit_length())),
        ],
        outputs=[
            PortDesc("input_tready", "output", 1),
            PortDesc("output_tdata", "output", cic_reg_width),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("cycle_reg", "int", "Decimation cycle counter", rtl_type="reg", rtl_width=max(1, cic_rmax.bit_length())),
            StateDesc("int_reg", "int", "Integrator chain", rtl_type="reg", rtl_width=cic_reg_width),
            StateDesc("comb_reg", "int", "Comb output", rtl_type="reg", rtl_width=cic_reg_width),
            StateDesc("delay_reg", "int", "Delay line", rtl_type="reg", rtl_width=cic_reg_width),
        ],
        behavior=TemplateRegistry.get("cic_decimator"),
        can_stall=False, latency=1,
    )

    # 12. CIC_INTERPOLATOR
    cic_interp_gain_bits = ((cic_rmax * cic_m) ** cic_n // cic_rmax - 1).bit_length() if cic_rmax > 0 else 0
    cic_interp_reg_width = cic_width + max(cic_n, cic_interp_gain_bits)
    cic_interp_pe = ProcessingElement(
        name="CIC_INTERPOLATOR", pe_type="cic_interpolator",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("input_tdata", "input", cic_width),
            PortDesc("input_tvalid", "input", 1),
            PortDesc("output_tready", "input", 1),
            PortDesc("rate", "input", max(1, cic_rmax.bit_length())),
        ],
        outputs=[
            PortDesc("input_tready", "output", 1),
            PortDesc("output_tdata", "output", cic_interp_reg_width),
            PortDesc("output_tvalid", "output", 1),
        ],
        state=[
            StateDesc("cycle_reg", "int", "Interpolation cycle counter", rtl_type="reg", rtl_width=max(1, cic_rmax.bit_length())),
            StateDesc("comb_reg", "int", "Comb output", rtl_type="reg", rtl_width=cic_interp_reg_width),
            StateDesc("int_reg", "int", "Integrator chain", rtl_type="reg", rtl_width=cic_interp_reg_width),
            StateDesc("delay_reg", "int", "Delay line", rtl_type="reg", rtl_width=cic_interp_reg_width),
        ],
        behavior=TemplateRegistry.get("cic_interpolator"),
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="DSP_Suite",
        description="Digital Signal Processor suite: signed multipliers, I/Q synchronizers, "
                    "I2S audio interface, DDS sine/cosine generator, and CIC sample-rate "
                    "converter (decimator and interpolator).",
        isa="algorithm",
        processing_elements=[
            dsp_mult_pe, iq_join_pe, iq_split_pe, i2s_ctrl_pe,
            phase_acc_pe, dsp_iq_mult_pe, i2s_rx_pe, i2s_tx_pe,
            sine_dds_lut_pe, sine_dds_pe, cic_dec_pe, cic_interp_pe,
        ],
        interconnects=[
            InterconnectSpec("PHASE_ACCUMULATOR", "SINE_DDS_LUT", signals=[
                PortDesc("output_phase_tdata", "output", phase_width),
                PortDesc("output_phase_tvalid", "output", 1),
            ], flow_type="stream"),
            InterconnectSpec("I2S_CTRL", "I2S_RX", signals=[
                PortDesc("sck", "output", 1),
                PortDesc("ws", "output", 1),
            ], flow_type="clock"),
            InterconnectSpec("I2S_CTRL", "I2S_TX", signals=[
                PortDesc("sck", "output", 1),
                PortDesc("ws", "output", 1),
            ], flow_type="clock"),
        ],
        model=Algorithm_Model(),
        ppa_targets={"max_area": 50000, "target_freq": 100e6},
    )


class DSP_SuiteModel:
    """DSP suite behavioral model for simulation.

    Combines all 12 DSP module models for end-to-end simulation.
    """

    def __init__(
        self,
        mult_width: int = 16,
        phase_width: int = 32,
        dds_output_width: int = 16,
        cic_width: int = 16,
        cic_rmax: int = 2,
        cic_m: int = 1,
        cic_n: int = 2,
        i2s_width: int = 16,
    ):
        from skills.dsp.models import (
            DSP_MULT_Model, IQ_JOIN_Model, IQ_SPLIT_Model,
            I2S_CTRL_Model, PHASE_ACCUMULATOR_Model, DSP_IQ_MULT_Model,
            I2S_RX_Model, I2S_TX_Model, SINE_DDS_LUT_Model, SINE_DDS_Model,
            CIC_DECIMATOR_Model, CIC_INTERPOLATOR_Model,
        )
        self.mult = DSP_MULT_Model(width=mult_width)
        self.iq_join = IQ_JOIN_Model(width=mult_width)
        self.iq_split = IQ_SPLIT_Model(width=mult_width)
        self.i2s_ctrl = I2S_CTRL_Model(width=i2s_width)
        self.phase_acc = PHASE_ACCUMULATOR_Model(width=phase_width)
        self.dsp_iq_mult = DSP_IQ_MULT_Model(width=mult_width)
        self.i2s_rx = I2S_RX_Model(width=i2s_width)
        self.i2s_tx = I2S_TX_Model(width=i2s_width)
        self.sine_lut = SINE_DDS_LUT_Model(output_width=dds_output_width)
        self.sine_dds = SINE_DDS_Model(
            phase_width=phase_width, output_width=dds_output_width,
        )
        self.cic_dec = CIC_DECIMATOR_Model(width=cic_width, rmax=cic_rmax, m=cic_m, n=cic_n)
        self.cic_interp = CIC_INTERPOLATOR_Model(width=cic_width, rmax=cic_rmax, m=cic_m, n=cic_n)
        self.cycle_count = 0
