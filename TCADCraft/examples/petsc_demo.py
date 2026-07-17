"""
PETSc solver demo for tcad.

Compares default dense-direct solver against PETSc (BiCGStab + ILU)
on a 1D NPN BJT equilibrium solve.

Usage:
    python examples/petsc_demo.py

To tune PETSc at runtime via command-line options:
    python examples/petsc_demo.py -ksp_type cg -pc_type hypre -pc_hypre_type boomeramg
"""

import numpy as np
import time
from tcad.core import PyDeviceSimulator, SolverType


def build_bjt_sim():
    """Create a 1D NPN BJT simulator (low-doping thin device)."""
    nx = 151
    dx = 1e-9  # 1 nm spacing
    sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)

    # Doping profile
    NdNa = np.zeros(nx)
    NdNa[:50] = 1e22      # Emitter: n-type
    NdNa[50:100] = -1e21  # Base: p-type
    NdNa[100:] = 1e20     # Collector: n-type
    sim.set_doping(NdNa)

    # Ground both ends
    sim.set_dirichlet_potential({0: 0.0, nx - 1: 0.0})
    sim.set_gummel_max_iter(100)
    return sim, nx


def main():
    # --- Default solver ---
    sim_default, nx = build_bjt_sim()
    t0 = time.perf_counter()
    res_default = sim_default.solve()
    t_default = time.perf_counter() - t0
    print(f"Default solver  : converged={res_default['converged']} "
          f"iters={res_default['iterations']} time={t_default:.3f}s")

    # --- PETSc solver ---
    sim_petsc, _ = build_bjt_sim()
    sim_petsc.set_poisson_solver_type(SolverType.PETSC)
    sim_petsc.set_continuity_solver_type(SolverType.PETSC)
    t0 = time.perf_counter()
    res_petsc = sim_petsc.solve()
    t_petsc = time.perf_counter() - t0
    print(f"PETSc solver    : converged={res_petsc['converged']} "
          f"iters={res_petsc['iterations']} time={t_petsc:.3f}s")

    # --- Accuracy comparison ---
    phi_diff = np.max(np.abs(res_default['phi'] - res_petsc['phi']))
    n_diff = np.max(np.abs(res_default['n'] - res_petsc['n']))
    p_diff = np.max(np.abs(res_default['p'] - res_petsc['p']))
    print(f"\nMax absolute difference:")
    print(f"  phi = {phi_diff:.3e} V")
    print(f"  n   = {n_diff:.3e} m^-3")
    print(f"  p   = {p_diff:.3e} m^-3")

    assert res_default['converged'] and res_petsc['converged']
    assert phi_diff < 1e-10
    assert n_diff < 1e10
    assert p_diff < 1e10
    print("\nPETSc integration test PASSED.")


if __name__ == "__main__":
    main()
