"""Shared removal notices for historical AST/JIT simulation surfaces."""

from __future__ import annotations


DSL_SIM_REMOVED_MESSAGE = (
    "rtlgen no longer supports the historical AST/JIT simulator surface. "
    "Lower the DSL module with lower_dsl_module_to_sim(...) and use "
    "rtlgen.sim.PythonSimulator or rtlgen.dsl.build_compiled_simulator_from_dsl(...)."
)


class DslSimulationRemovedError(RuntimeError):
    """Raised when callers try to use removed historical simulation surfaces."""


def raise_dsl_sim_removed() -> "None":
    raise DslSimulationRemovedError(DSL_SIM_REMOVED_MESSAGE)
