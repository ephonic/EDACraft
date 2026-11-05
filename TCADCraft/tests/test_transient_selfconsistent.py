"""Independent Poisson/SG/BE scalar reduction for coupled classical dynamics."""

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.validation.conservation import TransientConservationTest


QE = float(native_constants()["elementary_charge_C"])
EPS = 8.854187817e-12 * 11.7
VT = .025852


def bernoulli(x):
    if abs(x) < 1e-5:
        return 1 - x / 2 + x*x / 12 - x**4 / 720
    return x / np.expm1(x)


def central_cell(scale, log_space, axis, stretched, polarity=1, *, final=2.5e-10,
                 potential_reference=True):
    shape = [1, 1, 1]
    shape[axis] = 3
    # Numerical scale stress: keep the high-density initial potential modest
    # by shortening the cell, and retain the same diffusion Courant number.
    spacing = min(1e-6, np.sqrt(1e19 / scale) * 1e-6)
    spacings = [1e-6] * 3
    spacings[axis] = spacing
    sim = PyDeviceSimulator(*shape, *spacings)
    x = np.array([0., .7, 2.1]) * spacing if stretched else np.arange(3) * spacing
    [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions][axis](x)
    sim.set_permittivity(np.full(3, EPS))
    sim.set_mobility(np.full(3, .1), np.full(3, .05))
    sim.set_doping(np.array([0., polarity * .15 * scale, 0.]))
    sim.set_effective_dos(np.full(3, scale), np.full(3, scale))
    sim.set_bandgap(np.zeros(3))
    sim.set_thermal_voltage(VT)
    sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    sim.set_newton_use_log_space(log_space)
    if potential_reference:
        sim.set_dirichlet_potential({0: 0., 2: 0.})
    sim.set_electron_bc({0: scale, 2: scale})
    sim.set_hole_bc({0: scale, 2: scale})
    nn, pp = (1.6, 1.1) if polarity > 0 else (1.1, 1.6)
    sim.set_initial_guess(np.zeros(3), scale * np.array([1., nn, 1.]),
                          scale * np.array([1., pp, 1.]))
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-11)
    time_scale = (spacing / 1e-6)**2
    sim.set_transient_dt(1e-10 * time_scale)
    sim.set_transient_t_final(final * time_scale)
    return sim, x, nn, pp


def reference_step(nn, pp, dt, x, scale, doping):
    """Eliminate carrier densities analytically, then bisect one potential."""
    left, right = np.diff(x)
    width = (left + right) / 2
    geometric_rate = (1 / left + 1 / right) / width
    kappa = QE * scale / (EPS * geometric_rate)
    if dt == 0.:
        return kappa * (pp - nn + doping), nn, pp
    an, ap = dt * .1 * VT * geometric_rate, dt * .05 * VT * geometric_rate

    def carriers(phi):
        u = phi / VT
        return ((nn + an * bernoulli(-u)) / (1 + an * bernoulli(u)),
                (pp + ap * bernoulli(u)) / (1 + ap * bernoulli(-u)))

    def residual(phi):
        n, p = carriers(phi)
        return phi - kappa * (p - n + doping)

    low, high = -10 * VT, 10 * VT
    assert residual(low) < 0 < residual(high)
    for _ in range(100):
        mid = (low + high) / 2
        if residual(mid) < 0:
            low = mid
        else:
            high = mid
    phi = (low + high) / 2
    n, p = carriers(phi)
    return phi, n, p


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("polarity", [-1, 1])
@pytest.mark.parametrize("scale", [1e16, 1e24])
def test_classical_coupled_transient_matches_scalar_poisson_sg_be(scale, polarity, log_space, stretched, axis):
    sim, x, nn, pp = central_cell(scale, log_space, axis, stretched, polarity)
    history = sim.solve_transient()
    assert len(history) == 4
    for state in history:
        assert state["valid"] and not state["phi_frozen"] and not state["majority_frozen"]
        phi, nn, pp = reference_step(nn, pp, state["dt_s"], x, scale, polarity * .15)
        np.testing.assert_allclose(state["phi"], [0., phi, 0.], rtol=2e-8, atol=1e-12)
        np.testing.assert_allclose(state["n"] / scale, [1., nn, 1.], rtol=2e-8)
        np.testing.assert_allclose(state["p"] / scale, [1., pp, 1.], rtol=2e-8)
    assert np.max(np.abs(history[-1]["phi"] - history[0]["phi"])) > 1e-8
    verdict = TransientConservationTest(integration="backward_euler", charge_atol_C=0.,
                                       tolerance=1e-5).run(lambda: history)
    assert verdict.passed, verdict.message


