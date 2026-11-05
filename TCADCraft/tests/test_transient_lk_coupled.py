"""Independent simultaneous Poisson/LK and carrier BE references."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_energy
from tcad.core import PyDeviceSimulator
from tcad.simulator import Simulator
from test_fe_transient_feedback import dielectric
from test_transient_displacement import film
from test_transient_voltage_waveforms import driven_film, CLOCK, VOLTAGE
from test_transient_selfconsistent import central_cell, bernoulli, QE, EPS, VT
from test_physical_step_commit import high_level


def simultaneous_film_step(x, eps, mask, old, dt, voltage, imprint=0., depol=0.):
    """Solve a 2N block system directly; no native/local-root elimination."""
    count = len(x)
    lap = np.zeros((count, count)); div = np.zeros_like(lap); grad = np.zeros_like(lap)
    for i in range(count):
        left, right = max(i-1, 0), min(i+1, count-1)
        grad[i, left], grad[i, right] = 1/(x[right]-x[left]), -1/(x[right]-x[left])
        if i in (0, count-1):
            lap[i, i] = 1.
            continue
        cell = .5*(x[i+1]-x[i-1])
        for nbr, sign in ((i-1, -1), (i+1, 1)):
            face = 2*eps[i]*eps[nbr]/(eps[i]+eps[nbr])
            coefficient = face/(cell*abs(x[nbr]-x[i]))
            lap[i, nbr] += coefficient; lap[i, i] -= coefficient
            div[i, i] += sign*face*mask[i]/(2*cell*eps[i])
            div[i, nbr] += sign*face*mask[nbr]/(2*cell*eps[nbr])
    a = -1e8 + (1/(depol*8.854187817e-12) if depol else 0.)
    beta, rate = 1e12, .1/dt
    guess = np.r_[voltage*x/x[-1], old]
    scales = np.r_[np.max(abs(lap), axis=1), np.full(count, abs(a+rate))]
    scales[count:][mask == 0] = 1.
    def equations(value):
        phi, polarization = value[:count], value[count:]
        f = np.r_[lap@phi-div@polarization,
                  a*polarization+beta*polarization**3+rate*(polarization-old)+imprint-grad@phi]
        f[0] = phi[0]; f[count-1] = phi[-1]-voltage
        f[count:][mask == 0] = polarization[mask == 0]
        return f/scales
    for _ in range(80):
        f = equations(guess)
        if np.max(abs(f)) < 1e-14:
            return guess[:count], guess[count:]
        p = guess[count:]
        jac = np.block([[lap, -div], [-grad, np.diag(a+rate+3*beta*p*p)]])
        for i in np.flatnonzero(mask == 0):
            jac[count+i] = 0.; jac[count+i, count+i] = 1.
        direction = np.linalg.solve(jac/scales[:, None], -f)
        damping = 1.
        while np.max(abs(equations(guess+damping*direction))) > np.max(abs(f)) and damping > 1e-8:
            damping *= .5
        guess += damping*direction
    raise AssertionError("independent simultaneous film solve did not converge")


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("layered", [False, True])
@pytest.mark.parametrize("driven", [False, True])
def test_simultaneous_poisson_lk_matches_independent_block_system(axis, stretched, layered, driven):
    if driven:
        sim, x, eps, mask, _ = driven_film(axis, model=0, fe=True, stretched=stretched, layered=layered, dt=.19e-9)
    else:
        sim, x, eps, mask, _ = film(axis, 0, stretched, layered)
    sim.set_tolerance(1e-12)
    sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_material_field(False)  # Explicit legacy central-field equations below.
    history = sim.solve_transient()
    old = np.zeros(len(x))
    for state in history:
        assert state["valid"] and state["lk_coupled"]
        if not state["dt_s"]:
            continue
        voltage = np.interp(state["time_s"], CLOCK, VOLTAGE) if driven else -.01
        phi, p = simultaneous_film_step(x, eps, mask, old, state["dt_s"], voltage)
        np.testing.assert_allclose(state["phi"], phi, rtol=1e-9, atol=5e-12)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], p, rtol=1e-8, atol=1e-12)
        np.testing.assert_array_equal(state["lk_drive_field_V_per_m"],
            np.column_stack([state["Ex"], state["Ey"], state["Ez"]]).ravel())
        old = p
    result = audit_transient_lk_energy(history)
    assert result["valid"] and result["lk_coupled"] and not result["energy_balance_validated"]


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("depol", [0., 30.])
def test_imprint_and_extra_depolarization_in_simultaneous_equations(axis, depol):
    sim, x, eps, mask, _ = film(axis, 0, True, True)
    sim.set_ferroelectric_builtin_field(2e5); sim.set_ferroelectric_depol(depol)
    sim.set_transient_t_final(1e-10); sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_material_field(False)  # This reference tests the legacy discretization.
    state = sim.solve_transient()[-1]
    phi, p = simultaneous_film_step(x, eps, mask, np.zeros(9), 1e-10, -.01, 2e5, depol)
    assert state["valid"]
    np.testing.assert_allclose(state["phi"], phi, rtol=1e-9, atol=1e-11)
    np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], p, rtol=1e-8, atol=1e-12)


def carrier_reference(nn, pp, old_p, dt, x, scale, alpha=1e8):
    left, right = np.diff(x); cell = .5*(left+right)
    geometric_rate = (1/left+1/right)/cell
    an, ap = dt*.1*VT*geometric_rate, dt*.05*VT*geometric_rate
    def at(phi):
        u = phi/VT
        n = (nn+an*bernoulli(-u))/(1+an*bernoulli(u))
        p = (pp+ap*bernoulli(u))/(1+ap*bernoulli(-u))
        fields = [-phi/left, 0., phi/right]
        polarization = []
        for field, previous in zip(fields, old_p):
            roots = np.roots([1e12, 0., alpha+.1/dt, -(.1/dt*previous+field)])
            polarization.append(next(root.real for root in roots if abs(root.imag) < 1e-9))
        polarization = np.array(polarization)
        div = .5*(polarization[2]-polarization[0])/cell
        residual = -EPS*geometric_rate*phi+QE*scale*(p-n+.15)-div
        return residual, n, p, polarization
    low, high = -.25, .25
    assert at(low)[0] > 0 > at(high)[0]
    for _ in range(90):
        mid = .5*(low+high)
        if at(mid)[0] > 0:
            low = mid
        else:
            high = mid
    phi = .5*(low+high)
    _, n, p, polarization = at(phi)
    return phi, n, p, polarization


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("scale", [1e16, 1e19])
def test_mobile_carriers_and_lk_simultaneously_match_independent_scalar_reference(axis, stretched, log_space, scale):
    sim, x, nn, pp = central_cell(scale, log_space, axis, stretched)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), 1e8, 1e12)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_polar_axis(axis)
    sim.set_ferroelectric_gamma(.1); sim.set_transient_lk_coupled(True)
    sim.set_transient_lk_material_field(False)  # The scalar reference uses legacy centred E.
    history = sim.solve_transient(); old_p = np.zeros(3)
    for state in history:
        assert state["valid"] and not state["phi_frozen"] and not state["majority_frozen"]
        if not state["dt_s"]:
            continue
        phi, nn, pp, old_p = carrier_reference(nn, pp, old_p, state["dt_s"], x, scale)
        np.testing.assert_allclose(state["phi"], [0., phi, 0.], rtol=1e-8, atol=1e-11)
        np.testing.assert_allclose(state["n"]/scale, [1., nn, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["p"]/scale, [1., pp, 1.], rtol=1e-8)
        np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, axis], old_p, rtol=1e-8, atol=1e-12)
    assert audit_transient_lk_energy(history)["valid"]


def test_split_error_is_observable_and_coupled_final_field_satisfies_lk():
    split, x, eps, mask, _ = film(0, 0, True, True)
    coupled, *_ = film(0, 0, True, True)
    coupled.set_transient_lk_coupled(True)
    first, second = split.solve_transient(), coupled.solve_transient()
    assert max(abs(first[1]["P"]-second[1]["P"])) > 1e-6
    assert max(abs(first[1]["lk_drive_field_V_per_m"].reshape(-1, 3)[:, 0]-first[1]["Ex"])) > 1e4
    assert audit_transient_lk_energy(second)["valid"]
    wrong = deepcopy(second)
    wrong[1]["lk_drive_field_V_per_m"] = first[1]["lk_drive_field_V_per_m"]
    with pytest.raises(ValueError, match="accepted final field"):
        audit_transient_lk_energy(wrong)


@pytest.mark.parametrize("case", ["model1", "model2", "model3", "disabled", "nonmonotone"])
def test_unsupported_mode_rejected_without_consuming_state(case):
    sim, _ = dielectric(final=1e-10)
    original = sim.solve_transient()[-1]["P"].copy()
    sim.set_transient_lk_coupled(True)
    if case.startswith("model"):
        sim.set_ferroelectric_model(int(case[-1]))
    elif case == "disabled":
        sim.set_ferroelectric_enabled(False); sim.set_ferroelectric_gamma(0.)
    else:
        sim.set_transient_dt(1e-7); sim.set_transient_t_final(1e-7)
    with pytest.raises(ValueError, match="coupled LK"):
        sim.solve_transient()
    sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_model(0); sim.set_ferroelectric_gamma(.1)
    sim.set_transient_dt(1e-10); sim.set_transient_t_final(0.)
    np.testing.assert_array_equal(sim.solve_transient()[0]["P"], original)


def test_failed_coupled_attempt_rolls_back_and_retry_matches_fresh():
    sim, *_ = driven_film(model=0, fe=True, layered=True)
    sim.set_transient_lk_coupled(True); sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert not failed[-1]["valid"] and failed[-1]["dt_s"] == 0.
    np.testing.assert_array_equal(failed[0]["P"], failed[-1]["P"])
    assert not failed[-1]["lk_energy_available"]
    sim.set_gummel_max_iter(80)
    retry = sim.solve_transient()
    fresh, *_ = driven_film(model=0, fe=True, layered=True)
    fresh.set_transient_lk_coupled(True)
    direct = fresh.solve_transient()
    for actual, expected in zip(retry, direct):
        for key in ("phi", "n", "p", "P"):
            np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("invalid", [0, 1, "true", None, [], np.array([True])])
def test_native_and_high_level_mode_require_boolean(invalid):
    sim, _ = dielectric()
    with pytest.raises(ValueError, match="boolean"):
        sim.set_transient_lk_coupled(invalid)
    host = type("Host", (), {"_sim": sim})()
    with pytest.raises(ValueError, match="boolean"):
        Simulator.set_transient_lk_coupled(host, invalid)


def test_high_level_option_and_mode_metadata():
    sim = high_level()
    sim.set_transient_lk_coupled(np.bool_(True))
    sim.set_transient_lk_coupled(False)
    assert hasattr(sim._sim, "set_transient_lk_coupled")


@pytest.mark.parametrize("case", ["type", "change"])
def test_energy_audit_rejects_invalid_or_mixed_mode_metadata(case):
    sim, _ = dielectric(final=1e-10)
    sim.set_transient_lk_coupled(True)
    history = sim.solve_transient()
    history[-1]["lk_coupled"] = 1 if case == "type" else False
    with pytest.raises(ValueError):
        audit_transient_lk_energy(history)


def linear_multidimensional_case(dimensions, partial, overrides):
    shape = [4, 3, 3 if dimensions == 3 else 1]
    positions = [np.array([0., .3, 1.6, 3.])*1e-8, np.array([0., .8, 2.])*1e-8,
                 np.array([0., 1.1, 3.])*1e-8 if dimensions == 3 else np.array([0.])]
    spacing = [1e-8, 1e-8, 4e-7]
    count = int(np.prod(shape))
    sim = PyDeviceSimulator(*shape, *spacing)
    for method, x in zip((sim.set_x_positions, sim.set_y_positions, sim.set_z_positions), positions):
        method(x)
    eps = 8.854187817e-12*(10+.2*np.arange(count))
    mask = ((np.arange(count)%4 != 0) if partial else np.ones(count, dtype=bool)).astype(np.int8)
    boundary = {i: (0. if i%4 == 0 else .003) for i in range(count) if i%4 in (0, 3)}
    sim.set_permittivity(eps); sim.set_mobility(np.zeros(count), np.zeros(count)); sim.set_doping(np.zeros(count))
    sim.set_effective_dos(np.full(count, 1e16), np.full(count, 1e16)); sim.set_bandgap(np.full(count, 6.))
    sim.set_dirichlet_potential(boundary)
    sim.set_initial_guess(np.zeros(count), np.zeros(count), np.zeros(count))
    sim.set_ferroelectric_enabled(True); sim.set_ferroelectric_params(mask, 1e9, 1e-6)
    sim.set_ferroelectric_model(0); sim.set_ferroelectric_gamma(.1)
    sim.set_transient_lk_coupled(True); sim.set_transient_dt(1e-10); sim.set_transient_t_final(2e-10)
    sim.set_gummel_max_iter(80); sim.set_tolerance(1e-13)
    lap = np.zeros((count, count)); grad = [np.zeros_like(lap) for _ in range(3)]
    div = [np.zeros_like(lap) for _ in range(3)]
    faces = [np.zeros(count) for _ in range(6)]
    strides = [1, shape[0], shape[0]*shape[1]]
    for node in range(count):
        coordinates = [node%shape[0], node//shape[0]%shape[1], node//strides[2]]
        for axis, (coordinate, nodes, stride, x) in enumerate(zip(coordinates, shape, strides, positions)):
            if nodes == 1:
                continue
            lo, hi = max(coordinate-1, 0), min(coordinate+1, nodes-1)
            grad[axis][node, node+(lo-coordinate)*stride] = 1/(x[hi]-x[lo])
            grad[axis][node, node+(hi-coordinate)*stride] = -1/(x[hi]-x[lo])
            left_width = x[coordinate]-x[coordinate-1] if coordinate else x[1]-x[0]
            right_width = x[coordinate+1]-x[coordinate] if coordinate+1 < nodes else x[-1]-x[-2]
            cell = .5*(left_width+right_width)
            for sign in (-1, 1):
                neighbour_coordinate = coordinate+sign
                if not 0 <= neighbour_coordinate < nodes:
                    continue
                nbr = node+sign*stride
                face = 2*eps[node]*eps[nbr]/(eps[node]+eps[nbr])
                if overrides:
                    face *= 1.1+.1*axis
                faces[2*axis+(sign < 0)][node] = face
                if node in boundary:
                    continue
                coefficient = face/(cell*abs(x[coordinate]-x[neighbour_coordinate]))
                lap[node, nbr] += coefficient; lap[node, node] -= coefficient
                div[axis][node, node] += sign*face*mask[node]/(2*cell*eps[node])
                div[axis][node, nbr] += sign*face*mask[nbr]/(2*cell*eps[nbr])
    if overrides:
        sim.set_edge_permittivity(*faces)
    for node in boundary:
        lap[node, node] = 1.
    matrix = np.zeros((4*count, 4*count)); matrix[:count, :count] = lap
    rate, a = .1/1e-10, 1e9+.1/1e-10
    for axis in range(3):
        block = slice((axis+1)*count, (axis+2)*count)
        matrix[:count, block] = -div[axis]
        matrix[block, :count] = -grad[axis]*mask[:, None]
        matrix[block, block] = np.diag(np.where(mask, a, 1.))
    return sim, count, matrix, boundary, mask, rate


@pytest.mark.parametrize("dimensions", [2, 3])
@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("overrides", [False, True])
def test_multidimensional_nonzero_feedback_matches_independent_four_block_linear_limit(dimensions, partial, overrides):
    sim, count, matrix, boundary, mask, rate = linear_multidimensional_case(dimensions, partial, overrides)
    history = sim.solve_transient()
    old = np.zeros((count, 3))
    for state in history[1:]:
        rhs = np.zeros(4*count)
        for node, voltage in boundary.items():
            rhs[node] = voltage
        for axis in range(3):
            rhs[(axis+1)*count:(axis+2)*count] = rate*old[:, axis]*mask
        row_scales = np.max(abs(matrix), axis=1)
        result = np.linalg.solve(matrix/row_scales[:, None], rhs/row_scales)
        assert state["valid"]
        np.testing.assert_allclose(state["phi"], result[:count], rtol=1e-9, atol=5e-13)
        expected_p = result[count:].reshape(3, count).T
        np.testing.assert_allclose(state["P"].reshape(count, 3), expected_p, rtol=1e-8, atol=5e-13)
        assert np.max(abs(expected_p)) > 1e-6
        old = expected_p
    assert audit_transient_lk_energy(history)["valid"]


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_coupled_continuation_reuses_accepted_p_once_per_new_run(axis):
    sim, x, eps, mask, _ = film(axis, 0, True, True)
    sim.set_transient_lk_coupled(True); sim.set_transient_t_final(1e-10)
    sim.set_transient_lk_material_field(False)  # Preserve the explicit central-field reference.
    old = np.zeros(9)
    for voltage in (-.01, .002, -.003, 0.):
        sim.set_dirichlet_potential({0: 0., 8: voltage})
        history = sim.solve_transient()
        np.testing.assert_allclose(history[0]["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-12)
        phi, old = simultaneous_film_step(x, eps, mask, old, 1e-10, voltage)
        np.testing.assert_allclose(history[-1]["phi"], phi, rtol=1e-8, atol=1e-11)
        np.testing.assert_allclose(history[-1]["P"].reshape(-1, 3)[:, axis], old, rtol=1e-8, atol=1e-12)
        assert audit_transient_lk_energy(history)["valid"]


def test_actual_short_final_step_can_make_coarse_configured_dt_monotone():
    sim, _ = dielectric(dt=1e-7, final=1e-10)
    sim.set_transient_lk_coupled(True)
    history = sim.solve_transient()
    assert len(history) == 2 and history[-1]["dt_s"] == 1e-10
    assert audit_transient_lk_energy(history)["valid"]


def test_voltage_knots_can_make_coarse_configured_dt_monotone():
    sim, _ = dielectric(dt=1e-7, final=3e-10, voltage=0.)
    sim.set_transient_voltage_waveforms([0., 1e-10, 2e-10, 3e-10], {8: [0., -.01, 0., .01]})
    sim.set_transient_lk_coupled(True)
    history = sim.solve_transient()
    assert len(history) == 4 and max(s["dt_s"] for s in history) < 1.01e-10
    assert audit_transient_lk_energy(history)["valid"]
