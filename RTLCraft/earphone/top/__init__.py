"""Top-level SoC contract package for the Earphone flow."""

from __future__ import annotations

from earphone.top.layer_L3_architecture.src.arch import TOP_ARCH, describe as describe_architecture
from earphone.top.layer_L4_structure.src.structure import TOP_STRUCTURE, describe as describe_structure

__all__ = ["TOP_ARCH", "TOP_STRUCTURE", "describe_architecture", "describe_structure"]
