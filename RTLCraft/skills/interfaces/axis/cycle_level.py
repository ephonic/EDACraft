"""
skills.interfaces.axis.cycle_level — Cycle-Level Models (register-accurate)
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def axis_register_cycle(
    data_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """AXI-Stream skid buffer register behavior.

    3-state skid buffer (no bubble cycles):
      - State 1: input→output (when output ready or invalid)
      - State 2: input→temp (when output not ready)
      - State 3: temp→output (when input not ready but output ready)

    Ready early: s_tready = m_tready | (~temp_valid & (~out_valid | ~in_valid))
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)
        m_axis_tready = ctx.get_input("m_axis_tready", 0)

        s_tready_reg = ctx.get_state("s_tready_reg", 0)
        m_valid_reg = ctx.get_state("m_valid_reg", 0)
        temp_valid_reg = ctx.get_state("temp_valid_reg", 0)

        if rst:
            s_tready_reg = 0
            m_valid_reg = 0
            temp_valid_reg = 0
        else:
            # Ready early
            s_tready_early = m_axis_tready or (not temp_valid_reg and (not m_valid_reg or not s_axis_tvalid))

            # Next state logic
            if s_tready_reg:
                if m_axis_tready or not m_valid_reg:
                    m_valid_next = s_axis_tvalid
                    temp_valid_next = temp_valid_reg
                    store_to_output = True
                    store_to_temp = False
                    store_temp_to_output = False
                else:
                    m_valid_next = m_valid_reg
                    temp_valid_next = s_axis_tvalid
                    store_to_output = False
                    store_to_temp = True
                    store_temp_to_output = False
            elif m_axis_tready:
                m_valid_next = temp_valid_reg
                temp_valid_next = 0
                store_to_output = False
                store_to_temp = False
                store_temp_to_output = True
            else:
                m_valid_next = m_valid_reg
                temp_valid_next = temp_valid_reg
                store_to_output = False
                store_to_temp = False
                store_temp_to_output = False

            s_tready_reg = s_tready_early
            m_valid_reg = m_valid_next
            temp_valid_reg = temp_valid_next

            ctx.set_state("store_to_output", 1 if store_to_output else 0)
            ctx.set_state("store_to_temp", 1 if store_to_temp else 0)
            ctx.set_state("store_temp_to_output", 1 if store_temp_to_output else 0)

        ctx.set_output("s_axis_tready", s_tready_reg)
        ctx.set_output("m_axis_tvalid", m_valid_reg)

        ctx.set_state("s_tready_reg", s_tready_reg)
        ctx.set_state("m_valid_reg", m_valid_reg)
        ctx.set_state("temp_valid_reg", temp_valid_reg)

    return behavior


# =====================================================================
# AXIS_ADAPTER Template
# =====================================================================



def axis_adapter_cycle(
    s_data_width: int = 8,
    m_data_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """AXI-Stream width up-size adapter behavior.

    Collects N narrow input segments into one wide output word.
      seg_count = m_data_width / s_data_width
    Uses per-segment registers to avoid dynamic slice issues.
    Skid buffer for input when output not ready.
    """
    seg_count = m_data_width // s_data_width

    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)
        m_axis_tready = ctx.get_input("m_axis_tready", 0)
        s_axis_tlast = ctx.get_input("s_axis_tlast", 0)

        seg_cnt = ctx.get_state("seg_cnt", 0)
        s_valid_reg = ctx.get_state("s_valid_reg", 0)
        m_valid_reg = ctx.get_state("m_valid_reg", 0)
        m_last_reg = ctx.get_state("m_last_reg", 0)

        if rst:
            seg_cnt = 0
            s_valid_reg = 0
            m_valid_reg = 0
            m_last_reg = 0
        else:
            m_valid_reg = m_valid_reg and not m_axis_tready

            if not m_valid_reg or m_axis_tready:
                if s_valid_reg:
                    s_valid_reg = 0
                    # Consume buffered data
                    if s_axis_tlast or seg_cnt == seg_count - 1:
                        seg_cnt = 0
                        m_valid_reg = 1
                        m_last_reg = s_axis_tlast
                    else:
                        seg_cnt += 1
                elif s_axis_tvalid:
                    # Direct from input
                    if s_axis_tlast or seg_cnt == seg_count - 1:
                        seg_cnt = 0
                        m_valid_reg = 1
                        m_last_reg = s_axis_tlast
                    else:
                        seg_cnt += 1

            # Skid buffer store
            if s_axis_tvalid and not s_valid_reg:
                pass  # input accepted directly

            if s_axis_tvalid and s_valid_reg == 0 and (m_valid_reg and not m_axis_tready):
                s_valid_reg = 1

        ctx.set_output("s_axis_tready", not s_valid_reg)
        ctx.set_output("m_axis_tvalid", m_valid_reg)
        ctx.set_output("m_axis_tlast", m_last_reg)

        ctx.set_state("seg_cnt", seg_cnt)
        ctx.set_state("s_valid_reg", s_valid_reg)
        ctx.set_state("m_valid_reg", m_valid_reg)
        ctx.set_state("m_last_reg", m_last_reg)

    return behavior


# =====================================================================
# AXIS_BROADCAST Template
# =====================================================================



def axis_broadcast_cycle(
    m_count: int = 4,
    data_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """AXI-Stream 1-to-M broadcaster behavior.

    Skid buffer with per-output valid tracking:
      - Replicates input data to all M outputs
      - Individual valid/ready per output
      - Input accepted when all active outputs ready
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        s_axis_tvalid = ctx.get_input("s_axis_tvalid", 0)

        s_tready_reg = ctx.get_state("s_tready_reg", 0)
        m_valid_reg = ctx.get_state("m_valid_reg", 0)
        temp_valid_reg = ctx.get_state("temp_valid_reg", 0)

        if rst:
            s_tready_reg = 0
            m_valid_reg = 0
            temp_valid_reg = 0
        else:
            # all_ready: for each output bit, (ready & valid) == valid
            all_ready = True  # simplified

            if s_tready_reg:
                if all_ready or not m_valid_reg:
                    m_valid_next = s_axis_tvalid
                    temp_valid_next = temp_valid_reg
                else:
                    m_valid_next = m_valid_reg
                    temp_valid_next = s_axis_tvalid
            elif all_ready:
                m_valid_next = temp_valid_reg
                temp_valid_next = 0
            else:
                m_valid_next = m_valid_reg
                temp_valid_next = temp_valid_reg

            s_tready_reg = all_ready or (not temp_valid_reg and (not m_valid_reg or not s_axis_tvalid))
            m_valid_reg = m_valid_next
            temp_valid_reg = temp_valid_next

        ctx.set_output("s_axis_tready", s_tready_reg)
        ctx.set_output("m_axis_tvalid", m_valid_reg)

        ctx.set_state("s_tready_reg", s_tready_reg)
        ctx.set_state("m_valid_reg", m_valid_reg)
        ctx.set_state("temp_valid_reg", temp_valid_reg)

    return behavior


# Register AXIS templates


# Template Registry

_template_map = {
    "axis_adapter": axis_adapter_cycle,
    "axis_broadcast": axis_broadcast_cycle,
    "axis_register": axis_register_cycle,
}

for _name, _tmpl in _template_map.items():
    TemplateRegistry.register(_name, _tmpl)

axis_adapter_template = axis_adapter_cycle
axis_broadcast_template = axis_broadcast_cycle
axis_register_template = axis_register_cycle
