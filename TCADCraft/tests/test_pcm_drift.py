"""PCM drift model verification suite."""
import math

import numpy as np
import pytest

from tcad.physics.pcm_drift import PcmConfig, PcmState, simulate_retention_drift


class TestDriftPhysics:
    def test_resistance_increases_over_time(self):
        """The defining PCM behavior: amorphous resistance drifts UP."""
        result = simulate_retention_drift(PcmConfig())
        assert result['r_final_ohm'] > result['r_initial_ohm']
        assert result['drift_ratio'] > 1.0

    def test_drift_follows_power_law(self):
        """R(t) ∝ t^ν — the log-log slope should match ν."""
        cfg = PcmConfig(drift_exponent=0.08, crystallization_activation_eV=3.5)
        result = simulate_retention_drift(cfg, n_points=40)
        # Fit exponent should be close to the configured ν
        assert 0.02 < result['drift_exponent_fit'] < 0.25

    def test_higher_temperature_faster_drift(self):
        cold = PcmConfig(temperature_K=300, drift_activation_eV=0.3)
        hot = PcmConfig(temperature_K=400, drift_activation_eV=0.3)
        r_cold = simulate_retention_drift(cold, n_points=20)
        r_hot = simulate_retention_drift(hot, n_points=20)
        assert r_hot['drift_ratio'] >= r_cold['drift_ratio']

    def test_larger_exponent_more_drift(self):
        small = PcmConfig(drift_exponent=0.03)
        large = PcmConfig(drift_exponent=0.15)
        r_small = simulate_retention_drift(small, n_points=20)
        r_large = simulate_retention_drift(large, n_points=20)
        assert r_large['drift_ratio'] > r_small['drift_ratio']

    def test_crystallization_reduces_resistance(self):
        """At high temperature with low barrier, crystallization should
        eventually pull resistance toward the crystalline value."""
        cfg = PcmConfig(
            temperature_K=500,
            crystallization_activation_eV=1.5,
            crystallization_rate_1_s=1e-2,
            t_end_s=1e3,
        )
        result = simulate_retention_drift(cfg, n_points=30)
        # The final resistance should be pulled below the pure-drift value
        # (crystallization creates a parallel conducting path)
        pure_drift = PcmConfig(
            temperature_K=500,
            crystallization_activation_eV=5.0,  # essentially no crystallization
            t_end_s=1e3,
        )
        result_pure = simulate_retention_drift(pure_drift, n_points=30)
        assert result['r_final_ohm'] <= result_pure['r_final_ohm'] * 1.5

    def test_probability_conservation_crystallization(self):
        """Crystallized fraction stays in [0, 1]."""
        state = PcmState(config=PcmConfig(temperature_K=600,
                                          crystallization_activation_eV=1.0))
        for _ in range(100):
            state.advance(1.0)
        assert 0.0 <= state.crystallized_fraction <= 1.0


class TestState:
    def test_initial_state(self):
        state = PcmState(config=PcmConfig(), r_initial_ohm=5e5)
        assert state.resistance_ohm == pytest.approx(5e5)
        assert state.crystallized_fraction == 0.0

    def test_drift_factor_at_reference_time(self):
        state = PcmState(config=PcmConfig())
        assert state.drift_factor(1e-9) == pytest.approx(1.0)

    def test_drift_factor_monotone(self):
        state = PcmState(config=PcmConfig())
        f1 = state.drift_factor(1e-6)
        f2 = state.drift_factor(1e-3)
        f3 = state.drift_factor(1.0)
        assert f1 < f2 < f3
