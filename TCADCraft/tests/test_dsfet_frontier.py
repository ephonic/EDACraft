"""Verification suite for the E4 cold-source/Dirac-source explorer (plan0918 E4).

Physics anchors (probed and verified 2026-09-18):
* The steep window comes from the SUPPLY-SIDE energy filter, not the Dirac
  DOS alone (filter-open limit gives SS = 60*(1+kT/w) > 60).
* In the window, SS ~ 1.151 * x mV/dec with x = E_cut - E_b [meV]:
  sub-60 for x < 52 meV, i.e. a ~(52 + kT) ~ 78 mV gate window.
* Degenerate source filling buys on-current at the price of the off-state
  (leak through the filter), and short-channel smearing destroys the filter.
"""

import math

import numpy as np
import pytest

from tcad.search.fe_frontier import _vec_dominates
from tcad.search.dsfet_frontier import (
    DsFetConfig,
    _transfer_curve,
    evaluate_dsfet_candidate,
    evolve_dsfet_frontier,
    k_b_mev,
    K_B_MEV_300K,
    SS_THERMAL,
)

BASE = {
    "filter_window_meV": 150.0,
    "filter_cutoff_meV": 100.0,
    "source_fermi_meV": -25.0,
    "lambda_sc_nm": 3.0,
    "vdd": 0.5,
}


def interval_swings(x, config, lg_nm=None):
    config = config or DsFetConfig()
    lg = config.lg0_nm if lg_nm is None else lg_nm
    vg, cur = _transfer_curve(x, config, lg)
    li = np.log10(cur)
    vg_mid, ss = [], []
    for k in range(1, len(vg)):
        if cur[k] > cur[k - 1] and (li[k] - li[k - 1]) > 1e-6:
            vg_mid.append(0.5 * (vg[k] + vg[k - 1]))
            ss.append((vg[k] - vg[k - 1]) / (li[k] - li[k - 1]) * 1000.0)
    return np.asarray(vg_mid), np.asarray(ss)


class TestAnalyticGoldens:
    def test_filter_edge_quadratic_swing(self):
        # In the steep window SS ~ 1.151 * x [mV/dec]; at the verified
        # design the minimum lands near x ~ 17 meV -> SS ~ 19-20.
        config = DsFetConfig()
        _, ss = interval_swings(BASE, config)
        assert ss.min() < 25.0
        assert ss.min() > 15.0

    def test_sub60_window_is_narrow(self):
        # Sub-60 exists only while E_cut - E_b < 52 meV (plus the kT
        # thermal rounding of the filter edge): the gate span with SS < 60
        # must stay below ~100 mV.
        config = DsFetConfig()
        vg_mid, ss = interval_swings(BASE, config)
        below = ss < 60.0
        assert np.any(below)
        span_mV = (vg_mid[below].max() - vg_mid[below].min()) * 1000.0
        assert span_mV < 100.0

    def test_filter_open_limit_is_above_thermal(self):
        # A vanishing DOS alone does not cool the tail: with a wide filter
        # window most of the swing sits above 60 mV/dec.
        config = DsFetConfig()
        x = dict(BASE)
        x["filter_window_meV"] = 300.0
        x["filter_cutoff_meV"] = 200.0
        _, ss = interval_swings(x, config)
        assert ss.max() > 62.0
        assert np.count_nonzero(ss > 60.0) >= np.count_nonzero(ss < 60.0) // 2


class TestTradeoffPhysics:
    def test_degenerate_filling_trades_off_state_for_current(self):
        config = DsFetConfig()
        cold = evaluate_dsfet_candidate(BASE, config)
        hot = evaluate_dsfet_candidate({**BASE, "source_fermi_meV": 100.0}, config)
        assert cold.trusted and hot.trusted
        assert hot.ion > 10.0 * cold.ion
        assert hot.ioff > 10.0 * cold.ioff

    def test_short_channel_smearing_destroys_the_filter(self):
        config = DsFetConfig()
        tight = evaluate_dsfet_candidate(BASE, config)
        leaky = evaluate_dsfet_candidate({**BASE, "lambda_sc_nm": 25.0}, config)
        assert tight.trusted and leaky.trusted
        assert leaky.ss_window_mV_per_dec > SS_THERMAL
        assert tight.ss_window_mV_per_dec < SS_THERMAL
        _, ss_leaky = interval_swings({**BASE, "lambda_sc_nm": 25.0}, config)
        assert np.count_nonzero(ss_leaky < 60.0) == 0

    def test_supply_cutoff_reduces_on_current(self):
        config = DsFetConfig()
        open_filter = evaluate_dsfet_candidate(
            {**BASE, "filter_cutoff_meV": 320.0,
             "filter_window_meV": 380.0}, config,
        )
        tight_filter = evaluate_dsfet_candidate(BASE, config)
        assert open_filter.trusted and tight_filter.trusted
        assert open_filter.ion > tight_filter.ion


class TestCandidateEvaluation:
    def test_supply_filter_above_barrier_rejected(self):
        config = DsFetConfig()
        cand = evaluate_dsfet_candidate(
            {**BASE, "filter_cutoff_meV": 200.0,
             "filter_window_meV": 150.0}, config,
        )
        assert not cand.trusted
        assert any("off state" in v for v in cand.violations)

    def test_bounds_clipped(self):
        config = DsFetConfig()
        cand = evaluate_dsfet_candidate({
            "filter_window_meV": 1e5, "filter_cutoff_meV": -1e5,
            "source_fermi_meV": -1e5, "lambda_sc_nm": 1e5, "vdd": 100.0,
        }, config)
        assert cand.x["filter_window_meV"] <= config.filter_window_meV[1]
        assert cand.x["vdd"] <= config.vdd[1]


class TestEvolutionRun:
    def test_deterministic_run(self):
        a = evolve_dsfet_frontier(DsFetConfig(), 8, 3, seed=17)
        b = evolve_dsfet_frontier(DsFetConfig(), 8, 3, seed=17)
        for ra, rb in zip(a.to_rows(), b.to_rows()):
            assert ra["filter_window_meV"] == pytest.approx(
                rb["filter_window_meV"], rel=1e-12, abs=1e-18)
            assert ra["trusted"] == rb["trusted"]
            if ra["trusted"]:
                assert ra["ss_window_mV_per_dec"] == pytest.approx(
                    rb["ss_window_mV_per_dec"], rel=1e-12)

    def test_front_nondominated_and_exposes_tradeoff(self):
        seeds = [
            {**BASE},
            {**BASE, "filter_cutoff_meV": 70.0},
            {**BASE, "filter_window_meV": 300.0, "filter_cutoff_meV": 200.0},
            {**BASE, "source_fermi_meV": 150.0},
        ]
        result = evolve_dsfet_frontier(
            DsFetConfig(), 12, 6, seed=5, init_population=seeds,
        )
        assert result.front
        objectives = np.vstack([c.objectives for c in result.front])
        for i in range(len(objectives)):
            for j in range(len(objectives)):
                if i != j:
                    assert not _vec_dominates(objectives[j], objectives[i])
        ss = np.array([c.ss_window_mV_per_dec for c in result.front])
        ion = np.log10(np.array([c.ion for c in result.front]))
        if len(result.front) > 1:
            assert ion[int(np.argmin(ss))] < ion.max()

    def test_history_counts_every_evaluation(self):
        result = evolve_dsfet_frontier(DsFetConfig(), 8, 3, seed=1)
        assert len(result.history) == 8 * (3 + 1)
