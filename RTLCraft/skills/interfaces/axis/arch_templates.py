"""
skills.interfaces.axis.arch_templates — AXI-Stream Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_axis_arch(
    data_width: int = 8,
    m_data_width: int = 32,
    m_count: int = 4,
) -> ArchDefinition:
    """Build AXI-Stream architecture with 3 PEs."""
    reg_behavior = TemplateRegistry.get("axis_register")
    adapter_behavior = TemplateRegistry.get("axis_adapter")
    broadcast_behavior = TemplateRegistry.get("axis_broadcast")
    seg_count = m_data_width // data_width

    pe_reg = ProcessingElement(
        name="AXIS_REGISTER", pe_type="axis_register",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("s_axis_tdata", "input", data_width),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("m_axis_tready", "input", 1),
        ],
        outputs=[
            PortDesc("s_axis_tready", "output", 1),
            PortDesc("m_axis_tdata", "output", data_width),
            PortDesc("m_axis_tvalid", "output", 1),
        ],
        state=[
            StateDesc("s_tready_reg", "int", "Input ready", rtl_type="reg", rtl_width=1),
            StateDesc("m_valid_reg", "int", "Output valid", rtl_type="reg", rtl_width=1),
            StateDesc("temp_valid_reg", "int", "Temp valid", rtl_type="reg", rtl_width=1),
        ],
        behavior=reg_behavior(data_width=data_width) if reg_behavior else None,
        can_stall=False, latency=1,
    )

    pe_adapter = ProcessingElement(
        name="AXIS_ADAPTER", pe_type="axis_adapter",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("s_axis_tdata", "input", data_width),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("s_axis_tlast", "input", 1),
            PortDesc("m_axis_tready", "input", 1),
        ],
        outputs=[
            PortDesc("s_axis_tready", "output", 1),
            PortDesc("m_axis_tdata", "output", m_data_width),
            PortDesc("m_axis_tvalid", "output", 1),
            PortDesc("m_axis_tlast", "output", 1),
        ],
        state=[
            StateDesc("seg_cnt", "int", "Segment counter", rtl_type="reg", rtl_width=max(seg_count.bit_length(), 1)),
            StateDesc("m_valid_reg", "int", "Output valid", rtl_type="reg", rtl_width=1),
        ],
        behavior=adapter_behavior(s_data_width=data_width, m_data_width=m_data_width) if adapter_behavior else None,
        can_stall=False, latency=1,
    )

    pe_broadcast = ProcessingElement(
        name="AXIS_BROADCAST", pe_type="axis_broadcast",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("s_axis_tdata", "input", data_width),
            PortDesc("s_axis_tvalid", "input", 1),
            PortDesc("m_axis_tready", "input", m_count),
        ],
        outputs=[
            PortDesc("s_axis_tready", "output", 1),
            PortDesc("m_axis_tdata", "output", m_count * data_width),
            PortDesc("m_axis_tvalid", "output", m_count),
        ],
        state=[
            StateDesc("s_tready_reg", "int", "Input ready", rtl_type="reg", rtl_width=1),
            StateDesc("m_valid_reg", "int", "Output valid vector", rtl_type="reg", rtl_width=m_count),
        ],
        behavior=broadcast_behavior(m_count=m_count, data_width=data_width) if broadcast_behavior else None,
        can_stall=False, latency=1,
    )

    arch = ArchDefinition(
        name="AXI-Stream",
        description=f"AXI-Stream components: register, adapter ({data_width}→{m_data_width}), broadcast (1→{m_count})",
        isa="protocol",
        processing_elements=[pe_reg, pe_adapter, pe_broadcast],
        interconnects=[],
        model=Protocol_Model(),
    )

    return arch


AXIS_StreamModel = Protocol_Model

__all__ = ["build_axis_arch", "AXIS_StreamModel"]
