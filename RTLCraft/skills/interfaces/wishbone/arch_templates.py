"""
skills.interfaces.wishbone.arch_templates — Wishbone Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_wishbone_arch(
    data_width: int = 32,
    addr_width: int = 32,
) -> ArchDefinition:
    """Build Wishbone architecture with 2 PEs: wb_reg, wb_mux_2."""
    wb_reg_behavior = TemplateRegistry.get("wb_reg")
    wb_mux_behavior = TemplateRegistry.get("wb_mux_2")
    select_width = data_width // 8

    pe_reg = ProcessingElement(
        name="WB_REG", pe_type="wb_reg",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("wbm_adr_i", "input", addr_width),
            PortDesc("wbm_dat_i", "input", data_width),
            PortDesc("wbm_we_i", "input", 1),
            PortDesc("wbm_sel_i", "input", select_width),
            PortDesc("wbm_stb_i", "input", 1),
            PortDesc("wbm_cyc_i", "input", 1),
            PortDesc("wbs_dat_i", "input", data_width),
            PortDesc("wbs_ack_i", "input", 1),
            PortDesc("wbs_err_i", "input", 1),
            PortDesc("wbs_rty_i", "input", 1),
        ],
        outputs=[
            PortDesc("wbm_dat_o", "output", data_width),
            PortDesc("wbm_ack_o", "output", 1),
            PortDesc("wbm_err_o", "output", 1),
            PortDesc("wbm_rty_o", "output", 1),
            PortDesc("wbs_adr_o", "output", addr_width),
            PortDesc("wbs_dat_o", "output", data_width),
            PortDesc("wbs_we_o", "output", 1),
            PortDesc("wbs_sel_o", "output", select_width),
            PortDesc("wbs_stb_o", "output", 1),
            PortDesc("wbs_cyc_o", "output", 1),
        ],
        state=[
            StateDesc("wbs_cyc_o_reg", "int", "Cycle register", rtl_type="reg", rtl_width=1),
            StateDesc("wbs_stb_o_reg", "int", "Strobe register", rtl_type="reg", rtl_width=1),
        ],
        behavior=wb_reg_behavior(data_width=data_width, addr_width=addr_width) if wb_reg_behavior else None,
        can_stall=False, latency=1,
    )

    pe_mux = ProcessingElement(
        name="WB_MUX_2", pe_type="wb_mux_2",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("wbm_adr_i", "input", addr_width),
            PortDesc("wbm_dat_i", "input", data_width),
            PortDesc("wbm_we_i", "input", 1),
            PortDesc("wbm_sel_i", "input", select_width),
            PortDesc("wbm_stb_i", "input", 1),
            PortDesc("wbm_cyc_i", "input", 1),
            PortDesc("wbs0_dat_i", "input", data_width),
            PortDesc("wbs0_ack_i", "input", 1),
            PortDesc("wbs0_err_i", "input", 1),
            PortDesc("wbs0_rty_i", "input", 1),
            PortDesc("wbs0_addr", "input", addr_width),
            PortDesc("wbs0_addr_msk", "input", addr_width),
            PortDesc("wbs1_dat_i", "input", data_width),
            PortDesc("wbs1_ack_i", "input", 1),
            PortDesc("wbs1_err_i", "input", 1),
            PortDesc("wbs1_rty_i", "input", 1),
            PortDesc("wbs1_addr", "input", addr_width),
            PortDesc("wbs1_addr_msk", "input", addr_width),
        ],
        outputs=[
            PortDesc("wbm_dat_o", "output", data_width),
            PortDesc("wbm_ack_o", "output", 1),
            PortDesc("wbm_err_o", "output", 1),
            PortDesc("wbm_rty_o", "output", 1),
            PortDesc("wbs0_adr_o", "output", addr_width),
            PortDesc("wbs0_dat_o", "output", data_width),
            PortDesc("wbs0_we_o", "output", 1),
            PortDesc("wbs0_sel_o", "output", select_width),
            PortDesc("wbs0_stb_o", "output", 1),
            PortDesc("wbs0_cyc_o", "output", 1),
            PortDesc("wbs1_adr_o", "output", addr_width),
            PortDesc("wbs1_dat_o", "output", data_width),
            PortDesc("wbs1_we_o", "output", 1),
            PortDesc("wbs1_sel_o", "output", select_width),
            PortDesc("wbs1_stb_o", "output", 1),
            PortDesc("wbs1_cyc_o", "output", 1),
        ],
        state=[],
        behavior=wb_mux_behavior(data_width=data_width, addr_width=addr_width) if wb_mux_behavior else None,
        can_stall=False, latency=0,
    )

    arch = ArchDefinition(
        name="Wishbone",
        description=f"Wishbone bus interface: register slice + 2-to-1 MUX ({data_width}-bit)",
        isa="protocol",
        processing_elements=[pe_reg, pe_mux],
        interconnects=[],
        model=Protocol_Model(),
    )

    return arch


Wishbone_BusModel = Protocol_Model

__all__ = ["build_wishbone_arch", "Wishbone_BusModel"]
