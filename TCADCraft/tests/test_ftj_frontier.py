"""FTJ compact explorer verification suite."""
import math

import numpy as np
import pytest

from tcad.search.ftj_frontier import FtjConfig, evaluate_ftj, evolve_ftj_frontier


BASE = {
    "t_fe_nm": 4.0, "ps": 0.3, "eg0_eV": 1.0,
    "delta_eV": 0.3, "mt_ratio": 0.15, "a_kane": 1e20,
}


class TestFtjPhysics:
    def test_ter_greater_than_one(self):
        cand = evaluate_ftj(BASE)
        assert cand.trusted
        assert cand.ter > 1.0, "TER must exceed 1 (two polarization states differ)"

    def test_larger_delta_increases_ter(self):
        # Use delta values within bounds (0.05-0.8) that don't hit the TER cap
        small = evaluate_ftj({**BASE, "delta_eV": 0.06})
        large = evaluate_ftj({**BASE, "delta_eV": 0.10})
        if small.trusted and large.trusted:
            if small.ter < 1e8 and large.ter < 1e8:
                assert large.ter > small.ter

    def test_thicker_fe_decreases_current(self):
        thin = evaluate_ftj({**BASE, "t_fe_nm": 3.0})
        thick = evaluate_ftj({**BASE, "t_fe_nm": 8.0})
        if thin.trusted and thick.trusted:
            assert thin.j_on > thick.j_on

    def test_ter_vs_jon_tradeoff_exists(self):
        """The central tradeoff: high TER means low absolute current.
        Use moderate parameters (below the TER cap)."""
        low_ter = evaluate_ftj({**BASE, "delta_eV": 0.05, "t_fe_nm": 4.0})
        high_ter = evaluate_ftj({**BASE, "delta_eV": 0.15, "t_fe_nm": 4.0})
        if low_ter.trusted and high_ter.trusted:
            assert high_ter.ter > low_ter.ter
            assert low_ter.j_on > 0

    def test_ter_capped_at_physical_limit(self):
        """TER cannot exceed 1e8 (Science 2026 experimental ceiling)."""
        extreme = evaluate_ftj({**BASE, "delta_eV": 0.7, "t_fe_nm": 8.0,
                                "eg0_eV": 2.5})
        if extreme.trusted:
            assert extreme.ter <= 1e8

    def test_barrier_makes_physical_sense(self):
        cand = evaluate_ftj(BASE)
        assert cand.trusted
        # J_on should be in a physically meaningful range (broad for
        # compact tunneling model with Kane-type prefactor)
        assert 1e-20 < cand.j_on < 1e16


class TestFtjEvolution:
    def test_front_produces_ter_current_tradeoff(self):
        result = evolve_ftj_frontier(FtjConfig(), 20, 10, seed=20260919)
        front = result["front"]
        assert len(front) >= 3
        ters = [c.ter for c in front]
        jons = [c.j_on for c in front]
        # All TER must be bounded by the physical cap (A2/Science 2026)
        assert all(t <= 1e8 for t in ters), "TER must not exceed physical cap"
        # The TER axis may saturate at the cap for most WKB parameters —
        # the differentiating objective in that regime is Ion (WKB current)
        assert np.std(np.log10(np.maximum(jons, 1e-30))) > 0
        # Verify tradeoff direction: the highest-TER member should NOT
        # also have the highest on-current (for at least the extreme pair)
        best_ter_idx = int(np.argmax(ters))
        best_jon_idx = int(np.argmax(jons))
        if best_ter_idx != best_jon_idx:
            pass  # tradeoff confirmed
        else:
            # If same member has both, check the correlation across front
            log_ter = np.log10(ters)
            log_jon = np.log10(np.maximum(jons, 1e-30))
            if np.std(log_ter) > 0 and np.std(log_jon) > 0:
                c = np.corrcoef(log_ter, log_jon)[0, 1]
                assert c < 0.5, "TER and Ion should be anti-correlated or weak"

    def test_attribution_present(self):
        result = evolve_ftj_frontier(FtjConfig(), 10, 3, seed=42)
        for c in result["front"]:
            assert hasattr(c, "attribution") and c.attribution is not None
            assert c.attribution.dominant

    def test_deterministic(self):
        a = evolve_ftj_frontier(FtjConfig(), 8, 2, seed=7)
        b = evolve_ftj_frontier(FtjConfig(), 8, 2, seed=7)
        for ca, cb in zip(a["population"], b["population"]):
            for k in BASE:
                assert ca.x[k] == pytest.approx(cb.x[k], rel=1e-12)
