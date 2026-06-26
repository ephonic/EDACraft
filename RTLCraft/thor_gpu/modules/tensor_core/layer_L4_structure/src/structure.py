"""L4 StructuralIR for the ThorTensorCore module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class TensorCoreStructure:
    name: str = "ThorTensorCore"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "operand_unpack",
            "Unpack the 512-bit A/B matrices into 8x8 INT8 elements and C into 8x8 INT32.",
            ["a", "b", "c", "A_elem", "B_elem", "C_elem"],
        ),
        SubBlock(
            "mac_array",
            "8x8 INT32 accumulators, each summing 8 INT8*INT8 products (k-dimension).",
            ["A_elem", "B_elem", "C_elem", "acc_en", "acc"],
        ),
        SubBlock(
            "result_pack",
            "Pack the 8x8 INT32 result back into the 2048-bit output vector.",
            ["acc", "result"],
        ),
    ])


STRUCTURE = TensorCoreStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into operand unpack, MAC array, and result pack.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["matrix_operands", "matrix_result"],
    }


__all__ = ["SubBlock", "TensorCoreStructure", "STRUCTURE", "describe"]
