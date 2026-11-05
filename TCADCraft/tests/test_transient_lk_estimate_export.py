"""An accepted local error estimate must survive its float64 export."""
from copy import deepcopy
from decimal import Decimal, localcontext

import numpy as np
import pytest

from tcad.postprocess import audit_transient_lk_error_control
from test_fe_transient_feedback import dielectric
from test_transient_lk_error_control import controlled


@pytest.mark.parametrize("sign", [-1., 1.])
@pytest.mark.parametrize("case", ["zero_delta", "quantized_delta"])
def test_unrepresentable_error_estimate_is_not_committed(case, sign):
    voltage, alpha, atol = ((1e-280, 1e30, 1e-306) if case == "zero_delta"
                            else (1e-320, 1e8, 1e-320))
    sim, _ = dielectric(voltage=sign*voltage, alpha=alpha, dt=1e-9, final=1e-9)
    controlled(sim, atol=atol)
    history = sim.solve_transient()
    assert len(history) == 2
    failure = history[-1]
    assert not failure["valid"] and not failure["converged"]
    assert failure["lk_error_status"] == "unrepresentable_estimate"
    assert not failure["lk_error_estimate_available"]
    assert failure["dt_s"] == failure["time_s"] == 0.
    assert failure["attempted_time_s"] == 1e-9
    assert failure["lk_rejected_attempts"] == 1
    for key in ("P", "phi", "n", "p", "electrode_voltages_V"):
        np.testing.assert_array_equal(failure[key], history[0][key])
    # A normal drive retries from the original physical state, not the trial P.
    sim.set_dirichlet_potential({8: sign*.003})
    sim.set_ferroelectric_params(np.ones(9, dtype=np.int8), 1e8, 1e12)
    sim.set_transient_lk_error_control(True)
    retry = sim.solve_transient()
    fresh, _ = dielectric(voltage=sign*.003, alpha=1e8, dt=1e-9, final=1e-9)
    reference = controlled(fresh).solve_transient()
    assert len(retry) == len(reference)
    for actual, expected in zip(retry, reference):
        assert actual["valid"]
        for key in ("time_s", "dt_s", "phi", "n", "p", "P"):
            np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("sign", [-1., 1.])
@pytest.mark.parametrize("voltage", [1e-312, 1e-310, 1e-305])
def test_resolvable_subnormal_polarization_matches_linear_be_reference(sign, voltage):
    sim, x = dielectric(voltage=sign*voltage, alpha=1e8, dt=1e-9, final=1e-9)
    history = controlled(sim, atol=1e-301 if voltage == 1e-305 else 1e-310).solve_transient()
    assert len(history) == 3 and all(s["valid"] for s in history)
    assert audit_transient_lk_error_control(history)["valid"]
    # beta*P^3 is below 1e-900 here. Independently evaluate the linear BE
    # formula in Decimal rather than reproducing the cubic root algorithm.
    with localcontext() as context:
        context.prec = 100
        alpha, gamma = Decimal.from_float(1e8), Decimal.from_float(.1)
        field = -Decimal.from_float(sign*voltage)/Decimal.from_float(float(x[-1]))
        previous = Decimal(0)
        for state in history[1:]:
            rate = gamma/Decimal.from_float(state["dt_s"])
            previous = (rate*previous+field)/(alpha+rate)
            np.testing.assert_allclose(state["P"].reshape(-1, 3)[:, 0], float(previous),
                                       rtol=1e-10, atol=2*np.nextafter(0., 1.))
        macro = Decimal.from_float(history[-1]["lk_error_interval_s"])
        coarse = field/(alpha+gamma/macro)
        delta = previous-coarse
        np.testing.assert_allclose(history[-1]["lk_error_delta_P_C_per_m2"].reshape(-1, 3)[:, 0],
                                   float(delta), rtol=1e-9, atol=2*np.nextafter(0., 1.))


def test_subnormal_audit_still_rejects_a_resolvable_forged_increment():
    sim, _ = dielectric(voltage=-1e-312, alpha=1e8, dt=1e-9, final=1e-9)
    history = controlled(sim, atol=1e-310).solve_transient()
    assert audit_transient_lk_error_control(history)["valid"]
    forged = deepcopy(history)
    forged[-1]["lk_error_delta_P_C_per_m2"][0] += 100*np.nextafter(0., 1.)
    with pytest.raises(ValueError, match="disagrees"):
        audit_transient_lk_error_control(forged)


@pytest.mark.parametrize("sign", [-1., 1.])
def test_export_rounding_cannot_cross_the_acceptance_threshold(sign):
    voltage, atol = sign*9.926e-313, 6.824125e-315
    sim, _ = dielectric(voltage=voltage, alpha=1e8, dt=1e-9, final=1e-9)
    # Native norm is below one but exported norm is above one. With no retry
    # budget this must return the unchanged state, not accepted half steps.
    controlled(sim, atol=atol, max_reject=0)
    history = sim.solve_transient()
    assert len(history) == 2 and not history[-1]["valid"]
    assert history[-1]["lk_error_status"] == "accuracy_limit"
    assert history[-1]["lk_error_estimate_available"]
    assert history[-1]["lk_error_ratio"] < 1.
    np.testing.assert_array_equal(history[-1]["P"], history[0]["P"])
    assert history[-1]["time_s"] == history[-1]["dt_s"] == 0.
    sim.set_transient_lk_error_control(True, atol=atol)
    retry = sim.solve_transient()
    assert all(s["valid"] for s in retry)
    assert audit_transient_lk_error_control(retry)["valid"]
    assert sum(s["lk_rejected_attempts"] for s in retry[2::2]) >= 1


def test_unrepresentable_later_group_preserves_accepted_prefix_and_retry():
    def configured(final):
        sim, _ = dielectric(voltage=-.003, alpha=1e18, dt=1e-9, final=final)
        controlled(sim)
        sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9, 20e-9],
                                           {8: [0., 0., .003, .003]})
        return sim

    sim = configured(20e-9)
    history = sim.solve_transient()
    failure, previous = history[-2:][::-1]
    assert not failure["valid"] and failure["lk_error_status"] == "unrepresentable_estimate"
    assert previous["time_s"] > 0. and np.any(previous["P"] != 0.)
    assert audit_transient_lk_error_control(history[:-1])["valid"]
    for key in ("time_s", "phi", "n", "p", "P", "electrode_voltages_V"):
        np.testing.assert_array_equal(failure[key], previous[key])
    reference = configured(previous["time_s"])
    reference_history = reference.solve_transient()
    assert len(reference_history) == len(history)-1
    for actual, expected in zip(history[:-1], reference_history):
        np.testing.assert_array_equal(actual["P"], expected["P"])
    for device in (sim, reference):
        device.clear_transient_voltage_waveforms()
        device.set_dirichlet_potential({8: -.003})
        device.set_transient_t_final(1e-9)
    retry, fresh = sim.solve_transient(), reference.solve_transient()
    assert len(retry) == len(fresh)
    for actual, expected in zip(retry, fresh):
        assert actual["valid"]
        for key in ("time_s", "dt_s", "phi", "n", "p", "P"):
            np.testing.assert_array_equal(actual[key], expected[key])
