"""L5 DSL module for the qspi module.

Currently a placeholder.  The real DSL class will be migrated from
earphone/design_earphone.py in a later phase.
"""

from __future__ import annotations


class QspiDSL:
    """Placeholder DSL class for qspi."""

    def __init__(self):
        self.name = "qspi"


def describe() -> dict:
    return {"name": "qspi", "layer": "L5_dsl", "status": "stub"}
