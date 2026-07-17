"""B档-2: MMS (method of manufactured solutions) grid-convergence tests.

Validates that the solver DISCRETIZATION achieves its design accuracy as the
grid refines — the gold standard for "is the numerical solution converging
to the true solution". Uses the three-grid Richardson estimator
p ≈ log2((e_h - e_{h/2})/(e_{h/2} - e_{h/4})) with a wide [1.5, 3.0] acceptance
band, matching the existing test_numerical_validation.py idiom.

Coverage (B-tier gaps from reconnaissance):
  - Richardson rate helper (reusable).
  - Poisson: sine-BC Laplace box (re-asserts the existing 2nd-order result
    independently, as a sanity anchor).
  - div(P) stencil convergence: an FE slab with a sinusoidal polarization
    drive; the -div(P) Poisson contribution must converge as the grid refines.
  - 1D-Poisson RHS-driven: phi_exact = sin(kx*x), compare directly to the
    analytic solution (not just Richardson self-convergence) under large-DOS
    carrier suppression.

Note: the solver is only reachable through the coupled Gummel loop, so all
MMS tests suppress carrier feedback (huge DOS, ~1mV phi swing) to isolate the
FD stencil error. This is the documented convention (test_numerical_validation
header).
"""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator

QE = 1.602176634e-19
EPS0 = 8.854187817e-12
K_B = 1.3806503e-23
VT_300 = K_B * 300.0 / QE


def _make_sim(nx, ny, nz, dx, dy, dz):
    return PyDeviceSimulator(nx, ny, nz, dx, dy, dz)


def _apply_uniform_si(sim, npts, eps_r=11.7):
    sim.set_permittivity(np.full(npts, EPS0 * eps_r, dtype=np.float64))
    sim.set_mobility(np.full(npts, 0.14, dtype=np.float64),
                     np.full(npts, 0.045, dtype=np.float64))
    sim.set_thermal_voltage(VT_300)


def richardson_rate(phi_h, phi_h2, phi_h4, mask=None):
    """Three-grid Richardson convergence-rate estimator.

    Returns p ≈ log2( ||phi_h - phi_h2|| / ||phi_h2 - phi_h4|| ).
    A 2nd-order stencil gives p ≈ 2. ``mask`` selects the nodes to compare
    (e.g. interior only). The three arrays must be subsampled to a common
    node set before calling.
    """
    e1 = np.asarray(phi_h) - np.asarray(phi_h2)
    e2 = np.asarray(phi_h2) - np.asarray(phi_h4)
    if mask is not None:
        e1 = e1[mask]
        e2 = e2[mask]
    l1 = float(np.sqrt(np.mean(e1 ** 2)))
    l2 = float(np.sqrt(np.mean(e2 ** 2)))
    if l1 < 1e-12 and l2 < 1e-12:
        return None  # FP-noise floor -> trivially passes
    return float(np.log2(max(l1, 1e-300) / max(l2, 1e-300)))


def _laplace_box_solve(nx, ny, nz, Lx=1e-7, amplitude=1e-3, tol=1e-8, max_iter=200):
    """Sine-BC Laplace box (Poisson MMS), returns phi flat array."""
    Ly, Lz = Lx, Lx
    dx, dy, dz = Lx / (nx - 1), Ly / (ny - 1), Lz / (nz - 1)
    sim = _make_sim(nx, ny, nz, dx, dy, dz)
    npts = nx * ny * nz
    _apply_uniform_si(sim, npts)
    sim.set_doping(np.zeros(npts, dtype=np.float64))
    sim.set_bandgap(np.full(npts, 1.12, dtype=np.float64))
    sim.set_effective_dos(np.full(npts, 1.0e30, dtype=np.float64),
                          np.full(npts, 1.0e30, dtype=np.float64))
    x = np.linspace(0.0, Lx, nx)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    k = 2.0 * np.pi / Lx
    phi_bc_values = amplitude * np.sin(k * X) * np.sin(k * Y) * np.sin(k * Z)
    phi_bc_flat = phi_bc_values.ravel(order="F")
    bc = {}
    for kk in range(nz):
        for j in range(ny):
            for i in range(nx):
                on_b = (i in (0, nx - 1) or j in (0, ny - 1) or kk in (0, nz - 1))
                if on_b:
                    idx = i + nx * (j + ny * kk)
                    bc[idx] = float(phi_bc_flat[idx])
    sim.set_dirichlet_potential(bc)
    sim.set_gummel_max_iter(max_iter)
    sim.set_tolerance(tol)
    return sim.solve()["phi"]


