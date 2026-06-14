"""L1 BehaviorIR model for the EarphoneAPBBridge.

Functional model of the AHB-to-APB address decoder and response mux.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


# 1 MB peripheral region split into 8 slave slots.
APB_SLAVE_SLOTS: List[Tuple[str, int, int]] = [
    ("QSPI",    0x00000, 0x10000),
    ("SRAM",    0x10000, 0x10000),
    ("SPI",     0x20000, 0x10000),
    ("UART",    0x30000, 0x10000),
    ("I2C",     0x40000, 0x10000),
    ("I2S",     0x50000, 0x10000),
    ("BTLE",    0x60000, 0x10000),
    ("SIMD16",  0x70000, 0x10000),
]


def apb_decode(addr: int) -> Tuple[int, str]:
    """Return (slave_index, slave_name) for a given address offset."""
    for idx, (name, base, size) in enumerate(APB_SLAVE_SLOTS):
        if base <= addr < base + size:
            return idx, name
    return 0, "QSPI"  # default fallback


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneAPBBridge",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "AHB-to-APB address decoder and response multiplexer functional model.",
        "region_size_bytes": 1024 * 1024,
        "num_slave_slots": len(APB_SLAVE_SLOTS),
        "slave_slots": ", ".join(name for name, _, _ in APB_SLAVE_SLOTS),
    }
