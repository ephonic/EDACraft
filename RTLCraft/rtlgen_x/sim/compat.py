"""Small compatibility shims between the legacy DSL simulator and the new runtime.

The legacy :class:`rtlgen_x.dsl.Simulator` drives a reset *sequence*
(``reset(rst=None, cycles=2)``: assert the reset port, step a few cycles, then
deassert), while the new :class:`rtlgen_x.sim.PythonSimulator` wipes state
directly with a no-arg ``reset()``. Test harnesses that want to work with
either frontend can use :func:`reset_simulator` to reset either one without
branching on the concrete class.
"""

from __future__ import annotations

import inspect
from typing import Optional


def reset_simulator(simulator, *, rst: Optional[str] = None, cycles: Optional[int] = None) -> None:
    """Reset either simulator frontend through a single entry point.

    - New-style simulators (e.g. :class:`PythonSimulator`, :class:`CompiledSimulator`)
      expose a no-argument ``reset()`` that reloads initial state; the ``rst``
      and ``cycles`` arguments are ignored for them.
    - Legacy :class:`~rtlgen_x.dsl.Simulator` exposes
      ``reset(rst=None, cycles=2)`` and drives the reset port for ``cycles``
      steps; the arguments are forwarded when provided.

    The dispatch is signature-based so this helper does not need to import the
    legacy simulator class (which may be unavailable in some deployments).
    """

    try:
        signature = inspect.signature(simulator.reset)
    except (TypeError, ValueError):
        signature = None

    accepts_args = False
    if signature is not None:
        params = signature.parameters
        # A no-arg reset() has no positional params beyond self. A legacy reset
        # accepts rst/cycles either by name or via *args.
        accepts_args = any(
            name in params
            for name in ("rst", "cycles")
        ) or any(
            p.kind is inspect.Parameter.VAR_POSITIONAL for p in params.values()
        )

    if accepts_args:
        kwargs = {}
        if rst is not None:
            kwargs["rst"] = rst
        if cycles is not None:
            kwargs["cycles"] = cycles
        simulator.reset(**kwargs)
    else:
        simulator.reset()
