"""C3 search-engine truth-chain (plan0619.md §C3).

Two layers:

1. **Fast unit tests** (no solver) — NSGA-II mechanics: non-dominated sort,
   crowding distance, tournament selection, the performance scalar, the
   novelty metric, the surrogate (kNN + LCB), and the candidate feature vector.
   These run in milliseconds and pin down the algorithmic correctness of the
   search engine independently of the physics.

2. **Slow integration tests** (solver-backed, gated on ``TCAD_RUN_SLOW=1``) —
   the actual discovery truth-chain:
     * Known-space: a parameter-only MOSFET search (``allow_mechanism_mutation=
       False``) stays inside the seed template's kind set (``nontrivial_found``
       is False) and produces at least one trusted candidate.
     * Open-space: the same seed with ``allow_mechanism_mutation=True`` can
       produce a non-trivial candidate whose kind set differs from the seed
       (topology outside the 14 templates — e.g. an inserted FE layer).
   These are slow (~minutes) because each candidate runs a full Vg sweep; they
   are skipped unless the caller opts in via the env var.
"""

import os
import random

import numpy as np
import pytest

from tcad.search.grammar import (
    tree_from_template, template_default_params,
    KIND_OXIDE, KIND_FERROELECTRIC, KIND_METAL,
)
from tcad.search.evolution import (
    Candidate, EvolutionResult, Surrogate,
    compute_perf, compute_novelty, evaluate_candidate,
    non_dominated_sort, crowding_distance, tournament_select,
    _dominates, evolve,
)


RUN_SLOW = os.environ.get("TCAD_RUN_SLOW", "") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set TCAD_RUN_SLOW=1 to run solver-backed tests")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cand(perf, novelty=0.0, trust=True, tree=None):
    """Build a Candidate with given objective values (no solver needed)."""
    if tree is None:
        tree = tree_from_template("mosfet")
    c = Candidate(tree=tree, template_name="mosfet")
    c.perf = perf
    c.novelty = novelty
    c.trust = trust
    c.evaluated = True
    return c


# ===========================================================================
# 1. Performance scalar
# ===========================================================================

class TestComputePerf:
    def test_good_metrics_finite_positive(self):
        m = {"Ion": 1e-5, "Ioff": 1e-11, "SS": 70.0, "Vth": 0.3, "DIBL": 50.0,
             "Ion_Ioff": 1e6}
        p = compute_perf(m)
        assert np.isfinite(p) and p > 0

    def test_higher_ion_ioff_is_better(self):
        base = {"Ion": 1e-5, "Ioff": 1e-11, "SS": 70.0, "Vth": 0.3, "DIBL": 0.0,
                "Ion_Ioff": 1e6}
        better = dict(base, Ioff=1e-13, Ion_Ioff=1e8)
        assert compute_perf(better) > compute_perf(base)

    def test_lower_ss_is_better(self):
        base = {"Ion": 1e-5, "Ioff": 1e-11, "SS": 120.0, "Vth": 0.3, "DIBL": 0.0,
                "Ion_Ioff": 1e6}
        better = dict(base, SS=60.0)
        assert compute_perf(better) > compute_perf(base)

    def test_nan_metrics_is_neg_inf(self):
        m = {"Ion": float("nan"), "Ioff": 1e-11, "SS": 70.0, "Vth": 0.3,
             "DIBL": 0.0, "Ion_Ioff": 1e6}
        assert compute_perf(m) == float("-inf")

    def test_none_metrics_is_neg_inf(self):
        assert compute_perf(None) == float("-inf")

    def test_zero_current_is_neg_inf(self):
        m = {"Ion": 0.0, "Ioff": 0.0, "SS": 70.0, "Vth": 0.3, "DIBL": 0.0,
             "Ion_Ioff": 1.0}
        assert compute_perf(m) == float("-inf")

    def test_ion_ioff_capped(self):
        """A 1e12 ratio should not beat a 1e8 ratio by much (capped at 1e8)."""
        m1 = {"Ion": 1e-3, "Ioff": 1e-11, "SS": 70.0, "Vth": 0.3, "DIBL": 0.0,
              "Ion_Ioff": 1e8}
        m2 = {"Ion": 1e-3, "Ioff": 1e-15, "SS": 70.0, "Vth": 0.3, "DIBL": 0.0,
              "Ion_Ioff": 1e12}
        assert abs(compute_perf(m1) - compute_perf(m2)) < 0.5  # capped


# ===========================================================================
# 2. NSGA-II dominance + non-dominated sort
# ===========================================================================

