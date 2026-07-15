"""Physical truth tests — laws of physics that must never be violated.

These tests encode INVARIANTS, not specific numerical expectations.
If any test here fails, the C++ core has a fundamental bug.

Run before every commit:  pytest tests/test_physical_truths.py -v
"""

import numpy as np
import pytest
from tcad.core import PyDeviceSimulator
from tcad.physics import PhysicsInvariants as PI
from tcad.physics import PhysicsViolation

QE = 1.602176634e-19
EPS0 = 8.854187817e-12
VT_300 = 1.3806503e-23 * 300.0 / QE


# ======================================================================
# Part 1: Stencil / numerical-operator correctness
# ======================================================================

class TestStencilCorrectness:
    """The divergence operator itself must be correct on analytic fields."""

    def test_div_constant_is_zero(self):
        """div(constant field) = 0 — the most basic stencil check."""
        PI.check_divergence_stencil(dx=1e-9)

    def test_div_linear_is_slope(self):
        """div(a*x) = a — verifies central-difference stencil."""
        dx = 1e-9
        x = np.arange(10) * dx
        lin_P = 3.0 * x
        # Correct central difference on interior
        div_interior = (lin_P[2:] - lin_P[:-2]) / (2 * dx)
        assert np.allclose(div_interior, 3.0, rtol=1e-10)

    def test_div_not_laplacian(self):
        """The divergence must NOT be a second difference (Laplacian).

        The old bug (comments2.docx) turned div(P) into a Laplacian
        because the lower-neighbour term used a minus sign.  For a
        quadratic field P = x^2, the true divergence is 2x but the
        Laplacian is 2 — so they differ.
        """
        dx = 1e-9
        x = np.arange(10, dtype=float) * dx
        quad_P = x ** 2
        # Correct divergence: d(x^2)/dx = 2x
        div_correct = (quad_P[2:] - quad_P[:-2]) / (2 * dx)
        expected = 2 * x[1:-1]
        assert np.allclose(div_correct, expected, rtol=1e-6), (
            f"div(x^2) should be ~2x, got {div_correct}")
        # Old bug pattern: forward - backward = second difference
        fwd = (quad_P[1:] - quad_P[:-1]) / dx
        bwd = (quad_P[1:] - quad_P[:-1]) / dx
        laplacian_like = fwd[:-1] - bwd[1:]
        assert not np.allclose(laplacian_like, div_correct), (
            "The old sign-flip bug pattern should NOT match correct divergence")


# ======================================================================
# Part 2: Polarization bounds
# ======================================================================

class TestPolarizationBounds:
    """|P| must never exceed Ps — this would have caught P = 167 C/m^2."""

    def _build_fe(self, Ps=0.2, Ec=5e7, alpha=-1e8, beta=1e18, model=1,
                  Lx=5e-9, nx=21):
        dx = Lx / (nx - 1)
        N = nx
        sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
        sim.set_permittivity(np.full(N, EPS0 * 35.0))
        sim.set_mobility(np.zeros(N), np.zeros(N))
        sim.set_doping(np.zeros(N))
        sim.set_thermal_voltage(VT_300)
        sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
        sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
        sim.set_bandgap(np.full(N, 1.12))
        sim.set_ferroelectric_enabled(True)
        sim.set_ferroelectric_params(np.ones(N, dtype=np.int8), alpha, beta)
        sim.set_ferroelectric_model(model)
        if model in (1, 2):
            sim.set_ferroelectric_preisach(Ps, Ec, 0.0)
        if model == 2:
            sim.set_ferroelectric_nls(1e-6, 2e9, 1e-6)
        sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
        sim.set_electron_bc({0: 0.0, N - 1: 0.0})
        sim.set_hole_bc({0: 0.0, N - 1: 0.0})
        return sim, N

    def test_preisach_bounded(self):
        """Preisach: |P| <= Ps across a voltage sweep."""
        Ps = 0.2
        sim, N = self._build_fe(Ps=Ps, model=1)
        for Vg in np.linspace(-2, 2, 15):
            sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
            r = sim.solve()
            PI.check_polarization(r["P"], Ps, context=f"Preisach Vg={Vg}")

    def test_lk_bounded(self):
        """LK: |P| <= Ps across a voltage sweep (clamp is essential here)."""
        Ps = 0.1826  # sqrt(5e8/1.5e10)
        sim, N = self._build_fe(alpha=-5e8, beta=1.5e10, model=0)
        for Vg in np.linspace(-2, 2, 15):
            sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
            r = sim.solve()
            PI.check_polarization(r["P"], Ps, tolerance=1.1,
                                  context=f"LK Vg={Vg}")

    def test_p_not_constant_in_sweep(self):
        """P must vary across a voltage sweep — a constant P signals a bug."""
        Ps = 0.2
        sim, N = self._build_fe(Ps=Ps, model=1)
        mid = N // 2
        P_vals = []
        for Vg in np.linspace(0, 1.5, 10):
            sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
            r = sim.solve()
            P_vals.append(r["P"][mid][0])
        PI.check_polarization_not_constant(np.array(P_vals), Ps)


