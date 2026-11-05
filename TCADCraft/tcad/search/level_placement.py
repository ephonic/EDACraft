"""Multi-level count placement using complete coded readout channels.

Search objectives are fixed-code bit BER and fixed-prior mutual information.
Adjacent-pair errors remain diagnostics. Model acceptance is numerical;
uncalibrated default rates do not establish physical storage reliability.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts
from ..physics.storage_readout import (
    electron_storage_readout, symbol_priors, binary_codewords, _retained_count,
)

Q_E = 1.602176634e-19


@dataclass
class LevelPlacementConfig:
    n_levels: int = 4                    # K storage levels
    total_budget: float = 200.0          # max electron count
    mu0_per_s: float = 2e-10             # per-electron loss rate (scales with n)
    lam0_per_s: float = 2e-8             # constant leak-in rate (hits level 0)
    t_retention_s: float = 3.156e8       # 10 years
    n_chain: int = 240                   # BirthDeathChain n_max (budget + drift headroom)
    mutation_sigma: float = 0.06
    priors: Optional[Tuple[float, ...]] = None
    codewords: Optional[Tuple[str, ...]] = None
    overflow_tolerance: float = 1e-10
    rate_source: str = "unvalidated_default_proxy"

    def __post_init__(self):
        for name in ("n_levels", "n_chain"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < (2 if name == "n_levels" else 1):
                raise ValueError(f"{name} must be a valid positive integer")
        if (not math.isfinite(self.total_budget) or self.total_budget < 1
                or self.total_budget != round(self.total_budget)
                or self.total_budget > self.n_chain):
            raise ValueError("total_budget must be an integer count in [1, n_chain]")
        for name in ("mu0_per_s", "lam0_per_s", "t_retention_s", "mutation_sigma", "overflow_tolerance"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if self.overflow_tolerance > 1:
            raise ValueError("overflow_tolerance must not exceed one")
        if not isinstance(self.rate_source, str) or not self.rate_source.strip():
            raise ValueError("rate_source must identify a source or unvalidated proxy")
        symbol_priors(self.n_levels, self.priors)
        binary_codewords(self.n_levels, self.codewords)


@dataclass
class LevelPlacementCandidate:
    positions: np.ndarray
    # Compatibility diagnostic: worst equal-prior adjacent binary pair.
    ber_worst: float = float("nan")
    # Compatibility alias: now the actual fixed-prior mutual information.
    effective_bits: float = float("nan")
    uniform_ber: float = float("nan")  # Compatibility alias for uniform coded BER.
    improvement_factor: Optional[float] = None
    trusted: bool = False  # Numerical consistency within the declared model.
    symbol_error_rate: float = float("nan")
    bit_error_rate: float = float("nan")
    mutual_information_bits: float = float("nan")
    worst_bit_error: float = float("nan")
    worst_symbol_error: float = float("nan")
    uniform_mutual_information_bits: float = float("nan")
    readout: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    gap_logits: Optional[np.ndarray] = None

    @property
    def objectives(self):
        if not self.trusted:
            return np.full(2, -np.inf)
        return np.array([-math.log10(max(self.bit_error_rate, 1e-30)),
                         self.mutual_information_bits])

    def as_dict(self):
        return {
            "positions": self.positions.tolist(),
            "ber_worst": self.ber_worst,
            "effective_bits": self.effective_bits,
            "uniform_ber": self.uniform_ber,
            "uniform_mutual_information_bits": self.uniform_mutual_information_bits,
            "improvement_factor": self.improvement_factor,
            "trusted": self.trusted,
            "symbol_error_rate": self.symbol_error_rate,
            "bit_error_rate": self.bit_error_rate,
            "mutual_information_bits": self.mutual_information_bits,
            "worst_bit_error": self.worst_bit_error,
            "worst_symbol_error": self.worst_symbol_error,
            "readout": self.readout,
            "validation": self.validation,
            "legacy_field_semantics": {
                "ber_worst": "adjacent_binary_pair_error_diagnostic_not_full_bit_BER",
                "effective_bits": "alias_of_fixed_prior_mutual_information_bits",
                "uniform_ber": "uniform_placement_full_coded_bit_error_rate",
            },
            "search_error_floor": 1e-30,
        }


MIN_GAP_E = 1.5  # minimum inter-level spacing in electrons (survives rounding)


def _gaps_to_positions(z: np.ndarray, budget: float, n_levels: int) -> np.ndarray:
    """Map unconstrained logits to valid sorted positions.

    Gaps are parameterized as min_gap + softmax(z) * slack, which guarantees
    strictly increasing, in-budget positions for ANY z (no rejection needed).
    """
    if not isinstance(n_levels, int) or isinstance(n_levels, bool) or n_levels < 2:
        raise ValueError("n_levels must be an integer >= 2")
    n_gaps = n_levels - 1
    raw = np.asarray(z, dtype=float)
    if raw.shape != (n_gaps,) or not np.all(np.isfinite(raw)):
        raise ValueError("one finite gap logit is required per inter-level gap")
    if not math.isfinite(budget) or budget < MIN_GAP_E * n_gaps:
        raise ValueError("electron budget is insufficient for minimum gap spacing")
    z = np.clip(raw, -30.0, 30.0)
    w = np.exp(z - z.max())
    w /= w.sum()
    gaps = MIN_GAP_E + w * (budget - MIN_GAP_E * n_gaps)
    positions = np.concatenate([[0.0], np.cumsum(gaps)])
    positions[-1] = budget
    return positions


def _pair_ber(pos_lo: float, pos_hi: float, threshold: float,
              config: LevelPlacementConfig) -> float:
    """Equal-prior binary error for a pair; not full K-state coded BER."""
    if not all(math.isfinite(v) for v in (pos_lo, pos_hi, threshold)):
        raise ValueError("pair positions and threshold must be finite")
    lo, hi = int(round(pos_lo)), int(round(pos_hi))
    if not 0 <= lo < hi <= config.n_chain or not 0 <= threshold <= config.n_chain + 1:
        raise ValueError("pair counts and decision boundary must lie in the chain domain")
    decision = int(math.ceil(threshold))
    lower, _ = _retained_count(config.n_chain, lo, config.lam0_per_s,
                                config.mu0_per_s, config.t_retention_s, False)
    upper, _ = _retained_count(config.n_chain, hi, config.lam0_per_s,
                                config.mu0_per_s, config.t_retention_s, False)
    return 0.5 * (float(lower[decision:].sum()) + float(upper[:decision].sum()))


def _evaluate_positions(positions: np.ndarray, config: LevelPlacementConfig):
    counts = np.rint(positions).astype(int)
    readout, validation = electron_storage_readout(
        counts, config.n_chain, config.lam0_per_s, config.mu0_per_s,
        config.t_retention_s, priors=config.priors, codes=config.codewords,
        numerical_upper_boundary=True, overflow_tolerance=config.overflow_tolerance)
    validation["rate_source"] = config.rate_source
    worst_pair = max(_pair_ber(int(lo), int(hi), (int(lo)+int(hi))/2, config)
                     for lo, hi in zip(counts[:-1], counts[1:]))
    return readout, validation, worst_pair


def evaluate_placement(gap_logits: np.ndarray,
                       config: Optional[LevelPlacementConfig] = None) -> LevelPlacementCandidate:
    """Evaluate full decoded errors/information after integer programming."""
    config = config or LevelPlacementConfig()
    positions = _gaps_to_positions(gap_logits, config.total_budget, config.n_levels)
    result, validation, pair = _evaluate_positions(positions, config)
    uniform, uniform_validation, _ = _evaluate_positions(
        np.linspace(0, config.total_budget, config.n_levels), config)
    valid = bool(validation["numerical_valid"] and uniform_validation["numerical_valid"])
    validation["uniform_reference_numerical_valid"] = uniform_validation["numerical_valid"]
    if result.bit_error_rate > 0:
        improvement = uniform.bit_error_rate / result.bit_error_rate
    else:
        improvement = 1.0 if uniform.bit_error_rate == 0 else None
    return LevelPlacementCandidate(
        positions=positions, gap_logits=np.asarray(gap_logits, dtype=float).copy(),
        ber_worst=pair, effective_bits=result.mutual_information_bits,
        uniform_ber=uniform.bit_error_rate, improvement_factor=improvement, trusted=valid,
        symbol_error_rate=result.symbol_error_rate, bit_error_rate=result.bit_error_rate,
        mutual_information_bits=result.mutual_information_bits,
        worst_bit_error=result.worst_bit_error, worst_symbol_error=result.worst_symbol_error,
        uniform_mutual_information_bits=uniform.mutual_information_bits,
        readout=result.as_dict(), validation=validation)


def refine_placement(cand: LevelPlacementCandidate,
                     config: LevelPlacementConfig,
                     rounds: int = 4) -> LevelPlacementCandidate:
    """Coordinate ascent on gap logits.

    The full coded-BER landscape has a ridge structure: both end gaps must
    widen together (bottom suffers constant leak-in, top suffers the pinned
    budget level drifting down). Single-gene mutations climb it slowly, so
    we refine the GA best with per-gap coordinate ascent.
    """
    z = cand.gap_logits.copy()
    best = evaluate_placement(z, config)
    for _ in range(rounds):
        improved = False
        for i in range(len(z)):
            for delta in (0.4, 0.15, 0.05):
                z2 = z.copy()
                z2[i] += delta
                trial = evaluate_placement(z2, config)
                if trial.trusted and trial.bit_error_rate < best.bit_error_rate * (1.0 - 1e-3):
                    best = trial
                    z = z2
                    improved = True
        if not improved:
            break
    return best


def evolve_placement(config=None, pop=20, gen=10, seed=0):
    """Optimize level placement using NSGA-II over gap logits."""
    config = config or LevelPlacementConfig()
    if not isinstance(pop, int) or pop < 2 or not isinstance(gen, int) or gen < 0:
        raise ValueError("population must be >= 2 and generations >= 0")
    rng = random.Random(seed)
    K = config.n_levels
    n_vars = K - 1  # gap logits (softmax → inter-level spacings)

    def random_z():
        # Small random perturbations around uniform (z=0)
        return np.array([rng.gauss(0.0, 1.0) for _ in range(n_vars)])

    def mutate(parent_z):
        child = parent_z.copy()
        # Per-gene gaussian mutation on logits
        for i in range(n_vars):
            child[i] += rng.gauss(0.0, config.mutation_sigma * 10.0)
        # Occasional coordinated 2-gene jump (helps climb end-gap ridges)
        if rng.random() < 0.25 and n_vars > 2:
            a, b = rng.sample(range(n_vars), 2)
            child[a] += rng.gauss(0.0, 1.5)
            child[b] += rng.gauss(0.0, 1.5)
        return child

    def evaluate_z(z):
        return evaluate_placement(z, config)

    # Seed with uniform baseline so the known reference is always in the pool
    population = [evaluate_z(np.zeros(n_vars))]
    population += [evaluate_z(random_z()) for _ in range(pop - 1)]

    for _ in range(gen):
        # Tournament selection + mutation, then elitist replacement
        objs = np.vstack([c.objectives for c in population])
        fronts = _non_dominated_fronts(objs)
        rank = np.empty(len(population), dtype=int)
        crowd = np.zeros(len(population))
        for r, front in enumerate(fronts):
            for i in front:
                rank[i] = r
            fc = _crowding(objs[front])
            for li, i in enumerate(front):
                crowd[i] = fc[li]
        children = []
        while len(children) < pop:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                winner = i
            else:
                winner = j
            child_z = mutate(population[winner].gap_logits)
            child = evaluate_z(child_z)
            child.gap_logits = child_z
            children.append(child)
        # Elitism: merge parents + children, keep best pop by (rank, crowd)
        pool = list(population) + children
        objs = np.vstack([c.objectives for c in pool])
        fronts = _non_dominated_fronts(objs)
        scored = []
        for r, front in enumerate(fronts):
            fc = _crowding(objs[front])
            for li, i in enumerate(front):
                scored.append((r, -fc[li], i))
        scored.sort()
        population = [pool[i] for _, _, i in scored[:pop]]

    objs = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objs)
    front = [population[i] for i in fronts[0] if population[i].trusted]
    # Coordinate-ascent refinement of the best-BER front member
    seed_best = min(front, key=lambda c: c.bit_error_rate) if front else population[0]
    refined = refine_placement(seed_best, config)
    if refined.trusted and refined.bit_error_rate <= seed_best.bit_error_rate:
        front = [refined] + front
    return {"front": front, "population": population}


def discover_optimal_placement():
    """Regenerate a model-only search using fixed-code BER and information."""
    print("Finite-count storage placement: coded BER and fixed-prior mutual information")
    print("Numerical model acceptance does not validate default material rates")
    results = {}
    for k in (4, 8, 16, 32):
        config = LevelPlacementConfig(n_levels=k, total_budget=200)
        result = evolve_placement(config, pop=30, gen=25, seed=20260922)
        if not result["front"]:
            continue
        best = min(result["front"], key=lambda c: c.bit_error_rate)
        uniform = evaluate_placement(np.zeros(k-1), config)
        print(f"K={k}: uniform coded BER={uniform.bit_error_rate:.4e}, "
              f"best={best.bit_error_rate:.4e}, I(X;Y)={best.mutual_information_bits:.4f} bits")
        results[k] = {"uniform": uniform.as_dict(), "optimal": best.as_dict(),
                      "improvement_factor": best.improvement_factor}
    return results


if __name__ == "__main__":
    discover_optimal_placement()
