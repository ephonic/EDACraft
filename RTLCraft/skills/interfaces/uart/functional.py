"""
skills.interfaces.uart.functional — Functional Models (combinatorial, no timing)
"""
from __future__ import annotations
from typing import Any, Callable, Dict


def uart_functional(**kwargs) -> Callable:
    """Functional Uart model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def uart_rx_functional(**kwargs) -> Callable:
    """Functional Uart_Rx model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def uart_top_functional(**kwargs) -> Callable:
    """Functional Uart_Top model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func


def uart_tx_functional(**kwargs) -> Callable:
    """Functional Uart_Tx model."""
    def func(**inputs) -> Dict:
        """Functional behavior stub."""
        return {}
    return func

