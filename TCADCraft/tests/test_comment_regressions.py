"""Regression tests for defects identified in the comments review."""

import math

import numpy as np
import pytest

from tcad.physics.electron_counting import BirthDeathChain
from tcad.postprocess.fe_loops import extract_mlc_memory_window
from tcad.search.level_placement import LevelPlacementConfig, _pair_ber
from tcad.search.grammar import MaterialSpec
from tcad.validation.conservation import ConservationTest


def test_uniformization_remains_finite_for_large_poisson_parameter():
    chain = BirthDeathChain(
        n_max=2,
        capture_rate=lambda n: 1000.0,
        emission_rate=lambda n: 0.0,
    )
    chain.initialize(count=0)
    state = chain.advance(1.0)
    assert np.all(np.isfinite(state))
    assert np.all(state >= 0.0)
    assert np.sum(state) == pytest.approx(1.0, abs=1e-12)


def test_pair_ber_uses_one_discrete_decision_boundary():
    config = LevelPlacementConfig(
        n_levels=2, total_budget=1, n_chain=4,
        mu0_per_s=1.0, lam0_per_s=0.0, t_retention_s=1.0,
    )
    # State 1 is lost with probability 1-exp(-1); the lower state cannot
    # cross the threshold, so equal-prior BER is half that tail.
    assert _pair_ber(0.0, 1.0, 0.5, config) == pytest.approx(
        0.5 * (1.0 - math.exp(-1.0)), rel=1e-10,
    )


def test_mlc_window_uses_internal_nonmonotonic_span():
    out = extract_mlc_memory_window(
        [0.0, 1.0, 2.0], [1e-9, 1e-6, 1e-9], 0.1,
    )
    assert out["memory_window_decades"] == pytest.approx(3.0)
    np.testing.assert_array_equal(out["censored_mask"], [False, False, False])


def test_mlc_zero_requires_explicit_noise_floor():
    with pytest.raises(ValueError, match="noise_floor"):
        extract_mlc_memory_window([0.0, 1.0], [0.0, 1e-6])
    out = extract_mlc_memory_window(
        [0.0, 1.0], [0.0, 1e-6], noise_floor=1e-9,
    )
    assert bool(out["censored_mask"][0])
    assert out["raw_read_currents"][0] == 0.0


def test_conservation_rejects_invalid_dict_result():
    result = ConservationTest(check_charge=False, check_energy=False).run(
        lambda: {"valid": False, "converged": False}
    )
    assert not result.passed


def test_material_spec_preserves_extended_fields():
    spec = MaterialSpec(
        name="test", fe_ps=1.4, fe_ec=3.5e8, Dit=2e11,
        tail_DOS=3e20, ii_A_n=7e7,
    )
    material = spec.to_material()
    assert material.fe_ps == 1.4
    assert material.fe_ec == 3.5e8
    assert material.Dit == 2e11
    assert material.tail_DOS == 3e20
    assert material.ii_A_n == 7e7
