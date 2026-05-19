"""
skills.dsp.behaviors — DSP Behavior Templates

12 behavior templates for DSP PE types:
  dsp_mult, iq_join, iq_split, i2s_ctrl, phase_accumulator, dsp_iq_mult,
  i2s_rx, i2s_tx, sine_dds_lut, sine_dds, cic_decimator, cic_interpolator

All templates register into TemplateRegistry at import time.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Optional

from rtlgen.behaviors import TemplateRegistry
from rtlgen.arch_def import CycleContext


# =====================================================================
# DSP_MULT — 4-stage pipelined signed scalar multiplier
# =====================================================================

def dsp_mult_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """4-stage pipelined signed multiplier with AXI-Stream backpressure.

    Pipeline: input_reg_0 → input_reg_1 → multiply → output_reg_0 → output_reg_1
    Latency: 4 cycles from input handshake to output.
    """
    def behavior(ctx: CycleContext):
        input_a_tdata = ctx.get_input("input_a_tdata", 0)
        input_b_tdata = ctx.get_input("input_b_tdata", 0)
        input_a_tvalid = ctx.get_input("input_a_tvalid", 0)
        input_b_tvalid = ctx.get_input("input_b_tvalid", 0)
        output_tready = ctx.get_input("output_tready", 0)

        input_a_reg_0 = ctx.get_state("input_a_reg_0", 0)
        input_a_reg_1 = ctx.get_state("input_a_reg_1", 0)
        input_b_reg_0 = ctx.get_state("input_b_reg_0", 0)
        input_b_reg_1 = ctx.get_state("input_b_reg_1", 0)
        output_reg_0 = ctx.get_state("output_reg_0", 0)
        output_reg_1 = ctx.get_state("output_reg_1", 0)

        # Backpressure
        ctx.set_output("input_a_tready", 1 if (input_b_tvalid and output_tready) else 0)
        ctx.set_output("input_b_tready", 1 if (input_a_tvalid and output_tready) else 0)
        ctx.set_output("output_tdata", _sign_extend(output_reg_1, width * 2))
        ctx.set_output("output_tvalid", 1 if (input_a_tvalid and input_b_tvalid) else 0)

        transfer = input_a_tvalid and input_b_tvalid and output_tready
        if transfer:
            ctx.set_state("input_a_reg_0", input_a_tdata)
            ctx.set_state("input_b_reg_0", input_b_tdata)
            ctx.set_state("input_a_reg_1", input_a_reg_0)
            ctx.set_state("input_b_reg_1", input_b_reg_0)
            ctx.set_state("output_reg_0", _signed_mul(input_a_reg_1, input_b_reg_1, width))
            ctx.set_state("output_reg_1", output_reg_0)

    return behavior


# =====================================================================
# IQ_JOIN — Two-channel AXI-Stream synchronizer
# =====================================================================

def iq_join_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Buffers independent I and Q AXI-Stream inputs, presents synchronized pair."""
    def behavior(ctx: CycleContext):
        input_i_tdata = ctx.get_input("input_i_tdata", 0)
        input_q_tdata = ctx.get_input("input_q_tdata", 0)
        input_i_tvalid = ctx.get_input("input_i_tvalid", 0)
        input_q_tvalid = ctx.get_input("input_q_tvalid", 0)
        output_tready = ctx.get_input("output_tready", 0)

        i_data_reg = ctx.get_state("i_data_reg", 0)
        q_data_reg = ctx.get_state("q_data_reg", 0)
        i_valid_reg = ctx.get_state("i_valid_reg", 0)
        q_valid_reg = ctx.get_state("q_valid_reg", 0)

        output_tvalid = 1 if (i_valid_reg and q_valid_reg) else 0
        ctx.set_output("input_i_tready", 1 if (not i_valid_reg or (output_tready and output_tvalid)) else 0)
        ctx.set_output("input_q_tready", 1 if (not q_valid_reg or (output_tready and output_tvalid)) else 0)
        ctx.set_output("output_i_tdata", _sign_extend(i_data_reg, width))
        ctx.set_output("output_q_tdata", _sign_extend(q_data_reg, width))
        ctx.set_output("output_tvalid", output_tvalid)

        if ctx.get_output("input_i_tready", 0) and input_i_tvalid:
            ctx.set_state("i_data_reg", input_i_tdata)
            ctx.set_state("i_valid_reg", 1)
        elif output_tready and output_tvalid:
            ctx.set_state("i_valid_reg", 0)

        if ctx.get_output("input_q_tready", 0) and input_q_tvalid:
            ctx.set_state("q_data_reg", input_q_tdata)
            ctx.set_state("q_valid_reg", 1)
        elif output_tready and output_tvalid:
            ctx.set_state("q_valid_reg", 0)

    return behavior


# =====================================================================
# IQ_SPLIT — Two-channel AXI-Stream demultiplexer
# =====================================================================

