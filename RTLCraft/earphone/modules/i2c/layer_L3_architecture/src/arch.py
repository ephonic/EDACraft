"""L3 ArchitectureIR for the EarphoneI2C module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class I2CArchitecture:
    """Micro-architecture contract for the APB I2C controller."""

    name: str = "EarphoneI2C"
    role: str = "APB-programmable single-byte I2C master controller."
    pipeline: str = "register-programmed byte-controller state machine"
    states: List[str] = field(default_factory=lambda: ["idle", "start", "byte", "ack", "data", "stop", "finish"])
    apb_addr_width: int = 12
    transaction_data_width: int = 8
    host_protocol: str = "APB4 register access to open-drain I2C pin control"
    timing: str = "APB accesses complete immediately; byte transfers run through a start/address/ack/data/stop FSM."
    invariants: List[str] = field(default_factory=lambda: [
        "Register writes program ctrl and data before the byte controller launches.",
        "Open-drain outputs are driven through scl_oe and sda_oe rather than direct push-pull pins.",
        "Read and write directions share the same byte-level controller state machine.",
    ])


ARCH = I2CArchitecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "states": list(ARCH.states),
        "apb_addr_width": ARCH.apb_addr_width,
        "transaction_data_width": ARCH.transaction_data_width,
        "host_protocol": ARCH.host_protocol,
        "timing": ARCH.timing,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["I2CArchitecture", "ARCH", "describe"]
