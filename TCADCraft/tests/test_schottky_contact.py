"""Analytic and API tests for calibrated Schottky/NLM injection."""

from __future__ import annotations

import math

import numpy as np
import pytest

from tcad.material import gallium_nitride
from tcad.geometry.device_builder import Device, DopingProfile, Region
from tcad.geometry.shapes import Box
from tcad.mesh.generator import structured_mesh_from_device
from tcad.physics.contact import (
    K_B_EV,
    SchottkyContactModel,
    WSe2CompactContactModel,
    WSe2TransportWindow,
    WSe2TwoWindowTransferModel,
    pinned_schottky_barrier_height,
)
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


def test_high_field_bulk_drop_and_subbarrier_window_are_physical():
    model = SchottkyContactModel(
        barrier_height_eV=0.8642,
        effective_mass_ratio=0.2,
        area_m2=1.0e-13,
        series_resistance_ohm=460.0,
        transport_saturation_current_A=360.0e-6,
        tunneling_barrier_lowering_eV=0.107,
        tunneling_cutoff_energy_eV=0.815,
        tunneling_decay_exponent=0.33,
    )
    thermionic_high = model.current(10.0, 300.0, False)
    assert 0.0 < thermionic_high < model.transport_saturation_current_A

    low = model.components(0.05, 300.0)
    middle = model.components(0.60, 300.0)
    cutoff = model.components(0.815, 300.0)
    assert low["tunneling_increment_A"] > 0.0
    assert middle["tunneling_increment_A"] > 0.0
    assert cutoff["tunneling_increment_A"] == 0.0
    assert (
        low["total_A"] / low["thermionic_A"]
        > middle["total_A"] / middle["thermionic_A"]
        > 1.0
    )


def test_gan_reference_barrier_matches_calibration_deck():
    gan = gallium_nitride()
    assert gan.name == "GaN"
    assert math.isclose(4.80 - gan.chi, 0.86420028, abs_tol=1e-10)
    assert gan.mu_n == 1800.0
    assert gan.mu_p == 150.0


def test_pinned_schottky_barrier_interpolates_to_charge_neutrality_level():
    schottky_mott = pinned_schottky_barrier_height(
        4.8, 3.9, pinning_factor=1.0, charge_neutrality_level_eV=4.2
    )
    pinned = pinned_schottky_barrier_height(
        4.8, 3.9, pinning_factor=0.0, charge_neutrality_level_eV=4.2
    )
    midpoint = pinned_schottky_barrier_height(
        4.8, 3.9, pinning_factor=0.5, charge_neutrality_level_eV=4.2
    )
    assert math.isclose(schottky_mott, 0.9, abs_tol=1e-14)
    assert math.isclose(pinned, 0.3, abs_tol=1e-14)
    assert math.isclose(midpoint, 0.6, abs_tol=1e-14)


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
        transport_saturation_current_A=360.0e-6,
        tunneling_cutoff_energy_eV=0.815,
        tunneling_decay_exponent=0.33,
    )
    assert math.isclose(model.barrier_height_eV, 0.86420028, abs_tol=1e-10)
    assert model.transport_saturation_current_A == 360.0e-6
    assert sim.schottky_contact_current("top") > 0.0


def test_wse2_schottky_contact_accepts_fermi_level_pinning():
    device = Device.wse2_schottky_fet(
        Lg=40e-9,
        Lsd=10e-9,
        W=5e-9,
        t_ch=2e-9,
        tox=3e-9,
        source_workfunction=4.8,
        drain_workfunction=4.8,
    )
    mesh = structured_mesh_from_device(device, nx=7, ny=1, nz=3)
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    sim.set_contact("source", 0.2, workfunction=4.8)
    ideal = sim.set_wse2_schottky_contact("source", area_m2=1.0e-15)
    pinned = sim.set_wse2_schottky_contact(
        "source",
        area_m2=1.0e-15,
        pinning_factor=0.0,
        charge_neutrality_level_eV=4.2,
        tunneling_barrier_lowering_eV=0.05,
    )
    assert math.isclose(ideal.barrier_height_eV, 0.9, abs_tol=1e-12)
    assert math.isclose(pinned.barrier_height_eV, 0.3, abs_tol=1e-12)
    assert pinned.current(0.2, 300.0, True) > ideal.current(0.2, 300.0, False)


