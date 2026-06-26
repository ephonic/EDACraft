"""EarphoneSRAM256K module package.

Public API:
    - SRAM256KFunctional: L1 byte-addressable functional model.
"""

from __future__ import annotations

from earphone.modules.sram256k.layer_L1_behavior.src.behavior import SRAM256KFunctional

__all__ = ["SRAM256KFunctional"]
