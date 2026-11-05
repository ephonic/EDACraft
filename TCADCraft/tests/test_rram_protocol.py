"""Verification for RRAM protocol discovery."""
import math

import numpy as np
import pytest

from tcad.search.rram_protocol import (
    ProtocolConfig, ProtocolPoint, _simulate_protocol, sweep_protocols,
    pareto_front, find_elbow, find_reliable_optimal,
    compare_pulse_strategies,
)


class TestProtocolSimulation:
    def test_weak_protocol_not_formed(self):
        cfg = ProtocolConfig(n_cycles=6)
        p = _simulate_protocol(0.45e8, 0.2e-6, 1, cfg)
        assert p.p_on < 0.5  # weak field, short pulse: mostly OFF

    def test_strong_protocol_saturates(self):
        cfg = ProtocolConfig(n_cycles=6)
        p = _simulate_protocol(0.75e8, 3.0e-6, 1, cfg)
        assert p.p_on > 0.95  # strong overdrive: always ON

    def test_mid_protocol_partial(self):
        cfg = ProtocolConfig(n_cycles=12)
        p = _simulate_protocol(0.60e8, 1.0e-6, 1, cfg)
        assert 0.05 < p.p_on < 0.99  # stochastic forming window

    def test_ratio_positive_when_on(self):
        cfg = ProtocolConfig(n_cycles=8)
        p = _simulate_protocol(0.75e8, 1.0e-6, 1, cfg)
        assert p.mean_log_ratio > 0

    def test_finite_statistics(self):
        cfg = ProtocolConfig(n_cycles=8)
        p = _simulate_protocol(0.6e8, 1.0e-6, 1, cfg)
        assert math.isfinite(p.mean_log_ratio)
        assert math.isfinite(p.sigma_log_ratio)
        assert p.sigma_log_ratio >= 0


class TestProtocolSweep:
    def test_sweep_produces_grid(self):
        cfg = ProtocolConfig(n_field=3, n_width=3, n_cycles=6)
        pts = sweep_protocols(cfg)
        assert len(pts) == 9

    def test_pareto_front_subset(self):
        cfg = ProtocolConfig(n_field=4, n_width=4, n_cycles=8)
        pts = sweep_protocols(cfg)
        front = pareto_front(pts)
        assert 1 <= len(front) <= len(pts)
        # Front members must not dominate each other
        for i, a in enumerate(front):
            for j, b in enumerate(front):
                if i != j:
                    dominant = (np.all(a.objectives >= b.objectives)
                                and np.any(a.objectives > b.objectives))
                    assert not dominant

    def test_elbow_unsaturated(self):
        cfg = ProtocolConfig(n_field=6, n_width=5, n_cycles=10)
        pts = sweep_protocols(cfg)
        elbow = find_elbow(pts)
        if elbow is not None:
            assert elbow.p_on < 0.995

    def test_reliable_optimal_satisfies_constraint(self):
        cfg = ProtocolConfig(n_field=6, n_width=5, n_cycles=12)
        pts = sweep_protocols(cfg)
        r = find_reliable_optimal(pts, p_on_min=0.9)
        if r is not None:
            assert r.p_on >= 0.9
        # Sweeping the full grid must find at least one reliable protocol
        full = ProtocolConfig(n_cycles=20)
        pts_full = sweep_protocols(full)
        assert find_reliable_optimal(pts_full, 0.9) is not None

    def test_pulse_strategies_run(self):
        cfg = ProtocolConfig(n_cycles=8)
        out = compare_pulse_strategies(cfg)
        assert set(out.keys()) == {"1_pulse", "2_pulse", "4_pulse",
                                   "adaptive"}
        for p in out.values():
            assert math.isfinite(p.mean_log_ratio)

    def test_adaptive_uses_fewer_pulses_than_its_maximum(self):
        """Verify-and-stop uses fewer pulses than the fixed budget allows."""
        from tcad.search.rram_protocol import _simulate_adaptive
        cfg = ProtocolConfig(n_cycles=40)
        p = _simulate_adaptive(0.60e8, 0.5e-6, 6, cfg)
        assert 1 <= p.n_pulses <= 6
        # If forming typically happens within the budget, the adaptive
        # strategy must apply fewer than the max on average
        if p.p_on > 0.5:
            assert p.n_pulses < 6
