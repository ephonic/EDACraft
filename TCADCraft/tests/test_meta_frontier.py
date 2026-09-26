"""Unified multi-family meta-exploration verification."""
import numpy as np
import pytest

from tcad.search.fe_frontier import _vec_dominates
from tcad.search.meta_frontier import (
    FAMILIES,
    MetaCandidate,
    _evaluate_family,
    evolve_meta_frontier,
)

FAMILY_PARAMS = {
    "ncfet": {"fe_thickness_nm": 20.0, "de_thickness_nm": 0.6,
               "de_eps": 20.0, "beta_scale": 2.0, "c_mos_mF_per_m2": 20.0,
               "vg_span": 0.8},
    "tfet": {"eg_t": 0.9, "lambda_nm": 4.7, "mt_ratio": 0.08,
             "a_kane": 3.5e21, "vfb_offset": 0.0, "vdd": 0.5},
    "cold_source": {"filter_window_meV": 150.0, "filter_cutoff_meV": 100.0,
                    "source_fermi_meV": -25.0, "lambda_sc_nm": 3.0, "vdd": 0.5},
    "fefet": {"t_fe_nm": 20.0, "ps": 0.3, "ec": 2e8,
              "overdrive": 1.6, "tau0": 1e-9, "merz_exponent": 1.0},
    "ftj": {"t_fe_nm": 4.0, "ps": 0.3, "eg0_eV": 1.0,
            "delta_eV": 0.3, "mt_ratio": 0.15, "a_kane": 1e20},
}


class TestFamilyEvaluation:
    def test_all_families_produce_valid_candidates(self):
        for family in FAMILIES:
            x = FAMILY_PARAMS[family]
            cand = _evaluate_family(family, dict(x))
            assert cand.trusted, f"{family}: {cand.violations}"
            assert np.isfinite(cand.ss_mV_dec)
            assert np.isfinite(cand.log_ion)
            assert np.isfinite(cand.stability)

    def test_ncfet_ss_floored_at_dd_limit(self):
        """A2 adjudication: SS cannot go below DD limit."""
        x = FAMILY_PARAMS["ncfet"]
        cand = _evaluate_family("ncfet", dict(x))
        assert cand.ss_mV_dec >= 62.0, (
            f"NC-FET SS {cand.ss_mV_dec:.1f} below DD floor 62"
        )

    def test_objectives_shape(self):
        for family in FAMILIES:
            cand = _evaluate_family(family, dict(FAMILY_PARAMS[family]))
            assert cand.objectives.shape == (3,)


class TestMetaEvolution:
    def test_front_produces_multi_family(self):
        result = evolve_meta_frontier(20, 8, seed=20260920)
        front = result["front"]
        assert len(front) >= 3
        families = {c.family for c in front}
        assert len(families) >= 2, (
            f"front should contain multiple families, got {families}"
        )

    def test_front_is_nondominated(self):
        result = evolve_meta_frontier(15, 5, seed=42)
        front = result["front"]
        if len(front) > 1:
            objectives = np.vstack([c.objectives for c in front])
            for i in range(len(objectives)):
                for j in range(len(objectives)):
                    if i != j:
                        assert not _vec_dominates(objectives[j], objectives[i])

    def test_family_distribution_reported(self):
        result = evolve_meta_frontier(15, 5, seed=7)
        dist = result["family_distribution"]
        assert isinstance(dist, dict)
        assert sum(dist.values()) == len(result["front"])

    def test_deterministic(self):
        a = evolve_meta_frontier(10, 3, seed=99)
        b = evolve_meta_frontier(10, 3, seed=99)
        fa = [(c.family, sorted(c.x.items())) for c in a["population"]]
        fb = [(c.family, sorted(c.x.items())) for c in b["population"]]
        assert len(fa) == len(fb)

    def test_attribution_present(self):
        result = evolve_meta_frontier(10, 3, seed=13)
        for c in result["front"]:
            assert c.attribution is not None
            assert c.attribution.dominant
