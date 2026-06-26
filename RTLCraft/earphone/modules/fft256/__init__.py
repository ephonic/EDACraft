"""EarphoneFFT256 module package.

Public API:
    - fft256_functional: L1 golden FFT256 reference.
"""

from __future__ import annotations

from earphone.modules.fft256.layer_L1_behavior.src.behavior import fft256_functional

__all__ = ["fft256_functional"]
