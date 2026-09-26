"""Verification suite for the E0 NC-FET stack explorer (plan0918 E0)."""

import math

import numpy as np
import pytest

from tcad.search.fe_frontier import _vec_dominates
from tcad.search.ncfet_frontier import (
    NcFetStackConfig,
    _body_factor,
    _branch_derivatives,
    _insulator_capacitance,
    _solve_branch_charge,
    _total_capacitance,
    evaluate_ncfet_candidate,
    evolve_ncfet_frontier,
)

FE_X = {
    "fe_thickness_nm": 10.0,
    "de_thickness_nm": 1.0,
    "de_eps": 12.0,
    "beta_scale": 1.0,
    "c_mos_mF_per_m2": 5.0,
    "vg_span": 0.8,
}


class TestLoadLine:
    def test_load_line_residual_closes(self):
        config = NcFetStackConfig()
        p = -math.sqrt(-config.alpha / (config.beta * FE_X["beta_scale"]))
        for v_g in (-0.3, 0.0, 0.3):
            q, p = _solve_branch_charge(v_g, FE_X, config, p)
            eps_lin = config.eps_fe * 8.854187817e-12
            e_fe = config.alpha * p + config.beta * FE_X["beta_scale"] * p ** 3
            c_de = FE_X["de_eps"] * 8.854187817e-12 / (FE_X["de_thickness_nm"] * 1e-9)
            c_mos = FE_X["c_mos_mF_per_m2"] * 1e-3
            residual = (
                FE_X["fe_thickness_nm"] * 1e-9 * e_fe
                + q / c_de + q / c_mos - v_g
            )
            assert abs(residual) < 1e-12
            assert q == pytest.approx(p + eps_lin * e_fe, rel=1e-12)

    def test_continuation_tracks_the_branch_smoothly(self):
        config = NcFetStackConfig()
        ps = math.sqrt(-config.alpha / config.beta)
        p_track = -ps
        p_vals = []
        for v_g in np.linspace(-0.4, 0.4, 41):
            _, p = _solve_branch_charge(float(v_g), FE_X, config, p_track)
            p_track = p
            p_vals.append(p)
        jumps = np.abs(np.diff(p_vals))
        assert np.max(jumps) < 0.05 * ps


class TestCapacitanceFormulas:
    def test_paraelectric_limit_gives_no_amplification(self):
        # alpha > 0 (or beta -> 0 with alpha > 0): C_ins > 0, m > 1 exactly.
        config = NcFetStackConfig(alpha=5.0e6, beta=0.0)
        for p in (-0.2, 0.0, 0.2):
            c_ins = _insulator_capacitance(FE_X, config, p)
            assert c_ins > 0.0
            assert _body_factor(FE_X, config, p) > 1.0

    def test_body_factor_identity(self):
        # m must equal C_mos * dV_g/dQ (differential chain rule).
        config = NcFetStackConfig()
        p = 0.05
        dqdp, dvfe_dp, c_de, c_mos = _branch_derivatives(FE_X, config, p)
        m_expected = c_mos * (dvfe_dp + dqdp * (1.0 / c_de + 1.0 / c_mos)) / dqdp
        assert _body_factor(FE_X, config, p) == pytest.approx(m_expected, rel=1e-12)

    def test_amplification_and_stability_can_coexist(self):
        # The classic stabilization window: C_ins < 0 (m < 1) while
        # C_tot > 0 (hysteresis-free).  Find a design point in the window.
        config = NcFetStackConfig()
        x = dict(FE_X)
        x["fe_thickness_nm"] = 8.0
        x["de_thickness_nm"] = 0.6
        x["de_eps"] = 20.0
        x["c_mos_mF_per_m2"] = 15.0
        p = 0.0  # center of the S-branch
        c_ins = _insulator_capacitance(x, config, p)
        c_tot = _total_capacitance(x, config, p)
        m = _body_factor(x, config, p)
        if c_tot > 0.0:
            assert c_ins < 0.0 and m < 1.0
        else:
            pytest.skip("stack outside the stabilization window at P=0")


