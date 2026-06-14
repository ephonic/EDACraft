"""L5 DSL module for the sram256k module.

Currently a placeholder.  The real DSL class will be migrated from
earphone/design_earphone.py in a later phase.
"""

from __future__ import annotations


class Sram256kDSL:
    """Placeholder DSL class for sram256k."""

    def __init__(self):
        self.name = "sram256k"


def describe() -> dict:
    return {"name": "sram256k", "layer": "L5_dsl", "status": "stub"}
