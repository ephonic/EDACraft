"""Tests for log-space Newton solver (M6b / audit §18).

The log-space path stores u=log(n), v=log(p) in the Newton state vector instead
of n, p.  Because the residuals are evaluated on the linearised densities
n=exp(u), the physics is identical to the linear-space path — only the
Jacobian conditioning and update rule change.  These tests verify:

1. Equivalence: linear-space and log-space Newton produce the same phi/n/p.
2. Positivity: log-space never produces n<=0 or p<=0.
3. Option exposure: use_log_space threads through the Python/Cython/C++ stack.
4. Dynamic range: log-space handles a wide depletion<->inversion span.
"""

import numpy as np
import pytest

from tcad.simulator import Simulator
from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device


def _make_1d_sim(vbias_p=0.0, use_newton=False):
    """Build a fast 1D PN junction for quick Newton tests."""
    L = 40e-9
    dev = Device.pnjunction(L=L, W=L, H=L, x_junction=L / 2, Na=1e24, Nd=1e22)
    mesh = structured_mesh_from_device(dev, nx=11, ny=1, nz=1)
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.set_contact("p_contact", voltage=vbias_p)
    sim.set_contact("n_contact", voltage=0.0)
    sim.set_use_newton(use_newton)
    return sim, mesh


class TestLogSpaceEquivalence:
    """Log-space and linear-space Newton must agree on the same device."""

    def test_equilibrium_equivalence(self):
        """At equilibrium, linear and log-space Newton give the same solution."""
        sim_lin, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        res_lin = sim_lin.run(max_iter=100, tol=1e-8)

        sim_log, _ = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim_log.set_newton_options(use_log_space=True)
        res_log = sim_log.run(max_iter=100, tol=1e-8)

        assert res_lin["converged"], "linear-space Newton did not converge"
        assert res_log["converged"], "log-space Newton did not converge"

        phi_diff = np.abs(res_lin["phi"] - res_log["phi"]).max()
        # Relative difference on the max density (avoids div-by-zero in depletion)
        n_max = max(res_lin["n"].max(), 1.0)
        p_max = max(res_lin["p"].max(), 1.0)
        n_diff = np.abs(res_lin["n"] - res_log["n"]).max()
        p_diff = np.abs(res_lin["p"] - res_log["p"]).max()

        assert phi_diff < 1e-6, f"phi mismatch: {phi_diff}"
        assert n_diff / n_max < 1e-4, f"n relative mismatch: {n_diff / n_max}"
        assert p_diff / p_max < 1e-4, f"p relative mismatch: {p_diff / p_max}"

    def test_biased_equivalence(self):
        """Under forward bias, linear and log-space Newton give the same solution."""
        sim_lin, mesh = _make_1d_sim(vbias_p=0.1, use_newton=True)
        res_lin = sim_lin.run(max_iter=100, tol=1e-8)

        sim_log, _ = _make_1d_sim(vbias_p=0.1, use_newton=True)
        sim_log.set_newton_options(use_log_space=True)
        res_log = sim_log.run(max_iter=100, tol=1e-8)

        assert res_lin["converged"], "linear-space Newton did not converge"
        assert res_log["converged"], "log-space Newton did not converge"

        phi_diff = np.abs(res_lin["phi"] - res_log["phi"]).max()
        n_max = max(res_lin["n"].max(), 1.0)
        p_max = max(res_lin["p"].max(), 1.0)
        n_diff = np.abs(res_lin["n"] - res_log["n"]).max()
        p_diff = np.abs(res_lin["p"] - res_log["p"]).max()

        assert phi_diff < 1e-6, f"phi mismatch: {phi_diff}"
        assert n_diff / n_max < 1e-4, f"n relative mismatch: {n_diff / n_max}"
        assert p_diff / p_max < 1e-4, f"p relative mismatch: {p_diff / p_max}"


class TestLogSpacePositivity:
    """Log-space must guarantee n > 0 and p > 0 everywhere."""

    def test_no_negative_densities(self):
        sim, mesh = _make_1d_sim(vbias_p=0.1, use_newton=True)
        sim.set_newton_options(use_log_space=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert (results["n"] > 0).all(), "log-space produced n <= 0"
        assert (results["p"] > 0).all(), "log-space produced p <= 0"
        # No underflow to exactly zero either
        assert (results["n"] > 1e-300).all(), "log-space n underflowed to 0"
        assert (results["p"] > 1e-300).all(), "log-space p underflowed to 0"


class TestLogSpaceOptions:
    """Option exposure through the Python/Cython/C++ stack."""

    def test_option_set_without_error(self):
        """use_log_space can be set without error."""
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim.set_newton_options(use_log_space=True)
        # Should not raise
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]

    def test_log_space_with_srh(self):
        """Log-space Newton converges with SRH recombination enabled."""
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        npts = mesh.npts()
        sim._sim.set_recombination(
            np.ones(npts, dtype=float) * 1e-7,
            np.ones(npts, dtype=float) * 1e-7,
        )
        sim.set_newton_options(use_log_space=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert results["n"].max() > 1e20
        assert results["p"].max() > 1e20

    def test_log_space_with_optical_generation(self):
        """Log-space Newton converges with optical generation."""
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim.set_optical_generation(np.ones(mesh.npts()) * 1e20)
        sim.set_newton_options(use_log_space=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert results["n"].max() > 1e16
        assert results["p"].max() > 1e16


class TestLogSpaceDynamicRange:
    """Log-space should handle a wide carrier dynamic range without freezing."""

    def test_high_doping_range(self):
        """A junction with Na=1e26, Nd=1e24 has p~1e26 next to n~1e24 — a
        100dB range that stresses linear-space conditioning.  Log-space should
        converge and produce physically sane densities."""
        L = 40e-9
        dev = Device.pnjunction(L=L, W=L, H=L, x_junction=L / 2,
                                Na=1e26, Nd=1e24)
        mesh = structured_mesh_from_device(dev, nx=11, ny=1, nz=1)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        sim.set_use_newton(True)
        sim.set_newton_options(use_log_space=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"], "log-space did not converge on high-doping junction"
        # Majority carriers should be near their doping levels
        assert results["p"].max() > 1e25, f"p too low: {results['p'].max()}"
        assert results["n"].max() > 1e23, f"n too low: {results['n'].max()}"
        # And positive everywhere
        assert (results["n"] > 0).all()
        assert (results["p"] > 0).all()
