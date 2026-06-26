"""ThorLSU module package.

Public API:
    - lsu_functional: L1 functional model.
"""

from __future__ import annotations

from thor_gpu.modules.lsu.layer_L1_behavior.src.behavior import lsu_functional

__all__ = ["lsu_functional"]
