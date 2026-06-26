"""L3 ArchitectureIR for the ThorCluster module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ClusterArchitecture:
    name: str = "ThorCluster"
    role: str = "2-SM compute cluster sharing one global memory port via a round-robin L2 arbiter."
    pipeline: str = "SM x2 -> round-robin L2 arbiter -> global memory"
    stages: List[str] = field(default_factory=lambda: ["sm_compute", "l2_arbiter", "global_memory"])
    nsm: int = 2
    arbiter: str = "round-robin (1-bit grant toggling on any_req & mem_ready)"
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "Each SM owns its IMEM write port and its warp state.",
        "The L2 arbiter grants one SM per cycle and toggles on completion.",
        "all_done asserts when both SMs report sm_done.",
        "Global memory responses are steered to the SM that holds the grant.",
    ])


ARCH = ClusterArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "nsm": ARCH.nsm,
        "arbiter": ARCH.arbiter,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["ClusterArchitecture", "ARCH", "describe"]
