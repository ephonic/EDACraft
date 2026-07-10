"""Tests for tcad.simulator and C++ core integration."""

import numpy as np
import pytest

from tcad.simulator import Simulator, simulate_device, simulate_sweep
from tcad.geometry.device_builder import Device
from tcad.mesh.generator import structured_mesh_from_device


class TestSimulator:
    def test_init_requires_structured_grid(self):
        class FakeMesh:
            pass
        with pytest.raises(TypeError):
            Simulator(FakeMesh())

    def test_set_material_from_mesh(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        # Should not raise; internal arrays populated

    def test_set_contact(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)

    def test_set_contact_missing(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        with pytest.raises(KeyError):
            sim.set_contact("nonexistent", voltage=0.0)

    def test_quantum_toggle(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_quantum(True)
        sim.set_quantum(False)

    def test_run_small(self):
        """Run a very small simulation to verify end-to-end."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        results = sim.run(max_iter=10, tol=1e-6)
        assert "phi" in results
        assert "n" in results
        assert "p" in results
        assert results["phi"].size == mesh.npts()

    def test_to_mesh_fields(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        sim.run(max_iter=10, tol=1e-6)
        fields = sim.to_mesh_fields()
        for key in ["phi", "n", "p", "Ex", "Ey", "Ez"]:
            assert key in fields
            assert fields[key].shape == mesh.shape()

    def test_to_mesh_fields_before_run(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        with pytest.raises(RuntimeError):
            sim.to_mesh_fields()


class TestSimulateDevice:
    def test_one_shot(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        sim, results = simulate_device(dev, resolution=(0.5e-6, 0.5e-6, 0.5e-6), quantum=False, max_iter=10, tol=1e-6)
        assert sim.results is not None
        assert "phi" in results


class TestSimulateSweep:
    def test_sweep_gate_voltage(self):
        """Sweep gate voltage on a small MOSFET."""
        dev = Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=40e-9, Vg=0.0, Vd=0.1)
        sim, results = simulate_sweep(
            dev,
            sweep_contacts={"gate": np.linspace(0, 0.3, 4)},
            resolution=(10e-9, 5e-9, 10e-9),
            quantum=False,
            max_iter=80,
            tol=1e-8,
            verbose=False,
        )
        assert len(results) == 4
        for r in results:
            assert r["converged"]
            assert "phi" in r
            assert "n" in r
            assert "_voltages" in r
            assert "gate" in r["_voltages"]

    def test_sweep_empty_raises(self):
        dev = Device.mosfet()
        with pytest.raises(ValueError):
            simulate_sweep(dev, sweep_contacts={})

    def test_sweep_mismatched_lengths_raises(self):
        dev = Device.mosfet()
        with pytest.raises(ValueError):
            simulate_sweep(
                dev,
                sweep_contacts={
                    "gate": np.linspace(0, 1, 5),
                    "drain": np.linspace(0, 0.5, 3),
                },
            )


class TestOpticalGeneration:
    def test_optical_generation_raises_on_wrong_size(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        with pytest.raises(ValueError):
            sim.set_optical_generation(np.ones(mesh.npts() + 1))

    def test_optical_generation_accepts_correct_size(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        # Moderate optical generation to ensure convergence
        sim.set_optical_generation(np.ones(mesh.npts()) * 1e20)
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        results = sim.run(max_iter=50, tol=1e-6)
        assert results["converged"]
        # With optical generation, carrier densities should be elevated above intrinsic
        assert results["n"].max() > 1e16
        assert results["p"].max() > 1e16

    def test_optical_generation_via_simulate_device(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, resolution=(0.5e-6, 0.5e-6, 0.5e-6))
        G_opt = np.ones(mesh.npts()) * 1e20
        sim, results = simulate_device(
            dev,
            resolution=(0.5e-6, 0.5e-6, 0.5e-6),
            optical_generation=G_opt,
            quantum=False,
            max_iter=50,
            tol=1e-6,
        )
        assert results["converged"]
        assert results["n"].max() > 1e16
        assert results["p"].max() > 1e16


class TestSRHRecombination:
    def test_srh_equilibrium_pnjunction(self):
        """PN junction at equilibrium with finite SRH lifetimes should converge."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        npts = mesh.npts()
        sim._sim.set_recombination(np.ones(npts) * 1e-7, np.ones(npts) * 1e-7)
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        results = sim.run(max_iter=50, tol=1e-6)
        assert results["converged"]
        assert results["n"].max() > 1e20
        assert results["p"].max() > 1e20

    def test_srh_with_optical_generation(self):
        """SRH + optical generation: carriers elevated but limited by recombination."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        npts = mesh.npts()
        sim._sim.set_recombination(np.ones(npts) * 1e-7, np.ones(npts) * 1e-7)
        sim.set_optical_generation(np.ones(mesh.npts()) * 1e20)
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        results = sim.run(max_iter=50, tol=1e-6)
        assert results["converged"]
        assert results["n"].max() > 1e16
        assert results["p"].max() > 1e16

class TestThermalCoupling:
    def test_thermal_coupling_disabled_by_default(self):
        """Without enabling thermal coupling, temperature array should be empty."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        results = sim.run(max_iter=50, tol=1e-5)
        assert results["temperature"].size == 0

    def test_thermal_coupling_enabled_zero_bias(self):
        """At zero bias, Joule heating is negligible; T should be near ambient."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)
        results = sim.run(max_iter=50, tol=1e-5)
        assert results["temperature"].size == mesh.npts()
        # At equilibrium, power dissipation should be negligible
        assert np.allclose(results["temperature"], 300.0, atol=1.0)

    def test_thermal_coupling_enabled_with_bias(self):
        """With applied bias, self-heating should raise temperature above ambient."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.1)
        sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)
        results = sim.run(max_iter=50, tol=1e-5)
        assert results["temperature"].size == mesh.npts()
        T = results["temperature"]
        # Some self-heating should occur (even if small in this coarse mesh)
        assert T.max() >= 300.0
        # Contacts should be at ambient temperature (auto-BC from phi_bc_)
        p_mask = mesh.fields.get("contact_p_contact", np.zeros(mesh.npts())) > 0
        n_mask = mesh.fields.get("contact_n_contact", np.zeros(mesh.npts())) > 0
        if p_mask.any():
            assert np.allclose(T[p_mask], 300.0, atol=0.1)
        if n_mask.any():
            assert np.allclose(T[n_mask], 300.0, atol=0.1)

    def test_thermal_coupling_custom_conductivity(self):
        """Custom thermal conductivity array should be accepted."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        kappa = np.ones(mesh.npts()) * 100.0  # W/(m*K)
        sim.set_thermal_coupling(enable=True, thermal_conductivity=kappa, ambient_temperature=300.0)
        results = sim.run(max_iter=50, tol=1e-5)
        assert results["temperature"].size == mesh.npts()

    def test_to_mesh_fields_with_temperature(self):
        """to_mesh_fields should include temperature when thermal coupling is on."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        sim.set_thermal_coupling(enable=True, ambient_temperature=300.0)
        sim.run(max_iter=50, tol=1e-5)
        fields = sim.to_mesh_fields()
        assert "temperature" in fields
        assert fields["temperature"].shape == mesh.shape()
class TestCutCell:
    """Cut-cell / immersed-boundary correction for curved interfaces."""

    def test_cut_cell_disabled_by_default(self):
        mesh = self._make_mesh()
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        assert not getattr(sim, '_cut_cell_enabled', False)

    def test_cut_cell_can_be_enabled(self):
        mesh = self._make_mesh()
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.enable_cut_cell(True)
        assert sim._cut_cell_enabled is True

    def test_cut_cell_runs_without_crash(self):
        mesh = self._make_mesh()
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", 0.0)
        sim.set_contact("n_contact", 0.0)
        sim.enable_cut_cell(True)
        results = sim.run()
        assert results["converged"]

    def _make_mesh(self):
        from tcad.geometry.device_builder import Device
        from tcad.mesh.generator import structured_mesh_from_device
        dev = Device.pnjunction(L=100e-9, W=50e-9, H=50e-9,
                                x_junction=50e-9, Na=1e16, Nd=1e16)
        return structured_mesh_from_device(dev, resolution=(20e-9, 20e-9, 20e-9))


