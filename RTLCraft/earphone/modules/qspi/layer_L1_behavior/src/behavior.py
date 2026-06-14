"""L1 BehaviorIR model for the EarphoneQSPI controller.

This module models the external QSPI Flash and the memory-mapped XIP read
transaction semantics used by the Earphone SoC.
"""

from __future__ import annotations

from typing import Any, Dict


class QSPIFlashFunctional:
    """Functional model of external 32 MB QSPI Flash and controller transactions."""

    def __init__(self, size_bytes: int = 32 * 1024 * 1024):
        self.memory: Dict[int, int] = {i: 0 for i in range(size_bytes)}
        self.mode = 0  # 0=single, 1=dual, 2=quad

    def load_data(self, addr: int, data: bytes):
        for i, b in enumerate(data):
            self.memory[addr + i] = b & 0xFF

    def xip_read(self, addr: int, nbytes: int = 4) -> int:
        """Little-endian XIP read."""
        val = 0
        for i in range(nbytes):
            val |= self.memory.get(addr + i, 0) << (i * 8)
        return val


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneQSPI",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Functional model of 32 MB external QSPI Flash with memory-mapped XIP reads.",
        "flash_size_bytes": 32 * 1024 * 1024,
        "read_command": "0xEB (Fast Read Quad I/O)",
        "endianness": "Little-endian",
    }
