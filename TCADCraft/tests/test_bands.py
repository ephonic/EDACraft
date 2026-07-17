"""D1 band-diagram truth-chain (plan0619.md §D1).

Fast unit tests (no solver) pin down the band-edge algebra and the 1-D
cutline helper against synthetic fields, so the formulas are verified
independently of the Newton solver:

  * ``Evac = -phi``                       (vacuum level; phi in V)
  * ``Ec   = Evac - chi``                 (conduction band)
  * ``Ev   = Ec - Eg``                    (valence band)
  * ``Efn  = Ec + VT*ln(n/Nc)``           (electron quasi-Fermi, Boltzmann)
  * ``Efp  = Ev - VT*ln(p/Nv)``           (hole quasi-Fermi, Boltzmann)
  * heterojunction: an ``Ec`` jump of exactly ``-dchi`` at the interface
  * cutline length == ``nx`` and consistent node ordering

Slow integration tests (solver-backed, ``TCAD_RUN_SLOW=1``) check that a
real MOSFET solve produces a band cutline whose ``Ec`` bends in the channel
under gate bias — the qualitative "band picture" sanity check.
"""

import os
import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess.bands import (
    cutline_x_at_jk, band_edges, band_diagram_1d, BandEdges, BandCutline,
)


RUN_SLOW = os.environ.get("TCAD_RUN_SLOW", "") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set TCAD_RUN_SLOW=1 to run solver-backed tests")


# ---------------------------------------------------------------------------
# Minimal fake simulator: carries the attributes band_edges reads (mesh, VT).
# ---------------------------------------------------------------------------

class _FakeSim:
    def __init__(self, mesh, VT=0.02585):
        self.mesh = mesh
        self.VT = VT


def _make_mesh(nx=5, ny=1, nz=1, chi=None, Eg=None, Nc=None, Nv=None):
    """Uniform 1-D-ish mesh with optional per-node material fields."""
    mesh = StructuredGrid(((0.0, 1.0), (0.0, 0.1), (0.0, 0.1)), nx, ny, nz)
    n = mesh.npts()
    mesh.fields["chi"] = np.full(n, 4.05) if chi is None else np.asarray(chi, float)
    mesh.fields["Eg"] = np.full(n, 1.12) if Eg is None else np.asarray(Eg, float)
    mesh.fields["Nc"] = np.full(n, 2.8e19) if Nc is None else np.asarray(Nc, float)
    mesh.fields["Nv"] = np.full(n, 1.04e19) if Nv is None else np.asarray(Nv, float)
    return mesh


# ===========================================================================
# 1. cutline_x_at_jk
# ===========================================================================

class TestCutline:
    def test_length_equals_nx(self):
        mesh = _make_mesh(nx=7, ny=3, nz=2)
        x, line = cutline_x_at_jk(mesh, j=1, k=0)
        assert len(x) == 7
        assert len(line) == 7

    def test_indices_follow_node_ordering(self):
        """idx = i + nx*(j + ny*k) — the x-line at fixed (j,k)."""
        mesh = _make_mesh(nx=4, ny=2, nz=2)
        nx, ny = mesh.nx, mesh.ny
        j, k = 1, 1
        _, line = cutline_x_at_jk(mesh, j=j, k=k)
        expected = np.array([i + nx * (j + ny * k) for i in range(nx)])
        np.testing.assert_array_equal(line, expected)

    def test_x_coords_match_grid(self):
        mesh = _make_mesh(nx=5, ny=1, nz=1)
        x, _ = cutline_x_at_jk(mesh, j=0, k=0)
        np.testing.assert_allclose(x, np.linspace(0.0, 1.0, 5))

    def test_out_of_bounds_raises(self):
        mesh = _make_mesh(nx=3, ny=2, nz=1)
        with pytest.raises(IndexError):
            cutline_x_at_jk(mesh, j=5, k=0)


