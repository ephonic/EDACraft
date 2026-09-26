"""Verification suite for the E2 TFET steepness-current explorer (plan0918 E2)."""

import math

import numpy as np
import pytest

from tcad.search.fe_frontier import _vec_dominates
from tcad.search.tfet_frontier import (
    REF_A_KANE,
    REF_EG_EV,
    REF_ION_A_PER_UM,
    REF_LAMBDA_NM,
    REF_MT,
    TfetFrontierConfig,
    _anchor_scale,
    _current_at,
    _junction_field,
    evaluate_tfet_candidate,
    evolve_tfet_frontier,
    theta_kernel,
)


REFERENCE = {
    "eg_t": REF_EG_EV,
    "lambda_nm": REF_LAMBDA_NM,
    "mt_ratio": REF_MT,
    "a_kane": REF_A_KANE,
    "vfb_offset": 0.0,
}


class TestAnchor:
    def test_reference_design_reproduces_dd_replay_anchor(self):
        candidate = evaluate_tfet_candidate(REFERENCE)
        assert candidate.trusted, candidate.violations
        assert candidate.ion == pytest.approx(REF_ION_A_PER_UM, rel=1.0e-6)

    def test_anchor_scale_is_positive_and_finite(self):
        scale = _anchor_scale()
        assert np.isfinite(scale) and scale > 0.0


class TestCompactCurve:
    def test_current_is_monotone_in_gate_voltage(self):
        config = TfetFrontierConfig()
        scale = _anchor_scale()
        currents = [
            _current_at(vg, REFERENCE, config, scale)
            for vg in np.arange(0.0, 0.8, 0.05)
        ]
        assert all(b >= a for a, b in zip(currents, currents[1:]))

    def test_subthreshold_swing_matches_closed_form(self):
        config = TfetFrontierConfig()
        scale = _anchor_scale()
        x = dict(REFERENCE)
        x["eg_t"] = 0.9
        x["vfb_offset"] = 0.15
        vg_a, vg_b = 0.40, 0.42
        ia = _current_at(vg_a, x, config, scale)
        ib = _current_at(vg_b, x, config, scale)
        ss_numeric = 0.02 / (math.log10(ib) - math.log10(ia)) * 1000.0
        # Closed form: dlnG/dVg = (D/E + 2*Theta/E) * eta/lambda.
        e = _junction_field(0.41, x, config)
        slope = (config.d_exp / e + 2.0 * theta_kernel(e, x["mt_ratio"], x["eg_t"]) / e)
        slope *= config.eta / (x["lambda_nm"] * 1e-9)
        ss_closed = 1000.0 * math.log(10.0) / slope
        assert ss_numeric == pytest.approx(ss_closed, rel=2.0e-3)

    def test_smaller_gap_raises_both_ion_and_ioff(self):
        base = evaluate_tfet_candidate(dict(REFERENCE))
        narrow = evaluate_tfet_candidate({**REFERENCE, "eg_t": 0.55})
        assert narrow.trusted and base.trusted
        assert narrow.ion > 10.0 * base.ion
        assert narrow.ioff > base.ioff

    def test_steeper_electrostatics_raise_current_only(self):
        # In the compact model the swing at a given current is set by eta and
        # the local exponential slope: SS = ln10*V_eff/(eta*(D + 2*Theta(E)))
        # with E = V_eff/lambda, so the lambda prefactor cancels.  Tighter
        # electrostatics buy current (E ~ 1/lambda), not swing - a declared
        # v1 model statement, asserted against the closed form.
        base = evaluate_tfet_candidate(dict(REFERENCE))
        tight = evaluate_tfet_candidate({**REFERENCE, "lambda_nm": 3.2})
        assert tight.trusted and base.trusted
        assert tight.ion > 10.0 * base.ion
        config = TfetFrontierConfig()

        def ss_closed(x):
            e_on = _junction_field(config.vdd, x, config)
            v_eff = e_on * x["lambda_nm"] * 1e-9
            theta = theta_kernel(e_on, x["mt_ratio"], x["eg_t"])
            return 1000.0 * math.log(10.0) * v_eff / (
                config.eta * (config.d_exp + 2.0 * theta)
            )

        assert tight.ss_avg_mV_per_dec == pytest.approx(
            ss_closed(tight.x), rel=0.6,
        )
        assert base.ss_avg_mV_per_dec == pytest.approx(
            ss_closed(base.x), rel=0.6,
        )


class TestConstraintGate:
    def test_dead_device_is_rejected(self):
        # The junction field must stay positive at Vdd; a workfunction
        # placing the device beyond turn-on gives zero current everywhere.
        dead_config = TfetFrontierConfig(vfb_offset=(0.9, 1.0))
        candidate = evaluate_tfet_candidate(
            {**REFERENCE, "vfb_offset": 0.95}, dead_config,
        )
        assert not candidate.trusted
        assert candidate.violations

    def test_bounds_are_clipped(self):
        candidate = evaluate_tfet_candidate({
            "eg_t": 5.0, "lambda_nm": 100.0, "mt_ratio": 2.0,
            "a_kane": 1e25, "vfb_offset": 10.0,
        })
        assert candidate.x["eg_t"] <= 1.12416
        assert candidate.x["mt_ratio"] <= 0.30
        assert candidate.x["vfb_offset"] <= 0.30


class TestEvolutionRun:
    def test_deterministic_run(self):
        a = evolve_tfet_frontier(TfetFrontierConfig(), 8, 3, seed=21)
        b = evolve_tfet_frontier(TfetFrontierConfig(), 8, 3, seed=21)
        for ra, rb in zip(a.to_rows(), b.to_rows()):
            for key in ("eg_t", "lambda_nm", "mt_ratio", "ion_A_per_um"):
                assert ra[key] == pytest.approx(rb[key], rel=1e-12, abs=1e-18)

    def test_front_is_nondominated_and_exposes_the_tradeoff(self):
        seeds = [
            {**REFERENCE},
            {**REFERENCE, "eg_t": 0.5},
            {**REFERENCE, "eg_t": 0.7, "lambda_nm": 3.5},
            {**REFERENCE, "lambda_nm": 12.0, "eg_t": 0.85},
        ]
        result = evolve_tfet_frontier(
            TfetFrontierConfig(), 12, 6, seed=5, init_population=seeds,
        )
        assert result.front
        objectives = np.vstack([c.objectives for c in result.front])
        for i in range(len(objectives)):
            for j in range(len(objectives)):
                if i != j:
                    assert not _vec_dominates(objectives[j], objectives[i])
        ion = np.array([c.ion for c in result.front])
        ss = np.array([c.ss_avg_mV_per_dec for c in result.front])
        ratio = np.log10(np.array([
            c.ion / max(c.ioff, 1e-30) for c in result.front
        ]))
        assert ion.max() / ion.min() > 10.0
        assert ss.max() - ss.min() > 5.0
        # The robust in-model tradeoff (comment7 4.1): the stagger that buys
        # on-current also destroys the on/off ratio; the highest-current
        # member does not hold the best ratio.
        assert ratio[int(np.argmax(ion))] < ratio.max()

    def test_history_counts_every_evaluation(self):
        result = evolve_tfet_frontier(TfetFrontierConfig(), 8, 3, seed=1)
        assert len(result.history) == 8 * (3 + 1)
