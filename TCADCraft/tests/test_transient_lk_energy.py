"""Independent cubic/polynomial LK energy, splitting and rejection checks."""
from copy import deepcopy
from decimal import Decimal, localcontext

import numpy as np
import pytest

import tcad.postprocess as postprocess
from tcad.core import PyDeviceSimulator
from test_fe_transient_feedback import dielectric
from test_transient_voltage_waveforms import driven_film
from test_transient_selfconsistent import central_cell


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("alpha", [-1e8, 1e8])
@pytest.mark.parametrize("imprint,depol", [(0., 0.), (2e5, 30.)])
def test_uniform_film_independent_cubic_free_energy_and_gamma_loss(axis, stretched, alpha, imprint, depol):
    sim, x, _, _, area = driven_film(axis, model=0, stretched=stretched, fe=True, dt=.19e-9)
    sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), alpha, 1e12)
    sim.set_ferroelectric_gamma(.1)
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_builtin_field(imprint)
    sim.set_ferroelectric_depol(depol)
    history = sim.solve_transient()
    a = alpha + (1/(depol*8.854187817e-12) if depol else 0.)
    old = 0.
    volume = area*(x[-1]-x[0])
    previous_energy = 0.
    for state in history:
        assert state["valid"] and state["lk_energy_available"]
        assert sum(state["lk_node_volumes_m3"]) == pytest.approx(volume, rel=1e-14)
        p = state["P"].reshape(-1, 3)[0, axis]
        energy = volume*(.5*a*p**2 + .25*1e12*p**4 + imprint*p)
        assert state["lk_free_energy_J"] == pytest.approx(energy, rel=1e-11, abs=1e-31)
        if state["dt_s"]:
            field = state["lk_drive_field_V_per_m"].reshape(-1, 3)[0, axis]
            rate = .1/state["dt_s"]
            roots = np.roots([1e12, 0., a+rate, -(rate*old+field-imprint)])
            real = [r.real for r in roots if abs(r.imag) < 1e-10]
            assert any(np.isclose(p, value, rtol=1e-10) for value in real)
            d = p-old
            assert state["lk_free_energy_increment_J"] == pytest.approx(energy-previous_energy, rel=1e-9, abs=1e-28)
            assert state["lk_dissipation_J"] == pytest.approx(volume*.1*d*d/state["dt_s"], rel=1e-9, abs=1e-30)
            assert state["lk_field_work_J"] == pytest.approx(volume*field*d, rel=1e-9, abs=1e-28)
        old, previous_energy = p, energy
    result = postprocess.audit_transient_lk_energy(history)
    assert result["valid"] and result["lk_kinetics_validated"]
    assert not result["energy_balance_validated"] and not result["physical_validated"]
    assert result["lk_dissipation_J"] >= 0.


def test_layered_feedback_uses_actual_pre_kinetic_field_and_geometric_mask_volume():
    mask = np.zeros(9, dtype=np.int8); mask[2:7] = 1
    x = np.array([0., .2, .7, 1.4, 2.5, 4., 5.8, 7., 8.])*1e-8
    sim, _ = dielectric(mask=mask, positions=x, final=3e-10)
    history = sim.solve_transient()
    expected_volumes = np.r_[np.diff(x)/2, 0.] + np.r_[0., np.diff(x)/2]
    expected_volumes *= mask
    np.testing.assert_allclose(history[0]["lk_node_volumes_m3"], expected_volumes, rtol=1e-14)
    assert np.max(abs(history[1]["lk_drive_field_V_per_m"].reshape(-1, 3)[:, 0]-history[1]["Ex"])) > 1e4
    assert postprocess.audit_transient_lk_energy(history)["lk_kinetics_validated"]
    wrong = deepcopy(history)
    for state in wrong[1:]:
        state["lk_drive_field_V_per_m"] = np.column_stack([state["Ex"], state["Ey"], state["Ez"]]).ravel()
    assert not postprocess.audit_transient_lk_energy(wrong)["valid"]


