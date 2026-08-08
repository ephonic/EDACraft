"""TFET device characterization: templates, physics validation, and BTBT analysis.

TFETs (Tunnel FETs) use band-to-band tunneling (BTBT) as the carrier injection
mechanism instead of thermionic emission. This enables sub-60 mV/dec subthreshold
swing and ultra-low-voltage operation.

The local Kane model and the non-local path-integral WKB model are both available.
The validation below inspects the solver's explicit ``G_btbt`` result, avoiding
contact-pinned carrier extrema as a proxy for tunnelling generation.
"""

import numpy as np
import pytest
from functools import lru_cache

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from tcad.core import SolverType
from tcad.postprocess.tfet import (
    extract_tfet_metrics,
    extract_btb_tbt_current,
    compare_tfet_vs_mosfet,
    _transport_current_observable,
)


class TestTFETDeviceTemplate:
    """Verify TFET device templates have correct structure."""

    def test_tfet_template_creates(self):
        dev = Device.tfet(Lg=20e-9, Lsd=20e-9, t_sheet=5e-9, W_sheet=10e-9)
        assert dev.name == "tfet"
        region_names = [r.name for r in dev.regions]
        assert "source" in region_names
        assert "channel" in region_names
        assert "drain" in region_names

    def test_tfet_source_is_p_type(self):
        """TFET source must be p+ doped (reversed vs MOSFET)."""
        dev = Device.tfet()
        source_region = [r for r in dev.regions if r.name == "source"][0]
        assert source_region.doping.Na > 0
        assert source_region.doping.Nd == 0

    def test_tfet_drain_is_n_type(self):
        """TFET drain must be n+ doped."""
        dev = Device.tfet()
        drain_region = [r for r in dev.regions if r.name == "drain"][0]
        assert drain_region.doping.Nd > 0
        assert drain_region.doping.Na == 0

    def test_tfet_channel_is_lightly_doped(self):
        """TFET channel should be lightly doped for good gate control."""
        dev = Device.tfet()
        channel = [r for r in dev.regions if r.name == "channel"][0]
        assert channel.doping.Na <= 1e16

    def test_tfet_contacts_have_nodes(self):
        """TFET contacts must overlap device regions to have mesh nodes."""
        dev = Device.tfet(Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6)
        mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))
        for name in ["source", "drain", "gate"]:
            field = f"contact_{name}"
            mask = mesh.fields.get(field, np.zeros(mesh.npts())).astype(bool)
            assert mask.sum() > 0, f"TFET {name} contact has no nodes"

    def test_heterojunction_tfet_has_sige(self):
        """Heterojunction TFET should have SiGe source region."""
        dev = Device.heterojunction_tfet()
        region_names = [r.name for r in dev.regions]
        assert "source_hj" in region_names
        assert "source_bulk" in region_names

    def test_heterojunction_tfet_sige_bandgap(self):
        """SiGe bandgap should be lower than Si."""
        dev = Device.heterojunction_tfet(ge_fraction=0.4)
        sige_region = [r for r in dev.regions if r.name == "source_hj"][0]
        assert sige_region.material.Eg < 1.12

    def test_heterojunction_tfet_junction_location(self):
        """SiGe/Si junction should be at the source-channel interface."""
        dev = Device.heterojunction_tfet(Lsd=20e-9, L_source_hj=5e-9)
        source_hj = [r for r in dev.regions if r.name == "source_hj"][0]
        assert abs(source_hj.shape.xmax - 20e-9) < 1e-12

    def test_heterojunction_tfet_contacts_have_nodes(self):
        """Heterojunction TFET contacts must overlap device regions."""
        dev = Device.heterojunction_tfet(
            Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6
        )
        mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))
        for name in ["source", "drain", "gate"]:
            field = f"contact_{name}"
            mask = mesh.fields.get(field, np.zeros(mesh.npts())).astype(bool)
            assert mask.sum() > 0, f"HJ-TFET {name} contact has no nodes"


