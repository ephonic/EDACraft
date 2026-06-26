"""
skills.fft.cycle_level — Layer 2: Cycle-accurate models.

Pipeline timing and register-accurate behavior for each FFT module.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry


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

def _log2_int(x: int) -> int:
    return max(x - 1, 0).bit_length()


def _generate_twiddle(N: int, width: int) -> Tuple[List[int], List[int]]:
    re_table = []
    im_table = []
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    for k in range(N):
        ang = -2.0 * math.pi * k / N
        re_q = int(round(math.cos(ang) * (1 << (width - 1))))
        im_q = int(round(math.sin(ang) * (1 << (width - 1))))
        re_table.append(_to_unsigned(max(lo, min(hi, re_q)), width))
        im_table.append(_to_unsigned(max(lo, min(hi, im_q)), width))
    return re_table, im_table


def fftbutterfly_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTButterfly: complex radix-2 butterfly (combinatorial)."""
    width = kwargs.get('width', 16)
    rh = kwargs.get('rh', 0)
    def behavior(ctx: CycleContext) -> None:
        x0_re = ctx.get_input('x0_re', 0); x0_im = ctx.get_input('x0_im', 0)
        x1_re = ctx.get_input('x1_re', 0); x1_im = ctx.get_input('x1_im', 0)
        w = width
        add_re = _to_signed(x0_re, w) + _to_signed(x1_re, w)
        add_im = _to_signed(x0_im, w) + _to_signed(x1_im, w)
        sub_re = _to_signed(x0_re, w) - _to_signed(x1_re, w)
        sub_im = _to_signed(x0_im, w) - _to_signed(x1_im, w)
        ctx.set_output('y0_re', _to_unsigned(_sra(add_re + rh, 1, w + 1), w))
        ctx.set_output('y0_im', _to_unsigned(_sra(add_im + rh, 1, w + 1), w))
        ctx.set_output('y1_re', _to_unsigned(_sra(sub_re + rh, 1, w + 1), w))
        ctx.set_output('y1_im', _to_unsigned(_sra(sub_im + rh, 1, w + 1), w))
    return behavior


def fftdelaybuffer_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTDelayBuffer: shift-register delay line."""
    depth = kwargs.get('depth', 32)
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for i in range(depth):
                ctx.state[f'b_re_{i}'] = 0; ctx.state[f'b_im_{i}'] = 0
            return
        di_re = ctx.get_input('di_re', 0); di_im = ctx.get_input('di_im', 0)
        for i in range(depth - 1, 0, -1):
            ctx.state[f'b_re_{i}'] = ctx.state.get(f'b_re_{i-1}', 0)
            ctx.state[f'b_im_{i}'] = ctx.state.get(f'b_im_{i-1}', 0)
        ctx.state['b_re_0'] = di_re
        ctx.state['b_im_0'] = di_im
        do_re = ctx.state.get(f'b_re_{depth-1}', di_re) if depth > 0 else di_re
        do_im = ctx.state.get(f'b_im_{depth-1}', di_im) if depth > 0 else di_im
        ctx.set_output('do_re', do_re)
        ctx.set_output('do_im', do_im)
    return behavior


def fftmultiply_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTMultiply: complex multiplier (combinatorial)."""
    width = kwargs.get('width', 16)
    def behavior(ctx: CycleContext) -> None:
        a_re = ctx.get_input('a_re', 0); a_im = ctx.get_input('a_im', 0)
        b_re = ctx.get_input('b_re', 0); b_im = ctx.get_input('b_im', 0)
        w = width
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
        ctx.set_output('m_re', m_re)
        ctx.set_output('m_im', m_im)
    return behavior


