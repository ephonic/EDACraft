"""
skills.interfaces.ethernet.arch_templates — Ethernet Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_ethernet_arch(
    ts_width: int = 96,
    ts_offset: int = 1,
) -> ArchDefinition:
    """Build Ethernet architecture with 1 PE: ptp_ts_extract."""
    behavior = TemplateRegistry.get("ptp_ts_extract")
    user_width = ts_width + ts_offset

    pe = ProcessingElement(
        name="PTP_TS_EXTRACT", pe_type="ptp_ts_extract",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("s_axis_tlast", "input", 1),
            PortDesc("s_axis_tuser", "input", user_width),
        ],
        outputs=[
            PortDesc("m_axis_ts", "output", ts_width),
            PortDesc("m_axis_ts_valid", "output", 1),
        ],
        state=[
            StateDesc("frame_reg", "int", "Frame tracking", rtl_type="reg", rtl_width=1),
        ],
        behavior=behavior(ts_width=ts_width, ts_offset=ts_offset) if behavior else None,
        can_stall=False, latency=0,
    )

    return ArchDefinition(
        name="Ethernet",
        description=f"PTP timestamp extract: {ts_width}-bit from tuser[{ts_offset}+:{ts_width}]",
        isa="protocol",
        processing_elements=[pe],
        interconnects=[],
        model=Protocol_Model(),
    )


Ethernet_TSModel = Protocol_Model

__all__ = ["build_ethernet_arch", "Ethernet_TSModel"]
