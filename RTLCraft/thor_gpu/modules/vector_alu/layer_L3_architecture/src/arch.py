"""L3 ArchitectureIR for the ThorVectorALU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class VectorALUArchitecture:
    """Micro-architecture contract for the Thor vector ALU."""

    name: str = "ThorVectorALU"
    role: str = "8-lane INT32 vector ALU with per-lane active-mask predication."
    pipeline: str = "combinational per-lane compute feeding a 1-stage result register"
    stages: List[str] = field(default_factory=lambda: ["lane_compute", "result_register"])
    lane_width: int = 32
    lane_count: int = 8
    vector_width: int = 256
    latency_cycles: int = 1
    function_codes: List[int] = field(default_factory=lambda: [0, 1, 4, 5, 6, 7, 10, 12, 14])
    invariants: List[str] = field(default_factory=lambda: [
        "Each lane computes independently on a 32-bit slice of the source vectors.",
        "Disabled lanes (active_mask bit low) produce zero and clear their result_mask bit.",
        "ADD/SUB wrap modulo 2**32 (two's-complement).",
        "SLT is signed; SLTU is unsigned.",
        "Shift amount is masked to 5 bits (s2 & 0x1F).",
    ])


ARCH = VectorALUArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "lane_width": ARCH.lane_width,
        "lane_count": ARCH.lane_count,
        "vector_width": ARCH.vector_width,
        "latency_cycles": ARCH.latency_cycles,
        "function_codes": list(ARCH.function_codes),
        "invariants": list(ARCH.invariants),
    }


__all__ = ["VectorALUArchitecture", "ARCH", "describe"]
