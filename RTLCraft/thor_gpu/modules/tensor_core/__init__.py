"""ThorTensorCore module package.

Public API:
    - tc_mma_reference: L1 functional model.
"""

from __future__ import annotations

from thor_gpu.modules.tensor_core.layer_L1_behavior.src.behavior import tc_mma_reference

__all__ = ["tc_mma_reference"]
