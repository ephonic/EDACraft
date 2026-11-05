"""Independent dielectric energy, source work, small changes and scope gates."""
from copy import deepcopy
import math
from fractions import Fraction

import numpy as np
import pytest

import tcad.postprocess as postprocess
from tcad.core import PyDeviceSimulator
from test_transient_voltage_waveforms import driven_film, CLOCK, VOLTAGE
from test_transient_selfconsistent import central_cell


def capacitance(x, eps, area):
    face = 2 * eps[:-1] * eps[1:] / (eps[:-1] + eps[1:])
    return area / sum(np.diff(x) / face)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("layered", [False, True])
@pytest.mark.parametrize("dt", [.19e-9, .6e-9])
def test_linear_capacitor_closed_pulse_has_independent_storage_and_zero_net_work(axis, stretched, layered, dt):
    sim, x, eps, _, area = driven_film(axis, stretched=stretched, layered=layered, dt=dt)
    history = sim.solve_transient()
    cap = capacitance(x, eps, area)
    previous_voltage = 0.
    for state in history:
        assert state["valid"] and state["dielectric_energy_available"]
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        assert state["dielectric_energy_J"] == pytest.approx(.5 * cap * voltage**2, rel=1e-12, abs=0.)
        if state["dt_s"]:
            expected = .5 * cap * (voltage - previous_voltage) * (voltage + previous_voltage)
            assert state["dielectric_energy_increment_J"] == pytest.approx(expected, rel=1e-11, abs=1e-34)
        else:
            assert not state["dielectric_energy_increment_available"]
            assert "dielectric_energy_increment_J" not in state
        previous_voltage = voltage
    linear = postprocess.integrate_transient_terminal_history(history, voltage_quadrature="linear")
    endpoint = postprocess.integrate_transient_terminal_history(history)
    energy_scale = .5 * cap * max(abs(VOLTAGE))**2
    assert abs(linear["supplied_energy_J"]) < 1e-12 * energy_scale
    assert endpoint["supplied_energy_J"] > 1e-3 * energy_scale
    assert linear["integration_kind"] == "linear_voltage_with_backward_euler_interval_current"
    assert not linear["energy_balance_validated"]
    audited = postprocess.audit_transient_dielectric_energy(history, rtol=1e-10)
    assert audited["valid"] and audited["energy_balance_validated"]
    assert audited["dissipated_energy_J"] == 0. and not audited["physical_validated"]
    assert abs(audited["stored_energy_change_J"]) < 1e-12 * energy_scale


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("direction", ["charge", "discharge", "cross_zero"])
def test_charging_discharging_and_internal_voltage_zero_crossing(axis, direction):
    sim, x, eps, _, area = driven_film(axis)
    if direction == "charge":
        initial, final = 0., .02
    elif direction == "discharge":
        initial, final = .02, 0.
    else:
        initial, final = -.02, .02
    sim.set_transient_dt(1e-9)
    sim.set_transient_t_final(1e-9)
    sim.set_transient_voltage_waveforms([0., 1e-9], {8: [initial, final]})
    history = sim.solve_transient()
    assert len(history) == 2
    cap = capacitance(x, eps, area)
    stored = .5 * cap * .02**2
    result = postprocess.audit_transient_dielectric_energy(history)
    assert result["energy_balance_validated"]
    assert result["absorbed_energy_J"] == pytest.approx(stored if direction != "discharge" else 0., rel=1e-12, abs=0.)
    assert result["returned_energy_J"] == pytest.approx(stored if direction != "charge" else 0., rel=1e-12, abs=0.)
    expected = stored if direction == "charge" else (-stored if direction == "discharge" else 0.)
    assert result["supplied_energy_J"] == pytest.approx(expected, rel=1e-12, abs=1e-34)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_energy_increment_survives_large_static_field_and_absolute_rounding(axis):
    sim, x, eps, _, area = driven_film(axis)
    sim.set_dirichlet_potential({0: 0., 8: 1e8})
    sim.set_transient_dt(1e-10)
    sim.set_transient_t_final(2e-10)
    sim.set_transient_voltage_waveforms([0., 1e-10, 2e-10], {8: [0., 1e-13, 2e-13]})
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    cap = capacitance(x, eps, area)
    np.testing.assert_array_equal([s["dielectric_energy_J"] for s in history], history[0]["dielectric_energy_J"])
    np.testing.assert_array_equal([s["electrode_voltages_V"][1] for s in history], 1e8)
    for state in history[1:]:
        assert state["dielectric_energy_increment_J"] == pytest.approx(cap * 1e8 * 1e-13, rel=3e-12, abs=0.)
        assert state["electrode_total_currents_A"][1] == pytest.approx(cap * 1e-13 / 1e-10, rel=3e-12, abs=0.)
    report = postprocess.audit_transient_dielectric_energy(history, rtol=1e-10)
    assert report["energy_balance_validated"]
    assert report["stored_energy_change_J"] == pytest.approx(2 * cap * 1e8 * 1e-13, rel=3e-12, abs=0.)
    # A large static stored energy cannot hide a 1% incremental defect.
    corrupted = deepcopy(history)
    corrupted[1]["dielectric_energy_increment_J"] *= 1.01
    failed = postprocess.audit_transient_dielectric_energy(corrupted, rtol=1e-8)
    assert not failed["valid"] and not failed["energy_balance_validated"]
    assert failed["max_interval_relative_residual"] > .009