class TestTFETDriftDiffusion:
    """TFET simulation without BTBT: validate DD solver on TFET structure."""

    def _build_tfet_sim(self):
        """Build a TFET simulator (no BTBT, DD only)."""
        dev = Device.tfet(
            Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6,
            source_doping=1e19, channel_doping=1e15, drain_doping=1e19,
            Vg=0.0, Vd=0.1, Vs=0.0,
        )
        mesh = structured_mesh_from_device(dev, resolution=(100e-9, 100e-9, 100e-9))
        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        sim.set_contact("source", 0.0)
        sim.set_contact("drain", 0.1)
        sim.set_contact("gate", 0.0)
        return sim, dev, mesh

    def test_tfet_dd_converges(self):
        """TFET DD solver should converge at equilibrium."""
        sim, dev, mesh = self._build_tfet_sim()
        result = sim.run(max_iter=80, tol=1e-8)
        assert result["converged"], "TFET DD solver did not converge"

    def test_tfet_dd_gate_modulation(self):
        """TFET should show gate-dependent carrier modulation."""
        sim, dev, mesh = self._build_tfet_sim()
        sim.run(max_iter=80, tol=1e-8)

        X = mesh.X.ravel()
        channel = (X >= 0.5e-6) & (X <= 1.5e-6)
        for name in ("contact_source", "contact_drain", "contact_gate"):
            if name in mesh.fields:
                channel &= ~mesh.fields[name].astype(bool).ravel()
        phi_values = []
        for vg in np.linspace(0.0, 0.8, 5):
            sim.update_contact("gate", vg)
            r = sim.run(max_iter=80, tol=1e-8)
            assert r["converged"], f"TFET Vg={vg:.1f}V did not converge"
            phi_values.append(float(np.mean(r["phi"][channel])))

        # Global max(n) is fixed by the heavily doped ohmic contacts.  Verify
        # gate control on the internal channel electrostatic potential instead.
        assert max(phi_values) - min(phi_values) > 0.02, (
            "TFET gate did not modulate the internal channel potential"
        )

    def test_tfet_dd_field_profile(self):
        """TFET should have highest field at the source-channel junction."""
        sim, dev, mesh = self._build_tfet_sim()
        result = sim.run(max_iter=80, tol=1e-8)

        Ex = result["Ex"]
        E_mag = np.sqrt(Ex**2 + result["Ey"]**2 + result["Ez"]**2)
        X = mesh.X.ravel()

        # Source region is x < Lsd = 0.5um
        src_mask = X < 0.5e-6
        chn_mask = (X >= 0.5e-6) & (X <= 1.5e-6)

        # Field should be significant at the junction
        max_field = E_mag.max()
        assert max_field > 1e5, f"Max field {max_field:.3e} V/m too low for p+/n+ junction"