@pytest.mark.parametrize("log_space", [False, True])
def test_selfconsistent_failure_does_not_commit_time_or_carriers_and_retry_matches_fresh(log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, 0, True)
    sim.set_gummel_max_iter(0)
    failed = sim.solve_transient()
    assert len(failed) == 2
    assert not failed[-1]["valid"] and failed[-1]["time_s"] == 0. and failed[-1]["dt_s"] == 0.
    for name in ("phi", "n", "p"):
        np.testing.assert_array_equal(failed[-1][name], failed[0][name])
    phi, _, _ = reference_step(nn, pp, 0., x, 1e16, .15)
    assert failed[0]["phi"][1] == pytest.approx(phi, rel=1e-12)
    sim.set_gummel_max_iter(100)
    retried = sim.solve_transient()
    fresh, *_ = central_cell(1e16, log_space, 0, True)
    expected = fresh.solve_transient()
    for actual, baseline in zip(retried, expected):
        for name in ("phi", "n", "p"):
            np.testing.assert_array_equal(actual[name], baseline[name])


def test_explicit_frozen_potential_is_honored_in_classical_transient():
    sim, *_ = central_cell(1e16, False, 0, False)
    sim.set_newton_freeze_phi(True)
    history = sim.solve_transient()
    assert all(state["valid"] and state["phi_frozen"] for state in history)
    for state in history:
        np.testing.assert_array_equal(state["phi"], np.zeros(3))


def test_missing_potential_reference_is_rejected_in_coupled_mode():
    sim, *_ = central_cell(1e16, False, 0, False, potential_reference=False)
    with pytest.raises(ValueError, match="Dirichlet"):
        sim.solve_transient()


def test_fe_cannot_silently_ignore_a_frozen_potential_request():
    sim, *_ = central_cell(1e16, False, 0, False)
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(3, dtype=np.int8), -1e8, 1e12)
    sim.set_ferroelectric_gamma(.1)
    sim.set_newton_freeze_phi(True)
    with pytest.raises(ValueError, match="frozen potential"):
        sim.solve_transient()


@pytest.mark.parametrize("log_space", [False, True])
def test_initial_gauss_projection_uses_actual_charge_fraction(log_space):
    sim, x, nn, pp = central_cell(1e16, log_space, 0, True, final=0.)
    sim.set_charge_volume_fraction(np.array([1., .3, 1.]))
    state, = sim.solve_transient()
    phi, _, _ = reference_step(nn, pp, 0., x, 1e16, .15)
    np.testing.assert_allclose(state["phi"], [0., .3 * phi, 0.], rtol=1e-12)
    np.testing.assert_array_equal(state["n"], 1e16 * np.array([1., nn, 1.]))
    np.testing.assert_array_equal(state["p"], 1e16 * np.array([1., pp, 1.]))
    assert state["valid"] and not state["charge_ledger_available"]


