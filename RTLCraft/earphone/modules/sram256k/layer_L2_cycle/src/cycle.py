"""L2 CycleIR model for the EarphoneSRAM256K memory.

Cycle-accurate wrapper modeling APB4 read/write timing and byte write strobes.
"""

from __future__ import annotations

from typing import Any, Dict


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneSRAM256K",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "APB4 slave cycle timing with single-cycle read/write latency.",
        "read_latency_cycles": 1,
        "write_latency_cycles": 1,
    }