@pytest.mark.parametrize("dimensions", [2, 3])
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_multidimensional_dual_volumes_and_vector_kinetics(dimensions, axis):
    shape = [3, 3, 3 if dimensions == 3 else 1]
    spacings = [1e-6, 2e-6, 3e-6]
    sim = PyDeviceSimulator(*shape, *spacings)
    size = int(np.prod(shape))
    phi, boundary = [], {}
    for k in range(shape[2]):
        for j in range(shape[1]):
            for i in range(shape[0]):
                value = -.01*i-.02*j+.005*k
                idx = len(phi); phi.append(value)
                if i in (0, 2) or j in (0, 2) or (dimensions == 3 and k in (0, 2)):
                    boundary[idx] = value
    sim.set_permittivity(np.full(size, 20*8.854187817e-12))
    sim.set_mobility(np.zeros(size), np.zeros(size)); sim.set_doping(np.zeros(size))
    sim.set_dirichlet_potential(boundary)
    sim.set_initial_guess(np.array(phi), np.zeros(size), np.zeros(size))
    sim.set_gummel_max_iter(80); sim.set_tolerance(1e-11)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(size, dtype=np.int8), 1e8, 1e12)
    sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_gamma(.1)
    sim.set_ferroelectric_polar_axis(axis)
    sim.set_transient_dt(1e-10); sim.set_transient_t_final(2e-10)
    history = sim.solve_transient()
    assert all(s["valid"] for s in history)
    expected_volume = np.prod([spacings[c]*(shape[c]-1 if shape[c] > 1 else 1) for c in range(3)])
    assert sum(history[0]["lk_node_volumes_m3"]) == pytest.approx(expected_volume, rel=1e-14)
    result = postprocess.audit_transient_lk_energy(history)
    assert result["lk_kinetics_validated"] and not result["energy_balance_validated"]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_local_lk_identity_with_mobile_carrier_feedback_does_not_claim_total_energy(axis):
    sim, _, _, _ = central_cell(1e16, False, axis, True, final=1e-10)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), 1e8, 1e12)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_gamma(.1)
    result = postprocess.audit_transient_lk_energy(sim.solve_transient())
    assert result["valid"] and not result["energy_balance_validated"]


def test_signed_be_correction_can_be_negative_and_is_not_heat():
    sim, _ = dielectric(final=1e-10, voltage=-.001)
    history = sim.solve_transient()
    state = history[-1]
    assert state["lk_be_correction_J"] < 0.
    assert state["lk_dissipation_J"] > 0.
    result = postprocess.audit_transient_lk_energy(history)
    assert result["valid"] and result["be_discretization_correction_J"] < 0.


@pytest.mark.parametrize("key", ["lk_free_energy_increment_J", "lk_dissipation_J", "lk_field_work_J", "lk_be_correction_J"])
def test_independent_native_energy_component_corruption_is_rejected(key):
    sim, _ = dielectric(final=1e-10)
    history = sim.solve_transient()
    history[-1][key] *= 1.01
    assert not postprocess.audit_transient_lk_energy(history)["valid"]


def test_equal_opposite_local_field_corruption_cannot_cancel_in_total_work():
    sim, _ = dielectric(final=1e-10)
    history = sim.solve_transient()
    # Two equal-volume interior nodes, equal polarization changes: work sum
    # unchanged, while both local kinetic equations are violated.
    field = history[-1]["lk_drive_field_V_per_m"]
    field[3] *= 1.01; field[6] *= .99
    result = postprocess.audit_transient_lk_energy(history)
    assert not result["valid"] and result["max_local_relative_residual"] > 1e-4


@pytest.mark.parametrize("model", [1, 2, 3])
def test_other_fe_models_do_not_inherit_lk_energy(model):
    sim, _ = dielectric(model=model, gamma=0., final=1e-10)
    history = sim.solve_transient()
    assert all(not s["lk_energy_available"] for s in history)
    assert all("lk_free_energy_J" not in s for s in history)
    with pytest.raises(ValueError):
        postprocess.audit_transient_lk_energy(history)


