"""FP16 activation/trig SFU example built on rtlgen_x.

The current unit is a scalar fully pipelined SFU supporting:

- relu
- sigmoid
- tanh
- sin
- cos

All non-linear functions are approximated with piecewise quadratic
interpolation, and the Python golden shares the same generated coefficient
tables as the RTL.
"""

from __future__ import annotations

from .dsl import Fp16Sfu, Fp16Sfu32
from . import reference

__all__ = ["Fp16Sfu", "Fp16Sfu32", "reference"]
