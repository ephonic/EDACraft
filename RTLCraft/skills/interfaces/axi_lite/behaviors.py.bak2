"""
skills.interfaces.axi_lite.behaviors — AXI-Lite Behavior Templates

Domain-specific behavior templates for AXI-Lite RAM components.
Registered into TemplateRegistry at import time.

Components:
  - axil_ram:     AXI-Lite RAM with word-level read/write (AW/W/B + AR/R handshakes)

Reference: ref_rtl/interfaces/axi/rtl/axil_ram.v, design_interfaces.py AXIL_RAM
"""
from __future__ import annotations

from typing import Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# AXIL_RAM Template
# =====================================================================

def axil_ram_template(
    data_width: int = 32,
    addr_width: int = 16,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """AXI-Lite RAM behavior.

    Simplified AXI-Lite slave with word-level read/write:
      - Write channel (AW/W/B handshakes):
          When awvalid & wvalid & !bvalid:
            awready=1, wready=1, bvalid=1
            Latch awaddr, write wdata to memory[awaddr]
        B response cleared when bready & bvalid.

      - Read channel (AR/R handshakes):
          When arvalid & (!rvalid | rready):
            arready=1, rvalid=1
            Latch araddr, read memory[araddr] into rdata
        R response cleared when rready & rvalid.

      - Both bresp and rresp are always OK (0).
      - Memory is zero-initialized.

    Registers: awready_reg, wready_reg, bvalid_reg,
               arready_reg, rvalid_reg, rdata_reg,
               awaddr_reg, araddr_reg
    """
    def behavior(ctx: CycleContext):
        rst = ctx.get_input("rst", 1)

        # Defaults
        awready_reg = ctx.get_state("awready_reg", 0)
        wready_reg = ctx.get_state("wready_reg", 0)
        bvalid_reg = ctx.get_state("bvalid_reg", 0)
        arready_reg = ctx.get_state("arready_reg", 0)
        rvalid_reg = ctx.get_state("rvalid_reg", 0)
        rdata_reg = ctx.get_state("rdata_reg", 0)
        awaddr_reg = ctx.get_state("awaddr_reg", 0)
        araddr_reg = ctx.get_state("araddr_reg", 0)
        mem = ctx.get_state("mem", {})

        if rst:
            awready_reg = 0
            wready_reg = 0
            bvalid_reg = 0
            arready_reg = 0
            rvalid_reg = 0
            rdata_reg = 0
            awaddr_reg = 0
            araddr_reg = 0
            mem = {}
        else:
            s_axil_awvalid = ctx.get_input("s_axil_awvalid", 0)
            s_axil_wvalid = ctx.get_input("s_axil_wvalid", 0)
            s_axil_awaddr = ctx.get_input("s_axil_awaddr", 0)
            s_axil_wdata = ctx.get_input("s_axil_wdata", 0)
            s_axil_bready = ctx.get_input("s_axil_bready", 0)

            s_axil_arvalid = ctx.get_input("s_axil_arvalid", 0)
            s_axil_araddr = ctx.get_input("s_axil_araddr", 0)
            s_axil_rready = ctx.get_input("s_axil_rready", 0)

            # Write response clear
            if s_axil_bready and bvalid_reg:
                bvalid_reg = 0

            # Read response clear
            if s_axil_rready and rvalid_reg:
                rvalid_reg = 0

            # Write transaction: awvalid & wvalid & !bvalid
            if s_axil_awvalid and s_axil_wvalid and (not bvalid_reg):
                awready_reg = 1
                wready_reg = 1
                bvalid_reg = 1
                awaddr_reg = s_axil_awaddr
                mem[s_axil_awaddr] = s_axil_wdata
            else:
                awready_reg = 0
                wready_reg = 0

            # Read transaction: arvalid & (!rvalid | rready)
            if s_axil_arvalid and (not rvalid_reg or s_axil_rready):
                arready_reg = 1
                rvalid_reg = 1
                araddr_reg = s_axil_araddr
                rdata_reg = mem.get(s_axil_araddr, 0)
            else:
                arready_reg = 0

        ctx.set_output("s_axil_awready", awready_reg)
        ctx.set_output("s_axil_wready", wready_reg)
        ctx.set_output("s_axil_bvalid", bvalid_reg)
        ctx.set_output("s_axil_bresp", 0)
        ctx.set_output("s_axil_arready", arready_reg)
        ctx.set_output("s_axil_rvalid", rvalid_reg)
        ctx.set_output("s_axil_rdata", rdata_reg)
        ctx.set_output("s_axil_rresp", 0)

        ctx.set_state("awready_reg", awready_reg)
        ctx.set_state("wready_reg", wready_reg)
        ctx.set_state("bvalid_reg", bvalid_reg)
        ctx.set_state("arready_reg", arready_reg)
        ctx.set_state("rvalid_reg", rvalid_reg)
        ctx.set_state("rdata_reg", rdata_reg)
        ctx.set_state("awaddr_reg", awaddr_reg)
        ctx.set_state("araddr_reg", araddr_reg)
        ctx.set_state("mem", mem)

    return behavior


# Register AXI-Lite templates
TemplateRegistry.register("axil_ram", axil_ram_template)

__all__ = [
    "axil_ram_template",
]
