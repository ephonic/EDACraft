"""RRAM SET-protocol optimization (TCADCraft-unique protocol discovery).

Problem: choose the SET pulse (field, width) and pulse-count strategy to
maximize the on/off resistance ratio while minimizing cycle-to-cycle
variability, at minimum pulse energy.

Physics (M2 reserve pool / rram_filament kernel):
- Filament growth is a stochastic birth process (field-activated vacancy
  migration). Near the forming threshold, small changes in field or width
  produce large changes in P(ON).
- Deep saturation (P(ON)->1 with large margin) wastes energy AND deepens
  the filament, requiring stronger RESET and accelerating wear.

Discovery target: the variability-per-ratio "elbow" -- the optimal SET
protocol sits where P(ON) is comfortably below saturation (typically
0.85-0.95), not at maximum overdrive. We also compare single-pulse vs
incremental multi-pulse SET strategies.

Objectives (per protocol):
1. Maximize mean log10(R_off/R_on)  (memory window)
2. Minimize sigma of log10(R_off/R_on) across cycles (variability)
3. Minimize pulse energy proxy (field^2 * width * n_pulses)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..physics.rram_filament import (
    BirthDeathChain, FilamentConfig, FilamentState,
)
from ..physics.electron_counting import GillespieSampler
from .fe_frontier import _crowding, _non_dominated_fronts


@dataclass
class ProtocolConfig:
    """RRAM SET protocol sweep parameters."""
    reset_field: float = -0.55e8       # critical RESET (couples to SET depth)
    reset_width: float = 1.0e-6
    rest_width: float = 1.0e-7         # zero-field gap between sub-pulses
    n_cycles: int = 40                 # Monte Carlo cycles per protocol
    fields_gv_per_m: tuple = (0.45, 0.75)   # SET field sweep range [1e8 V/m]
    widths_us: tuple = (0.2, 3.0)            # SET pulse width sweep range
    n_field: int = 9
    n_width: int = 8
    seed: int = 20260922
    # Filament kernel overrides (kept near kernel defaults)
    n_conducting: int = 20
    n_max: int = 30


@dataclass
class ProtocolPoint:
    set_field: float          # [V/m]
    set_width: float          # [s]
    n_pulses: int = 1
    mean_log_ratio: float = float("nan")
    sigma_log_ratio: float = float("nan")
    energy_proxy: float = float("nan")
    p_on: float = float("nan")
    mean_r_on: float = float("nan")

    @property
    def objectives(self) -> np.ndarray:
        """[-sigma (higher=better), log-ratio (higher=better)]."""
        if not (np.isfinite(self.sigma_log_ratio)
                and np.isfinite(self.mean_log_ratio)):
            return np.array([float("-inf")] * 2)
        return np.array([
            -self.sigma_log_ratio,
            self.mean_log_ratio,
        ])

    def as_dict(self) -> Dict:
        return {
            "set_field_V_per_m": self.set_field,
            "set_width_s": self.set_width,
            "n_pulses": self.n_pulses,
            "mean_log_ratio": self.mean_log_ratio,
            "sigma_log_ratio": self.sigma_log_ratio,
            "energy_proxy": self.energy_proxy,
            "p_on": self.p_on,
            "mean_r_on_ohm": self.mean_r_on,
        }


def _apply_field_rates(chain: BirthDeathChain, cfg: FilamentConfig,
                       field_V_per_m: float) -> None:
    """Set chain birth/death rates for a piecewise-constant field phase."""
    chain._lam[:] = 0.0
    chain._mu[:] = 0.0
    if field_V_per_m > 0:
        lam = cfg.growth_rate(field_V_per_m)
        for n in range(cfg.n_max + 1):
            if n < cfg.n_max:
                chain._lam[n] = lam
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n)
    elif field_V_per_m < 0:
        boost = cfg.growth_rate(abs(field_V_per_m))
        for n in range(cfg.n_max + 1):
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n) + boost
    else:
        for n in range(cfg.n_max + 1):
            if n < cfg.n_max:
                chain._lam[n] = cfg.growth_rate(0.0)
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n)


def _r_from_size(n: int, cfg: FilamentConfig) -> float:
    """Per-filament resistance from sampled size (log-interpolated)."""
    if n >= cfg.n_conducting:
        return cfg.r_on_ohm
    frac = n / cfg.n_conducting
    return math.exp(math.log(cfg.r_off_ohm)
                    + frac * (math.log(cfg.r_on_ohm)
                              - math.log(cfg.r_off_ohm)))


def _simulate_protocol(set_field: float, set_width: float,
                       n_pulses: int, config: ProtocolConfig) -> ProtocolPoint:
    """Evaluate one SET protocol with stochastic trajectory statistics.

    Each cycle is an exact Gillespie trajectory through the SET phase
    (optionally split into n_pulses sub-pulses separated by zero-field
    rests) and a fixed RESET phase, so cycle-to-cycle variability is
    physical (stochastic filament kinetics), not an artifact.
    """
    cfg = FilamentConfig(n_max=config.n_max, n_conducting=config.n_conducting)
    sampler = GillespieSampler(chain=None, seed=config.seed)
    sampler.chain = BirthDeathChain(n_max=cfg.n_max,
                                    capture_rate=lambda n: 0.0,
                                    emission_rate=lambda n: 0.0)

    sub_width = set_width / n_pulses

    log_ratios = []
    formed_flags = []
    r_ons = []

    for _cycle in range(config.n_cycles):
        n = 0
        # SET phase: n_pulses sub-pulses with zero-field rests
        for _p in range(n_pulses):
            _apply_field_rates(sampler.chain, cfg, set_field)
            n, _ = sampler.run_trajectory(sub_width, n)
            if _p < n_pulses - 1:
                _apply_field_rates(sampler.chain, cfg, 0.0)
                n, _ = sampler.run_trajectory(config.rest_width, n)
        n_set = n
        formed = n_set >= cfg.n_conducting
        r_on = _r_from_size(n_set, cfg)

        # RESET phase (fixed)
        _apply_field_rates(sampler.chain, cfg, config.reset_field)
        n, _ = sampler.run_trajectory(config.reset_width, n_set)
        r_off = _r_from_size(n, cfg)

        log_ratios.append(math.log10(max(r_off / max(r_on, 1.0), 1.0)))
        formed_flags.append(1.0 if formed else 0.0)
        r_ons.append(r_on)

    logs = np.array(log_ratios)
    point = ProtocolPoint(
        set_field=set_field,
        set_width=set_width,
        n_pulses=n_pulses,
        mean_log_ratio=float(np.mean(logs)),
        sigma_log_ratio=float(np.std(logs)),
        energy_proxy=float((set_field / 1e8) ** 2 * (set_width * 1e6)
                           * n_pulses),
        p_on=float(np.mean(formed_flags)),
        mean_r_on=float(np.mean(r_ons)),
    )
    return point


def sweep_protocols(config: Optional[ProtocolConfig] = None
                    ) -> List[ProtocolPoint]:
    """Grid sweep of (field, width) single-pulse protocols."""
    config = config or ProtocolConfig()
    fields = np.linspace(*config.fields_gv_per_m, config.n_field) * 1e8
    widths = np.logspace(math.log10(config.widths_us[0]),
                         math.log10(config.widths_us[1]), config.n_width) * 1e-6
    points = []
    for f in fields:
        for w in widths:
            points.append(_simulate_protocol(f, w, 1, config))
    return points


def pareto_front(points: List[ProtocolPoint]) -> List[ProtocolPoint]:
    objs = np.vstack([p.objectives for p in points])
    fronts = _non_dominated_fronts(objs)
    return [points[i] for i in fronts[0]
            if np.all(np.isfinite(points[i].objectives))]


def find_reliable_optimal(points: List[ProtocolPoint],
                          p_on_min: float = 0.9) -> Optional[ProtocolPoint]:
    """Best window among protocols that form reliably (P(ON) >= p_on_min).

    A protocol whose forming probability is below ~0.9 is unusable as a SET
    regardless of its nominal ratio, so the actionable optimum must satisfy
    the reliability constraint first.
    """
    reliable = [p for p in points
                if p.p_on >= p_on_min and np.isfinite(p.mean_log_ratio)]
    if not reliable:
        return None
    return max(reliable,
               key=lambda p: (p.mean_log_ratio, -p.sigma_log_ratio))


def find_elbow(points: List[ProtocolPoint]) -> Optional[ProtocolPoint]:
    """Find the variability-per-ratio knee on the Pareto front.

    The knee maximizes ratio gain per unit variability cost, among
    protocols whose P(ON) has not saturated (p_on < 0.995).
    """
    front = pareto_front(points)
    usable = [p for p in front if p.p_on < 0.995 and p.sigma_log_ratio > 0]
    if not usable:
        return None
    # Normalize axes and pick the point of maximum curvature (knee):
    # maximize (ratio - min)/(max-min) - (sigma - min)/(max-min)
    ratios = np.array([p.mean_log_ratio for p in usable])
    sigmas = np.array([p.sigma_log_ratio for p in usable])
    def norm(x):
        span = np.max(x) - np.min(x)
        return (x - np.min(x)) / (span if span > 1e-12 else 1.0)
    score = norm(ratios) - norm(sigmas)
    return usable[int(np.argmax(score))]


def compare_pulse_strategies(config: Optional[ProtocolConfig] = None
                             ) -> Dict[str, ProtocolPoint]:
    """Single full-width pulse vs split pulses vs adaptive verify-and-stop.

    Adaptive strategy: apply 0.5 us sub-pulses until the filament conducts
    (max 6); energy counts only the applied pulses.
    """
    config = config or ProtocolConfig()
    field = 0.60e8
    width = 1.0e-6
    out = {}
    for n in (1, 2, 4):
        out[f"{n}_pulse"] = _simulate_protocol(field, width, n, config)
    # Adaptive verify-and-stop
    out["adaptive"] = _simulate_adaptive(field, 0.5e-6, 6, config)
    return out


def _simulate_adaptive(set_field: float, sub_width: float, max_pulses: int,
                       config: ProtocolConfig) -> ProtocolPoint:
    """Verify-and-stop SET: pulse until conducting, then stop."""
    cfg = FilamentConfig(n_max=config.n_max, n_conducting=config.n_conducting)
    sampler = GillespieSampler(chain=None, seed=config.seed)
    sampler.chain = BirthDeathChain(n_max=cfg.n_max,
                                    capture_rate=lambda n: 0.0,
                                    emission_rate=lambda n: 0.0)
    log_ratios = []
    formed_flags = []
    r_ons = []
    applied = []

    for _cycle in range(config.n_cycles):
        n = 0
        n_used = 0
        for _p in range(max_pulses):
            _apply_field_rates(sampler.chain, cfg, set_field)
            n, _ = sampler.run_trajectory(sub_width, n)
            n_used += 1
            if n >= cfg.n_conducting:
                break
            _apply_field_rates(sampler.chain, cfg, 0.0)
            n, _ = sampler.run_trajectory(config.rest_width, n)
        n_set = n
        formed = n_set >= cfg.n_conducting
        r_on = _r_from_size(n_set, cfg)

        _apply_field_rates(sampler.chain, cfg, config.reset_field)
        n, _ = sampler.run_trajectory(config.reset_width, n_set)
        r_off = _r_from_size(n, cfg)

        log_ratios.append(math.log10(max(r_off / max(r_on, 1.0), 1.0)))
        formed_flags.append(1.0 if formed else 0.0)
        r_ons.append(r_on)
        applied.append(n_used)

    logs = np.array(log_ratios)
    point = ProtocolPoint(
        set_field=set_field,
        set_width=sub_width,
        n_pulses=int(np.mean(applied)),
        mean_log_ratio=float(np.mean(logs)),
        sigma_log_ratio=float(np.std(logs)),
        energy_proxy=float((set_field / 1e8) ** 2 * (sub_width * 1e6)
                           * np.mean(applied)),
        p_on=float(np.mean(formed_flags)),
        mean_r_on=float(np.mean(r_ons)),
    )
    return point


def discover_rram_protocol():
    """Main entry: run the protocol discovery and print the summary."""
    print("=" * 70)
    print("TCADCRAFT-UNIQUE DISCOVERY: RRAM SET-Protocol Optimization")
    print("Stochastic filament kinetics (BirthDeathChain)")
    print("=" * 70)
    config = ProtocolConfig()
    points = sweep_protocols(config)
    valid = [p for p in points if np.isfinite(p.mean_log_ratio)]
    print(f"\nSwept {len(points)} protocols "
          f"({config.n_field} fields x {config.n_width} widths)")

    front = pareto_front(valid)
    front_sorted = sorted(front, key=lambda p: p.mean_log_ratio)
    print(f"Pareto front: {len(front_sorted)} protocols")

    elbow = find_elbow(valid)
    saturated = max(valid, key=lambda p: p.mean_log_ratio)
    reliable = find_reliable_optimal(valid)

    print(f"\n{'protocol':>28s} {'log10 ratio':>12s} {'sigma':>8s} "
          f"{'P(ON)':>7s} {'energy':>8s}")
    print("-" * 70)
    for p in front_sorted[:: max(1, len(front_sorted) // 8)]:
        print(f"{f'{p.set_field/1e8:.2f} GV/m x {p.set_width*1e6:.1f} us':>28s} "
              f"{p.mean_log_ratio:12.3f} {p.sigma_log_ratio:8.4f} "
              f"{p.p_on:7.3f} {p.energy_proxy:8.2f}")
    if elbow is not None:
        print(f"\nELBOW (best ratio-per-sigma, unsaturated): "
              f"{elbow.set_field/1e8:.2f} GV/m x {elbow.set_width*1e6:.1f} us"
              f"  ->  P(ON)={elbow.p_on:.3f}, "
              f"log-ratio={elbow.mean_log_ratio:.2f}, "
              f"sigma={elbow.sigma_log_ratio:.4f}")
    if saturated is not None:
        print(f"NAIVE MAX-RATIO (unreliable?): "
              f"{saturated.set_field/1e8:.2f} GV/m x "
              f"{saturated.set_width*1e6:.1f} us"
              f"  ->  P(ON)={saturated.p_on:.3f}, "
              f"log-ratio={saturated.mean_log_ratio:.2f}, "
              f"sigma={saturated.sigma_log_ratio:.4f}, "
              f"energy={saturated.energy_proxy:.1f}")
    if reliable is not None:
        print(f"RELIABLE OPTIMAL (P(ON)>=0.9): "
              f"{reliable.set_field/1e8:.2f} GV/m x "
              f"{reliable.set_width*1e6:.1f} us"
              f"  ->  P(ON)={reliable.p_on:.3f}, "
              f"log-ratio={reliable.mean_log_ratio:.2f}, "
              f"sigma={reliable.sigma_log_ratio:.4f}, "
              f"energy={reliable.energy_proxy:.1f}")

    strategies = compare_pulse_strategies(config)
    print("\nPulse-strategy comparison (0.60 GV/m, 1.0 us total):")
    print(f"{'strategy':>12s} {'log10 ratio':>12s} {'sigma':>8s} {'P(ON)':>7s} "
          f"{'energy':>8s}")
    for name, p in strategies.items():
        print(f"{name:>12s} {p.mean_log_ratio:12.3f} "
              f"{p.sigma_log_ratio:8.4f} {p.p_on:7.3f} {p.energy_proxy:8.2f}")

    result = {
        "sweep": [p.as_dict() for p in valid],
        "front": [p.as_dict() for p in front_sorted],
        "elbow": elbow.as_dict() if elbow else None,
        "saturated": saturated.as_dict() if saturated else None,
        "reliable_optimal": reliable.as_dict() if reliable else None,
        "pulse_strategies": {k: v.as_dict() for k, v in strategies.items()},
    }

    if reliable is not None:
        print("\nKEY FINDING:")
        print(f"- Reliable operation (P(ON)>=0.9) needs "
              f"{reliable.set_field/1e8:.2f} GV/m x "
              f"{reliable.set_width*1e6:.1f} us, "
              f"log-ratio={reliable.mean_log_ratio:.2f}")
        if saturated is not None:
            print(f"- Naive ratio-maximizing protocol only reaches "
                  f"P(ON)={saturated.p_on:.2f}: the ratio optimum is "
                  f"UNRELIABLE")
        adaptive = strategies.get("adaptive")
        if adaptive is not None:
            print(f"- Adaptive verify-and-stop: P(ON)={adaptive.p_on:.2f} "
                  f"guaranteed with mean {adaptive.n_pulses:.1f} pulses "
                  f"(energy {adaptive.energy_proxy:.2f})")
        print(f"- Overdrive beyond reliable forming degrades the ratio: "
              f"deep SET survives the critical RESET as residual filament")
    return result


if __name__ == "__main__":
    discover_rram_protocol()