def ffttwiddle_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTTwiddle: twiddle factor ROM lookup (combinatorial)."""
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    re_table, im_table = _generate_twiddle(N, width)

    def behavior(ctx: CycleContext) -> None:
        addr = ctx.get_input('addr', 0)
        idx = addr % N
        ctx.set_output('tw_re', re_table[idx])
        ctx.set_output('tw_im', im_table[idx])
    return behavior


def fftsdfunit_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTSdfUnit: Radix-2^2 SDF with stateful control + delays."""
    N = kwargs.get('N', 64)
    M = kwargs.get('M', 64)
    width = kwargs.get('width', 16)
    log_n = _log2_int(N)
    log_m = _log2_int(M)
    db1_depth = 1 << (log_m - 1) if log_m >= 1 else 1
    db2_depth = 1 << (log_m - 2) if log_m >= 2 else 1
    re_table, im_table = _generate_twiddle(N, width)

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['di_count'] = 0
            ctx.state['bf1_bf'] = 0; ctx.state['bf1_sp_en'] = 0; ctx.state['bf1_count'] = 0
            ctx.state['bf2_bf'] = 0; ctx.state['bf2_sp_en'] = 0; ctx.state['bf2_count'] = 0
            ctx.state['bf2_start'] = 0; ctx.state['bf2_do_en'] = 0
            ctx.state['mu_en'] = 0; ctx.state['mu_do_en'] = 0
            for i in range(db1_depth):
                ctx.state[f'db1_re_{i}'] = 0; ctx.state[f'db1_im_{i}'] = 0
            for i in range(db2_depth):
                ctx.state[f'db2_re_{i}'] = 0; ctx.state[f'db2_im_{i}'] = 0
            return

        di_en = ctx.get_input('di_en', 0)
        di_re = ctx.get_input('di_re', 0); di_im = ctx.get_input('di_im', 0)
        w = width

        # Save register state
        p_bf1_bf = ctx.state.get('bf1_bf', 0)
        p_bf1_sp_en = ctx.state.get('bf1_sp_en', 0)
        p_bf1_count = ctx.state.get('bf1_count', 0)
        p_bf2_bf = ctx.state.get('bf2_bf', 0)
        p_bf2_sp_en = ctx.state.get('bf2_sp_en', 0)
        p_bf2_count = ctx.state.get('bf2_count', 0)
        p_bf2_start = ctx.state.get('bf2_start', 0)
        p_bf2_do_en = ctx.state.get('bf2_do_en', 0)
        p_mu_do_en = ctx.state.get('mu_do_en', 0)

        # Next bf1_bf
        new_bf1_bf = (ctx.state.get('di_count', 0) >> (log_m - 1)) & 1 if log_m >= 1 else 0
        bf1_bf = p_bf1_bf

        # DB1 shift
        for i in range(db1_depth - 1, 0, -1):
            ctx.state[f'db1_re_{i}'] = ctx.state.get(f'db1_re_{i-1}', 0)
            ctx.state[f'db1_im_{i}'] = ctx.state.get(f'db1_im_{i-1}', 0)
        ctx.state['db1_re_0'] = di_re
        ctx.state['db1_im_0'] = di_im
        db1_do_re = ctx.state.get(f'db1_re_{db1_depth-1}', 0) if db1_depth > 0 else di_re
        db1_do_im = ctx.state.get(f'db1_im_{db1_depth-1}', 0) if db1_depth > 0 else di_im

        # BF1: butterfly 1
        if bf1_bf:
            bf1_x0_re, bf1_x0_im = db1_do_re, db1_do_im
            bf1_x1_re, bf1_x1_im = di_re, di_im
        else:
            bf1_x0_re = bf1_x0_im = 0
            bf1_x1_re = bf1_x1_im = 0

        add_re = _to_signed(bf1_x0_re, w) + _to_signed(bf1_x1_re, w)
        add_im = _to_signed(bf1_x0_im, w) + _to_signed(bf1_x1_im, w)
        sub_re = _to_signed(bf1_x0_re, w) - _to_signed(bf1_x1_re, w)
        sub_im = _to_signed(bf1_x0_im, w) - _to_signed(bf1_x1_im, w)
        y0_re = _to_unsigned(_sra(add_re, 1, w + 1), w)
        y0_im = _to_unsigned(_sra(add_im, 1, w + 1), w)
        y1_re = _to_unsigned(_sra(sub_re, 1, w + 1), w)
        y1_im = _to_unsigned(_sra(sub_im, 1, w + 1), w)

        db1_di_re = y1_re if bf1_bf else di_re
        db1_di_im = y1_im if bf1_bf else di_im

        # BF1 single-path output
        bf1_mj = ((p_bf1_count >> (log_m - 2)) & 0x3) == 3 if log_m >= 2 else False
        if bf1_bf:
            bf1_sp_re, bf1_sp_im = y0_re, y0_im
        elif bf1_mj:
            bf1_sp_re = 0
            bf1_sp_im = _to_unsigned(-_to_signed(ctx.state.get(f'db1_re_{db1_depth-1}', 0), w), w)
        else:
            bf1_sp_re = ctx.state.get(f'db1_re_{db1_depth-1}', 0)
            bf1_sp_im = ctx.state.get(f'db1_im_{db1_depth-1}', 0)

        # BF2
        bf2_bf = new_bf1_bf
        bf1_do_re, bf1_do_im = bf1_sp_re, bf1_sp_im

        # DB2 shift
        for i in range(db2_depth - 1, 0, -1):
            ctx.state[f'db2_re_{i}'] = ctx.state.get(f'db2_re_{i-1}', 0)
            ctx.state[f'db2_im_{i}'] = ctx.state.get(f'db2_im_{i-1}', 0)
        ctx.state['db2_re_0'] = bf1_do_re
        ctx.state['db2_im_0'] = bf1_do_im
        db2_do_re = ctx.state.get(f'db2_re_{db2_depth-1}', 0) if db2_depth > 0 else bf1_do_re
        db2_do_im = ctx.state.get(f'db2_im_{db2_depth-1}', 0) if db2_depth > 0 else bf1_do_im

        if bf2_bf:
            bf2_x0_re, bf2_x0_im = db2_do_re, db2_do_im
            bf2_x1_re, bf2_x1_im = bf1_do_re, bf1_do_im
        else:
            bf2_x0_re = bf2_x0_im = 0
            bf2_x1_re = bf2_x1_im = 0

        add2_re = _to_signed(bf2_x0_re, w) + _to_signed(bf2_x1_re, w)
        add2_im = _to_signed(bf2_x0_im, w) + _to_signed(bf2_x1_im, w)
        sub2_re = _to_signed(bf2_x0_re, w) - _to_signed(bf2_x1_re, w)
        sub2_im = _to_signed(bf2_x0_im, w) - _to_signed(bf2_x1_im, w)
        y20_re = _to_unsigned(_sra(add2_re + 1, 1, w + 1), w)
        y20_im = _to_unsigned(_sra(add2_im + 1, 1, w + 1), w)
        y21_re = _to_unsigned(_sra(sub2_re + 1, 1, w + 1), w)
        y21_im = _to_unsigned(_sra(sub2_im + 1, 1, w + 1), w)

        if bf2_bf:
            bf2_sp_re, bf2_sp_im = y20_re, y20_im
        else:
            bf2_sp_re = ctx.state.get(f'db2_re_{db2_depth-1}', 0)
            bf2_sp_im = ctx.state.get(f'db2_im_{db2_depth-1}', 0)

        # Update bf2 registered state
        if bf2_bf:
            ctx.state['bf2_sp_en'] = 1
            ctx.state['bf2_count'] = p_bf2_count + 1
        else:
            ctx.state['bf2_sp_en'] = 0
        ctx.state['bf1_bf'] = new_bf1_bf
        ctx.state['bf2_bf'] = new_bf1_bf
        ctx.state['bf2_start'] = new_bf1_bf
        ctx.state['bf2_do_en'] = p_bf2_sp_en

        if new_bf1_bf:
            ctx.state['bf1_sp_en'] = 1
            ctx.state['bf1_count'] = p_bf1_count + 1
        else:
            ctx.state['bf1_sp_en'] = 0
            ctx.state['bf1_count'] = 0

        # Twiddle and multiply
        tw_sel_1 = (p_bf2_count >> (log_m - 2)) & 1 if log_m >= 2 else 0
        tw_sel_0 = (p_bf2_count >> (log_m - 1)) & 1 if log_m >= 1 else 0
        tw_num = (p_bf2_count << (log_n - log_m)) & ((1 << log_n) - 1)
        tw_addr = tw_num * ((tw_sel_1 << 1) | tw_sel_0)
        tw_r = re_table[tw_addr % N] if tw_addr > 0 else 0
        tw_i = im_table[tw_addr % N] if tw_addr > 0 else 0

        mu_en = 1 if tw_addr != 0 else 0
        ctx.state['mu_en'] = mu_en

        bf2_do_re, bf2_do_im = bf2_sp_re, bf2_sp_im
        if mu_en:
            arbr = _to_signed(bf2_do_re, w) * _to_signed(tw_r, w)
            arbi = _to_signed(bf2_do_re, w) * _to_signed(tw_i, w)
            aibr = _to_signed(bf2_do_im, w) * _to_signed(tw_r, w)
            aibi = _to_signed(bf2_do_im, w) * _to_signed(tw_i, w)
            sc_arbr = _sra(arbr, w - 1, w * 2)
            sc_arbi = _sra(arbi, w - 1, w * 2)
            sc_aibr = _sra(aibr, w - 1, w * 2)
            sc_aibi = _sra(aibi, w - 1, w * 2)
            mu_re = _to_unsigned(_sat(_to_signed(sc_arbr, w) - _to_signed(sc_aibi, w), w), w)
            mu_im = _to_unsigned(_sat(_to_signed(sc_arbi, w) + _to_signed(sc_aibr, w), w), w)
        else:
            mu_re, mu_im = bf2_do_re, bf2_do_im
        ctx.state['mu_do_en'] = p_bf2_do_en

        # Update di_count
        if di_en:
            ctx.state['di_count'] = (ctx.state.get('di_count', 0) + 1) & ((1 << log_n) - 1)

        # Output
        if log_m == 2:
            ctx.set_output('do_en', p_bf2_sp_en)
            ctx.set_output('do_re', bf2_sp_re)
            ctx.set_output('do_im', bf2_sp_im)
        else:
            ctx.set_output('do_en', p_mu_do_en)
            ctx.set_output('do_re', mu_re)
            ctx.set_output('do_im', mu_im)
    return behavior