def multidimensional_capacitor(axis, dimension, stretched):
    shape = [4, 4, 3] if dimension == 3 else [4, 4, 1]
    if dimension == 2 and axis == 2:
        shape = [4, 1, 4]
    size = np.prod(shape)
    spacing = [1e-8, 2e-8, 3e-8]
    axes = [np.arange(n) * h for n, h in zip(shape, spacing)]
    if stretched:
        axes = [x * (1 + .15 * np.arange(len(x))) for x in axes]
    widths = [np.r_[np.diff(x)[0], (np.diff(x)[:-1] + np.diff(x)[1:]) / 2, np.diff(x)[-1]]
              if len(x) > 1 else np.array([h]) for x, h in zip(axes, spacing)]
    coords = np.array([(i, j, k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    epsilon = 8.854187817e-12 * (10 + coords @ np.array([1., 2., 3.]))
    contacts = (coords[:, axis] == 0) | (coords[:, axis] == shape[axis] - 1)
    upper = coords[:, axis] == shape[axis] - 1
    # Independent symmetric graph Laplacian and Dirichlet elimination.
    edges = []
    matrix = np.zeros((size, size))
    strides = [1, shape[0], shape[0] * shape[1]]
    for idx, xyz in enumerate(coords):
        for dim in range(3):
            coordinate = xyz[dim]
            if coordinate + 1 == shape[dim]: continue
            neighbor = idx + strides[dim]
            if contacts[idx] and contacts[neighbor]: continue
            face = 2 * epsilon[idx] * epsilon[neighbor] / (epsilon[idx] + epsilon[neighbor])
            area = np.prod([widths[d][xyz[d]] for d in range(3) if d != dim])
            weight = face * area / (axes[dim][coordinate+1] - axes[dim][coordinate])
            edges.append((idx, neighbor, weight))
            matrix[idx, idx] += weight; matrix[neighbor, neighbor] += weight
            matrix[idx, neighbor] -= weight; matrix[neighbor, idx] -= weight
    unit_phi = upper.astype(float)
    free = np.flatnonzero(~contacts)
    boundary = np.flatnonzero(contacts)
    unit_phi[free] = np.linalg.solve(matrix[np.ix_(free, free)], -matrix[np.ix_(free, boundary)] @ unit_phi[boundary])
    energy = .5 * math.fsum(weight * (unit_phi[b] - unit_phi[a])**2 for a, b, weight in edges)
    sim = PyDeviceSimulator(*shape, *spacing)
    for x, setter in zip(axes, [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions]): setter(x)
    sim.set_permittivity(epsilon)
    sim.set_mobility(np.zeros(size), np.zeros(size))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, 1e16), np.full(size, 1e16))
    sim.set_bandgap(np.full(size, 6.))
    sim.set_initial_guess(np.zeros(size), np.zeros(size), np.zeros(size))
    sim.set_dirichlet_potential({int(idx): 0. for idx in boundary})
    sim.set_gummel_max_iter(80); sim.set_tolerance(1e-11)
    sim.set_transient_dt(.6e-9); sim.set_transient_t_final(CLOCK[-1])
    sim.set_transient_voltage_waveforms(CLOCK, {int(idx): VOLTAGE for idx in np.flatnonzero(upper)})
    return sim, unit_phi, energy


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("dimension", [2, 3])
@pytest.mark.parametrize("stretched", [False, True])
def test_multidimensional_energy_uses_independent_graph_geometry(axis, dimension, stretched):
    sim, unit_phi, unit_energy = multidimensional_capacitor(axis, dimension, stretched)
    history = sim.solve_transient()
    for state in history:
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        np.testing.assert_allclose(state["phi"], voltage * unit_phi, atol=1e-16)
        assert state["dielectric_energy_J"] == pytest.approx(unit_energy * voltage**2, rel=1e-12, abs=0.)
    assert postprocess.audit_transient_dielectric_energy(history, rtol=1e-10)["energy_balance_validated"]


@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_fe_cannot_claim_closed_dielectric_energy(model):
    sim, *_ = driven_film(model=model, fe=True)
    history = sim.solve_transient()
    assert all(not s["dielectric_energy_available"] for s in history)
    assert all("dielectric_energy_J" not in s for s in history)
    with pytest.raises(ValueError, match="scope"):
        postprocess.audit_transient_dielectric_energy(history)


@pytest.mark.parametrize("reason", ["transport", "doping", "optical", "fraction", "frozen", "failed"])
def test_energy_scope_excludes_incomplete_physics_and_failed_intervals(reason):
    sim, *_ = driven_film()
    if reason == "transport":
        sim, *_ = central_cell(1e16, False, 0, False)
    elif reason == "doping": sim.set_doping(np.full(9, 1e16))
    elif reason == "optical": sim.set_optical_generation(np.full(9, 1e20))
    elif reason == "fraction": sim.set_charge_volume_fraction(np.full(9, .9))
    elif reason == "frozen":
        sim.clear_transient_voltage_waveforms(); sim.set_newton_freeze_phi(True)
    else: sim.set_gummel_max_iter(0)
    history = sim.solve_transient()
    assert not history[-1]["dielectric_energy_available"]
    with pytest.raises(ValueError): postprocess.audit_transient_dielectric_energy(history)


@pytest.mark.parametrize("scale", ["overflow", "underflow"])
def test_unrepresentable_energy_is_unavailable_instead_of_zero_or_inf(scale):
    spacing = 1e150 if scale == "overflow" else 1e-7
    voltage = 1e6 if scale == "overflow" else 1e-180
    sim = PyDeviceSimulator(9, 1, 1, 1e-8, spacing, spacing)
    sim.set_permittivity(np.full(9, 20 * 8.854187817e-12))
    sim.set_mobility(np.zeros(9), np.zeros(9)); sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9, 1e16), np.full(9, 1e16)); sim.set_bandgap(np.full(9, 6.))
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_dirichlet_potential({0: 0., 8: 0.})
    sim.set_transient_dt(1.); sim.set_transient_t_final(1.)
    sim.set_transient_voltage_waveforms([0., 1.], {8: [0., voltage]})
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    assert not history[-1]["dielectric_energy_available"]
    assert "dielectric_energy_J" not in history[-1]
    with pytest.raises(ValueError, match="scope"): postprocess.audit_transient_dielectric_energy(history)


