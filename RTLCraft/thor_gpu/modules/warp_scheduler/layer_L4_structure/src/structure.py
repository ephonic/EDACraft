"""L4 StructuralIR for the ThorWarpScheduler module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class WarpSchedulerStructure:
    name: str = "ThorWarpScheduler"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "idle_decode",
            "Decode per-warp idle status (IDLE/DONE/BARRIER) from warp state inputs.",
            ["warp_idle", "warp_done", "warp_at_barrier"],
        ),
        SubBlock(
            "sticky_rr_logic",
            "Compute next warp_sel using the sticky round-robin rule.",
            ["warp_sel", "warp_idle", "next_warp_sel"],
        ),
        SubBlock(
            "barrier_sync",
            "Detect all-at-barrier and assert barrier_release.",
            ["warp_at_barrier", "warp_done", "barrier_release"],
        ),
        SubBlock(
            "sel_register",
            "Register the selected warp index.",
            ["next_warp_sel", "warp_sel"],
        ),
    ])


STRUCTURE = WarpSchedulerStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into idle decode, sticky-RR logic, barrier sync, and sel register.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["warp_status", "warp_selection"],
    }


__all__ = ["SubBlock", "WarpSchedulerStructure", "STRUCTURE", "describe"]
