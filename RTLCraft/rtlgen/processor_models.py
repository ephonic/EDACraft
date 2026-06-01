"""
rtlgen.processor_models — Backward-compatible re-exports from skills.

Canonical implementations are now in:
  - skills.cpu.models: RV32ISS, RV32State, CPUModel, BehavioralModelFactory
  - skills.gpgpu.models: GPGPUModel, GPUWarp, GPUThread, GPUState
"""
from __future__ import annotations

# Lazy imports to avoid circular dependency at import time.
# rtlgen.__init__ imports from this module, which would otherwise
# trigger skills.cpu.models → rtlgen.core → rtlgen.__init__ cycle.

__all__ = [
    "RV32ISS", "RV32State", "CPUModel",
    "GPGPUModel", "GPUState", "GPUThread", "GPUWarp",
    "BehavioralModelFactory",
]


def __getattr__(name: str):
    if name in ("RV32ISS", "RV32State", "CPUModel", "BehavioralModelFactory"):
        from skills.cpu.models import RV32ISS, RV32State, CPUModel, BehavioralModelFactory
        return locals()[name]
    if name in ("GPGPUModel", "GPUState", "GPUThread", "GPUWarp"):
        from skills.gpgpu.models import GPGPUModel, GPUState, GPUThread, GPUWarp
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
