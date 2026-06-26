"""L4 StructuralIR for the ThorVectorALU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class VectorALUStructure:
    """Structural decomposition of the Thor vector ALU."""

    name: str = "ThorVectorALU"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "lane_slice_array",
            "8 independent 32-bit lane compute slices (ADD/SUB/AND/OR/XOR/SLL/SRL/SLT/SLTU).",
            ["src1", "src2", "alu_fn", "active_mask", "lane_results"],
        ),
        SubBlock(
            "active_mask_decode",
            "Decode the 8-bit active mask into per-lane enable gates.",
            ["active_mask", "lane_en"],
        ),
        SubBlock(
            "result_register",
            "256-bit registered result plus 8-bit result_mask output.",
            ["lane_results", "result", "result_mask"],
        ),
    ])


STRUCTURE = VectorALUStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into per-lane compute slices, mask decode, and result register.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["vector_operands", "vector_result"],
    }


__all__ = ["SubBlock", "VectorALUStructure", "STRUCTURE", "describe"]