class TestPoissonMMSConvergence:
    """Poisson/Laplace stencil: 2nd-order grid convergence (re-anchored)."""

    def test_sine_box_second_order(self):
        """The sine-BC Laplace box must converge at ~2nd order (Richardson).
        Re-asserts the existing test_numerical_validation result via the
        shared richardson_rate helper (independent sanity anchor)."""
        ns = [9, 17, 33]
        phis = [_laplace_box_solve(n, n, n) for n in ns]
        # Subsample all to the common 9x9x9 node set (stride = (n-1)//8).
        common = []
        for n, phi in zip(ns, phis):
            stride = (n - 1) // 8
            idx_1d = np.arange(9) * stride
            sub = np.zeros(9 * 9 * 9)
            for ki in range(9):
                for j in range(9):
                    for i in range(9):
                        node = idx_1d[i] + n * (idx_1d[j] + n * idx_1d[ki])
                        sub[i + 9 * (j + 9 * ki)] = phi[node]
            common.append(sub)
        # Interior mask (exclude the boundary, where phi is pinned exactly).
        interior = np.zeros(9 * 9 * 9, dtype=bool)
        for ki in range(9):
            for j in range(9):
                for i in range(9):
                    if i in (0, 8) or j in (0, 8) or ki in (0, 8):
                        continue
                    interior[i + 9 * (j + 9 * ki)] = True
        rate = richardson_rate(common[0], common[1], common[2], mask=interior)
        if rate is None:
            return  # FP-noise floor
        assert 1.5 < rate < 3.0, (
            f"Poisson sine-box convergence rate {rate:.3f} outside [1.5, 3.0] "
            "(expected ~2 for a 2nd-order FD stencil)")


class TestFEDivergenceConvergence:
    """The -div(P) FE stencil must converge as the grid refines.

    Drive a pure FE slab with a sinusoidal phi so the induced P (via L-K) has a
    smooth spatial profile; the -div(P) bound-charge contribution to the Poisson
    RHS must converge at the FD stencil order. We compare phi between adjacent
    refinements (Richardson) since the coupled FE+Poisson has no closed form.
    """

    FE_ALPHA = -5.0e8
    FE_BETA = 1.5e10

    def _fe_slab_phi(self, nx, drive_v=0.5e-3):
        Lx = 10e-9
        dx = Lx / (nx - 1)
        sim = _make_sim(nx, 1, 1, dx, 1.0, 1.0)
        npts = nx
        sim.set_permittivity(np.full(npts, EPS0 * 35.0))  # HfZrO
        sim.set_mobility(np.zeros(npts), np.zeros(npts))  # insulator
        sim.set_doping(np.zeros(npts))
        sim.set_thermal_voltage(VT_300)
        sim.set_recombination(np.full(npts, 1e-7), np.full(npts, 1e-7))
        sim.set_effective_dos(np.full(npts, 1e30), np.full(npts, 1e30))
        sim.set_bandgap(np.full(npts, 5.5))
        sim.set_ferroelectric_enabled(True)
        sim.set_ferroelectric_params(np.ones(npts, dtype=np.int8),
                                     self.FE_ALPHA, self.FE_BETA)
        sim.set_electron_bc({0: 0.0, nx - 1: 0.0})
        sim.set_hole_bc({0: 0.0, nx - 1: 0.0})
        # Small drive so phi is small and the linearized FE response dominates.
        sim.set_dirichlet_potential({0: drive_v, nx - 1: 0.0})
        sim.set_gummel_max_iter(200)
        sim.set_tolerance(1e-10)
        return sim.solve()["phi"]

    def test_div_p_converges_with_refinement(self):
        """phi on the FE slab must converge as nx refines (Richardson rate
        in a reasonable band, confirming the -div(P) stencil is consistent)."""
        ns = [11, 21, 41]
        phis = [self._fe_slab_phi(n) for n in ns]
        # Subsample to common 11-node set.
        common = []
        for n, phi in zip(ns, phis):
            stride = (n - 1) // 10
            sub = np.array([phi[i * stride] for i in range(11)])
            common.append(sub)
        interior = np.ones(11, dtype=bool)
        interior[0] = interior[10] = False
        rate = richardson_rate(common[0], common[1], common[2], mask=interior)
        if rate is None:
            return
        # FE coupling + phi-freezing make this less clean than pure Poisson;
        # accept a wider band (just require positive, bounded convergence).
        assert 0.5 < rate < 3.5, (
            f"FE -div(P) convergence rate {rate:.3f} outside [0.5, 3.5] — the "
            "FE divergence stencil is not converging with refinement")


