"""L1 BehaviorIR model for the fft256 module.

This module defines the cycle-unaware functional reference model.
It will be migrated from earphone/design_earphone.py in a later phase.
"""

from __future__ import annotations


MODULE_NAME = "fft256"


def describe() -> dict:
    """Return module metadata for document generation."""
    return {
        "name": MODULE_NAME,
        "layer": "L1_behavior",
        "status": "stub - implementation pending migration",
        "description": "Cycle-unaware functional model for fft256.",
    }
