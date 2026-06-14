"""EarphoneRV32 module package.

Public API:
    - RV32IM_ISS: L1 cycle-unaware instruction-set simulator.
    - EarphoneRV32: L5 DSL / Verilog-ready RV32IM core.
"""

from __future__ import annotations

from earphone.modules.rv32.layer_L1_behavior.src.behavior import RV32IM_ISS
from earphone.modules.rv32.layer_L5_dsl.src.dsl import EarphoneRV32

__all__ = ["RV32IM_ISS", "EarphoneRV32"]