class TestNonDominatedSort:
    def test_single_pareto_front(self):
        # All mutually non-dominating (perf up, novelty down).
        pop = [_cand(1.0, 5.0), _cand(2.0, 4.0), _cand(3.0, 3.0)]
        fronts = non_dominated_sort(pop)
        assert len(fronts) == 1
        assert set(fronts[0]) == {0, 1, 2}

    def test_two_fronts(self):
        # a dominates b (better on both); c is non-dominated by a.
        a = _cand(3.0, 3.0)
        b = _cand(1.0, 1.0)  # dominated by a
        c = _cand(2.0, 5.0)  # not dominated by a (higher novelty)
        pop = [a, b, c]
        fronts = non_dominated_sort(pop)
        assert len(fronts) == 2
        assert set(fronts[0]) == {0, 2}  # a, c on front 0
        assert set(fronts[1]) == {1}     # b on front 1

    def test_untrusted_is_dominated(self):
        # Untrusted has perf=-inf.  A trusted candidate better on *both*
        # objectives dominates it; here trusted has higher perf AND higher
        # novelty, so untrusted lands on front 1.
        trusted = _cand(2.0, 5.0, trust=True)
        untrusted = _cand(float("-inf"), 2.0, trust=False)
        pop = [trusted, untrusted]
        fronts = non_dominated_sort(pop)
        assert 0 in fronts[0]
        assert 1 in fronts[1]

    def test_untrusted_non_dominating_when_novel(self):
        # Untrusted (perf=-inf, high novelty) is NOT dominated by a trusted
        # candidate that is better on perf but worse on novelty: they share
        # front 0.  This is the intended NSGA-II behaviour — novelty keeps
        # untrusted-but-structurally-diverse candidates visible.
        trusted = _cand(2.0, 2.0, trust=True)
        untrusted = _cand(float("-inf"), 5.0, trust=False)
        pop = [trusted, untrusted]
        fronts = non_dominated_sort(pop)
        assert len(fronts) == 1
        assert set(fronts[0]) == {0, 1}

    def test_all_indices_covered(self):
        pop = [_cand(random.random(), random.random()) for _ in range(10)]
        fronts = non_dominated_sort(pop)
        flat = [i for f in fronts for i in f]
        assert sorted(flat) == list(range(10))

    def test_empty_population(self):
        assert non_dominated_sort([]) == []


class TestDominates:
    def test_strict_dominance(self):
        a = _cand(3.0, 3.0)
        b = _cand(1.0, 1.0)
        assert _dominates(a, b)
        assert not _dominates(b, a)

    def test_non_dominating(self):
        a = _cand(3.0, 1.0)
        b = _cand(1.0, 3.0)
        assert not _dominates(a, b)
        assert not _dominates(b, a)

    def test_equal_is_not_dominance(self):
        a = _cand(2.0, 2.0)
        b = _cand(2.0, 2.0)
        assert not _dominates(a, b)


# ===========================================================================
# 3. Crowding distance + tournament selection
# ===========================================================================

class TestCrowdingDistance:
    def test_extremes_are_infinite(self):
        front = [_cand(1.0, 1.0), _cand(2.0, 2.0), _cand(3.0, 3.0)]
        cd = crowding_distance(front)
        assert cd[0] == float("inf")
        assert cd[-1] == float("inf")

    def test_single_or_pair_all_infinite(self):
        assert crowding_distance([_cand(1.0, 1.0)]) == [float("inf")]
        assert crowding_distance([_cand(1.0, 1.0), _cand(2.0, 2.0)]) == [float("inf"), float("inf")]

    def test_middle_has_finite(self):
        front = [_cand(1.0, 1.0), _cand(2.0, 2.0), _cand(3.0, 3.0)]
        cd = crowding_distance(front)
        assert cd[1] != float("inf")
        assert cd[1] >= 0.0


class TestTournamentSelect:
    def test_dominant_wins(self):
        a = _cand(5.0, 5.0)
        b = _cand(1.0, 1.0)
        rng = random.Random(0)
        # Force selection of indices 0 and 1.
        chosen = []
        for _ in range(20):
            c = tournament_select([a, b], rng)
            chosen.append(c)
        # a dominates b, so a should always win when paired.
        assert all(c is a for c in chosen) or chosen.count(a) > chosen.count(b)

    def test_returns_member_of_population(self):
        pop = [_cand(random.random(), random.random()) for _ in range(5)]
        rng = random.Random(1)
        c = tournament_select(pop, rng)
        assert c in pop


