"""L3 ArchitectureIR for the ThorLSU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LSUArchitecture:
    name: str = "ThorLSU"
    role: str = "Vector load/store unit with memory request/response handshake."
    pipeline: str = "request issue followed by response capture"
    stages: List[str] = field(default_factory=lambda: ["request", "response"])
    data_width: int = 256
    addr_width: int = 32
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "mem_req asserts when a new op is presented and the port is ready.",
        "mem_wen is 1 for stores, 0 for loads.",
        "done asserts the cycle mem_valid is observed; rdata captures mem_rdata.",
    ])


ARCH = LSUArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "data_width": ARCH.data_width,
        "addr_width": ARCH.addr_width,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["LSUArchitecture", "ARCH", "describe"]
