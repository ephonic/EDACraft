"""Removed historical AST simulator surface for rtlgen.dsl.

This module is intentionally kept as a tiny compatibility stub so callers get
an explicit, actionable removal error instead of silently using an unmaintained
simulation path.
"""

from __future__ import annotations

from rtlgen.dsl.unsupported import raise_dsl_sim_removed


class Simulator:
    """Removed legacy DSL AST simulator."""

    def __init__(self, *args, **kwargs):
        raise_dsl_sim_removed()


class SimValue:
    """Removed legacy 4-state value helper tied to the old AST simulator."""

    def __init__(self, *args, **kwargs):
        raise_dsl_sim_removed()


__all__ = ["Simulator", "SimValue"]