def iq_split_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Splits synchronized IQ pair into independent I and Q AXI-Stream outputs."""
    def behavior(ctx: CycleContext):
        input_i_tdata = ctx.get_input("input_i_tdata", 0)
        input_q_tdata = ctx.get_input("input_q_tdata", 0)
        input_tvalid = ctx.get_input("input_tvalid", 0)
        output_i_tready = ctx.get_input("output_i_tready", 0)
        output_q_tready = ctx.get_input("output_q_tready", 0)

        i_data_reg = ctx.get_state("i_data_reg", 0)
        q_data_reg = ctx.get_state("q_data_reg", 0)
        i_valid_reg = ctx.get_state("i_valid_reg", 0)
        q_valid_reg = ctx.get_state("q_valid_reg", 0)

        i_consume = output_i_tready and i_valid_reg
        q_consume = output_q_tready and q_valid_reg
        input_tready = 1 if ((not i_valid_reg or i_consume) and (not q_valid_reg or q_consume)) else 0

        ctx.set_output("input_tready", input_tready)
        ctx.set_output("output_i_tdata", _sign_extend(i_data_reg, width))
        ctx.set_output("output_i_tvalid", 1 if i_valid_reg else 0)
        ctx.set_output("output_q_tdata", _sign_extend(q_data_reg, width))
        ctx.set_output("output_q_tvalid", 1 if q_valid_reg else 0)

        if input_tready and input_tvalid:
            ctx.set_state("i_data_reg", input_i_tdata)
            ctx.set_state("q_data_reg", input_q_tdata)
            ctx.set_state("i_valid_reg", 1)
            ctx.set_state("q_valid_reg", 1)
        else:
            if i_consume:
                ctx.set_state("i_valid_reg", 0)
            if q_consume:
                ctx.set_state("q_valid_reg", 0)

    return behavior


# =====================================================================
# I2S_CTRL — I2S bus clock generator
# =====================================================================

def i2s_ctrl_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Produces serial clock (sck) and word-select (ws) from system clock."""
    def behavior(ctx: CycleContext):
        prescale = ctx.get_input("prescale", 0)

        prescale_cnt = ctx.get_state("prescale_cnt", 0)
        ws_cnt = ctx.get_state("ws_cnt", 0)
        sck_reg = ctx.get_state("sck_reg", 0)
        ws_reg = ctx.get_state("ws_reg", 0)

        ctx.set_output("sck", sck_reg)
        ctx.set_output("ws", ws_reg)

        if prescale_cnt > 0:
            ctx.set_state("prescale_cnt", prescale_cnt - 1)
        else:
            ctx.set_state("prescale_cnt", prescale)
            if sck_reg:
                ctx.set_state("sck_reg", 0)
                if ws_cnt > 0:
                    ctx.set_state("ws_cnt", ws_cnt - 1)
                else:
                    ctx.set_state("ws_cnt", width - 1)
                    ctx.set_state("ws_reg", 1 - ws_reg)
            else:
                ctx.set_state("sck_reg", 1)

    return behavior


# =====================================================================
# PHASE_ACCUMULATOR — NCO phase accumulator
# =====================================================================

def phase_accumulator_template(
    width: int = 32,
) -> Callable[[CycleContext], None]:
    """NCO phase accumulator: continuous phase ramp with programmable step."""
    def behavior(ctx: CycleContext):
        input_phase_tdata = ctx.get_input("input_phase_tdata", 0)
        input_phase_tvalid = ctx.get_input("input_phase_tvalid", 0)
        input_phase_step_tdata = ctx.get_input("input_phase_step_tdata", 0)
        input_phase_step_tvalid = ctx.get_input("input_phase_step_tvalid", 0)
        output_phase_tready = ctx.get_input("output_phase_tready", 0)

        phase_reg = ctx.get_state("phase_reg", 0)
        phase_step_reg = ctx.get_state("phase_step_reg", 0)

        input_phase_tready = output_phase_tready
        ctx.set_output("input_phase_tready", input_phase_tready)
        ctx.set_output("input_phase_step_tready", 1)
        ctx.set_output("output_phase_tdata", phase_reg & ((1 << width) - 1))
        ctx.set_output("output_phase_tvalid", 1)

        if input_phase_tready and input_phase_tvalid:
            ctx.set_state("phase_reg", input_phase_tdata & ((1 << width) - 1))
        elif output_phase_tready:
            ctx.set_state("phase_reg", (phase_reg + phase_step_reg) & ((1 << width) - 1))

        if input_phase_step_tvalid:
            ctx.set_state("phase_step_reg", input_phase_step_tdata & ((1 << width) - 1))

    return behavior


# =====================================================================
# DSP_IQ_MULT — Complex IQ multiplier (4-stage pipeline)
# =====================================================================

