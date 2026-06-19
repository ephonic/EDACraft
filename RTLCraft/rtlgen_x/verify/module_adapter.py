"""Normalize verification-facing modules onto the executable model."""

from __future__ import annotations

from typing import Any

from rtlgen_x.dsl import LoweredLegacyModule, lower_legacy_module_to_sim
from rtlgen_x.sim import SimModule


def normalize_executable_module(module: Any) -> SimModule:
    """Accept either a ``SimModule`` or a legacy DSL module and return ``SimModule``."""

    if isinstance(module, SimModule):
        return module
    if isinstance(module, LoweredLegacyModule):
        return module.module
    if hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks"):
        return lower_legacy_module_to_sim(module).module
    raise TypeError(f"unsupported executable module type: {type(module)!r}")
