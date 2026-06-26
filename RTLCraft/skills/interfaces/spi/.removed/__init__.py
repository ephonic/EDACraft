"""
skills.interfaces.spi — SPI Controller Skill

APB-based SPI controller with Master/Slave dual-mode operation,
12-state FSM, CPOL/CPHA support, and programmable baud-rate divider.

Modules:
  - behaviors.py: Cycle-accurate behavior templates (registers, control FSM, TX, RX, sync)
  - models.py: SPI behavioral model (controller + FIFO)
  - arch_templates.py: Architecture template builder (build_spi_arch)
  - skeleton_templates.py: PE type → implementation steps
"""

# Import behaviors to register templates
import skills.interfaces.spi.behaviors  # noqa: F401

from skills.interfaces.spi.models import SPIControllerModel, SPIFIFOModel
from skills.interfaces.spi.arch_templates import SPI_ControllerModel, build_spi_arch
from skills.interfaces.spi.skeleton_templates import register_spi_skeleton_steps

from skills.interfaces.spi.dsl_modules import (
    SPIDataSync,
    SPIMuxWto1,
    SPIFIFO,
    SPIRegisters,
    SPIControl,
    SPISlaveSync,
    SPISlaveTX,
    SPIExtSync,
    SPITransmit,
    SPIReceive,
    SPIController,
)

__all__ = [
    "SPIDataSync", "SPIMuxWto1", "SPIFIFO", "SPIRegisters", "SPIControl", "SPISlaveSync", "SPISlaveTX", "SPIExtSync", "SPITransmit", "SPIReceive", "SPIController",
    "SPIControllerModel",
    "SPIFIFOModel",
    "SPI_ControllerModel",
    "build_spi_arch",
    "register_spi_skeleton_steps",
]
