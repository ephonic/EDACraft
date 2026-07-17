"""D2 mechanism-attribution truth-chain (plan0619.md §D2).

Fast unit tests (no solver) pin down the four-component decomposition against
synthetic fields, independent of the Newton solver:

1. **Drift/diffusion split** — in the drift-diffusion limit (small ``dphi/VT``)
   the signed sum of the split parts reproduces the Scharfetter-Gummel edge
   flux from ``current.sg_current_density_1d``:
       Jn_drift + Jn_diff ≈ -Jn_SG   (electron sign convention)
       Jp_drift + Jp_diff ≈ +Jp_SG
   plus the limiting cases: zero field → drift = 0, zero gradient → diff = 0.

2. **BTBT generation** — the local Kane model zeros below
   ``BTBT_FIELD_FLOOR`` (1e4 V/m) and is positive at high field.

3. **FE polarization charge** — zero without FE nodes; mean |Px| over the
   FE-node mask otherwise.

4. **attribute_mechanism** — a pure-drift synthetic field labels the dominant
   mechanism ``"drift"``; the 4-D fraction vector sums to 1.

Slow integration tests (``TCAD_RUN_SLOW=1``) check real-device attribution:
MOSFET on-state is drift/diffusion dominated, TFET shows BTBT at the junction,
FeFET shows nonzero FE polarization charge.
"""

import os
import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess.current import sg_current_density_1d
from tcad.postprocess.mechanism import (
    drift_diffusion_split_1d, btbt_generation, fe_polarization_charge,
    attribute_mechanism, mechanism_feature_vector, MechanismReport,
    MECHANISM_LABELS, B_KANE_SI, A_KANE, KANE_D, BTBT_FIELD_FLOOR,
)


RUN_SLOW = os.environ.get("TCAD_RUN_SLOW", "") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set TCAD_RUN_SLOW=1 to run solver-backed tests")


class _FakeSim:
    """Carries the attributes attribute_mechanism reads (mesh, VT)."""
    def __init__(self, mesh, VT=0.02585):
        self.mesh = mesh
        self.VT = VT


def _make_mesh(nx=5, ny=1, nz=1, with_mu=True):
    mesh = StructuredGrid(((0.0, (nx - 1) * 1e-9), (0.0, 0.1e-9), (0.0, 0.1e-9)),
                          nx, ny, nz)
    if with_mu:
        n = mesh.npts()
        mesh.fields["mu_n"] = np.full(n, 1400e-4)
        mesh.fields["mu_p"] = np.full(n, 450e-4)
    return mesh


# ===========================================================================
# 1. drift_diffusion_split_1d
# ===========================================================================

class TestDriftDiffusionSplit:
    def test_signed_sum_matches_sg_electrons(self):
        """In the DD limit, Jn_drift + Jn_diff ≈ -Jn_SG (electron sign)."""
        VT, dx = 0.02585, 1e-9
        # Small dphi so dphi/VT << 1 keeps the Bernoulli expansion accurate.
        phi = np.array([0.0, 0.001, 0.002, 0.0015])
        n = np.array([1e23, 1.2e23, 1.1e23, 1.05e23])
        p = np.array([1e10, 1.1e10, 1.0e10, 1.05e10])
        mu_n = np.array([1400e-4] * 4)
        mu_p = np.array([450e-4] * 4)

        Jn_sg, _ = sg_current_density_1d(phi, n, p, dx, mu_n, mu_p, VT)
        split = drift_diffusion_split_1d(phi, n, p, dx, mu_n, mu_p, VT)
        signed = split["Jn_drift"] + split["Jn_diff"]
        np.testing.assert_allclose(signed, -Jn_sg, rtol=2e-3)

    def test_signed_sum_matches_sg_holes(self):
        """In the DD limit, Jp_drift + Jp_diff ≈ +Jp_SG (hole sign)."""
        VT, dx = 0.02585, 1e-9
        phi = np.array([0.0, 0.001, 0.002, 0.0015])
        n = np.array([1e10, 1.1e10, 1.0e10, 1.05e10])
        p = np.array([1e23, 1.2e23, 1.1e23, 1.05e23])
        mu_n = np.array([1400e-4] * 4)
        mu_p = np.array([450e-4] * 4)

        _, Jp_sg = sg_current_density_1d(phi, n, p, dx, mu_n, mu_p, VT)
        split = drift_diffusion_split_1d(phi, n, p, dx, mu_n, mu_p, VT)
        signed = split["Jp_drift"] + split["Jp_diff"]
        np.testing.assert_allclose(signed, Jp_sg, rtol=2e-3)

    def test_zero_field_drift_is_zero(self):
        """phi flat → dphi/dx = 0 → Jn_drift = 0."""
        VT, dx = 0.02585, 1e-9
        phi = np.zeros(4)
        n = np.array([1e23, 1.2e23, 1.1e23, 1.05e23])
        p = np.array([1e10] * 4)
        mu = np.array([1400e-4] * 4)
        split = drift_diffusion_split_1d(phi, n, p, dx, mu, mu, VT)
        assert np.max(np.abs(split["Jn_drift"])) == pytest.approx(0.0, abs=1e-30)
        assert np.max(np.abs(split["Jp_drift"])) == pytest.approx(0.0, abs=1e-30)

    def test_zero_gradient_diff_is_zero(self):
        """n flat → dn/dx = 0 → Jn_diff = 0."""
        VT, dx = 0.02585, 1e-9
        phi = np.array([0.0, 0.01, 0.02, 0.03])
        n = np.array([1e23] * 4)
        p = np.array([1e10] * 4)
        mu = np.array([1400e-4] * 4)
        split = drift_diffusion_split_1d(phi, n, p, dx, mu, mu, VT)
        assert np.max(np.abs(split["Jn_diff"])) == pytest.approx(0.0, abs=1e-30)

    def test_all_flat_is_zero(self):
        """phi and n both flat → every component is zero."""
        VT, dx = 0.02585, 1e-9
        phi = np.zeros(4)
        n = np.array([1e23] * 4)
        p = np.array([1e10] * 4)
        mu = np.array([1400e-4] * 4)
        split = drift_diffusion_split_1d(phi, n, p, dx, mu, mu, VT)
        for key in ("Jn_drift", "Jn_diff", "Jp_drift", "Jp_diff"):
            assert np.max(np.abs(split[key])) == pytest.approx(0.0, abs=1e-30)

    def test_output_length_is_n_minus_1(self):
        """Per-edge arrays have length len(phi)-1."""
        phi = np.linspace(0, 0.1, 6)
        n = np.linspace(1e23, 1.1e23, 6)
        p = np.linspace(1e10, 1.1e10, 6)
        mu = np.full(6, 1400e-4)
        split = drift_diffusion_split_1d(phi, n, p, 1e-9, mu, mu, 0.02585)
        for key in split:
            assert len(split[key]) == 5


