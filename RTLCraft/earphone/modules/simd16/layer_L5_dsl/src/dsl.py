"""L5 DSL module for the simd16 module.

Currently a placeholder.  The real DSL class will be migrated from
earphone/design_earphone.py in a later phase.
"""

from __future__ import annotations


class Simd16DSL:
    """Placeholder DSL class for simd16."""

    def __init__(self):
        self.name = "simd16"


def describe() -> dict:
    return {"name": "simd16", "layer": "L5_dsl", "status": "stub"}
