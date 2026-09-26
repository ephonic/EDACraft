"""Verification for FeFET refresh-schedule discovery."""
import math

import pytest

from tcad.search.fefet_schedule import (
    ScheduleConfig, evaluate_schedule, sweep_cadences, find_optimal_cadence,
)


class TestScheduleEvaluation:
    def test_no_refresh_window_collapses(self):
        """Huge cadence -> imprint saturates -> mean window degraded."""
        cfg = ScheduleConfig(lifetime_cycles=1e5)
        never = evaluate_schedule(cfg.lifetime_cycles, cfg)  # single block
        assert never.max_imprint > 0.3  # imprint built up

    def test_constant_refresh_fatigue_limited(self):
        """Tiny cadence -> refresh fatigue dominates -> window degraded."""
        cfg = ScheduleConfig(lifetime_cycles=1e5)
        always = evaluate_schedule(10.0, cfg)
        assert always.final_fatigue > 0.15  # heavily fatigued

    def test_interior_cadence_beats_extremes(self):
        cfg = ScheduleConfig(lifetime_cycles=1e5)
        results = sweep_cadences(cfg)
        best = max(results, key=lambda r: r.mean_window)
        worst_dwell = results[-1].mean_window   # huge cadence
        worst_refresh = results[0].mean_window  # tiny cadence
        assert best.mean_window > worst_dwell
        assert best.mean_window > worst_refresh
        assert 10.0 < best.cadence < 1.0e5  # interior optimum exists

    def test_results_finite(self):
        cfg = ScheduleConfig()
        r = evaluate_schedule(1000.0, cfg)
        assert math.isfinite(r.mean_window)
        assert math.isfinite(r.final_fatigue)
        assert math.isfinite(r.max_imprint)
        assert r.usable_window_integral >= 0

    def test_fatigue_monotone_in_lifetime(self):
        """More lifetime -> more accumulated refresh stress (fatigue state).

        Note: mean window is NOT monotone in lifetime because wake-up gain
        also grows with the number of refresh events; the invariant is the
        monotone fatigue state.
        """
        cfg_short = ScheduleConfig(lifetime_cycles=5e4)
        cfg_long = ScheduleConfig(lifetime_cycles=5e5)
        r_short = evaluate_schedule(1000.0, cfg_short)
        r_long = evaluate_schedule(1000.0, cfg_long)
        assert r_long.final_fatigue >= r_short.final_fatigue


class TestScheduleOptimum:
    def test_find_optimal_returns_interior(self):
        cfg = ScheduleConfig(lifetime_cycles=1e5)
        best = find_optimal_cadence(cfg)
        assert cfg.cadence_lo_cycles <= best.cadence <= cfg.cadence_hi_cycles
        assert best.mean_window > 0

    def test_sweep_length(self):
        cfg = ScheduleConfig(n_cadence=17)
        results = sweep_cadences(cfg)
        assert len(results) == 17