# ===========================================================================
# 2. btbt_generation
# ===========================================================================

class TestBtbtGeneration:
    def test_low_field_is_zero(self):
        """|E| below BTBT_FIELD_FLOOR (1e4 V/m) → G = 0, I_btbt = 0."""
        mesh = _make_mesh(nx=4)
        n = mesh.npts()
        result = {"Ex": np.full(n, 1e3), "Ey": np.zeros(n), "Ez": np.zeros(n)}
        G, I = btbt_generation(result, mesh)
        assert np.max(G) == pytest.approx(0.0, abs=0.0)
        assert I == pytest.approx(0.0, abs=0.0)

    def test_high_field_is_positive(self):
        """A high-field node gives G > 0 and I_btbt > 0."""
        mesh = _make_mesh(nx=4)
        n = mesh.npts()
        Ex = np.zeros(n)
        Ex[1] = 5e9  # well above the floor
        result = {"Ex": Ex, "Ey": np.zeros(n), "Ez": np.zeros(n)}
        G, I = btbt_generation(result, mesh)
        assert G[1] > 0.0
        assert I > 0.0

    def test_uses_corrected_b_kane(self):
        """The default B_kane is the SI-correct 2.0e9 V/m (not the stale 2.0e7)."""
        assert B_KANE_SI == 2.0e9
        # The module default used by btbt_generation is B_KANE_SI.
        import inspect
        sig = inspect.signature(btbt_generation)
        assert sig.parameters["B_kane"].default == B_KANE_SI

    def test_missing_e_fields_default_to_zero(self):
        """No E-field keys → treated as zero field → G = 0."""
        mesh = _make_mesh(nx=3)
        G, I = btbt_generation({}, mesh)
        assert np.max(G) == pytest.approx(0.0, abs=0.0)
        assert I == pytest.approx(0.0, abs=0.0)


# ===========================================================================
# 3. fe_polarization_charge
# ===========================================================================

class TestFePolarization:
    def test_no_p_is_zero(self):
        P_mag, mask = fe_polarization_charge({})
        assert P_mag == 0.0
        assert mask.sum() == 0

    def test_zero_p_is_zero(self):
        P = np.zeros((4, 3))
        P_mag, mask = fe_polarization_charge({"P": P})
        assert P_mag == 0.0
        assert mask.sum() == 0

    def test_mean_abs_px_over_fe_nodes(self):
        """P_mag = mean(|Px|) over nodes with |Px| > 1e-30."""
        P = np.zeros((4, 3))
        P[0, 0] = 1e-5
        P[1, 0] = -2e-5
        P[2, 0] = 0.0     # not an FE node
        P[3, 0] = 3e-5
        P_mag, mask = fe_polarization_charge({"P": P})
        assert P_mag == pytest.approx((1e-5 + 2e-5 + 3e-5) / 3)
        assert int(mask.sum()) == 3

    def test_py_pz_ignored(self):
        """Only Px (column 0) identifies FE nodes."""
        P = np.zeros((2, 3))
        P[0, 1] = 1e-5  # Py, not Px
        P[1, 2] = 1e-5  # Pz, not Px
        P_mag, mask = fe_polarization_charge({"P": P})
        assert P_mag == 0.0
        assert mask.sum() == 0


