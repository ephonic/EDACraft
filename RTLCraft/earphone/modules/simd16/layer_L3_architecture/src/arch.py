"""L3 ArchitectureIR for the EarphoneSIMD16 module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SIMD16Architecture:
    """Micro-architecture contract for the SIMD16 accelerator."""

    name: str = "EarphoneSIMD16"
    role: str = "16-lane vector ALU with single-cycle INT16 ops and a 3-stage FP16 MAC pipeline."
    pipeline: str = "single-cycle INT16 path plus 3-stage FP16 MAC pipeline"
    stages: List[str] = field(default_factory=lambda: ["issue", "int_execute", "fp_stage0", "fp_stage1", "fp_stage2", "writeback"])
    vector_width: int = 256
    lane_width: int = 16
    lane_count: int = 16
    int_latency_cycles: int = 1
    fp_latency_cycles: int = 3
    predicate_support: str = "16-bit per-lane mask"
    invariants: List[str] = field(default_factory=lambda: [
        "INT16 operations complete in one cycle when start is asserted in integer mode.",
        "FP16 MAC results appear after three occupied pipeline stages.",
        "Predicate masking zeros disabled lanes in both INT16 and FP16 datapaths.",
    ])


ARCH = SIMD16Architecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "vector_width": ARCH.vector_width,
        "lane_width": ARCH.lane_width,
        "lane_count": ARCH.lane_count,
        "int_latency_cycles": ARCH.int_latency_cycles,
        "fp_latency_cycles": ARCH.fp_latency_cycles,
        "predicate_support": ARCH.predicate_support,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["SIMD16Architecture", "ARCH", "describe"]
