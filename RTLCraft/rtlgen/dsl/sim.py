"""Compatibility wrapper for the historical DSL simulator surface."""

from __future__ import annotations

from typing import Mapping, Optional

from rtlgen.dsl.adapter import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator


class Simulator:
    """Small wrapper exposing the old ``reset/poke/peek/step`` API.

    The maintained runtime is still ``rtlgen.sim.PythonSimulator``; this class
    only adapts legacy tests and seed flows onto that runtime.
    """

    def __init__(self, module):
        self.lowered = lower_dsl_module_to_sim(module)
        self._sim = PythonSimulator(self.lowered.module)
        self._inputs = {name: 0 for name in self._sim.input_names}
        self._last_outputs = {name: 0 for name in self._sim.output_names}

    def reset(self, rst: Optional[str] = None, cycles: int = 2, **kwargs) -> None:
        reset_name = rst or kwargs.get("reset") or kwargs.get("reset_name")
        self._sim.reset()
        if not reset_name:
            self._last_outputs = self._sim.step(self._inputs)
            return
        active_value = 0 if str(reset_name).endswith("_n") else 1
        inactive_value = 1 - active_value
        self._inputs[reset_name] = active_value
        for _ in range(cycles):
            self._last_outputs = self._sim.step(self._inputs)
        self._inputs[reset_name] = inactive_value
        self._last_outputs = self._sim.step(self._inputs)

    def poke(self, name: str, value: int) -> None:
        if name not in self._inputs:
            raise KeyError(f"unknown simulator input: {name}")
        self._inputs[name] = int(value)

    def peek(self, name: str) -> int:
        if name in self._last_outputs:
            return self._last_outputs[name]
        if name in self._inputs:
            return self._inputs[name]
        if name in getattr(self._sim, "_state", {}):
            return self._sim._state[name]
        raise KeyError(f"unknown simulator signal: {name}")

    def step(self, inputs: Optional[Mapping[str, int]] = None):
        if inputs:
            for name, value in inputs.items():
                self.poke(name, value)
        self._last_outputs = self._sim.step(self._inputs)
        return dict(self._last_outputs)


class SimValue:
    """Removed legacy 4-state value helper tied to the old AST simulator."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("SimValue is not available in the compatibility simulator")


__all__ = ["Simulator", "SimValue"]
