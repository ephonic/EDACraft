"""L4 StructuralIR for the EarphoneAPBBridge module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class APBBridgeStructure:
    """Structural decomposition of the APB bridge."""

    name: str = "EarphoneAPBBridge"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "region_decode",
            "Decode the APB master address into a one-hot peripheral slot select.",
            ["m_paddr", "m_psel", "s_psel"],
        ),
        SubBlock(
            "request_fanout",
            "Forward request address, write data, strobes, and control into the selected slot.",
            ["m_paddr", "m_pwdata", "m_pwrite", "m_penable", "m_pstrb", "s_paddr", "s_pwdata", "s_pwrite", "s_penable", "s_pstrb"],
        ),
        SubBlock(
            "response_mux",
            "Return the selected slave response to the APB master interface.",
            ["s_prdata", "s_pready", "s_pslverr", "m_prdata", "m_pready", "m_pslverr"],
        ),
    ])


STRUCTURE = APBBridgeStructure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural decomposition of the APB bridge into decode, fanout, and response mux logic.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["master_apb", "slave_apb_slots"],
    }


__all__ = ["SubBlock", "APBBridgeStructure", "STRUCTURE", "describe"]
