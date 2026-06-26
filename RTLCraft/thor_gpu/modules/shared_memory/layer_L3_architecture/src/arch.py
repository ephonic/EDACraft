"""L3 ArchitectureIR for the ThorSharedMemory module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SharedMemoryArchitecture:
    name: str = "ThorSharedMemory"
    role: str = "Per-SM single-port shared SRAM (256-bit word, 4096 deep)."
    pipeline: str = "synchronous-read SRAM with a 1-stage read-data register"
    stages: List[str] = field(default_factory=lambda: ["array_read", "read_register"])
    word_width: int = 256
    addr_width: int = 12
    depth: int = 4096
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "Write has priority over a simultaneous read to the same address.",
        "Read data is registered (available one cycle after re is asserted).",
        "Uninitialized reads return zero.",
    ])


ARCH = SharedMemoryArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "word_width": ARCH.word_width,
        "addr_width": ARCH.addr_width,
        "depth": ARCH.depth,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["SharedMemoryArchitecture", "ARCH", "describe"]
