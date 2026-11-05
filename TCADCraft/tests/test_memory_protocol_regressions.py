"""Independent limits for the comments refresh/RRAM defects."""
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.linalg import expm

from tcad.physics.electron_counting import BirthDeathChain, GillespieSampler
from tcad.physics.rram_filament import FilamentConfig, simulate_forming, simulate_cycling
from tcad.search.fefet_schedule import ScheduleConfig, evaluate_schedule
from tcad.search.rram_protocol import (
    ProtocolConfig, ProtocolPoint, _simulate_protocol, _simulate_adaptive,
    compare_pulse_strategies, pareto_front, find_reliable_optimal,
)


def no_loss(**kwargs):
    return ScheduleConfig(lifetime_cycles=10, wakeup_gain=0, fatigue_loss=0,
                          imprint_rate=0, imprint_field_max=0, **kwargs)


@pytest.mark.parametrize("cadence", [7, 10, 20, 0.1])
def test_refresh_no_loss_covers_exact_lifetime(cadence):
    result = evaluate_schedule(cadence, no_loss())
    assert result.usable_window_integral == pytest.approx(10, abs=1e-12)
    assert result.mean_window == pytest.approx(1, abs=1e-12)
    assert result.covered_cycles == 10


@pytest.mark.parametrize("cadence", [10, 20])
def test_refresh_has_no_terminal_damage(cadence):
    result = evaluate_schedule(cadence, ScheduleConfig(lifetime_cycles=10))
    assert result.final_fatigue == 0
    assert result.refresh_count == 0


def test_refresh_partial_block_analytic_integral():
    cfg = ScheduleConfig(lifetime_cycles=10, wakeup_gain=0, fatigue_loss=0,
                         imprint_rate=0.2, imprint_field_max=0.5)
    result = evaluate_schedule(7, cfg)
    expected = sum(0.5*h + 0.5*(-math.expm1(-0.2*h))/0.2 for h in (7, 3))
    assert result.usable_window_integral == pytest.approx(expected, rel=2e-14)
    assert result.refresh_count == 1


def test_refresh_retained_imprint_survives_block_boundaries():
    cfg = ScheduleConfig(lifetime_cycles=10, wakeup_gain=0, fatigue_loss=0,
                         imprint_rate=0.2, imprint_field_max=0.5,
                         refresh_imprint_retention=1)
    split = evaluate_schedule(3, cfg)
    unsplit = evaluate_schedule(10, cfg)
    assert split.usable_window_integral == pytest.approx(unsplit.usable_window_integral, rel=1e-14)
    assert split.final_imprint == pytest.approx(0.5*(1-math.exp(-2)), rel=1e-14)


@pytest.mark.parametrize("rate,maximum,amplitude,initial,duration", [
    (0.2, 2, 1, 0, 10), (0, 2, 1, 0.2, 10),
    (0.1, 0.5, 1, 0.2, 3), (1e-10, 0.5, 1, 0, 1),
    (0.2, 2, 0.1, 0.2, 10),
])
def test_clipped_dwell_matches_independent_quadrature(rate, maximum, amplitude, initial, duration):
    from tcad.search.fefet_schedule import _dwell_integral
    expected = quad(lambda t: max(amplitude - maximum + (maximum-initial)*math.exp(-rate*t), 0),
                    0, duration, epsabs=1e-12, points=[math.log(2)/rate]
                    if rate and initial == 0 and maximum == 2 and amplitude == 1 else None)[0]
    actual, final = _dwell_integral(amplitude, initial, maximum, rate, duration)
    assert actual == pytest.approx(expected, rel=1e-11, abs=1e-12)
    assert final == pytest.approx(maximum+(initial-maximum)*math.exp(-rate*duration), abs=1e-14)


@pytest.mark.parametrize("cadence", [0, -1, float("nan"), float("inf")])
def test_invalid_refresh_cadence_rejected(cadence):
    with pytest.raises(ValueError):
        evaluate_schedule(cadence, no_loss())


def test_refresh_asymptotic_signature_declares_its_scope():
    from tcad.search.fefet_schedule import scaling_signature
    cfg = ScheduleConfig(lifetime_cycles=100, n_cadence=3,
                         cadence_lo_cycles=1, cadence_hi_cycles=100)
    signature = scaling_signature(cfg)
    stress = cfg.refresh_events_per_block*(cfg.refresh_field/cfg.write_field)**cfg.fatigue_field_exponent
    assert signature["n_fatigue_eff"] == pytest.approx(cfg.fatigue_cycles/stress)
    assert not signature["asymptotic_regime_satisfied"]  # Default wake-up violates the limit.
    disabled = scaling_signature(ScheduleConfig(lifetime_cycles=100, n_cadence=3,
                                                refresh_events_per_block=0))
    assert disabled["asymptotic_cadence"] is None


def test_fixed_split_cost_is_invariant():
    config = ProtocolConfig(n_cycles=4, rest_width=0)
    points = [_simulate_protocol(0.6e8, 1e-6, count, config) for count in (1, 2, 4)]
    assert [p.energy_proxy for p in points] == pytest.approx([0.36+0.3025]*3)
    assert [p.set_cost_proxy for p in points] == pytest.approx([0.36]*3)
    assert [p.mean_set_time_s for p in points] == pytest.approx([1e-6]*3)


