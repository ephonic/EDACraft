"""L4 StructuralIR for the ThorVectorFPU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class VectorFPUStructure:
    name: str = "ThorVectorFPU"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "fp_lane_array",
            "8 independent FP32 compute slices (FADD/FMUL/FMADD).",
            ["src1", "src2", "src3", "fpu_fn", "active_mask", "lane_results"],
        ),
        SubBlock(
            "active_mask_decode",
            "Decode the 8-bit active mask into per-lane FP enable gates.",
            ["active_mask", "lane_en"],
        ),
        SubBlock(
            "result_register",
            "256-bit registered result plus 8-bit result_mask output.",
            ["lane_results", "result", "result_mask"],
        ),
    ])


STRUCTURE = VectorFPUStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into FP lane array, mask decode, and result register.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["vector_operands", "vector_result"],
    }


__all__ = ["SubBlock", "VectorFPUStructure", "STRUCTURE", "describe"]
