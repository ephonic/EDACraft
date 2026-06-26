"""Normalize verification-facing modules onto the executable model."""

from __future__ import annotations

from typing import Any

from rtlgen.dsl import LoweredDslModule, lower_dsl_module_to_sim
from rtlgen.sim import SimModule


def normalize_executable_module(module: Any, *, context: str) -> SimModule:
    """Accept a DSL module or lowered DSL module and return the executable model."""

    if isinstance(module, SimModule):
        raise TypeError(
            f"{context} is a DSL-facing API and does not accept raw SimModule. "
            "Pass a rtlgen.dsl.Module instance, or pass the LoweredDslModule returned by "
            "lower_dsl_module_to_sim(...), not lowered.module."
        )
    if isinstance(module, LoweredDslModule):
        return module.module
    if hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks"):
        return lower_dsl_module_to_sim(module).module
    raise TypeError(
        f"{context} expects a rtlgen.dsl.Module or LoweredDslModule; "
        f"got {type(module)!r}"
    )


def require_single_clock_module(module: SimModule, *, context: str) -> SimModule:
    """Raise a targeted error when one verification flow only supports single-clock modules."""

    if len(module.clock_domains) <= 1:
        return module
    domains = ", ".join(domain.name for domain in module.clock_domains)
    raise ValueError(
        f"{context} currently supports only single-clock executable models; "
        f"found multi-clock domains: {domains}. "
        "Use explicit simulator stepping via step_clocks(...) or emitted RTL plus an "
        "external simulator/UVM flow for multi-clock verification."
    )
