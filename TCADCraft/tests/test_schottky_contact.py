"""Analytic and API tests for calibrated Schottky/NLM injection."""

from __future__ import annotations

import math

import numpy as np

from tcad.material import gallium_nitride
from tcad.geometry.device_builder import Device, DopingProfile, Region
from tcad.geometry.shapes import Box
from tcad.mesh.generator import structured_mesh_from_device
from tcad.physics.contact import K_B_EV, SchottkyContactModel
from tcad.simulator import Simulator


def test_thermionic_saturation_and_zero_nlm_limit():
    model = SchottkyContactModel(
        barrier_height_eV=0.8,
        effective_mass_ratio=0.2,
        area_m2=1.0e-12,
    )
    expected = (
        model.richardson_constant * 300.0**2 * model.area_m2
        * math.exp(-0.8 / (K_B_EV * 300.0))
    )
    assert math.isclose(model.saturation_current(300.0), expected, rel_tol=1e-14)
    assert model.current(0.3, 300.0, False) == model.current(0.3, 300.0, True)


def test_nlm_enhancement_temperature_and_series_resistance_bounds():
    model = SchottkyContactModel(
        barrier_height_eV=0.8642,
        effective_mass_ratio=0.2,
        area_m2=1.0e-13,
        series_resistance_ohm=1360.0,
        tunneling_barrier_lowering_eV=0.0928,
    )
    thermionic = model.current(0.3, 300.0, False)
    total = model.current(0.3, 300.0, True)
    assert total > thermionic > 0.0
    assert total < 0.3 / model.series_resistance_ohm
    # A barrier-energy correction has an explicit temperature dependence;
    # this guards against regressing to a temperature-independent multiplier.
    ratio_300 = (
        model.saturation_current(300.0, True)
        / model.saturation_current(300.0, False)
    )
    ratio_450 = (
        model.saturation_current(450.0, True)
        / model.saturation_current(450.0, False)
    )
    assert ratio_300 > ratio_450 > 1.0


def test_nlm_energy_window_removes_false_high_bias_tail():
    model = SchottkyContactModel(
        barrier_height_eV=0.8642,
        effective_mass_ratio=0.2,
        area_m2=1.0e-13,
        series_resistance_ohm=1360.0,
        tunneling_barrier_lowering_eV=0.0925,
        tunneling_window_center_eV=0.768,
        tunneling_window_width_eV=0.011,
    )
    increment_near_peak = (
        model.current(0.785, 300.0, True)
        - model.current(0.785, 300.0, False)
    )
    increment_high_bias = (
        model.current(1.5, 300.0, True)
        - model.current(1.5, 300.0, False)
    )
    assert increment_near_peak > 0.0
    assert increment_high_bias < 1.0e-2 * increment_near_peak


def test_gan_reference_barrier_matches_calibration_deck():
    gan = gallium_nitride()
    assert gan.name == "GaN"
    assert math.isclose(4.80 - gan.chi, 0.86420028, abs_tol=1e-10)
    assert gan.mu_n == 1800.0
    assert gan.mu_p == 150.0


def test_simulator_configures_contact_model_from_workfunction_and_affinity():
    gan = gallium_nitride()
    device = Device("gan_schottky")
    device.add_region(
        Region(
            "gan",
            Box(0.0, 100e-9, 0.0, 10e-9, 0.0, 10e-9),
            gan,
            DopingProfile(Nd=1.0e17),
        )
    )
    device.add_contact(
        "top", Box(0.0, 0.0, 0.0, 10e-9, 0.0, 10e-9),
        workfunction=4.80,
    )
    mesh = structured_mesh_from_device(device, nx=5, ny=1, nz=1)
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_contact("top", 0.3, workfunction=4.80)
    model = sim.set_schottky_tunneling(
        "top",
        effective_mass_ratio=0.20,
        area_m2=1.0e-13,
        tunneling_barrier_lowering_eV=0.0928,
        series_resistance_ohm=1360.0,
        tunneling_window_center_eV=0.768,
        tunneling_window_width_eV=0.011,
    )
    assert math.isclose(model.barrier_height_eV, 0.86420028, abs_tol=1e-10)
    assert sim.schottky_contact_current("top") > 0.0


def test_automatic_continuation_preserves_schottky_workfunction():
    """A >0.25 V first solve must not silently turn Schottky into ohmic."""

    class DummyCore:
        def set_gummel_max_iter(self, _value):
            pass

        def set_tolerance(self, _value):
            pass

        def set_initial_guess(self, *_args):
            pass

        def solve(self):
            empty = np.zeros(1)
            return {
                "converged": True,
                "iterations": 1,
                "phi": empty,
                "n": empty,
                "p": empty,
            }

    sim = object.__new__(Simulator)
    sim._sim = DummyCore()
    sim._contact_voltages = {"top": 1.0}
    sim._contact_workfunctions = {"top": 4.8}
    sim._pending_contact_ramps = {}
    sim.results = None
    calls = []

    def record_contact(name, voltage, workfunction=None):
        calls.append((name, voltage, workfunction))
        sim._contact_voltages[name] = float(voltage)

    sim.set_contact = record_contact
    sim.run(max_iter=2, tol=1e-6)
    assert calls
    assert all(call[2] == 4.8 for call in calls if call[0] == "top")
