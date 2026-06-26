"""L3 ArchitectureIR for the ThorVectorFPU module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class VectorFPUArchitecture:
    name: str = "ThorVectorFPU"
    role: str = "8-lane IEEE-754 FP32 vector FPU (FADD/FMUL/FMADD) with per-lane predication."
    pipeline: str = "per-lane FP32 compute feeding a 1-stage result register"
    stages: List[str] = field(default_factory=lambda: ["fp_compute", "result_register"])
    lane_width: int = 32
    lane_count: int = 8
    vector_width: int = 256
    datatype: str = "FP32"
    latency_cycles: int = 1
    function_codes: List[int] = field(default_factory=lambda: [0, 1, 2])
    invariants: List[str] = field(default_factory=lambda: [
        "FP32 operations follow IEEE-754 single precision with round-to-nearest-even.",
        "FMADD computes s1*s2 + s3 (fused semantics at the functional layer).",
        "Disabled lanes (active_mask bit low) produce zero and clear their result_mask bit.",
    ])


ARCH = VectorFPUArchitecture()


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
        "datatype": ARCH.datatype,
        "latency_cycles": ARCH.latency_cycles,
        "function_codes": list(ARCH.function_codes),
        "invariants": list(ARCH.invariants),
    }


__all__ = ["VectorFPUArchitecture", "ARCH", "describe"]
