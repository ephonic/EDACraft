"""
skills.interfaces.btle.behaviors — Thin Shim
Re-exports from functional.py and cycle_level.py for backward compatibility.
"""
from __future__ import annotations
from skills.interfaces.btle.functional import *  # noqa: F401, F403
from skills.interfaces.btle.cycle_level import *  # noqa: F401, F403


def arch_gen(**kwargs):
    """Auto-generated stub for arch_template."""
    def behavior(ctx):
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0: return
    return behavior
arch_template = arch_gen


__all__ = [
    "access_address_detect_template",
    "bit_repeat_upsample_template",
    "bit_upsampler_template",
    "btle_phy_template",
    "btle_rx_core_template",
    "btle_tx_template",
    "crc24_template",
    "crc24_core_template",
    "crc_wrapper_template",
    "gauss_filter_template",
    "gfsk_demod_template",
    "gfsk_demodulation_template",
    "gfsk_mod_template",
    "gfsk_modulation_template",
    "scramble_template",
    "scramble_core_template",
    "scramble_wrapper_template",
    "sdpram_template",
    "sdpram_one_clk_template",
    "sdpram_two_clk_template",
    "search_unique_bit_seq_template",
    "vco_template",
]
