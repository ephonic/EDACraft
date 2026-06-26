"""
skills.interfaces.uart — UART Skill

AXI-Stream UART with configurable data width and baud rate.

Architecture:
  UART (top wrapper)
    ├── UART_TX (transmitter: AXI-Stream → serial TxD)
    └── UART_RX (receiver: serial RxD → AXI-Stream)

Modules:
  - behaviors.py: uart_tx_template, uart_rx_template, uart_top_template
  - models.py: UART_TX_Model, UART_RX_Model golden simulators
  - arch_templates.py: build_uart_arch() for ProcessingElement + ArchDefinition
  - skeleton_templates.py: DSL skeleton generation steps for UART PE types
"""

# Register behaviors and skeleton steps at import time
import skills.interfaces.uart.behaviors  # noqa: F401
import skills.interfaces.uart.skeleton_templates  # noqa: F401

from skills.interfaces.uart.models import UART_TX_Model, UART_RX_Model
from skills.interfaces.uart.arch_templates import UART_ControllerModel, build_uart_arch
from skills.interfaces.uart.behaviors import (
    uart_tx_template,
    uart_rx_template,
    uart_top_template,
)

from skills.interfaces.uart.dsl_modules import (
    UART_TX,
    UART_RX,
    UART,
)

__all__ = [
    "UART_TX", "UART_RX", "UART",
    "UART_TX_Model",
    "UART_RX_Model",
    "UART_ControllerModel",
    "build_uart_arch",
    "uart_tx_template",
    "uart_rx_template",
    "uart_top_template",
]
