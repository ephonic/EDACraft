"""NDR tunnel diode: device template, physics validation, and metrics extraction."""

import numpy as np
import pytest

from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad.simulator import Simulator
from tcad.postprocess.ndr import extract_btb_current, extract_ndr_metrics, plot_ndr_curve


class TestTunnelDiodeTemplate:
    """Verify tunnel diode device templates have correct structure."""

    def test_tunnel_diode_creates(self):
        dev = Device.tunnel_diode()
        assert dev.name == "tunnel_diode"
        region_names = [r.name for r in dev.regions]
        assert "p_side" in region_names
        assert "n_side" in region_names

    def test_tunnel_diode_p_is_heavily_doped(self):
        """p+ region should have degenerate acceptor doping."""
        dev = Device.tunnel_diode()
        p_region = [r for r in dev.regions if r.name == "p_side"][0]
        assert p_region.doping.Na > 1e19
        assert p_region.doping.Nd == 0

    def test_tunnel_diode_n_is_heavily_doped(self):
        """n+ region should have degenerate donor doping."""
        dev = Device.tunnel_diode()
        n_region = [r for r in dev.regions if r.name == "n_side"][0]
        assert n_region.doping.Nd > 1e19
        assert n_region.doping.Na == 0

    def test_tunnel_diode_has_two_contacts(self):
        """Tunnel diode is a 2-terminal device."""
        dev = Device.tunnel_diode()
        assert "anode" in dev.contacts
        assert "cathode" in dev.contacts
        assert len(dev.contacts) == 2

    def test_tunnel_diode_contacts_have_nodes(self):
        """Contacts must overlap device regions."""
        dev = Device.tunnel_diode(Lp=50e-9, Ln=50e-9, W=50e-9, H=50e-9)
        mesh = structured_mesh_from_device(dev, resolution=(10e-9, 10e-9, 10e-9))
        for name in ["anode", "cathode"]:
            field = f"contact_{name}"
            mask = mesh.fields.get(field, np.zeros(mesh.npts())).astype(bool)
            assert mask.sum() > 0, f"Tunnel diode {name} contact has no nodes"

    def test_tunnel_diode_custom_doping(self):
        """Custom doping levels should be applied."""
        dev = Device.tunnel_diode(Na=1e21, Nd=2e20)
        p_region = [r for r in dev.regions if r.name == "p_side"][0]
        n_region = [r for r in dev.regions if r.name == "n_side"][0]
        assert p_region.doping.Na == 1e21
        assert n_region.doping.Nd == 2e20


class TestNDRPhysics:
    """Validate NDR physics in tunnel diode simulations."""

    def _run_bias_sweep(self, v_max=0.3, n_steps=8):
        """Run forward bias sweep on a tunnel diode."""
        dev = Device.tunnel_diode(
            Lp=40e-9, Ln=40e-9, W=40e-9, H=40e-9,
            Na=5e20, Nd=5e20,
        )
        mesh = structured_mesh_from_device(dev, resolution=(8e-9, 8e-9, 8e-9))

        sim = Simulator(mesh, temperature=300.0)
        sim.set_material_from_mesh()
        sim.set_contact("anode", 0.0)
        sim.set_contact("cathode", 0.0)
        sim.set_btbt(enabled=True, use_nonlocal=True)

        V_points = np.linspace(0.0, v_max, n_steps)
        results = []

        for v in V_points:
            if sim.results is None:
                sim.set_contact("cathode", v)
            else:
                sim.update_contact("cathode", v)
            r = sim.run(max_iter=80, tol=1e-8)
            r["_voltages"] = {"cathode": v, "anode": 0.0}
            results.append(r)

        return results, mesh

    def test_tunnel_diode_converges(self):
        """Tunnel diode DD+BTBT solver should converge."""
        results, mesh = self._run_bias_sweep(v_max=0.2, n_steps=4)
        for i, r in enumerate(results):
            assert r["converged"], f"Bias step {i} did not converge"

    def test_tunnel_diode_gate_modulation(self):
        """Tunnel diode should show bias-dependent carrier response."""
        results, mesh = self._run_bias_sweep(v_max=0.3, n_steps=6)

        n_values = [r["n"].max() for r in results]
        # Should show variation with bias (not flat)
        assert max(n_values) > min(n_values) * 1.05, (
            "Tunnel diode should show bias-dependent carrier density"
        )

    def test_tunnel_diode_field_at_junction(self):
        """Tunnel diode should have strong field at the p+/n+ junction."""
        results, mesh = self._run_bias_sweep(v_max=0.1, n_steps=3)

        r = results[-1]
        Ex = r["Ex"]
        E_mag = np.sqrt(Ex**2 + r["Ey"]**2 + r["Ez"]**2)

        # Heavy doping should create strong junction field
        max_field = E_mag.max()
        assert max_field > 1e6, f"Max field {max_field:.3e} V/m too low for degenerate junction"


class TestNDRMetrics:
    """Validate NDR metrics extraction."""

    def test_btb_current_on_mock_results(self):
        """BTBT current extraction should work on synthetic results."""
        dev = Device.tunnel_diode(Lp=40e-9, Ln=40e-9, W=40e-9, H=40e-9)
        mesh = structured_mesh_from_device(dev, resolution=(10e-9, 10e-9, 10e-9))

        npts = mesh.npts()
        results = {
            "phi": np.zeros(npts),
            "n": np.ones(npts) * 1e20,
            "p": np.ones(npts) * 1e20,
            "Ex": np.ones(npts) * 1e7,
            "Ey": np.zeros(npts),
            "Ez": np.zeros(npts),
        }

        I_btb = extract_btb_current(results, mesh)
        assert I_btb >= 0, f"BTBT current should be >= 0, got {I_btb}"

    def test_ndr_metrics_extraction(self):
        """NDR metrics extraction should work on synthetic I-V data."""
        # Create synthetic NDR-like data: peak then valley
        V = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30])
        I = np.array([1e18, 5e19, 1e21, 5e20, 2e19, 1e19, 5e19])  # NDR at 0.10-0.25V

        results = []
        for v, i in zip(V, I):
            results.append({
                "n": np.ones(100) * i,
                "_voltages": {"cathode": v},
            })

        metrics = extract_ndr_metrics(results, contact_name="cathode")
        assert "Vp" in metrics
        assert "Ip" in metrics
        assert "Vv" in metrics
        assert "Iv" in metrics
        assert "PVR" in metrics
        assert metrics["PVR"] > 1.0, "PVR should be > 1 for NDR behavior"

    @pytest.mark.skip(reason="matplotlib font rendering causes bus error on this system")
    def test_ndr_plot_generation(self):
        """NDR plot generation should not crash."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        V = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 0.25])
        I = np.array([1e18, 5e19, 1e21, 5e20, 2e19, 1e19])

        results = []
        for v, i in zip(V, I):
            results.append({
                "n": np.ones(100) * i,
                "_voltages": {"cathode": v},
            })

        ax = plot_ndr_curve(results, contact_name="cathode")
        assert ax is not None
        plt.close("all")
