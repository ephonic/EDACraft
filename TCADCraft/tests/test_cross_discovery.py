"""Verification suite for cross-tier discovery (grammar topologies x mechanisms)."""

import numpy as np
import pytest

from tcad.search.cross_discovery import (
    CrossDiscoveryConfig,
    classify_tree,
    run_cross_discovery,
    structural_signature,
    _tree_fe_thickness_nm,
)
from tcad.search.grammar import tree_from_template


class TestClassification:
    def test_baseline_templates_classified(self):
        assert classify_tree(tree_from_template("mosfet")) == "baseline"
        assert classify_tree(tree_from_template("gaa")) == "baseline"

    def test_tunnel_templates_classified(self):
        assert classify_tree(tree_from_template("tfet")) in ("baseline", "tunnel")
        assert classify_tree(tree_from_template("graphene_source_tfet")) == "tunnel"

    def test_fe_template_classified(self):
        assert classify_tree(tree_from_template("gaa_fefet")) == "fe"

    def test_fe_thickness_extracted(self):
        tree = tree_from_template("gaa_fefet", t_fe=8e-9)
        assert _tree_fe_thickness_nm(tree) == pytest.approx(8.0, rel=1e-6)

    def test_signatures_discriminate(self):
        sig_mos = structural_signature(tree_from_template("mosfet"))
        sig_gaa = structural_signature(tree_from_template("gaa"))
        assert sig_mos != sig_gaa


class TestTruthChain:
    def test_no_mechanism_mutation_no_fe_discovery(self):
        config = CrossDiscoveryConfig(
            population_size=8, generations=2, seed=3,
            insert_fe_probability=0.0,
        )
        result = run_cross_discovery(["mosfet", "gaa"], config)
        assert result["stats"]["insert_fe_origins"] == 0
        assert result["stats"]["fe_candidates"] == 0

    def test_mechanism_mutation_discovers_fe_topologies(self):
        # Open-space truth chain: baseline seeds + insert-FE operator must
        # produce FE-bearing topologies that did not exist in any template
        # the search started from.
        config = CrossDiscoveryConfig(
            population_size=12, generations=4, seed=20260918,
            insert_fe_probability=0.5,
        )
        result = run_cross_discovery(["mosfet", "gaa"], config)
        assert result["stats"]["insert_fe_origins"] > 0
        assert result["stats"]["fe_candidates"] > 0
        assert result["stats"]["distinct_signatures"] >= 3

    def test_discovered_fe_front_carries_attribution(self):
        config = CrossDiscoveryConfig(
            population_size=12, generations=3, seed=7,
            insert_fe_probability=0.5,
        )
        result = run_cross_discovery(["mosfet", "gaa"], config)
        for cand in result["fronts"]["fe"]:
            att = getattr(cand, "attribution", None)
            assert att is not None
            assert att.dominant
            assert "cross-tier" in att.model_class_limitation

    def test_deterministic_run(self):
        kwargs = dict(seed=11, population_size=8, generations=2)
        a = run_cross_discovery(["mosfet"], CrossDiscoveryConfig(**kwargs))
        b = run_cross_discovery(["mosfet"], CrossDiscoveryConfig(**kwargs))
        assert a["stats"] == b["stats"]
        assert a["archive"] == b["archive"]


class TestLawGate:
    def test_every_evaluated_candidate_passes_laws(self):
        # The loop skips violators; surviving history must be violation-free.
        config = CrossDiscoveryConfig(
            population_size=10, generations=3, seed=5,
            insert_fe_probability=0.4,
        )
        result = run_cross_discovery(["mosfet", "gaa"], config)
        for row in result["history"]:
            if row.get("origin", "").startswith("mutate"):
                assert row["law_violations"] == ""
                assert row["valid"] == 1.0
