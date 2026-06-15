"""L4 StructuralIR contract for the Earphone top-level SoC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class TopConnection:
    source: str
    sink: str
    protocol: str
    description: str


@dataclass(frozen=True)
class TopSubBlock:
    instance: str
    module: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class TopLevelStructure:
    """Structural contract for the EarphoneTop hierarchy."""

    name: str = "EarphoneTop"
    subblocks: List[TopSubBlock] = field(default_factory=lambda: [
        TopSubBlock("cpu", "EarphoneRV32", ["imem_bus", "dmem_bus"]),
        TopSubBlock("simd16", "EarphoneSIMD16", ["accelerator_control"]),
        TopSubBlock("fft256", "EarphoneFFT256", ["streaming_sample_path"]),
        TopSubBlock("qspi", "EarphoneQSPI", ["qspi_pads", "xip_req_ready"]),
        TopSubBlock("apb_bridge", "EarphoneAPBBridge", ["apb_debug", "apb_slave_slots"]),
        TopSubBlock("sram", "EarphoneSRAM256K", ["apb_slot_1"]),
        TopSubBlock("i2c", "EarphoneI2C", ["apb_slot_4", "i2c_pads"]),
    ])
    connections: List[TopConnection] = field(default_factory=lambda: [
        TopConnection("apb_debug", "apb_bridge", "APB4", "External test/debug access enters through APB bridge."),
        TopConnection("apb_bridge.slot1", "sram", "APB4", "Slot 1 routes to on-chip SRAM."),
        TopConnection("apb_bridge.slot4", "i2c", "APB4", "Slot 4 routes to I2C master registers."),
        TopConnection("qspi", "qspi_pads", "QSPI", "QSPI controller owns the external flash pad bundle."),
        TopConnection("i2c", "i2c_pads", "I2C", "I2C master owns SCL/SDA input/output/enable pads."),
    ])


TOP_STRUCTURE = TopLevelStructure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation and tests."""
    return {
        "name": TOP_STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "subblocks": [subblock.instance for subblock in TOP_STRUCTURE.subblocks],
        "module_bindings": {subblock.instance: subblock.module for subblock in TOP_STRUCTURE.subblocks},
        "connections": [f"{conn.source}->{conn.sink}:{conn.protocol}" for conn in TOP_STRUCTURE.connections],
        "external_interfaces": ["apb_debug", "qspi_pads", "i2c_pads", "imem_bus", "dmem_bus"],
    }


__all__ = ["TopConnection", "TopSubBlock", "TopLevelStructure", "TOP_STRUCTURE", "describe"]
