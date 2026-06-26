"""L2 CycleIR model for the EarphoneAPBBridge.

Cycle-accurate wrapper modeling AHB-to-APB address decode and response mux timing.
"""

from __future__ import annotations

from typing import Any, Dict


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneAPBBridge",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "AHB-to-APB bridge decode and response mux timing.",
        "decode_latency_cycles": 0,
        "num_slave_slots": 8,
    }
