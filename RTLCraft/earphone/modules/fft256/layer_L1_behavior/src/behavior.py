"""L1 BehaviorIR model for the EarphoneFFT256 accelerator.

Golden FFT256 reference using Python complex arithmetic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from earphone.modules.common.utils import _to_s32


def fft256_functional(samples_re: List[int], samples_im: List[int], width: int = 16) -> Tuple[List[int], List[int]]:
    """Golden FFT256 reference using Python complex arithmetic.

    Input samples are 16-bit signed fixed-point Q1.15.
    Output is scaled by 1/256 to match hardware butterfly scaling.
    """
    import numpy as np
    scale = 1 << (width - 1)
    samples = np.array([complex(_to_s32(r) / scale, _to_s32(i) / scale) for r, i in zip(samples_re, samples_im)])
    out = np.fft.fft(samples)
    out_re = [int(round((v.real / 256.0) * scale)) for v in out]
    out_im = [int(round((v.imag / 256.0) * scale)) for v in out]
    return out_re, out_im


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneFFT256",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Golden 256-point FFT reference using NumPy complex arithmetic.",
        "points": 256,
        "sample_width": 16,
        "scaling": "1/256 per butterfly stage",
    }
