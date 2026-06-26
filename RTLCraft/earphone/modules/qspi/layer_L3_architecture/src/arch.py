"""L3 ArchitectureIR for the EarphoneQSPI module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QSPIArchitecture:
    """Micro-architecture contract for the QSPI XIP controller."""

    name: str = "EarphoneQSPI"
    role: str = "Memory-mapped XIP controller for external quad-SPI Flash reads."
    pipeline: str = "multi-phase read finite-state machine"
    phases: List[str] = field(default_factory=lambda: ["idle", "cmd", "addr", "dummy", "data"])
    addr_width: int = 32
    data_width: int = 32
    read_command: str = "0xEB"
    host_protocol: str = "req/ready host read channel to quad-SPI pad interface"
    timing: str = "First-word reads span command, address, dummy, and data phases before ready is asserted."
    invariants: List[str] = field(default_factory=lambda: [
        "The controller only asserts ready after the full read data phase completes.",
        "QSPI outputs drive command/address phases and release the IO bus during data capture.",
        "Chip select remains active whenever the FSM is outside the idle phase.",
    ])


ARCH = QSPIArchitecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "phases": list(ARCH.phases),
        "addr_width": ARCH.addr_width,
        "data_width": ARCH.data_width,
        "read_command": ARCH.read_command,
        "host_protocol": ARCH.host_protocol,
        "timing": ARCH.timing,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["QSPIArchitecture", "ARCH", "describe"]
