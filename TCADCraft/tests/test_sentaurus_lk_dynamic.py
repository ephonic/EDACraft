"""Commercial BE transients and independent SI/centimeter energy invariance."""
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.validation import native_lk_to_sentaurus, sentaurus_lk_to_native


@pytest.mark.parametrize("alpha,beta,rho", [(-1e8, 1e12, .1), (2e8, 3e12, .2), (0., 1., 1.)])
@pytest.mark.parametrize("polarization,rate", [(-.01, 1e7), (.003, -2e6), (0., 0.)])
def test_conversion_preserves_equation_energy_and_dissipation(alpha, beta, rho, polarization, rate):
    p = native_lk_to_sentaurus(alpha, beta, rho)
    pcm, ratecm = polarization / 1e4, rate / 1e4
    field_cm = p["rho"]*ratecm + 2*p["alpha"]*pcm + 4*p["beta"]*pcm**3
    field_si = rho*rate + alpha*polarization + beta*polarization**3
    assert field_cm * 100 == pytest.approx(field_si, rel=1e-14, abs=1e-30)
    energy_cm = p["alpha"]*pcm**2 + p["beta"]*pcm**4
    energy_si = alpha*polarization**2/2 + beta*polarization**4/4
    assert energy_cm*1e6 == pytest.approx(energy_si, rel=1e-14, abs=1e-30)
    assert p["rho"]*ratecm**2*1e6 == pytest.approx(rho*rate**2)
    assert sentaurus_lk_to_native(p) == pytest.approx(dict(alpha=alpha, beta=beta, fe_gamma=rho))


def test_viscosity_and_sextic_coefficient_have_different_meanings():
    p = native_lk_to_sentaurus(-1e8, 1e12, .1)
    assert p == dict(alpha=-5e9, beta=2.5e21, gamma=0., g=0., rho=10.)
    p["gamma"] = .1
    with pytest.raises(ValueError, match="gamma=0"):
        sentaurus_lk_to_native(p)
    p["gamma"], p["g"] = 0., 1e-3
    with pytest.raises(ValueError, match="g=0"):
        sentaurus_lk_to_native(p)


@pytest.mark.parametrize("key", ["alpha", "beta", "fe_gamma"])
@pytest.mark.parametrize("value", [True, np.bool_(True), "1", [], np.array(1.), np.nan, np.inf, 10**1000])
def test_export_rejects_invalid_scalar(key, value):
    params = dict(alpha=-1e8, beta=1e12, fe_gamma=.1)
    params[key] = value
    with pytest.raises(ValueError):
        native_lk_to_sentaurus(**params)


@pytest.mark.parametrize("params", [dict(alpha=1, beta=0, fe_gamma=1),
    dict(alpha=1, beta=1, fe_gamma=0), dict(alpha=1, beta=-1, fe_gamma=1),
    dict(alpha=1, beta=1, fe_gamma=-1), dict(alpha=1e308, beta=1, fe_gamma=1),
    dict(alpha=1, beta=1e308, fe_gamma=1), dict(alpha=1, beta=1, fe_gamma=1e308)])
def test_export_rejects_non_dynamic_or_unrepresentable_parameters(params):
    with pytest.raises(ValueError):
        native_lk_to_sentaurus(**params)


@pytest.mark.parametrize("key", ["alpha", "beta", "gamma", "g", "rho"])
def test_import_requires_every_coefficient_explicitly(key):
    p = native_lk_to_sentaurus(-1e8, 1e12, .1)
    del p[key]
    with pytest.raises(ValueError, match="exactly"):
        sentaurus_lk_to_native(p)


@pytest.mark.parametrize("key", ["alpha", "beta", "rho"])
def test_import_rejects_underflow(key):
    p = native_lk_to_sentaurus(-1e8, 1e12, .1)
    p[key] = 5e-324
    with pytest.raises(ValueError, match="underflow"):
        sentaurus_lk_to_native(p)


@pytest.mark.parametrize("change", [dict(extra=1), dict(beta=-1), dict(rho=0),
    dict(alpha=np.nan), dict(g=True), dict(gamma="0")])
def test_import_rejects_ambiguous_or_invalid_parameters(change):
    p = native_lk_to_sentaurus(-1e8, 1e12, .1)
    p.update(change)
    with pytest.raises(ValueError):
        sentaurus_lk_to_native(p)


FIXTURE = json.loads((Path(__file__).parent / "data/sentaurus_lk_dynamic.json").read_text())


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: f'{c["name"]}-{c["max_step_normalized"]}')
def test_native_matches_independent_commercial_polarization_charge_and_current(case):
    times, voltage = np.array(case["times_s"]), np.array(case["voltage_V"])
    sim = PyDeviceSimulator(9, 1, 1, FIXTURE["length_m"]/8, 1e-7, 1e-6)
    sim.set_permittivity(np.full(9, FIXTURE["epsilon_F_m"]))
    sim.set_mobility(np.zeros(9), np.zeros(9))
    sim.set_doping(np.zeros(9))
    sim.set_effective_dos(np.full(9, 1e16), np.full(9, 1e16))
    sim.set_bandgap(np.full(9, 6.))
    sim.set_recombination(np.full(9, 1e100), np.full(9, 1e100))
    sim.set_dirichlet_potential({0: 0., 8: 0.})
    sim.set_initial_guess(np.zeros(9), np.zeros(9), np.zeros(9))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_model(0)
    sim.set_ferroelectric_polar_axis(0)
    sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), case["alpha"], case["beta"])
    sim.set_ferroelectric_gamma(case["rho"])
    sim.set_transient_lk_coupled(True)
    sim.set_gummel_max_iter(80)
    sim.set_tolerance(1e-12)
    sim.set_transient_dt(float(times[-1]))
    sim.set_transient_t_final(float(times[-1]))
    sim.set_transient_voltage_waveforms(times, {8: voltage})
    history = sim.solve_transient()
    assert all(s["valid"] and s["lk_coupled"] for s in history)
    np.testing.assert_array_equal([s["time_s"] for s in history], times)
    p = np.array([s["P"].reshape(-1, 3)[:, 0] for s in history])
    expected_p = np.array(case["polarization_C_m2"])
    scale_p = max(abs(expected_p))
    np.testing.assert_allclose(p, np.broadcast_to(expected_p[:, None], p.shape),
                               rtol=0., atol=1e-7*scale_p)
    q = np.array([s["electrode_charges_C"][1] for s in history])
    np.testing.assert_allclose(q, case["top_charge_C"], rtol=0., atol=1e-7*FIXTURE["area_m2"]*scale_p)
    current = np.r_[0., [s["electrode_total_currents_A"][1] for s in history[1:]]]
    np.testing.assert_allclose(current, case["top_current_A"], rtol=0.,
                               atol=1e-7*max(abs(np.array(case["top_current_A"]))))
    # Absolute signs, charge increments and integral are checked against raw
    # commercial port quantities, independently of native polarization output.
    integral = np.dot(np.diff(times), current[1:])
    assert integral == pytest.approx(case["top_charge_C"][-1]-case["top_charge_C"][0],
                                     rel=1e-7, abs=1e-25)
