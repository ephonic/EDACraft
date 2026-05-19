"""
skills.fft.behaviors — FFT Behavior Templates

7 behavior templates for FFT PE types:
  fft_butterfly, fft_delay_buffer, fft_multiply, fft_twiddle,
  fft_sdf_unit, fft_sdf_unit2, fft_controller

All templates register into TemplateRegistry at import time.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Optional, Tuple

from rtlgen.behaviors import TemplateRegistry
from rtlgen.arch_def import CycleContext


# =====================================================================
# Helper functions (mirror models.py)
# =====================================================================

def _log2_int(x: int) -> int:
    return max(x - 1, 0).bit_length()


def _to_signed(val: int, width: int) -> int:
    if val & (1 << (width - 1)):
        return val - (1 << width)
    return val


def _to_unsigned(val: int, width: int) -> int:
    return val & ((1 << width) - 1)


def _sra(val: int, shift: int, width: int) -> int:
    return _to_signed(val, width) >> shift


def _sat(val: int, width: int) -> int:
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    return max(lo, min(hi, val))


def _generate_twiddle(N: int, width: int) -> Tuple[list, list]:
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
# FFT_BUTTERFLY — Complex radix-2 butterfly with scaling
# =====================================================================

def fft_butterfly_template(
    width: int = 16,
    rh: int = 0,
) -> Callable[[CycleContext], None]:
    """Complex radix-2 butterfly.

    y0 = (x0 + x1 + RH) >>> 1
    y1 = (x0 - x1 + RH) >>> 1
    """
    def behavior(ctx: CycleContext):
        x0_re = ctx.get_input("x0_re", 0)
        x0_im = ctx.get_input("x0_im", 0)
        x1_re = ctx.get_input("x1_re", 0)
        x1_im = ctx.get_input("x1_im", 0)

        add_re = _to_signed(x0_re, width) + _to_signed(x1_re, width)
        add_im = _to_signed(x0_im, width) + _to_signed(x1_im, width)
        sub_re = _to_signed(x0_re, width) - _to_signed(x1_re, width)
        sub_im = _to_signed(x0_im, width) - _to_signed(x1_im, width)

        y0_re = _to_unsigned(_sra(add_re + rh, 1, width + 1), width)
        y0_im = _to_unsigned(_sra(add_im + rh, 1, width + 1), width)
        y1_re = _to_unsigned(_sra(sub_re + rh, 1, width + 1), width)
        y1_im = _to_unsigned(_sra(sub_im + rh, 1, width + 1), width)

        ctx.set_output("y0_re", y0_re)
        ctx.set_output("y0_im", y0_im)
        ctx.set_output("y1_re", y1_re)
        ctx.set_output("y1_im", y1_im)

    return behavior


# =====================================================================
# FFT_DELAY_BUFFER — Shift-register delay line
# =====================================================================

def fft_delay_buffer_template(
    depth: int = 32,
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Shift-register delay line.

    State: delay_buf (list of `depth` unsigned values).
    """
    def behavior(ctx: CycleContext):
        di_re = ctx.get_input("di_re", 0)
        di_im = ctx.get_input("di_im", 0)

        buf_re = []
        buf_im = []
        for i in range(depth):
            buf_re.append(ctx.get_state(f"buf_re_{i}", 0))
            buf_im.append(ctx.get_state(f"buf_im_{i}", 0))

        # Shift
        for i in range(depth - 1, 0, -1):
            ctx.set_state(f"buf_re_{i}", buf_re[i - 1])
            ctx.set_state(f"buf_im_{i}", buf_im[i - 1])
        if depth > 0:
            ctx.set_state(f"buf_re_0", di_re)
            ctx.set_state(f"buf_im_0", di_im)

        do_re = buf_re[depth - 1] if depth > 0 else di_re
        do_im = buf_im[depth - 1] if depth > 0 else di_im
        ctx.set_output("do_re", do_re)
        ctx.set_output("do_im", do_im)

    return behavior


