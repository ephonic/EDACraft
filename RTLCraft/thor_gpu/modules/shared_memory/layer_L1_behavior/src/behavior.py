"""L1 BehaviorIR model for the ThorSharedMemory.

Cycle-unaware functional reference for the per-SM shared SRAM. Single-port,
256-bit word (one vector register), 12-bit address (4096 words). Write has
priority over read in the same cycle.
"""

from __future__ import annotations

from typing import Any, Dict


def shmem_read(mem: Dict[int, int], addr: int) -> int:
    """Read one 256-bit word from the shared memory model."""
    return mem.get(addr & 0xFFF, 0)


def shmem_write(mem: Dict[int, int], addr: int, data: int) -> None:
    """Write one 256-bit word into the shared memory model."""
    mem[addr & 0xFFF] = data & ((1 << 256) - 1)


def shmem_functional(mem: Dict[int, int], we: int, re: int, addr: int,
                     wdata: int) -> Dict[str, int]:
    """One access. Write takes priority; returns read data (0 on pure write)."""
    addr &= 0xFFF
    if we:
        mem[addr] = wdata & ((1 << 256) - 1)
    rdata = mem.get(addr, 0) if re else 0
    return {"rdata": rdata}


def describe() -> Dict[str, Any]:
    return {
        "name": "ThorSharedMemory",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Per-SM shared SRAM functional model (256-bit word, 4096 deep).",
        "word_width": 256,
        "addr_width": 12,
        "depth": 4096,
        "ports": 1,
    }


__all__ = ["shmem_read", "shmem_write", "shmem_functional", "describe"]
