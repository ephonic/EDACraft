"""
skills.interfaces.spi.functional — Functional Models (combinatorial, no timing)
"""
from __future__ import annotations
from typing import Any, Callable, Dict


def neg_edge_detector_functional(**kwargs) -> Callable:
    """Functional Negedgedetector model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def pos_edge_detector_functional(**kwargs) -> Callable:
    """Functional Posedgedetector model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def spi_clock_divider_functional(**kwargs) -> Callable:
    """Functional Spiclockdivider model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def spi_module_functional(**kwargs) -> Callable:
    """Functional Spimodule model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def spi_top_functional(**kwargs) -> Callable:
    """Functional Spitop model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func

