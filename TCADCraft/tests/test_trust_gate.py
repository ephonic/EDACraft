"""Truth-chain tests for the convergence credibility gate (plan0619.md M1/B5).

The trust gate must reject non-converged or unphysical solves so the discovery
search never promotes a bad candidate to the Pareto front.  Verified cases:

  1. A converged, well-behaved PN solve -> trust=True.
  2. A result with ``converged=False`` -> trust=False (reason recorded).
  3. A result whose KCL residual exceeds threshold -> trust=False.
  4. Metrics outside the physical range (SS<=0, Ioff>Ion, non-finite) ->
     trust=False.
  5. Equilibrium (zero current -> NaN KCL spread) is treated as trusted.
  6. ``annotate_sweep_with_trust`` propagates trust=False to every result whose
     solve failed, and a non-converged point never enters a trusted set.
"""

from __future__ import annotations
import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from tcad.core import PyDeviceSimulator
from tcad.postprocess import (
    kcl_residual_1d,
    assess_trust,
    annotate_sweep_with_trust,
)

VT_300 = 8.617333262e-5 * 300.0
EPS0 = 8.854187817e-12
EPS_SI = EPS0 * 11.7


class _RawMesh:
    """Minimal mesh facade exposing what ``kcl_residual_1d`` reads."""
    def __init__(self, nx, dx):
        self.nx = nx
        self.ny = 1
        self.nz = 1
        self.dx = dx
        self._npts = nx
        self.fields = {}

    def npts(self):
        return self._npts


class _RawSim:
    """Adapter wrapping a raw ``PyDeviceSimulator`` result + mesh so the
    postprocess trust API (which expects a ``Simulator``-like object with
    ``.mesh`` and ``.VT``) can assess a raw-C++ solve.  This is the
    KCL-consistent path the audit certifies (test_numerical_validation
    ``TestCurrentConservation``), and the appropriate "credible" reference for
    the trust gate."""

    def __init__(self, nx, dx, mu_n=0.14, mu_p=0.045):
        self.mesh = _RawMesh(nx, dx)
        self.mesh.fields = {
            "mu_n": np.full(nx, mu_n, dtype=float),
            "mu_p": np.full(nx, mu_p, dtype=float),
        }
        self.VT = VT_300


