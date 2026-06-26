"""L3 ArchitectureIR for the EarphoneAPBBridge module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class APBBridgeArchitecture:
    """Micro-architecture contract for the APB bridge."""

    name: str = "EarphoneAPBBridge"
    role: str = "APB4 address decoder and response mux for eight peripheral slots."
    pipeline: str = "single-cycle combinational decode"
    stages: List[str] = field(default_factory=lambda: ["decode", "select_fanout", "response_mux"])
    decode_field: str = "m_paddr[29:22]"
    slot_count: int = 8
    slave_region_size_bytes: int = 4 * 1024 * 1024
    host_protocol: str = "APB4 master ingress to APB4 peripheral fanout"
    timing: str = "Decode is combinational; the selected slave determines pready and pslverr timing."
    invariants: List[str] = field(default_factory=lambda: [
        "Exactly one slave slot is selected for an in-range address.",
        "The selected slave's pready and pslverr status are returned to the master.",
        "All request fields are broadcast unchanged into the selected APB slot.",
    ])


ARCH = APBBridgeArchitecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "decode_field": ARCH.decode_field,
        "slot_count": ARCH.slot_count,
        "slave_region_size_bytes": ARCH.slave_region_size_bytes,
        "host_protocol": ARCH.host_protocol,
        "timing": ARCH.timing,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["APBBridgeArchitecture", "ARCH", "describe"]
