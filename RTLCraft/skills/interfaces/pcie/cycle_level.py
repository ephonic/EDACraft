"""
skills.interfaces.pcie.cycle_level — Cycle-Level Models (register-accurate)
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def pulse_merge_cycle(
    input_width: int = 2,
    count_width: int = 4,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Pulse merge counter behavior.

    - Accumulate input pulses (population count of pulse_in bits)
    - Decrement counter each cycle while count > 0
    - pulse_out = 1 while count > 0
    - Saturating: new pulses add to existing count
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        pulse_in = ctx.get_input("pulse_in", 0)
        count_reg = ctx.get_state("count_reg", 0)

        if rst:
            count_reg = 0
        else:
            # Count pulses in input vector
            pulse_sum = 0
            for i in range(input_width):
                if (pulse_in >> i) & 1:
                    pulse_sum += 1

            # Decrement if count > 0
            count_base = count_reg - 1 if count_reg > 0 else 0

            # Add new pulses
            count_reg = count_base + pulse_sum
            # Cap at max
            max_count = (1 << count_width) - 1
            if count_reg > max_count:
                count_reg = max_count

        ctx.set_output("count_out", count_reg)
        ctx.set_output("pulse_out", 1 if count_reg > 0 else 0)

        ctx.set_state("count_reg", count_reg)

    return behavior


# =====================================================================
# PCIE_PTILE_FC Template
# =====================================================================



def pcie_ptile_fc_cycle(
    width: int = 16,
    index: int = 0,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """PCIe P-Tile flow control counter behavior.

    Tracks available credits with saturating arithmetic:
      fc_av = clamp(fc_av - fc_dec + fc_inc, 0, fc_cap)
    - Increments on tx_cdts_limit update (matching index)
    - Decrements on fc_dec
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        tx_cdts_limit = ctx.get_input("tx_cdts_limit", 0)
        tx_cdts_limit_tdm_idx = ctx.get_input("tx_cdts_limit_tdm_idx", 0)
        fc_dec = ctx.get_input("fc_dec", 0)

        fc_cap_reg = ctx.get_state("fc_cap_reg", 0)
        fc_limit_reg = ctx.get_state("fc_limit_reg", 0)
        fc_av_reg = ctx.get_state("fc_av_reg", 0)

        if rst:
            fc_cap_reg = 0
            fc_limit_reg = 0
            fc_av_reg = 0
        else:
            # Update credit limit on matching TDM index
            if tx_cdts_limit_tdm_idx == index:
                if fc_cap_reg == 0:
                    fc_cap_reg = tx_cdts_limit
                fc_inc = tx_cdts_limit - fc_limit_reg
                fc_limit_reg = tx_cdts_limit
            else:
                fc_inc = 0

            # Saturating: fc_av = clamp(fc_av - fc_dec + fc_inc, 0, fc_cap)
            add_result = fc_av_reg + fc_inc
            if add_result >= fc_dec:
                sub_result = add_result - fc_dec
                fc_av_reg = sub_result if sub_result <= fc_cap_reg else fc_cap_reg
            else:
                fc_av_reg = 0

        ctx.set_output("fc_av", fc_av_reg)

        ctx.set_state("fc_cap_reg", fc_cap_reg)
        ctx.set_state("fc_limit_reg", fc_limit_reg)
        ctx.set_state("fc_av_reg", fc_av_reg)

    return behavior




def pcie_ptile_fc_counter_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate PCIE_PTILE_FC_COUNTER model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
        # TODO: implement full cycle-level logic
    return behavior


def ptp_ts_extract_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate PTP_TS_EXTRACT model."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input("rst_n", 1)
        if rst_n == 0:
            for o in []:
                ctx.set_output(o, 0)
            return
        # TODO: implement full cycle-level logic
    return behavior


# Template Registry

_template_map = {
    "pcie_ptile_fc": pcie_ptile_fc_cycle,
    "pcie_ptile_fc_counter": pcie_ptile_fc_counter_cycle,
    "ptp_ts_extract": ptp_ts_extract_cycle,
    "pulse_merge": pulse_merge_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

pcie_ptile_fc_template = pcie_ptile_fc_cycle
pcie_ptile_fc_counter_template = pcie_ptile_fc_counter_cycle
ptp_ts_extract_template = ptp_ts_extract_cycle
pulse_merge_template = pulse_merge_cycle
