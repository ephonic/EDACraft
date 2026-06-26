"""L4 StructuralIR for the EarphoneSRAM256K module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class SRAM256KStructure:
    """Structural decomposition of the SRAM block."""

    name: str = "EarphoneSRAM256K"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "apb_frontend",
            "Decode APB transfer control and expose the memory-side enables.",
            ["paddr", "pwdata", "pwrite", "psel", "penable", "pready", "pslverr"],
        ),
        SubBlock(
            "byte_write_mask",
            "Merge byte strobes with the current memory word to form mem_wdata.",
            ["pstrb", "pwdata", "mem_rdata", "mem_wdata"],
        ),
        SubBlock(
            "mem_array",
            "Store the 64K x 32-bit SRAM contents.",
            ["mem", "addr_word", "mem_rdata", "mem_wdata"],
        ),
        SubBlock(
            "read_data_register",
            "Register the returned memory data onto the APB read data channel.",
            ["rdata_reg", "prdata"],
        ),
    ])


STRUCTURE = SRAM256KStructure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural decomposition into APB frontend, byte-write mask, memory array, and readback register.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["apb_slave", "sram_array"],
    }


__all__ = ["SubBlock", "SRAM256KStructure", "STRUCTURE", "describe"]