@pytest.mark.parametrize("case", ["classical", "fraction", "empty_mask"])
def test_unavailable_geometry_or_model_is_explicit(case):
    sim, _ = dielectric(final=1e-10)
    if case == "classical":
        sim.set_ferroelectric_enabled(False); sim.set_ferroelectric_gamma(0.)
    elif case == "fraction":
        sim.set_charge_volume_fraction(np.full(9, .5))
    else:
        sim.set_ferroelectric_params(np.zeros(9, dtype=np.int8), -1e8, 1e12)
    history = sim.solve_transient()
    assert all(not s["lk_energy_available"] for s in history)


def test_failed_attempt_has_no_kinetic_energy_and_retry_is_identical():
    mask = np.zeros(9, dtype=np.int8); mask[2:7] = 1
    sim, _ = dielectric(mask=mask, final=1e-10)
    sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]["valid"] and not failed[-1]["lk_energy_available"]
    assert "lk_dissipation_J" not in failed[-1]
    with pytest.raises(ValueError):
        postprocess.audit_transient_lk_energy(failed)
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, _ = dielectric(mask=mask, final=1e-10)
    direct = fresh.solve_transient()
    for actual, expected in zip(retry, direct):
        for key in ("lk_free_energy_J", "lk_free_energy_increment_J", "lk_dissipation_J", "lk_field_work_J", "lk_be_correction_J"):
            if key in expected:
                assert actual[key] == expected[key]


@pytest.mark.parametrize("key,value", [
    ("lk_energy_available", 1), ("lk_energy_increment_available", "true"),
    ("valid", None), ("converged", np.nan), ("time_s", 0.),
    ("attempted_time_s", 3e-10), ("dt_s", 2e-10), ("lk_free_energy_J", np.inf),
    ("lk_dissipation_J", -1.), ("lk_energy_scope", "device_energy"),
    ("lk_parameters", np.ones(7)), ("lk_node_volumes_m3", [-1.]*9),
    ("lk_drive_field_V_per_m", np.zeros(26)), ("lk_polarization_increment_C_per_m2", np.zeros(27)),
])
def test_invalid_history_is_rejected(key, value):
    sim, _ = dielectric(final=1e-10)
    history = sim.solve_transient(); history[-1][key] = value
    with pytest.raises(ValueError):
        postprocess.audit_transient_lk_energy(history)


@pytest.mark.parametrize("kwargs", [{"rtol": True}, {"rtol": 1.}, {"rtol": 0.}, {"atol_J": -1.}, {"atol_J": "0"}])
def test_invalid_error_budget(kwargs):
    sim, _ = dielectric(final=1e-10)
    with pytest.raises(ValueError):
        postprocess.audit_transient_lk_energy(sim.solve_transient(), **kwargs)


def test_stable_native_increment_is_checked_with_decimal_polynomial_difference():
    sim, x = dielectric(final=1e-7, dt=1e-7)
    sim.solve_transient()  # Establish a large persistent Landau energy.
    sim.set_transient_dt(1e-26); sim.set_transient_t_final(1e-26)
    history = sim.solve_transient()
    state = history[-1]
    np.testing.assert_array_equal(history[0]["P"], state["P"])
    assert history[0]["lk_free_energy_J"] == state["lk_free_energy_J"]
    assert state["lk_free_energy_increment_J"] != 0.
    with localcontext() as ctx:
        ctx.prec = 80
        p = Decimal.from_float(float(state["P"][0]))
        d = Decimal.from_float(float(state["lk_polarization_increment_C_per_m2"][0]))
        def f(value):
            return Decimal('-5e7')*value**2 + Decimal('2.5e11')*value**4
        expected = Decimal.from_float(float(x[-1]))*(f(p)-f(p-d))
        assert state["lk_free_energy_increment_J"] == pytest.approx(float(expected), rel=1e-10, abs=0.)
    assert postprocess.audit_transient_lk_energy(history)["valid"]
    corrupted = deepcopy(history)
    corrupted[-1]["lk_free_energy_increment_J"] *= 1.01
    assert not postprocess.audit_transient_lk_energy(corrupted)["valid"]


