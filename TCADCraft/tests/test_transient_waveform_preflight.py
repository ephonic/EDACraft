"""Voltage arithmetic and validation must precede any physical dwell."""
import numpy as np
import pytest

from test_transient_displacement import film


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("model", [0, 1, 2, 3])
def test_future_voltage_overflow_does_not_consume_prepared_fe_state(axis, model):
    sim, *_ = film(axis, model, False, False)
    prepared = sim.solve_transient()[-1]
    assert prepared["valid"] and np.any(prepared["P"] != 0.)
    sim.set_dirichlet_potential({0: 0., 8: 1e308})
    sim.set_transient_dt(.25e-9)
    sim.set_transient_t_final(2e-9)
    sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9],
                                       {8: [-1e308, -1e308, 1e308]})
    with pytest.raises(ValueError, match="finite output range"):
        sim.solve_transient()
    # The replacement cancels the configured DC and has no physical dwell.
    sim.set_transient_voltage_waveforms([0., 2e-9], {8: [-1e308, -1e308]})
    sim.set_transient_t_final(0.)
    restored, = sim.solve_transient()
    np.testing.assert_array_equal(restored["P"], prepared["P"])
    np.testing.assert_array_equal(restored["electrode_voltages_V"], [0., 0.])


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("base", [1e308, -1e308])
def test_constant_dc_offset_cancellation_is_exact_at_interior_samples(axis, base):
    sim, *_ = film(axis, 2, False, False)
    sim.set_ferroelectric_enabled(False)
    sim.set_dirichlet_potential({0: 0., 8: base})
    sim.set_transient_dt(.1e-9)
    sim.set_transient_t_final(.3e-9)
    sim.set_transient_voltage_waveforms([0., .3e-9], {8: [-base, -base]})
    history = sim.solve_transient()
    assert len(history) >= 4
    for state in history:
        assert state["valid"]
        np.testing.assert_array_equal(state["electrode_voltages_V"], [0., 0.])
        np.testing.assert_array_equal(state["phi"], 0.)
        np.testing.assert_array_equal(state["electrode_charges_C"], 0.)
        if state["dt_s"]:
            np.testing.assert_array_equal(state["electrode_total_currents_A"], 0.)


@pytest.mark.parametrize("base", [1e308, -1e308])
@pytest.mark.parametrize("final", [0., 1e-9])
def test_overflow_beyond_active_interval_does_not_reject_valid_drive(base, final):
    sim, *_ = film(0, 2, False, False)
    sim.set_ferroelectric_enabled(False)
    sim.set_dirichlet_potential({0: 0., 8: base})
    sim.set_transient_dt(.25e-9)
    sim.set_transient_t_final(final)
    sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9],
                                       {8: [-base, -base, base]})
    for state in sim.solve_transient():
        assert state["valid"]
        np.testing.assert_array_equal(state["electrode_voltages_V"], [0., 0.])


def test_final_time_inside_invalid_segment_is_checked_before_fe_dwell():
    sim, *_ = film(0, 0, False, False)
    prepared = sim.solve_transient()[-1]
    assert prepared["valid"] and np.any(prepared["P"] != 0.)
    sim.set_dirichlet_potential({0: 0., 8: 1e308})
    sim.set_transient_dt(.25e-9)
    sim.set_transient_t_final(1.95e-9)
    sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9],
                                       {8: [-1e308, -1e308, 1e308]})
    with pytest.raises(ValueError, match="finite output range"):
        sim.solve_transient()
    sim.set_transient_t_final(0.)
    restored, = sim.solve_transient()
    np.testing.assert_array_equal(restored["P"], prepared["P"])


@pytest.mark.parametrize("mode", ["split", "coupled", "adaptive"])
def test_rejected_drive_and_subsequent_valid_retry_match_fresh_history(mode):
    def prepared_device():
        sim, *_ = film(0, 0, False, False)
        if mode != "split":
            sim.set_transient_lk_coupled(True)
        if mode == "adaptive":
            sim.set_transient_lk_substepping(True)
            sim.set_transient_lk_error_control(True)
        history = sim.solve_transient()
        assert all(s["valid"] for s in history)
        sim.set_dirichlet_potential({0: 0., 8: 1e308})
        sim.set_transient_dt(.25e-9)
        sim.set_transient_t_final(2e-9)
        return sim

    failed, fresh = prepared_device(), prepared_device()
    failed.set_transient_voltage_waveforms([0., 1e-9, 2e-9],
                                          {8: [-1e308, -1e308, 1e308]})
    with pytest.raises(ValueError, match="finite output range"):
        failed.solve_transient()
    for sim in (failed, fresh):
        sim.set_transient_voltage_waveforms([0., 2e-9], {8: [-1e308, -1e308]})
    retry, reference = failed.solve_transient(), fresh.solve_transient()
    assert len(retry) == len(reference)
    for actual, expected in zip(retry, reference):
        assert actual["valid"] and expected["valid"]
        for key in ("time_s", "dt_s", "phi", "n", "p", "P",
                    "electrode_voltages_V", "electrode_total_currents_A"):
            if key in expected:
                np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize("base", [1e308, -1e308])
def test_clipped_final_voltage_can_be_valid_when_future_endpoint_overflows(base):
    sim, *_ = film(0, 2, False, False)
    sim.set_ferroelectric_enabled(False)
    sim.set_dirichlet_potential(dict.fromkeys(range(9), base))
    sim.set_initial_guess(np.full(9, base), np.zeros(9), np.zeros(9))
    sim.set_transient_dt(.1e-9)
    sim.set_transient_t_final(.4e-9)
    sim.set_transient_voltage_waveforms([0., 1e-9],
                                       dict.fromkeys(range(9), [0., base]))
    for state in sim.solve_transient():
        assert state["valid"]
        np.testing.assert_allclose(state["phi"], base * (1 + state["time_s"] / 1e-9),
                                   rtol=2e-16, atol=0.)
        np.testing.assert_array_equal(state["Ex"], 0.)


@pytest.mark.parametrize("coupled", [False, True])
def test_late_overflow_preflight_preserves_nonzero_lk_before_zero_field_relaxation(coupled):
    sim, *_ = film(0, 0, False, False)
    sim.set_transient_lk_coupled(coupled)
    prepared = sim.solve_transient()[-1]
    assert prepared["valid"] and np.any(prepared["P"] != 0.)
    # All nodes are prescribed to a common potential: no large field or
    # Poisson cancellation can obscure the voltage validation failure.
    sim.set_dirichlet_potential(dict.fromkeys(range(9), 1e308))
    sim.set_initial_guess(np.full(9, 1e308), np.zeros(9), np.zeros(9))
    sim.set_transient_dt(.25e-9)
    sim.set_transient_t_final(2e-9)
    sim.set_transient_voltage_waveforms([0., 1e-9, 2e-9],
                                       dict.fromkeys(range(9), [0., 0., 1e308]))
    with pytest.raises(ValueError, match="finite output range"):
        sim.solve_transient()
    sim.clear_transient_voltage_waveforms()
    sim.set_transient_t_final(0.)
    state, = sim.solve_transient()
    np.testing.assert_array_equal(state["P"], prepared["P"])
