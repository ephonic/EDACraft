"""
skills.mem.ddr3 — DDR3 Controller Skill

Domain-specific skill for DDR3 memory controller designs.
Uses the Spec2RTL flow with MemoryModel and MemoryControllerSpec.

Architecture:
  DDR3Controller (top wrapper)
    └── DDR3Core (core FSM: INIT/IDLE/ACT/READ/WRITE/PRE/REF)
          ├── DDR3DFISeq (DFI sequencer: timing + data serialization)
          └── DDR3FIFO × 2 (ID tracking + write data buffer)

Modules:
  - behaviors.py: 2 behavior templates (memory_controller, dfi_sequencer)
  - models.py: DDR3CoreModel, DDR3DFISeqModel, DDR3Model golden-reference simulators
  - arch_templates.py: build_ddr3_arch() for ProcessingElement + InterconnectSpec
  - skeleton_templates.py: DSL skeleton generation steps for DDR3 PE types
  - ddr3_controller.py: Full Spec2RTL flow script (Phase 0-5)
"""

# Register behaviors and skeleton steps at import time
import skills.mem.ddr3.behaviors  # noqa: F401
import skills.mem.ddr3.skeleton_templates  # noqa: F401

from skills.mem.ddr3.models import DDR3CoreModel, DDR3DFISeqModel, DDR3Model
from skills.mem.ddr3.arch_templates import DDR3_Model, build_ddr3_arch
from skills.mem.ddr3.behaviors import (
    memory_controller_template,
    dfi_sequencer_template,
)

from skills.mem.ddr3.dsl_modules import (
    DDR3FIFO,
    DDR3DFISeq,
    DDR3Core,
    DDR3Controller,
)

__all__ = [
    "DDR3FIFO", "DDR3DFISeq", "DDR3Core", "DDR3Controller",
    "DDR3CoreModel",
    "DDR3DFISeqModel",
    "DDR3Model",
    "DDR3_Model",
    "build_ddr3_arch",
    "memory_controller_template",
    "dfi_sequencer_template",
]
