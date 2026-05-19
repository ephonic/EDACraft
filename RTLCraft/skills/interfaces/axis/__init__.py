"""
skills.interfaces.axis — AXI-Stream Skill

AXI-Stream skid buffer register, width adapter, and broadcaster.

Architecture:
  AXIS_REGISTER — Skid buffer (REG_TYPE=2), bubble-free 1-cycle latency
  AXIS_ADAPTER — Width up-size (narrow→wide), segment collection
  AXIS_BROADCAST — 1-to-M fanout with per-output back-pressure

Modules:
  - behaviors.py: axis_register_template, axis_adapter_template, axis_broadcast_template
  - models.py: AXIS_Register_Model, AXIS_Adapter_Model
  - arch_templates.py: build_axis_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.axis.behaviors  # noqa: F401
import skills.interfaces.axis.skeleton_templates  # noqa: F401

from skills.interfaces.axis.models import AXIS_Register_Model, AXIS_Adapter_Model
from skills.interfaces.axis.arch_templates import AXIS_StreamModel, build_axis_arch
from skills.interfaces.axis.behaviors import (
    axis_register_template,
    axis_adapter_template,
    axis_broadcast_template,
)

from skills.interfaces.axis.dsl_modules import (
    AXIS_REGISTER,
    AXIS_ADAPTER,
    AXIS_BROADCAST,
)

__all__ = [
    "AXIS_REGISTER", "AXIS_ADAPTER", "AXIS_BROADCAST",
    "AXIS_Register_Model", "AXIS_Adapter_Model",
    "AXIS_StreamModel", "build_axis_arch",
    "axis_register_template", "axis_adapter_template", "axis_broadcast_template",
]
