"""L3 ArchitectureIR for the ThorGpuSM module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GpuSMArchitecture:
    name: str = "ThorGpuSM"
    role: str = "One streaming multiprocessor: scheduler + SIMT core + exec units + LSU + shared memory."
    pipeline: str = "fetch -> decode -> execute/writeback (multi-cycle for memory)"
    stages: List[str] = field(default_factory=lambda: ["fetch", "decode", "execute", "writeback"])
    xlen: int = 32
    nlane: int = 8
    vlen: int = 256
    vregs: int = 8
    nwarp: int = 4
    imem_depth: int = 32
    accw: int = 64
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "VRF is a flat array; warp w owns indices [w*VREGS, (w+1)*VREGS).",
        "The sticky-RR scheduler dispatches one warp per cycle.",
        "VMAC accumulates lane-0 product into a 64-bit per-warp accumulator.",
        "sm_done asserts when all warps reach DONE.",
    ])


ARCH = GpuSMArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "xlen": ARCH.xlen, "nlane": ARCH.nlane, "vlen": ARCH.vlen,
        "vregs": ARCH.vregs, "nwarp": ARCH.nwarp,
        "imem_depth": ARCH.imem_depth, "accw": ARCH.accw,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["GpuSMArchitecture", "ARCH", "describe"]
