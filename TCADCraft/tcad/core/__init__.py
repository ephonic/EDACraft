"""Core C++ solver bindings."""

from enum import IntEnum

try:
    from ._bindings import PyDeviceSimulator
except ImportError as exc:
    raise ImportError(
        "TCAD core extension not built. Run: python setup.py build_ext --inplace"
    ) from exc


class SolverType(IntEnum):
    """Linear solver backend selection. Must match src/linear_solver.h ordering."""
    BICGSTAB = 0
    BICGSTAB_ILU0 = 1
    GMRES = 2
    CG = 3
    JACOBI = 4
    GAUSS_SEIDEL = 5
    DENSE_DIRECT = 6
    PETSC = 7


__all__ = ["PyDeviceSimulator", "SolverType"]
