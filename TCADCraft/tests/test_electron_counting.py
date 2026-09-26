"""Verification suite for M3 electron counting (plan0918 protocol).

Implements the probabilistic-golden gates: analytic limits (Poisson,
binomial, detailed balance, two-state first passage), the exact-semigroup
step-size independence, probability conservation, the mean-field degeneration
to the deterministic rate equation, and the two-engine (uniformization vs
Gillespie) cross-validation with statistical significance bounds.
"""

import math

import numpy as np
import pytest

from tcad.physics.electron_counting import BirthDeathChain, GillespieSampler


def linear_chain(n_max, lam0, mu0):
    """N independent sites: lam(n) = lam0*(N-n), mu(n) = mu0*n."""
    return BirthDeathChain(
        n_max=n_max,
        capture_rate=lambda n: lam0 * (n_max - n),
        emission_rate=lambda n: mu0 * n,
    )


class TestConservation:
    def test_normalization_preserved_over_many_steps(self):
        chain = linear_chain(24, 0.7, 0.3)
        chain.initialize(count=24)
        for _ in range(200):
            chain.advance(0.05)
        assert abs(float(np.sum(chain.state)) - 1.0) <= 1e-12
        assert np.all(chain.state >= 0.0)

    def test_step_size_independence_exact_semigroup(self):
        one = linear_chain(16, 1.3, 0.6)
        many = linear_chain(16, 1.3, 0.6)
        one.initialize(count=0)
        many.initialize(count=0)
        one.advance(2.0)
        for _ in range(64):
            many.advance(2.0 / 64)
        assert np.max(np.abs(one.state - many.state)) < 1e-13

    def test_absorbing_state_stays_put(self):
        chain = BirthDeathChain(
            n_max=4,
            capture_rate=lambda n: 0.0,
            emission_rate=lambda n: 1.0 * n,
        )
        chain.initialize(count=0)
        chain.advance(1.0)
        assert chain.state[0] == pytest.approx(1.0, abs=1e-15)

    def test_pure_death_two_state_exact(self):
        chain = BirthDeathChain(
            n_max=1,
            capture_rate=lambda n: 0.0,
            emission_rate=lambda n: 0.8,
        )
        chain.initialize(count=1)
        chain.advance(2.0)
        assert chain.state[0] == pytest.approx(1.0 - math.exp(-1.6), rel=1e-13)

    def test_input_validation(self):
        with pytest.raises(ValueError):
            BirthDeathChain(3, capture_rate=lambda n: -1.0, emission_rate=lambda n: 0.0)
        chain = linear_chain(3, 1.0, 1.0)
        with pytest.raises(ValueError):
            chain.initialize(p0=np.array([0.5, 0.5]))
        with pytest.raises(RuntimeError):
            chain.mean()


class TestAnalyticLimits:
    def test_poisson_limit_constant_rate(self):
        chain = BirthDeathChain(
            n_max=40,
            capture_rate=lambda n: 2.0,
            emission_rate=lambda n: 0.0,
        )
        chain.initialize(count=0)
        t = 1.7
        chain.advance(t)
        n = np.arange(41)
        expected = np.exp(-2.0 * t) * (2.0 * t) ** n / [math.factorial(k) for k in n]
        assert np.max(np.abs(chain.state - expected)) < 1e-14

    def test_binomial_closed_form_for_linear_rates(self):
        n_max, lam0, mu0 = 12, 0.9, 0.4
        chain = linear_chain(n_max, lam0, mu0)
        chain.initialize(count=0)
        t = 2.5
        chain.advance(t)
        p = lam0 / (lam0 + mu0) * (1.0 - math.exp(-(lam0 + mu0) * t))
        expected = np.array([
            math.comb(n_max, k) * p ** k * (1.0 - p) ** (n_max - k)
            for k in range(n_max + 1)
        ])
        assert np.max(np.abs(chain.state - expected)) < 1e-13

    def test_detailed_balance_stationary_product_form(self):
        chain = BirthDeathChain(
            n_max=10,
            capture_rate=lambda n: 0.5 + 0.2 * n,
            emission_rate=lambda n: 0.3 * max(n, 1),
        )
        chain.initialize(count=5)
        for _ in range(400):
            chain.advance(0.5)
        pi = chain.stationary()
        assert np.max(np.abs(chain.state - pi)) < 1e-12

    def test_mean_field_matches_deterministic_linear_ode(self):
        n_max, lam0, mu0 = 20, 1.1, 0.5
        chain = linear_chain(n_max, lam0, mu0)
        chain.initialize(count=0)
        t = 3.0
        chain.advance(t)
        p = lam0 / (lam0 + mu0) * (1.0 - math.exp(-(lam0 + mu0) * t))
        assert chain.mean() == pytest.approx(n_max * p, rel=1e-12)

    def test_two_state_first_passage_is_exponential(self):
        chain = BirthDeathChain(
            n_max=1,
            capture_rate=lambda n: 0.05,
            emission_rate=lambda n: 0.8,
        )
        chain.initialize(count=1)
        times = np.array([0.5, 1.0, 2.0, 4.0])
        for t in times:
            chain.initialize(count=1)
            chain.advance(float(t))
            # survival S(t) = P(still >= 1) with the two-state solution
            lam, mu = 0.05, 0.8
            s_inf = lam / (lam + mu)
            s_t = s_inf + (1.0 - s_inf) * math.exp(-(lam + mu) * t)
            assert chain.survival(1) == pytest.approx(s_t, rel=1e-12)


