"""Small compatibility shims around reset-style differences.

`rtlgen_x` itself now standardizes on :class:`rtlgen_x.sim.PythonSimulator` and
`CompiledSimulator`, both of which expose a no-argument ``reset()``.

Some external or older-style simulators still use a reset *sequence*
(``reset(rst=None, cycles=2)``: assert the reset port, step a few cycles, then
deassert). Test harnesses that need to tolerate both styles can use
:func:`reset_simulator` without branching on the concrete class.
"""

from __future__ import annotations

import inspect
from typing import Optional


def reset_simulator(simulator, *, rst: Optional[str] = None, cycles: Optional[int] = None) -> None:
    """Reset either simulator frontend through a single entry point.

    - New-style simulators (e.g. :class:`PythonSimulator`, :class:`CompiledSimulator`)
      expose a no-argument ``reset()`` that reloads initial state; the ``rst``
      and ``cycles`` arguments are ignored for them.
    - Older-style simulators expose
      ``reset(rst=None, cycles=2)`` and drives the reset port for ``cycles``
      steps; the arguments are forwarded when provided.

    The dispatch is signature-based so this helper does not need to import the
    external simulator class (which may be unavailable in some deployments).
    """

    try:
        signature = inspect.signature(simulator.reset)
    except (TypeError, ValueError):
        signature = None

    accepts_args = False
    if signature is not None:
        params = signature.parameters
        # A no-arg reset() has no positional params beyond self. A older reset
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
