"""E3 MLC stored-electron state design explorer (plan0918 direction-2).

Design question (comment7 2.1 / 5.5): at scaled nodes a programmed level
holds a handful of electrons, so multi-level storage must trade
state count against probabilistic retention.  "Reducing the number of
states per cell is the most effective mitigation of retention loss, at the
cost of density" becomes a computable Pareto frontier here.

Objective space (all maximized)
-------------------------------
``bits``               log2 of the number of stored levels K
``reliability``        -log10 of the worst adjacent-pair read-error
                       probability after the retention spec (exact from the
                       M3 :class:`BirthDeathChain` distribution, not a
                       Gaussian tail approximation)
``budget_efficiency``  negative total stored-electron count (the cell swing
                       K*spacing, a capacitance/area proxy).  A stress-scale
                       "quality" objective was tried first and is degenerate:
                       lower stress improves every other objective, so the
                       search pins it to its bound; quality has no modelled
                       price and therefore cannot be a frontier axis.

Design variables
----------------
``levels`` (K in {2,4,8,16}), ``spacing`` (electrons between adjacent
levels), ``stress_scale`` (multiplier on the unit disturb rates).

Physics model
-------------
Stored count evolves as a birth-death chain with per-electron loss
``mu(n) = mu0 * stress_scale * n`` and constant leak-in
``lam(n) = lam0 * stress_scale`` (capped at the cell budget).  Levels sit at
``spacing, 2*spacing, ..., K*spacing``; decision boundaries at half spacing.
The pair error is the worse of the two confusion directions, evaluated with
one exact chain advance per level over the full retention time (rates are
autonomous, so the uniformization step is exact).

Honesty boundaries
------------------
* The rate structure (independent per-electron loss + constant leak-in) is a
  declared v1 model; a trap-spectrum-coupled rate set (M1 ``TrapKinetics``)
  is the follow-up once physical golden parameters are frozen
  (calibration C-class).
* BER uses equal priors and midpoint thresholds; no read-noise sigma is
  folded in (that would need a sensing model).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..physics.electron_counting import BirthDeathChain
from .attribution import attach_attributions
from .fe_frontier import _crowding, _non_dominated_fronts

#: Numerical BER floor reported when the exact tail mass underflows.
BER_FLOOR = 1.0e-16


@dataclass
class MlcFrontierConfig:
    """Bounds and stress model for the E3 search."""

    levels_choices: Tuple[int, ...] = (2, 4, 8, 16)
    spacing: Tuple[float, float] = (2.0, 16.0)
    stress_scale: Tuple[float, float] = (0.05, 1.0)
    #: Unit disturb rates [1/s]: per-electron loss and constant leak-in.
    mu0: float = 1.0e-8
    lam0: float = 2.0e-9
    #: Retention specification [s] (10 years).
    t_retention: float = 10.0 * 365.25 * 24.0 * 3600.0
    n_max_cap: int = 256
    mutation_sigma: float = 0.20

    def bounds(self) -> Dict[str, tuple]:
        return {
            "spacing": self.spacing,
            "stress_scale": self.stress_scale,
        }


@dataclass
class MlcFrontierCandidate:
    x: Dict[str, float]
    levels: int = 2
    bits: float = float("nan")
    reliability: float = float("nan")
    budget_efficiency: float = float("nan")
    worst_pair_error: float = float("nan")
    budget_electrons: int = 0
    trusted: bool = False
    violations: List[str] = field(default_factory=list)

    @property
    def objectives(self) -> np.ndarray:
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([self.bits, self.reliability, self.budget_efficiency])

    def as_dict(self) -> Dict[str, object]:
        out = {"levels": self.levels}
        out.update(self.x)
        out.update({
            "bits": self.bits,
            "reliability_neg_log10_ber": self.reliability,
            "budget_electrons": self.budget_electrons,
            "budget_efficiency": self.budget_efficiency,
            "worst_pair_error": self.worst_pair_error,
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def _cell_chain(config: MlcFrontierConfig, n_max: int, stress: float) -> BirthDeathChain:
    return BirthDeathChain(
        n_max=n_max,
        capture_rate=lambda n: config.lam0 * stress,
        emission_rate=lambda n: config.mu0 * stress * n,
    )


def evaluate_mlc_candidate(
    x: Dict[str, float],
    levels: int,
    config: Optional[MlcFrontierConfig] = None,
) -> MlcFrontierCandidate:
    """Evaluate one E3 candidate (exact-chain BER at the retention spec)."""
    config = config or MlcFrontierConfig()
    spacing = float(np.clip(x["spacing"], *config.bounds()["spacing"]))
    stress = float(np.clip(x["stress_scale"], *config.bounds()["stress_scale"]))
    candidate = MlcFrontierCandidate(
        x={"spacing": spacing, "stress_scale": stress}, levels=int(levels),
    )
    if levels not in config.levels_choices:
        candidate.violations.append(f"levels={levels} not in {config.levels_choices}")
        return candidate
    n_max = int(round(levels * spacing))
    if n_max < 2:
        candidate.violations.append("cell budget below two electrons")
        return candidate
    if n_max > config.n_max_cap:
        candidate.violations.append(
            f"cell budget {n_max} exceeds cap {config.n_max_cap}"
        )
        return candidate

    chain = _cell_chain(config, n_max, stress)
    level_counts = [int(round(k * spacing)) for k in range(1, levels + 1)]
    worst = 0.0
    for k in range(levels - 1):
        boundary = 0.5 * (level_counts[k] + level_counts[k + 1])
        # Upward confusion: level k read above the boundary.
        chain.initialize(count=level_counts[k])
        p_up = chain.advance(config.t_retention)[
            int(np.floor(boundary + 1e-9)) + 1:
        ].sum()
        # Downward confusion: level k+1 read below the boundary.
        chain.initialize(count=level_counts[k + 1])
        p_down = chain.advance(config.t_retention)[
            : int(np.floor(boundary + 1e-9))
        ].sum()
        worst = max(worst, float(p_up), float(p_down))
    if not np.isfinite(worst):
        candidate.violations.append("non-finite pair error")
        return candidate
    error = max(worst, BER_FLOOR)
    candidate.worst_pair_error = float(worst)
    candidate.bits = float(np.log2(levels))
    candidate.reliability = float(-np.log10(error))
    candidate.budget_electrons = n_max
    candidate.budget_efficiency = float(-n_max)
    candidate.trusted = True
    return candidate


@dataclass
class MlcFrontierResult:
    population: List[MlcFrontierCandidate]
    front: List[MlcFrontierCandidate]
    history: List[Dict[str, object]] = field(default_factory=list)

    def to_rows(self):
        return [c.as_dict() for c in self.population]

    def front_rows(self):
        return [c.as_dict() for c in self.front]


def _mutate_mlc(
    candidate: MlcFrontierCandidate,
    config: MlcFrontierConfig,
    rng: random.Random,
) -> Dict[str, object]:
    child = {}
    for name, (lo, hi) in config.bounds().items():
        scale = max(hi - lo, 1e-30)
        child[name] = float(np.clip(
            candidate.x[name] + rng.gauss(0.0, config.mutation_sigma) * scale,
            lo, hi,
        ))
    choices = list(config.levels_choices)
    if rng.random() < 0.3:
        idx = choices.index(candidate.levels)
        step = rng.choice([-1, 1])
        idx = int(np.clip(idx + step, 0, len(choices) - 1))
        child["levels"] = choices[idx]
    else:
        child["levels"] = candidate.levels
    return child


def evolve_mlc_frontier(
    config: Optional[MlcFrontierConfig] = None,
    population_size: int = 16,
    generations: int = 8,
    seed: int = 0,
    init_population: Optional[List[Dict[str, object]]] = None,
) -> MlcFrontierResult:
    """Run the E3 NSGA-II loop (trusted candidates only enter the front)."""
    config = config or MlcFrontierConfig()
    if population_size < 4:
        raise ValueError("population_size must be >= 4")
    if generations < 1:
        raise ValueError("generations must be >= 1")
    rng = random.Random(seed)
    bounds = config.bounds()
    levels_choices = config.levels_choices

    designs: List[Dict[str, object]] = []
    if init_population:
        for d in init_population:
            entry = {
                "spacing": float(np.clip(d["spacing"], *bounds["spacing"])),
                "stress_scale": float(np.clip(
                    d["stress_scale"], *bounds["stress_scale"],
                )),
                "levels": int(d["levels"]),
            }
            designs.append(entry)
    while len(designs) < population_size:
        designs.append({
            "spacing": rng.uniform(*bounds["spacing"]),
            "stress_scale": rng.uniform(*bounds["stress_scale"]),
            "levels": rng.choice(levels_choices),
        })

    history: List[Dict[str, object]] = []

    def evaluate(design):
        cand = evaluate_mlc_candidate(design, int(design["levels"]), config)
        history.append(cand.as_dict())
        return cand

    population = [evaluate(d) for d in designs]

    for _ in range(generations):
        objectives = np.vstack([c.objectives for c in population])
        fronts = _non_dominated_fronts(objectives)
        rank = np.empty(len(population), dtype=int)
        crowd = np.zeros(len(population))
        for r, front in enumerate(fronts):
            for i in front:
                rank[i] = r
            front_crowd = _crowding(objectives[front])
            for local_i, i in enumerate(front):
                crowd[i] = front_crowd[local_i]
        children = []
        while len(children) < population_size:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            child_design = _mutate_mlc(parent, config, rng)
            children.append(evaluate(child_design))
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]
    deduplicated = []
    seen = set()
    for cand in front:
        key = tuple(np.round(cand.objectives, 9))
        if key not in seen:
            seen.add(key)
            deduplicated.append(cand)
    attach_attributions(
        deduplicated,
        lambda d: evaluate_mlc_candidate(d, int(d["levels"]), config),
        config.bounds(),
        lambda c: {**c.x, "levels": c.levels},
        model_class_limitation="declared v1 rate structure (per-electron loss + constant leak-in); equal priors and midpoint thresholds; no read-noise sigma; synthetic unit stress rates until a trap-spectrum physical golden.",
    )
    return MlcFrontierResult(
        population=population, front=deduplicated, history=history,
    )

