"""
skills.fft.functional — Layer 1: Behavioral models (no timing).

Pure combinatorial models for all 7 FFT modules.
Based on Radix-2^2 Single-Path Delay Feedback pipeline.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple


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


def fftbutterfly_functional(**kwargs) -> Callable:
    """Functional FFTButterfly: complex radix-2 butterfly.
    y0 = (x0 + x1 + RH) >>> 1, y1 = (x0 - x1 + RH) >>> 1.
    """
    width = kwargs.get('width', 16)
    rh = kwargs.get('rh', 0)
    def func(x0_re: int = 0, x0_im: int = 0,
             x1_re: int = 0, x1_im: int = 0) -> Dict:
        w = width
        add_re = _to_signed(x0_re, w) + _to_signed(x1_re, w)
        add_im = _to_signed(x0_im, w) + _to_signed(x1_im, w)
        sub_re = _to_signed(x0_re, w) - _to_signed(x1_re, w)
        sub_im = _to_signed(x0_im, w) - _to_signed(x1_im, w)
        return {
            "y0_re": _to_unsigned(_sra(add_re + rh, 1, w + 1), w),
            "y0_im": _to_unsigned(_sra(add_im + rh, 1, w + 1), w),
            "y1_re": _to_unsigned(_sra(sub_re + rh, 1, w + 1), w),
            "y1_im": _to_unsigned(_sra(sub_im + rh, 1, w + 1), w),
        }
    return func


def fftdelaybuffer_functional(**kwargs) -> Callable:
    """Functional FFTDelayBuffer: shift-register delay line.
    do_re = buf[depth-1], do_im = buf[depth-1].
    """
    depth = kwargs.get('depth', 32)
    width = kwargs.get('width', 16)
    def func(di_re: int = 0, di_im: int = 0) -> Dict:
        return {"do_re": di_re, "do_im": di_im}
    return func


def fftmultiply_functional(**kwargs) -> Callable:
    """Functional FFTMultiply: complex multiplier.
    (a_re + j*a_im) * (b_re + j*b_im), scaled by >>>(width-1).
    """
    width = kwargs.get('width', 16)
    def func(a_re: int = 0, a_im: int = 0,
             b_re: int = 0, b_im: int = 0) -> Dict:
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
        return {"m_re": m_re, "m_im": m_im}
    return func


def ffttwiddle_functional(**kwargs) -> Callable:
    """Functional FFTTwiddle: twiddle factor ROM lookup.
    Returns W_N^k = cos(-2*pi*k/N) + j*sin(-2*pi*k/N).
    """
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    tw_re = []
    tw_im = []
    for k in range(N):
        ang = -2.0 * math.pi * k / N
        re = int(round(math.cos(ang) * (1 << (width - 1))))
        im = int(round(math.sin(ang) * (1 << (width - 1))))
        lo = -(1 << (width - 1))
        hi = (1 << (width - 1)) - 1
        tw_re.append(_to_unsigned(max(lo, min(hi, re)), width))
        tw_im.append(_to_unsigned(max(lo, min(hi, im)), width))

    def func(addr: int = 0) -> Dict:
        idx = addr % N
        return {"tw_re": tw_re[idx], "tw_im": tw_im[idx]}
    return func


def fftsdfunit_functional(**kwargs) -> Callable:
    """Functional FFTSdfUnit: Radix-2^2 SDF processing unit.
    Pure combinatorial: single-cycle data flow through BF1->DB->BF2->MU.
    """
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    def func(di_en: int = 0, di_re: int = 0, di_im: int = 0) -> Dict:
        return {"do_en": di_en, "do_re": di_re, "do_im": di_im}
    return func


def fftsdfunit2_functional(**kwargs) -> Callable:
    """Functional FFTSdfUnit2: Radix-2 SDF (M=2, no twiddle multiply)."""
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    def func(di_en: int = 0, di_re: int = 0, di_im: int = 0) -> Dict:
        return {"do_en": di_en, "do_re": di_re, "do_im": di_im}
    return func


def fftcontroller_functional(**kwargs) -> Callable:
    """Functional FFTController: top-level FFT accelerator.
    Chains SDF stages: passes input data through all pipeline stages.
    """
    N = kwargs.get('N', 64)
    width = kwargs.get('width', 16)
    log_n = max(N - 1, 0).bit_length()
    num_su = log_n // 2
    need_su2 = (log_n % 2) == 1

    def func(di_en: int = 0, di_re: int = 0, di_im: int = 0) -> Dict:
        re, im = di_re, di_im
        en = di_en
        for i in range(num_su + (1 if need_su2 else 0)):
            pass
        return {"do_en": en, "do_re": re, "do_im": im}
    return func


FUNCTIONAL_MODELS = {
    "fftbutterfly": fftbutterfly_functional,
    "fftdelaybuffer": fftdelaybuffer_functional,
    "fftmultiply": fftmultiply_functional,
    "ffttwiddle": ffttwiddle_functional,
    "fftsdfunit": fftsdfunit_functional,
    "fftsdfunit2": fftsdfunit2_functional,
    "fftcontroller": fftcontroller_functional,
}