def test_cost_participates_in_pareto_front():
    cheap = ProtocolPoint(1, 1, mean_log_ratio=2, sigma_log_ratio=0.1, energy_proxy=1)
    expensive = ProtocolPoint(1, 1, mean_log_ratio=2, sigma_log_ratio=0.1, energy_proxy=2)
    assert cheap.objectives.size == 3
    assert pareto_front([expensive, cheap]) == [cheap]
    assert pareto_front([]) == []


def test_fixed_read_and_driver_overheads_are_separate():
    config = ProtocolConfig(n_cycles=3, read_cost_proxy=0.1, driver_cost_proxy_per_pulse=0.2,
                            rest_width=0, read_width=2e-8)
    point = _simulate_protocol(0.6e8, 1e-6, 4, config)
    assert point.read_cost_proxy == pytest.approx(0.2)
    assert point.driver_cost_proxy == pytest.approx(1)
    assert point.energy_proxy == pytest.approx(0.36+0.3025+0.2+1)
    assert point.mean_elapsed_time_s == pytest.approx(2e-6+4e-8)


def test_comparison_gives_equal_set_time_budget():
    points = compare_pulse_strategies(ProtocolConfig(n_cycles=3))
    assert [p.set_width for p in points.values()] == pytest.approx([1e-6]*4)
    assert all(p.mean_set_time_s <= p.set_width for p in points.values())


def deterministic_trajectory(self, duration, n0, t_start=0):
    return (20 if self.chain._lam[0] > 0 else 0), duration


def test_adaptive_controller_uses_observation_not_latent_count(monkeypatch):
    import tcad.search.rram_protocol as mod
    monkeypatch.setattr(GillespieSampler, "run_trajectory", deterministic_trajectory)
    monkeypatch.setattr(mod, "_observe_log_resistance", lambda *args: 9.0)
    point = _simulate_adaptive(0.6e8, 1e-7, 6, ProtocolConfig(n_cycles=3))
    assert point.p_on == 1
    assert point.n_pulses == 6  # The observed OFF result overrides true ON.
    assert all(not s["verify_stopped"] for s in point.cycle_samples)


def test_false_positive_verify_is_recorded(monkeypatch):
    import tcad.search.rram_protocol as mod
    monkeypatch.setattr(GillespieSampler, "run_trajectory", lambda self,t,n: (0,t))
    monkeypatch.setattr(mod, "_observe_log_resistance", lambda *args: 0.0)
    point = _simulate_adaptive(0.6e8, 1e-7, 6, ProtocolConfig(n_cycles=4))
    assert point.n_pulses == 1
    assert point.p_success == 0
    assert point.failures["false_positive_verify"] == 4
    assert find_reliable_optimal([point]) is None


def test_noise_and_mean_pulse_count_are_reproducible():
    config = ProtocolConfig(n_cycles=30, read_noise_log10_std=0.3, read_cost_proxy=0.01)
    first = _simulate_adaptive(0.6e8, 0.5e-6, 6, config)
    second = _simulate_adaptive(0.6e8, 0.5e-6, 6, config)
    assert first.cycle_samples == second.cycle_samples
    assert first.n_pulses == np.mean([s["applied_pulses"] for s in first.cycle_samples])
    assert first.set_cost_proxy == pytest.approx((0.6**2)*0.5*first.n_pulses)


def test_gaussian_observation_stop_counts_match_geometric_limit(monkeypatch):
    monkeypatch.setattr(GillespieSampler, "run_trajectory", deterministic_trajectory)
    config = ProtocolConfig(n_cycles=2000, read_noise_log10_std=0.2,
                            verify_threshold_ohm=1e4, independent_trials=True)
    point = _simulate_adaptive(0.6e8, 1e-7, 6, config)
    # At true R=threshold each noisy read has 1/2 chance to stop; censor at six.
    expected = sum(0.5**k for k in range(6))
    assert point.n_pulses == pytest.approx(expected, abs=0.1)


def test_full_cycle_reliability_includes_reset_failure(monkeypatch):
    monkeypatch.setattr(GillespieSampler, "run_trajectory", lambda self,t,n: (20,t))
    point = _simulate_protocol(0.6e8, 1e-6, 1, ProtocolConfig(n_cycles=4))
    assert point.p_on == 1
    assert point.p_success == 0
    assert point.failures["reset_failed"] == 4
    assert find_reliable_optimal([point]) is None


def test_protocol_preserves_reset_residue(monkeypatch):
    def step(self, duration, n0, t_start=0):
        return (min(n0+3, 30) if self.chain._lam[0] > 0 else max(n0-1, 0)), duration
    monkeypatch.setattr(GillespieSampler, "run_trajectory", step)
    point = _simulate_protocol(0.6e8, 1e-6, 1, ProtocolConfig(n_cycles=4))
    assert [s["initial_count"] for s in point.cycle_samples] == [0, 2, 4, 6]
    assert point.sample_mode == "correlated_cycles"
    assert point.failure_probability_upper95 is None