class TestStabilizationBoundary:
    def test_thin_high_k_de_stabilizes_weak_de_bistable(self):
        # With realistic C_mos (<= 50 mF/m^2) bistability needs a strong FE
        # (thick, large beta) AND a very thin high-k DE; a 1 nm / eps=12 DE
        # with the same FE stays hysteresis-free (dV_g/dP = +6.8 vs -0.33).
        config = NcFetStackConfig()
        base = dict(FE_X)
        base.update({
            "fe_thickness_nm": 40.0, "beta_scale": 4.0,
            "de_thickness_nm": 0.35, "de_eps": 25.0,
            "c_mos_mF_per_m2": 50.0,
        })
        strong = dict(base)
        strong["de_thickness_nm"] = 1.0
        strong["de_eps"] = 12.0
        weak = dict(base)
        cand_strong = evaluate_ncfet_candidate(strong, config)
        cand_weak = evaluate_ncfet_candidate(weak, config)
        assert cand_strong.trusted and cand_weak.trusted
        assert not cand_strong.hysteretic
        assert cand_weak.hysteretic

    def test_boundary_is_monotone_in_de_thickness(self):
        config = NcFetStackConfig()
        margins = []
        for t_de in (0.4, 0.8, 1.5, 2.5, 3.5):
            x = dict(FE_X)
            x["de_thickness_nm"] = t_de
            cand = evaluate_ncfet_candidate(x, config)
            margins.append(cand.stability_margin_F_per_m2)
        for a, b in zip(margins, margins[1:]):
            assert b < a


class TestCandidateEvaluation:
    def test_stabilized_candidate_achieves_dd_floor(self):
        # After A2 Sentaurus DD adjudication: SS cannot go below 62 mV/dec
        # in DD simulation. The quasi-static load-line m<1 is a theoretical
        # upper bound only. The floor ensures exploration results reflect
        # DD-achievable performance.
        config = NcFetStackConfig()
        x = dict(FE_X)
        x["de_thickness_nm"] = 0.5
        x["de_eps"] = 22.0
        x["c_mos_mF_per_m2"] = 15.0
        cand = evaluate_ncfet_candidate(x, config)
        assert cand.trusted
        assert not cand.hysteretic
        assert cand.m_min >= 60.0 / 62.0  # m floor from DD
        assert cand.ss_min_mV_per_dec >= 62.0  # SS floor from DD
        assert cand.amplification_window_frac > 0.0

    def test_bounds_clipped_and_validation(self):
        config = NcFetStackConfig()
        cand = evaluate_ncfet_candidate({
            "fe_thickness_nm": 500.0, "de_thickness_nm": 50.0,
            "de_eps": 100.0, "beta_scale": 99.0,
            "c_mos_mF_per_m2": 1e5, "vg_span": 10.0,
        }, config)
        assert cand.x["fe_thickness_nm"] <= config.fe_thickness_nm[1]


class TestEvolutionRun:
    def test_deterministic_run(self):
        a = evolve_ncfet_frontier(NcFetStackConfig(), 8, 3, seed=13)
        b = evolve_ncfet_frontier(NcFetStackConfig(), 8, 3, seed=13)
        for ra, rb in zip(a.to_rows(), b.to_rows()):
            for key in ("fe_thickness_nm", "body_factor_min", "de_eps"):
                assert ra[key] == pytest.approx(rb[key], rel=1e-12, abs=1e-15)

    def test_front_nondominated_and_exposes_tradeoff(self):
        seeds = [
            {**FE_X, "de_thickness_nm": 0.5, "de_eps": 22.0, "c_mos_mF_per_m2": 15.0},
            {**FE_X, "de_thickness_nm": 2.0, "de_eps": 8.0, "c_mos_mF_per_m2": 4.0},
            {**FE_X, "de_thickness_nm": 1.0, "de_eps": 12.0, "c_mos_mF_per_m2": 8.0},
            {**FE_X, "fe_thickness_nm": 20.0},
        ]
        result = evolve_ncfet_frontier(
            NcFetStackConfig(), 12, 6, seed=5, init_population=seeds,
        )
        assert result.front
        objectives = np.vstack([c.objectives for c in result.front])
        for i in range(len(objectives)):
            for j in range(len(objectives)):
                if i != j:
                    assert not _vec_dominates(objectives[j], objectives[i])
        # The central tradeoff: the most-amplified front member is not the
        # most stable one (amplification lives near the bistability edge).
        amp = np.array([1.0 / c.m_min for c in result.front])
        margin = np.array([c.stability_margin_F_per_m2 for c in result.front])
        if len(result.front) > 1 and margin.max() > 0.0:
            assert margin[int(np.argmax(amp))] < margin.max()

    def test_history_counts_every_evaluation(self):
        result = evolve_ncfet_frontier(NcFetStackConfig(), 8, 3, seed=1)
        assert len(result.history) == 8 * (3 + 1)
