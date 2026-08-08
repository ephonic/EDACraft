"""Tests for Newton-Raphson full-coupled solver."""

import numpy as np
import pytest

from tcad.simulator import Simulator
from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device


def _make_1d_sim(vbias_p=0.0, use_newton=False):
    """Build a fast 1D PN junction for quick Newton tests."""
    L = 40e-9
    dev = Device.pnjunction(L=L, W=L, H=L, x_junction=L/2, Na=1e24, Nd=1e22)
    mesh = structured_mesh_from_device(dev, nx=11, ny=1, nz=1)
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.set_contact("p_contact", voltage=vbias_p)
    sim.set_contact("n_contact", voltage=0.0)
    sim.set_use_newton(use_newton)
    return sim, mesh


class TestNewtonConvergence:
    """Verify Newton solver converges in scenarios where Gummel also works."""

    def test_newton_equilibrium_pnjunction(self):
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert results["phi"].size == mesh.npts()
        assert results["n"].size == mesh.npts()
        assert results["p"].size == mesh.npts()

    def test_newton_biased_pnjunction(self):
        sim, mesh = _make_1d_sim(vbias_p=0.1, use_newton=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]

    def test_newton_with_srh(self):
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        npts = mesh.npts()
        sim._sim.set_recombination(np.ones(npts, dtype=float) * 1e-7, np.ones(npts, dtype=float) * 1e-7)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert results["n"].max() > 1e20
        assert results["p"].max() > 1e20

    def test_newton_with_optical_generation(self):
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim.set_optical_generation(np.ones(mesh.npts()) * 1e20)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
        assert results["n"].max() > 1e16
        assert results["p"].max() > 1e16

    def test_newton_primary_auger_reduces_high_injection(self):
        """Newton-primary must not silently drop the enabled Auger model."""
        def run(enable_auger):
            sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
            sim._sim.set_newton_primary(True)
            sim._sim.set_auger_enabled(enable_auger)
            if enable_auger:
                # Deliberately strong coefficient makes the regression
                # observable on this tiny mesh; production defaults are
                # independently calibrated against Sentaurus.
                sim._sim.set_auger_params(1e-38, 1e-38)
            sim.set_optical_generation(np.full(mesh.npts(), 1e34))
            result = sim.run(max_iter=200, tol=1e-8)
            assert result["converged"]
            # Auger acts on electron-hole pairs; majority charge is pinned by
            # doping/contacts, so compare the pair-limited minority density.
            return float(np.mean(np.minimum(result["n"], result["p"])[1:-1]))

        without_auger = run(False)
        with_auger = run(True)
        assert with_auger < without_auger * 0.999

    def test_newton_primary_does_not_inherit_skipped_gummel_success(self):
        """A skipped Gummel stage must not mask primary-Newton failure."""
        sim, _ = _make_1d_sim(vbias_p=0.1, use_newton=True)
        sim._sim.set_newton_primary(True)
        # Zero iterations deterministically makes the primary Newton stage
        # fail.  Before this regression fix, gummel_ok started as true even
        # though Gummel was skipped, so this result was falsely converged.
        results = sim.run(max_iter=0, tol=1e-8)
        assert not results["converged"]

    def test_newton_primary_preserves_coupled_state_kcl(self):
        """Post-processing must not re-solve phi apart from converged n,p."""
        sim, _ = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim._sim.set_newton_primary(True)
        results = sim.run(max_iter=120, tol=1e-8)
        assert results["converged"]
        current = (np.asarray(results["Jn_x"]) + np.asarray(results["Jp_x"]))[:-1]
        spread = float(np.max(current) - np.min(current))
        assert spread < 1e-8, f"primary-Newton state was changed after convergence: {spread:g} A/m2"


class TestNewtonGummelAgreement:
    """Verify Newton and Gummel produce identical physical solutions."""

    def test_newton_gummel_agreement_equilibrium(self):
        sim_g, mesh = _make_1d_sim(vbias_p=0.0, use_newton=False)
        res_g = sim_g.run(max_iter=100, tol=1e-8)

        sim_n, _ = _make_1d_sim(vbias_p=0.0, use_newton=True)
        res_n = sim_n.run(max_iter=100, tol=1e-8)

        assert res_g["converged"]
        assert res_n["converged"]

        phi_diff = np.abs(res_g["phi"] - res_n["phi"]).max()
        n_diff = np.abs(res_g["n"] - res_n["n"]).max()
        p_diff = np.abs(res_g["p"] - res_n["p"]).max()

        assert phi_diff < 1e-6, f"phi mismatch: {phi_diff}"
        assert n_diff / res_g["n"].max() < 1e-6, f"n relative mismatch: {n_diff / res_g['n'].max()}"
        assert p_diff / res_g["p"].max() < 1e-6, f"p relative mismatch: {p_diff / res_g['p'].max()}"

    def test_newton_gummel_agreement_biased(self):
        sim_g, mesh = _make_1d_sim(vbias_p=0.1, use_newton=False)
        res_g = sim_g.run(max_iter=100, tol=1e-8)

        sim_n, _ = _make_1d_sim(vbias_p=0.1, use_newton=True)
        res_n = sim_n.run(max_iter=100, tol=1e-8)

        assert res_g["converged"]
        assert res_n["converged"]

        phi_diff = np.abs(res_g["phi"] - res_n["phi"]).max()
        n_diff = np.abs(res_g["n"] - res_n["n"]).max()
        p_diff = np.abs(res_g["p"] - res_n["p"]).max()

        assert phi_diff < 1e-6, f"phi mismatch: {phi_diff}"
        assert n_diff / res_g["n"].max() < 1e-6, f"n relative mismatch: {n_diff / res_g['n'].max()}"
        assert p_diff / res_g["p"].max() < 1e-6, f"p relative mismatch: {p_diff / res_g['p'].max()}"

class TestNewtonOptions:
    """Verify Newton option exposure works end-to-end."""

    def test_newton_options_exposure(self):
        """All Newton options can be set without error."""
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim.set_newton_options(
            damping=0.9,
            min_damping=0.05,
            use_line_search=True,
            line_search_max=15,
            use_log_damping=True,
            jacobian_reuse_threshold=5.0,
        )
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]

    def test_newton_log_damping_biased(self):
        """Log damping should converge on a forward-biased junction."""
        sim, mesh = _make_1d_sim(vbias_p=0.1, use_newton=True)
        sim.set_newton_options(use_log_damping=True)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]

    def test_newton_jacobian_reuse(self):
        """Jacobian reuse should not break convergence."""
        sim, mesh = _make_1d_sim(vbias_p=0.0, use_newton=True)
        sim.set_newton_options(jacobian_reuse_threshold=10.0)
        results = sim.run(max_iter=100, tol=1e-8)
        assert results["converged"]