def _raw_pn_solve(vbias=0.05, nx=41, use_newton=True, max_iter=200, tol=1e-9):
    """Raw-C++ biased PN solve (mirrors TestCurrentConservation._biased_pn).

    Returns (raw_sim_adapter, result_dict).  The adapter carries the mesh/VT
    needed by ``assess_trust`` / ``kcl_residual_1d``.
    """
    Lx = 80e-9
    dx = Lx / (nx - 1)
    cxx = PyDeviceSimulator(nx, 1, 1, dx, dx, dx)
    cxx.set_permittivity(np.full(nx, EPS_SI, dtype=np.float64))
    cxx.set_mobility(np.full(nx, 0.14, dtype=np.float64),
                     np.full(nx, 0.045, dtype=np.float64))
    cxx.set_thermal_voltage(VT_300)
    Na, Nd = 1e23, 1e22
    ni = 6.6759e9 * 1e6
    Nc = Nv = ni * np.exp(1.12 / (2 * VT_300))
    doping = np.zeros(nx, dtype=np.float64)
    doping[: nx // 2] = -Na
    doping[nx // 2:] = Nd
    cxx.set_doping(doping)
    cxx.set_bandgap(np.full(nx, 1.12, dtype=np.float64))
    cxx.set_effective_dos(np.full(nx, Nc, dtype=np.float64),
                          np.full(nx, Nv, dtype=np.float64))
    phi_p = -VT_300 * np.log(max(Na, ni) / ni) + vbias
    phi_n = VT_300 * np.log(max(Nd, ni) / ni)
    cxx.set_dirichlet_potential({0: float(phi_p), nx - 1: float(phi_n)})
    cxx.set_electron_bc({0: float(ni * ni / max(Na, 1.0)),
                         nx - 1: float(Nd)})
    cxx.set_hole_bc({0: float(Na), nx - 1: float(ni * ni / max(Nd, 1.0))})
    cxx.set_use_newton(use_newton)
    cxx.set_gummel_max_iter(max_iter)
    cxx.set_tolerance(tol)
    r = cxx.solve()
    sim = _RawSim(nx, dx)
    return sim, r


def _pn_simulator(vbias: float = 0.0, nx: int = 61, L: float = 200e-9,
                  use_newton: bool = True):
    """1-D-like PN junction via the high-level Device API (named contacts).

    Uses Newton by default because the Gummel path on abrupt high-doping
    junctions is not KCL-consistent (audit_recheck.md #3, rel spread ~16) — the
    Newton path is the one the audit certifies as divergence-free and is what a
    credible discovery pipeline should use.  The Gummel KCL violation is itself
    something the trust gate is meant to surface.
    """
    dev = Device.pnjunction(
        L=L, W=1e-9, H=1e-9, x_junction=L / 2, Na=1e18, Nd=1e18,
    )
    dx = L / (nx - 1)
    mesh = structured_mesh_from_device(dev, resolution=(dx, 1e-9, 1e-9))
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_use_newton(use_newton)
    sim.set_contact("p_contact", voltage=vbias)
    sim.set_contact("n_contact", voltage=0.0)
    return sim


# ---------------------------------------------------------------------------
# 1. Converged good solve -> trust=True  (raw-C++ Newton, KCL-consistent)
# ---------------------------------------------------------------------------
class TestTrustOnGoodSolve:
    def test_converged_solve_is_trusted(self):
        sim, r = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)
        assert r["converged"]
        rep = assess_trust(sim, r)
        assert rep.trust, f"good solve untrusted: {rep.reasons}"
        assert rep.converged
        # KCL spread should be a finite, small number (raw Newton ~1e-3).
        assert np.isfinite(rep.kcl_rel_spread)
        assert rep.kcl_rel_spread < 1e-2


# ---------------------------------------------------------------------------
# 2. Non-converged result -> trust=False
# ---------------------------------------------------------------------------
class TestTrustOnNonConverged:
    def test_nonconverged_result_untrusted(self):
        sim, r = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True,
                               max_iter=1, tol=1e-15)
        if r["converged"]:
            pytest.skip("single-iter solve unexpectedly converged")
        rep = assess_trust(sim, r)
        assert not rep.trust
        assert any("did not converge" in s for s in rep.reasons)

    def test_explicit_converged_false_flag_untrusted(self):
        """A result with converged=False is untrusted regardless of the fields
        (the gate must not trust a solver that gave up)."""
        sim, r = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)
        r["converged"] = False  # simulate a ramp failure
        rep = assess_trust(sim, r)
        assert not rep.trust
        assert rep.converged is False
        assert any("did not converge" in s for s in rep.reasons)


# ---------------------------------------------------------------------------
# 3. KCL residual threshold -> trust=False when violated
# ---------------------------------------------------------------------------
class TestTrustKclResidual:
    def test_kcl_residual_finite_on_biased_solve(self):
        sim, r = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)
        spread = kcl_residual_1d(sim, r)
        assert np.isfinite(spread)
        assert spread >= 0.0

    def test_trust_false_when_kcl_exceeds_tight_threshold(self):
        """A converged raw-Newton solve has KCL spread ~1e-3.  With a threshold
        below that, it must be flagged untrusted even though ``converged=True``
        — proving the KCL signal is independent of the solver flag."""
        sim, r = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)
        assert r["converged"]
        spread = kcl_residual_1d(sim, r)
        # Threshold below the actual spread -> must be untrusted.
        rep = assess_trust(sim, r, kcl_rel_spread_threshold=max(spread * 0.5, 1e-6))
        assert not rep.trust
        assert any("KCL residual" in s for s in rep.reasons)

    def test_gummel_high_kcl_flagged_as_marginal(self):
        """The Gummel path on the high-level Device PN junction has KCL spread
        ~1-3 (audit_recheck.md #3).  With the *default* threshold (10) it stays
        trusted-but-marginal; with a tight threshold (0.1) it is correctly
        flagged untrusted — surfacing the known solver-quality gap."""
        sim = _pn_simulator(vbias=0.05, nx=81, use_newton=False)
        r = sim.run(max_iter=200, tol=1e-9)
        if not r["converged"]:
            pytest.skip("Gummel solve did not converge on this path")
        spread = kcl_residual_1d(sim, r)
        # Tight threshold must flag the marginal Gummel path.
        rep = assess_trust(sim, r, kcl_rel_spread_threshold=0.1)
        assert not rep.trust
        assert any("KCL residual" in s for s in rep.reasons)


