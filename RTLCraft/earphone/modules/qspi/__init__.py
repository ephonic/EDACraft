"""EarphoneQSPI module package.

Public API:
    - QSPIFlashFunctional: L1 external Flash / XIP read model.
"""

from __future__ import annotations

from earphone.modules.qspi.layer_L1_behavior.src.behavior import QSPIFlashFunctional

__all__ = ["QSPIFlashFunctional"]