@pytest.mark.parametrize("change", ["missing_energy", "negative_energy", "nan_energy", "boolean_energy",
    "scope", "numeric_flag", "missing_increment", "numeric_increment_flag", "initial_increment",
    "increment_overflow", "failed", "time", "current", "energy_defect", "current_defect"])
def test_energy_audit_rejects_invalid_input_and_detects_real_defects(change):
    sim, *_ = driven_film()
    history = sim.solve_transient()
    state = history[1]
    if change == "missing_energy": del state["dielectric_energy_J"]
    elif change == "negative_energy": state["dielectric_energy_J"] = -1.
    elif change == "nan_energy": state["dielectric_energy_J"] = np.nan
    elif change == "boolean_energy": state["dielectric_energy_J"] = True
    elif change == "scope": state["dielectric_energy_scope"] = "all_physics"
    elif change == "numeric_flag": state["dielectric_energy_available"] = 1
    elif change == "missing_increment": del state["dielectric_energy_increment_J"]
    elif change == "numeric_increment_flag": state["dielectric_energy_increment_available"] = 1
    elif change == "initial_increment": history[0]["dielectric_energy_increment_J"] = 0.
    elif change == "increment_overflow": state["dielectric_energy_increment_J"] = np.inf
    elif change == "failed": state["valid"] = False
    elif change == "time": state["dt_s"] *= 2
    elif change == "current": state["electrode_total_currents_A"][1] = np.nan
    elif change == "energy_defect": state["dielectric_energy_J"] *= 1.01
    else: state["electrode_total_currents_A"] *= 1.01
    if change.endswith("defect"):
        result = postprocess.audit_transient_dielectric_energy(history)
        assert not result["valid"] and not result["energy_balance_validated"]
    else:
        with pytest.raises(ValueError): postprocess.audit_transient_dielectric_energy(history)


