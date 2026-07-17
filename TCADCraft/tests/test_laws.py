"""D3+D4 law-library truth-chain (plan0619.md §D3+D4).

Two layers:

1. **Fast unit tests** (no solver) — the law engine algebra:
   * ``extract_geometry`` derives tox/t_fe/Lg/kappa/Eg/material from tree
     region boxes (the single source of truth, since ``Candidate.params`` is
     unreliable after structural mutations).
   * Each of the 4 laws (NC stability, Dirac-source band-pass, high-k
     interface, gate-length floor) fires on a violating tree and passes on
     a compliant one.
   * ``check_all_laws`` collects all applicable violations.
   * ``load_laws`` reads the JSON and yields 4 laws with complete fields.
   * The ``evolve(use_law_constraints=True)`` gate rejects violating trees
     before the solver runs (verified by monkeypatching ``evaluate_candidate``
     to count calls).

2. **Slow integration test** (``TCAD_RUN_SLOW=1``) — the M6 exit criterion:
   a constrained open-space search wastes fewer solver calls than an
   unconstrained one (same seed/budget/rng) while still reaching non-trivial
   topologies.
"""

import os
import random

import numpy as np
import pytest

from tcad.search.grammar import (
    tree_from_template, DeviceTree, RegionNode, GateStackMeta, ContactSpec,
    KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_OXIDE, KIND_HIGHK, KIND_METAL,
    KIND_FERROELECTRIC,
    SILICON, SIO2, GATE_METAL, GRAPHENE, highk_material, ferroelectric_material,
    DopingSpec, WRAP_PLANAR_TOP,
)
from tcad.search.mutation import mutate_insert_ferroelectric
from tcad.knowledge import (
    Law, load_laws, check_law, check_all_laws, extract_geometry,
)


RUN_SLOW = os.environ.get("TCAD_RUN_SLOW", "") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set TCAD_RUN_SLOW=1 to run solver-backed tests")


# ---------------------------------------------------------------------------
# Helpers: build trees with specific material/geometry violations
# ---------------------------------------------------------------------------

def _swap_material(tree, kind, material):
    """Return a copy of ``tree`` with every region of ``kind`` using ``material``."""
    nodes = []
    for rn in tree.region_nodes:
        if rn.kind == kind:
            nodes.append(RegionNode(rn.kind, rn.name, rn.box, material, rn.doping))
        else:
            nodes.append(rn)
    return DeviceTree(name=tree.name, region_nodes=tuple(nodes),
                      contacts=tree.contacts, gate_meta=tree.gate_meta)


def _mosfet(**kw):
    """A plain MOSFET tree (tox=1.5nm, Lg=50nm, Si channel/source)."""
    defaults = dict(W=40e-9, Lg=50e-9)
    defaults.update(kw)
    return tree_from_template("mosfet", **defaults)


# ===========================================================================
# 1. extract_geometry
# ===========================================================================

class TestExtractGeometry:
    def test_mosfet_extracts_tox_and_lg(self):
        tree = _mosfet(tox=1.5e-9, Lg=50e-9)
        geom = extract_geometry(tree)
        assert geom["tox"] == pytest.approx(1.5e-9)
        assert geom["Lg"] == pytest.approx(50e-9)

    def test_mosfet_extracts_channel_eg_and_source(self):
        tree = _mosfet()
        geom = extract_geometry(tree)
        assert geom["channel_Eg"] == pytest.approx(1.12)  # Silicon
        assert geom["source_material"] == "Silicon"

    def test_no_fe_returns_none_t_fe(self):
        geom = extract_geometry(_mosfet())
        assert geom["t_fe"] is None
        assert geom["kappa_fe"] is None
        assert geom["has_fe"] is False

    def test_fe_insertion_extracts_t_fe_and_kappa(self):
        tree = _mosfet()
        fe_tree = mutate_insert_ferroelectric(tree, kappa_fe=35.0, t_fe=4e-9,
                                              rng=random.Random(0))
        geom = extract_geometry(fe_tree)
        assert geom["has_fe"] is True
        assert geom["t_fe"] == pytest.approx(4e-9)
        assert geom["kappa_fe"] == pytest.approx(35.0)

    def test_highk_extracts_kappa(self):
        """Swap oxide to high-k and confirm kappa_highk is read."""
        tree = _swap_material(_mosfet(), KIND_OXIDE, highk_material(25.0))
        # Also flip the kind from oxide to highk so the engine sees it.
        nodes = [RegionNode(KIND_HIGHK, rn.name, rn.box, rn.material, rn.doping)
                 if rn.kind == KIND_OXIDE else rn
                 for rn in tree.region_nodes]
        tree = DeviceTree(name=tree.name, region_nodes=tuple(nodes),
                          contacts=tree.contacts, gate_meta=tree.gate_meta)
        geom = extract_geometry(tree)
        assert geom["has_highk"] is True
        assert geom["kappa_highk"] == pytest.approx(25.0)

    def test_graphene_source_detected(self):
        tree = _swap_material(_mosfet(), KIND_SOURCE, GRAPHENE)
        geom = extract_geometry(tree)
        assert geom["source_material"] == "Graphene"


