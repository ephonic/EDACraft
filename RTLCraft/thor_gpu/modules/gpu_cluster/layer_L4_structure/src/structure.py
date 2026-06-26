"""L4 StructuralIR for the ThorCluster module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class ClusterStructure:
    name: str = "ThorCluster"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock("sm_array", "2 streaming multiprocessors.", ["sm0_*", "sm1_*"]),
        SubBlock("l2_arbiter", "Round-robin grant over the 2 SM memory requests.",
                 ["sm0_mem_req", "sm1_mem_req", "grant", "mem_req"]),
        SubBlock("response_demux", "Steer the global response to the granted SM.",
                 ["mem_valid", "mem_rdata", "sm0_mem_valid", "sm1_mem_valid"]),
    ])


STRUCTURE = ClusterStructure()


def describe() -> Dict[str, Any]:
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Decomposition into SM array, L2 arbiter, and response demux.",
        "subblocks": [sb.name for sb in STRUCTURE.subblocks],
        "external_interfaces": ["global_memory", "cluster_status"],
    }


__all__ = ["SubBlock", "ClusterStructure", "STRUCTURE", "describe"]
