"""
skills.interfaces.ethernet.cycle_level — Cycle-Level Models (register-accurate)
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def ptp_ts_extract_cycle(
    ts_width: int = 96,
    ts_offset: int = 1,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """PTP timestamp extract from AXI-Stream tuser.

    Extracts timestamp from tuser[ts_offset+ts_width-1 : ts_offset].
    Outputs valid on first beat of each frame (tvalid & ~frame_reg).
    frame_reg tracks whether we are mid-frame (set by tlast).
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)
        s_axis_tlast = ctx.get_input("s_axis_tlast", 0)
        s_axis_tuser = ctx.get_input("s_axis_tuser", 0)
        frame_reg = ctx.get_state("frame_reg", 0)

        if rst:
            frame_reg = 0

        # Extract timestamp field
        ts_mask = (1 << ts_width) - 1
        ts_value = (s_axis_tuser >> ts_offset) & ts_mask

        # Valid on first beat of frame
        ts_valid = s_axis_tvalid and not frame_reg

        # Update frame tracking
        if s_axis_tvalid:
            frame_reg = not s_axis_tlast

        ctx.set_output("m_axis_ts", ts_value)
        ctx.set_output("m_axis_ts_valid", ts_valid)

        ctx.set_state("frame_reg", frame_reg)

    return behavior




# Template Registry

_template_map = {
    "ptp_ts_extract": ptp_ts_extract_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

ptp_ts_extract_template = ptp_ts_extract_cycle