# ===========================================================================
# 4. Novelty (structural distance to archive)
# ===========================================================================

class TestComputeNovelty:
    def test_empty_archive_is_zero(self):
        c = _cand(1.0, 0.0)
        assert compute_novelty(c, []) == 0.0

    def test_identical_tree_is_zero_novelty(self):
        tree = tree_from_template("mosfet")
        seed = _cand(1.0, 0.0, tree=tree)
        child = _cand(2.0, 0.0, tree=tree_from_template("mosfet"))
        # Same kind set + wrap -> feature vectors identical -> novelty 0.
        n = compute_novelty(child, [seed])
        assert n == pytest.approx(0.0, abs=1e-9)

    def test_different_topology_is_novel(self):
        seed = _cand(1.0, 0.0, tree=tree_from_template("mosfet"))
        # A GAA has a different kind set (BOX, etc.) -> nonzero distance.
        other = _cand(2.0, 0.0, tree=tree_from_template("gaa"))
        n = compute_novelty(other, [seed])
        assert n > 0.0

    def test_k_nearest_average(self):
        seed = _cand(1.0, 0.0, tree=tree_from_template("mosfet"))
        arch = [
            _cand(1.0, 0.0, tree=tree_from_template("mosfet")),
            _cand(1.0, 0.0, tree=tree_from_template("gaa")),
            _cand(1.0, 0.0, tree=tree_from_template("tfet")),
        ]
        c = _cand(2.0, 0.0, tree=tree_from_template("mosfet"))
        n = compute_novelty(c, arch, k=2)
        assert n >= 0.0


# ===========================================================================
# 5. Candidate feature vector
# ===========================================================================

class TestFeatureVector:
    def test_mosfet_feature_vector_shape(self):
        c = _cand(1.0, 0.0, tree=tree_from_template("mosfet"))
        fv = c.feature_vector()
        # 15 bag-of-kinds + 3 wrap one-hot + 4 mechanism-fraction = 22.
        assert fv.shape == (22,)

    def test_feature_vector_deterministic(self):
        tree = tree_from_template("mosfet")
        c = _cand(1.0, 0.0, tree=tree)
        assert np.allclose(c.feature_vector(), c.feature_vector())

    def test_different_topology_different_vector(self):
        a = _cand(1.0, 0.0, tree=tree_from_template("mosfet"))
        b = _cand(1.0, 0.0, tree=tree_from_template("gaa"))
        assert not np.allclose(a.feature_vector(), b.feature_vector())


# ===========================================================================
# 6. Surrogate (kNN + LCB)
# ===========================================================================

class TestSurrogate:
    def test_empty_predict_returns_default(self):
        s = Surrogate(k=3)
        c = _cand(1.0, 0.0)
        mean, std = s.predict(c)
        assert mean == 0.0
        assert std == 1.0

    def test_fit_uses_trusted_only(self):
        s = Surrogate(k=1)
        trusted = _cand(5.0, 0.0, trust=True)
        untrusted = _cand(1.0, 0.0, trust=False)
        s.fit([trusted, untrusted])
        assert len(s.X) == 1
        assert s.y == [5.0]

    def test_predict_returns_neighbour_mean(self):
        s = Surrogate(k=1)
        tree = tree_from_template("mosfet")
        c = _cand(5.0, 0.0, trust=True, tree=tree)
        s.fit([c])
        query = _cand(0.0, 0.0, tree=tree)  # identical feature vector
        mean, std = s.predict(query)
        assert mean == pytest.approx(5.0)

    def test_lcb_below_mean(self):
        s = Surrogate(k=3)
        tree = tree_from_template("mosfet")
        s.fit([_cand(5.0, 0.0, trust=True, tree=tree),
               _cand(3.0, 0.0, trust=True, tree=tree)])
        query = _cand(0.0, 0.0, tree=tree)
        mean, std = s.predict(query)
        assert s.lcb(query, kappa=1.0) == pytest.approx(mean - std)


# ===========================================================================
# 7. evaluate_candidate (single seed, no search) — fast-ish sanity
# ===========================================================================

