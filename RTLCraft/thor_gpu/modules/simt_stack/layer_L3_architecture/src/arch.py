"""L3 ArchitectureIR for the ThorSIMTStack module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SIMTStackArchitecture:
    name: str = "ThorSIMTStack"
    role: str = "SIMT divergence/reconvergence stack for conditional branches."
    pipeline: str = "combinational push/pop with registered stack pointers"
    stages: List[str] = field(default_factory=lambda: ["stack_update", "output"])
    mask_width: int = 8
    max_depth: int = 8
    pc_width: int = 32
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "On push, the not-taken active lanes are saved with the reconvergence PC.",
        "On pop, control resumes at the saved PC with the saved mask.",
        "A divergent branch only pushes when taken and not-taken lanes both exist.",
    ])


ARCH = SIMTStackArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "mask_width": ARCH.mask_width,
        "max_depth": ARCH.max_depth,
        "pc_width": ARCH.pc_width,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["SIMTStackArchitecture", "ARCH", "describe"]