# ===========================================================================
# 2. band_edges algebra
# ===========================================================================

class TestBandEdges:
    def test_evac_is_neg_phi(self):
        """Evac = -phi."""
        mesh = _make_mesh(nx=4)
        phi = np.array([0.0, 0.1, -0.2, 0.3])
        n = np.full(4, 1e23)
        p = np.full(4, 1e23)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        np.testing.assert_allclose(be.Evac, -phi)

    def test_ec_is_evac_minus_chi(self):
        """Ec = Evac - chi (phi=0 -> Ec = -chi)."""
        mesh = _make_mesh(nx=4, chi=[4.05, 4.05, 3.5, 4.05])
        phi = np.zeros(4)
        n = np.full(4, 1e23)
        p = np.full(4, 1e23)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        np.testing.assert_allclose(be.Ec, -np.array([4.05, 4.05, 3.5, 4.05]))

    def test_ev_is_ec_minus_eg(self):
        """Ev = Ec - Eg."""
        mesh = _make_mesh(nx=3, chi=[4.0, 4.0, 4.0], Eg=[1.12, 1.0, 0.7])
        phi = np.zeros(3)
        n = np.full(3, 1e23)
        p = np.full(3, 1e23)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        np.testing.assert_allclose(be.Ev, be.Ec - np.array([1.12, 1.0, 0.7]))

    def test_efn_equilibrium_is_ec(self):
        """At equilibrium n = Nc -> Efn = Ec (Boltzmann)."""
        mesh = _make_mesh(nx=3, Nc=[2.8e19 * 1e6, 2.8e19 * 1e6, 2.8e19 * 1e6])
        # NOTE: Nc stored in cm^-3 in the field; band_edges converts *1e6 to m^-3.
        # So set Nc field to 2.8e19 (cm^-3) and n to 2.8e25 (m^-3) = Nc*1e6.
        mesh.fields["Nc"] = np.full(3, 2.8e19)  # cm^-3
        n = np.full(3, 2.8e25)                   # m^-3  (= Nc_cm3 * 1e6)
        p = np.full(3, 1.0e10)
        phi = np.zeros(3)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        np.testing.assert_allclose(be.Efn, be.Ec, atol=1e-12)

    def test_efp_equilibrium_is_ev(self):
        """At equilibrium p = Nv -> Efp = Ev (Boltzmann)."""
        mesh = _make_mesh(nx=3)
        mesh.fields["Nv"] = np.full(3, 1.04e19)  # cm^-3
        p = np.full(3, 1.04e25)                   # m^-3
        n = np.full(3, 1.0e10)
        phi = np.zeros(3)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        np.testing.assert_allclose(be.Efp, be.Ev, atol=1e-12)

    def test_heterojunction_ec_jump(self):
        """A chi step of dchi produces an Ec jump of exactly +dchi.

        Ec = -chi, so a *decrease* in chi by dchi raises Ec by dchi — the
        classic conduction-band spike at a heterojunction into a material
        with larger electron affinity.
        """
        dchi = 0.3
        chi = np.array([4.05, 4.05, 4.05 - dchi, 4.05 - dchi])
        mesh = _make_mesh(nx=4, chi=chi)
        phi = np.zeros(4)
        n = np.full(4, 1e23)
        p = np.full(4, 1e23)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        # Ec jump across the interface (node 1 -> node 2): dEc = -dchi_chi = +dchi.
        jump = be.Ec[2] - be.Ec[1]
        assert jump == pytest.approx(dchi)
        # The flat regions on each side have constant Ec.
        assert be.Ec[0] == pytest.approx(be.Ec[1])
        assert be.Ec[2] == pytest.approx(be.Ec[3])

    def test_zero_density_clamped(self):
        """n=0/p=0 must not blow up the log (clamped to 1)."""
        mesh = _make_mesh(nx=3)
        phi = np.zeros(3)
        n = np.zeros(3)
        p = np.zeros(3)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": phi, "n": n, "p": p})
        assert np.all(np.isfinite(be.Efn))
        assert np.all(np.isfinite(be.Efp))

    def test_as_dict_keys(self):
        mesh = _make_mesh(nx=2)
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": np.zeros(2), "n": np.full(2, 1e23),
                              "p": np.full(2, 1e23)})
        d = be.as_dict()
        assert set(d) == {"Evac", "Ec", "Ev", "Efn", "Efp"}


