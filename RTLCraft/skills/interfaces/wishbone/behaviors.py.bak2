"""
skills.interfaces.wishbone.behaviors — Wishbone Behavior Templates

Domain-specific behavior templates for Wishbone bus components.
Registered into TemplateRegistry at import time.

Components:
  - wb_reg:    Wishbone register slice (cycle-hold, 1-cycle latency)
  - wb_mux_2:  Wishbone 2-to-1 address-decode multiplexer (combinational)

Reference: ref_rtl/interfaces/wishbone/rtl/wb_reg.v, wb_mux_2.v
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# WB_REG Template
# =====================================================================

def wb_reg_template(
    data_width: int = 32,
    addr_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Wishbone register slice behavior.

    2-state behavior:
      - Idle: pass master signals directly to slave
      - Cycle (wbs_cyc_o & wbs_stb_o): hold values until slave responds
        (ack/err/rty), then pass response back to master

    Adds 1-cycle latency to transactions.
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)
        wbs_cyc_o_reg = ctx.get_state("wbs_cyc_o_reg", 0)
        wbs_stb_o_reg = ctx.get_state("wbs_stb_o_reg", 0)

        # Response flags (OR-reduced)
        wbs_ack_i = ctx.get_input("wbs_ack_i", 0)
        wbs_err_i = ctx.get_input("wbs_err_i", 0)
        wbs_rty_i = ctx.get_input("wbs_rty_i", 0)
        wbm_ack_o = 0
        wbm_err_o = 0
        wbm_rty_o = 0

        if wbs_cyc_o_reg and wbs_stb_o_reg:
            # Active cycle - hold
            if wbs_ack_i or wbs_err_i or wbs_rty_i:
                # End of cycle
                wbm_ack_o = wbs_ack_i
                wbm_err_o = wbs_err_i
                wbm_rty_o = wbs_rty_i
                wbs_stb_o_reg = 0

        # Outputs
        ctx.set_output("wbm_ack_o", wbm_ack_o)
        ctx.set_output("wbm_err_o", wbm_err_o)
        ctx.set_output("wbm_rty_o", wbm_rty_o)

        ctx.set_state("wbs_cyc_o_reg", wbs_cyc_o_reg)
        ctx.set_state("wbs_stb_o_reg", wbs_stb_o_reg)

    return behavior


# =====================================================================
# WB_MUX_2 Template
# =====================================================================

def wb_mux_2_template(
    data_width: int = 32,
    addr_width: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Wishbone 2-to-1 MUX behavior.

    Pure combinational:
      - Address match: match = ~|((adr ^ slave_addr) & slave_addr_msk)
      - Priority: slave0 > slave1
      - Select error: no match during active cycle → err=1
      - Data MUX: selected slave's data to master
      - Response OR-reduce: ack/err/rty from all slaves
    """
    def behavior(ctx: CycleContext):
        wbm_adr_i = ctx.get_input("wbm_adr_i", 0)
        wbm_cyc_i = ctx.get_input("wbm_cyc_i", 0)
        wbm_stb_i = ctx.get_input("wbm_stb_i", 0)

        wbs0_addr = ctx.get_input("wbs0_addr", 0)
        wbs0_addr_msk = ctx.get_input("wbs0_addr_msk", 0)
        wbs1_addr = ctx.get_input("wbs1_addr", 0)
        wbs1_addr_msk = ctx.get_input("wbs1_addr_msk", 0)

        wbs0_dat_i = ctx.get_input("wbs0_dat_i", 0)
        wbs0_ack_i = ctx.get_input("wbs0_ack_i", 0)
        wbs0_err_i = ctx.get_input("wbs0_err_i", 0)
        wbs0_rty_i = ctx.get_input("wbs0_rty_i", 0)

        wbs1_dat_i = ctx.get_input("wbs1_dat_i", 0)
        wbs1_ack_i = ctx.get_input("wbs1_ack_i", 0)
        wbs1_err_i = ctx.get_input("wbs1_err_i", 0)
        wbs1_rty_i = ctx.get_input("wbs1_rty_i", 0)

        # Address decode
        wbs0_match = 1 if ((wbm_adr_i ^ wbs0_addr) & wbs0_addr_msk) == 0 else 0
        wbs1_match = 1 if ((wbm_adr_i ^ wbs1_addr) & wbs1_addr_msk) == 0 else 0

        # Priority select
        wbs0_sel = wbs0_match
        wbs1_sel = wbs1_match and not wbs0_match

        master_cycle = wbm_cyc_i and wbm_stb_i
        select_error = (not (wbs0_sel or wbs1_sel)) and master_cycle

        # Data MUX
        if wbs0_sel:
            wbm_dat_o = wbs0_dat_i
        elif wbs1_sel:
            wbm_dat_o = wbs1_dat_i
        else:
            wbm_dat_o = 0

        # Outputs
        ctx.set_output("wbm_dat_o", wbm_dat_o)
        ctx.set_output("wbm_ack_o", wbs0_ack_i or wbs1_ack_i)
        ctx.set_output("wbm_err_o", wbs0_err_i or wbs1_err_i or select_error)
        ctx.set_output("wbm_rty_o", wbs0_rty_i or wbs1_rty_i)

        ctx.set_output("wbs0_adr_o", wbm_adr_i)
        ctx.set_output("wbs0_dat_o", ctx.get_input("wbm_dat_i", 0))
        ctx.set_output("wbs0_we_o", ctx.get_input("wbm_we_i", 0) and wbs0_sel)
        ctx.set_output("wbs0_sel_o", ctx.get_input("wbm_sel_i", 0))
        ctx.set_output("wbs0_stb_o", wbm_stb_i and wbs0_sel)
        ctx.set_output("wbs0_cyc_o", wbm_cyc_i and wbs0_sel)

        ctx.set_output("wbs1_adr_o", wbm_adr_i)
        ctx.set_output("wbs1_dat_o", ctx.get_input("wbm_dat_i", 0))
        ctx.set_output("wbs1_we_o", ctx.get_input("wbm_we_i", 0) and wbs1_sel)
        ctx.set_output("wbs1_sel_o", ctx.get_input("wbm_sel_i", 0))
        ctx.set_output("wbs1_stb_o", wbm_stb_i and wbs1_sel)
        ctx.set_output("wbs1_cyc_o", wbm_cyc_i and wbs1_sel)

    return behavior


# Register Wishbone templates
TemplateRegistry.register("wb_reg", wb_reg_template)
TemplateRegistry.register("wb_mux_2", wb_mux_2_template)

__all__ = [
    "wb_reg_template",
    "wb_mux_2_template",
]
