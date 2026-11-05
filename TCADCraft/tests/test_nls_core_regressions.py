"""Independent compact NLS kinetics and configuration references."""
import math

import numpy as np
import pytest

from test_physical_step_commit import N, PS, high_level, native


def pulse(sim, voltage=4.):
    if sim.results is None:
        sim.set_contact("right", voltage)
    else:
        sim.update_contact("right", voltage)
    result = sim.run(max_iter=300, tol=1e-8)
    assert result["converged"] and result["physical_step_accepted"]
    return result["P"][:, 0]


@pytest.mark.parametrize("tau,E0,dt", [
    (0., 0., .1), (-1., 0., .1), (math.nan, 0., .1),
    (math.inf, 0., .1), (1., -1., .1), (1., math.nan, .1),
    (1., math.inf, .1), (1., 0., 0.), (1., 0., -1.),
    (1., 0., math.nan), (1., 0., math.inf),
])
def test_native_invalid_nls_parameters_preserve_good_configuration(tau, E0, dt):
    sim = native()
    sim.set_ferroelectric_nls(2., 0., .2)
    with pytest.raises(ValueError):
        sim.set_ferroelectric_nls(tau, E0, dt)
    sim.set_dirichlet_potential({0: 0., N-1: 4.})
    result = sim.solve()
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:, 0], -PS*(-math.expm1(-.1)), atol=1e-12)


@pytest.mark.parametrize("name", ["Ps", "Ec", "Escale"])
@pytest.mark.parametrize("bad", [-1., math.nan, math.inf])
def test_native_invalid_amplitude_parameters_are_rejected(name, bad):
    sim = native()
    params = dict(Ps=PS, Ec=1e8, Escale=1e8)
    params[name] = bad
    with pytest.raises(ValueError):
        sim.set_ferroelectric_preisach(params["Ps"], params["Ec"], params["Escale"])
    sim.set_dirichlet_potential({0: 0., N-1: 4.})
    result = sim.solve()
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:, 0], -PS*(-math.expm1(-.1)), atol=1e-12)


@pytest.mark.parametrize("setter", ["set_ferroelectric", "set_ferroelectric_model"])
@pytest.mark.parametrize("params", [dict(nls_tau0=0.), dict(nls_E0=-1.),
    dict(nls_dt=math.inf), dict(Ps=-1.), dict(Ec=math.nan), dict(Escale=-1.)])
def test_high_level_invalid_configuration_does_not_change_model_or_kinetics(setter, params):
    sim = high_level()
    before = (sim._fe_model_int, sim._fe_base_ps, sim._fe_nls_tau0,
              sim._fe_nls_E0, sim._fe_nls_dt)
    mask = sim._fe_node_mask.copy()
    with pytest.raises(ValueError):
        getattr(sim, setter)(model="nls", **params)
    assert before == (sim._fe_model_int, sim._fe_base_ps, sim._fe_nls_tau0,
                      sim._fe_nls_E0, sim._fe_nls_dt)
    np.testing.assert_array_equal(sim._fe_node_mask, mask)
    np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.1)), atol=1e-12)


def test_model_setter_preserves_new_kinetics_when_dwell_is_changed():
    sim = high_level()
    sim.set_ferroelectric_model("nls", Ps=PS, Ec=1e8, Escale=1e8,
                               nls_tau0=2., nls_E0=0., nls_dt=.3)
    sim.set_ferroelectric_nls_dwell_time(.2)
    assert (sim._fe_nls_tau0, sim._fe_nls_E0, sim._fe_nls_dt) == (2., 0., .2)
    np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.1)), atol=1e-12)


@pytest.mark.parametrize("field", ["fe_ps", "fe_ec"])
@pytest.mark.parametrize("bad", [-1., math.nan, math.inf])
def test_invalid_material_amplitude_is_rejected_before_model_changes(field, bad):
    sim = high_level()
    sim.mesh.fields[field] = np.full(N, bad)
    with pytest.raises(ValueError):
        sim.set_ferroelectric(model="preisach", fe_mask_override=np.ones(N, dtype=np.int8))
    assert sim._fe_model_int == 2 and sim._fe_base_ps == PS
    np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.1)), atol=1e-12)


