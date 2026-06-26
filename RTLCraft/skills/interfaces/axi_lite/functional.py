"""
skills.interfaces.axi_lite.functional — Functional Models (combinatorial, no timing)
"""
from __future__ import annotations
from typing import Any, Callable, Dict


def axil_ram_functional(**kwargs) -> Callable:
    """Functional Axil_Ram model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func

