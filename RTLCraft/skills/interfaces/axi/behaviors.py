"""
skills.interfaces.axi.behaviors — Thin Shim
Re-exports from functional.py and cycle_level.py for backward compatibility.
"""
from __future__ import annotations
from skills.interfaces.axi.functional import *  # noqa: F401, F403
from skills.interfaces.axi.cycle_level import *  # noqa: F401, F403


def arch_gen(**kwargs):
    """Auto-generated stub for arch_template."""
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
arch_template = arch_gen


__all__ = [
    "axi_dp_ram_simple_template",
    "axil_ram_template",
]
