"""L3 ArchitectureIR for the ThorWarpScheduler module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WarpSchedulerArchitecture:
    name: str = "ThorWarpScheduler"
    role: str = "Sticky round-robin warp scheduler with barrier synchronization."
    pipeline: str = "combinational scheduler decision feeding a warp_sel register"
    stages: List[str] = field(default_factory=lambda: ["decision", "warp_sel_register"])
    num_warps: int = 4
    policy: str = "sticky round-robin (advance only when current warp idle)"
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "warp_sel advances to warp_sel+1 only when the currently selected warp is idle.",
        "A warp is idle when in IDLE/DONE/BARRIER state.",
        "barrier_release asserts when all warps are at the barrier or done.",
        "sm_done asserts when all warps have reached DONE.",
    ])


ARCH = WarpSchedulerArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "num_warps": ARCH.num_warps,
        "policy": ARCH.policy,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["WarpSchedulerArchitecture", "ARCH", "describe"]
