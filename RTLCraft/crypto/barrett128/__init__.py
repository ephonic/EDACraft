"""128-bit Barrett modular multiplier design package.

Public API:
    - BarrettModMul: the executable (legacy DSL) RTL module.
    - reference: golden model (modmul, barrett_reduce, barrett_constant).
"""

from __future__ import annotations

from .dsl import BarrettModMul
from . import reference

__all__ = ["BarrettModMul", "reference"]