def test_wse2_compact_contact_gate_controls_barrier_and_current():
    model = WSe2CompactContactModel()
    barrier_off = model.effective_barrier_height_eV(0.0)
    barrier_on = model.effective_barrier_height_eV(2.0)
    assert barrier_on < barrier_off
    assert (
        model.abs_current_A_per_um(2.0, 0.05, 300.0)
        > model.abs_current_A_per_um(0.0, 0.05, 300.0)
    )


def test_wse2_compact_contact_optional_hole_branch_is_explicit():
    electron_only = WSe2CompactContactModel()
    ambipolar = WSe2CompactContactModel(
        hole_current_scale=1.0,
        hole_drain_barrier_coupling=1.0,
        hole_tunneling_barrier_lowering_eV=0.05,
    )
    assert ambipolar.nominal_hole_barrier_height_eV > 0.0
    assert (
        ambipolar.effective_hole_barrier_height_eV(1.0, 0.5)
        < ambipolar.nominal_hole_barrier_height_eV
    )
    assert (
        ambipolar.abs_current_A_per_um(1.0, 0.5, 300.0)
        > electron_only.abs_current_A_per_um(1.0, 0.5, 300.0)
    )


def test_wse2_compact_contact_optional_ambipolar_notch_is_explicit():
    base = WSe2CompactContactModel()
    notch = WSe2CompactContactModel(
        ambipolar_notch_center_V=1.0,
        ambipolar_notch_width_V=0.2,
        ambipolar_notch_depth_decades=2.0,
    )
    assert math.isclose(base.ambipolar_notch_factor(1.0), 1.0, abs_tol=0.0)
    assert notch.ambipolar_notch_factor(1.0) < 0.02
    assert notch.ambipolar_notch_factor(0.0) > notch.ambipolar_notch_factor(1.0)
    assert (
        notch.abs_current_A_per_um(1.0, 0.05, 300.0)
        < base.abs_current_A_per_um(1.0, 0.05, 300.0)
    )


def test_wse2_compact_contact_optional_ambipolar_recovery_is_explicit():
    base = WSe2CompactContactModel(
        ambipolar_notch_center_V=0.8,
        ambipolar_notch_width_V=0.3,
        ambipolar_notch_depth_decades=2.0,
    )
    recovery = WSe2CompactContactModel(
        ambipolar_notch_center_V=0.8,
        ambipolar_notch_width_V=0.3,
        ambipolar_notch_depth_decades=2.0,
        ambipolar_recovery_center_V=1.2,
        ambipolar_recovery_width_V=0.1,
        ambipolar_recovery_gain_decades=2.0,
    )

    assert math.isclose(base.ambipolar_recovery_factor(2.0), 1.0, abs_tol=0.0)
    assert recovery.ambipolar_recovery_factor(0.0) == pytest.approx(1.0, abs=1e-4)
    assert recovery.ambipolar_recovery_factor(2.0) > 90.0
    assert (
        recovery.abs_current_A_per_um(2.0, 0.5, 300.0)
        > base.abs_current_A_per_um(2.0, 0.5, 300.0)
    )


def test_wse2_transport_window_has_gate_temperature_and_drain_controls():
    window = WSe2TransportWindow(
        center_gate_V=1.5,
        width_V=0.25,
        peak_current_A_per_um=1.0e-8,
        floor_current_A_per_um=1.0e-20,
        temperature_activation_eV=0.08,
        drain_exponent=1.0,
        drain_reference_V=0.5,
    )
    centered = window.current_A_per_um(1.5, 0.5, 300.0)
    off_center = window.current_A_per_um(0.5, 0.5, 300.0)
    high_temp = window.current_A_per_um(1.5, 0.5, 400.0)
    high_drain = window.current_A_per_um(1.5, 1.0, 300.0)

    assert centered > off_center
    assert high_temp > centered
    assert math.isclose(high_drain / centered, 2.0, rel_tol=1e-12)


