"""mom top-level package."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _load_extension():
    alt_pyd = os.environ.get("MOM_ALT_PYD")
    if alt_pyd:
        mod_name = f"{__name__}._mom"
        spec = importlib.util.spec_from_file_location(mod_name, str(Path(alt_pyd)))
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load extension module from {alt_pyd}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        return module

    from . import _mom as module

    return module


_mom = _load_extension()

__version__ = _mom.__version__
SweepScale = _mom.SweepScale
square_inplace = _mom.square_inplace
MicrostripConfig = _mom.MicrostripConfig
solve_microstrip = _mom.solve_microstrip
solve_microstrip_sweep = _mom.solve_microstrip_sweep

from .sweep import FreqSweep  # noqa: E402,F401
from .microstrip import Microstrip  # noqa: E402,F401
from .touchstone import write_touchstone, read_touchstone  # noqa: E402,F401
from .structure import Structure, RectangleConductor, Stackup  # noqa: E402,F401

__all__ = [
    "FreqSweep",
    "SweepScale",
    "square_inplace",
    "MicrostripConfig",
    "Microstrip",
    "solve_microstrip",
    "solve_microstrip_sweep",
    "write_touchstone",
    "read_touchstone",
    "Structure",
    "RectangleConductor",
    "Stackup",
    "__version__",
]