# ---------------------------------------------------------------------------
# 4. Physical-range checks -> trust=False on unphysical metrics
# ---------------------------------------------------------------------------
class TestTrustPhysicalRange:
    def _good_result(self):
        return _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)

    def test_negative_ss_untrusted(self):
        sim, r = self._good_result()
        metrics = {"Ion": 1e-4, "Ioff": 1e-7, "SS": -5.0, "Vth": 0.1}
        rep = assess_trust(sim, r, metrics=metrics)
        assert not rep.trust
        assert any("SS" in s for s in rep.reasons)

    def test_ioff_exceeds_ion_untrusted(self):
        sim, r = self._good_result()
        metrics = {"Ion": 1e-7, "Ioff": 1e-4, "SS": 60.0, "Vth": 0.1}
        rep = assess_trust(sim, r, metrics=metrics)
        assert not rep.trust
        assert any("Ioff" in s for s in rep.reasons)

    def test_non_finite_ion_untrusted(self):
        sim, r = self._good_result()
        metrics = {"Ion": float("nan"), "Ioff": 1e-7, "SS": 60.0, "Vth": 0.1}
        rep = assess_trust(sim, r, metrics=metrics)
        assert not rep.trust
        assert any("Ion" in s for s in rep.reasons)

    def test_good_metrics_no_metric_reasons(self):
        sim, r = self._good_result()
        metrics = {"Ion": 1e-4, "Ioff": 1e-7, "SS": 80.0, "Vth": 0.2}
        rep = assess_trust(sim, r, metrics=metrics)
        # converged + KCL may still produce reasons, but none from metric range.
        metric_reasons = [s for s in rep.reasons
                          if any(k in s for k in ("Ion", "Ioff", "SS", "Vth"))]
        assert metric_reasons == [], f"unexpected metric-range failure: {metric_reasons}"


# ---------------------------------------------------------------------------
# 5. Equilibrium (zero current, NaN KCL) is trusted
# ---------------------------------------------------------------------------
class TestTrustEquilibrium:
    def test_zero_current_equilibrium_trusted(self):
        """Zero-bias equilibrium carries only discretization-noise current
        (max|J| ~ 1e-7, ~4 orders below a typical on-current ~1e-3).  With an
        on-current scale supplied, the KCL floor classifies it as negligible
        (NaN spread) and the converged solve is trusted."""
        sim, r = _raw_pn_solve(vbias=0.0, nx=41, use_newton=True)
        assert r["converged"], "equilibrium raw solve did not converge"
        # Typical 1-D on-current density for this device family [A/m^2].
        rep = assess_trust(sim, r, on_current_scale=1e-2)
        assert rep.trust, f"equilibrium untrusted: {rep.reasons}"
        assert np.isnan(rep.kcl_rel_spread)


# ---------------------------------------------------------------------------
# 6. annotate_sweep_with_trust propagates failures across a sweep
# ---------------------------------------------------------------------------
class TestSweepTrustPropagation:
    def test_nonconverged_point_marked_untrusted_in_sweep(self):
        """A sweep with one hand-injected non-converged point must have that
        point's ``trust=False`` while converged points stay trusted."""
        sim0, r0 = _raw_pn_solve(vbias=0.0, nx=41, use_newton=True)
        sim1, r1 = _raw_pn_solve(vbias=0.05, nx=41, use_newton=True)
        r_bad = dict(r1)
        r_bad["converged"] = False  # simulate a ramp failure at this point
        # Use sim1's mesh (same geometry) for the joint assessment.  Supply an
        # on-current scale so the zero-bias point (equilibrium noise) is trusted.
        sweep = [r0, r_bad, r1]
        reports = annotate_sweep_with_trust(sim1, sweep, on_current_scale=1e-2)
        assert len(reports) == 3
        # The injected-failure point must be untrusted.
        assert not reports[1].trust
        assert not sweep[1]["trust"]
        # The two genuine converged points must carry a trust flag key.
        assert "trust" in sweep[0]
        assert "trust" in sweep[2]
        # Converged raw-Newton points should be trusted.
        assert sweep[0]["trust"], f"point 0 untrusted: {reports[0].reasons}"
        assert sweep[2]["trust"], f"point 2 untrusted: {reports[2].reasons}"
