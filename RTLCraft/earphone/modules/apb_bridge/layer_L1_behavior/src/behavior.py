"""L1 BehaviorIR model for the EarphoneAPBBridge.

Functional model of the AHB-to-APB address decoder and response mux.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


# APB peripheral region split into 8 slave slots.
# The L5 DSL selects the slot using m_paddr[29:22], which corresponds to
# 4 MB-aligned regions, so the L1 decoder uses the same 4 MB slot size.
SLOT_SIZE = 4 * 1024 * 1024
APB_SLAVE_SLOTS: List[Tuple[str, int, int]] = [
    ("QSPI",    0 * SLOT_SIZE, SLOT_SIZE),
    ("SRAM",    1 * SLOT_SIZE, SLOT_SIZE),
    ("SPI",     2 * SLOT_SIZE, SLOT_SIZE),
    ("UART",    3 * SLOT_SIZE, SLOT_SIZE),
    ("I2C",     4 * SLOT_SIZE, SLOT_SIZE),
    ("I2S",     5 * SLOT_SIZE, SLOT_SIZE),
    ("BTLE",    6 * SLOT_SIZE, SLOT_SIZE),
    ("SIMD16",  7 * SLOT_SIZE, SLOT_SIZE),
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
        "region_size_bytes": 8 * SLOT_SIZE,
        "num_slave_slots": len(APB_SLAVE_SLOTS),
        "slave_slots": ", ".join(name for name, _, _ in APB_SLAVE_SLOTS),
    }
