"""L4 StructuralIR for the ThorSharedMemory module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class SharedMemoryStructure:
    name: str = "ThorSharedMemory"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "sram_array",
            "4096x256-bit storage array (single-port).",
            ["addr", "wdata", "we", "re", "array_rdata"],
        ),
        SubBlock(
            "read_register",
            "256-bit read-data output register.",
            ["array_rdata", "rdata"],
        ),
        SubBlock(
            "address_decode",
            "12-bit address decode and write/read priority mux.",
            ["addr", "we", "re"],
        ),
    ])


STRUCTURE = SharedMemoryStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into SRAM array, read register, and address decode.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["mem_port", "read_data"],
    }


__all__ = ["SubBlock", "SharedMemoryStructure", "STRUCTURE", "describe"]
