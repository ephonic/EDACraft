"""L5 DSL module for the i2c module.

Currently a placeholder.  The real DSL class will be migrated from
earphone/design_earphone.py in a later phase.
"""

from __future__ import annotations


class I2cDSL:
    """Placeholder DSL class for i2c."""

    def __init__(self):
        self.name = "i2c"


def describe() -> dict:
    return {"name": "i2c", "layer": "L5_dsl", "status": "stub"}