@pytest.mark.parametrize("extreme", ["overflow", "underflow"])
def test_native_unrepresentable_free_energy_is_unavailable(extreme):
    sim, _, _, _, _ = driven_film(fe=True, model=0)
    sim.set_transient_dt(1e-10); sim.set_transient_t_final(1e-10)
    if extreme == "overflow":
        # Large extrusion with representable individual nodal volumes, but
        # unrepresentable total Landau energy.
        sim = PyDeviceSimulator(9, 1, 1, 1e-8, 1e158, 1e158)
        sim.set_permittivity(np.full(9, 20*8.854187817e-12))
        sim.set_mobility(np.zeros(9), np.zeros(9)); sim.set_doping(np.zeros(9))
        sim.set_dirichlet_potential({0: 0., 8: -.1})
        sim.set_initial_guess(np.linspace(0., -.1, 9), np.zeros(9), np.zeros(9))
        sim.set_ferroelectric_enabled(True)
        sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), -1e8, 1e12)
        sim.set_ferroelectric_model(0); sim.set_ferroelectric_gamma(.1)
        sim.set_transient_dt(1e-10); sim.set_transient_t_final(1e-10)
    else:
        sim.set_transient_voltage_waveforms([0., 1e-10], {8: [0., 1e-180]})
    state = sim.solve_transient()[-1]
    assert state["valid"] and not state["lk_energy_available"]
    assert not state["lk_energy_increment_available"]
    assert "lk_free_energy_J" not in state and "lk_dissipation_J" not in state


@pytest.mark.parametrize("case", ["initial_interval", "initial_time", "parameter_change", "volume_change", "zero_volume", "zero_beta", "invalid_axis", "nan_drive"])
def test_missing_or_inconsistent_metadata_is_rejected(case):
    sim, _ = dielectric(final=1e-10)
    history = sim.solve_transient()
    if case == "initial_interval":
        history[0]["lk_dissipation_J"] = 0.
    elif case == "initial_time":
        history[0]["time_s"] = 1e-10
    elif case == "parameter_change":
        history[-1]["lk_parameters"][0] *= 1.01
    elif case == "volume_change":
        history[-1]["lk_node_volumes_m3"][1] *= 1.01
    elif case == "zero_volume":
        history[0]["lk_node_volumes_m3"][:] = 0.
    elif case == "zero_beta":
        history[0]["lk_parameters"][1] = 0.
    elif case == "invalid_axis":
        history[0]["lk_parameters"][5] = .5
    else:
        history[-1]["lk_drive_field_V_per_m"][0] = np.nan
    with pytest.raises(ValueError):
        postprocess.audit_transient_lk_energy(history)


def rk4_reference(final=1e-9, steps=10000):
    """Independent continuous ODE plus integrated gamma*(dP/dt)^2."""
    alpha, beta, gamma, field = 1e8, 1e12, .1, 1.25e6
    dt = final/steps
    p = loss = 0.
    def derivative(p):
        velocity = (field-alpha*p-beta*p**3)/gamma
        return velocity, gamma*velocity**2
    for _ in range(steps):
        k1, l1 = derivative(p)
        k2, l2 = derivative(p+.5*dt*k1)
        k3, l3 = derivative(p+.5*dt*k2)
        k4, l4 = derivative(p+dt*k3)
        p += dt*(k1+2*k2+2*k3+k4)/6
        loss += dt*(l1+2*l2+2*l3+l4)/6
    return p, loss