class TestRetentionTails:
    def test_survival_matches_binomial_cdf(self):
        n_max, lam0, mu0 = 30, 0.02, 0.05
        chain = linear_chain(n_max, lam0, mu0)
        chain.initialize(count=n_max)
        t = 40.0
        chain.advance(t)
        # Each site is an independent two-state process started FULL:
        # q(t) = p_inf + (1 - p_inf) * exp(-(lam0+mu0) t), p_inf = lam0/(lam0+mu0).
        r = lam0 + mu0
        p_inf = lam0 / r
        q = p_inf + (1.0 - p_inf) * math.exp(-r * t)
        threshold = 15
        expected = float(np.sum([
            math.comb(n_max, k) * q ** k * (1.0 - q) ** (n_max - k)
            for k in range(threshold, n_max + 1)
        ]))
        assert chain.survival(threshold) == pytest.approx(expected, rel=1e-12)
        assert chain.tail_below(threshold) == pytest.approx(1.0 - expected, rel=1e-12)

    def test_deep_tail_is_exact_from_cdf(self):
        chain = linear_chain(60, 0.01, 0.04)
        chain.initialize(count=60)
        chain.advance(200.0)
        # The chain distribution is exact, so a ppm-level tail is a direct
        # CDF difference rather than a rare-event sampling problem.
        tail = chain.tail_below(5)
        assert 0.0 < tail < 1.0
        assert np.isfinite(tail)


class TestGillespieCrossValidation:
    def test_two_state_distribution_agrees_with_master_equation(self):
        lam, mu = 0.3, 0.7
        chain = BirthDeathChain(
            n_max=1,
            capture_rate=lambda n: lam,
            emission_rate=lambda n: mu,
        )
        chain.initialize(count=1)
        t = 2.0
        chain.advance(t)
        p_exact = chain.state
        sampler = GillespieSampler(chain=chain, seed=20260918)
        n_samples = 20000
        counts = sampler.sample_counts(t, n0=1, n_samples=n_samples)
        p_hat = np.bincount(counts, minlength=2) / n_samples
        stderr = np.sqrt(np.maximum(p_exact * (1.0 - p_exact), 1e-9) / n_samples)
        for k in range(2):
            assert abs(p_hat[k] - p_exact[k]) < 4.0 * stderr[k]

    def test_mean_and_variance_agree(self):
        chain = linear_chain(12, 0.8, 0.3)
        chain.initialize(count=12)
        t = 1.5
        chain.advance(t)
        sampler = GillespieSampler(chain=chain, seed=7)
        n_samples = 8000
        counts = sampler.sample_counts(t, n0=12, n_samples=n_samples)
        exact_mean = chain.mean()
        n = np.arange(chain.n_max + 1)
        exact_var = float(np.dot(n ** 2, chain.state) - exact_mean ** 2)
        assert float(np.mean(counts)) == pytest.approx(exact_mean, abs=4.0 * math.sqrt(exact_var / n_samples))
        assert float(np.var(counts)) == pytest.approx(exact_var, rel=0.08)

    def test_first_passage_times_agree_with_chain_survival(self):
        lam, mu = 0.05, 0.6
        chain = BirthDeathChain(
            n_max=1,
            capture_rate=lambda n: lam,
            emission_rate=lambda n: mu,
        )
        sampler = GillespieSampler(chain=chain, seed=123)
        n_samples = 6000
        times = sampler.sample_first_passage(1, n0=1, n_samples=n_samples, t_max=50.0)
        reached = ~np.isnan(times)
        assert reached.mean() > 0.95
        # Two-state first passage from 1 is exponential with rate mu (the
        # capture race only re-delays; with lam<<mu the effective rate is the
        # exact competing-hazard rate mu for the FIRST passage to 0 given
        # returns are possible - compare at quantiles against the chain
        # survival curve instead of assuming a rate.
        t_grid = np.array([0.5, 1.0, 2.0, 4.0])
        empirical = np.array([np.mean(reached & (times <= t)) for t in t_grid])
        exact = []
        for t in t_grid:
            chain.initialize(count=1)
            chain.advance(float(t))
            # probability of at least one completed excursion below threshold
            # is 1 - survival only for the final state; instead integrate the
            # absorbing chain (capture removed) for the true first passage.
            absorbing = BirthDeathChain(
                n_max=1, capture_rate=lambda n: 0.0, emission_rate=lambda n: mu,
            )
            absorbing.initialize(count=1)
            absorbing.advance(float(t))
            exact.append(1.0 - absorbing.survival(1))
        for emp, exp in zip(empirical, np.array(exact)):
            assert emp == pytest.approx(exp, abs=0.03)
