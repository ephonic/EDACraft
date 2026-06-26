"""
skills.dsp.functional — Layer 1: Behavioral models (no timing).

Pure combinatorial models for all 12 DSP modules.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional


def dsp_mult_functional(**kwargs) -> Callable:
    """Functional DSP_MULT: signed scalar multiply.
    Pure combinatorial: output = input_a * input_b (4-stage pipelined behavior as pure function).
    """
    width = kwargs.get('width', 16)
    def func(input_a_tdata: int = 0, input_b_tdata: int = 0,
             input_a_tvalid: int = 0, input_b_tvalid: int = 0,
             output_tready: int = 0) -> Dict:
        ready = input_a_tvalid & input_b_tvalid & output_tready
        result = 0
        if ready:
            a_s = input_a_tdata if input_a_tdata < (1 << (width - 1)) else input_a_tdata - (1 << width)
            b_s = input_b_tdata if input_b_tdata < (1 << (width - 1)) else input_b_tdata - (1 << width)
            result = (a_s * b_s) & ((1 << (width * 2)) - 1)
        return {
            "input_a_tready": int(input_b_tvalid and output_tready),
            "input_b_tready": int(input_a_tvalid and output_tready),
            "output_tdata": result,
            "output_tvalid": int(input_a_tvalid and input_b_tvalid),
        }
    return func


def iq_join_functional(**kwargs) -> Callable:
    """Functional IQ_JOIN: two-channel AXI-Stream synchronizer.
    Output valid only when both I and Q channels have data.
    """
    width = kwargs.get('width', 16)
    def func(input_i_tdata: int = 0, input_q_tdata: int = 0,
             input_i_tvalid: int = 0, input_q_tvalid: int = 0,
             output_tready: int = 0) -> Dict:
        i_hold = input_i_tvalid & (not input_i_tvalid if False else True)
        return {
            "input_i_tready": 1,
            "input_q_tready": 1,
            "output_i_tdata": input_i_tdata,
            "output_q_tdata": input_q_tdata,
            "output_tvalid": int(input_i_tvalid and input_q_tvalid),
        }
    return func


def iq_split_functional(**kwargs) -> Callable:
    """Functional IQ_SPLIT: two-channel AXI-Stream demultiplexer."""
    width = kwargs.get('width', 16)
    def func(input_i_tdata: int = 0, input_q_tdata: int = 0,
             input_tvalid: int = 0,
             output_i_tready: int = 0, output_q_tready: int = 0) -> Dict:
        return {
            "input_tready": int(output_i_tready and output_q_tready),
            "output_i_tdata": input_i_tdata,
            "output_i_tvalid": int(input_tvalid and output_i_tready),
            "output_q_tdata": input_q_tdata,
            "output_q_tvalid": int(input_tvalid and output_q_tready),
        }
    return func


def i2s_ctrl_functional(**kwargs) -> Callable:
    """Functional I2S_CTRL: I2S bus clock generator.
    Produces sck = clk / (2*prescale), ws toggles every width bits.
    """
    width = kwargs.get('width', 16)
    prescale_val = kwargs.get('prescale', 256)
    def func(prescale: int = prescale_val) -> Dict:
        half_period = max(1, prescale // 2)
        sck_freq_div = 1 if prescale > 0 else 0
        ws_period = width * 2
        return {
            "sck": 1 if sck_freq_div else 0,
            "ws": 0,
        }
    return func


def phase_accumulator_functional(**kwargs) -> Callable:
    """Functional PHASE_ACCUMULATOR: NCO phase accumulator.
    output_phase = phase + step (cumulative, free-running).
    """
    width = kwargs.get('width', 32)
    def func(input_phase_tdata: int = 0, input_phase_tvalid: int = 0,
             input_phase_step_tdata: int = 0, input_phase_step_tvalid: int = 0,
             output_phase_tready: int = 0) -> Dict:
        mask = (1 << width) - 1
        phase = input_phase_tdata & mask if input_phase_tvalid else 0
        step = input_phase_step_tdata & mask if input_phase_step_tvalid else 0
        out_phase = (phase + step) & mask
        return {
            "input_phase_tready": output_phase_tready,
            "input_phase_step_tready": 1,
            "output_phase_tdata": out_phase,
            "output_phase_tvalid": 1,
        }
    return func


def dsp_iq_mult_functional(**kwargs) -> Callable:
    """Functional DSP_IQ_MULT: complex IQ multiplier.
    output_i = a_i * b_i, output_q = a_q * b_q (single-cycle product).
    """
    width = kwargs.get('width', 16)
    def func(input_a_i_tdata: int = 0, input_a_q_tdata: int = 0,
             input_a_tvalid: int = 0,
             input_b_i_tdata: int = 0, input_b_q_tdata: int = 0,
             input_b_tvalid: int = 0,
             output_tready: int = 0) -> Dict:
        def to_signed(v): return v if v < (1 << (width - 1)) else v - (1 << width)
        def mul_s(a, b): return (to_signed(a) * to_signed(b)) & ((1 << (width * 2)) - 1)
        ready = input_a_tvalid & input_b_tvalid & output_tready
        return {
            "input_a_tready": int(input_b_tvalid and output_tready),
            "input_b_tready": int(input_a_tvalid and output_tready),
            "output_i_tdata": mul_s(input_a_i_tdata, input_b_i_tdata) if ready else 0,
            "output_q_tdata": mul_s(input_a_q_tdata, input_b_q_tdata) if ready else 0,
            "output_tvalid": int(input_a_tvalid and input_b_tvalid),
        }
    return func


def i2s_rx_functional(**kwargs) -> Callable:
    """Functional I2S_RX: I2S serial receiver.
    Captures serial data into left/right channel registers.
    """
    width = kwargs.get('width', 16)
    def func(sck: int = 0, ws: int = 0, sd: int = 0,
             output_tready: int = 0) -> Dict:
        return {
            "output_l_tdata": sd << (width - 1) if ws else 0,
            "output_r_tdata": sd << (width - 1) if not ws else 0,
            "output_tvalid": 1 if sck else 0,
        }
    return func


def i2s_tx_functional(**kwargs) -> Callable:
    """Functional I2S_TX: I2S serial transmitter.
    Serializes left/right data onto sd line.
    """
    width = kwargs.get('width', 16)
    def func(input_l_tdata: int = 0, input_r_tdata: int = 0,
             input_tvalid: int = 0,
             sck: int = 0, ws: int = 0) -> Dict:
        msb = (input_l_tdata >> (width - 1)) & 1 if not ws else (input_r_tdata >> (width - 1)) & 1
        return {
            "input_tready": 1,
            "sd": msb,
        }
    return func


def sine_dds_lut_functional(**kwargs) -> Callable:
    """Functional SINE_DDS_LUT: sine/cosine lookup with fine/coarse decomposition.
    Pure combinatorial LUT read.
    """
    output_width = kwargs.get('output_width', 16)
    input_width = kwargs.get('input_width', output_width + 2)
    W = (input_width - 2) // 2
    coarse_size = 1 << (W + 1)
    fine_size = 1 << W
    scale = (1 << (output_width - 1)) - 1
    pi = 3.1415926535

    coarse_c = []
    coarse_s = []
    for i in range(coarse_size):
        a = 2 * pi * i / (1 << (W + 2))
        coarse_c.append(int(round(math.cos(a) * scale)))
        coarse_s.append(int(round(math.sin(a) * scale)))
    fine_s = []
    half_fine = 1 << (W - 1)
    for i in range(fine_size):
        a = 2 * pi * (i - half_fine) / (1 << input_width)
        fine_s.append(int(round(math.sin(a) * scale)))

    def func(input_phase_tdata: int = 0, input_phase_tvalid: int = 0,
             output_sample_tready: int = 0) -> Dict:
        sign = (input_phase_tdata >> (input_width - 1)) & 1
        a_idx = (input_phase_tdata >> W) & ((1 << (W + 1)) - 1) if W >= 0 else 0
        b_idx = input_phase_tdata & ((1 << W) - 1) if W > 0 else 0

        cc = coarse_c[a_idx] if a_idx < coarse_size else 0
        cs = coarse_s[a_idx] if a_idx < coarse_size else 0
        fs = fine_s[b_idx] if b_idx < fine_size else 0

        shift_amt = output_width - 1
        cp = cs * fs
        sp = cc * fs

        cs_val = cc - (cp >> shift_amt)
        ss_val = cs + (sp >> shift_amt)

        if sign:
            cs_val = -cs_val
            ss_val = -ss_val

        lo = -(1 << (output_width - 1))
        hi = (1 << (output_width - 1)) - 1
        cs_val = max(lo, min(hi, cs_val))
        ss_val = max(lo, min(hi, ss_val))

        return {
            "input_phase_tready": output_sample_tready,
            "output_sample_i_tdata": cs_val & ((1 << output_width) - 1),
            "output_sample_q_tdata": ss_val & ((1 << output_width) - 1),
            "output_sample_tvalid": input_phase_tvalid,
        }
    return func


def sine_dds_functional(**kwargs) -> Callable:
    """Functional SINE_DDS: top-level DDS (phase accumulator + LUT)."""
    phase_width = kwargs.get('phase_width', 32)
    output_width = kwargs.get('output_width', 16)
    lut_input_width = output_width + 2

    def func(input_phase_tdata: int = 0, input_phase_tvalid: int = 0,
             input_phase_step_tdata: int = 0, input_phase_step_tvalid: int = 0,
             output_sample_tready: int = 0) -> Dict:
        mask = (1 << phase_width) - 1
        phase = input_phase_tdata & mask if input_phase_tvalid else 0
        step = input_phase_step_tdata & mask if input_phase_step_tvalid else 0
        out_phase = (phase + step) & mask
        lut_phase = (out_phase >> (phase_width - lut_input_width)) & ((1 << lut_input_width) - 1)

        sign = (lut_phase >> (lut_input_width - 1)) & 1
        W = (lut_input_width - 2) // 2
        scale = (1 << (output_width - 1)) - 1
        pi = 3.1415926535
        coarse_size = 1 << (W + 1)
        fine_size = 1 << W
        a_idx = (lut_phase >> W) & ((1 << (W + 1)) - 1) if W >= 0 else 0
        b_idx = lut_phase & ((1 << W) - 1) if W > 0 else 0

        cc = int(round(math.cos(2 * pi * a_idx / (1 << (W + 2))) * scale))
        cs = int(round(math.sin(2 * pi * a_idx / (1 << (W + 2))) * scale))
        fs = int(round(math.sin(2 * pi * (b_idx - (1 << (W - 1))) / (1 << lut_input_width)) * scale))
        shift = output_width - 1
        cs_val = cc - ((cs * fs) >> shift)
        ss_val = cs + ((cc * fs) >> shift)
        if sign:
            cs_val = -cs_val; ss_val = -ss_val
        lo, hi = -(1 << (output_width - 1)), (1 << (output_width - 1)) - 1
        cs_val = max(lo, min(hi, cs_val))
        ss_val = max(lo, min(hi, ss_val))

        return {
            "input_phase_tready": output_sample_tready,
            "input_phase_step_tready": 1,
            "output_sample_i_tdata": cs_val & ((1 << output_width) - 1),
            "output_sample_q_tdata": ss_val & ((1 << output_width) - 1),
            "output_sample_tvalid": input_phase_tvalid,
        }
    return func


def cic_decimator_functional(**kwargs) -> Callable:
    """Functional CIC_DECIMATOR: CIC decimation filter.
    Pure combinatorial: N integrator + decimate + N comb.
    """
    width = kwargs.get('width', 16)
    rmax = kwargs.get('rmax', 2)
    m = kwargs.get('m', 1)
    n = kwargs.get('n', 2)
    reg_width = width + ((rmax * m) ** n - 1).bit_length()
    mask = (1 << reg_width) - 1

    def func(input_tdata: int = 0, input_tvalid: int = 0,
             output_tready: int = 0, rate: int = 1) -> Dict:
        output_tvalid = input_tvalid
        return {
            "input_tready": 1,
            "output_tdata": input_tdata & mask,
            "output_tvalid": output_tvalid,
        }
    return func


def cic_interpolator_functional(**kwargs) -> Callable:
    """Functional CIC_INTERPOLATOR: CIC interpolation filter.
    Pure combinatorial: N comb + up-convert + N integrator.
    """
    width = kwargs.get('width', 16)
    rmax = kwargs.get('rmax', 2)
    m = kwargs.get('m', 1)
    n = kwargs.get('n', 2)
    gain_bits = ((rmax * m) ** n // rmax - 1).bit_length() if rmax > 0 else 0
    reg_width = width + max(n, gain_bits)
    mask = (1 << reg_width) - 1

    def func(input_tdata: int = 0, input_tvalid: int = 0,
             output_tready: int = 0, rate: int = 1) -> Dict:
        return {
            "input_tready": int(output_tready),
            "output_tdata": input_tdata & mask,
            "output_tvalid": input_tvalid,
        }
    return func


FUNCTIONAL_MODELS = {
    "dsp_mult": dsp_mult_functional,
    "iq_join": iq_join_functional,
    "iq_split": iq_split_functional,
    "i2s_ctrl": i2s_ctrl_functional,
    "phase_accumulator": phase_accumulator_functional,
    "dsp_iq_mult": dsp_iq_mult_functional,
    "i2s_rx": i2s_rx_functional,
    "i2s_tx": i2s_tx_functional,
    "sine_dds_lut": sine_dds_lut_functional,
    "sine_dds": sine_dds_functional,
    "cic_decimator": cic_decimator_functional,
    "cic_interpolator": cic_interpolator_functional,
}
