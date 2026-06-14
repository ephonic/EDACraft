"""L1 BehaviorIR model for the EarphoneSRAM256K memory.

Simple byte-addressable functional model of the 256 KB on-chip SRAM.
"""

from __future__ import annotations

from typing import Any, Dict


SRAM_SIZE_BYTES = 256 * 1024


class SRAM256KFunctional:
    """Functional model of 256 KB single-port SRAM."""

    def __init__(self):
        self.memory: Dict[int, int] = {i: 0 for i in range(SRAM_SIZE_BYTES)}

    def write(self, addr: int, data: int, mask: int = 0xF):
        """Word write with byte mask."""
        base = addr & (SRAM_SIZE_BYTES - 1)
        for i in range(4):
            if (mask >> i) & 1:
                self.memory[base + i] = (data >> (i * 8)) & 0xFF

    def read(self, addr: int) -> int:
        """Word read."""
        base = addr & (SRAM_SIZE_BYTES - 1)
        val = 0
        for i in range(4):
            val |= self.memory.get(base + i, 0) << (i * 8)
        return val


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneSRAM256K",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Byte-addressable functional model of the 256 KB on-chip SRAM.",
        "size_bytes": SRAM_SIZE_BYTES,
        "data_width": 32,
        "byte_mask": "4-bit write strobe",
    }