# =====================================================================
# FFT_MULTIPLY — Complex multiplier (4 real multiplies)
# =====================================================================

def fft_multiply_template(
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Complex multiplier: (a_re + j*a_im) * (b_re + j*b_im).

    4 real multiplications, scaled back to width bits by >>>(width-1).
    """
    def behavior(ctx: CycleContext):
        a_re = ctx.get_input("a_re", 0)
        a_im = ctx.get_input("a_im", 0)
        b_re = ctx.get_input("b_re", 0)
        b_im = ctx.get_input("b_im", 0)

        arbr = _to_signed(a_re, width) * _to_signed(b_re, width)
        arbi = _to_signed(a_re, width) * _to_signed(b_im, width)
        aibr = _to_signed(a_im, width) * _to_signed(b_re, width)
        aibi = _to_signed(a_im, width) * _to_signed(b_im, width)

        sc_arbr = _sra(arbr, width - 1, width * 2)
        sc_arbi = _sra(arbi, width - 1, width * 2)
        sc_aibr = _sra(aibr, width - 1, width * 2)
        sc_aibi = _sra(aibi, width - 1, width * 2)

        m_re = _to_unsigned(_sat(_to_signed(sc_arbr, width) - _to_signed(sc_aibi, width), width), width)
        m_im = _to_unsigned(_sat(_to_signed(sc_arbi, width) + _to_signed(sc_aibr, width), width), width)

        ctx.set_output("m_re", m_re)
        ctx.set_output("m_im", m_im)

    return behavior


# =====================================================================
# FFT_TWIDDLE — Twiddle factor ROM
# =====================================================================

def fft_twiddle_template(
    N: int = 64,
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Twiddle factor ROM: W_N^k lookup table."""
    re_table, im_table = _generate_twiddle(N, width)

    def behavior(ctx: CycleContext):
        addr = ctx.get_input("addr", 0)
        idx = addr % N
        ctx.set_output("tw_re", re_table[idx])
        ctx.set_output("tw_im", im_table[idx])

    return behavior


# =====================================================================
# FFT_SDF_UNIT — Radix-2^2 Single-Path Delay Feedback Unit
# =====================================================================

def fft_sdf_unit_template(
    N: int = 64,
    M: int = 64,
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Radix-2^2 SDF Unit: BF1→DB1→BF2→DB2→Multiply→Output."""
    log_n = _log2_int(N)
    log_m = _log2_int(M)
    db1_depth = 1 << (log_m - 1) if log_m >= 1 else 1
    db2_depth = 1 << (log_m - 2) if log_m >= 2 else 1

    # Pre-compute twiddle tables
    re_table, im_table = _generate_twiddle(N, width)

    def behavior(ctx: CycleContext):
        di_en = ctx.get_input("di_en", 0)
        di_re = ctx.get_input("di_re", 0)
        di_im = ctx.get_input("di_im", 0)

        # Read all state
        di_count = ctx.get_state("di_count", 0)
        bf1_sp_en = ctx.get_state("bf1_sp_en", 0)
        bf1_count = ctx.get_state("bf1_count", 0)
        bf2_bf = ctx.get_state("bf2_bf", 0)
        bf2_sp_en = ctx.get_state("bf2_sp_en", 0)
        bf2_count = ctx.get_state("bf2_count", 0)
        bf2_start = ctx.get_state("bf2_start", 0)
        bf2_do_en = ctx.get_state("bf2_do_en", 0)
        mu_en = ctx.get_state("mu_en", 0)
        mu_do_en = ctx.get_state("mu_do_en", 0)

        # Delay buffer state
        db1_buf_re = [ctx.get_state(f"db1_buf_re_{i}", 0) for i in range(db1_depth)]
        db1_buf_im = [ctx.get_state(f"db1_buf_im_{i}", 0) for i in range(db1_depth)]
        db2_buf_re = [ctx.get_state(f"db2_buf_re_{i}", 0) for i in range(db2_depth)]
        db2_buf_im = [ctx.get_state(f"db2_buf_im_{i}", 0) for i in range(db2_depth)]

        prev_bf1_sp_en = bf1_sp_en
        prev_bf1_count = bf1_count
        prev_bf2_bf = bf2_bf
        prev_bf2_sp_en = bf2_sp_en
        prev_bf2_count = bf2_count
        prev_bf2_start = bf2_start
        prev_bf2_do_en = bf2_do_en
        prev_mu_do_en = mu_do_en

        # --- BF1 control ---
        bf1_bf = (di_count >> (log_m - 1)) & 1 if log_m >= 1 else 0

        # DB1 shift
        if bf1_bf:
            for i in range(db1_depth - 1, 0, -1):
                db1_buf_re[i] = db1_buf_re[i - 1]
                db1_buf_im[i] = db1_buf_im[i - 1]
            if db1_depth > 0:
                db1_buf_re[0] = di_re
                db1_buf_im[0] = di_im
            bf1_x0_re, bf1_x0_im = db1_buf_re[0], db1_buf_im[0]
            bf1_x1_re, bf1_x1_im = di_re, di_im
        else:
            for i in range(db1_depth - 1, 0, -1):
                db1_buf_re[i] = db1_buf_re[i - 1]
                db1_buf_im[i] = db1_buf_im[i - 1]
            if db1_depth > 0:
                db1_buf_re[0] = di_re
                db1_buf_im[0] = di_im
            bf1_x0_re, bf1_x0_im = 0, 0
            bf1_x1_re, bf1_x1_im = 0, 0

        # BF1 butterfly
        add_re = _to_signed(bf1_x0_re, width) + _to_signed(bf1_x1_re, width)
        add_im = _to_signed(bf1_x0_im, width) + _to_signed(bf1_x1_im, width)
        sub_re = _to_signed(bf1_x0_re, width) - _to_signed(bf1_x1_re, width)
        sub_im = _to_signed(bf1_x0_im, width) - _to_signed(bf1_x1_im, width)

        y0_re = _to_unsigned(_sra(add_re, 1, width + 1), width)
        y0_im = _to_unsigned(_sra(add_im, 1, width + 1), width)
        y1_re = _to_unsigned(_sra(sub_re + 1, 1, width + 1), width)  # BF2 uses RH=1
        y1_im = _to_unsigned(_sra(sub_im + 1, 1, width + 1), width)

        # DB1 input
        db1_di_re = y1_re if bf1_bf else di_re
        db1_di_im = y1_im if bf1_bf else di_im

        # BF1 single-path output
        bf1_mj = ((prev_bf1_count >> (log_m - 2)) & 0x3) == 3 if log_m >= 2 else False
        if bf1_bf:
            bf1_sp_re, bf1_sp_im = y0_re, y0_im
        elif bf1_mj:
            bf1_sp_re = 0
            bf1_sp_im = _to_unsigned(-_to_signed(db1_buf_re[-1], width), width)
        else:
            bf1_sp_re = db1_buf_re[-1]
            bf1_sp_im = db1_buf_im[-1]

        # BF1 start/end
        bf1_start_val = (di_count == (1 << (log_m - 1)) - 1) if log_m >= 1 else 0
        bf1_end = (prev_bf1_count == (1 << log_n) - 1)

        new_bf1_sp_en = bf1_sp_en
        if bf1_start_val:
            new_bf1_sp_en = 1
        elif bf1_end:
            new_bf1_sp_en = 0
        new_bf1_count = (prev_bf1_count + 1) if new_bf1_sp_en else 0

        # BF2 control
        bf2_bf_val = (prev_bf1_count >> (log_m - 2)) & 1 if log_m >= 2 else 0
        bf1_do_re, bf1_do_im = bf1_sp_re, bf1_sp_im

        # DB2 shift
        if bf2_bf_val:
            for i in range(db2_depth - 1, 0, -1):
                db2_buf_re[i] = db2_buf_re[i - 1]
                db2_buf_im[i] = db2_buf_im[i - 1]
            if db2_depth > 0:
                db2_buf_re[0] = bf1_do_re
                db2_buf_im[0] = bf1_do_im
            bf2_x0_re, bf2_x0_im = db2_buf_re[0], db2_buf_im[0]
            bf2_x1_re, bf2_x1_im = bf1_do_re, bf1_do_im
        else:
            for i in range(db2_depth - 1, 0, -1):
                db2_buf_re[i] = db2_buf_re[i - 1]
                db2_buf_im[i] = db2_buf_im[i - 1]
            if db2_depth > 0:
                db2_buf_re[0] = bf1_do_re
                db2_buf_im[0] = bf1_do_im
            bf2_x0_re, bf2_x0_im = 0, 0
            bf2_x1_re, bf2_x1_im = 0, 0

        # BF2 butterfly (RH=1)
        add2_re = _to_signed(bf2_x0_re, width) + _to_signed(bf2_x1_re, width)
        add2_im = _to_signed(bf2_x0_im, width) + _to_signed(bf2_x1_im, width)
        sub2_re = _to_signed(bf2_x0_re, width) - _to_signed(bf2_x1_re, width)
        sub2_im = _to_signed(bf2_x0_im, width) - _to_signed(bf2_x1_im, width)

        y20_re = _to_unsigned(_sra(add2_re + 1, 1, width + 1), width)
        y20_im = _to_unsigned(_sra(add2_im + 1, 1, width + 1), width)
        y21_re = _to_unsigned(_sra(sub2_re + 1, 1, width + 1), width)
        y21_im = _to_unsigned(_sra(sub2_im + 1, 1, width + 1), width)

        # DB2 input
        db2_di_re = y21_re if bf2_bf_val else bf1_do_re
        db2_di_im = y21_im if bf2_bf_val else bf1_do_im

        # BF2 single-path output
        if bf2_bf_val:
            bf2_sp_re, bf2_sp_im = y20_re, y20_im
        else:
            bf2_sp_re = db2_buf_re[-1]
            bf2_sp_im = db2_buf_im[-1]

        # BF2 start/end
        bf2_start_val = ((prev_bf1_count == (1 << (log_m - 2)) - 1) and prev_bf1_sp_en) if log_m >= 2 else 0
        bf2_end = (prev_bf2_count == (1 << log_n) - 1)

        new_bf2_sp_en = bf2_sp_en
        if bf2_start_val:
            new_bf2_sp_en = 1
        elif bf2_end:
            new_bf2_sp_en = 0
        new_bf2_count = (prev_bf2_count + 1) if new_bf2_sp_en else 0
        new_bf2_do_en = prev_bf2_sp_en

        # --- Multiplication ---
        tw_sel_1 = (prev_bf2_count >> (log_m - 2)) & 1 if log_m >= 2 else 0
        tw_sel_0 = (prev_bf2_count >> (log_m - 1)) & 1 if log_m >= 1 else 0
        tw_num = (prev_bf2_count << (log_n - log_m)) & ((1 << log_n) - 1)
        tw_addr = tw_num * ((tw_sel_1 << 1) | tw_sel_0)

        tw_re = re_table[tw_addr % N]
        tw_im = im_table[tw_addr % N]

        bf2_do_re, bf2_do_im = bf2_sp_re, bf2_sp_im

        new_mu_en = 1 if tw_addr != 0 else 0

        if new_mu_en:
            arbr = _to_signed(bf2_do_re, width) * _to_signed(tw_re, width)
            arbi = _to_signed(bf2_do_re, width) * _to_signed(tw_im, width)
            aibr = _to_signed(bf2_do_im, width) * _to_signed(tw_re, width)
            aibi = _to_signed(bf2_do_im, width) * _to_signed(tw_im, width)

            sc_arbr = _sra(arbr, width - 1, width * 2)
            sc_arbi = _sra(arbi, width - 1, width * 2)
            sc_aibr = _sra(aibr, width - 1, width * 2)
            sc_aibi = _sra(aibi, width - 1, width * 2)

            mu_m_re = _to_unsigned(_sat(_to_signed(sc_arbr, width) - _to_signed(sc_aibi, width), width), width)
            mu_m_im = _to_unsigned(_sat(_to_signed(sc_arbi, width) + _to_signed(sc_aibr, width), width), width)
        else:
            mu_m_re = bf2_do_re
            mu_m_im = bf2_do_im

        mu_do_re = mu_m_re if new_mu_en else bf2_do_re
        mu_do_im = mu_m_im if new_mu_en else bf2_do_im

        new_mu_do_en = prev_bf2_do_en

        # Update di_count
        new_di_count = (di_count + 1) & ((1 << log_n) - 1) if di_en else 0

        # --- Write state ---
        ctx.set_state("di_count", new_di_count)
        ctx.set_state("bf1_sp_en", new_bf1_sp_en)
        ctx.set_state("bf1_count", new_bf1_count)
        ctx.set_state("bf2_bf", bf2_bf_val)
        ctx.set_state("bf2_sp_en", new_bf2_sp_en)
        ctx.set_state("bf2_count", new_bf2_count)
        ctx.set_state("bf2_start", bf2_start_val)
        ctx.set_state("bf2_do_en", new_bf2_do_en)
        ctx.set_state("mu_en", new_mu_en)
        ctx.set_state("mu_do_en", new_mu_do_en)

        for i in range(db1_depth):
            ctx.set_state(f"db1_buf_re_{i}", db1_buf_re[i])
            ctx.set_state(f"db1_buf_im_{i}", db1_buf_im[i])
        for i in range(db2_depth):
            ctx.set_state(f"db2_buf_re_{i}", db2_buf_re[i])
            ctx.set_state(f"db2_buf_im_{i}", db2_buf_im[i])

        # Output
        if log_m == 2:
            ctx.set_output("do_en", new_bf2_do_en)
            ctx.set_output("do_re", bf2_do_re)
            ctx.set_output("do_im", bf2_do_im)
        else:
            ctx.set_output("do_en", new_mu_do_en)
            ctx.set_output("do_re", mu_do_re)
            ctx.set_output("do_im", mu_do_im)

    return behavior


# =====================================================================
# FFT_SDF_UNIT2 — Radix-2 SDF Unit (M=2, no twiddle multiply)
# =====================================================================

def fft_sdf_unit2_template(
    N: int = 64,
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Radix-2 SDF Unit for M=2 (no twiddle multiply)."""
    def behavior(ctx: CycleContext):
        di_en = ctx.get_input("di_en", 0)
        di_re = ctx.get_input("di_re", 0)
        di_im = ctx.get_input("di_im", 0)

        bf_en = ctx.get_state("bf_en", 0)
        bf_sp_en = ctx.get_state("bf_sp_en", 0)
        do_en = ctx.get_state("do_en", 0)
        db_buf_0_re = ctx.get_state("db_buf_0_re", 0)
        db_buf_0_im = ctx.get_state("db_buf_0_im", 0)

        if bf_en:
            x0_re, x0_im = db_buf_0_re, db_buf_0_im
            x1_re, x1_im = di_re, di_im
            new_db_buf_0_re = di_re
            new_db_buf_0_im = di_im
        else:
            x0_re, x0_im = 0, 0
            x1_re, x1_im = 0, 0
            new_db_buf_0_re = di_re
            new_db_buf_0_im = di_im

        # BF butterfly (RH=0)
        add_re = _to_signed(x0_re, width) + _to_signed(x1_re, width)
        add_im = _to_signed(x0_im, width) + _to_signed(x1_im, width)
        sub_re = _to_signed(x0_re, width) - _to_signed(x1_re, width)
        sub_im = _to_signed(x0_im, width) - _to_signed(x1_im, width)

        y0_re = _to_unsigned(_sra(add_re, 1, width + 1), width)
        y0_im = _to_unsigned(_sra(add_im, 1, width + 1), width)
        y1_re = _to_unsigned(_sra(sub_re, 1, width + 1), width)
        y1_im = _to_unsigned(_sra(sub_im, 1, width + 1), width)

        if bf_en:
            bf_sp_re, bf_sp_im = y0_re, y0_im
        else:
            bf_sp_re, bf_sp_im = db_buf_0_re, db_buf_0_im

        prev_bf_sp_en = bf_sp_en
        new_bf_en = (1 - bf_en) if di_en else 0
        new_bf_sp_en = di_en
        new_do_en = prev_bf_sp_en

        ctx.set_state("bf_en", new_bf_en)
        ctx.set_state("bf_sp_en", new_bf_sp_en)
        ctx.set_state("do_en", new_do_en)
        ctx.set_state("db_buf_0_re", new_db_buf_0_re)
        ctx.set_state("db_buf_0_im", new_db_buf_0_im)

        ctx.set_output("do_en", new_do_en)
        ctx.set_output("do_re", bf_sp_re)
        ctx.set_output("do_im", bf_sp_im)

    return behavior


# =====================================================================
# FFT_CONTROLLER — Top-level FFT accelerator
# =====================================================================

def fft_controller_template(
    N: int = 64,
    width: int = 16,
) -> Callable[[CycleContext], None]:
    """Top-level FFT controller: chains SdfUnit and SdfUnit2 stages."""
    log_n = _log2_int(N)
    num_su = log_n // 2
    need_su2 = (log_n % 2) == 1

    def behavior(ctx: CycleContext):
        di_en = ctx.get_input("di_en", 0)
        di_re = ctx.get_input("di_re", 0)
        di_im = ctx.get_input("di_im", 0)

        # Pipeline through stages (combinational within one cycle)
        cur_en = di_en
        cur_re = di_re
        cur_im = di_im

        for i in range(num_su):
            m = N >> (2 * i)
            log_m = _log2_int(m)

            # Read stage state
            stage_prefix = f"su{i}_"
            s_di_count = ctx.get_state(f"{stage_prefix}di_count", 0)
            s_bf1_sp_en = ctx.get_state(f"{stage_prefix}bf1_sp_en", 0)
            s_bf1_count = ctx.get_state(f"{stage_prefix}bf1_count", 0)
            s_bf2_bf = ctx.get_state(f"{stage_prefix}bf2_bf", 0)
            s_bf2_sp_en = ctx.get_state(f"{stage_prefix}bf2_sp_en", 0)
            s_bf2_count = ctx.get_state(f"{stage_prefix}bf2_count", 0)
            s_bf2_start = ctx.get_state(f"{stage_prefix}bf2_start", 0)
            s_bf2_do_en = ctx.get_state(f"{stage_prefix}bf2_do_en", 0)
            s_mu_en = ctx.get_state(f"{stage_prefix}mu_en", 0)
            s_mu_do_en = ctx.get_state(f"{stage_prefix}mu_do_en", 0)

            # Simplified: delegate to per-stage behavior
            # This is a comb pass through the stage — state is managed internally
            # For the behavior template, we pass through and let the RTL handle the pipeline
            pass

        # Output (placeholder — full chaining requires stage-by-stage state)
        ctx.set_output("do_en", cur_en)
        ctx.set_output("do_re", cur_re)
        ctx.set_output("do_im", cur_im)

    return behavior


# =====================================================================
# Register all 7 FFT templates
# =====================================================================

TemplateRegistry.register("fft_butterfly", fft_butterfly_template())
TemplateRegistry.register("fft_delay_buffer", fft_delay_buffer_template())
TemplateRegistry.register("fft_multiply", fft_multiply_template())
TemplateRegistry.register("fft_twiddle", fft_twiddle_template())
TemplateRegistry.register("fft_sdf_unit", fft_sdf_unit_template())
TemplateRegistry.register("fft_sdf_unit2", fft_sdf_unit2_template())
TemplateRegistry.register("fft_controller", fft_controller_template())
