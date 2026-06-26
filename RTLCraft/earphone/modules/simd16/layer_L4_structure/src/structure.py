"""L4 StructuralIR for the EarphoneSIMD16 module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class SIMD16Structure:
    """Structural decomposition of the SIMD16 accelerator."""

    name: str = "EarphoneSIMD16"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "int16_lane_array",
            "Compute per-lane INT16 arithmetic and logic operations.",
            ["vsrc0", "vsrc1", "op", "pred", "int_result"],
        ),
        SubBlock(
            "fp16_pipeline",
            "Advance FP16 MAC operands across three registered pipeline stages.",
            ["vsrc0", "vsrc1", "vsrc2", "pred", "fp_s0_valid", "fp_s1_valid", "fp_s2_valid"],
        ),
        SubBlock(
            "predicate_mask",
            "Apply the per-lane predicate bits to both datapaths.",
            ["pred", "int_result", "fp_s2_result"],
        ),
        SubBlock(
            "result_mux",
            "Select the active datapath result and expose vdst/done.",
            ["int_valid", "fp_s2_valid", "vdst", "done"],
        ),
    ])


STRUCTURE = SIMD16Structure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural decomposition into INT16 lanes, FP16 pipeline, predicate masking, and result selection.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["vector_operands", "vector_result"],
    }


__all__ = ["SubBlock", "SIMD16Structure", "STRUCTURE", "describe"]