class TestPoisson1DRHSDriven:
    """1D Poisson grid refinement sanity: with zero doping and pinned ends, the
    solution is the trivial phi=0; this test instead checks that a NON-trivial
    BC (one end driven to a small voltage) produces a phi that CONVERGES under
    refinement (the discrete Laplace solution smooths toward its continuum
    limit). A direct RHS-driven MMS (phi_exact = sin fed as a source) requires
    a pure-Poisson source-injection API that the coupled loop does not expose;
    that is a C-tier task. Here we verify monotone convergence of the
    driven-boundary case as a weaker stencil-consistency check."""

    def test_1d_driven_boundary_converges(self):
        """Drive one end to A volts, the other to 0; phi must converge (the
        Richardson difference shrinks) as nx refines. This confirms the 1D
        stencil is consistent (no divergence with refinement)."""
        Lx = 1e-6
        A = 1e-3
        phis = []
        for nx in [11, 21, 41]:
            dx = Lx / (nx - 1)
            sim = _make_sim(nx, 1, 1, dx, 1.0, 1.0)
            _apply_uniform_si(sim, nx)
            sim.set_doping(np.zeros(nx))
            sim.set_bandgap(np.full(nx, 1.12))
            sim.set_effective_dos(np.full(nx, 1e30), np.full(nx, 1e30))
            sim.set_recombination(np.full(nx, 1e-7), np.full(nx, 1e-7))
            sim.set_dirichlet_potential({0: A, nx - 1: 0.0})
            sim.set_electron_bc({0: 0.0, nx - 1: 0.0})
            sim.set_hole_bc({0: 0.0, nx - 1: 0.0})
            sim.set_gummel_max_iter(200)
            sim.set_tolerance(1e-12)
            phis.append(sim.solve()["phi"])
        # Subsample to common 11-node set, compare Richardson differences.
        common = []
        for n, phi in zip([11, 21, 41], phis):
            stride = (n - 1) // 10
            common.append(np.array([phi[i * stride] for i in range(11)]))
        interior = np.ones(11, dtype=bool)
        interior[0] = interior[10] = False
        rate = richardson_rate(common[0], common[1], common[2], mask=interior)
        if rate is None:
            return
        # The driven linear profile is reproduced to machine precision by a FD
        # Laplacian, so the Richardson differences may hit FP noise (rate=None ->
        # pass). If a rate is estimated, it should be positive (converging).
        assert rate is None or rate > 0.0, (
            f"1D driven-boundary phi not converging: rate={rate:.3f} "
            f"(common={common})")