def fftsdfunit2_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTSdfUnit2: Radix-2 SDF for M=2 (no twiddle)."""
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            ctx.state['bf_en'] = 0; ctx.state['bf_sp_en'] = 0; ctx.state['do_en'] = 0
            ctx.state['db_re_0'] = 0; ctx.state['db_im_0'] = 0
            return

        di_en = ctx.get_input('di_en', 0)
        di_re = ctx.get_input('di_re', 0); di_im = ctx.get_input('di_im', 0)
        w = width
        bf_en = ctx.state.get('bf_en', 0)

        if bf_en:
            db_do_re = ctx.state.get('db_re_0', 0)
            db_do_im = ctx.state.get('db_im_0', 0)
            x0_re, x0_im = db_do_re, db_do_im
            x1_re, x1_im = di_re, di_im
        else:
            x0_re = x0_im = 0
            x1_re = x1_im = 0

        add_re = _to_signed(x0_re, w) + _to_signed(x1_re, w)
        add_im = _to_signed(x0_im, w) + _to_signed(x1_im, w)
        sub_re = _to_signed(x0_re, w) - _to_signed(x1_re, w)
        sub_im = _to_signed(x0_im, w) - _to_signed(x1_im, w)

        y0_re = _to_unsigned(_sra(add_re, 1, w + 1), w)
        y0_im = _to_unsigned(_sra(add_im, 1, w + 1), w)
        y1_re = _to_unsigned(_sra(sub_re, 1, w + 1), w)
        y1_im = _to_unsigned(_sra(sub_im, 1, w + 1), w)

        ctx.state['db_re_0'] = di_re
        ctx.state['db_im_0'] = di_im

        if bf_en:
            bf_sp_re, bf_sp_im = y0_re, y0_im
        else:
            bf_sp_re = ctx.state.get('db_re_0', 0)
            bf_sp_im = ctx.state.get('db_im_0', 0)

        prev_bf_sp_en = ctx.state.get('bf_sp_en', 0)
        if di_en:
            ctx.state['bf_en'] = 1 - bf_en
        else:
            ctx.state['bf_en'] = 0
        ctx.state['bf_sp_en'] = di_en
        ctx.state['do_en'] = prev_bf_sp_en

        ctx.set_output('do_en', ctx.state.get('do_en', 0))
        ctx.set_output('do_re', bf_sp_re)
        ctx.set_output('do_im', bf_sp_im)
    return behavior


def fftcontroller_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate FFTController: top-level FFT chaining SDF stages."""
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    log_n = _log2_int(N)
    num_su = log_n // 2
    need_su2 = (log_n % 2) == 1
    re_table, im_table = _generate_twiddle(N, width)

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 1)
        if rst == 1:
            for i in range(num_su):
                ctx.state[f'su{i}_di_count'] = 0
                ctx.state[f'su{i}_bf1_bf'] = 0; ctx.state[f'su{i}_bf1_sp_en'] = 0
                ctx.state[f'su{i}_bf1_count'] = 0
                ctx.state[f'su{i}_bf2_bf'] = 0; ctx.state[f'su{i}_bf2_sp_en'] = 0
                ctx.state[f'su{i}_bf2_count'] = 0; ctx.state[f'su{i}_bf2_start'] = 0
                ctx.state[f'su{i}_bf2_do_en'] = 0
                ctx.state[f'su{i}_mu_en'] = 0; ctx.state[f'su{i}_mu_do_en'] = 0
                m_val = N >> (2 * i)
                log_m = _log2_int(m_val)
                d1 = 1 << (log_m - 1) if log_m >= 1 else 1
                d2 = 1 << (log_m - 2) if log_m >= 2 else 1
                for j in range(d1):
                    ctx.state[f'su{i}_db1_re_{j}'] = 0; ctx.state[f'su{i}_db1_im_{j}'] = 0
                for j in range(d2):
                    ctx.state[f'su{i}_db2_re_{j}'] = 0; ctx.state[f'su{i}_db2_im_{j}'] = 0
            if need_su2:
                ctx.state['su2_bf_en'] = 0; ctx.state['su2_bf_sp_en'] = 0
                ctx.state['su2_do_en'] = 0
                ctx.state['su2_db_re_0'] = 0; ctx.state['su2_db_im_0'] = 0
            return

        di_en = ctx.get_input('di_en', 0)
        di_re = ctx.get_input('di_re', 0); di_im = ctx.get_input('di_im', 0)
        w = width
        cur_en, cur_re, cur_im = di_en, di_re, di_im

        for i in range(num_su):
            m_val = N >> (2 * i)
            log_m = _log2_int(m_val)
            d1 = 1 << (log_m - 1) if log_m >= 1 else 1
            d2 = 1 << (log_m - 2) if log_m >= 2 else 1
            log_n_su = log_n

            p_bf1_bf = ctx.state.get(f'su{i}_bf1_bf', 0)
            p_bf1_count = ctx.state.get(f'su{i}_bf1_count', 0)
            p_bf2_count = ctx.state.get(f'su{i}_bf2_count', 0)
            p_bf2_sp_en = ctx.state.get(f'su{i}_bf2_sp_en', 0)
            p_bf2_do_en = ctx.state.get(f'su{i}_bf2_do_en', 0)
            p_mu_do_en = ctx.state.get(f'su{i}_mu_do_en', 0)

            new_bf1_bf = (ctx.state.get(f'su{i}_di_count', 0) >> (log_m - 1)) & 1 if log_m >= 1 else 0
            bf1_bf = p_bf1_bf

            # DB1 shift
            for j in range(d1 - 1, 0, -1):
                ctx.state[f'su{i}_db1_re_{j}'] = ctx.state.get(f'su{i}_db1_re_{j-1}', 0)
                ctx.state[f'su{i}_db1_im_{j}'] = ctx.state.get(f'su{i}_db1_im_{j-1}', 0)
            ctx.state[f'su{i}_db1_re_0'] = cur_re
            ctx.state[f'su{i}_db1_im_0'] = cur_im
            db1_do_re = ctx.state.get(f'su{i}_db1_re_{d1-1}', 0) if d1 > 0 else cur_re
            db1_do_im = ctx.state.get(f'su{i}_db1_im_{d1-1}', 0) if d1 > 0 else cur_im

            # BF1
            if bf1_bf:
                bf1_x0_re, bf1_x0_im = db1_do_re, db1_do_im
                bf1_x1_re, bf1_x1_im = cur_re, cur_im
            else:
                bf1_x0_re = bf1_x0_im = 0
                bf1_x1_re = bf1_x1_im = 0

            add_re = _to_signed(bf1_x0_re, w) + _to_signed(bf1_x1_re, w)
            add_im = _to_signed(bf1_x0_im, w) + _to_signed(bf1_x1_im, w)
            sub_re = _to_signed(bf1_x0_re, w) - _to_signed(bf1_x1_re, w)
            sub_im = _to_signed(bf1_x0_im, w) - _to_signed(bf1_x1_im, w)
            y0_re = _to_unsigned(_sra(add_re, 1, w + 1), w)
            y0_im = _to_unsigned(_sra(add_im, 1, w + 1), w)
            y1_re = _to_unsigned(_sra(sub_re, 1, w + 1), w)
            y1_im = _to_unsigned(_sra(sub_im, 1, w + 1), w)

            bf1_mj = ((p_bf1_count >> (log_m - 2)) & 0x3) == 3 if log_m >= 2 else False
            if bf1_bf:
                bf1_sp_re, bf1_sp_im = y0_re, y0_im
            elif bf1_mj:
                bf1_sp_re = 0
                bf1_sp_im = _to_unsigned(-_to_signed(ctx.state.get(f'su{i}_db1_re_{d1-1}', 0), w), w)
            else:
                bf1_sp_re = ctx.state.get(f'su{i}_db1_re_{d1-1}', 0)
                bf1_sp_im = ctx.state.get(f'su{i}_db1_im_{d1-1}', 0)

            # DB2 shift
            for j in range(d2 - 1, 0, -1):
                ctx.state[f'su{i}_db2_re_{j}'] = ctx.state.get(f'su{i}_db2_re_{j-1}', 0)
                ctx.state[f'su{i}_db2_im_{j}'] = ctx.state.get(f'su{i}_db2_im_{j-1}', 0)
            ctx.state[f'su{i}_db2_re_0'] = bf1_sp_re
            ctx.state[f'su{i}_db2_im_0'] = bf1_sp_im
            db2_do_re = ctx.state.get(f'su{i}_db2_re_{d2-1}', 0) if d2 > 0 else bf1_sp_re
            db2_do_im = ctx.state.get(f'su{i}_db2_im_{d2-1}', 0) if d2 > 0 else bf1_sp_im

            bf2_bf = new_bf1_bf
            if bf2_bf:
                bf2_x0_re, bf2_x0_im = db2_do_re, db2_do_im
                bf2_x1_re, bf2_x1_im = bf1_sp_re, bf1_sp_im
            else:
                bf2_x0_re = bf2_x0_im = 0
                bf2_x1_re = bf2_x1_im = 0

            add2_re = _to_signed(bf2_x0_re, w) + _to_signed(bf2_x1_re, w)
            add2_im = _to_signed(bf2_x0_im, w) + _to_signed(bf2_x1_im, w)
            sub2_re = _to_signed(bf2_x0_re, w) - _to_signed(bf2_x1_re, w)
            sub2_im = _to_signed(bf2_x0_im, w) - _to_signed(bf2_x1_im, w)
            y20_re = _to_unsigned(_sra(add2_re + 1, 1, w + 1), w)
            y20_im = _to_unsigned(_sra(add2_im + 1, 1, w + 1), w)

            if bf2_bf:
                bf2_sp_re, bf2_sp_im = y20_re, y20_im
            else:
                bf2_sp_re = ctx.state.get(f'su{i}_db2_re_{d2-1}', 0)
                bf2_sp_im = ctx.state.get(f'su{i}_db2_im_{d2-1}', 0)

            # Update state
            if bf2_bf:
                ctx.state[f'su{i}_bf2_sp_en'] = 1
                ctx.state[f'su{i}_bf2_count'] = p_bf2_count + 1
            else:
                ctx.state[f'su{i}_bf2_sp_en'] = 0
            ctx.state[f'su{i}_bf1_bf'] = new_bf1_bf
            ctx.state[f'su{i}_bf2_bf'] = new_bf1_bf
            ctx.state[f'su{i}_bf2_start'] = new_bf1_bf
            ctx.state[f'su{i}_bf2_do_en'] = p_bf2_sp_en

            if new_bf1_bf:
                ctx.state[f'su{i}_bf1_sp_en'] = 1
                ctx.state[f'su{i}_bf1_count'] = p_bf1_count + 1
            else:
                ctx.state[f'su{i}_bf1_sp_en'] = 0
                ctx.state[f'su{i}_bf1_count'] = 0

            # Twiddle
            tw_sel_1 = (p_bf2_count >> (log_m - 2)) & 1 if log_m >= 2 else 0
            tw_sel_0 = (p_bf2_count >> (log_m - 1)) & 1 if log_m >= 1 else 0
            tw_num = (p_bf2_count << (log_n_su - log_m)) & ((1 << log_n_su) - 1)
            tw_addr = tw_num * ((tw_sel_1 << 1) | tw_sel_0)
            mu_en = 1 if tw_addr != 0 else 0
            ctx.state[f'su{i}_mu_en'] = mu_en

            bf2_do_re, bf2_do_im = bf2_sp_re, bf2_sp_im
            if mu_en:
                tw_r = re_table[tw_addr % N]
                tw_i = im_table[tw_addr % N]
                arbr = _to_signed(bf2_do_re, w) * _to_signed(tw_r, w)
                arbi = _to_signed(bf2_do_re, w) * _to_signed(tw_i, w)
                aibr = _to_signed(bf2_do_im, w) * _to_signed(tw_r, w)
                aibi = _to_signed(bf2_do_im, w) * _to_signed(tw_i, w)
                sc_arbr = _sra(arbr, w - 1, w * 2)
                sc_arbi = _sra(arbi, w - 1, w * 2)
                sc_aibr = _sra(aibr, w - 1, w * 2)
                sc_aibi = _sra(aibi, w - 1, w * 2)
                mu_re = _to_unsigned(_sat(_to_signed(sc_arbr, w) - _to_signed(sc_aibi, w), w), w)
                mu_im = _to_unsigned(_sat(_to_signed(sc_arbi, w) + _to_signed(sc_aibr, w), w), w)
            else:
                mu_re, mu_im = bf2_do_re, bf2_do_im
            ctx.state[f'su{i}_mu_do_en'] = p_bf2_do_en

            if cur_en:
                ctx.state[f'su{i}_di_count'] = (ctx.state.get(f'su{i}_di_count', 0) + 1) & ((1 << log_n_su) - 1)

            if log_m == 2:
                cur_en, cur_re, cur_im = p_bf2_sp_en, bf2_sp_re, bf2_sp_im
            else:
                cur_en, cur_re, cur_im = p_mu_do_en, mu_re, mu_im

        if need_su2:
            bf_en = ctx.state.get('su2_bf_en', 0)
            if bf_en:
                db_do_re = ctx.state.get('su2_db_re_0', 0)
                db_do_im = ctx.state.get('su2_db_im_0', 0)
                x0_re, x0_im = db_do_re, db_do_im
                x1_re, x1_im = cur_re, cur_im
            else:
                x0_re = x0_im = 0
                x1_re = x1_im = 0

            add_re = _to_signed(x0_re, w) + _to_signed(x1_re, w)
            add_im = _to_signed(x0_im, w) + _to_signed(x1_im, w)
            sub_re = _to_signed(x0_re, w) - _to_signed(x1_re, w)
            sub_im = _to_signed(x0_im, w) - _to_signed(x1_im, w)
            y0_re = _to_unsigned(_sra(add_re, 1, w + 1), w)
            y0_im = _to_unsigned(_sra(add_im, 1, w + 1), w)

            ctx.state['su2_db_re_0'] = cur_re
            ctx.state['su2_db_im_0'] = cur_im

            if bf_en:
                bf_sp_re, bf_sp_im = y0_re, y0_im
            else:
                bf_sp_re = ctx.state.get('su2_db_re_0', 0)
                bf_sp_im = ctx.state.get('su2_db_im_0', 0)

            prev_bf_sp_en = ctx.state.get('su2_bf_sp_en', 0)
            if cur_en:
                ctx.state['su2_bf_en'] = 1 - bf_en
            else:
                ctx.state['su2_bf_en'] = 0
            ctx.state['su2_bf_sp_en'] = cur_en
            ctx.state['su2_do_en'] = prev_bf_sp_en

            cur_en = ctx.state.get('su2_do_en', 0)
            cur_re, cur_im = bf_sp_re, bf_sp_im

        ctx.set_output('do_en', cur_en)
        ctx.set_output('do_re', cur_re)
        ctx.set_output('do_im', cur_im)
    return behavior


TemplateRegistry.register('fftbutterfly', fftbutterfly_cycle)
TemplateRegistry.register('fftdelaybuffer', fftdelaybuffer_cycle)
TemplateRegistry.register('fftmultiply', fftmultiply_cycle)
TemplateRegistry.register('ffttwiddle', ffttwiddle_cycle)
TemplateRegistry.register('fftsdfunit', fftsdfunit_cycle)
TemplateRegistry.register('fftsdfunit2', fftsdfunit2_cycle)
TemplateRegistry.register('fftcontroller', fftcontroller_cycle)

fftbutterfly_template = fftbutterfly_cycle
fftdelaybuffer_template = fftdelaybuffer_cycle
fftmultiply_template = fftmultiply_cycle
ffttwiddle_template = ffttwiddle_cycle
fftsdfunit_template = fftsdfunit_cycle
fftsdfunit2_template = fftsdfunit2_cycle
fftcontroller_template = fftcontroller_cycle
fft_butterfly_template = fftbutterfly_cycle
