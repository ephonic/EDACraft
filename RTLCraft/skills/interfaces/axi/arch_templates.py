"""
skills.interfaces.axi.arch_templates — AXI Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_axi_arch(
    data_width: int = 32,
    addr_width: int = 16,
) -> ArchDefinition:
    """Build AXI architecture with 1 PE: axi_dp_ram_simple."""
    behavior = TemplateRegistry.get("axi_dp_ram_simple")

    pe = ProcessingElement(
        name="AXI_DP_RAM_SIMPLE", pe_type="axi_dp_ram_simple",
        inputs=[
            PortDesc("a_clk", "input", 1), PortDesc("a_rst", "input", 1),
            PortDesc("a_awaddr", "input", addr_width),
            PortDesc("a_awvalid", "input", 1),
            PortDesc("a_wdata", "input", data_width),
            PortDesc("a_wvalid", "input", 1),
            PortDesc("a_bready", "input", 1),
            PortDesc("a_araddr", "input", addr_width),
            PortDesc("a_arvalid", "input", 1),
            PortDesc("a_rready", "input", 1),
            PortDesc("b_clk", "input", 1), PortDesc("b_rst", "input", 1),
            PortDesc("b_awaddr", "input", addr_width),
            PortDesc("b_awvalid", "input", 1),
            PortDesc("b_wdata", "input", data_width),
            PortDesc("b_wvalid", "input", 1),
            PortDesc("b_bready", "input", 1),
            PortDesc("b_araddr", "input", addr_width),
            PortDesc("b_arvalid", "input", 1),
            PortDesc("b_rready", "input", 1),
        ],
        outputs=[
            PortDesc("a_awready", "output", 1),
            PortDesc("a_wready", "output", 1),
            PortDesc("a_bresp", "output", 2),
            PortDesc("a_bvalid", "output", 1),
            PortDesc("a_arready", "output", 1),
            PortDesc("a_rdata", "output", data_width),
            PortDesc("a_rresp", "output", 2),
            PortDesc("a_rvalid", "output", 1),
            PortDesc("b_awready", "output", 1),
            PortDesc("b_wready", "output", 1),
            PortDesc("b_bresp", "output", 2),
            PortDesc("b_bvalid", "output", 1),
            PortDesc("b_arready", "output", 1),
            PortDesc("b_rdata", "output", data_width),
            PortDesc("b_rresp", "output", 2),
            PortDesc("b_rvalid", "output", 1),
        ],
        state=[
            StateDesc("a_bvalid_reg", "int", "Port A B valid", rtl_type="reg", rtl_width=1),
            StateDesc("a_rvalid_reg", "int", "Port A R valid", rtl_type="reg", rtl_width=1),
            StateDesc("b_bvalid_reg", "int", "Port B B valid", rtl_type="reg", rtl_width=1),
            StateDesc("b_rvalid_reg", "int", "Port B R valid", rtl_type="reg", rtl_width=1),
        ],
        behavior=behavior(data_width=data_width, addr_width=addr_width) if behavior else None,
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="AXI",
        description=f"AXI dual-port RAM: {data_width}-bit, 2^{addr_width} entries",
        isa="protocol",
        processing_elements=[pe],
        interconnects=[],
        model=Protocol_Model(),
    )


AXI_DP_RAM_Model = Protocol_Model

__all__ = ["build_axi_arch", "AXI_DP_RAM_Model"]