def test_wse2_transport_window_supports_asymmetry_and_notch():
    symmetric = WSe2TransportWindow(
        center_gate_V=1.0,
        width_V=0.2,
        peak_current_A_per_um=1.0e-9,
    )
    asymmetric = WSe2TransportWindow(
        center_gate_V=1.0,
        width_V=0.2,
        left_width_V=0.6,
        right_width_V=0.1,
        peak_current_A_per_um=1.0e-9,
    )
    notched = WSe2TransportWindow(
        center_gate_V=1.0,
        width_V=0.5,
        peak_current_A_per_um=1.0e-9,
        notch_center_gate_V=1.2,
        notch_width_V=0.05,
        notch_depth_decades=3.0,
    )

    assert asymmetric.gate_weight(0.5) > symmetric.gate_weight(0.5)
    assert asymmetric.gate_weight(1.4) < symmetric.gate_weight(1.4)
    assert notched.gate_weight(1.2) < 2.0e-3 * symmetric.gate_weight(1.2)
    assert notched.gate_weight(0.6) > notched.gate_weight(1.2)


def test_wse2_transport_window_supports_sigmoid_plateau_tail():
    base = WSe2TransportWindow(
        center_gate_V=0.3,
        width_V=0.08,
        peak_current_A_per_um=1.0e-9,
    )
    plateau = WSe2TransportWindow(
        center_gate_V=0.3,
        width_V=0.08,
        peak_current_A_per_um=1.0e-9,
        right_tail_fraction=0.95,
        right_tail_smoothing_V=0.02,
    )

    assert plateau.gate_weight(0.8) > 100.0 * base.gate_weight(0.8)
    assert plateau.gate_weight(0.0) == pytest.approx(base.gate_weight(0.0), rel=1e-2)
    assert plateau.gate_weight(0.8) == pytest.approx(0.95, rel=1e-3)

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        WSe2TransportWindow(
            center_gate_V=0.3,
            width_V=0.08,
            peak_current_A_per_um=1.0e-9,
            right_tail_fraction=1.1,
        )
    with pytest.raises(ValueError, match="right_tail_smoothing_V"):
        WSe2TransportWindow(
            center_gate_V=0.3,
            width_V=0.08,
            peak_current_A_per_um=1.0e-9,
            right_tail_fraction=0.5,
            right_tail_smoothing_V=0.0,
        )


def test_wse2_two_window_transfer_exposes_electron_hole_components():
    model = WSe2TwoWindowTransferModel(
        electron_window=WSe2TransportWindow(
            center_gate_V=1.6,
            width_V=0.2,
            peak_current_A_per_um=1.0e-7,
            floor_current_A_per_um=1.0e-25,
        ),
        hole_window=WSe2TransportWindow(
            center_gate_V=-0.8,
            width_V=0.3,
            peak_current_A_per_um=1.0e-8,
            floor_current_A_per_um=1.0e-25,
        ),
        valley_floor_A_per_um=1.0e-18,
        component_coupling=0.5,
    )

    electron_side = model.components_A_per_um(1.6, 0.5, 300.0)
    hole_side = model.components_A_per_um(-0.8, 0.5, 300.0)
    valley = model.components_A_per_um(0.4, 0.5, 300.0)

    assert electron_side["electron_A_per_um"] > electron_side["hole_A_per_um"]
    assert hole_side["hole_A_per_um"] > hole_side["electron_A_per_um"]
    assert valley["total_A_per_um"] >= model.valley_floor_A_per_um
    assert electron_side["total_A_per_um"] > valley["total_A_per_um"]


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