# ===========================================================================
# 3. band_diagram_1d (cutline view)
# ===========================================================================

class TestBandCutline1d:
    def test_cutline_shape(self):
        mesh = _make_mesh(nx=6, ny=2, nz=2)
        sim = _FakeSim(mesh)
        bc = band_diagram_1d(sim, {"phi": np.zeros(mesh.npts()),
                                   "n": np.full(mesh.npts(), 1e23),
                                   "p": np.full(mesh.npts(), 1e23)},
                            j=1, k=1)
        assert isinstance(bc, BandCutline)
        assert len(bc.x) == 6
        assert len(bc.Ec) == 6
        for name in ("Evac", "Ec", "Ev", "Efn", "Efp"):
            assert len(getattr(bc, name)) == 6

    def test_cutline_matches_full_field_at_jk(self):
        """The cutline values equal the full field indexed at (j,k)."""
        mesh = _make_mesh(nx=4, ny=2, nz=1)
        sim = _FakeSim(mesh)
        phi = np.linspace(0.0, 0.4, mesh.npts())
        be = band_edges(sim, {"phi": phi, "n": np.full(mesh.npts(), 1e23),
                              "p": np.full(mesh.npts(), 1e23)})
        j, k = 1, 0
        _, line = cutline_x_at_jk(mesh, j, k)
        bc = band_diagram_1d(sim, {"phi": phi, "n": np.full(mesh.npts(), 1e23),
                                   "p": np.full(mesh.npts(), 1e23)}, j=j, k=k)
        np.testing.assert_allclose(bc.Ec, be.Ec[line])

    def test_chi_fallback_default_when_missing(self):
        """Mesh without a chi field uses the Si default 4.05."""
        mesh = StructuredGrid(((0.0, 1.0), (0.0, 0.1), (0.0, 0.1)), 3, 1, 1)
        # No chi field; no device fallback either.
        sim = _FakeSim(mesh)
        be = band_edges(sim, {"phi": np.zeros(3), "n": np.full(3, 1e23),
                              "p": np.full(3, 1e23)})
        np.testing.assert_allclose(be.Ec, -4.05)


# ===========================================================================
# 4. Slow integration: a real MOSFET band cutline bends in the channel
# ===========================================================================

@slow
class TestBandEdgesSolver:
    def test_mosfet_ec_bends_under_gate(self):
        """A gated MOSFET at Vg>0 shows Ec bending in the channel region."""
        from tcad.search.grammar import tree_from_template, build
        from tcad.simulator import simulate_sweep

        tree = tree_from_template("mosfet", W=40e-9, Lg=50e-9)
        dev = build(tree)
        dev.contacts["drain"] = (dev.contacts["drain"][0], 0.1)
        sim, results = simulate_sweep(
            dev, sweep_contacts={"gate": np.linspace(0.0, 0.4, 6)},
            resolution=(10e-9, 5e-9, 10e-9), quantum=False,
            max_iter=50, tol=1e-7, verbose=False,
        )
        # Last point = strongest gate bias -> largest band bending.
        bc = band_diagram_1d(sim, results[-1], j=0, k=0)
        # Ec should not be flat across the channel: the peak-to-peak swing
        # exceeds a small threshold (the gate bends the bands).
        swing = float(np.ptp(bc.Ec))
        assert swing > 1e-3, f"Ec too flat (swing={swing} eV); bands did not bend"
        assert np.all(np.isfinite(bc.Ec))
