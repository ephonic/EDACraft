"""Verification suite for frontier-member mechanism attribution (plan0918 governance)."""

import numpy as np
import pytest

from tcad.search.attribution import attach_attributions, sensitivity_attribution
from tcad.search.ncfet_frontier import NcFetStackConfig, evolve_ncfet_frontier


CONFIG = NcFetStackConfig()
DESIGN = {
    "fe_thickness_nm": 20.0,
    "de_thickness_nm": 0.6,
    "de_eps": 20.0,
    "beta_scale": 2.0,
    "c_mos_mF_per_m2": 20.0,
    "vg_span": 0.8,
}


def _evaluate(x):
    from tcad.search.ncfet_frontier import evaluate_ncfet_candidate
    return evaluate_ncfet_candidate(x, CONFIG)


class TestSensitivityAttribution:
    def test_contributions_normalized_and_complete(self):
        att = sensitivity_attribution(_evaluate, DESIGN, CONFIG.bounds())
        assert set(att.contributions) == set(CONFIG.bounds())
        assert sum(att.contributions.values()) == pytest.approx(1.0, abs=1e-12)
        assert all(v >= 0.0 for v in att.contributions.values())
        assert att.dominant in att.contributions

    def test_dominant_knob_identified(self):
        # For a strong-FE design near the stabilization edge the attribution
        # truthfully ranks the capacitance-matching knobs (FE thickness, DE
        # thickness, C_mos) as the dominant mechanism; a beta nudge past the
        # bistability cliff makes the perturbed candidate untrusted and
        # contributes zero by policy (the cliff is a violation, not a slope).
        att = sensitivity_attribution(_evaluate, DESIGN, CONFIG.bounds())
        matching = (
            att.contributions["fe_thickness_nm"]
            + att.contributions["de_thickness_nm"]
            + att.contributions["c_mos_mF_per_m2"]
        )
        assert matching >= 0.8
        assert att.dominant in (
            "fe_thickness_nm", "de_thickness_nm", "c_mos_mF_per_m2",
        )

    def test_clamped_perturbation_contributes_zero(self):
        # A variable already at its upper bound cannot move: zero effect.
        design = dict(DESIGN)
        design["c_mos_mF_per_m2"] = CONFIG.c_mos_mF_per_m2[1]
        att = sensitivity_attribution(_evaluate, design, CONFIG.bounds())
        assert att.contributions["c_mos_mF_per_m2"] == 0.0

    def test_deterministic(self):
        a = sensitivity_attribution(_evaluate, DESIGN, CONFIG.bounds())
        b = sensitivity_attribution(_evaluate, DESIGN, CONFIG.bounds())
        assert a.contributions == b.contributions
        assert a.dominant == b.dominant

    def test_limitation_string_carried(self):
        att = sensitivity_attribution(
            _evaluate, DESIGN, CONFIG.bounds(),
            model_class_limitation="quasi-static only",
        )
        assert att.model_class_limitation == "quasi-static only"
        assert "quasi-static only" in att.as_dict()["model_class_limitation"]

    def test_delta_fraction_validation(self):
        with pytest.raises(ValueError):
            sensitivity_attribution(_evaluate, DESIGN, CONFIG.bounds(), delta_frac=1.5)


class TestFrontierIntegration:
    def test_every_front_member_carries_attribution(self):
        result = evolve_ncfet_frontier(CONFIG, 10, 3, seed=9)
        assert result.front
        for cand in result.front:
            att = getattr(cand, "attribution", None)
            assert att is not None, "front member without attribution"
            assert sum(att.contributions.values()) == pytest.approx(1.0, abs=1e-9)
            assert att.dominant
            assert att.model_class_limitation
        rows = result.front_rows()
        for row in rows:
            assert "attribution_dominant" in row
            assert "model_class_limitation" in row
            assert row["attribution_dominant"]
