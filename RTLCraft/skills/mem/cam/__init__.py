"""
skills.mem.cam — CAM (Content Addressable Memory) Skill

Domain-specific skill for content addressable memory designs.
Based on Alex Forencich's verilog-cam.

Architecture:
  CAM #(CAM_STYLE)
    ├── CamSRL (SRL-based): shift-register LUT array, 4-state FSM
    └── CamBRAM (BRAM-based): dual-port RAM slices + erase RAM, 6-state FSM

Common sub-blocks:
  PriorityEncoder — recursive tree priority encoder
  RamDP — dual-port RAM with read-first behavior

Modules:
  - behaviors.py: 5 cycle-accurate behavior templates
  - models.py: CAMModel golden-reference simulator
  - arch_templates.py: build_cam_arch() for ProcessingElement + InterconnectSpec
  - skeleton_templates.py: DSL skeleton generation steps for 5 PE types
"""

# Register behaviors and skeleton steps at import time
import skills.mem.cam.behaviors  # noqa: F401
import skills.mem.cam.skeleton_templates  # noqa: F401

from skills.mem.cam.models import CAMModel
from skills.mem.cam.arch_templates import CAM_Model, build_cam_arch
from skills.mem.cam.behaviors import (
    priority_encoder_template,
    ram_dp_template,
    cam_srl_template,
    cam_bram_template,
    cam_top_template,
)

from skills.mem.cam.dsl_modules import (
    PriorityEncoder,
    RamDP,
    CamSRL,
    CamBRAM,
    CAM,
)

__all__ = [
    "PriorityEncoder", "RamDP", "CamSRL", "CamBRAM", "CAM",
    "CAMModel",
    "CAM_Model",
    "build_cam_arch",
    "priority_encoder_template",
    "ram_dp_template",
    "cam_srl_template",
    "cam_bram_template",
    "cam_top_template",
]