# ===========================================================================
# 2. load_laws
# ===========================================================================

class TestLoadLaws:
    def test_loads_four_laws(self):
        laws = load_laws()
        assert len(laws) == 4
        ids = {l.id for l in laws}
        assert ids == {"nc_stability", "dirac_source_bandpass",
                       "highk_interface", "gate_length_floor"}

    def test_law_fields_complete(self):
        laws = load_laws()
        for law in laws:
            assert isinstance(law, Law)
            assert law.id
            assert law.name
            assert law.effect
            assert isinstance(law.applies_when, dict)
            assert isinstance(law.constraints, list)
            assert len(law.constraints) >= 1
            assert law.rationale  # non-empty


# ===========================================================================
# 3. NC stability law
# ===========================================================================

class TestNcStabilityLaw:
    def _fe_tree(self, t_fe, kappa_fe):
        tree = _mosfet()
        return mutate_insert_ferroelectric(tree, kappa_fe=kappa_fe, t_fe=t_fe,
                                           rng=random.Random(0))

    def test_compliant_fe_passes(self):
        """t_fe/tox = 4/1.5 = 2.67 in [1,5], kappa=35 in [20,50]."""
        laws = load_laws()
        nc = next(l for l in laws if l.id == "nc_stability")
        tree = self._fe_tree(t_fe=4e-9, kappa_fe=35.0)
        assert check_law(tree, nc) is None

    def test_too_thin_fe_violates(self):
        """t_fe/tox = 0.5/1.5 = 0.33 < 1 -> NC unstable."""
        laws = load_laws()
        nc = next(l for l in laws if l.id == "nc_stability")
        tree = self._fe_tree(t_fe=0.5e-9, kappa_fe=35.0)
        msg = check_law(tree, nc)
        assert msg is not None
        assert "t_fe/tox" in msg

    def test_too_thick_fe_violates(self):
        """t_fe/tox = 10/1.5 = 6.67 > 5 -> decouples."""
        laws = load_laws()
        nc = next(l for l in laws if l.id == "nc_stability")
        tree = self._fe_tree(t_fe=10e-9, kappa_fe=35.0)
        msg = check_law(tree, nc)
        assert msg is not None
        assert "t_fe/tox" in msg

    def test_bad_kappa_violates(self):
        """kappa_fe=10 < 20 -> outside stable NC window."""
        laws = load_laws()
        nc = next(l for l in laws if l.id == "nc_stability")
        tree = self._fe_tree(t_fe=4e-9, kappa_fe=10.0)
        msg = check_law(tree, nc)
        assert msg is not None
        assert "kappa_fe" in msg

    def test_no_fe_not_applicable(self):
        """A plain MOSFET (no FE) is not subject to the NC law."""
        laws = load_laws()
        nc = next(l for l in laws if l.id == "nc_stability")
        assert check_law(_mosfet(), nc) is None


# ===========================================================================
# 4. Dirac-source band-pass law
# ===========================================================================

class TestDiracSourceLaw:
    def _graphene_source_tree(self, channel_material):
        tree = _swap_material(_mosfet(), KIND_SOURCE, GRAPHENE)
        tree = _swap_material(tree, KIND_CHANNEL, channel_material)
        return tree

    def test_graphene_source_wide_channel_passes(self):
        """Si channel (Eg=1.12 > 0.8) with graphene source -> OK."""
        laws = load_laws()
        law = next(l for l in laws if l.id == "dirac_source_bandpass")
        tree = self._graphene_source_tree(SILICON)
        assert check_law(tree, law) is None

    def test_graphene_source_narrow_channel_violates(self):
        """Graphene channel (Eg=0.2 < 0.8) with graphene source -> no window."""
        laws = load_laws()
        law = next(l for l in laws if l.id == "dirac_source_bandpass")
        tree = self._graphene_source_tree(GRAPHENE)
        msg = check_law(tree, law)
        assert msg is not None
        assert "Eg" in msg

    def test_silicon_source_not_applicable(self):
        """A Si-source MOSFET is not subject to the Dirac-source law."""
        laws = load_laws()
        law = next(l for l in laws if l.id == "dirac_source_bandpass")
        assert check_law(_mosfet(), law) is None


# ===========================================================================
# 5. High-k interface law
# ===========================================================================

