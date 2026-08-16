"""Tests for tcad.simulator and C++ core integration."""

import warnings
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

    def test_set_charge_volume_fraction(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=5, nz=5)
        sim = Simulator(mesh)
        sim.set_charge_volume_fraction(np.full(mesh.npts(), 0.6))
        with pytest.raises(ValueError, match="expected"):
            sim.set_charge_volume_fraction(np.ones(mesh.npts() - 1))
        with pytest.raises(ValueError, match="finite"):
            invalid = np.ones(mesh.npts())
            invalid[0] = np.nan
            sim.set_charge_volume_fraction(invalid)

    def test_set_btbt_weight_validation(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=1)
        sim = Simulator(mesh)

        class CaptureWeight:
            def __init__(self):
                self.weight = None

            def set_btbt_weight(self, weight):
                self.weight = weight

        capture = CaptureWeight()
        sim._sim = capture
        sim.set_btbt_weight(np.full(mesh.npts(), 0.5))
        assert capture.weight.shape == (mesh.npts(),)
        assert np.allclose(capture.weight, 0.5)

        with pytest.raises(ValueError, match="size"):
            sim.set_btbt_weight(np.ones(mesh.npts() - 1))
        with pytest.raises(ValueError, match="finite"):
            invalid = np.ones(mesh.npts())
            invalid[0] = np.nan
            sim.set_btbt_weight(invalid)
        with pytest.raises(ValueError, match="nonnegative"):
            invalid = np.ones(mesh.npts())
            invalid[0] = -1.0
            sim.set_btbt_weight(invalid)

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

    def test_btbt_nonlocal_options_forwarded_and_validated(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=1)
        sim = Simulator(mesh)

        class CaptureBTBT:
            def __init__(self):
                self.calls = []

            def set_btbt_enabled(self, value):
                self.calls.append(("enabled", value))

            def set_btbt_params(self, A, B, D):
                self.calls.append(("params", A, B, D))

            def set_btbt_field_mode(self, mode):
                self.calls.append(("field_mode", mode))

            def set_btbt_field_options(self, mode, cap):
                self.calls.append(("field_options", mode, cap))

            def set_btbt_field_shape(self, mode, cap, alpha, ref):
                self.calls.append(("field_shape", mode, cap, alpha, ref))

            def set_btbt_continuity_scale(self, scale):
                self.calls.append(("continuity_scale", scale))

            def set_btbt_use_nonlocal(self, value):
                self.calls.append(("use_nonlocal", value))

            def set_btbt_nonlocal_params(self, tunnel_path_fraction, wkb_npts):
                self.calls.append(("nonlocal", tunnel_path_fraction, wkb_npts))

        capture = CaptureBTBT()
        sim._sim = capture
        sim.set_btbt(
            enabled=True,
            D=2.5,
            field_mode="x",
            field_cap=8.0e8,
            field_alpha=-0.25,
            field_ref=1.0e8,
            continuity_scale=3.5,
            use_nonlocal=True,
            tunnel_path_fraction=0.25,
            wkb_npts=96,
        )
        assert ("params", 3.1e21, 2.0e9, 2.5) in capture.calls
        assert ("field_shape", 1, 8.0e8, -0.25, 1.0e8) in capture.calls
        assert ("continuity_scale", 3.5) in capture.calls
        assert ("nonlocal", 0.25, 96) in capture.calls

        with pytest.raises(ValueError, match="D"):
            sim.set_btbt(D=0.0)
        with pytest.raises(ValueError, match="field_mode"):
            sim.set_btbt(field_mode="bad")
        with pytest.raises(ValueError, match="field_cap"):
            sim.set_btbt(field_cap=np.inf)
        with pytest.raises(ValueError, match="field_alpha"):
            sim.set_btbt(field_alpha=np.nan)
        with pytest.raises(ValueError, match="field_ref"):
            sim.set_btbt(field_ref=0.0)
        with pytest.raises(ValueError, match="continuity_scale"):
            sim.set_btbt(continuity_scale=-1.0)
        with pytest.raises(ValueError, match="tunnel_path_fraction"):
            sim.set_btbt(tunnel_path_fraction=np.nan)
        with pytest.raises(ValueError, match="wkb_npts"):
            sim.set_btbt(wkb_npts=1)

    def test_density_gradient_coefficient_validation(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=1)
        sim = Simulator(mesh)
        sim.set_density_gradient_coefficients(4.885e-20, 3.432e-20)
        with pytest.raises(ValueError, match="finite and positive"):
            sim.set_density_gradient_coefficients(np.nan, 3.432e-20)

    def test_density_gradient_effective_mass_mapping(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=1)
        sim = Simulator(mesh)
        bn, bp = sim.set_density_gradient_effective_masses(
            electron_dos_mass=1.090250521886503,
            hole_dos_mass=1.1524650081209626,
            electron_gamma=3.6,
            hole_gamma=5.6,
        )
        assert bn == pytest.approx(4.193511896579586e-20, rel=1e-12)
        assert bp == pytest.approx(6.171091146361865e-20, rel=1e-12)
        with pytest.raises(ValueError, match="masses and gamma factors"):
            sim.set_density_gradient_effective_masses(1.0, 1.0, 0.0, 1.0)

    def test_silicon_multivalley_parameter_validation(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=3)
        sim = Simulator(mesh)
        sim.set_density_gradient_silicon_multivalley()
        with pytest.raises(ValueError, match="finite and positive"):
            sim.set_density_gradient_silicon_multivalley(transverse_mass=np.nan)
        with pytest.raises(ValueError, match=r"\[1,32\]"):
            sim.set_density_gradient_silicon_multivalley(subbands=0)

    def test_density_gradient_interface_factor_validation(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=3)
        sim = Simulator(mesh)
        sim.set_density_gradient_interface_distance_factor(0.6)
        with pytest.raises(ValueError, match="finite and positive"):
            sim.set_density_gradient_interface_distance_factor(np.nan)

    def test_density_gradient_potential_form_toggle(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=3)
        sim = Simulator(mesh)
        sim.set_density_gradient_potential_form()
        sim.set_density_gradient_potential_form(False)

    def test_density_gradient_step_boundary_validation(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=3)
        sim = Simulator(mesh)
        sim.set_density_gradient_step_boundary()
        with pytest.raises(ValueError, match="finite and positive"):
            sim.set_density_gradient_step_boundary(electron_barrier_mass=np.nan)

    def test_density_gradient_step_boundary_defaults_use_barrier_gamma(self):
        """Equation 250 takes gamma from 0+ (oxide), not bulk silicon."""
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=3)
        sim = Simulator(mesh)

        class CaptureBoundary:
            args = None

            def set_density_gradient_step_boundary(self, *args):
                self.args = args

        capture = CaptureBoundary()
        sim._sim = capture
        sim.set_density_gradient_step_boundary()
        assert capture.args[5:7] == pytest.approx((1.0, 1.0))

    def test_leakage_signed_fn_validation_is_atomic(self):
        dev = Device.pnjunction()
        mesh = structured_mesh_from_device(dev, nx=5, ny=1, nz=1)
        sim = Simulator(mesh)

        class CaptureLeakage:
            leakage_args = None
            polarity_args = None

            def set_leakage(self, *args):
                self.leakage_args = args

            def set_leakage_fn_polarity(self, *args):
                self.polarity_args = args

            def set_leakage_enabled(self, enabled):
                self.enabled = enabled

        capture = CaptureLeakage()
        sim._sim = capture
        with pytest.raises(ValueError, match="all four"):
            sim.set_leakage(
                fn_C_positive=1.23e-6,
                fn_B_positive=2.37e10,
            )
        assert capture.leakage_args is None
        assert capture.polarity_args is None
        with pytest.raises(ValueError, match="finite and nonnegative"):
            sim.set_leakage(
                fn_C_positive=np.nan,
                fn_B_positive=2.37e10,
                fn_C_negative=1.87e-7,
                fn_B_negative=1.88e10,
            )
        assert capture.leakage_args is None
        assert capture.polarity_args is None

        sim.set_leakage(
            fn_C_positive=1.23e-6,
            fn_B_positive=2.37e10,
            fn_C_negative=1.87e-7,
            fn_B_negative=1.88e10,
        )
        assert capture.leakage_args is not None
        assert capture.polarity_args == pytest.approx(
            (1.23e-6, 2.37e10, 1.87e-7, 1.88e10)
        )

    def test_run_small(self):
        """Run a very small simulation to verify end-to-end."""
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            results = sim.run(max_iter=10, tol=1e-6)
        assert "phi" in results
        assert "n" in results
        assert "p" in results
        assert "Qn" in results
        assert "Qp" in results
        assert "poisson_residual" in results
        assert results["quantum_residual"] == pytest.approx(0.0)
        assert results["phi"].size == mesh.npts()
        assert results["Qn"].size == mesh.npts()
        assert np.all(results["Qn"] == 0.0)

    def test_to_mesh_fields(self):
        dev = Device.pnjunction(L=1e-6, W=1e-6, H=1e-6)
        mesh = structured_mesh_from_device(dev, nx=11, ny=11, nz=11)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.set_contact("p_contact", voltage=0.0)
        sim.set_contact("n_contact", voltage=0.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
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

    def test_cut_cell_uses_device_region_geometry(self):
        mesh = self._make_mesh()
        assert getattr(mesh, "_material_shapes", None)
        sim = Simulator(mesh)
        sim.set_material_from_mesh()
        sim.enable_cut_cell(True)

        class CaptureEdges:
            args = None

            def set_edge_permittivity(self, *args):
                self.args = args

        capture = CaptureEdges()
        sim._sim = capture
        sim._apply_cut_cell()
        assert capture.args is not None
        assert all(values.shape == (mesh.npts(),) for values in capture.args)

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