def test_raw_inverted_windows_are_not_clipped(monkeypatch):
    monkeypatch.setattr(GillespieSampler, "run_trajectory",
                        lambda self,t,n: (min(n+1,30),t))
    point = _simulate_protocol(0.6e8, 1e-6, 1, ProtocolConfig(n_cycles=4))
    assert point.mean_log_ratio < 0
    assert point.failures["inverted_window"] == 4
    assert all(s["ratio"] < 1 for s in point.cycle_samples)


def test_zero_failures_has_nonzero_independent_upper_bound(monkeypatch):
    monkeypatch.setattr(GillespieSampler, "run_trajectory", deterministic_trajectory)
    point = _simulate_protocol(0.6e8, 1e-6, 1,
                               ProtocolConfig(n_cycles=40, independent_trials=True))
    assert point.p_success == 1
    assert point.failure_probability_upper95 == pytest.approx(1-0.05**(1/40), rel=1e-13)
    assert all(s["initial_count"] == 0 for s in point.cycle_samples)


@pytest.mark.parametrize("parameter,value", [
    ("read_noise_log10_std", -1), ("read_cost_proxy", float("nan")),
    ("read_width", -1), ("n_cycles", 0), ("verify_threshold_ohm", 0),
])
def test_invalid_protocol_parameters_rejected(parameter, value):
    with pytest.raises(ValueError):
        ProtocolConfig(**{parameter: value})


def test_forming_completes_hold_after_threshold_crossing():
    cfg = FilamentConfig(n_max=2, n_conducting=1)
    cfg.growth_rate = lambda field: 2.0
    cfg.rupture_rate = lambda n: 0.0
    result = simulate_forming(cfg, 1e8, t_max=1, n_steps=20)
    expected = np.array([math.exp(-2), 2*math.exp(-2), 1-3*math.exp(-2)])
    assert result["probabilities"] == pytest.approx(expected, rel=1e-12)
    assert result["time_s"] == result["requested_time_s"] == 1
    assert result["completed"]


def test_forming_high_rate_and_subdivision_agree():
    cfg = FilamentConfig(n_max=2, n_conducting=1)
    cfg.growth_rate = lambda field: 8e7
    cfg.rupture_rate = lambda n: 2e7
    whole = simulate_forming(cfg, 1e8, t_max=1e-3, n_steps=1)
    split = simulate_forming(cfg, 1e8, t_max=1e-3, n_steps=7)
    stationary = np.array([1,4,16])/21
    assert whole["probabilities"] == pytest.approx(stationary, rel=1e-12)
    assert split["probabilities"] == pytest.approx(stationary, rel=1e-12)
    assert split["time_s"] == whole["time_s"] == 1e-3


def test_scaled_chain_matches_independent_generator_exponential():
    chain = BirthDeathChain(n_max=2, capture_rate=lambda n: 0.3 if n==0 else 1e6,
                           emission_rate=lambda n: 0)
    chain.initialize()
    generator = np.array([[-0.3,0,0], [0.3,-1e6,0], [0,1e6,0]])
    expected = expm(generator*2) @ np.array([1,0,0])
    actual = chain.advance(2)
    assert actual == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert actual.sum() == pytest.approx(1, abs=1e-15)


def test_scaled_chain_retains_small_stationary_tail():
    chain = BirthDeathChain(n_max=1, capture_rate=lambda n: 0.2,
                           emission_rate=lambda n: 1e8)
    chain.initialize()
    chain.advance(1e-3)
    assert chain.state[1] == pytest.approx(0.2/(1e8+0.2), rel=1e-8)


@pytest.mark.parametrize("birth", [0, 0.01])
def test_ssa_reports_horizon_not_next_event(birth):
    chain = BirthDeathChain(1, lambda n: birth, lambda n: 0)
    count, time = GillespieSampler(chain, seed=7).run_trajectory(1e-6, 0)
    assert time == 1e-6
    assert count == 0


def test_cycling_has_full_duration_residue_and_seed():
    cfg = FilamentConfig(n_max=20, n_conducting=12)
    a = simulate_cycling(cfg, set_field=0.6e8, reset_field=0, pulse_width=1e-4,
                         n_cycles=5, seed=123)
    b = simulate_cycling(cfg, set_field=0.6e8, reset_field=0, pulse_width=1e-4,
                         n_cycles=5, seed=123)
    assert a["time_s"] == pytest.approx(1e-3)
    assert a["cycle_end_times_s"][-1] == pytest.approx(1e-3)
    assert np.array_equal(a["initial_counts"][1:], a["reset_counts"][:-1])
    assert np.array_equal(a["ratios"], b["ratios"])
    assert a["completed"]


def test_cycling_seed_affects_stochastic_trajectory():
    cfg = FilamentConfig(n_max=20, n_conducting=12)
    kwargs = dict(set_field=0.6e8, reset_field=-0.55e8, pulse_width=0.3e-6, n_cycles=12)
    a = simulate_cycling(cfg, seed=1, **kwargs)
    b = simulate_cycling(cfg, seed=2, **kwargs)
    assert not np.array_equal(a["set_counts"], b["set_counts"])
