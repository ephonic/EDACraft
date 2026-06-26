"""
skills.interfaces.axi — AXI Skill

Simplified AXI dual-port RAM with word-level access on both ports.

Architecture:
  AXI_DP_RAM_SIMPLE — Shared memory with dual AXI-Lite interfaces
  - Port A: independent write/read
  - Port B: independent write/read

Modules:
  - behaviors.py: axi_dp_ram_simple_template
  - models.py: AXI_DP_RAM_Simple_Model
  - arch_templates.py: build_axi_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.axi.behaviors  # noqa: F401
import skills.interfaces.axi.skeleton_templates  # noqa: F401

from skills.interfaces.axi.models import AXI_DP_RAM_Simple_Model
from skills.interfaces.axi.arch_templates import AXI_DP_RAM_Model, build_axi_arch
from skills.interfaces.axi.behaviors import axi_dp_ram_simple_template

from skills.interfaces.axi.dsl_modules import (
    AXIL_RAM,
    AXI_DP_RAM_SIMPLE,
)

__all__ = [
    "AXIL_RAM", "AXI_DP_RAM_SIMPLE",
    "AXI_DP_RAM_Simple_Model", "AXI_DP_RAM_Model", "build_axi_arch",
    "axi_dp_ram_simple_template",
]