@pytest.mark.parametrize("shape", [(5, 4, 1), (5, 4, 3)])
@pytest.mark.parametrize("all_faces", [False, True])
@pytest.mark.parametrize("stretched", [False, True])
@pytest.mark.parametrize("log_space", [False, True])
def test_multidimensional_coupled_gauss_continuity_and_mobile_charge(shape, all_faces, stretched, log_space):
    size = np.prod(shape)
    sim = PyDeviceSimulator(*shape, 1e-7, 1.3e-7, .8e-7)
    positions = [np.arange(count) * spacing for count, spacing in zip(shape, [1e-7, 1.3e-7, .8e-7])]
    widths = []
    for x in positions:
        if stretched:
            x *= 1 + .1 * np.arange(len(x))
        edge = np.diff(x)
        widths.append(np.r_[edge[0], (edge[1:] + edge[:-1]) / 2, edge[-1]] if len(x) > 1
                      else np.array([.8e-7]))
    for x, setter in zip(positions, [sim.set_x_positions, sim.set_y_positions, sim.set_z_positions]):
        setter(x)
    coords = np.array([(i, j, k) for k in range(shape[2]) for j in range(shape[1]) for i in range(shape[0])])
    contacts = (coords[:, 0] == 0) | (coords[:, 0] == shape[0] - 1)
    if all_faces:
        for axis in range(1, 3):
            if shape[axis] > 1:
                contacts |= (coords[:, axis] == 0) | (coords[:, axis] == shape[axis] - 1)
    free = ~contacts
    scale = 1e20
    eps = EPS * (1 + .2 * coords[:, 1] + .3 * coords[:, 2])
    doping = .15 * scale * np.cos(coords[:, 0])
    n0 = scale * (1 + .08 * coords[:, 1]**2 + .06 * coords[:, 2])
    p0 = scale * (1 + .04 * coords[:, 1] + .05 * coords[:, 2]**2)
    n0[free] += .5 * scale
    p0[free] += .2 * scale
    sim.set_permittivity(eps)
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(doping)
    sim.set_effective_dos(np.full(size, scale), np.full(size, scale))
    sim.set_bandgap(np.zeros(size))
    sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    sim.set_thermal_voltage(VT)
    sim.set_newton_use_log_space(log_space)
    sim.set_dirichlet_potential({int(idx): 0. for idx in np.flatnonzero(contacts)})
    sim.set_electron_bc({int(idx): float(n0[idx]) for idx in np.flatnonzero(contacts)})
    sim.set_hole_bc({int(idx): float(p0[idx]) for idx in np.flatnonzero(contacts)})
    sim.set_initial_guess(np.zeros(size), n0, p0)
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-11)
    sim.set_transient_dt(1e-12)
    sim.set_transient_t_final(2.5e-12)
    history = sim.solve_transient()
    assert len(history) == 4
    strides = [1, shape[0], shape[0] * shape[1]]
    poisson = np.zeros((size, size))
    for idx, xyz in enumerate(coords):
        if contacts[idx]:
            poisson[idx, idx] = 1
            continue
        for axis in range(3):
            for sign in (-1, 1):
                position = xyz[axis] + sign
                if 0 <= position < shape[axis]:
                    neighbor = idx + sign * strides[axis]
                    edge = abs(positions[axis][position] - positions[axis][xyz[axis]])
                    coefficient = 2 * eps[idx] * eps[neighbor] / (eps[idx] + eps[neighbor]) / (
                        edge * widths[axis][xyz[axis]])
                    poisson[idx, idx] += coefficient
                    poisson[idx, neighbor] -= coefficient
    previous_n, previous_p = n0.copy(), p0.copy()
    for state in history:
        assert state["valid"] and not state["phi_frozen"] and state["charge_ledger_available"]
        rhs = QE * (state["p"] - state["n"] + doping)
        rhs[contacts] = 0
        expected_phi = np.linalg.solve(poisson, rhs)
        np.testing.assert_allclose(state["phi"], expected_phi, rtol=2e-8, atol=2e-12)
        if state["dt_s"]:
            for idx in np.flatnonzero(free):
                residual_n = (state["n"][idx] - previous_n[idx]) / state["dt_s"]
                residual_p = (state["p"][idx] - previous_p[idx]) / state["dt_s"]
                for axis in range(3):
                    for sign in (-1, 1):
                        position = coords[idx, axis] + sign
                        if 0 <= position < shape[axis]:
                            neighbor = idx + sign * strides[axis]
                            edge = abs(positions[axis][position] - positions[axis][coords[idx, axis]])
                            geometric_rate = 1 / (edge * widths[axis][coords[idx, axis]])
                            delta = (state["phi"][neighbor] - state["phi"][idx]) / VT
                            residual_n += .1 * VT * geometric_rate * (
                                state["n"][idx] * bernoulli(-delta) - state["n"][neighbor] * bernoulli(delta))
                            residual_p += .05 * VT * geometric_rate * (
                                state["p"][idx] * bernoulli(delta) - state["p"][neighbor] * bernoulli(-delta))
                # Independent dimensionless defect uses the BE storage rate,
                # not the native Jacobian or its row-equilibration metadata.
                assert abs(residual_n) * state["dt_s"] / scale < 1e-8
                assert abs(residual_p) * state["dt_s"] / scale < 1e-8
        else:
            np.testing.assert_array_equal(state["n"], n0)
            np.testing.assert_array_equal(state["p"], p0)
        previous_n, previous_p = state["n"], state["p"]
    verdict = TransientConservationTest(integration="backward_euler", charge_atol_C=0.,
                                       tolerance=1e-5).run(lambda: history)
    assert verdict.passed, verdict.message


@pytest.mark.parametrize("log_space", [False, True])
@pytest.mark.parametrize("source", ["optical", "srh"])
def test_neutral_pair_sources_match_analytic_coupled_be(source, log_space):
    size, scale, dt = 5, 1e20, 1e-12
    sim = PyDeviceSimulator(size, 1, 1, 1e-7, 1e-7, 1e-7)
    sim.set_permittivity(np.full(size, EPS))
    sim.set_mobility(np.full(size, .1), np.full(size, .05))
    sim.set_doping(np.zeros(size))
    sim.set_effective_dos(np.full(size, scale), np.full(size, scale))
    sim.set_bandgap(np.zeros(size))
    sim.set_thermal_voltage(VT)
    tau = 5 * dt if source == "srh" else 1e100
    sim.set_recombination(np.full(size, tau), np.full(size, tau))
    if source == "optical":
        sim.set_optical_generation(np.full(size, .2 * scale / dt))
    sim.set_newton_use_log_space(log_space)
    sim.set_dirichlet_potential({0: 0., size - 1: 0.})
    sim.set_initial_guess(.02 * np.sin(np.pi * np.arange(size) / (size - 1)),
                          np.full(size, 2 * scale), np.full(size, 2 * scale))
    sim.set_gummel_max_iter(100)
    sim.set_tolerance(1e-11)
    sim.set_transient_dt(dt)
    sim.set_transient_t_final(2.5 * dt)
    history = sim.solve_transient()
    assert len(history) == 4
    density = 2 * scale
    for state in history:
        assert state["valid"] and not state["phi_frozen"]
        if source == "optical":
            density += .2 * scale / dt * state["dt_s"]
        else:
            density = (density + state["dt_s"] * scale / (2 * tau)) / (1 + state["dt_s"] / (2 * tau))
        np.testing.assert_allclose(state["n"], density, rtol=2e-9)
        np.testing.assert_allclose(state["p"], density, rtol=2e-9)
        np.testing.assert_allclose(state["phi"], 0., atol=1e-12)