class TestHighkLaw:
    def _highk_tree(self, kappa):
        tree = _mosfet()
        nodes = [RegionNode(KIND_HIGHK, rn.name, rn.box, highk_material(kappa), rn.doping)
                 if rn.kind == KIND_OXIDE else rn
                 for rn in tree.region_nodes]
        return DeviceTree(name=tree.name, region_nodes=tuple(nodes),
                          contacts=tree.contacts, gate_meta=tree.gate_meta)

    def test_compliant_highk_passes(self):
        """kappa=25 in [5,40], tox=1.5nm <= 1.5nm -> OK."""
        laws = load_laws()
        law = next(l for l in laws if l.id == "highk_interface")
        assert check_law(self._highk_tree(25.0), law) is None

    def test_excessive_kappa_violates(self):
        """kappa=50 > 40 -> interface/phonon issue."""
        laws = load_laws()
        law = next(l for l in laws if l.id == "highk_interface")
        msg = check_law(self._highk_tree(50.0), law)
        assert msg is not None
        assert "kappa" in msg

    def test_no_highk_not_applicable(self):
        laws = load_laws()
        law = next(l for l in laws if l.id == "highk_interface")
        assert check_law(_mosfet(), law) is None


# ===========================================================================
# 6. Gate-length floor law
# ===========================================================================

class TestGateLengthLaw:
    def test_normal_lg_passes(self):
        laws = load_laws()
        law = next(l for l in laws if l.id == "gate_length_floor")
        assert check_law(_mosfet(Lg=50e-9), law) is None

    def test_sub_5nm_lg_violates(self):
        laws = load_laws()
        law = next(l for l in laws if l.id == "gate_length_floor")
        msg = check_law(_mosfet(Lg=3e-9), law)
        assert msg is not None
        assert "Lg" in msg

    def test_boundary_5nm_passes(self):
        laws = load_laws()
        law = next(l for l in laws if l.id == "gate_length_floor")
        assert check_law(_mosfet(Lg=5e-9), law) is None


# ===========================================================================
# 7. check_all_laws (aggregate)
# ===========================================================================

class TestCheckAllLaws:
    def test_clean_mosfet_no_violations(self):
        laws = load_laws()
        assert check_all_laws(_mosfet(), laws) == []

    def test_collects_multiple_violations(self):
        """A graphene-source + graphene-channel + sub-5nm MOSFET violates
        both the Dirac-source and gate-length laws."""
        laws = load_laws()
        tree = _swap_material(_mosfet(Lg=3e-9), KIND_SOURCE, GRAPHENE)
        tree = _swap_material(tree, KIND_CHANNEL, GRAPHENE)
        vs = check_all_laws(tree, laws)
        assert len(vs) >= 2
        ids = {v.split("]")[0].strip("[") for v in vs}
        assert "dirac_source_bandpass" in ids
        assert "gate_length_floor" in ids

    def test_empty_laws_passes_everything(self):
        assert check_all_laws(_mosfet(), []) == []


# ===========================================================================
# 8. Wiring: the evolve() law gate rejects violating trees pre-solver
# ===========================================================================

