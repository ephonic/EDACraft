"""mom — 互连线 S 参数提取（MoM + 多层介质格林函数）。

顶层包：声明式 DSL（Stackup/Geometry/Port/Sweep）+ C++ 核心（_mom）。
设计详见 plan0627.md。
"""

from ._mom import (  # noqa: F401
    __version__,
    SweepScale,
    square_inplace,
    MicrostripConfig,
    solve_microstrip,
    solve_microstrip_sweep,
)
from .sweep import FreqSweep  # noqa: F401
from .microstrip import Microstrip  # noqa: F401
from .touchstone import write_touchstone, read_touchstone  # noqa: F401
from .structure import Structure, RectangleConductor, Stackup  # noqa: F401

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
