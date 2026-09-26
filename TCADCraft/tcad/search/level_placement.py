"""Optimal non-uniform multi-level storage placement (TCADCraft-unique discovery).

Problem: Given a storage cell with known electron disturb statistics, find
the OPTIMAL placement of K storage levels within a fixed electron budget
that minimizes the worst-pair bit-error rate.

This is a problem ONLY TCADCraft can solve:
- Requires M3 BirthDeathChain (exact electron-count statistics)
- Requires design-space optimization (NSGA-II over level positions)
- Sentaurus has no probabilistic BER output

Novel contribution: Existing multi-level storage uses either uniform
spacing or ad-hoc placement. This module finds the OPTIMAL non-uniform
placement from first-principles electron statistics.

Design variables:
  level_positions: (n_levels-1) continuous variables defining where
    each storage level sits within [0, total_budget]
  (levels are sorted; first=0, last=total_budget by convention)

Objectives:
  1. Minimize worst-pair BER (most confused adjacent pair)
  2. Maximize effective bits = K * (1 - BER_worst)
  3. Minimize total electron budget (power/area proxy)

Key comparison: uniform vs optimal placement BER for same K and budget.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts

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


@dataclass
class LevelPlacementCandidate:
    positions: np.ndarray                # sorted level positions [0, budget]
    ber_worst: float = float("nan")
    effective_bits: float = float("nan")
    uniform_ber: float = float("nan")
    improvement_factor: float = float("nan")
    trusted: bool = False

    @property
    def objectives(self):
        if not self.trusted:
            return np.array([float("-inf")] * 2)
        return np.array([
            -math.log10(max(self.ber_worst, 1e-30)),  # -log10(BER)
            self.effective_bits,
        ])

    def as_dict(self):
        return {
            "positions": self.positions.tolist(),
            "ber_worst": self.ber_worst,
            "effective_bits": self.effective_bits,
            "uniform_ber": self.uniform_ber,
            "improvement_factor": self.improvement_factor,
            "trusted": float(self.trusted),
        }


MIN_GAP_E = 1.5  # minimum inter-level spacing in electrons (survives rounding)


def _gaps_to_positions(z: np.ndarray, budget: float, n_levels: int) -> np.ndarray:
    """Map unconstrained logits to valid sorted positions.

    Gaps are parameterized as min_gap + softmax(z) * slack, which guarantees
    strictly increasing, in-budget positions for ANY z (no rejection needed).
    """
    n_gaps = n_levels - 1
    z = np.clip(np.asarray(z, dtype=float), -30.0, 30.0)
    w = np.exp(z - z.max())
    w = w / w.sum()
    slack = budget - MIN_GAP_E * n_gaps
    gaps = MIN_GAP_E + w * slack
    return np.concatenate([[0.0], np.cumsum(gaps)])


def _pair_ber(pos_lo: float, pos_hi: float, threshold: float,
              config: LevelPlacementConfig) -> float:
    """BER for one adjacent pair using BirthDeathChain."""
    from ..physics.electron_counting import BirthDeathChain
    chain = BirthDeathChain(
        n_max=config.n_chain,
        capture_rate=lambda n: config.lam0_per_s,
        emission_rate=lambda n: config.mu0_per_s * n,
    )
    # Lower level
    chain.initialize(count=int(round(pos_lo)))
    chain.advance(config.t_retention_s)
    p_read_hi_lo = float(np.sum(chain.state[int(np.ceil(threshold)):]))
    # Upper level
    chain.initialize(count=int(round(pos_hi)))
    chain.advance(config.t_retention_s)
    p_read_lo_hi = float(np.sum(chain.state[:int(np.floor(threshold))]))
    return 0.5 * (p_read_hi_lo + p_read_lo_hi)


def evaluate_placement(gap_logits: np.ndarray,
                       config: Optional[LevelPlacementConfig] = None) -> LevelPlacementCandidate:
    """Evaluate a level placement given unconstrained gap logits."""
    config = config or LevelPlacementConfig()
    K = config.n_levels
    budget = config.total_budget
    pos = _gaps_to_positions(gap_logits, budget, K)

    cand = LevelPlacementCandidate(positions=pos)
    cand.gap_logits = np.asarray(gap_logits, dtype=float).copy()

    # Compute BER for each adjacent pair
    worst = 0.0
    for k in range(K - 1):
        threshold = 0.5 * (pos[k] + pos[k+1])
        ber = _pair_ber(pos[k], pos[k+1], threshold, config)
        worst = max(worst, ber)

    # Uniform placement for comparison
    uniform_pos = np.linspace(0, budget, K)
    uniform_worst = 0.0
    for k in range(K - 1):
        threshold = 0.5 * (uniform_pos[k] + uniform_pos[k+1])
        ber = _pair_ber(uniform_pos[k], uniform_pos[k+1], threshold, config)
        uniform_worst = max(uniform_worst, ber)

    cand.ber_worst = worst
    cand.uniform_ber = uniform_worst
    cand.improvement_factor = uniform_worst / max(worst, 1e-30)
    cand.effective_bits = K * math.log2(K) * (1 - worst) / math.log2(K) if worst < 1 else 0
    # Simpler: effective_bits = K * (1 - worst) / K * log2(K) = (1-worst)*log2(K)
    cand.effective_bits = (1 - worst) * math.log2(K)
    cand.trusted = np.isfinite(worst) and np.isfinite(uniform_worst)
    return cand


def refine_placement(cand: LevelPlacementCandidate,
                     config: LevelPlacementConfig,
                     rounds: int = 4) -> LevelPlacementCandidate:
    """Coordinate ascent on gap logits.

    The worst-pair-BER landscape has a ridge structure: both end gaps must
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
                if trial.ber_worst < best.ber_worst * (1.0 - 1e-3):
                    best = trial
                    z = z2
                    improved = True
        if not improved:
            break
    return best