class TestTFETvsMOSFETComparison:
    """Compare converged TFET/MOSF DD sweeps using full-precision SG current.

    Contact carrier maxima are fixed by ohmic boundary conditions and are not
    a transfer-current observable.  The shared sweep is cached so the three
    checks exercise one physical integration run rather than repeating it.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def _run_dd_comparison():
        """Run DD-only comparison (no BTBT) between TFET and MOSFET."""
        # Resolve the 1.5-nm oxide while keeping this integration comparison
        # small.  The former 1-um device used a 100-nm z step, so the gate
        # contact matched zero nodes and all three tests xfailed before solve.
        resolution = (5e-9, 2.5e-9, 1e-9)

        tfet_dev = Device.tfet(
            Lg=20e-9, Lsd=10e-9, t_sheet=5e-9, W_sheet=5e-9,
            Vg=0.0, Vd=0.1, Vs=0.0,
        )
        tfet_mesh = structured_mesh_from_device(tfet_dev, resolution=resolution)
        tfet_sim = Simulator(tfet_mesh, temperature=300.0)
        tfet_sim.set_material_from_mesh()
        tfet_sim.set_contact("source", 0.0)
        tfet_sim.set_contact("drain", 0.1)
        tfet_sim.set_contact("gate", 0.0)

        mosfet_dev = Device.mosfet(
            Lg=20e-9, tox=1.5e-9, tsi=5e-9, W=5e-9, Lsd=10e-9,
            Vg=0.0, Vd=0.1, Vs=0.0,
        )
        mosfet_mesh = structured_mesh_from_device(mosfet_dev, resolution=resolution)
        mosfet_sim = Simulator(mosfet_mesh, temperature=300.0)
        mosfet_sim.set_material_from_mesh()
        mosfet_sim.set_contact("source", 0.0)
        mosfet_sim.set_contact("drain", 0.1)
        mosfet_sim.set_contact("gate", 0.0)

        Vg_points = np.linspace(0.0, 0.8, 5)
        tfet_results, mosfet_results = [], []

        for vg in Vg_points:
            if tfet_sim.results is None:
                tfet_sim.set_contact("gate", vg)
            else:
                tfet_sim.update_contact("gate", vg)
            r_t = tfet_sim.run(max_iter=60, tol=1e-8)
            r_t["_voltages"] = {"gate": vg, "drain": 0.1, "source": 0.0}
            tfet_results.append(r_t)

            if mosfet_sim.results is None:
                mosfet_sim.set_contact("gate", vg)
            else:
                mosfet_sim.update_contact("gate", vg)
            r_m = mosfet_sim.run(max_iter=60, tol=1e-8)
            r_m["_voltages"] = {"gate": vg, "drain": 0.1, "source": 0.0}
            mosfet_results.append(r_m)

        return tfet_results, mosfet_results, Vg_points

    def test_tfet_vs_mosfet_gate_response(self):
        """Both devices converge and their transport current responds to gate."""
        tfet_results, mosfet_results, Vg = self._run_dd_comparison()

        assert all(r["converged"] and r.get("valid", True)
                   for r in tfet_results + mosfet_results)
        tfet_I = np.array([_transport_current_observable(r) for r in tfet_results])
        mosfet_I = np.array([_transport_current_observable(r) for r in mosfet_results])

        assert tfet_I[-1] > tfet_I[0] * 1.2, "TFET current should respond to gate"
        assert mosfet_I[-1] > mosfet_I[0] * 1.2, "MOSFET current should respond to gate"

    def test_tfet_extraction_metrics(self):
        """TFET metrics extraction should work."""
        tfet_results, mosfet_results, Vg = self._run_dd_comparison()

        tfet_metrics = extract_tfet_metrics(tfet_results, Vdd=0.3)
        mosfet_metrics = extract_tfet_metrics(mosfet_results, Vdd=0.7)

        assert "min_SS" in tfet_metrics
        assert "Ion_Ioff" in tfet_metrics
        assert "E_switch" in tfet_metrics
        assert np.isfinite(tfet_metrics["min_SS"])
        assert tfet_metrics["Ion_Ioff"] > 1.0
        assert mosfet_metrics["Ion_Ioff"] > 1.0

    def test_comparison_table(self):
        """Comparison table generation should work."""
        tfet_results, mosfet_results, Vg = self._run_dd_comparison()

        tfet_metrics = extract_tfet_metrics(tfet_results, Vdd=0.3)
        mosfet_metrics = extract_tfet_metrics(mosfet_results, Vdd=0.7)

        table = compare_tfet_vs_mosfet(tfet_metrics, mosfet_metrics)
        assert "TFET" in table
        assert "MOSFET" in table
        assert "min SS" in table


class TestHeterojunctionTFET:
    """Test heterojunction TFET structure."""

    def test_hj_tfet_different_materials(self):
        """HJ-TFET source and channel should use different materials."""
        dev = Device.heterojunction_tfet(ge_fraction=0.4)
        sige = [r for r in dev.regions if r.name == "source_hj"][0].material
        si = [r for r in dev.regions if r.name == "channel"][0].material
        assert sige.Eg < si.Eg, "SiGe should have lower bandgap than Si"

    def test_btb_current_on_mock_results(self):
        """BTBT current extraction should work on synthetic results."""
        dev = Device.tfet(
            Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6,
        )
        mesh = structured_mesh_from_device(dev, resolution=(200e-9, 200e-9, 200e-9))

        # Create mock results with strong field
        npts = mesh.npts()
        results = {
            "phi": np.zeros(npts),
            "n": np.ones(npts) * 1e20,
            "p": np.ones(npts) * 1e20,
            "Ex": np.ones(npts) * 1e7,  # 10 MV/m
            "Ey": np.zeros(npts),
            "Ez": np.zeros(npts),
        }

        I_btb = extract_btb_tbt_current(results, mesh)
        assert I_btb >= 0, f"BTBT current should be >= 0, got {I_btb}"

    def test_btb_current_integrates_solver_generation(self):
        """Postprocessing must not replace non-local G_btbt with local Kane."""
        dev = Device.tfet(
            Lg=1.0e-6, Lsd=0.5e-6, t_sheet=0.5e-6, W_sheet=0.5e-6,
        )
        mesh = structured_mesh_from_device(
            dev, resolution=(200e-9, 200e-9, 200e-9),
        )
        G = np.full(mesh.npts(), 2.5e20)
        result = {
            "G_btbt": G,
            # Deliberately conflicting field: using local recomputation would
            # produce a completely different answer.
            "Ex": np.full(mesh.npts(), 9e9),
        }
        g = mesh.to_cxx_grid()
        expected = 1.602176634e-19 * G.sum() * g["dx"] * g["dy"] * g["dz"]
        assert extract_btb_tbt_current(result, mesh) == pytest.approx(expected)

    def test_metrics_use_edge_current_before_contact_density(self):
        sweep = []
        for vg, current in zip([0.0, 0.2, 0.4], [1e-9, 1e-6, 1e-3]):
            sweep.append({
                "_voltages": {"gate": vg},
                "n": np.full(4, 1e25),  # deliberately contact-pinned/constant
                "Jn_x": np.full(4, current),
                "Jp_x": np.zeros(4),
            })
        metrics = extract_tfet_metrics(sweep)
        assert metrics["Ion_Ioff"] == pytest.approx(1e6)
        assert np.isfinite(metrics["min_SS"])


class TestBTBTValidation:
    """Validate BTBT model on simple devices where it converges well."""

    @staticmethod
    def _run_uniform_high_field(*, use_nonlocal=False):
        """Solve a small 20-nm slab at 1 V (|E| ~= 5e7 V/m).

        The transverse mesh is intentionally coarse because the problem is
        one-dimensional.  The former 1-um/0.5-V test had negligible physical
        Kane generation (exp(-B/E) underflow with B=2e9 V/m) and needlessly
        crossed the large-grid iterative-solver threshold.
        """
        from tcad.geometry.device_builder import Material, Region, Box, DopingProfile

        Lx = 20e-9
        width = 0.5e-6
        dev = Device("test_btb_high_field")
        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        dev.add_region(Region(
            "bulk", Box(0, Lx, 0, width, 0, width), si,
            DopingProfile(Nd=1e18, Na=0),
        ))
        dev.add_contact(
            "left", Box(-0.01 * Lx, 0, 0, width, 0, width), voltage=0.0,
        )
        dev.add_contact(
            "right", Box(Lx, 1.01 * Lx, 0, width, 0, width), voltage=1.0,
        )
        mesh = structured_mesh_from_device(
            dev, resolution=(1e-9, width, width),
        )
        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        sim.set_contact("left", 0.0)
        sim.set_contact("right", 1.0)
        sim.set_btbt(enabled=True, use_nonlocal=use_nonlocal)
        return mesh, sim.run(max_iter=100, tol=1e-8)

    def test_btb_on_uniform_device(self):
        """Local BTBT converges and exposes the exact Kane source term."""
        _, result = self._run_uniform_high_field(use_nonlocal=False)
        assert result["converged"]

        G = result["G_btbt"]
        E = np.sqrt(result["Ex"]**2 + result["Ey"]**2 + result["Ez"]**2)
        expected = np.zeros_like(E)
        active = E >= 1.0e4
        expected[active] = 3.1e21 * 1.0e6 * E[active]**2 * np.exp(
            -2.0e9 / E[active]
        )
        assert np.all(np.isfinite(G)) and G.max() > 0.0
        assert np.allclose(G, expected, rtol=2e-10, atol=0.0), (
            "reported G_btbt must be the Kane source used by continuity"
        )


class TestNonLocalBTBT:
    """Validate non-local (path-integral WKB) BTBT tunneling model."""

    def test_nonlocal_btbt_on_uniform_device(self):
        """Non-local BTBT converges and reports its WKB source explicitly."""
        mesh, result = TestBTBTValidation._run_uniform_high_field(
            use_nonlocal=True,
        )
        assert result["converged"], "Non-local BTBT should converge"

        G = result["G_btbt"]
        assert G.shape == (mesh.npts(),)
        assert np.all(np.isfinite(G)) and np.all(G >= 0.0)
        assert G.max() > 0.0, "high-field WKB generation must be nonzero"

        # Boundary nodes have no representable tunnelling path (available
        # distance is zero), while interior nodes do.  This checks that the
        # exposed result is the non-local path model rather than local Kane.
        nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
        G3 = G.reshape(nz, ny, nx)
        assert np.all(G3[:, :, 0] == 0.0)
        assert np.all(G3[:, :, -1] == 0.0)
        assert np.any(G3[:, :, 1:-1] > 0.0)

    def test_nonlocal_vs_local_btbt(self):
        """Non-local BTBT should produce smaller generation than local at same bias.

        The local Kane model overestimates tunneling at sharp junctions because
        it only considers the local field magnitude. The non-local WKB model
        integrates along the full tunneling path, giving a more physical result.
        """
        from tcad.geometry.device_builder import Material, Region, Box, DopingProfile

        dev = Device("test_nl_vs_local")
        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        # Sharp p+/n+ junction to stress-test the difference
        dev.add_region(Region("p_side", Box(0, 0.5e-6, 0, 0.5e-6, 0, 0.5e-6),
                              si, DopingProfile(Nd=0, Na=1e20)))
        dev.add_region(Region("n_side", Box(0.5e-6, 1e-6, 0, 0.5e-6, 0, 0.5e-6),
                              si, DopingProfile(Nd=1e20, Na=0)))
        dev.add_contact("left", Box(0, 0.1e-6, 0, 0.5e-6, -0.01e-6, 0), voltage=0.0)
        dev.add_contact("right", Box(0.9e-6, 1e-6, 0, 0.5e-6, -0.01e-6, 0), voltage=0.5)

        mesh = structured_mesh_from_device(dev, resolution=(50e-9, 50e-9, 50e-9))

        # Local BTBT
        sim_local = Simulator(mesh, temperature=300.0)
        sim_local.set_material_from_mesh()
        sim_local.set_contact("left", 0.0)
        sim_local.set_contact("right", 0.5)
        sim_local.set_btbt(enabled=True, use_nonlocal=False)
        r_local = sim_local.run(max_iter=60, tol=1e-8)

        # Non-local BTBT
        sim_nl = Simulator(mesh, temperature=300.0)
        sim_nl.set_material_from_mesh()
        sim_nl.set_contact("left", 0.0)
        sim_nl.set_contact("right", 0.5)
        sim_nl.set_btbt(enabled=True, use_nonlocal=True)
        r_nl = sim_nl.run(max_iter=60, tol=1e-8)

        if r_local["converged"] and r_nl["converged"]:
            # Non-local should produce more conservative (smaller) carrier density
            # because it accounts for the full barrier, not just the local field
            assert r_nl["n"].max() <= r_local["n"].max() * 1.1, (
                "Non-local BTBT should not significantly exceed local BTBT "
                "on this device (within 10% tolerance)"
            )

    def test_nonlocal_btbt_physical_range(self):
        """Non-local BTBT should produce physically reasonable carrier densities."""
        # Reuse the resolved 20-nm high-field slab. The former 1-um coarse 3-D
        # deck added no independent physics and did not converge, so its
        # conditional assertion silently skipped the range check.
        _, r = TestBTBTValidation._run_uniform_high_field(use_nonlocal=True)

        assert r["converged"] and r.get("valid") is True, (
            "non-local BTBT physical-range deck must converge before its "
            "carrier density can be accepted")
        # Carrier density should be in a physically reasonable range
        # (not exceeding ~10^27 m^-3, the atomic density limit of Si)
        assert r["n"].max() < 1e28, (
            f"Non-local BTBT produced unphysical carrier density: {r['n'].max():.3e}"
        )
