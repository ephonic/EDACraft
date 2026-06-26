"""
skills.interfaces.axi_lite.arch_templates — AXI-Lite RAM Architecture Templates

Build ProcessingElement and ArchDefinition for AXI-Lite RAM components.
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc, CycleContext
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_axil_ram_arch(
    data_width: int = 32,
    addr_width: int = 16,
) -> ArchDefinition:
    """Build AXI-Lite RAM architecture with a single axil_ram PE.

    PE:
      - AXIL_RAM: AXI-Lite slave RAM (word-level read/write, zero-initialized)

    Ports:
      - AXI-Lite write address channel (AW): awaddr/awvalid/awready
      - AXI-Lite write data channel (W): wdata/wvalid/wready
      - AXI-Lite write response channel (B): bresp/bvalid/bready
      - AXI-Lite read address channel (AR): araddr/arvalid/arready
      - AXI-Lite read data channel (R): rdata/rresp/rvalid/rready
    """
    axil_ram_behavior = TemplateRegistry.get("axil_ram")

    pe_ram = ProcessingElement(
        name="AXIL_RAM", pe_type="axil_ram",
        inputs=[
            PortDesc("clk", "input", 1),
            PortDesc("rst", "input", 1),
            PortDesc("s_axil_awaddr", "input", addr_width),
            PortDesc("s_axil_awvalid", "input", 1),
            PortDesc("s_axil_wdata", "input", data_width),
            PortDesc("s_axil_wvalid", "input", 1),
            PortDesc("s_axil_bready", "input", 1),
            PortDesc("s_axil_araddr", "input", addr_width),
            PortDesc("s_axil_arvalid", "input", 1),
            PortDesc("s_axil_rready", "input", 1),
        ],
        outputs=[
            PortDesc("s_axil_awready", "output", 1),
            PortDesc("s_axil_wready", "output", 1),
            PortDesc("s_axil_bresp", "output", 2),
            PortDesc("s_axil_bvalid", "output", 1),
            PortDesc("s_axil_arready", "output", 1),
            PortDesc("s_axil_rdata", "output", data_width),
            PortDesc("s_axil_rresp", "output", 2),
            PortDesc("s_axil_rvalid", "output", 1),
        ],
        state=[
            StateDesc("awready_reg", "int", "Write address ready", rtl_type="reg", rtl_width=1),
            StateDesc("wready_reg", "int", "Write data ready", rtl_type="reg", rtl_width=1),
            StateDesc("bvalid_reg", "int", "Write response valid", rtl_type="reg", rtl_width=1),
            StateDesc("arready_reg", "int", "Read address ready", rtl_type="reg", rtl_width=1),
            StateDesc("rvalid_reg", "int", "Read response valid", rtl_type="reg", rtl_width=1),
            StateDesc("rdata_reg", "int", "Read data register", rtl_type="reg", rtl_width=data_width),
            StateDesc("awaddr_reg", "int", "Latched write address", rtl_type="reg", rtl_width=addr_width),
            StateDesc("araddr_reg", "int", "Latched read address", rtl_type="reg", rtl_width=addr_width),
        ],
        behavior=axil_ram_behavior(data_width=data_width, addr_width=addr_width) if axil_ram_behavior else None,
        can_stall=False, latency=1,
    )

    arch = ArchDefinition(
        name="AXI-Lite RAM",
        description=f"AXI-Lite RAM: {data_width}-bit words, 2^{addr_width} entries. "
                     "Word-level read/write with zero init.",
        isa="protocol",
        processing_elements=[pe_ram],
        interconnects=[],
        model=Protocol_Model(),
    )

    return arch


AXIL_RAM_Model = Protocol_Model

__all__ = ["build_axil_ram_arch", "AXIL_RAM_Model"]
