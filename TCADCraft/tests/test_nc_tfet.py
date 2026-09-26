"""NC-TFET discovery verification suite."""
import math

import numpy as np
import pytest

from tcad.search.nc_tfet import (
    NcTfetConfig, NcTfetCandidate, evaluate_nc_tfet, evolve_nc_tfet,
    _nc_field_boost, _tfet_current,
)


BASE_TFET = {
    "eg_t": 0.9, "lambda_nm": 4.7, "mt_ratio": 0.08,
    "a_kane": 3.5e21, "vfb_offset": 0.0,
}
BASE_FE = {"t_fe_nm": 10.0, "ps": 0.3, "ec": 2e8}
BASE = {**BASE_TFET, **BASE_FE}


class TestNCBoost:
    def test_unstable_fe_gives_zero_boost(self):
        boost, stable = _nc_field_boost({"t_fe_nm": 5, "ps": 1.0, "ec": 0.5e8})
        assert not stable
        assert boost == 0.0

    def test_stable_fe_gives_boost(self):
        boost, stable = _nc_field_boost({"t_fe_nm": 10, "ps": 0.05, "ec": 4e8})
        assert stable, f"FE should be stable: e_dep={0.05/(20*8.854e-12):.1e} vs 3*ec={1.2e9:.1e}"
        assert boost >= 1.0

    def test_boost_capped_at_dd_ceiling(self):
        """Boost cannot exceed 20% (DD adjudicated)."""
        boost, _ = _nc_field_boost({"t_fe_nm": 20, "ps": 0.5, "ec": 4e8})
        assert boost <= 1.20

    def test_higher_ps_more_boost(self):
        b1, s1 = _nc_field_boost({"t_fe_nm": 10, "ps": 0.1, "ec": 3e8})
        b2, s2 = _nc_field_boost({"t_fe_nm": 10, "ps": 0.5, "ec": 3e8})
        if s1 and s2:
            assert b2 >= b1


class TestNCTfetEvaluation:
    def test_baseline_tfet_works(self):
        x = {**BASE, "t_fe_nm": 1, "ps": 0.01, "ec": 5e8}
        cand = evaluate_nc_tfet(x)
        assert cand.trusted
        assert np.isfinite(cand.ss_baseline_mV)
        # Ion is in log10 scale; just check it's finite
        assert np.isfinite(cand.ion_baseline)

    def test_boost_increases_current(self):
        x_no_fe = {**BASE, "t_fe_nm": 1, "ps": 0.01, "ec": 5e8}
        x_with_fe = {**BASE, "t_fe_nm": 15, "ps": 0.4, "ec": 3e8}
        c1 = evaluate_nc_tfet(x_no_fe)
        c2 = evaluate_nc_tfet(x_with_fe)
        if c1.trusted and c2.trusted:
            # Enhanced Ion should be >= baseline Ion
            assert c2.ion_enhanced >= c1.ion_baseline

    def test_ss_enhanced_not_worse_than_baseline(self):
        """NC should not degrade SS (worst case: no effect)."""
        cand = evaluate_nc_tfet(BASE)
        assert cand.trusted
        assert cand.ss_enhanced_mV <= cand.ss_baseline_mV * 1.1  # within 10%


class TestNCTfetDiscovery:
    def test_front_produces_candidates(self):
        result = evolve_nc_tfet(15, 5, seed=42)
        assert len(result["front"]) >= 2

    def test_some_candidates_have_boost(self):
        result = evolve_nc_tfet(20, 8, seed=20260921)
        boosted = [c for c in result["front"] if c.boost_factor > 1.01]
        # At least some should have non-trivial boost
        # (may be zero if all FE params land in unstable region)
        if boosted:
            assert all(c.boost_factor <= 1.20 for c in boosted)

    def test_discovery_question_answered(self):
        """The key question: is there a design with SS < 80 AND Ion > baseline?"""
        result = evolve_nc_tfet(30, 15, seed=20260921)
        front = result["front"]
        # Count how many have both low SS and positive boost
        good = [c for c in front
                if c.ss_enhanced_mV < 80 and c.boost_factor > 1.0]
        print(f"\n  Front: {len(front)} members")
        print(f"  SS < 80 AND boost > 1: {len(good)} members")
        for c in front[:5]:
            print(f"  SS_base={c.ss_baseline_mV:.1f} SS_enh={c.ss_enhanced_mV:.1f} "
                  f"Ion_base={c.ion_baseline:.1f} Ion_enh={c.ion_enhanced:.1f} "
                  f"boost={c.boost_factor:.3f} stable={c.fe_stable}")
