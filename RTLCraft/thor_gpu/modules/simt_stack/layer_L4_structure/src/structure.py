"""L4 StructuralIR for the ThorSIMTStack module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class SIMTStackStructure:
    name: str = "ThorSIMTStack"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "stack_storage",
            "Up to 8 frames of (reconverge_pc[32], not_taken_mask[8]).",
            ["push", "pop", "frame_pc", "frame_mask"],
        ),
        SubBlock(
            "stack_pointer",
            "Depth pointer controlling push/pop addressing.",
            ["sp", "stack_depth"],
        ),
        SubBlock(
            "control_mux",
            "Select next_pc/next_mask between push path and pop path.",
            ["branch_pc", "reconverge_pc", "taken_mask", "next_pc", "next_mask"],
        ),
    ])


STRUCTURE = SIMTStackStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into stack storage, stack pointer, and control mux.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["branch_control", "reconvergence"],
    }


__all__ = ["SubBlock", "SIMTStackStructure", "STRUCTURE", "describe"]