def dsp_iq_mult_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Complex IQ multiplier: I×I and Q×Q products, 4-stage pipeline."""
    def behavior(ctx: CycleContext):
        input_a_i = ctx.get_input("input_a_i_tdata", 0)
        input_a_q = ctx.get_input("input_a_q_tdata", 0)
        input_b_i = ctx.get_input("input_b_i_tdata", 0)
        input_b_q = ctx.get_input("input_b_q_tdata", 0)
        input_a_tvalid = ctx.get_input("input_a_tvalid", 0)
        input_b_tvalid = ctx.get_input("input_b_tvalid", 0)
        output_tready = ctx.get_input("output_tready", 0)

        a_i_0 = ctx.get_state("input_a_i_reg_0", 0)
        a_q_0 = ctx.get_state("input_a_q_reg_0", 0)
        a_i_1 = ctx.get_state("input_a_i_reg_1", 0)
        a_q_1 = ctx.get_state("input_a_q_reg_1", 0)
        b_i_0 = ctx.get_state("input_b_i_reg_0", 0)
        b_q_0 = ctx.get_state("input_b_q_reg_0", 0)
        b_i_1 = ctx.get_state("input_b_i_reg_1", 0)
        b_q_1 = ctx.get_state("input_b_q_reg_1", 0)
        out_i_0 = ctx.get_state("output_i_reg_0", 0)
        out_q_0 = ctx.get_state("output_q_reg_0", 0)
        out_i_1 = ctx.get_state("output_i_reg_1", 0)
        out_q_1 = ctx.get_state("output_q_reg_1", 0)

        ctx.set_output("input_a_tready", 1 if (input_b_tvalid and output_tready) else 0)
        ctx.set_output("input_b_tready", 1 if (input_a_tvalid and output_tready) else 0)
        ctx.set_output("output_i_tdata", _sign_extend(out_i_1, width * 2))
        ctx.set_output("output_q_tdata", _sign_extend(out_q_1, width * 2))
        ctx.set_output("output_tvalid", 1 if (input_a_tvalid and input_b_tvalid) else 0)

        transfer = input_a_tvalid and input_b_tvalid and output_tready
        if transfer:
            ctx.set_state("input_a_i_reg_0", input_a_i)
            ctx.set_state("input_a_q_reg_0", input_a_q)
            ctx.set_state("input_b_i_reg_0", input_b_i)
            ctx.set_state("input_b_q_reg_0", input_b_q)
            ctx.set_state("input_a_i_reg_1", a_i_0)
            ctx.set_state("input_a_q_reg_1", a_q_0)
            ctx.set_state("input_b_i_reg_1", b_i_0)
            ctx.set_state("input_b_q_reg_1", b_q_0)
            ctx.set_state("output_i_reg_0", _signed_mul(a_i_1, b_i_1, width))
            ctx.set_state("output_q_reg_0", _signed_mul(a_q_1, b_q_1, width))
            ctx.set_state("output_i_reg_1", out_i_0)
            ctx.set_state("output_q_reg_1", out_q_0)

    return behavior


# =====================================================================
# I2S_RX — I2S serial receiver
# =====================================================================

def i2s_rx_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """I2S receiver: captures left/right audio from serial I2S signals."""
    def behavior(ctx: CycleContext):
        sck = ctx.get_input("sck", 0)
        ws = ctx.get_input("ws", 0)
        sd = ctx.get_input("sd", 0)
        output_tready = ctx.get_input("output_tready", 0)

        l_data_reg = ctx.get_state("l_data_reg", 0)
        r_data_reg = ctx.get_state("r_data_reg", 0)
        l_data_valid_reg = ctx.get_state("l_data_valid_reg", 0)
        r_data_valid_reg = ctx.get_state("r_data_valid_reg", 0)
        sreg = ctx.get_state("sreg", 0)
        bit_cnt = ctx.get_state("bit_cnt", 0)
        last_sck = ctx.get_state("last_sck", 0)
        last_ws = ctx.get_state("last_ws", 0)
        last_ws2 = ctx.get_state("last_ws2", 0)

        output_tvalid = 1 if (l_data_valid_reg and r_data_valid_reg) else 0
        ctx.set_output("output_l_tdata", _sign_extend(l_data_reg, width))
        ctx.set_output("output_r_tdata", _sign_extend(r_data_reg, width))
        ctx.set_output("output_tvalid", output_tvalid)

        if output_tready and output_tvalid:
            ctx.set_state("l_data_valid_reg", 0)
            ctx.set_state("r_data_valid_reg", 0)

        ctx.set_state("last_sck", sck)

        sck_rising = (not last_sck) and sck
        if sck_rising:
            ctx.set_state("last_ws", ws)
            ctx.set_state("last_ws2", last_ws)

            if last_ws2 != ws:
                ctx.set_state("bit_cnt", width - 1)
                ctx.set_state("sreg", sd)
            elif bit_cnt > 0:
                ctx.set_state("bit_cnt", bit_cnt - 1)
                if bit_cnt > 1:
                    ctx.set_state("sreg", ((sreg << 1) | sd) & ((1 << width) - 1))
                elif last_ws2:
                    ctx.set_state("r_data_reg", ((sreg << 1) | sd) & ((1 << width) - 1))
                    ctx.set_state("r_data_valid_reg", l_data_valid_reg)
                else:
                    ctx.set_state("l_data_reg", ((sreg << 1) | sd) & ((1 << width) - 1))
                    ctx.set_state("l_data_valid_reg", 1)

    return behavior


# =====================================================================
# I2S_TX — I2S serial transmitter
# =====================================================================

def i2s_tx_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """I2S transmitter: converts parallel L/R samples to serial I2S stream."""
    def behavior(ctx: CycleContext):
        input_l_tdata = ctx.get_input("input_l_tdata", 0)
        input_r_tdata = ctx.get_input("input_r_tdata", 0)
        input_tvalid = ctx.get_input("input_tvalid", 0)
        sck = ctx.get_input("sck", 0)
        ws = ctx.get_input("ws", 0)

        l_data_reg = ctx.get_state("l_data_reg", 0)
        r_data_reg = ctx.get_state("r_data_reg", 0)
        l_data_valid_reg = ctx.get_state("l_data_valid_reg", 0)
        r_data_valid_reg = ctx.get_state("r_data_valid_reg", 0)
        sreg = ctx.get_state("sreg", 0)
        bit_cnt = ctx.get_state("bit_cnt", 0)
        last_sck = ctx.get_state("last_sck", 0)
        last_ws = ctx.get_state("last_ws", 0)
        sd_reg = ctx.get_state("sd_reg", 0)

        input_tready = 1 if (not l_data_valid_reg and not r_data_valid_reg) else 0
        ctx.set_output("input_tready", input_tready)
        ctx.set_output("sd", sd_reg)

        if input_tready and input_tvalid:
            ctx.set_state("l_data_reg", input_l_tdata)
            ctx.set_state("r_data_reg", input_r_tdata)
            ctx.set_state("l_data_valid_reg", 1)
            ctx.set_state("r_data_valid_reg", 1)

        ctx.set_state("last_sck", sck)

        sck_rising = (not last_sck) and sck
        if sck_rising:
            ctx.set_state("last_ws", ws)
            if last_ws != ws:
                ctx.set_state("bit_cnt", width)
                if ws:
                    ctx.set_state("sreg", r_data_reg)
                    ctx.set_state("r_data_valid_reg", 0)
                else:
                    ctx.set_state("sreg", l_data_reg)
                    ctx.set_state("l_data_valid_reg", 0)

        sck_falling = last_sck and (not sck)
        if sck_falling and bit_cnt > 0:
            ctx.set_state("bit_cnt", bit_cnt - 1)
            msb = (sreg >> (width - 1)) & 1
            ctx.set_state("sd_reg", msb)
            ctx.set_state("sreg", (sreg << 1) & ((1 << width) - 1))

    return behavior


# =====================================================================
# SINE_DDS_LUT — Sine/cosine LUT with fine/coarse decomposition
# =====================================================================

def sine_dds_lut_template(
    output_width: int = 16,
    input_width: Optional[int] = None,
) -> Callable[[CycleContext], None]:
    """Pipelined sine/cosine LUT with fine/coarse angle decomposition.

    sin(A+B) = sin(A) + cos(A)*sin(B)
    cos(A+B) = cos(A) - sin(A)*sin(B)
    5-stage pipeline: LUT read → pipeline → multiply → add/sub → sign correction.
    """
    if input_width is None:
        input_width = output_width + 2

    W = (input_width - 2) // 2
    coarse_size = 2 ** (W + 1)
    fine_size = 2 ** W
    scale = (2 ** (output_width - 1)) - 1
    pi = 3.1415926535

    coarse_c_lut = []
    coarse_s_lut = []
    for i in range(coarse_size):
        cval = int(round(math.cos(2 * pi * i / (2 ** (W + 2))) * scale))
        sval = int(round(math.sin(2 * pi * i / (2 ** (W + 2))) * scale))
        cval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, cval))
        sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
        coarse_c_lut.append(_twos_complement(cval, output_width))
        coarse_s_lut.append(_twos_complement(sval, output_width))

    fine_s_lut = []
    half_fine = 2 ** (W - 1)
    for i in range(fine_size):
        sval = int(round(math.sin(2 * pi * (i - half_fine) / (2 ** input_width)) * scale))
        sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
        fine_s_lut.append(_twos_complement(sval, output_width))

    half_out = output_width // 2

    def behavior(ctx: CycleContext):
        input_phase_tdata = ctx.get_input("input_phase_tdata", 0)
        input_phase_tvalid = ctx.get_input("input_phase_tvalid", 0)
        output_sample_tready = ctx.get_input("output_sample_tready", 0)

        phase_reg = ctx.get_state("phase_reg", 0)

        ctx.set_output("input_phase_tready", output_sample_tready)

        if ctx.get_output("input_phase_tready", 0) and input_phase_tvalid:
            ctx.set_state("phase_reg", input_phase_tdata & ((1 << input_width) - 1))

        sign = (phase_reg >> (input_width - 1)) & 1
        a = (phase_reg >> W) & ((1 << (W + 1)) - 1)
        b = phase_reg & ((1 << W) - 1) if W > 0 else 0

        sign_reg_1 = ctx.get_state("sign_reg_1", 0)
        sign_reg_2 = ctx.get_state("sign_reg_2", 0)
        sign_reg_3 = ctx.get_state("sign_reg_3", 0)
        sign_reg_4 = ctx.get_state("sign_reg_4", 0)
        ccs_reg_1 = ctx.get_state("ccs_reg_1", 0)
        ccs_reg_2 = ctx.get_state("ccs_reg_2", 0)
        ccs_reg_3 = ctx.get_state("ccs_reg_3", 0)
        css_reg_1 = ctx.get_state("css_reg_1", 0)
        css_reg_2 = ctx.get_state("css_reg_2", 0)
        css_reg_3 = ctx.get_state("css_reg_3", 0)
        fss_reg_1 = ctx.get_state("fss_reg_1", 0)
        fss_reg_2 = ctx.get_state("fss_reg_2", 0)
        cp_reg_1 = ctx.get_state("cp_reg_1", 0)
        sp_reg_1 = ctx.get_state("sp_reg_1", 0)
        cs_reg_1 = ctx.get_state("cs_reg_1", 0)
        ss_reg_1 = ctx.get_state("ss_reg_1", 0)
        sample_i_reg = ctx.get_state("sample_i_reg", 0)
        sample_q_reg = ctx.get_state("sample_q_reg", 0)

        ctx.set_output("output_sample_i_tdata", _sign_extend(sample_i_reg, output_width))
        ctx.set_output("output_sample_q_tdata", _sign_extend(sample_q_reg, output_width))
        ctx.set_output("output_sample_tvalid", input_phase_tvalid)

        if ctx.get_output("input_phase_tready", 0) and input_phase_tvalid:
            ctx.set_state("sign_reg_1", sign)
            ctx.set_state("ccs_reg_1", coarse_c_lut[a])
            ctx.set_state("css_reg_1", coarse_s_lut[a])
            ctx.set_state("fss_reg_1", fine_s_lut[b])

            ctx.set_state("sign_reg_2", sign_reg_1)
            ctx.set_state("ccs_reg_2", ccs_reg_1)
            ctx.set_state("css_reg_2", css_reg_1)
            ctx.set_state("fss_reg_2", fss_reg_1)

            ctx.set_state("sign_reg_3", sign_reg_2)
            ctx.set_state("ccs_reg_3", ccs_reg_2)
            ctx.set_state("css_reg_3", css_reg_2)
            ctx.set_state("cp_reg_1", _signed_mul(css_reg_2, fss_reg_2, max(output_width, half_out)))
            ctx.set_state("sp_reg_1", _signed_mul(ccs_reg_2, fss_reg_2, max(output_width, half_out)))

            shift_amt = output_width - 1
            cp_shifted = _arithmetic_right(cp_reg_1, shift_amt, output_width * 2)
            sp_shifted = _arithmetic_right(sp_reg_1, shift_amt, output_width * 2)

            cs_val = (_to_signed(ccs_reg_3, output_width) - _to_signed(cp_shifted, output_width)) & ((1 << output_width) - 1)
            ss_val = (_to_signed(css_reg_3, output_width) + _to_signed(sp_shifted, output_width)) & ((1 << output_width) - 1)
            ctx.set_state("cs_reg_1", cs_val)
            ctx.set_state("ss_reg_1", ss_val)

            ctx.set_state("sign_reg_4", sign_reg_3)

            if sign_reg_4:
                ctx.set_state("sample_i_reg", _twos_complement(_to_signed(cs_val, output_width), output_width))
                ctx.set_state("sample_q_reg", _twos_complement(_to_signed(ss_val, output_width), output_width))
            else:
                ctx.set_state("sample_i_reg", cs_val)
                ctx.set_state("sample_q_reg", ss_val)

    return behavior


# =====================================================================
# SINE_DDS — Top-level DDS (phase_accumulator + sine_dds_lut)
# =====================================================================

def sine_dds_template(
    phase_width: int = 32,
    output_width: int = 16,
) -> Callable[[CycleContext], None]:
    """Top-level DDS combining phase accumulator + sine/cosine LUT."""
    def behavior(ctx: CycleContext):
        input_phase_tdata = ctx.get_input("input_phase_tdata", 0)
        input_phase_tvalid = ctx.get_input("input_phase_tvalid", 0)
        input_phase_step_tdata = ctx.get_input("input_phase_step_tdata", 0)
        input_phase_step_tvalid = ctx.get_input("input_phase_step_tvalid", 0)
        output_sample_tready = ctx.get_input("output_sample_tready", 0)

        phase_reg = ctx.get_state("phase_reg", 0)
        phase_step_reg = ctx.get_state("phase_step_reg", 0)

        input_phase_tready = output_sample_tready
        ctx.set_output("input_phase_tready", input_phase_tready)
        ctx.set_output("input_phase_step_tready", 1)

        if input_phase_tready and input_phase_tvalid:
            ctx.set_state("phase_reg", input_phase_tdata & ((1 << phase_width) - 1))
        elif output_sample_tready:
            ctx.set_state("phase_reg", (phase_reg + phase_step_reg) & ((1 << phase_width) - 1))

        if input_phase_step_tvalid:
            ctx.set_state("phase_step_reg", input_phase_step_tdata & ((1 << phase_width) - 1))

        phase_out = ctx.get_state("phase_reg", 0)
        lut_input_width = output_width + 2
        W = (lut_input_width - 2) // 2
        coarse_size = 2 ** (W + 1)
        fine_size = 2 ** W
        scale = (2 ** (output_width - 1)) - 1
        pi = 3.1415926535

        coarse_c_lut = []
        coarse_s_lut = []
        for i in range(coarse_size):
            cval = int(round(math.cos(2 * pi * i / (2 ** (W + 2))) * scale))
            sval = int(round(math.sin(2 * pi * i / (2 ** (W + 2))) * scale))
            cval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, cval))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            coarse_c_lut.append(_twos_complement(cval, output_width))
            coarse_s_lut.append(_twos_complement(sval, output_width))

        fine_s_lut = []
        half_fine = 2 ** (W - 1)
        for i in range(fine_size):
            sval = int(round(math.sin(2 * pi * (i - half_fine) / (2 ** lut_input_width)) * scale))
            sval = max(-(2 ** (output_width - 1)), min(2 ** (output_width - 1) - 1, sval))
            fine_s_lut.append(_twos_complement(sval, output_width))

        lut_phase = (phase_out >> (phase_width - lut_input_width)) & ((1 << lut_input_width) - 1)
        sign = (lut_phase >> (lut_input_width - 1)) & 1
        a = (lut_phase >> W) & ((1 << (W + 1)) - 1)
        b = lut_phase & ((1 << W) - 1) if W > 0 else 0

        sign_reg_1 = ctx.get_state("sign_reg_1", 0)
        sign_reg_2 = ctx.get_state("sign_reg_2", 0)
        sign_reg_3 = ctx.get_state("sign_reg_3", 0)
        sign_reg_4 = ctx.get_state("sign_reg_4", 0)
        ccs_reg_1 = ctx.get_state("ccs_reg_1", 0)
        ccs_reg_2 = ctx.get_state("ccs_reg_2", 0)
        ccs_reg_3 = ctx.get_state("ccs_reg_3", 0)
        css_reg_1 = ctx.get_state("css_reg_1", 0)
        css_reg_2 = ctx.get_state("css_reg_2", 0)
        css_reg_3 = ctx.get_state("css_reg_3", 0)
        fss_reg_1 = ctx.get_state("fss_reg_1", 0)
        fss_reg_2 = ctx.get_state("fss_reg_2", 0)
        cp_reg_1 = ctx.get_state("cp_reg_1", 0)
        sp_reg_1 = ctx.get_state("sp_reg_1", 0)
        cs_reg_1 = ctx.get_state("cs_reg_1", 0)
        ss_reg_1 = ctx.get_state("ss_reg_1", 0)
        sample_i_reg = ctx.get_state("sample_i_reg", 0)
        sample_q_reg = ctx.get_state("sample_q_reg", 0)

        ctx.set_output("output_sample_i_tdata", _sign_extend(sample_i_reg, output_width))
        ctx.set_output("output_sample_q_tdata", _sign_extend(sample_q_reg, output_width))
        ctx.set_output("output_sample_tvalid", input_phase_tvalid)

        if input_phase_tready and input_phase_tvalid:
            ctx.set_state("sign_reg_1", sign)
            ctx.set_state("ccs_reg_1", coarse_c_lut[a])
            ctx.set_state("css_reg_1", coarse_s_lut[a])
            ctx.set_state("fss_reg_1", fine_s_lut[b])

            ctx.set_state("sign_reg_2", sign_reg_1)
            ctx.set_state("ccs_reg_2", ccs_reg_1)
            ctx.set_state("css_reg_2", css_reg_1)
            ctx.set_state("fss_reg_2", fss_reg_1)

            ctx.set_state("sign_reg_3", sign_reg_2)
            ctx.set_state("ccs_reg_3", ccs_reg_2)
            ctx.set_state("css_reg_3", css_reg_2)
            half_out = output_width // 2
            ctx.set_state("cp_reg_1", _signed_mul(css_reg_2, fss_reg_2, max(output_width, half_out)))
            ctx.set_state("sp_reg_1", _signed_mul(ccs_reg_2, fss_reg_2, max(output_width, half_out)))

            shift_amt = output_width - 1
            cp_shifted = _arithmetic_right(cp_reg_1, shift_amt, output_width * 2)
            sp_shifted = _arithmetic_right(sp_reg_1, shift_amt, output_width * 2)

            cs_val = (_to_signed(ccs_reg_3, output_width) - _to_signed(cp_shifted, output_width)) & ((1 << output_width) - 1)
            ss_val = (_to_signed(css_reg_3, output_width) + _to_signed(sp_shifted, output_width)) & ((1 << output_width) - 1)
            ctx.set_state("cs_reg_1", cs_val)
            ctx.set_state("ss_reg_1", ss_val)

            ctx.set_state("sign_reg_4", sign_reg_3)

            if sign_reg_4:
                ctx.set_state("sample_i_reg", _twos_complement(_to_signed(cs_val, output_width), output_width))
                ctx.set_state("sample_q_reg", _twos_complement(_to_signed(ss_val, output_width), output_width))
            else:
                ctx.set_state("sample_i_reg", cs_val)
                ctx.set_state("sample_q_reg", ss_val)

    return behavior


# =====================================================================
# CIC_DECIMATOR — Cascaded integrator-comb decimator
# =====================================================================

def cic_decimator_template(
    width: int = 16,
    rmax: int = 2,
    m: int = 1,
    n: int = 2,
) -> Callable[[CycleContext], None]:
    """CIC decimator: N integrators → programmable decimator → N combs."""
    reg_width = width + ((rmax * m) ** n - 1).bit_length()

    def behavior(ctx: CycleContext):
        input_tdata = ctx.get_input("input_tdata", 0)
        input_tvalid = ctx.get_input("input_tvalid", 0)
        output_tready = ctx.get_input("output_tready", 0)
        rate = ctx.get_input("rate", 1)

        cycle_reg = ctx.get_state("cycle_reg", 0)
        mask = (1 << reg_width) - 1

        int_regs = []
        for k in range(n):
            int_regs.append(ctx.get_state(f"int_reg_{k}", 0))

        comb_regs = []
        for k in range(n):
            comb_regs.append(ctx.get_state(f"comb_reg_{k}", 0))

        delay_regs = []
        for k in range(n):
            stage = []
            for i in range(m):
                stage.append(ctx.get_state(f"delay_reg_{k}_{i}", 0))
            delay_regs.append(stage)

        output_tvalid = 1 if (input_tvalid and cycle_reg == 0) else 0
        input_tready = 1 if (output_tready or cycle_reg != 0) else 0
        ctx.set_output("input_tready", input_tready)
        ctx.set_output("output_tdata", comb_regs[n - 1] & mask)
        ctx.set_output("output_tvalid", output_tvalid)

        if input_tready and input_tvalid:
            for k in range(n):
                if k == 0:
                    new_val = _to_signed(int_regs[k], reg_width) + _to_signed(input_tdata, width)
                else:
                    new_val = _to_signed(int_regs[k], reg_width) + _to_signed(int_regs[k - 1], reg_width)
                ctx.set_state(f"int_reg_{k}", new_val & mask)

        if output_tready and output_tvalid:
            for k in range(n):
                if k == 0:
                    src = int_regs[n - 1]
                else:
                    src = comb_regs[k - 1]
                ctx.set_state(f"delay_reg_{k}_0", src & mask)
                diff = _to_signed(src, reg_width) - _to_signed(delay_regs[k][m - 1], reg_width)
                ctx.set_state(f"comb_reg_{k}", diff & mask)
                for i in range(m - 1):
                    ctx.set_state(f"delay_reg_{k}_{i + 1}", delay_regs[k][i] & mask)

        if input_tready and input_tvalid:
            if cycle_reg < (rmax - 1) and cycle_reg < (rate - 1):
                ctx.set_state("cycle_reg", cycle_reg + 1)
            else:
                ctx.set_state("cycle_reg", 0)

    return behavior


# =====================================================================
# CIC_INTERPOLATOR — Cascaded integrator-comb interpolator
# =====================================================================

def cic_interpolator_template(
    width: int = 16,
    rmax: int = 2,
    m: int = 1,
    n: int = 2,
) -> Callable[[CycleContext], None]:
    """CIC interpolator: N combs → programmable up-converter → N integrators."""
    gain_bits = ((rmax * m) ** n // rmax - 1).bit_length() if rmax > 0 else 0
    reg_width = width + max(n, gain_bits)

    def behavior(ctx: CycleContext):
        input_tdata = ctx.get_input("input_tdata", 0)
        input_tvalid = ctx.get_input("input_tvalid", 0)
        output_tready = ctx.get_input("output_tready", 0)
        rate = ctx.get_input("rate", 1)

        cycle_reg = ctx.get_state("cycle_reg", 0)
        mask = (1 << reg_width) - 1

        comb_regs = []
        for k in range(n):
            comb_regs.append(ctx.get_state(f"comb_reg_{k}", 0))

        int_regs = []
        for k in range(n):
            int_regs.append(ctx.get_state(f"int_reg_{k}", 0))

        delay_regs = []
        for k in range(n):
            stage = []
            for i in range(m):
                stage.append(ctx.get_state(f"delay_reg_{k}_{i}", 0))
            delay_regs.append(stage)

        input_tready = 1 if (output_tready and cycle_reg == 0) else 0
        ctx.set_output("input_tready", input_tready)
        ctx.set_output("output_tdata", int_regs[n - 1] & mask)
        ctx.set_output("output_tvalid", 1 if (input_tvalid or cycle_reg != 0) else 0)

        if input_tready and input_tvalid:
            for k in range(n):
                if k == 0:
                    src = input_tdata
                else:
                    src = comb_regs[k - 1]
                ctx.set_state(f"delay_reg_{k}_0", src & mask)
                diff = _to_signed(src, reg_width) - _to_signed(delay_regs[k][m - 1], reg_width)
                ctx.set_state(f"comb_reg_{k}", diff & mask)
                for i in range(m - 1):
                    ctx.set_state(f"delay_reg_{k}_{i + 1}", delay_regs[k][i] & mask)

        if output_tready and ctx.get_output("output_tvalid", 0):
            for k in range(n):
                if k == 0:
                    if cycle_reg == 0:
                        new_val = _to_signed(int_regs[k], reg_width) + _to_signed(comb_regs[n - 1], reg_width)
                        ctx.set_state(f"int_reg_{k}", new_val & mask)
                else:
                    new_val = _to_signed(int_regs[k], reg_width) + _to_signed(int_regs[k - 1], reg_width)
                    ctx.set_state(f"int_reg_{k}", new_val & mask)

        if output_tready and ctx.get_output("output_tvalid", 0):
            if cycle_reg < (rmax - 1) and cycle_reg < (rate - 1):
                ctx.set_state("cycle_reg", cycle_reg + 1)
            else:
                ctx.set_state("cycle_reg", 0)

    return behavior


# =====================================================================
# Signed arithmetic helpers
# =====================================================================

def _to_signed(val: int, width: int) -> int:
    """Convert unsigned int to signed Python int."""
    if val & (1 << (width - 1)):
        return val - (1 << width)
    return val


def _signed_mul(a: int, b: int, width: int) -> int:
    """Signed multiply two values, return unsigned 2*width result."""
    sa = _to_signed(a, width)
    sb = _to_signed(b, width)
    result = sa * sb
    out_width = width * 2
    if result < 0:
        result = result + (1 << out_width)
    return result & ((1 << out_width) - 1)


def _sign_extend(val: int, width: int) -> int:
    """Sign-extend an unsigned value to Python int."""
    return _to_signed(val, width)


def _twos_complement(val: int, width: int) -> int:
    """Convert signed Python int to unsigned bit representation."""
    if val < 0:
        return (val + (1 << width)) & ((1 << width) - 1)
    return val & ((1 << width) - 1)


def _arithmetic_right(val: int, shift: int, width: int) -> int:
    """Arithmetic right shift preserving sign."""
    signed_val = _to_signed(val, width)
    result = signed_val >> shift
    return _twos_complement(result, width)


# =====================================================================
# Register all 12 DSP templates
# =====================================================================

TemplateRegistry.register("dsp_mult", dsp_mult_template())
TemplateRegistry.register("iq_join", iq_join_template())
TemplateRegistry.register("iq_split", iq_split_template())
TemplateRegistry.register("i2s_ctrl", i2s_ctrl_template())
TemplateRegistry.register("phase_accumulator", phase_accumulator_template())
TemplateRegistry.register("dsp_iq_mult", dsp_iq_mult_template())
TemplateRegistry.register("i2s_rx", i2s_rx_template())
TemplateRegistry.register("i2s_tx", i2s_tx_template())
TemplateRegistry.register("sine_dds_lut", sine_dds_lut_template())
TemplateRegistry.register("sine_dds", sine_dds_template())
TemplateRegistry.register("cic_decimator", cic_decimator_template())
TemplateRegistry.register("cic_interpolator", cic_interpolator_template())
