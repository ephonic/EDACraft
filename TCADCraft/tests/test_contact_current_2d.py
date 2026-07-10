"""Truth-chain tests for contact_current_2d (M6c).

Validates the 2-D terminal-current extractor before the DevSim comparison:
  - Equilibrium: all terminal currents ≈ 0.
  - KCL: p + n contact currents sum to ≈ 0 (what flows in flows out).
  - Sign: forward-bias current is larger than reverse, correct sign.
  - Consistency with contact_current_1d: the 2-D integrator reduces to the
    1-D extractor scaled by the cross-sectional area on a quasi-1-D device.
  - z-scaling: doubling nz doubles the integrated current (uniform in z).

Uses the same low-doping PN junction as test_contact_current.py (Na=Nd=1e18,
L=200nm) which converges cleanly and has well-behaved SG fluxes.
"""

from __future__ import annotations
import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from tcad.postprocess.current import contact_current_1d, contact_current_2d


def _pn_simulator_2d(vbias: float = 0.0, nx: int = 61, nz: int = 3,
                     L: float = 200e-9, W: float = 1e-9, H: float = 10e-9):
    """A PN junction meshed as a 2-D slab (ny=1, nz>1) for 2-D current tests.

    Uses the same Device.pnjunction template and low doping (Na=Nd=1e18) as
    test_contact_current.py's _pn_simulator, so the physics is well-behaved.
    A true 2-D mesh (``ny=1``) avoids the __float128 slowdown from a spurious
    3rd dimension.  The contacts sit on the bottom face (z=0) at the left and
    right x-boundaries; contact_current_2d classifies them as x-normal (left =
    p_contact at i=0, right = n_contact at i=nx-1).
    """
    dev = Device.pnjunction(
        L=L, W=W, H=H, x_junction=L / 2, Na=1e18, Nd=1e18,
    )
    mesh = structured_mesh_from_device(dev, nx=nx, ny=1, nz=nz)
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_contact("p_contact", voltage=vbias)
    sim.set_contact("n_contact", voltage=0.0)
    return sim


# ---------------------------------------------------------------------------
# 1. Equilibrium: contact current ≈ 0
# ---------------------------------------------------------------------------
class TestEquilibriumCurrent2d:
    def test_zero_bias_current_approximately_zero(self):
        """At equilibrium the terminal current is ~0 (KCL truth-chain anchor)."""
        sim = _pn_simulator_2d(vbias=0.0, nx=61, nz=3)
        r = sim.run(max_iter=120, tol=1e-9)
        assert r["converged"], "equilibrium solve did not converge"
        I_p = contact_current_2d(sim, r, "p_contact")
        I_n = contact_current_2d(sim, r, "n_contact")
        # 2-D current is integrated [A] over a tiny cross-section
        # (W=1nm × H=10nm → ~1e-17 m²), so absolute currents are ~1e-18 A
        # under forward bias.  At equilibrium the __float128 solver drives the
        # current to ~1e-21 A (machine-zero relative to the on-current).
        assert abs(I_p) < 1e-15, f"equilibrium |I_p|={abs(I_p):.3e} not ~0"
        assert abs(I_n) < 1e-15, f"equilibrium |I_n|={abs(I_n):.3e} not ~0"


# ---------------------------------------------------------------------------
# 2. KCL: p + n ≈ 0 under bias
# ---------------------------------------------------------------------------
class TestKCLCurrent2d:
    def test_kcl_forward_bias(self):
        """Under forward bias, I_p + I_n ≈ 0 (divergence-free / KCL)."""
        sim = _pn_simulator_2d(vbias=0.3, nx=61, nz=3)
        r = sim.run(max_iter=120, tol=1e-9)
        assert r["converged"]
        I_p = contact_current_2d(sim, r, "p_contact")
        I_n = contact_current_2d(sim, r, "n_contact")
        assert abs(I_p + I_n) < 0.1 * max(abs(I_p), abs(I_n), 1e-30), (
            f"KCL violated: Ip={I_p}, In={I_n}, sum={I_p + I_n}"
        )

    def test_forward_bias_nonzero(self):
        """Forward bias drives a current well above the equilibrium floor.

        The device cross-section is tiny (W=1nm × H=10nm ≈ 1e-17 m²), so the
        absolute current is ~1e-18 A — but that is still many orders of
        magnitude above the equilibrium residual (~1e-21 A).  We require the
        forward-bias current to exceed the equilibrium current by ≥10²×.
        """
        sim_fwd = _pn_simulator_2d(vbias=0.3, nx=61, nz=3)
        r_fwd = sim_fwd.run(max_iter=120, tol=1e-9)
        assert r_fwd["converged"]
        I_fwd = abs(contact_current_2d(sim_fwd, r_fwd, "n_contact"))

        sim_eq = _pn_simulator_2d(vbias=0.0, nx=61, nz=3)
        r_eq = sim_eq.run(max_iter=120, tol=1e-9)
        assert r_eq["converged"]
        I_eq = abs(contact_current_2d(sim_eq, r_eq, "n_contact"))

        assert I_fwd > 1e2 * I_eq, (
            f"forward |I|={I_fwd:.3e} not >> equilibrium |I|={I_eq:.3e}"
        )


# ---------------------------------------------------------------------------
# 3. Consistency with contact_current_1d
# ---------------------------------------------------------------------------
class TestConsistency1d2d:
    def test_quasi_1d_agreement(self):
        """On a quasi-1-D slab the 2-D integrator = 1-D extractor × area."""
        sim = _pn_simulator_2d(vbias=0.3, nx=61, nz=3)
        r = sim.run(max_iter=120, tol=1e-9)
        assert r["converged"]

        I_1d = contact_current_1d(sim, r, "n_contact")  # [A/m^2] single edge
        I_2d = contact_current_2d(sim, r, "n_contact")  # [A] integrated
        mesh = sim.mesh
        # 2-D sums over nz z-rows (each = same density in quasi-1-D), times
        # dz * width.  So I_2d = I_1d * nz * dz * (dy * ny).
        scale = (mesh.nz * mesh.dz) * (mesh.dy * mesh.ny)
        assert I_2d == pytest.approx(I_1d * scale, rel=1e-6), (
            f"2d={I_2d} != 1d*scale={I_1d * scale} (scale={scale})"
        )

    def test_z_scaling(self):
        """Doubling nz doubles the integrated current (uniform in z)."""
        sim_a = _pn_simulator_2d(vbias=0.3, nx=61, nz=2, H=10e-9)
        r_a = sim_a.run(max_iter=120, tol=1e-9)
        assert r_a["converged"]
        I_a = contact_current_2d(sim_a, r_a, "n_contact")

        sim_b = _pn_simulator_2d(vbias=0.3, nx=61, nz=4, H=10e-9)
        r_b = sim_b.run(max_iter=120, tol=1e-9)
        assert r_b["converged"]
        I_b = contact_current_2d(sim_b, r_b, "n_contact")

        assert I_b == pytest.approx(2.0 * I_a, rel=1e-6), (
            f"doubling nz: I_b={I_b} != 2*I_a={2.0 * I_a}"
        )
