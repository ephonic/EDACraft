"""
skills.interfaces.pcie — PCIe Skill

PCIe pulse merge counter and P-Tile flow control counter.

Architecture:
  PULSE_MERGE — Accumulates input pulses, outputs pulse while count>0
  PCIE_PTILE_FC_COUNTER — Credit tracking with saturating arithmetic

Modules:
  - behaviors.py: pulse_merge_template, pcie_ptile_fc_template
  - models.py: Pulse_Merge_Model, PCIe_PTile_FC_Model
  - arch_templates.py: build_pcie_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.pcie.behaviors  # noqa: F401
import skills.interfaces.pcie.skeleton_templates  # noqa: F401

from skills.interfaces.pcie.models import Pulse_Merge_Model, PCIe_PTile_FC_Model
from skills.interfaces.pcie.arch_templates import PCIe_Model, build_pcie_arch
from skills.interfaces.pcie.behaviors import pulse_merge_template, pcie_ptile_fc_template

from skills.interfaces.pcie.dsl_modules import (
    PULSE_MERGE,
    PCIE_PTILE_FC_COUNTER,
    PTP_TS_EXTRACT,
)

__all__ = [
    "PULSE_MERGE", "PCIE_PTILE_FC_COUNTER", "PTP_TS_EXTRACT",
    "Pulse_Merge_Model", "PCIe_PTile_FC_Model",
    "PCIe_Model", "build_pcie_arch",
    "pulse_merge_template", "pcie_ptile_fc_template",
]
