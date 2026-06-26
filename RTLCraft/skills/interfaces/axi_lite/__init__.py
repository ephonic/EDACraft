"""
skills.interfaces.axi_lite — AXI-Lite RAM Skill

AXI-Lite slave RAM with word-level read/write access.

Architecture:
  AXIL_RAM — AXI-Lite slave RAM (AW/W/B write channel + AR/R read channel)

Modules:
  - behaviors.py: axil_ram_template
  - models.py: AXIL_RAM_Model golden simulator
  - arch_templates.py: build_axil_ram_arch() for ProcessingElement + ArchDefinition
  - skeleton_templates.py: DSL skeleton generation steps for axil_ram PE type
"""

# Register behaviors and skeleton steps at import time
import skills.interfaces.axi_lite.behaviors  # noqa: F401
import skills.interfaces.axi_lite.skeleton_templates  # noqa: F401

from skills.interfaces.axi_lite.models import AXIL_RAM_Model
from skills.interfaces.axi_lite.arch_templates import AXIL_RAM_Model as AXIL_RAM_ArchModel, build_axil_ram_arch
from skills.interfaces.axi_lite.behaviors import axil_ram_template

__all__ = [
    "AXIL_RAM_Model",
    "AXIL_RAM_ArchModel",
    "build_axil_ram_arch",
    "axil_ram_template",
]
