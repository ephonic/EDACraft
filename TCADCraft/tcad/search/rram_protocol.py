"""RRAM protocol exploration with explicit proxy costs and sampled readout.

Three objectives: window, dispersion and total cost proxy. Proxy costs are
normalized field-squared times duration plus declared read/driver overhead;
they are not joules. Cycles carry RESET residue by default. No calibrated
wear, thermal RESET or experimental reliability claim is provided.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from ..physics.rram_filament import (
    BirthDeathChain, FilamentConfig, filament_resistance, set_filament_rates,
)
from ..physics.electron_counting import GillespieSampler
from .fe_frontier import _non_dominated_fronts


@dataclass
class ProtocolConfig:
    reset_field: float = -0.55e8
    reset_width: float = 1e-6
    rest_width: float = 1e-7
    n_cycles: int = 40
    fields_gv_per_m: tuple = (0.45, 0.75)  # Historical name; values multiply 1e8 V/m.
    widths_us: tuple = (0.2, 3.0)
    n_field: int = 9
    n_width: int = 8
    seed: int = 20260922
    n_conducting: int = 20
    n_max: int = 30
    read_noise_log10_std: float = 0.0  # Explicit noiseless measurement limit.
    verify_threshold_ohm: Optional[float] = None
    read_width: float = 0.0
    read_cost_proxy: float = 0.0
    driver_cost_proxy_per_pulse: float = 0.0
    independent_trials: bool = False

    def __post_init__(self) -> None:
        for name in ("n_cycles", "n_field", "n_width", "n_max", "n_conducting"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.n_conducting > self.n_max:
            raise ValueError("n_conducting must not exceed n_max")
        for name in ("reset_width", "rest_width", "read_width", "read_noise_log10_std",
                     "read_cost_proxy", "driver_cost_proxy_per_pulse"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if not math.isfinite(self.reset_field):
            raise ValueError("reset_field must be finite")
        if self.verify_threshold_ohm is not None and (
            not math.isfinite(self.verify_threshold_ohm) or self.verify_threshold_ohm <= 0
        ):
            raise ValueError("verify_threshold_ohm must be finite and > 0")
        for name in ("fields_gv_per_m", "widths_us"):
            values = getattr(self, name)
            if (len(values) != 2 or any(not math.isfinite(v) or v <= 0 for v in values)
                    or values[1] < values[0]):
                raise ValueError(f"{name} must be a positive increasing range")
        if not isinstance(self.independent_trials, bool):
            raise ValueError("independent_trials must be boolean")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")


@dataclass
class ProtocolPoint:
    set_field: float
    set_width: float  # Total SET time budget per cycle, including adaptive protocols.
    n_pulses: float = 1.0  # Mean actually applied pulse count.
    mean_log_ratio: float = float("nan")
    sigma_log_ratio: float = float("nan")
    energy_proxy: float = float("nan")
    p_on: float = float("nan")
    mean_r_on: float = float("nan")
    p_success: float = float("nan")
    set_cost_proxy: float = 0.0
    reset_cost_proxy: float = 0.0
    read_cost_proxy: float = 0.0
    driver_cost_proxy: float = 0.0
    mean_set_time_s: float = 0.0
    mean_elapsed_time_s: float = 0.0
    total_elapsed_time_s: float = 0.0
    max_pulses: int = 1
    n_trials: int = 0
    n_success: int = 0
    failure_probability_upper95: Optional[float] = None
    sample_mode: str = "unavailable"
    failures: Dict[str, int] = field(default_factory=dict)
    cycle_samples: List[Dict] = field(default_factory=list)
    read_noise_log10_std: float = 0.0
    verify_threshold_ohm: float = float("nan")

    @property
    def objectives(self) -> np.ndarray:
        """Maximize [-dispersion, window, -total cost proxy]."""
        if (not all(np.isfinite(v) for v in
                    (self.sigma_log_ratio, self.mean_log_ratio, self.energy_proxy))
                or self.sigma_log_ratio < 0 or self.energy_proxy < 0):
            return np.full(3, -np.inf)
        return np.array([-self.sigma_log_ratio, self.mean_log_ratio, -self.energy_proxy])

    def as_dict(self) -> Dict:
        return {
            **self.__dict__,
            "set_field_V_per_m": self.set_field,
            "set_width_s": self.set_width,
            "mean_r_on_ohm": self.mean_r_on,
            "cost_unit": "normalized_proxy_not_joule",
            "damage_model": "unavailable",
            "read_model": "log10_resistance_plus_gaussian_noise",
            "completed": True,
        }


def _apply_field_rates(chain: BirthDeathChain, cfg: FilamentConfig,
                       field_V_per_m: float) -> None:
    set_filament_rates(chain, cfg, field_V_per_m)


def _r_from_size(n: int, cfg: FilamentConfig) -> float:
    return filament_resistance(n, cfg)


def _observe_log_resistance(n: int, cfg: FilamentConfig,
                            noise: float, rng: np.random.Generator) -> float:
    """Controller input; it does not expose the latent filament count."""
    value = math.log10(_r_from_size(n, cfg))
    return value + (float(rng.normal(0.0, noise)) if noise else 0.0)


def _run_protocol(set_field: float, sub_width: float, max_pulses: int,
                  config: ProtocolConfig, adaptive: bool) -> ProtocolPoint:
    if not math.isfinite(set_field) or set_field <= 0:
        raise ValueError("SET field must be finite and > 0")
    if not math.isfinite(sub_width) or sub_width <= 0:
        raise ValueError("SET pulse width must be finite and > 0")
    if not isinstance(max_pulses, int) or isinstance(max_pulses, bool) or max_pulses < 1:
        raise ValueError("pulse count must be a positive integer")
    cfg = FilamentConfig(n_max=config.n_max, n_conducting=config.n_conducting)
    chain = BirthDeathChain(n_max=cfg.n_max, capture_rate=lambda n: 0,
                           emission_rate=lambda n: 0)
    sampler = GillespieSampler(chain=chain, seed=config.seed)
    read_rng = np.random.default_rng(np.random.SeedSequence([config.seed, 1]))
    threshold = (config.verify_threshold_ohm if config.verify_threshold_ohm is not None
                 else 1.05 * cfg.r_on_ohm)
    samples = []
    failures = dict(set_failed=0, reset_failed=0, inverted_window=0,
                    false_positive_verify=0)
    n = 0
    for _ in range(config.n_cycles):
        if config.independent_trials:
            n = 0
        initial = n
        used = reads = rests = 0
        observations = []
        stopped = False
        for pulse in range(max_pulses):
            _apply_field_rates(chain, cfg, set_field)
            n, _ = sampler.run_trajectory(sub_width, n)
            used += 1
            if adaptive or pulse == max_pulses - 1:
                if config.read_width > 0:
                    _apply_field_rates(chain, cfg, 0.0)
                    n, _ = sampler.run_trajectory(config.read_width, n)
                reads += 1
                y = _observe_log_resistance(n, cfg, config.read_noise_log10_std, read_rng)
                observations.append(y)
                stopped = adaptive and y <= math.log10(threshold)
                if stopped:
                    break
            if pulse < max_pulses - 1 and config.rest_width > 0:
                _apply_field_rates(chain, cfg, 0.0)
                n, _ = sampler.run_trajectory(config.rest_width, n)
                rests += 1
        n_set = n
        r_on = _r_from_size(n, cfg)
        _apply_field_rates(chain, cfg, config.reset_field)
        if config.reset_width > 0:
            n, _ = sampler.run_trajectory(config.reset_width, n)
        if config.read_width > 0:
            _apply_field_rates(chain, cfg, 0.0)
            n, _ = sampler.run_trajectory(config.read_width, n)
        reads += 1  # RESET readout for both strategies.
        r_off = _r_from_size(n, cfg)
        ratio = r_off / r_on
        formed = n_set >= cfg.n_conducting
        reset_ok = n < cfg.n_conducting
        failures["set_failed"] += int(not formed)
        failures["reset_failed"] += int(not reset_ok)
        failures["inverted_window"] += int(ratio < 1)
        failures["false_positive_verify"] += int(stopped and not formed)
        duration = (used * sub_width + rests * config.rest_width
                    + reads * config.read_width + config.reset_width)
        samples.append(dict(initial_count=initial, set_count=n_set, reset_count=n,
                            ratio=ratio, log_ratio=math.log10(ratio), r_on_ohm=r_on,
                            formed=formed, success=formed and reset_ok and ratio > 1,
                            applied_pulses=used, read_count=reads, rest_count=rests,
                            elapsed_time_s=duration, set_time_s=used * sub_width,
                            verify_stopped=stopped, observed_log_resistance=observations))
    logs = np.array([s["log_ratio"] for s in samples])
    n_success = sum(s["success"] for s in samples)
    upper95 = None
    if config.independent_trials:
        from scipy.stats import beta
        failed = config.n_cycles - n_success
        upper95 = (1.0 if failed == config.n_cycles else
                   float(beta.ppf(0.95, failed + 1, n_success)))
    applied = float(np.mean([s["applied_pulses"] for s in samples]))
    set_time = applied * sub_width
    set_cost = (set_field / 1e8) ** 2 * set_time * 1e6
    reset_cost = (config.reset_field / 1e8) ** 2 * config.reset_width * 1e6
    read_cost = config.read_cost_proxy * float(np.mean([s["read_count"] for s in samples]))
    driver_cost = config.driver_cost_proxy_per_pulse * (applied + int(config.reset_width > 0))
    total_time = math.fsum(s["elapsed_time_s"] for s in samples)
    return ProtocolPoint(
        set_field=set_field, set_width=sub_width * max_pulses, n_pulses=applied,
        mean_log_ratio=float(np.mean(logs)), sigma_log_ratio=float(np.std(logs)),
        energy_proxy=set_cost + reset_cost + read_cost + driver_cost,
        p_on=float(np.mean([s["formed"] for s in samples])),
        mean_r_on=float(np.mean([s["r_on_ohm"] for s in samples])),
        p_success=n_success / config.n_cycles, set_cost_proxy=set_cost,
        reset_cost_proxy=reset_cost, read_cost_proxy=read_cost,
        driver_cost_proxy=driver_cost, mean_set_time_s=set_time,
        mean_elapsed_time_s=total_time / config.n_cycles,
        total_elapsed_time_s=total_time, max_pulses=max_pulses,
        n_trials=config.n_cycles, n_success=n_success,
        failure_probability_upper95=upper95,
        sample_mode="independent_trials" if config.independent_trials else "correlated_cycles",
        failures=failures, cycle_samples=samples,
        read_noise_log10_std=config.read_noise_log10_std,
        verify_threshold_ohm=threshold,
    )


def _simulate_protocol(set_field: float, set_width: float,
                       n_pulses: int, config: ProtocolConfig) -> ProtocolPoint:
    """Split a fixed total SET width; SET cost is independent of pulse count."""
    if not isinstance(n_pulses, int) or isinstance(n_pulses, bool) or n_pulses < 1:
        raise ValueError("pulse count must be a positive integer")
    return _run_protocol(set_field, set_width / n_pulses, n_pulses, config, False)


def _simulate_adaptive(set_field: float, sub_width: float, max_pulses: int,
                       config: ProtocolConfig) -> ProtocolPoint:
    return _run_protocol(set_field, sub_width, max_pulses, config, True)


def sweep_protocols(config: Optional[ProtocolConfig] = None) -> List[ProtocolPoint]:
    config = config or ProtocolConfig()
    fields = np.linspace(*config.fields_gv_per_m, config.n_field) * 1e8
    widths = np.logspace(math.log10(config.widths_us[0]),
                         math.log10(config.widths_us[1]), config.n_width) * 1e-6
    return [_simulate_protocol(f, w, 1, config) for f in fields for w in widths]


def pareto_front(points: List[ProtocolPoint]) -> List[ProtocolPoint]:
    valid = [p for p in points if np.all(np.isfinite(p.objectives))]
    if not valid:
        return []
    fronts = _non_dominated_fronts(np.vstack([p.objectives for p in valid]))
    return [valid[i] for i in fronts[0]]


def find_reliable_optimal(points: List[ProtocolPoint],
                          p_on_min: float = 0.9) -> Optional[ProtocolPoint]:
    """Best window satisfying an empirical full-cycle success constraint.

    This threshold on observed samples is not a certified failure bound.
    Correlated cycles intentionally have no independent-binomial bound.
    """
    if not math.isfinite(p_on_min) or not 0 <= p_on_min <= 1:
        raise ValueError("success threshold must lie in [0, 1]")
    reliable = [p for p in points if p.p_success >= p_on_min
                and np.all(np.isfinite(p.objectives))]
    return max(reliable, key=lambda p: (p.mean_log_ratio, -p.sigma_log_ratio,
                                        -p.energy_proxy)) if reliable else None


def find_elbow(points: List[ProtocolPoint]) -> Optional[ProtocolPoint]:
    """Window/dispersion heuristic restricted to the three-objective front."""
    usable = [p for p in pareto_front(points) if p.p_on < 0.995 and p.sigma_log_ratio > 0]
    if not usable:
        return None
    def norm(values):
        x = np.asarray(values)
        return (x - x.min()) / max(float(np.ptp(x)), 1e-12)
    scores = (norm([p.mean_log_ratio for p in usable])
              - norm([p.sigma_log_ratio for p in usable]))
    return usable[int(np.argmax(scores))]


def compare_pulse_strategies(config: Optional[ProtocolConfig] = None) -> Dict[str, ProtocolPoint]:
    """All strategies get the same field and maximum total SET budget: 1 us."""
    config = config or ProtocolConfig()
    field, width = 0.60e8, 1e-6
    out = {f"{n}_pulse": _simulate_protocol(field, width, n, config) for n in (1, 2, 4)}
    out["adaptive"] = _simulate_adaptive(field, width / 6, 6, config)
    return out


def discover_rram_protocol():
    config = ProtocolConfig()
    points = sweep_protocols(config)
    front = pareto_front(points)
    reliable = find_reliable_optimal(points)
    strategies = compare_pulse_strategies(config)
    print("RRAM proxy exploration: empirical cycle success, no calibrated wear model")
    print("Cost unit: normalized proxy, not joules; adaptive SET budget equals fixed budget")
    for name, point in strategies.items():
        print(f"{name}: success={point.p_success:.3f}, cost={point.energy_proxy:.4f}, "
              f"SET={point.mean_set_time_s:.3e} s, failures={point.failures}")
    return {
        "sweep": [p.as_dict() for p in points],
        "front": [p.as_dict() for p in front],
        "elbow": (p.as_dict() if (p := find_elbow(points)) else None),
        "saturated": max(points, key=lambda p: p.mean_log_ratio).as_dict(),
        "reliable_optimal": reliable.as_dict() if reliable else None,
        "pulse_strategies": {name: p.as_dict() for name, p in strategies.items()},
        "cost_unit": "normalized_proxy_not_joule",
    }


if __name__ == "__main__":
    discover_rram_protocol()
