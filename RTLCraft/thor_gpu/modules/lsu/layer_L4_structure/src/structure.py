"""L4 StructuralIR for the ThorLSU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class LSUStructure:
    name: str = "ThorLSU"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "request_gen",
            "Generate the memory request (req/wen/addr/wdata) from the op inputs.",
            ["op", "addr", "wdata", "valid_in", "mem_req", "mem_wen", "mem_addr", "mem_wdata"],
        ),
        SubBlock(
            "response_cap",
            "Capture the response (mem_valid/mem_rdata) into rdata/done.",
            ["mem_valid", "mem_rdata", "rdata", "done"],
        ),
    ])


STRUCTURE = LSUStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into request generator and response capture.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["mem_request", "mem_response"],
    }


__all__ = ["SubBlock", "LSUStructure", "STRUCTURE", "describe"]
