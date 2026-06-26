"""
skills.interfaces.pcie.arch_templates — PCIe Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_pcie_arch(
    input_width: int = 2,
    count_width: int = 4,
    fc_width: int = 16,
    fc_index: int = 0,
) -> ArchDefinition:
    """Build PCIe architecture with 2 PEs."""
    pm_behavior = TemplateRegistry.get("pulse_merge")
    fc_behavior = TemplateRegistry.get("pcie_ptile_fc")

    pe_pm = ProcessingElement(
        name="PULSE_MERGE", pe_type="pulse_merge",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("pulse_in", "input", input_width),
        ],
        outputs=[
            PortDesc("count_out", "output", count_width),
            PortDesc("pulse_out", "output", 1),
        ],
        state=[
            StateDesc("count_reg", "int", "Pulse counter", rtl_type="reg", rtl_width=count_width),
        ],
        behavior=pm_behavior(input_width=input_width, count_width=count_width) if pm_behavior else None,
        can_stall=False, latency=1,
    )

    pe_fc = ProcessingElement(
        name="PCIE_PTILE_FC_COUNTER", pe_type="pcie_ptile_fc",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("tx_cdts_limit", "input", fc_width),
            PortDesc("tx_cdts_limit_tdm_idx", "input", 3),
            PortDesc("fc_dec", "input", fc_width),
        ],
        outputs=[
            PortDesc("fc_av", "output", fc_width),
        ],
        state=[
            StateDesc("fc_cap_reg", "int", "Credit capacity", rtl_type="reg", rtl_width=fc_width),
            StateDesc("fc_limit_reg", "int", "Credit limit", rtl_type="reg", rtl_width=fc_width),
            StateDesc("fc_av_reg", "int", "Available credits", rtl_type="reg", rtl_width=fc_width),
        ],
        behavior=fc_behavior(width=fc_width, index=fc_index) if fc_behavior else None,
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="PCIe",
        description=f"PCIe interface: pulse_merge({input_width}→{count_width}), fc_counter({fc_width}-bit)",
        isa="protocol",
        processing_elements=[pe_pm, pe_fc],
        interconnects=[],
        model=Protocol_Model(),
    )


PCIe_Model = Protocol_Model

__all__ = ["build_pcie_arch", "PCIe_Model"]
