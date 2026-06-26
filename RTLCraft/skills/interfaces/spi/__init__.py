"""
skills.interfaces.spi — SPI Skill

SPI master/slave with full CPOL/CPHA support, configurable word length,
and MSB/LSB data order selection.

Architecture:
  SPI_TOP (top wrapper)
    ├── SPIClockDivider — free-running counter clock divider
    └── SPIModule — core SPI engine (2-state FSM, edge selection)

Modules:
  - behaviors.py: spi_clock_divider_template, spi_module_template, spi_top_template
  - models.py: SPIClockDividerModel, SPIModuleModel, SPITopModel golden simulators
  - arch_templates.py: build_spi_arch() for ProcessingElement + ArchDefinition
  - skeleton_templates.py: DSL skeleton generation steps for SPI PE types
"""

# Register behaviors and skeleton steps at import time
import skills.interfaces.spi.behaviors  # noqa: F401
import skills.interfaces.spi.skeleton_templates  # noqa: F401

from skills.interfaces.spi.models import (
    SPIClockDividerModel, SPIModuleModel, SPITopModel,
)
from skills.interfaces.spi.arch_templates import SPI_ControllerModel, build_spi_arch
from skills.interfaces.spi.behaviors import (
    spi_clock_divider_template,
    spi_module_template,
    spi_top_template,
)

from skills.interfaces.spi.dsl_modules import (
    PosEdgeDetector,
    NegEdgeDetector,
    SPIClockDivider,
    SPIModule,
    SPITop,
)

__all__ = [
    "PosEdgeDetector", "NegEdgeDetector",
    "SPIClockDivider", "SPIModule", "SPITop",
    "SPIClockDividerModel", "SPIModuleModel", "SPITopModel",
    "SPI_ControllerModel", "build_spi_arch",
    "spi_clock_divider_template", "spi_module_template", "spi_top_template",
]
