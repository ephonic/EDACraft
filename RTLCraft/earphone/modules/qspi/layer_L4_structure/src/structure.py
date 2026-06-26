"""L4 StructuralIR for the EarphoneQSPI module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class QSPIStructure:
    """Structural decomposition of the QSPI controller."""

    name: str = "EarphoneQSPI"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "host_request_frontend",
            "Latch the host request and address before the serial transfer launches.",
            ["req", "addr", "ready", "rdata"],
        ),
        SubBlock(
            "phase_fsm",
            "Sequence command, address, dummy, and data phases for the XIP read protocol.",
            ["state", "counter", "shift", "addr_reg"],
        ),
        SubBlock(
            "qspi_pad_control",
            "Drive chip-select, serial clock, and bidirectional quad IO enables.",
            ["qspi_sck", "qspi_cs_n", "qspi_io_o", "qspi_io_i", "qspi_io_oe"],
        ),
    ])


STRUCTURE = QSPIStructure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural decomposition into host frontend, read-phase FSM, and QSPI pad control.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["host_req_ready", "qspi_pads"],
    }


__all__ = ["SubBlock", "QSPIStructure", "STRUCTURE", "describe"]