def evolve_placement(config=None, pop=20, gen=10, seed=0):
    """Optimize level placement using NSGA-II over gap logits."""
    config = config or LevelPlacementConfig()
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
    seed_best = min(front, key=lambda c: c.ber_worst) if front else population[0]
    refined = refine_placement(seed_best, config)
    if refined.ber_worst <= seed_best.ber_worst:
        front = [refined] + front
    return {"front": front, "population": population}


def discover_optimal_placement():
    """Main discovery: find optimal placement for various K and compare."""
    print("=" * 70)
    print("TCADCRAFT-UNIQUE DISCOVERY: Optimal Multi-Level Storage Placement")
    print("Using M3 BirthDeathChain (electron counting statistics)")
    print("=" * 70)

    results = {}
    for K in (4, 8, 16, 32):
        config = LevelPlacementConfig(n_levels=K, total_budget=200.0)
        result = evolve_placement(config, pop=30, gen=25, seed=20260922)
        front = result["front"]
        if not front:
            print(f"\nK={K}: no valid placement found")
            continue

        best = min(front, key=lambda c: c.ber_worst)
        # Uniform reference: zero logits → equal gaps
        uniform = evaluate_placement(np.zeros(K - 1), config)

        print(f"\nK={K} levels (budget={config.total_budget:.0f} electrons):")
        print(f"  Uniform:   BER = {uniform.ber_worst:.4e}  "
              f"eff_bits = {uniform.effective_bits:.2f}")
        print(f"  Optimal:   BER = {best.ber_worst:.4e}  "
              f"eff_bits = {best.effective_bits:.2f}")
        print(f"  Improvement: {best.improvement_factor:.1f}x lower BER")
        print(f"  Positions: {[f'{p:.1f}' for p in best.positions]}")

        results[K] = {
            "uniform": uniform.as_dict(),
            "optimal": best.as_dict(),
            "improvement_factor": best.improvement_factor,
        }

    # Grand summary
    print("\n" + "=" * 70)
    print("DISCOVERY SUMMARY")
    print("=" * 70)
    print(f"{'K':>4s} {'Uniform BER':>12s} {'Optimal BER':>12s} "
          f"{'Improvement':>12s} {'Positions':>30s}")
    print("-" * 70)
    for K, r in sorted(results.items()):
        print(f"{K:4d} {r['uniform']['ber_worst']:12.4e} "
              f"{r['optimal']['ber_worst']:12.4e} "
              f"{r['improvement_factor']:11.1f}x "
              f"{'[' + ','.join(f'{p:.0f}' for p in r['optimal']['positions']) + ']':>30s}")

    # Key finding
    best_improvement = max(r["improvement_factor"] for r in results.values())
    print(f"\nKEY FINDING: Non-uniform placement reduces worst-pair BER by "
          f"up to {best_improvement:.0f}x compared to uniform placement.")
    print(f"This is achievable WITHOUT increasing the electron budget.")
    print(f"Result is from exact master-equation statistics (not Gaussian approx).")

    return results


if __name__ == "__main__":
    discover_optimal_placement()
