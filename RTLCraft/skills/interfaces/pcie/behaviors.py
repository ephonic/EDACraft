"""
skills.interfaces.pcie.behaviors — Thin Shim
Re-exports from functional.py and cycle_level.py for backward compatibility.
"""
from __future__ import annotations
from skills.interfaces.pcie.functional import *  # noqa: F401, F403
from skills.interfaces.pcie.cycle_level import *  # noqa: F401, F403


def arch_gen(**kwargs):
    """Auto-generated stub for arch_template."""
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
arch_template = arch_gen


__all__ = [
    "pcie_ptile_fc_template",
    "pcie_ptile_fc_counter_template",
    "ptp_ts_extract_template",
    "pulse_merge_template",
]