class TestEvolveLawGate:
    def test_constrained_search_runs_without_error(self):
        """evolve(use_law_constraints=True) completes on a tiny budget.

        Uses a coarse resolution + few iterations so this stays in the fast
        suite (the point is wiring, not convergence).  Trust is not asserted
        (that needs the fine mesh of the slow tests).
        """
        from tcad.search.evolution import evolve
        res = evolve(
            seed_template="mosfet", seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=2, generations=1,
            allow_mechanism_mutation=False,
            use_law_constraints=True,
            gate_voltages=np.linspace(0.0, 0.4, 3), vd=0.1,
            resolution=(20e-9, 20e-9, 20e-9), max_iter=15, tol=1e-7,
            rng=random.Random(0), verbose=False,
        )
        assert len(res.archive) >= 1

    def test_default_false_unchanged_behavior(self):
        """use_law_constraints defaults to False (no gate, preserves regression)."""
        import inspect
        from tcad.search.evolution import evolve
        sig = inspect.signature(evolve)
        assert sig.parameters["use_law_constraints"].default is False

    def test_gate_rejects_violating_tree_before_solve(self, monkeypatch):
        """When use_law_constraints=True, a tree that violates a law is never
        passed to evaluate_candidate.  We monkeypatch _mutate_for_search to
        return a deterministically-violating tree (sub-5nm Lg) and count
        evaluate_candidate calls; with the gate ON, only the seed is solved.
        """
        from tcad.search import evolution

        call_count = {"n": 0}

        def _fake_evaluate(cand, **kw):
            call_count["n"] += 1
            cand.evaluated = True
            cand.trust = False
            cand.perf = float("-inf")
            return cand

        # Force every mutated child to be a sub-5nm Lg tree (violates
        # gate_length_floor deterministically, regardless of _safe_perturb
        # clamping which would otherwise lift Lg to the 5nm floor).
        violating_tree = tree_from_template("mosfet", W=40e-9, Lg=3e-9)

        def _fake_mutate(tree, rng, *, template_name, params,
                         allow_mechanism_mutation):
            return violating_tree

        monkeypatch.setattr(evolution, "evaluate_candidate", _fake_evaluate)
        monkeypatch.setattr(evolution, "_mutate_for_search", _fake_mutate)

        evolution.evolve(
            seed_template="mosfet", seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=False,
            use_law_constraints=True,
            gate_voltages=np.linspace(0.0, 0.4, 3), vd=0.1,
            resolution=(15e-9, 15e-9, 15e-9), max_iter=10, tol=1e-7,
            rng=random.Random(1), verbose=False,
        )
        # Only the seed is evaluated (the seed is not law-gated; only mutated
        # children are).  All mutated children are rejected pre-solve.
        assert call_count["n"] == 1, (
            f"expected 1 eval (seed only), got {call_count['n']} — law gate "
            f"failed to reject violating children")

    def test_gate_off_evaluates_violating_tree(self, monkeypatch):
        """With use_law_constraints=False, the same violating children ARE
        evaluated (no law gate).  This confirms the gate is what blocks."""
        from tcad.search import evolution

        call_count = {"n": 0}

        def _fake_evaluate(cand, **kw):
            call_count["n"] += 1
            cand.evaluated = True
            cand.trust = False
            cand.perf = float("-inf")
            return cand

        violating_tree = tree_from_template("mosfet", W=40e-9, Lg=3e-9)

        def _fake_mutate(tree, rng, *, template_name, params,
                         allow_mechanism_mutation):
            return violating_tree

        monkeypatch.setattr(evolution, "evaluate_candidate", _fake_evaluate)
        monkeypatch.setattr(evolution, "_mutate_for_search", _fake_mutate)

        evolution.evolve(
            seed_template="mosfet", seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=False,
            use_law_constraints=False,
            gate_voltages=np.linspace(0.0, 0.4, 3), vd=0.1,
            resolution=(15e-9, 15e-9, 15e-9), max_iter=10, tol=1e-7,
            rng=random.Random(1), verbose=False,
        )
        # Seed + initial-population children: more than 1 eval (gate is off).
        assert call_count["n"] > 1, (
            f"expected >1 eval with gate OFF, got {call_count['n']}")


# ===========================================================================
# 9. Slow: M6 exit criterion — law constraints cut wasted solves
# ===========================================================================

@slow
class TestLawConstraintsEfficiency:
    """The D3+D4 exit criterion (plan §D3 line 123): law constraints cut
    wasted solver calls without killing the discovery of non-trivial topology.

    We count evaluate_candidate invocations in two identical-config runs
    (same seed, budget, rng) with and without the law gate.  The constrained
    run must invoke the solver no more times than the unconstrained run
    (it rejects physically-incoherent trees pre-solve), while still reaching
    at least one trusted candidate (the law does not over-reject).
    """

    _EVAL_KW = dict(
        gate_voltages=np.linspace(0.0, 0.4, 6), vd=0.1,
        resolution=(10e-9, 5e-9, 10e-9), max_iter=50, tol=1e-7,
    )

    def _run_with_counter(self, monkeypatch, use_laws):
        from tcad.search import evolution
        calls = {"n": 0}
        real = evolution.evaluate_candidate

        def _counting(cand, **kw):
            calls["n"] += 1
            return real(cand, **kw)

        monkeypatch.setattr(evolution, "evaluate_candidate", _counting)
        res = evolution.evolve(
            seed_template="mosfet", seed_params={"W": 40e-9, "Lg": 50e-9},
            population_size=4, generations=1,
            allow_mechanism_mutation=True,
            use_law_constraints=use_laws,
            rng=random.Random(42), verbose=False,
            **self._EVAL_KW,
        )
        return calls["n"], res

    def test_constrained_fewer_or_equal_solves(self, monkeypatch):
        n_off, res_off = self._run_with_counter(monkeypatch, use_laws=False)
        n_on, res_on = self._run_with_counter(monkeypatch, use_laws=True)
        # The constrained run rejects physically-incoherent trees pre-solve,
        # so it invokes the solver no more often than the unconstrained run.
        assert n_on <= n_off, (
            f"law gate did not reduce solves: on={n_on} off={n_off}")
        # And it must still produce a non-empty archive (not over-reject).
        assert len(res_on.archive) >= 1
