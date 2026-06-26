"""
skills.interfaces.ethernet — Ethernet Skill

PTP (Precision Time Protocol) timestamp extraction from AXI-Stream tuser.

Architecture:
  PTP_TS_EXTRACT — Extract ts from tuser, valid on first beat of each frame

Modules:
  - behaviors.py: ptp_ts_extract_template
  - models.py: PTP_TS_Extract_Model
  - arch_templates.py: build_ethernet_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.ethernet.behaviors  # noqa: F401
import skills.interfaces.ethernet.skeleton_templates  # noqa: F401

from skills.interfaces.ethernet.models import PTP_TS_Extract_Model
from skills.interfaces.ethernet.arch_templates import Ethernet_TSModel, build_ethernet_arch
from skills.interfaces.ethernet.behaviors import ptp_ts_extract_template

__all__ = [
    "PTP_TS_Extract_Model", "Ethernet_TSModel", "build_ethernet_arch",
    "ptp_ts_extract_template",
]