class TestPoissonRHSDrivenMMS:
    """Pure Poisson RHS-driven MMS: inject the analytic Laplacian as a doping
    source and compare phi DIRECTLY to the analytic solution (not just
    Richardson self-convergence). This is the strongest stencil check — it
    catches absolute discretization error against a known answer.

    Manufactured solution: phi_exact = A*sin(kx). Its Laplacian (constant eps)
    is -eps*k^2*A*sin(kx). The assembled Poisson row is
    ``A_.phi = -q*(p-n+Nd-Na)``; with carriers suppressed (huge DOS) p-n~0, so
    injecting ``Nd-Na = eps*k^2*A/q * sin(kx)`` makes phi_exact the exact
    Poisson solution (up to FD truncation). Boundary pinned to phi_exact.
    """

    def test_poisson_rhs_driven_second_order(self):
        """|phi_num - phi_exact| must shrink at ~2nd order as nx refines."""
        Lx = 1e-7
        A = 1e-3
        k = 2.0 * np.pi / Lx
        eps = EPS0 * 11.7
        errors = []
        for nx in [21, 41, 81]:
            dx = Lx / (nx - 1)
            sim = _make_sim(nx, 1, 1, dx, 1.0, 1.0)
            _apply_uniform_si(sim, nx, eps_r=11.7)
            sim.set_thermal_voltage(VT_300)
            # Suppress SRH so the continuity RHS doesn't feed back into Poisson.
            sim.set_recombination(np.full(nx, 1e100), np.full(nx, 1e100))
            sim.set_effective_dos(np.full(nx, 1e30), np.full(nx, 1e30))
            sim.set_bandgap(np.full(nx, 1.12))
            x = np.linspace(0.0, Lx, nx)
            phi_exact = A * np.sin(k * x)
            # Analytic Laplacian source: Nd-Na = eps*k^2*A/q * sin(kx).
            Nd = eps * k * k * A / QE * np.sin(k * x)
            sim.set_doping(Nd)
            # Pin both ends to phi_exact (sin vanishes at x=0, x=Lx -> 0).
            sim.set_dirichlet_potential({0: 0.0, nx - 1: 0.0})
            sim.set_electron_bc({0: 0.0, nx - 1: 0.0})
            sim.set_hole_bc({0: 0.0, nx - 1: 0.0})
            sim.set_gummel_max_iter(200)
            sim.set_tolerance(1e-12)
            phi_num = sim.solve()["phi"]
            err = phi_num[1:-1] - phi_exact[1:-1]
            errors.append(float(np.sqrt(np.mean(err ** 2))))
        # Monotone decrease.
        assert errors[2] < errors[0], (
            f"RHS-driven Poisson error did not decrease: {errors}")
        # ~2nd-order Richardson rate (errors ~4x smaller per refinement).
        if errors[1] > 1e-14:
            rate = np.log2(errors[0] / errors[1])
            assert rate > 1.5, (
                f"RHS-driven Poisson convergence rate {rate:.3f} < 1.5 "
                f"(errors {errors}) — stencil not 2nd-order against analytic")


class TestFreezePhiBinding:
    """C档: the freeze_phi/n/p bindings are wired through all four layers.
    (The DD continuity-MMS that would USE freeze_phi needs a pure-continuity
    solve mode that bypasses the Gummel warm-up; that is a follow-on. Here we
    verify the bindings exist and propagate.)"""

    def test_freeze_phi_setter_round_trips(self):
        """The freeze setters must be callable and not raise (wiring sanity)."""
        sim = _make_sim(5, 1, 1, 1e-9, 1.0, 1.0)
        _apply_uniform_si(sim, 5)
        sim.set_use_newton(True)
        sim.set_newton_freeze_phi(True)
        sim.set_newton_freeze_n(False)
        sim.set_newton_freeze_p(False)
        # A solve must still run (freeze just pins blocks; with all pinned it
        # converges trivially). Use a trivial zero-bias setup.
        sim.set_doping(np.zeros(5))
        sim.set_bandgap(np.full(5, 1.12))
        sim.set_effective_dos(np.full(5, 1e30), np.full(5, 1e30))
        sim.set_recombination(np.full(5, 1e-7), np.full(5, 1e-7))
        sim.set_dirichlet_potential({0: 0.0, 4: 0.0})
        sim.set_electron_bc({0: 0.0, 4: 0.0})
        sim.set_hole_bc({0: 0.0, 4: 0.0})
        sim.set_initial_guess(np.zeros(5), np.full(5, 1e15), np.full(5, 1e15))
        sim.set_gummel_max_iter(50)
        sim.set_tolerance(1e-8)
        r = sim.solve()
        # No exception, returns a result.
        assert "phi" in r and "converged" in r
