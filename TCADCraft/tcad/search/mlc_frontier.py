"""MLC design frontier using complete fixed-code readout metrics.

Objectives: fixed-prior mutual information, coded bit-error reliability,
and negative cell electron budget. The finite cell capacity is a declared
reflecting boundary; default rates and ideal count sensing are uncalibrated.
Worst directional adjacent-boundary errors remain diagnostic outputs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..physics.electron_counting import BirthDeathChain
from ..physics.storage_readout import electron_storage_readout
from .attribution import attach_attributions
from .fe_frontier import _crowding, _non_dominated_fronts

#: Search-score floor only; the measured BER is returned without flooring.
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
    priors_by_levels: Optional[Dict[int, Tuple[float, ...]]] = None
    codewords_by_levels: Optional[Dict[int, Tuple[str, ...]]] = None
    rate_source: str = "unvalidated_synthetic_stress_rates"

    def __post_init__(self):
        from ..physics.storage_readout import symbol_priors, binary_codewords
        if (not self.levels_choices or len(set(self.levels_choices)) != len(self.levels_choices)
                or any(not isinstance(k, int) or isinstance(k, bool) or k < 2 for k in self.levels_choices)):
            raise ValueError("levels_choices must contain distinct integer alphabets >= 2")
        for name in ("spacing", "stress_scale"):
            values = getattr(self, name)
            if (len(values) != 2 or not all(np.isfinite(v) and v > 0 for v in values)
                    or values[1] < values[0]):
                raise ValueError(f"{name} must be a positive increasing interval")
        for name in ("mu0", "lam0", "t_retention", "mutation_sigma"):
            value = getattr(self, name)
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if not isinstance(self.n_max_cap, int) or isinstance(self.n_max_cap, bool) or self.n_max_cap < 2:
            raise ValueError("n_max_cap must be an integer >= 2")
        if not isinstance(self.rate_source, str) or not self.rate_source.strip():
            raise ValueError("rate_source must identify a source or unvalidated proxy")
        for mapping in (self.priors_by_levels, self.codewords_by_levels):
            if mapping is not None and any(k not in self.levels_choices for k in mapping):
                raise ValueError("readout settings refer to an unsupported alphabet")
        for k in self.levels_choices:
            symbol_priors(k, (self.priors_by_levels or {}).get(k))
            binary_codewords(k, (self.codewords_by_levels or {}).get(k))

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

    nominal_bits: float = float("nan")
    symbol_error_rate: float = float("nan")
    bit_error_rate: float = float("nan")
    worst_bit_error: float = float("nan")
    readout: Dict = field(default_factory=dict)
    validation: Dict = field(default_factory=dict)

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
            "trusted": self.trusted,
            "nominal_bits": self.nominal_bits,
            "symbol_error_rate": self.symbol_error_rate,
            "bit_error_rate": self.bit_error_rate,
            "worst_bit_error": self.worst_bit_error,
            "mutual_information_bits": self.bits,
            "readout": self.readout,
            "validation": self.validation,
            "score_error_floor": BER_FLOOR,
            "legacy_field_semantics": {
                "bits": "fixed_prior_mutual_information_bits",
                "worst_pair_error": "directional_adjacent_boundary_diagnostic_not_full_bit_BER",
                "reliability_neg_log10_ber": "negative_log10_full_coded_BER_with_score_floor",
            },
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
    raw_spacing, raw_stress = float(x["spacing"]), float(x["stress_scale"])
    if not np.isfinite(raw_spacing) or not np.isfinite(raw_stress):
        candidate = MlcFrontierCandidate(
            x={"spacing": raw_spacing, "stress_scale": raw_stress}, levels=levels)
        candidate.violations.append("non-finite design input")
        return candidate
    spacing = float(np.clip(raw_spacing, *config.bounds()["spacing"]))
    stress = float(np.clip(raw_stress, *config.bounds()["stress_scale"]))
    candidate = MlcFrontierCandidate(x={"spacing": spacing, "stress_scale": stress}, levels=levels)
    if not isinstance(levels, (int, np.integer)) or isinstance(levels, bool) or levels not in config.levels_choices:
        candidate.violations.append(f"invalid or unsupported integer levels={levels}")
        return candidate
    n_max = int(round(levels * spacing))
    if n_max < 2:
        candidate.violations.append("cell budget below two electrons")
        return candidate
    if n_max > config.n_max_cap:
        candidate.violations.append(f"cell budget {n_max} exceeds cap {config.n_max_cap}")
        return candidate
    counts = [int(round(k * spacing)) for k in range(1, levels + 1)]
    try:
        readout, validation = electron_storage_readout(
            counts, n_max, config.lam0 * stress, config.mu0 * stress,
            config.t_retention, priors=(config.priors_by_levels or {}).get(levels),
            codes=(config.codewords_by_levels or {}).get(levels), numerical_upper_boundary=False)
    except ValueError as error:
        candidate.violations.append(str(error))
        return candidate
    validation["rate_source"] = config.rate_source
    c = readout.confusion_matrix
    worst = max(max(float(c[k, k+1:].sum()), float(c[k+1, :k+1].sum()))
                for k in range(levels - 1))
    candidate.worst_pair_error = worst
    candidate.nominal_bits = float(np.log2(levels))
    candidate.bits = readout.mutual_information_bits
    candidate.reliability = float(-np.log10(max(readout.bit_error_rate, BER_FLOOR)))
    candidate.symbol_error_rate = readout.symbol_error_rate
    candidate.bit_error_rate = readout.bit_error_rate
    candidate.worst_bit_error = readout.worst_bit_error
    candidate.budget_electrons = n_max
    candidate.budget_efficiency = float(-n_max)
    candidate.readout = readout.as_dict()
    candidate.validation = validation
    candidate.trusted = bool(validation["numerical_valid"])
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
        model_class_limitation="declared finite-capacity rate proxy; full fixed-code BER and fixed-prior mutual information; ideal integer sensing; material rate and small-tail validation unavailable.",
    )
    return MlcFrontierResult(
        population=population, front=deduplicated, history=history,
    )