@pytest.mark.parametrize("mode", [None, True, 1, "trapezoidal", ["linear"]])
def test_invalid_voltage_quadrature_is_rejected(mode):
    sim, *_ = driven_film()
    with pytest.raises(ValueError, match="voltage_quadrature"):
        postprocess.integrate_transient_terminal_history(sim.solve_transient(), voltage_quadrature=mode)


@pytest.mark.parametrize("rtol,atol", [(True, 0.), (np.nan, 0.), (0., 0.), (1., 0.),
                                      (1e-8, -1.), (1e-8, np.inf), (1e-8, True)])
def test_invalid_energy_error_budgets_are_rejected(rtol, atol):
    sim, *_ = driven_film()
    with pytest.raises(ValueError): postprocess.audit_transient_dielectric_energy(sim.solve_transient(), rtol=rtol, atol_J=atol)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("kind", ["total", "conduction", "displacement", "dielectric", "polarization"])
def test_linear_voltage_fe_component_work_matches_independent_nls_charge(axis, kind):
    sim, x, eps, _, area = driven_film(axis, fe=True)
    history = sim.solve_transient()
    cap = capacitance(x, eps, area)
    previous_p = previous_v = 0.
    expected_q, expected_work = [], []
    for state in history[1:]:
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE)
        polarization = previous_p
        if voltage:
            polarization += -np.expm1(-state["dt_s"] / 1e-9) * (-np.sign(voltage) * 1e-6 - previous_p)
        electric = cap * (voltage - previous_v)
        polar = -area * (polarization - previous_p)
        charge = (electric + polar if kind in ("total", "displacement") else
                  (electric if kind == "dielectric" else polar if kind == "polarization" else 0.))
        expected_q.append(charge)
        if previous_v * voltage < 0.:
            span = abs(previous_v) + abs(voltage)
            expected_work.extend([.5 * charge * previous_v * abs(previous_v) / span,
                                  .5 * charge * voltage * abs(voltage) / span])
        else:
            expected_work.append(.5 * charge * (previous_v + voltage))
        previous_p, previous_v = polarization, voltage
    result = postprocess.integrate_transient_terminal_history(history, current_kind=kind, voltage_quadrature="linear")
    scale = max(abs(x) for x in expected_work)
    assert result["terminal_charge_C"]["xyz"[axis] + "_max"] == pytest.approx(math.fsum(expected_q), rel=1e-11, abs=1e-32)
    assert abs(result["supplied_energy_J"] - math.fsum(expected_work)) <= 1e-10 * scale + 1e-35
    assert result["absorbed_energy_J"] == pytest.approx(math.fsum(max(w, 0.) for w in expected_work), rel=1e-10, abs=1e-35)
    assert result["returned_energy_J"] == pytest.approx(math.fsum(max(-w, 0.) for w in expected_work), rel=1e-10, abs=1e-35)
    assert not result["energy_balance_validated"] and not result["physical_validated"]


