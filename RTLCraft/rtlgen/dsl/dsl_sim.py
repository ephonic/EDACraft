"""Removed historical DSL simulation-validator surface.

This module remains only as a compatibility stub that raises a clear removal
error for callers that still reach for the old AST/JIT-based validator path.
"""

from __future__ import annotations

from rtlgen.dsl.unsupported import raise_dsl_sim_removed


class DSLSimValidator:
    """Removed legacy validation helper built on top of the old AST simulator."""

    def __init__(self, *args, **kwargs):
        raise_dsl_sim_removed()


__all__ = ["DSLSimValidator"]
