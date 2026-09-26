"""Verification suite for the E3 MLC state-design explorer (plan0918 E3).

Analytic goldens for the BER engine (pure-loss binomial, leak-only Poisson),
constraint gates, NSGA-II mechanics reuse, determinism, and the states-vs-
reliability tradeoff that the frontier must expose.
"""

import math

import numpy as np
import pytest

from tcad.physics.electron_counting import BirthDeathChain
from tcad.search.mlc_frontier import (
    MlcFrontierConfig,
    evaluate_mlc_candidate,
    evolve_mlc_frontier,
)
from tcad.search.fe_frontier import _vec_dominates


def binom_cdf_le(n, p, k):
    return float(np.sum([
        math.comb(n, i) * p ** i * (1.0 - p) ** (n - i)
        for i in range(0, k + 1)
    ]))


def poisson_cdf_ge(lam, k):
    total = 0.0
    term = math.exp(-lam)
    for i in range(0, k):
        total += term
        term *= lam / (i + 1.0)
    return max(1.0 - total, 0.0)


class TestBerEngineAnalytic:
    def test_pure_loss_binomial_golden(self):
        config = MlcFrontierConfig(lam0=0.0, mu0=1.0e-8)
        spacing, stress, levels = 6.0, 0.5, 2
        candidate = evaluate_mlc_candidate(
            {"spacing": spacing, "stress_scale": stress}, levels, config,
        )
        assert candidate.trusted, candidate.violations
        q = math.exp(-config.mu0 * stress * config.t_retention)
        n_upper = int(round(2 * spacing))
        boundary = 1.5 * spacing
        expected_down = binom_cdf_le(n_upper, q, int(np.ceil(boundary - 1e-9)) - 1)
        assert candidate.worst_pair_error == pytest.approx(expected_down, rel=1e-10)

    def test_leak_only_poisson_golden(self):
        config = MlcFrontierConfig(lam0=2.0e-9, mu0=0.0)
        spacing, stress, levels = 5.0, 1.0, 2
        candidate = evaluate_mlc_candidate(
            {"spacing": spacing, "stress_scale": stress}, levels, config,
        )
        assert candidate.trusted
        lam = config.lam0 * stress * config.t_retention
        boundary = 1.5 * spacing
        # Up-confusion from the lower level (start = spacing).
        expected_up = poisson_cdf_ge(lam, int(np.floor(boundary + 1e-9)) + 1 - int(spacing))
        assert candidate.worst_pair_error == pytest.approx(expected_up, rel=1e-9)

    def test_reliability_capped_at_floor(self):
        config = MlcFrontierConfig(
            lam0=0.0, mu0=1.0e-12, spacing=(10.0, 10.0),
            stress_scale=(0.05, 0.05),
        )
        candidate = evaluate_mlc_candidate(
            {"spacing": 10.0, "stress_scale": 0.05}, 2, config,
        )
        assert candidate.trusted
        assert candidate.reliability <= 16.0 + 1e-9
        # The exact engine returns the true (tiny) binomial tail, which is
        # below the reporting floor but not identically zero.
        assert 0.0 <= candidate.worst_pair_error < 1e-20

    def test_more_states_or_smaller_spacing_degrade_reliability(self):
        # Small-loss regime (per-electron survival ~99.4%): intuition holds.
        # Note the default stress_scale lower bound is 0.05 (per-electron
        # loss ~15%); this test widens the bound so the declared stress is
        # actually used. At harsh stress the ordering inverts because larger
        # stacks have more absolute loss.
        config = MlcFrontierConfig(stress_scale=(0.001, 1.0))
        two = evaluate_mlc_candidate(
            {"spacing": 8.0, "stress_scale": 0.002}, 2, config,
        )
        eight = evaluate_mlc_candidate(
            {"spacing": 8.0, "stress_scale": 0.002}, 8, config,
        )
        tight = evaluate_mlc_candidate(
            {"spacing": 3.0, "stress_scale": 0.002}, 2, config,
        )
        assert two.reliability > eight.reliability
        assert two.reliability > tight.reliability


class TestConstraintGate:
    def test_budget_cap_rejects(self):
        config = MlcFrontierConfig(n_max_cap=200)
        candidate = evaluate_mlc_candidate(
            {"spacing": 16.0, "stress_scale": 0.5}, 16, config,
        )
        assert not candidate.trusted
        assert any("cap" in v for v in candidate.violations)

    def test_invalid_levels_rejects(self):
        config = MlcFrontierConfig()
        candidate = evaluate_mlc_candidate(
            {"spacing": 4.0, "stress_scale": 0.5}, 3, config,
        )
        assert not candidate.trusted
        assert not candidate.violations == []

    def test_bounds_clipped(self):
        config = MlcFrontierConfig()
        candidate = evaluate_mlc_candidate(
            {"spacing": 100.0, "stress_scale": 5.0}, 2, config,
        )
        assert candidate.x["spacing"] <= config.spacing[1]
        assert candidate.x["stress_scale"] <= config.stress_scale[1]


class TestChainInterface:
    def test_uses_birth_death_chain_directly(self):
        chain = BirthDeathChain(
            n_max=10,
            capture_rate=lambda n: 1e-9,
            emission_rate=lambda n: 1e-8 * n,
        )
        chain.initialize(count=10)
        chain.advance(1.0e8)
        assert chain.survival(5) > 0.0
        assert abs(float(np.sum(chain.state)) - 1.0) <= 1e-12


class TestEvolutionRun:
    def test_deterministic_run(self):
        result_a = evolve_mlc_frontier(
            MlcFrontierConfig(), population_size=8, generations=3, seed=11,
        )
        result_b = evolve_mlc_frontier(
            MlcFrontierConfig(), population_size=8, generations=3, seed=11,
        )
        for ra, rb in zip(result_a.to_rows(), result_b.to_rows()):
            for key in ("levels", "spacing", "stress_scale", "reliability_neg_log10_ber"):
                assert ra[key] == pytest.approx(rb[key], rel=1e-12, abs=1e-15)

    def test_front_is_nondominated_and_multi_level(self):
        seeds = [
            {"levels": 2, "spacing": 12.0, "stress_scale": 0.5},
            {"levels": 16, "spacing": 4.0, "stress_scale": 0.1},
            {"levels": 4, "spacing": 8.0, "stress_scale": 0.3},
            {"levels": 8, "spacing": 6.0, "stress_scale": 0.2},
        ]
        result = evolve_mlc_frontier(
            MlcFrontierConfig(), population_size=12, generations=5, seed=3,
            init_population=seeds,
        )
        assert result.front, "front must contain trusted candidates"
        objectives = np.vstack([c.objectives for c in result.front])
        for i in range(len(objectives)):
            for j in range(len(objectives)):
                if i != j:
                    assert not _vec_dominates(objectives[j], objectives[i])
        levels = [c.levels for c in result.front]
        assert len(set(levels)) >= 2
        # The tradeoff: the highest-bits front member is not the most reliable.
        bits = np.array([c.bits for c in result.front])
        reliability = np.array([c.reliability for c in result.front])
        best_bits_idx = int(np.argmax(bits))
        assert reliability[best_bits_idx] < reliability.max()

    def test_history_counts_every_evaluation(self):
        result = evolve_mlc_frontier(
            MlcFrontierConfig(), population_size=8, generations=3, seed=1,
        )
        assert len(result.history) == 8 * (3 + 1)
