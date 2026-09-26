"""Verification for level placement discovery."""
import math

import numpy as np
import pytest

from tcad.search.level_placement import (
    LevelPlacementConfig, LevelPlacementCandidate,
    _gaps_to_positions, _pair_ber, evaluate_placement, evolve_placement,
)


class TestGapParameterization:
    def test_uniform_logits_give_uniform_positions(self):
        K = 8
        pos = _gaps_to_positions(np.zeros(K - 1), 200.0, K)
        np.testing.assert_allclose(pos, np.linspace(0, 200, K), atol=1e-9)

    def test_any_logits_valid(self):
        """Even extreme logits must give strictly increasing in-range positions."""
        rng = np.random.default_rng(0)
        for _ in range(20):
            z = rng.normal(0, 5, size=31)
            pos = _gaps_to_positions(z, 200.0, 32)
            assert pos[0] == 0.0
            assert pos[-1] == pytest.approx(200.0, abs=1e-6)
            assert np.all(np.diff(pos) > 1.0)  # > MIN_GAP_E - rounding

    def test_first_last_pinned(self):
        pos = _gaps_to_positions(np.array([3.0, -2.0, 5.0]), 100.0, 4)
        assert pos[0] == 0.0
        assert pos[-1] == pytest.approx(100.0)


class TestPlacementEvaluation:
    def test_uniform_reference_consistent(self):
        """Zero-logit input should equal the internal uniform baseline."""
        config = LevelPlacementConfig(n_levels=4)
        cand = evaluate_placement(np.zeros(3), config)
        assert cand.trusted
        assert cand.improvement_factor == pytest.approx(1.0, rel=1e-9)

    def test_wider_spacing_lower_ber(self):
        """Wider spacing between a pair should reduce BER."""
        config = LevelPlacementConfig(n_levels=2, total_budget=40)
        ber_narrow = _pair_ber(18, 22, 20, config)  # 4e spacing
        ber_wide = _pair_ber(10, 30, 20, config)     # 20e spacing
        assert ber_wide < ber_narrow

    def test_ber_bounded(self):
        config = LevelPlacementConfig(n_levels=4, total_budget=20)
        cand = evaluate_placement(np.array([0.3, -0.1, 0.2]), config)
        assert cand.trusted
        assert 0 <= cand.ber_worst <= 1.0

    def test_effective_bits_positive(self):
        config = LevelPlacementConfig(n_levels=4, total_budget=40)
        cand = evaluate_placement(np.zeros(3), config)
        assert 0 < cand.effective_bits <= math.log2(4)


class TestPlacementOptimization:
    def test_optimization_improves_ber(self):
        """Optimized placement should beat uniform when headroom exists."""
        config = LevelPlacementConfig(n_levels=16, total_budget=200)
        result = evolve_placement(config, pop=25, gen=15, seed=42)
        front = result["front"]
        assert len(front) >= 1
        best = min(front, key=lambda c: c.ber_worst)
        # High-K regime has large headroom; demand a real improvement
        assert best.improvement_factor > 1.5

    def test_k8_produces_valid_placement(self):
        config = LevelPlacementConfig(n_levels=8, total_budget=200)
        result = evolve_placement(config, pop=12, gen=6, seed=7)
        assert len(result["front"]) >= 1
        for c in result["front"]:
            assert len(c.positions) == 8
            assert c.positions[0] == 0.0
            assert c.positions[-1] == pytest.approx(200.0, abs=1e-6)
            assert np.all(np.diff(c.positions) > 0)

    def test_deterministic(self):
        a = evolve_placement(LevelPlacementConfig(n_levels=4), 8, 3, seed=99)
        b = evolve_placement(LevelPlacementConfig(n_levels=4), 8, 3, seed=99)
        for ca, cb in zip(a["population"], b["population"]):
            np.testing.assert_allclose(ca.positions, cb.positions, atol=1e-10)
