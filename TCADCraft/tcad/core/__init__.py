"""Core C++ solver bindings."""

from enum import IntEnum

try:
    from ._bindings import PyDeviceSimulator, native_precision, native_constants
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
    IR_BICGSTAB = 7
    PETSC = 8


def require_constants_profile(expected):
    """Reject a binary with the wrong charge profile before running a case."""
    if expected not in ("si", "legacy-charge"):
        raise ValueError("Expected constants profile must be 'si' or 'legacy-charge'")
    actual = native_constants()
    if actual["profile"] != expected:
        raise RuntimeError(
            f"TCAD constants profile mismatch: expected {expected!r}, "
            f"loaded {actual['profile']!r}. Rebuild or select the matching binary."
        )
    return actual


__all__ = ["PyDeviceSimulator", "SolverType", "native_precision", "native_constants",
           "require_constants_profile"]