@pytest.mark.parametrize("fraction", [0., .25, 1., 1.5])
def test_accepted_nls_state_is_bounded_by_configured_active_ps(fraction):
    sim = high_level()
    sim.set_ferroelectric_nls_dwell_time(20.)
    pulse(sim)
    sim.set_ferroelectric_active_fraction(fraction)
    for voltage in (4., -4., 4.):
        state = pulse(sim, voltage)
        assert np.all(np.abs(state) <= PS*fraction+1e-14)


@pytest.mark.parametrize("dt", [0., -1., math.nan, math.inf, True, [.1]])
def test_invalid_dwell_does_not_mutate_cache_or_native_parameters(dt):
    sim = high_level()
    with pytest.raises(ValueError):
        sim.set_ferroelectric_nls_dwell_time(dt)
    assert sim._fe_nls_dt == .1
    np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.1)), atol=1e-12)


def slab(extra=0.):
    sim = high_level()
    sim.mesh.fields["epsilon"] = np.full(N, 15*8.854187817e-12)
    sim._sim.set_permittivity(sim.mesh.fields["epsilon"])
    sim.set_ferroelectric(model="nls", Ps=PS, Ec=1e8, Escale=1e8,
        nls_tau0=1., nls_E0=0., nls_dt=.1, polar_axis="x",
        fe_mask_override=np.ones(N, dtype=np.int8),
        extra_depolarization_eps_r=extra)
    return sim


def test_ideal_electrode_slab_has_no_automatic_extra_depolarization():
    sim = slab()
    for number in (1, 2, 3):
        np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.1*number)), atol=1e-12)


def test_explicit_extra_screening_changes_the_second_pulse_with_declared_sign():
    sim = slab(15.)
    first = pulse(sim)
    np.testing.assert_allclose(first, -PS*(-math.expm1(-.1)), atol=1e-12)
    # Uniform P creates no volume bound charge in this full ideal-electrode
    # slab. The explicitly added -P/(eps_r*eps0) reverses the effective field.
    assert -4./40e-9-first[0]/(15*8.854187817e-12) > 0.
    second = first[0]*math.exp(-.1)+PS*(-math.expm1(-.1))
    np.testing.assert_allclose(pulse(sim), second, atol=1e-12)


def test_default_reconfiguration_disables_stale_extra_screening():
    sim = slab(15.)
    sim.set_ferroelectric(model="nls", Ps=PS, Ec=1e8, Escale=1e8,
        nls_tau0=1., nls_E0=0., nls_dt=.1, polar_axis="x",
        fe_mask_override=np.ones(N, dtype=np.int8))
    pulse(sim)
    np.testing.assert_allclose(pulse(sim), -PS*(-math.expm1(-.2)), atol=1e-12)


@pytest.mark.parametrize("eps", [-1., math.nan, math.inf])
def test_invalid_extra_screening_preserves_explicit_configuration(eps):
    sim = slab(15.)
    with pytest.raises(ValueError):
        sim.set_ferroelectric_depol(eps)
    with pytest.raises(ValueError):
        sim._sim.set_ferroelectric_depol(eps)
    first = pulse(sim)
    expected = first[0]*math.exp(-.1)+PS*(-math.expm1(-.1))
    np.testing.assert_allclose(pulse(sim), expected, atol=1e-12)


@pytest.mark.parametrize("dt", [1e-40, 1e-20, .1, 1., 1e6])
def test_native_merz_law_handles_tiny_and_saturated_pulses(dt):
    sim = native()
    sim.set_ferroelectric_nls(1., 0., dt)
    sim.set_dirichlet_potential({0: 0., N-1: 4.})
    result = sim.solve()
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:, 0], -PS*(-math.expm1(-dt)),
                               rtol=1e-12, atol=1e-65)


def test_native_nls_does_not_impose_undeclared_coercive_field_cutoff():
    sim = native()
    sim.set_dirichlet_potential({0: 0., N-1: 1e-3})
    result = sim.solve()
    assert result["converged"]
    np.testing.assert_allclose(result["P"][:, 0], -PS*(-math.expm1(-.1)), atol=1e-12)


@pytest.mark.parametrize("steps", [1, 4, 16])
def test_constant_field_merz_time_subdivision_matches_closed_form(steps):
    sim = high_level()
    sim.set_ferroelectric_model("nls", Ps=PS, Ec=1e8, Escale=1e8,
                               nls_tau0=.5, nls_E0=1e8, nls_dt=1./steps)
    for _ in range(steps):
        state = pulse(sim)
    expected = -PS*(-math.expm1(-2./math.e))
    np.testing.assert_allclose(state, expected, atol=1e-12, rtol=1e-12)
