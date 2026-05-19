"""
skills.fft.models — FFT Golden Reference Models

Cycle-accurate Python simulators for all FFT modules:
  FFTButterfly, FFTDelayBuffer, FFTMultiply, FFTTwiddle,
  FFTSdfUnit, FFTSdfUnit2, FFTController

Based on ref_rtl/fft/verilog/ (Radix-2^2 SDF pipeline).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


def log2_int(x: int) -> int:
    """Return ceil(log2(x)), i.e. bit width needed to represent x-1."""
    return max(x - 1, 0).bit_length()


def _to_signed(val: int, width: int) -> int:
    """Convert unsigned int to signed Python int."""
    if val & (1 << (width - 1)):
        return val - (1 << width)
    return val


def _to_unsigned(val: int, width: int) -> int:
    """Convert signed Python int to unsigned bit representation."""
    return val & ((1 << width) - 1)


def _sra(val: int, shift: int, width: int) -> int:
    """Arithmetic right shift, preserving sign."""
    return _to_signed(val, width) >> shift


def _sat(val: int, width: int) -> int:
    """Saturate signed value to width bits."""
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    return max(lo, min(hi, val))


def _generate_twiddle(N: int, width: int) -> Tuple[List[int], List[int]]:
    """Generate twiddle factor tables: W_N^k = cos(-2*pi*k/N) + j*sin(-2*pi*k/N)."""
    re_table = []
    im_table = []
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    for k in range(N):
        ang = -2.0 * math.pi * k / N
        re_f = math.cos(ang)
        im_f = math.sin(ang)
        re_q = int(round(re_f * (1 << (width - 1))))
        im_q = int(round(im_f * (1 << (width - 1))))
        re_table.append(_to_unsigned(max(lo, min(hi, re_q)), width))
        im_table.append(_to_unsigned(max(lo, min(hi, im_q)), width))
    return re_table, im_table


# =====================================================================
# FFTButterfly Model
# =====================================================================

class FFTButterflyModel:
    """Complex radix-2 butterfly with scaling.

    y0 = (x0 + x1 + RH) >>> 1
    y1 = (x0 - x1 + RH) >>> 1
    """

    def __init__(self, width: int = 16, rh: int = 0):
        self.width = width
        self.rh = rh

    def step(
        self,
        x0_re: int = 0,
        x0_im: int = 0,
        x1_re: int = 0,
        x1_im: int = 0,
    ) -> Tuple[int, int, int, int]:
        w = self.width
        add_re = _to_signed(x0_re, w) + _to_signed(x1_re, w)
        add_im = _to_signed(x0_im, w) + _to_signed(x1_im, w)
        sub_re = _to_signed(x0_re, w) - _to_signed(x1_re, w)
        sub_im = _to_signed(x0_im, w) - _to_signed(x1_im, w)

        y0_re = _to_unsigned(_sra(add_re + self.rh, 1, w + 1), w)
        y0_im = _to_unsigned(_sra(add_im + self.rh, 1, w + 1), w)
        y1_re = _to_unsigned(_sra(sub_re + self.rh, 1, w + 1), w)
        y1_im = _to_unsigned(_sra(sub_im + self.rh, 1, w + 1), w)

        return y0_re, y0_im, y1_re, y1_im


# =====================================================================
# FFTDelayBuffer Model
# =====================================================================

class FFTDelayBufferModel:
    """Shift-register delay line."""

    def __init__(self, depth: int = 32, width: int = 16):
        self.depth = depth
        self.width = width
        self.buf_re = [0] * depth
        self.buf_im = [0] * depth

    def step(
        self,
        di_re: int = 0,
        di_im: int = 0,
    ) -> Tuple[int, int]:
        for i in range(self.depth - 1, 0, -1):
            self.buf_re[i] = self.buf_re[i - 1]
            self.buf_im[i] = self.buf_im[i - 1]
        if self.depth > 0:
            self.buf_re[0] = di_re
            self.buf_im[0] = di_im
        do_re = self.buf_re[self.depth - 1] if self.depth > 0 else di_re
        do_im = self.buf_im[self.depth - 1] if self.depth > 0 else di_im
        return do_re, do_im


# =====================================================================
# FFTMultiply Model
# =====================================================================

class FFTMultiplyModel:
    """Complex multiplier: (a_re + j*a_im) * (b_re + j*b_im).

    4 real multiplications, scaled back to width bits by >>>(width-1).
    """

    def __init__(self, width: int = 16):
        self.width = width

    def step(
        self,
        a_re: int = 0,
        a_im: int = 0,
        b_re: int = 0,
        b_im: int = 0,
    ) -> Tuple[int, int]:
        w = self.width
        arbr = _to_signed(a_re, w) * _to_signed(b_re, w)
        arbi = _to_signed(a_re, w) * _to_signed(b_im, w)
        aibr = _to_signed(a_im, w) * _to_signed(b_re, w)
        aibi = _to_signed(a_im, w) * _to_signed(b_im, w)

        sc_arbr = _sra(arbr, w - 1, w * 2)
        sc_arbi = _sra(arbi, w - 1, w * 2)
        sc_aibr = _sra(aibr, w - 1, w * 2)
        sc_aibi = _sra(aibi, w - 1, w * 2)

        m_re = _to_unsigned(_sat(_to_signed(sc_arbr, w) - _to_signed(sc_aibi, w), w), w)
        m_im = _to_unsigned(_sat(_to_signed(sc_arbi, w) + _to_signed(sc_aibr, w), w), w)
        return m_re, m_im


# =====================================================================
# FFTTwiddle Model
# =====================================================================

class FFTTwiddleModel:
    """Twiddle factor ROM: W_N^k lookup table."""

    def __init__(self, N: int = 64, width: int = 16):
        self.N = N
        self.width = width
        self.re_table, self.im_table = _generate_twiddle(N, width)

    def lookup(self, addr: int) -> Tuple[int, int]:
        idx = addr % self.N
        return self.re_table[idx], self.im_table[idx]


# =====================================================================
# FFTSdfUnit Model (Radix-2^2 SDF Unit)
# =====================================================================

class FFTSdfUnitModel:
    """Radix-2^2 Single-Path Delay Feedback Unit.

    Matches ref_rtl/fft/verilog/SdfUnit.v behavior.
    """

    def __init__(self, N: int = 64, M: int = 64, width: int = 16):
        self.N = N
        self.M = M
        self.width = width
        log_n = log2_int(N)
        log_m = log2_int(M)

        self.bf1_model = FFTButterflyModel(width, rh=0)
        self.bf2_model = FFTButterflyModel(width, rh=1)
        self.db1_model = FFTDelayBufferModel(1 << (log_m - 1) if log_m >= 1 else 1, width)
        self.db2_model = FFTDelayBufferModel(1 << (log_m - 2) if log_m >= 2 else 1, width)
        self.tw_model = FFTTwiddleModel(N, width)
        self.mu_model = FFTMultiplyModel(width)

        self.di_count = 0
        self.bf1_bf = 0
        self.bf1_sp_en = 0
        self.bf1_count = 0
        self.bf2_bf = 0
        self.bf2_sp_en = 0
        self.bf2_count = 0
        self.bf2_start = 0
        self.bf2_do_en = 0
        self.mu_en = 0
        self.mu_do_en = 0

    def step(
        self,
        di_en: int = 0,
        di_re: int = 0,
        di_im: int = 0,
    ) -> Tuple[int, int, int]:
        log_n = log2_int(self.N)
        log_m = log2_int(self.M)
        w = self.width

        # Save registered values (state at start of cycle)
        prev_bf1_bf = self.bf1_bf
        prev_bf1_sp_en = self.bf1_sp_en
        prev_bf1_count = self.bf1_count
        prev_bf2_bf = self.bf2_bf
        prev_bf2_sp_en = self.bf2_sp_en
        prev_bf2_count = self.bf2_count
        prev_bf2_start = self.bf2_start
        prev_bf2_do_en = self.bf2_do_en
        prev_mu_do_en = self.mu_do_en

        # --- BF1 control ---
        # Compute next-cycle bf1_bf (registered in RTL: bf1_bf_r <= di_count[...] & 1)
        new_bf1_bf = (self.di_count >> (log_m - 1)) & 1 if log_m >= 1 else 0
        bf1_bf = prev_bf1_bf  # Use registered value for combinatorial logic

        # BF1 inputs
        if bf1_bf:
            bf1_x0_re, bf1_x0_im = self.db1_model.step(di_re, di_im)
            bf1_x1_re, bf1_x1_im = di_re, di_im
        else:
            _, _ = self.db1_model.step(di_re, di_im)
            bf1_x0_re, bf1_x0_im = 0, 0
            bf1_x1_re, bf1_x1_im = 0, 0

        y0_re, y0_im, y1_re, y1_im = self.bf1_model.step(
            bf1_x0_re, bf1_x0_im, bf1_x1_re, bf1_x1_im)

        # DB1 input
        db1_di_re = y1_re if bf1_bf else di_re
        db1_di_im = y1_im if bf1_bf else di_im

        # BF1 single-path output
        bf1_mj = ((prev_bf1_count >> (log_m - 2)) & 0x3) == 3 if log_m >= 2 else False
        if bf1_bf:
            bf1_sp_re, bf1_sp_im = y0_re, y0_im
        elif bf1_mj:
            bf1_sp_re, bf1_sp_im = 0, _to_unsigned(-_to_signed(self.db1_model.buf_re[-1], w), w)
        else:
            bf1_sp_re, bf1_sp_im = self.db1_model.buf_re[-1], self.db1_model.buf_im[-1]

        # BF1 enable follows bf1_bf (registered)
        # BF1 counter tracks output position within active BF1 phase
        if new_bf1_bf:
            self.bf1_sp_en = 1
            self.bf1_count = prev_bf1_count + 1
        else:
            self.bf1_sp_en = 0
            self.bf1_count = 0

        # BF2 control (mirrors BF1 timing after clock edge)
        bf2_bf = new_bf1_bf  # bf2_bf_r <= bf1_bf_r

        # BF2 inputs
        bf1_do_re, bf1_do_im = bf1_sp_re, bf1_sp_im
        if bf2_bf:
            bf2_x0_re, bf2_x0_im = self.db2_model.step(bf1_do_re, bf1_do_im)
            bf2_x1_re, bf2_x1_im = bf1_do_re, bf1_do_im
        else:
            _, _ = self.db2_model.step(bf1_do_re, bf1_do_im)
            bf2_x0_re, bf2_x0_im = 0, 0
            bf2_x1_re, bf2_x1_im = 0, 0

        y20_re, y20_im, y21_re, y21_im = self.bf2_model.step(
            bf2_x0_re, bf2_x0_im, bf2_x1_re, bf2_x1_im)

        # DB2 input
        db2_di_re = y21_re if bf2_bf else bf1_do_re
        db2_di_im = y21_im if bf2_bf else bf1_do_im

        # BF2 single-path output
        if bf2_bf:
            bf2_sp_re, bf2_sp_im = y20_re, y20_im
        else:
            bf2_sp_re, bf2_sp_im = self.db2_model.buf_re[-1], self.db2_model.buf_im[-1]

        # Update BF2 registers
        if bf2_bf:
            self.bf2_sp_en = 1
            self.bf2_count = prev_bf2_count + 1
        else:
            self.bf2_sp_en = 0

        self.bf1_bf = new_bf1_bf
        self.bf2_bf = new_bf1_bf  # mirrors bf1_bf_r
        self.bf2_start = new_bf1_bf
        self.bf2_do_en = prev_bf2_sp_en

        # --- Multiplication ---
        tw_sel_1 = (prev_bf2_count >> (log_m - 2)) & 1 if log_m >= 2 else 0
        tw_sel_0 = (prev_bf2_count >> (log_m - 1)) & 1 if log_m >= 1 else 0
        tw_num = (prev_bf2_count << (log_n - log_m)) & ((1 << log_n) - 1)
        tw_addr = tw_num * ((tw_sel_1 << 1) | tw_sel_0)

        tw_re, tw_im = self.tw_model.lookup(tw_addr)

        bf2_do_re, bf2_do_im = bf2_sp_re, bf2_sp_im

        # Multiply enable (bypass when tw_addr == 0)
        self.mu_en = 1 if tw_addr != 0 else 0

        if self.mu_en:
            mu_m_re, mu_m_im = self.mu_model.step(bf2_do_re, bf2_do_im, tw_re, tw_im)
        else:
            mu_m_re, mu_m_im = bf2_do_re, bf2_do_im

        mu_do_re = mu_m_re if self.mu_en else bf2_do_re
        mu_do_im = mu_m_im if self.mu_en else bf2_do_im

        self.mu_do_en = prev_bf2_do_en

        # Update di_count
        if di_en:
            self.di_count = (self.di_count + 1) & ((1 << log_n) - 1)
        else:
            self.di_count = 0

        # Output (bypass multiply when LOG_M == 2)
        if log_m == 2:
            return self.bf2_do_en, bf2_do_re, bf2_do_im
        else:
            return self.mu_do_en, mu_do_re, mu_do_im


# =====================================================================
# FFTSdfUnit2 Model (Radix-2 SDF, no twiddle multiply)
# =====================================================================

class FFTSdfUnit2Model:
    """Radix-2 SDF Unit for M=2 (no twiddle multiply).

    Matches ref_rtl/fft/verilog/SdfUnit2.v behavior.
    """

    def __init__(self, N: int = 64, width: int = 16):
        self.width = width
        self.bf_model = FFTButterflyModel(width, rh=0)
        self.db_model = FFTDelayBufferModel(1, width)

        self.bf_en = 0
        self.bf_sp_en = 0
        self.do_en = 0

    def step(
        self,
        di_en: int = 0,
        di_re: int = 0,
        di_im: int = 0,
    ) -> Tuple[int, int, int]:
        if self.bf_en:
            db_do_re, db_do_im = self.db_model.step(di_re, di_im)
            x0_re, x0_im = db_do_re, db_do_im
            x1_re, x1_im = di_re, di_im
        else:
            _, _ = self.db_model.step(di_re, di_im)
            x0_re, x0_im = 0, 0
            x1_re, x1_im = 0, 0

        y0_re, y0_im, y1_re, y1_im = self.bf_model.step(
            x0_re, x0_im, x1_re, x1_im)

        if self.bf_en:
            bf_sp_re, bf_sp_im = y0_re, y0_im
        else:
            bf_sp_re, bf_sp_im = self.db_model.buf_re[0], self.db_model.buf_im[0]

        prev_bf_sp_en = self.bf_sp_en
        if di_en:
            self.bf_en = 1 - self.bf_en
        else:
            self.bf_en = 0
        self.bf_sp_en = di_en
        self.do_en = prev_bf_sp_en

        return self.do_en, bf_sp_re, bf_sp_im


# =====================================================================
# FFTController Model (Top-level)
# =====================================================================

class FFTControllerModel:
    """Top-level parameterized FFT accelerator.

    Chains SdfUnit and SdfUnit2 stages based on N.
    """

    def __init__(self, N: int = 64, width: int = 16):
        self.N = N
        self.width = width
        log_n = log2_int(N)
        num_su = log_n // 2
        need_su2 = (log_n % 2) == 1

        self.stages = []
        for i in range(num_su):
            m = N >> (2 * i)
            self.stages.append(FFTSdfUnitModel(N, m, width))
        if need_su2:
            self.stages.append(FFTSdfUnit2Model(N, width))

    def step(
        self,
        di_en: int = 0,
        di_re: int = 0,
        di_im: int = 0,
    ) -> Tuple[int, int, int]:
        # First stage receives the actual input enable; subsequent stages
        # always process (RTL data flows continuously through the pipeline).
        cur_re = di_re
        cur_im = di_im
        cur_en = di_en
        for i, stage in enumerate(self.stages):
            cur_en, cur_re, cur_im = stage.step(cur_en if i == 0 else 1, cur_re, cur_im)
        return cur_en, cur_re, cur_im
