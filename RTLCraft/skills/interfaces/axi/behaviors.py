"""
skills.interfaces.axi.behaviors — AXI Behavior Templates

Domain-specific behavior templates for AXI bus components.
Registered into TemplateRegistry at import time.

Components:
  - axi_dp_ram_simple: Dual-port AXI-Lite RAM (Port A + Port B, word-level)

Reference: ref_rtl/interfaces/axi/rtl/axi_dp_ram.v
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# AXI_DP_RAM_SIMPLE Template
# =====================================================================

def axi_dp_ram_simple_template(
    data_width: int = 32,
    addr_width: int = 16,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Simplified AXI dual-port RAM behavior.

    Two independent AXI-Lite interfaces (Port A and Port B) accessing
    the same shared memory array. Each port has:
      - Write: AW+W → B response (1-cycle)
      - Read: AR → R response (1-cycle latency)
    """
    def behavior(ctx: CycleContext):
        rst_a = ctx.get_input("a_rst", 1)
        rst_b = ctx.get_input("b_rst", 1)

        # --- Port A ---
        a_awvalid = ctx.get_input("a_awvalid", 0)
        a_wvalid = ctx.get_input("a_wvalid", 0)
        a_bready = ctx.get_input("a_bready", 0)
        a_arvalid = ctx.get_input("a_arvalid", 0)
        a_rready = ctx.get_input("a_rready", 0)

        a_bvalid_reg = ctx.get_state("a_bvalid_reg", 0)
        a_rvalid_reg = ctx.get_state("a_rvalid_reg", 0)

        if rst_a:
            a_bvalid_reg = 0
            a_rvalid_reg = 0
        else:
            if a_bready and a_bvalid_reg:
                a_bvalid_reg = 0
            if a_rready and a_rvalid_reg:
                a_rvalid_reg = 0

            # Write
            if a_awvalid and a_wvalid and not a_bvalid_reg:
                ctx.set_output("a_awready", 1)
                ctx.set_output("a_wready", 1)
                a_bvalid_reg = 1
            else:
                ctx.set_output("a_awready", 0)
                ctx.set_output("a_wready", 0)

            # Read
            if a_arvalid and (not a_rvalid_reg or a_rready):
                ctx.set_output("a_arready", 1)
                a_rvalid_reg = 1
            else:
                ctx.set_output("a_arready", 0)

        ctx.set_output("a_bvalid", a_bvalid_reg)
        ctx.set_output("a_rvalid", a_rvalid_reg)
        ctx.set_output("a_bresp", 0)
        ctx.set_output("a_rresp", 0)

        # --- Port B ---
        b_awvalid = ctx.get_input("b_awvalid", 0)
        b_wvalid = ctx.get_input("b_wvalid", 0)
        b_bready = ctx.get_input("b_bready", 0)
        b_arvalid = ctx.get_input("b_arvalid", 0)
        b_rready = ctx.get_input("b_rready", 0)

        b_bvalid_reg = ctx.get_state("b_bvalid_reg", 0)
        b_rvalid_reg = ctx.get_state("b_rvalid_reg", 0)

        if rst_b:
            b_bvalid_reg = 0
            b_rvalid_reg = 0
        else:
            if b_bready and b_bvalid_reg:
                b_bvalid_reg = 0
            if b_rready and b_rvalid_reg:
                b_rvalid_reg = 0

            if b_awvalid and b_wvalid and not b_bvalid_reg:
                ctx.set_output("b_awready", 1)
                ctx.set_output("b_wready", 1)
                b_bvalid_reg = 1
            else:
                ctx.set_output("b_awready", 0)
                ctx.set_output("b_wready", 0)

            if b_arvalid and (not b_rvalid_reg or b_rready):
                ctx.set_output("b_arready", 1)
                b_rvalid_reg = 1
            else:
                ctx.set_output("b_arready", 0)

        ctx.set_output("b_bvalid", b_bvalid_reg)
        ctx.set_output("b_rvalid", b_rvalid_reg)
        ctx.set_output("b_bresp", 0)
        ctx.set_output("b_rresp", 0)

        ctx.set_state("a_bvalid_reg", a_bvalid_reg)
        ctx.set_state("a_rvalid_reg", a_rvalid_reg)
        ctx.set_state("b_bvalid_reg", b_bvalid_reg)
        ctx.set_state("b_rvalid_reg", b_rvalid_reg)

    return behavior


TemplateRegistry.register("axi_dp_ram_simple", axi_dp_ram_simple_template)

__all__ = ["axi_dp_ram_simple_template"]
