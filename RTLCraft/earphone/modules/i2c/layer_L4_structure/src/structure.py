"""L4 StructuralIR for the EarphoneI2C module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class I2CStructure:
    """Structural decomposition of the I2C controller."""

    name: str = "EarphoneI2C"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "apb_register_bank",
            "Expose ctrl, data, and status registers on the APB slave interface.",
            ["paddr", "pwdata", "prdata", "pwrite", "psel", "penable", "pready"],
        ),
        SubBlock(
            "byte_controller_fsm",
            "Sequence start, address, ack, data, and stop phases for a single-byte transfer.",
            ["state", "bit_cnt", "shift", "ctrl", "data", "status"],
        ),
        SubBlock(
            "open_drain_pad_ctrl",
            "Drive the external I2C pins through separate output and output-enable signals.",
            ["scl_i", "scl_o", "scl_oe", "sda_i", "sda_o", "sda_oe"],
        ),
    ])


STRUCTURE = I2CStructure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural decomposition into APB register control, byte FSM, and open-drain pad logic.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["apb_slave", "i2c_pads"],
    }


__all__ = ["SubBlock", "I2CStructure", "STRUCTURE", "describe"]