def convergence_rows():
    reference_p, reference_loss_density = rk4_reference()
    rows = []
    for count in (10, 20, 40, 80):
        sim, x = dielectric(alpha=1e8, dt=1e-9/count, final=1e-9)
        history = sim.solve_transient()
        audited = postprocess.audit_transient_lk_energy(history)
        assert audited["valid"]
        p = history[-1]["P"][0]
        loss = audited["lk_dissipation_J"]
        correction = audited["be_discretization_correction_J"]
        rows.append(dict(steps=count, dt_s=1e-9/count, final_p_C_per_m2=float(p),
            reference_p_C_per_m2=reference_p, polarization_error=float(abs(p-reference_p)),
            lk_dissipation_J=loss, reference_dissipation_J=reference_loss_density*x[-1],
            dissipation_error_J=abs(loss-reference_loss_density*x[-1]),
            be_correction_J=correction, max_local_relative_residual=audited["max_local_relative_residual"]))
    return rows


def test_backward_euler_polarization_and_loss_converge_to_independent_continuous_ode():
    rows = convergence_rows()
    for key in ("polarization_error", "dissipation_error_J", "be_correction_J"):
        errors = np.array([r[key] for r in rows])
        assert np.all(errors > 0.)
        assert np.all((errors[1:]/errors[:-1] > .4) & (errors[1:]/errors[:-1] < .6))
    p, loss_density = rk4_reference()
    # Continuous first law verified against the independently accumulated loss.
    free_energy = .5e8*p*p+.25e12*p**4
    assert 1.25e6*p == pytest.approx(free_energy+loss_density, rel=1e-12)


def test_metastable_branch_retention_and_switch_preserve_local_kinetic_identity():
    sim, x = dielectric(dt=1e-7, final=1e-7)
    assert postprocess.audit_transient_lk_energy(sim.solve_transient())["valid"]
    for voltage in (.001, .1):
        sim.set_dirichlet_potential({0: 0., 8: voltage})
        sim.set_initial_guess(voltage*x/x[-1], np.zeros(9), np.zeros(9))
        result = postprocess.audit_transient_lk_energy(sim.solve_transient())
        assert result["valid"] and result["lk_dissipation_J"] > 0.


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("dt", [.19e-9, .6e-9])
def test_uniform_source_work_separates_landau_loss_BE_and_voltage_quadrature(axis, dt):
    sim, x, eps, _, area = driven_film(axis, model=0, fe=True, dt=dt)
    history = sim.solve_transient()
    volume = area*x[-1]
    cap = eps[0]*area/x[-1]
    for old, state in zip(history, history[1:]):
        v0 = old["electrode_voltages_V"]
        v1 = state["electrode_voltages_V"]
        work = sum(.5*(v0+v1)*state["electrode_total_currents_A"])*state["dt_s"]
        electric_increment = .5*cap*(v1[1]-v0[1])*(v1[1]+v0[1])
        delta_p = state["lk_polarization_increment_C_per_m2"][axis]
        delta_field = -(v1[1]-v0[1])/x[-1]
        voltage_correction = -.5*volume*delta_field*delta_p
        expected = (electric_increment+state["lk_free_energy_increment_J"]
            +state["lk_dissipation_J"]+state["lk_be_correction_J"]+voltage_correction)
        scale = max(abs(work), abs(electric_increment), abs(state["lk_dissipation_J"]))
        assert abs(work-expected) < 1e-11*scale+1e-40
    # The reusable checker establishes only the declared local kinetic scope.
    assert not postprocess.audit_transient_lk_energy(history)["energy_balance_validated"]


@pytest.mark.parametrize("voltage", [1e-20, 1e-80, 1e-180, 1e-280])
@pytest.mark.parametrize("alpha", [-1e8, 1e8])
def test_weak_field_monotone_cubic_has_no_fixed_bisection_polarization_floor(voltage, alpha):
    sim, x = dielectric(alpha=alpha, final=1e-10, voltage=-voltage)
    state = sim.solve_transient()[-1]
    # Cubic contribution is < 1e-30 of the linear term in this regime.
    expected = (voltage/x[-1])/(alpha+.1/1e-10)
    np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], expected, rtol=1e-12, atol=0.)
    np.testing.assert_array_equal(state["P"].reshape(-1, 3)[:, 1:], 0.)