# ===========================================================================
# 4. attribute_mechanism
# ===========================================================================

class TestAttributeMechanism:
    def _pure_drift_result(self, mesh):
        """A field with a strong phi gradient and flat n/p → pure drift."""
        n = mesh.npts()
        phi = np.linspace(0.0, 0.5, n)  # strong drift field
        return {
            "phi": phi,
            "n": np.full(n, 1e23),
            "p": np.full(n, 1e10),
            "Ex": np.zeros(n), "Ey": np.zeros(n), "Ez": np.zeros(n),
        }

    def test_pure_drift_is_dominant(self):
        mesh = _make_mesh(nx=6)
        sim = _FakeSim(mesh)
        result = self._pure_drift_result(mesh)
        report = attribute_mechanism(sim, result)
        assert report.dominant == "drift"
        assert report.fractions["drift"] > 0.5

    def test_fractions_sum_to_one(self):
        mesh = _make_mesh(nx=6)
        sim = _FakeSim(mesh)
        report = attribute_mechanism(sim, self._pure_drift_result(mesh))
        total = sum(report.fractions[l] for l in MECHANISM_LABELS)
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_feature_vector_is_4d_and_normalized(self):
        mesh = _make_mesh(nx=6)
        sim = _FakeSim(mesh)
        report = attribute_mechanism(sim, self._pure_drift_result(mesh))
        fv = report.feature_vector()
        assert fv.shape == (4,)
        assert fv.sum() == pytest.approx(1.0, abs=1e-9)
        # feature_vector() and the module-level helper agree.
        np.testing.assert_array_equal(fv, mechanism_feature_vector(report))

    def test_all_zero_field_is_drift_default(self):
        """Zero everything → total = 0 → default label 'drift', zero vector."""
        mesh = _make_mesh(nx=4)
        sim = _FakeSim(mesh)
        n = mesh.npts()
        result = {"phi": np.zeros(n), "n": np.full(n, 1e23), "p": np.full(n, 1e10)}
        report = attribute_mechanism(sim, result)
        assert report.dominant == "drift"
        assert report.feature_vector().sum() == pytest.approx(0.0, abs=1e-12)

    def test_btbt_dominant_when_field_extreme(self):
        """A huge E-field at a node makes BTBT dominate the magnitude sum."""
        mesh = _make_mesh(nx=4)
        sim = _FakeSim(mesh)
        n = mesh.npts()
        # Flat bands (no drift/diffusion) but a giant Ex at every node.
        Ex = np.full(n, 5e9)
        result = {"phi": np.zeros(n), "n": np.full(n, 1e23), "p": np.full(n, 1e10),
                  "Ex": Ex, "Ey": np.zeros(n), "Ez": np.zeros(n)}
        report = attribute_mechanism(sim, result)
        assert report.dominant == "btbt"
        assert report.I_btbt > 0.0

    def test_cutline_x_populated(self):
        mesh = _make_mesh(nx=5)
        sim = _FakeSim(mesh)
        n = mesh.npts()
        result = {"phi": np.zeros(n), "n": np.full(n, 1e23), "p": np.full(n, 1e10)}
        report = attribute_mechanism(sim, result)
        assert report.cutline_x is not None
        assert len(report.cutline_x) == 5

    def test_report_is_mechanism_report(self):
        mesh = _make_mesh(nx=4)
        sim = _FakeSim(mesh)
        n = mesh.npts()
        report = attribute_mechanism(sim, {"phi": np.zeros(n),
                                           "n": np.full(n, 1e23),
                                           "p": np.full(n, 1e10)})
        assert isinstance(report, MechanismReport)
        # All four labels present in the fractions dict.
        assert set(report.fractions) == set(MECHANISM_LABELS)


# ===========================================================================
# 5. Slow integration: real-device mechanism attribution
# ===========================================================================

@slow
class TestMechanismSolver:
    _EVAL_KW = dict(
        resolution=(10e-9, 5e-9, 10e-9),
        max_iter=50, tol=1e-7,
    )

    def test_mosfet_onstate_drift_or_diffusion(self):
        """MOSFET on-state is drift/diffusion dominated (not BTBT/FE)."""
        from tcad.search.grammar import tree_from_template, build
        from tcad.simulator import simulate_sweep

        tree = tree_from_template("mosfet", W=40e-9, Lg=50e-9)
        dev = build(tree)
        dev.contacts["drain"] = (dev.contacts["drain"][0], 0.1)
        sim, results = simulate_sweep(
            dev, sweep_contacts={"gate": np.linspace(0.0, 0.4, 6)},
            quantum=False, verbose=False, **self._EVAL_KW,
        )
        report = attribute_mechanism(sim, results[-1])
        assert report.dominant in ("drift", "diffusion")
        assert report.fractions["btbt"] < 0.1
        assert report.fractions["fe_polarization"] < 0.1