def test_short_interval_work_avoids_intermediate_voltage_current_overflow():
    sim, *_ = driven_film()
    history = sim.solve_transient()[:2]
    history[0]["electrode_voltages_V"] = np.array([-1e200, 0.])
    history[1]["electrode_voltages_V"] = np.array([1e200, 0.])
    history[1]["time_s"] = history[1]["dt_s"] = 1e-200
    history[1]["electrode_total_currents_A"] = np.array([1e200, -1e200])
    # Instantaneous V*I overflows, while integrated work and mean net power
    # have finite representations. Each half contributes a triangle.
    result = postprocess.integrate_transient_terminal_history(history, voltage_quadrature="linear")
    assert result["supplied_energy_J"] == 0. and result["mean_source_power_W"] == 0.
    assert result["absorbed_energy_J"] == pytest.approx(2.5e199, rel=1e-14, abs=0.)
    assert result["returned_energy_J"] == pytest.approx(2.5e199, rel=1e-14, abs=0.)


@pytest.mark.parametrize("multipliers", [(1, 1), (1, 2), (-1, 1)])
def test_subnormal_voltage_is_not_lost_before_multiplication_by_charge(multipliers):
    sim, *_ = driven_film()
    history = sim.solve_transient()[:2]
    smallest = float(np.nextafter(0., 1.))
    v0, v1 = (smallest * m for m in multipliers)
    history[0]["electrode_voltages_V"] = np.array([v0, 0.])
    history[1]["electrode_voltages_V"] = np.array([v1, 0.])
    history[1]["time_s"] = history[1]["dt_s"] = 1.
    history[1]["electrode_total_currents_A"] = np.array([1e308, -1e308])
    expected = float(Fraction(1e308) * (Fraction(v0) + Fraction(v1)) / 2)
    result = postprocess.integrate_transient_terminal_history(history, voltage_quadrature="linear")
    assert result["supplied_energy_J"] == pytest.approx(expected, rel=1e-14, abs=0.)
    if v0 < 0.:
        triangle = float(Fraction(1e308) * Fraction(smallest) / 4)
        assert result["absorbed_energy_J"] == pytest.approx(triangle, rel=1e-14, abs=0.)
        assert result["returned_energy_J"] == pytest.approx(triangle, rel=1e-14, abs=0.)


@pytest.mark.parametrize("quadrature", ["endpoint", "linear"])
def test_unrepresentable_source_work_cannot_be_reported_as_zero(quadrature):
    sim, *_ = driven_film()
    history = sim.solve_transient()[:2]
    history[0]["electrode_voltages_V"] = history[1]["electrode_voltages_V"] = np.array([1e-200, 0.])
    history[1]["time_s"] = history[1]["dt_s"] = 1.
    history[1]["electrode_total_currents_A"] = np.array([1e-200, -1e-200])
    with pytest.raises(ValueError, match="represented"):
        postprocess.integrate_transient_terminal_history(history, voltage_quadrature=quadrature)