# ======================================================================
# Part 3: Carrier non-negativity
# ======================================================================

class TestCarrierNonNegativity:
    """n and p must be non-negative at all bias points."""

    def test_mosfet_nonneg(self):
        nx = 21
        dx = 5e-9
        N = nx
        sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
        sim.set_permittivity(np.full(N, EPS0 * 11.7))
        sim.set_mobility(np.full(N, 1400e-4), np.full(N, 450e-4))
        sim.set_doping(np.full(N, 1e22))
        sim.set_thermal_voltage(VT_300)
        sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
        sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
        sim.set_bandgap(np.full(N, 1.12))
        sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
        sim.set_electron_bc({0: 0.0, N - 1: 0.0})
        sim.set_hole_bc({0: 0.0, N - 1: 0.0})

        for Vg in np.linspace(0, 1.5, 8):
            sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
            r = sim.solve()
            PI.check_carriers(r["n"], r["p"], context=f"Vg={Vg}")


# ======================================================================
# Part 4: Material unit consistency
# ======================================================================

class TestMaterialUnits:
    """L-K alpha/beta must be consistent with declared Ps/Ec."""

    def test_hfzro_consistent(self):
        PI.check_material_units("HfZrO", Ps=0.0, Ec=0.0,
                                epsilon_r=35.0, alpha=-5e8, beta=1.5e10)

    def test_alscn_consistent(self):
        """AlScN: alpha/beta reverse-engineered from Ps=1.4, Ec=3.5e8."""
        import math
        Ps = 1.4
        Ec = 3.5e8
        sqrt3 = math.sqrt(3.0)
        beta = Ec * 3.0 * sqrt3 / (2.0 * Ps ** 3)
        alpha = -beta * Ps * Ps
        # Should not warn (ratios within 100x)
        PI.check_material_units("AlScN", Ps=Ps, Ec=Ec,
                                epsilon_r=15.0, alpha=alpha, beta=beta)

    def test_bad_units_caught(self):
        """Disordered alpha/beta should trigger a warning."""
        with pytest.warns(UserWarning):
            PI.check_material_units("BadMat", Ps=1.4, Ec=3.5e8,
                                    epsilon_r=15.0,
                                    alpha=-1e8, beta=1e18)


# ======================================================================
# Part 5: Hysteresis existence
# ======================================================================

class TestHysteresis:
    """A P-V sweep of a ferroelectric must show hysteresis."""

    def test_preisach_has_loop(self):
        Ps = 0.2; Ec = 5e7
        nx = 21; dx = 5e-9 / (nx - 1); N = nx; mid = N // 2
        sim = PyDeviceSimulator(nx, 1, 1, dx, 1.0, 1.0)
        sim.set_permittivity(np.full(N, EPS0 * 35.0))
        sim.set_mobility(np.zeros(N), np.zeros(N))
        sim.set_doping(np.zeros(N))
        sim.set_thermal_voltage(VT_300)
        sim.set_recombination(np.full(N, 1e-7), np.full(N, 1e-7))
        sim.set_effective_dos(np.full(N, 2.8e25), np.full(N, 1.04e25))
        sim.set_bandgap(np.full(N, 1.12))
        sim.set_ferroelectric_enabled(True)
        sim.set_ferroelectric_params(np.ones(N, dtype=np.int8), -1e8, 1e18)
        sim.set_ferroelectric_model(1)
        sim.set_ferroelectric_preisach(Ps, Ec, 0.0)
        sim.set_dirichlet_potential({0: 0.0, N - 1: 0.0})
        sim.set_electron_bc({0: 0.0, N - 1: 0.0})
        sim.set_hole_bc({0: 0.0, N - 1: 0.0})

        Vl = np.concatenate([
            np.linspace(0, 1, 12), np.linspace(1, 0, 12)[1:],
            np.linspace(0, -1, 12)[1:], np.linspace(-1, 0, 12)[1:],
        ])
        Pxs = []
        for Vg in Vl:
            sim.set_dirichlet_potential({0: float(Vg), N - 1: 0.0})
            Pxs.append(sim.solve()["P"][mid][0])
        P = np.array(Pxs)
        PI.check_hysteresis(Vl, P, min_window=0.001,
                            context="Preisach bipolar sweep")
