"""
rtlgen.processor_models — Backward-compatible re-exports from skills.

Canonical implementations are now in:
  - skills.cpu.models: RV32ISS, RV32State, CPUModel, BehavioralModelFactory
  - skills.gpgpu.models: GPGPUModel, GPUWarp, GPUThread, GPUState
"""
from __future__ import annotations

from skills.cpu.models import RV32ISS, RV32State, CPUModel, BehavioralModelFactory
from skills.gpgpu.models import GPGPUModel, GPUState, GPUThread, GPUWarp

__all__ = [
    "RV32ISS", "RV32State", "CPUModel",
    "GPGPUModel", "GPUState", "GPUThread", "GPUWarp",
    "BehavioralModelFactory",
]
