"""C3 search engine: minimal NSGA-II + surrogate for device discovery.

Implements the discovery loop (plan0619.md §C3):
- **Objective**: F = [Perf, Novelty] two-objective Pareto.  Perf is a scalar
  combining Ion/Ioff/SS (lower-is-better terms negated); Novelty is the
  structural distance of the candidate's grammar tree from the archive of
  evaluated designs (B4 novelty).
- **NSGA-II**: tournament selection, mutation-only reproduction (C2 operators),
  non-dominated sorting + crowding distance.  Population ~30, generations ~20.
- **Trust gate (B5)**: only candidates with ``trust=True`` enter the Pareto
  front; untrusted candidates are kept in the archive for novelty distance but
  never reported as discoveries.
- **Surrogate**: a lightweight kNN regressor predicts Perf mean + variance
  from the structural feature vector of the tree; LCB (mean - kappa*std)
  pre-screens offspring so only promising candidates invoke the solver.
  High-fidelity re-evaluation of the final Pareto front is the caller's job.

The truth-chain (plan §C3 line 105): a known-space search (Lg/tox/Ns of a
MOSFET) converges toward the known optimum; an open-space search (allowing
``insert_fe``) produces at least one non-trivial candidate (topology outside
the 14 templates).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from ..geometry import Device
from ..simulator import simulate_sweep
from ..postprocess import assess_candidate, assess_trust, attribute_mechanism, MechanismReport
from .grammar import (
    DeviceTree, build, validate, tree_from_template, supported_templates,
    template_default_params,
    RegionNode, KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_OXIDE, KIND_HIGHK,
    KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL, KIND_SUBSTRATE, KIND_BOX,
    KIND_WIRE, KIND_VIA, KIND_RAIL, KIND_P_SIDE, KIND_N_SIDE,
    WRAP_PLANAR_TOP, WRAP_DOUBLE_Y, WRAP_FOUR_SIDE,
)
from .mutation import mutate, mutate_parameter, mutate_gate_wrap, mutate_material


#: Module-level lazily-loaded law cache (D3+D4 law library).  Loaded on first
#: use by :func:`_get_laws`; avoids re-reading ``laws.json`` per candidate.
_LAWS = None


def _get_laws():
    """Lazily load the law library (cached after first call).

    The import is deferred to avoid a circular import: ``tcad.knowledge``
    imports from ``tcad.search.grammar``, and ``tcad.search.__init__`` imports
    this module, so a top-level ``from ..knowledge import ...`` would deadlock.
    """
    global _LAWS
    if _LAWS is None:
        from ..knowledge import load_laws as _load
        _LAWS = _load()
    return _LAWS


def _law_check(tree):
    """Return law violations for a tree (deferred import, see _get_laws)."""
    from ..knowledge import check_all_laws as _check
    return _check(tree, _get_laws())


def _mutate_for_search(
    tree: DeviceTree,
    rng: random.Random,
    *,
    template_name: Optional[str],
    params: Optional[Dict[str, float]],
    allow_mechanism_mutation: bool,
) -> Optional[DeviceTree]:
    """Pick a mutation operator consistent with the search mode.

    Known-space (allow_mechanism_mutation=False): only parameter mutation —
    the search explores the seed template's parameter space, so every candidate
    stays inside the 14-template topology (kind set unchanged).  This is what
    makes the known-space truth-chain meaningful (best point should track the
    analytic optimum).

    Open-space (allow_mechanism_mutation=True): parameter + structural +
    mechanism operators are all eligible, so the search can produce topologies
    outside the seed template (e.g. a MOSFET seed with an inserted FE layer).
    """
    if allow_mechanism_mutation:
        return mutate(tree, rng, template_name=template_name, params=params)
    # Known-space: parameter-only.  If the seed carries no perturbable params
    # (template_name/params missing), fall back to gate_wrap which keeps the
    # same kind set for the templates that have a gate.
    if template_name is not None and params:
        new_tree, _ = mutate_parameter(tree, template_name, params, rng)
        if new_tree is not None:
            return new_tree
    return mutate_gate_wrap(tree, rng)


# ---------------------------------------------------------------------------
# Candidate representation
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    """One evaluated (or to-be-evaluated) device candidate."""
    tree: DeviceTree
    template_name: str
    params: Dict[str, float] = field(default_factory=dict)
    perf: float = float("nan")
    novelty: float = float("nan")
    trust: bool = False
    metrics: Optional[dict] = None
    evaluated: bool = False
    origin: str = "seed"  # seed | mutated | crossover
    mechanism: Optional[MechanismReport] = None  # D2 attribution (trusted only)

    def feature_vector(self) -> np.ndarray:
        """Structural + physics feature vector for novelty + surrogate.

        A bag-of-kinds histogram (normalized) + wrap one-hot (18-D) plus a
        4-D mechanism-fraction vector (D2: drift/diffusion/BTBT/FE).  The
        mechanism vector is zero until the candidate is trusted and evaluated;
        once present it makes novelty a structural+physics distance (plan §64).
        """
        kinds = [
            KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_WIRE,
            KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE, KIND_FERROELECTRIC,
            KIND_METAL, KIND_SUBSTRATE, KIND_BOX, KIND_VIA, KIND_RAIL,
            KIND_P_SIDE, KIND_N_SIDE,
        ]
        counts = np.zeros(len(kinds), dtype=float)
        for rn in self.tree.region_nodes:
            if rn.kind in kinds:
                counts[kinds.index(rn.kind)] += 1.0
        total = counts.sum()
        if total > 0:
            counts /= total
        # Wrap one-hot.
        wrap = self.tree.gate_meta.wrap if self.tree.gate_meta else "none"
        wrap_oh = np.array([
            float(wrap == WRAP_PLANAR_TOP),
            float(wrap == WRAP_DOUBLE_Y),
            float(wrap == WRAP_FOUR_SIDE),
        ])
        # Mechanism-fraction vector (D2); zero if not yet attributed.
        if self.mechanism is not None:
            mech_vec = self.mechanism.feature_vector()
        else:
            mech_vec = np.zeros(4, dtype=float)
        return np.concatenate([counts, wrap_oh, mech_vec])


# ---------------------------------------------------------------------------
# Performance scalar
# ---------------------------------------------------------------------------

def compute_perf(metrics_dict: dict) -> float:
    """Scalar performance from discovery metrics (higher = better).

    Combines Ion/Ioff ratio (log10, capped), subthreshold swing (lower better),
    and on-current.  Untrusted / NaN metrics map to -inf so they never dominate
    the Pareto front.
    """
    if metrics_dict is None:
        return float("-inf")
    ion = metrics_dict.get("Ion", float("nan"))
    ioff = metrics_dict.get("Ioff", float("nan"))
    ss = metrics_dict.get("SS", float("nan"))
    if not (np.isfinite(ion) and np.isfinite(ioff) and np.isfinite(ss)):
        return float("-inf")
    if ion <= 0 or ioff <= 0 or ss <= 0:
        return float("-inf")
    ion_ioff = min(math.log10(ion / ioff), 8.0)  # cap at 1e8
    ss_term = max(0.0, 200.0 - ss) / 200.0  # 0 at SS=200, 1 at SS=0
    log_ion = math.log10(max(ion, 1e-15))
    # Weighted sum: switching quality dominates, on-current is a tiebreaker.
    return 0.5 * ion_ioff + 0.3 * ss_term + 0.2 * (log_ion + 15.0) / 30.0


# ---------------------------------------------------------------------------
# Evaluation (low-fidelity solver sweep + trust gate)
# ---------------------------------------------------------------------------

def evaluate_candidate(
    cand: Candidate,
    *,
    gate_voltages: np.ndarray,
    vd: float = 0.3,
    resolution: Tuple[float, float, float] = (10e-9, 10e-9, 10e-9),
    max_iter: int = 60,
    tol: float = 1e-7,
    verbose: bool = False,
) -> Candidate:
    """Run a low-fidelity Vg sweep and stamp Perf + trust on the candidate.

    The trust gate's default ``Ion_max=1e3`` assumes absolute current [A], but
    ``contact_current_1d`` (which backs Ion) returns current *density* [A/m²]
    (unit cross-section).  For a nanoscale device a few A/m² is a tiny absolute
    current yet blows past the 1e3 A ceiling, so every candidate is spuriously
    rejected.  We pass a density-scaled ``physical_range`` so the trust gate
    judges the *shape* of the transfer curve (monotonic switching, finite SS)
    rather than the absolute magnitude, which the coarse search mesh inflates.
    The high-fidelity re-evaluation step (caller) recomputes with a fine mesh
    and the strict default range.
    """
    dev = build(cand.tree)
    # Apply drain bias by overriding the drain contact voltage in the device.
    if "drain" in dev.contacts:
        shape, _ = dev.contacts["drain"]
        dev.contacts["drain"] = (shape, vd)
    try:
        sim, results = simulate_sweep(
            dev, sweep_contacts={"gate": gate_voltages},
            resolution=resolution, quantum=False,
            max_iter=max_iter, tol=tol, verbose=verbose,
        )
    except Exception:
        cand.evaluated = True
        cand.trust = False
        cand.perf = float("-inf")
        return cand

    # Density-scaled physical range: Ion is in [A/m²].  1e12 A/m² is ~1e3 A
    # through a 1µm² cross-section, i.e. the original sanity ceiling mapped to
    # the density units the current extractor actually returns.
    density_range = {"Ion_min": 0.0, "Ion_max": 1e12, "SS_min": 1.0, "SS_max": 1e5}
    rep = assess_candidate(sim, results, drain_contact="drain",
                           gate_contact="gate", physical_range=density_range)
    cand.metrics = rep.logic.as_dict() if rep.logic else None
    cand.trust = bool(rep.trust)
    cand.perf = compute_perf(cand.metrics) if cand.trust else float("-inf")
    cand.evaluated = True
    # D2 mechanism attribution on the last sweep point (representative bias).
    # Only computed for trusted candidates (untrusted results carry no
    # credible physics); zero vector is used by feature_vector() otherwise.
    if cand.trust:
        try:
            cand.mechanism = attribute_mechanism(sim, results[-1])
        except Exception:
            cand.mechanism = None
    return cand


# ---------------------------------------------------------------------------
# Novelty (B4 structural distance to archive)
# ---------------------------------------------------------------------------

def compute_novelty(cand: Candidate, archive: List[Candidate], k: int = 5) -> float:
    """Average Euclidean distance to the k nearest archive feature vectors."""
    if not archive:
        return 0.0
    fv = cand.feature_vector()
    dists = []
    for other in archive:
        if other is cand or not other.evaluated:
            continue
        d = float(np.linalg.norm(fv - other.feature_vector()))
        dists.append(d)
    if not dists:
        return 0.0
    dists.sort()
    kk = min(k, len(dists))
    return sum(dists[:kk]) / kk


# ---------------------------------------------------------------------------
# NSGA-II selection
# ---------------------------------------------------------------------------

def _dominates(a: Candidate, b: Candidate) -> bool:
    """a dominates b iff a >= b on all objectives and > on at least one.

    Objectives are maximized: Perf (higher better), Novelty (higher better).
    Untrusted candidates (perf = -inf) are dominated by any trusted one.
    """
    pa, na = a.perf, a.novelty
    pb, nb = b.perf, b.novelty
    if pa < pb and na < nb:
        return False
    if pa > pb and na > nb:
        return True
    return (pa >= pb and na >= nb) and (pa > pb or na > nb)


def non_dominated_sort(pop: List[Candidate]) -> List[List[int]]:
    """Return fronts (list of index-lists), front 0 = Pareto front.

    Robust O(n^3) implementation: a point is in the current front if no other
    unplaced point dominates it.
    """
    n = len(pop)
    placed = [False] * n
    fronts: List[List[int]] = []
    remaining = list(range(n))
    while remaining:
        front = []
        for i in remaining:
            dominated = False
            for j in remaining:
                if i == j:
                    continue
                if _dominates(pop[j], pop[i]):
                    dominated = True
                    break
            if not dominated:
                front.append(i)
        for i in front:
            placed[i] = True
        fronts.append(front)
        remaining = [i for i in remaining if i not in front]
    return fronts


def crowding_distance(front: List[Candidate]) -> List[float]:
    """Crowding distance for one front (for diversity preservation)."""
    n = len(front)
    if n <= 2:
        return [float("inf")] * n
    dists = [0.0] * n
    for key in ("perf", "novelty"):
        order = sorted(range(n), key=lambda i: getattr(front[i], key))
        vals = [getattr(front[i], key) for i in order]
        vmin, vmax = min(vals), max(vals)
        dists[order[0]] = float("inf")
        dists[order[-1]] = float("inf")
        if vmax > vmin:
            for idx in range(1, n - 1):
                dists[order[idx]] += (vals[idx + 1] - vals[idx - 1]) / (vmax - vmin)
    return dists


def tournament_select(pop: List[Candidate], rng: random.Random) -> Candidate:
    """Binary tournament: lower front rank wins; ties broken by crowding."""
    i, j = rng.sample(range(len(pop)), 2)
    # Lower front index is better; we approximate by direct dominance.
    if _dominates(pop[i], pop[j]):
        return pop[i]
    if _dominates(pop[j], pop[i]):
        return pop[j]
    # Tie: pick the more novel one (encourages exploration).
    return pop[i] if pop[i].novelty >= pop[j].novelty else pop[j]


# ---------------------------------------------------------------------------
# Surrogate (kNN regressor with LCB)
# ---------------------------------------------------------------------------

class Surrogate:
    """k-NN surrogate predicting Perf mean + std from feature vectors.

    Trained on evaluated candidates; ``lcb`` returns mean - kappa*std for
    acquisition.  This is the lightest possible uncertainty-aware surrogate
    (plan §C3 mentions RF/GP; kNN suffices for the discovery-grade first cut
    and needs no external deps).
    """

    def __init__(self, k: int = 5):
        self.k = k
        self.X: List[np.ndarray] = []
        self.y: List[float] = []

    def fit(self, candidates: List[Candidate]) -> None:
        self.X = [c.feature_vector() for c in candidates if c.evaluated and c.trust]
        self.y = [c.perf for c in candidates if c.evaluated and c.trust]

    def predict(self, cand: Candidate) -> Tuple[float, float]:
        if not self.X:
            return (0.0, 1.0)
        fv = cand.feature_vector()
        dists = [float(np.linalg.norm(fv - x)) for x in self.X]
        kk = min(self.k, len(dists))
        order = sorted(range(len(dists)), key=lambda i: dists[i])[:kk]
        ys = [self.y[i] for i in order]
        mean = float(np.mean(ys)) if ys else 0.0
        std = float(np.std(ys)) if len(ys) > 1 else 1.0
        return (mean, std)

    def lcb(self, cand: Candidate, kappa: float = 1.0) -> float:
        mean, std = self.predict(cand)
        return mean - kappa * std


# ---------------------------------------------------------------------------
# Evolution loop
# ---------------------------------------------------------------------------

@dataclass
class EvolutionResult:
    """Outcome of one ``evolve`` run."""
    population: List[Candidate]
    archive: List[Candidate]
    pareto_front: List[Candidate]
    history: List[dict] = field(default_factory=list)
    nontrivial_found: bool = False


def evolve(
    seed_template: str = "mosfet",
    seed_params: Optional[Dict[str, float]] = None,
    *,
    population_size: int = 12,
    generations: int = 6,
    gate_voltages: Optional[np.ndarray] = None,
    vd: float = 0.3,
    resolution: Tuple[float, float, float] = (12e-9, 12e-9, 12e-9),
    max_iter: int = 60,
    tol: float = 1e-7,
    allow_mechanism_mutation: bool = False,
    surrogate_kappa: float = 1.0,
    use_law_constraints: bool = False,
    rng: Optional[random.Random] = None,
    verbose: bool = False,
) -> EvolutionResult:
    """Run a discovery evolution loop.

    Parameters
    ----------
    seed_template, seed_params : starting design.
    population_size, generations : NSGA-II budget (small defaults for tests).
    allow_mechanism_mutation : if True, the ``insert_fe`` operator is enabled,
        opening the search to topologies outside the seed template (open space).
    surrogate_kappa : LCB exploration-exploitation tradeoff; 0 = pure mean.
    use_law_constraints : if True, the D3+D4 law library gates every mutated
        tree before the solver runs — trees violating an applicable physical
        law (e.g. NC stability window, Dirac-source band-pass, high-k
        interface, gate-length floor) are rejected without consuming solver
        budget.  Default False preserves the unconstrained search behavior.
    max_iter, tol : forwarded to the solver (low-fidelity search budget).
    """
    rng = rng or random.Random()
    if gate_voltages is None:
        gate_voltages = np.linspace(0.0, 0.5, 4)
    if seed_params is None:
        seed_params = {}

    # Seed population: the base design + parameter-perturbed variants.
    base_tree = tree_from_template(seed_template, **seed_params)
    # Populate the candidate's param dict with the template defaults overlaid
    # by the caller's overrides, so parameter mutation has perturbable knobs.
    seed_params_full = template_default_params(seed_template)
    seed_params_full.update(seed_params)
    base_cand = Candidate(tree=base_tree, template_name=seed_template,
                          params=seed_params_full, origin="seed")
    population: List[Candidate] = []
    archive: List[Candidate] = []

    # Evaluate the seed.
    evaluate_candidate(base_cand, gate_voltages=gate_voltages, vd=vd,
                       resolution=resolution, max_iter=max_iter, tol=tol,
                       verbose=verbose)
    base_cand.novelty = 0.0
    population.append(base_cand)
    archive.append(base_cand)

    # Generate initial population by parameter mutation.
    while len(population) < population_size:
        parent = rng.choice(population)
        new_tree = _mutate_for_search(
            parent.tree, rng,
            template_name=parent.template_name,
            params=parent.params,
            allow_mechanism_mutation=allow_mechanism_mutation,
        )
        if new_tree is None or validate(new_tree):
            continue
        # D3+D4 law gate: reject physically-incoherent trees before solving.
        if use_law_constraints and _law_check(new_tree):
            continue
        child = Candidate(tree=new_tree, template_name=parent.template_name,
                          params=dict(parent.params), origin="mutated")
        evaluate_candidate(child, gate_voltages=gate_voltages, vd=vd,
                           resolution=resolution, max_iter=max_iter, tol=tol,
                           verbose=verbose)
        child.novelty = compute_novelty(child, archive)
        population.append(child)
        archive.append(child)

    surrogate = Surrogate()
    history: List[dict] = []

    for gen in range(generations):
        surrogate.fit(archive)
        # Produce offspring.
        offspring: List[Candidate] = []
        attempts = 0
        while len(offspring) < population_size and attempts < population_size * 6:
            attempts += 1
            parent = tournament_select(population, rng)
            new_tree = _mutate_for_search(
                parent.tree, rng,
                template_name=parent.template_name,
                params=parent.params,
                allow_mechanism_mutation=allow_mechanism_mutation,
            )
            if new_tree is None or validate(new_tree):
                continue
            # D3+D4 law gate: reject physically-incoherent trees before solving.
            if use_law_constraints and _law_check(new_tree):
                continue
            child = Candidate(tree=new_tree, template_name=parent.template_name,
                              params=dict(parent.params), origin="mutated")
            # Surrogate pre-screen: skip candidates with very low LCB.
            if surrogate.lcb(child, kappa=surrogate_kappa) < -1e6:
                continue
            evaluate_candidate(child, gate_voltages=gate_voltages, vd=vd,
                               resolution=resolution, max_iter=max_iter, tol=tol,
                               verbose=verbose)
            child.novelty = compute_novelty(child, archive)
            offspring.append(child)
            archive.append(child)
        if not offspring:
            continue
        # Combine + select next generation by non-dominated sort + crowding.
        combined = population + offspring
        fronts = non_dominated_sort(combined)
        next_pop: List[Candidate] = []
        for front in fronts:
            if len(next_pop) + len(front) <= population_size:
                next_pop.extend([combined[i] for i in front])
            else:
                cd = crowding_distance([combined[i] for i in front])
                order = sorted(range(len(front)), key=lambda i: -cd[i])
                for idx in order:
                    next_pop.append(combined[front[idx]])
                    if len(next_pop) >= population_size:
                        break
            if len(next_pop) >= population_size:
                break
        population = next_pop[:population_size]
        trusted = [c for c in population if c.trust]
        best = max(trusted, key=lambda c: c.perf) if trusted else None
        history.append({
            "generation": gen,
            "trusted": len(trusted),
            "best_perf": best.perf if best else float("-inf"),
        })
        if verbose and best:
            print(f"  gen {gen}: trusted={len(trusted)} best_perf={best.perf:.3f}")

    # Final Pareto front over trusted candidates.
    trusted_all = [c for c in archive if c.trust]
    fronts = non_dominated_sort(trusted_all) if trusted_all else []
    pareto = [trusted_all[i] for i in fronts[0]] if fronts and fronts[0] else []

    # Non-trivial candidate: topology outside the seed template's kind set.
    seed_kinds = frozenset(rn.kind for rn in base_tree.region_nodes)
    nontrivial = any(
        frozenset(rn.kind for rn in c.tree.region_nodes) != seed_kinds
        for c in archive if c.trust
    )

    return EvolutionResult(
        population=population,
        archive=archive,
        pareto_front=pareto,
        history=history,
        nontrivial_found=nontrivial,
    )