class TestEvaluateCandidate:
    def test_seed_mosfet_evaluates(self):
        """A plain MOSFET seed produces a finite metrics dict (trusted or not).

        This pins the wiring: build -> sweep -> assess -> stamp.  It does not
        assert trust (that depends on resolution/mesh and is covered by the
        slow integration tests).
        """
        tree = tree_from_template("mosfet", W=40e-9, Lg=50e-9)
        cand = Candidate(tree=tree, template_name="mosfet",
                         params=template_default_params("mosfet"))
        evaluate_candidate(cand,
                           gate_voltages=np.linspace(0.0, 0.4, 6), vd=0.1,
                           resolution=(10e-9, 5e-9, 10e-9),
                           max_iter=50, tol=1e-7, verbose=False)
        assert cand.evaluated is True
        assert cand.metrics is not None
        assert "Ion" in cand.metrics and "SS" in cand.metrics

    def test_failed_build_marks_untrusted(self):
        """A tree whose build raises is marked untrusted, not crash."""
        # Construct a candidate with a deliberately bad tree (empty regions).
        from tcad.search.grammar import DeviceTree, GateStackMeta
        empty = DeviceTree(name="empty", region_nodes=(), contacts=(),
                           gate_meta=None)
        cand = Candidate(tree=empty, template_name="mosfet", params={})
        evaluate_candidate(cand,
                           gate_voltages=np.linspace(0.0, 0.4, 4), vd=0.1,
                           resolution=(15e-9, 15e-9, 15e-9),
                           max_iter=30, tol=1e-7, verbose=False)
        assert cand.trust is False
        assert cand.perf == float("-inf")


# ===========================================================================
# 8. Slow integration: the discovery truth-chain (solver-backed)
# ===========================================================================

@slow
class TestEvolutionTruthChain:
    """The C3 truth-chain (plan0619.md §C3 line 105).

    Known-space: a parameter-only MOSFET search converges inside the seed
    template's kind set (nontrivial_found is False) and yields trusted
    candidates.  Open-space: enabling mechanism mutation can produce a
    non-trivial candidate (topology outside the seed, e.g. an inserted FE
    layer).
    """

    _EVAL_KW = dict(
        gate_voltages=np.linspace(0.0, 0.4, 6),
        vd=0.1,
        resolution=(10e-9, 5e-9, 10e-9),
        max_iter=50,
        tol=1e-7,
    )

    def test_known_space_stays_in_template(self):
        res = evolve(
            seed_template="mosfet",
            seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=False,
            rng=random.Random(0), verbose=False,
            **self._EVAL_KW,
        )
        assert isinstance(res, EvolutionResult)
        assert len(res.archive) >= 4
        # Known-space (parameter-only) must not leave the seed topology.
        assert res.nontrivial_found is False
        # At least one trusted candidate should survive.
        trusted = [c for c in res.archive if c.trust]
        assert len(trusted) >= 1

    def test_open_space_can_find_nontrivial(self):
        """Open-space search may produce a topology outside the seed.

        We seed from a plain MOSFET and allow mechanism mutation.  Because the
        FE-insertion operator is one of the eligible mutations, the archive
        should contain at least one candidate whose kind set differs from the
        seed (contains KIND_FERROELECTRIC).  We assert this directly over the
        archive rather than via ``nontrivial_found`` (which requires the
        non-trivial candidate to also be trusted — a stricter bar that depends
        on the FE slab converging at this mesh).
        """
        res = evolve(
            seed_template="mosfet",
            seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=True,
            rng=random.Random(7), verbose=False,
            **self._EVAL_KW,
        )
        seed_kinds = frozenset(
            rn.kind for rn in tree_from_template("mosfet").region_nodes)
        # At least one archive member has a different kind set than the seed.
        nontrivial = [c for c in res.archive
                      if frozenset(rn.kind for rn in c.tree.region_nodes)
                      != seed_kinds]
        assert len(nontrivial) >= 1, (
            "open-space search produced no topology outside the seed template")
        # And at least one such non-trivial candidate inserted an FE layer.
        has_fe = any(KIND_FERROELECTRIC in
                     {rn.kind for rn in c.tree.region_nodes}
                     for c in nontrivial)
        assert has_fe, "no candidate carries an inserted ferroelectric layer"

    def test_known_space_best_perf_does_not_degrade(self):
        """The seed's perf should be a lower bound on the final best trusted perf.

        Parameter mutation explores the seed's own design space, so the search
        should not lose the seed's quality (NSGA-II elitism keeps it).  This is
        the 'known-space converges toward the optimum' half of the truth-chain.
        """
        res = evolve(
            seed_template="mosfet",
            seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=False,
            rng=random.Random(0), verbose=False,
            **self._EVAL_KW,
        )
        seed = res.archive[0]  # seed is evaluated first -> archive[0]
        trusted = [c for c in res.archive if c.trust]
        if trusted and seed.trust:
            best = max(c.perf for c in trusted)
            assert best >= seed.perf - 1e-9
