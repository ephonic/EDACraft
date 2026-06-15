"""L3 ArchitectureIR for the EarphoneSRAM256K module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SRAM256KArchitecture:
    """Micro-architecture contract for the APB SRAM."""

    name: str = "EarphoneSRAM256K"
    role: str = "Single-port 256 KB APB SRAM with byte write strobes."
    pipeline: str = "single-cycle APB transfer with registered readback"
    stages: List[str] = field(default_factory=lambda: ["apb_request", "memory_access", "readback"])
    depth_words: int = 64 * 1024
    data_width: int = 32
    byte_lanes: int = 4
    read_latency_cycles: int = 1
    write_latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "Read data is returned through a registered prdata path.",
        "Write strobes merge new byte lanes with the existing memory word.",
        "The SRAM datapath only updates while an APB transfer is selected and enabled.",
    ])


ARCH = SRAM256KArchitecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "depth_words": ARCH.depth_words,
        "data_width": ARCH.data_width,
        "byte_lanes": ARCH.byte_lanes,
        "read_latency_cycles": ARCH.read_latency_cycles,
        "write_latency_cycles": ARCH.write_latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["SRAM256KArchitecture", "ARCH", "describe"]
