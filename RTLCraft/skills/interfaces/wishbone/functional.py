"""
skills.interfaces.wishbone.functional — Functional Models (combinatorial, no timing)
"""
from __future__ import annotations
from typing import Any, Callable, Dict


def wb_mux_2_functional(**kwargs) -> Callable:
    """Functional Wb_Mux_2 model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def wb_reg_functional(**kwargs) -> Callable:
    """Functional Wb_Reg model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func

