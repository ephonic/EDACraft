"""
skills.interfaces.wishbone — Wishbone Bus Skill

Wishbone bus register slice and 2-to-1 address-decode multiplexer.

Modules:
  - behaviors.py: wb_reg_template, wb_mux_2_template
  - models.py: WB_Reg_Model, WB_MUX_2_Model golden simulators
  - arch_templates.py: build_wishbone_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.wishbone.behaviors  # noqa: F401
import skills.interfaces.wishbone.skeleton_templates  # noqa: F401

from skills.interfaces.wishbone.models import WB_Reg_Model, WB_MUX_2_Model
from skills.interfaces.wishbone.arch_templates import Wishbone_BusModel, build_wishbone_arch
from skills.interfaces.wishbone.behaviors import wb_reg_template, wb_mux_2_template

from skills.interfaces.wishbone.dsl_modules import (
    WB_REG,
    WB_MUX_2,
)

__all__ = [
    "WB_REG", "WB_MUX_2",
    "WB_Reg_Model", "WB_MUX_2_Model",
    "Wishbone_BusModel", "build_wishbone_arch",
    "wb_reg_template", "wb_mux_2_template",
]
