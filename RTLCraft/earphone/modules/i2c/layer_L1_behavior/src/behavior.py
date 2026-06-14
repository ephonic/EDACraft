"""L1 BehaviorIR model for the EarphoneI2C controller.

Functional model of I2C bus transactions used as the golden reference for
the APB I2C master byte controller.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class I2CBusFunctional:
    """Functional model of an I2C bus transaction."""

    def __init__(self):
        self.transactions: List[Tuple[int, List[int], bool]] = []  # addr, data, is_read

    def write(self, addr: int, data: List[int]):
        self.transactions.append((addr, data, False))

    def read(self, addr: int, nbytes: int) -> List[int]:
        data = [0] * nbytes
        self.transactions.append((addr, data, True))
        return data


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneI2C",
        "layer": "L1_behavior",
        "status": "implemented",
        "description": "Functional model of I2C bus transactions (7-bit address, single-byte reads/writes).",
        "address_width": 7,
        "data_width": 8,
    }
