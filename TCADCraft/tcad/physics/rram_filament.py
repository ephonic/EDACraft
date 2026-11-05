"""RRAM conductive-filament stochastic kinetics (P1-2, reserve pool).

comment7 2.2: RRAM's fatal flaw is the stochastic nucleation and growth
of conductive filaments during forming/SET. This module models the filament
radius as a birth-death chain (M3 infrastructure reuse):

- Birth (growth): field-driven oxygen vacancy migration
- Death (rupture): thermal diffusion of vacancies

The model outputs:
- Forming voltage distribution (first-passage to conducting state)
- On/off resistance ratio distribution (cycle-to-cycle variability)
- Retention (filament stability over time)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from ..physics.electron_counting import BirthDeathChain, GillespieSampler

Q_E = 1.602176634e-19
K_B = 1.381e-23


@dataclass
class FilamentConfig:
    """RRAM filament kinetics parameters."""
    n_max: int = 30               # max filament "size" (discrete voxels)
    field_ref_V_per_m: float = 1e8
    growth_activation_eV: float = 0.4   # vacancy migration barrier
    rupture_activation_eV: float = 0.8  # thermal rupture barrier
    temperature_K: float = 300.0
    attempt_freq_Hz: float = 1e13       # phonon frequency
    # Conducting threshold: filament size above this = ON state
    n_conducting: int = 20
    # Resistance parameters
    r_on_ohm: float = 1e4               # filament resistance (ON)
    r_off_ohm: float = 1e6              # bulk resistance (OFF)

    def growth_rate(self, field_V_per_m: float) -> float:
        """Field-accelerated vacancy migration rate [1/s].

        Field boost: q*E*a in energy, where a ≈ 1 nm hop distance.
        In eV: E[V/m] * a[m] = E * 1e-9 [eV].
        """
        field_boost_eV = abs(field_V_per_m) * 1e-9
        barrier = max(self.growth_activation_eV - field_boost_eV, 0.01)
        return self.attempt_freq_Hz * math.exp(
            -barrier / (8.617e-5 * self.temperature_K))

    def rupture_rate(self, n: int) -> float:
        """Thermal rupture rate [1/s] (size-dependent)."""
        # Larger filaments are slightly more stable
        size_factor = 1.0 / (1.0 + n / self.n_conducting)
        return self.attempt_freq_Hz * size_factor * math.exp(
            -self.rupture_activation_eV / (8.617e-5 * self.temperature_K))


def set_filament_rates(chain: BirthDeathChain, cfg: FilamentConfig,
                       field_V_per_m: float) -> None:
    """Declared field-driven rate proxy; no thermal RESET equation."""
    if not math.isfinite(field_V_per_m):
        raise ValueError("field must be finite")
    # Update the chain rates based on field polarity
    chain._lam[:] = 0.0
    chain._mu[:] = 0.0
    if field_V_per_m > 0:
        # SET: field-driven growth + thermal rupture
        lam = cfg.growth_rate(field_V_per_m)
        for n in range(cfg.n_max + 1):
            if n < cfg.n_max:
                chain._lam[n] = lam
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n)
    elif field_V_per_m < 0:
        # RESET: field-enhanced rupture (negative bias disperses vacancies)
        # Growth stops; rupture is enhanced by the reverse field
        rupture_boost = cfg.growth_rate(abs(field_V_per_m))
        for n in range(cfg.n_max + 1):
            if n < cfg.n_max:
                chain._lam[n] = 0.0  # no growth during reset
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n) + rupture_boost
    else:
        # Zero field: thermal equilibrium only
        for n in range(cfg.n_max + 1):
            if n < cfg.n_max:
                chain._lam[n] = cfg.growth_rate(0.0)
            if n > 0:
                chain._mu[n] = cfg.rupture_rate(n)


def filament_resistance(n: int, cfg: FilamentConfig) -> float:
    """Log-interpolated resistance of one sampled filament, in ohms."""
    if n >= cfg.n_conducting:
        return cfg.r_on_ohm
    fraction = n / cfg.n_conducting
    return math.exp(math.log(cfg.r_off_ohm) + fraction
                    * (math.log(cfg.r_on_ohm) - math.log(cfg.r_off_ohm)))


@dataclass
class FilamentState:
    """State of a single filament."""
    chain: BirthDeathChain
    config: FilamentConfig
    field_V_per_m: float = 0.0

    def step(self, dt: float) -> np.ndarray:
        """Advance the distribution over the complete requested interval."""
        set_filament_rates(self.chain, self.config, self.field_V_per_m)
        return self.chain.advance(dt)

    @property
    def is_conducting(self) -> bool:
        if self.chain.state is None:
            return False
        # Check if the probability of being in the conducting state is > 50%
        p_conducting = float(np.sum(self.chain.state[self.config.n_conducting:]))
        return p_conducting > 0.5

    @property
    def expected_resistance(self) -> float:
        """Expected resistance based on the filament size distribution."""
        if self.chain.state is None:
            return self.config.r_off_ohm
        p_on = float(np.sum(self.chain.state[self.config.n_conducting:]))
        p_off = 1.0 - p_on
        # Parallel combination weighted by probability
        if p_on < 1e-10:
            return self.config.r_off_ohm
        if p_off < 1e-10:
            return self.config.r_on_ohm
        return 1.0 / (p_on / self.config.r_on_ohm + p_off / self.config.r_off_ohm)


def simulate_forming(
    config: FilamentConfig,
    field_V_per_m: float,
    t_max: float = 1e-6,
    n_steps: int = 20,
) -> Dict:
    """Evolve to t_max, including after the conducting threshold is crossed.

    n_steps sets output integration subdivision. The probability engine
    handles high rate-time products without shortening the physical hold.
    """
    if not math.isfinite(t_max) or t_max < 0:
        raise ValueError("t_max must be finite and >= 0")
    if not isinstance(n_steps, int) or isinstance(n_steps, bool) or n_steps < 1:
        raise ValueError("n_steps must be a positive integer")
    chain = BirthDeathChain(n_max=config.n_max,
                           capture_rate=lambda n: 0.0,
                           emission_rate=lambda n: 0.0)
    chain.initialize(count=0)
    state = FilamentState(chain=chain, config=config, field_V_per_m=field_V_per_m)
    set_filament_rates(chain, config, field_V_per_m)
    elapsed = 0.0
    for target in np.linspace(0.0, t_max, n_steps + 1)[1:]:
        duration = float(target) - elapsed
        if duration > 0:
            state.step(duration)
        elapsed = float(target)
    return {
        'formed': float(state.is_conducting),
        'expected_resistance': state.expected_resistance,
        'p_conducting': float(np.sum(chain.state[config.n_conducting:])),
        'mean_size': chain.mean(),
        'probabilities': chain.state.copy(),
        'time_s': elapsed,
        'requested_time_s': t_max,
        'completed': True,
        'stop_reason': 'completed',
    }


def simulate_cycling(
    config: FilamentConfig,
    set_field: float = 1.5e8,
    reset_field: float = -0.5e8,
    pulse_width: float = 1e-6,
    n_cycles: int = 20,
    seed: int = 0,
) -> Dict:
    """Seeded SSA cycles carrying RESET residue into the following SET.

    Every SET and RESET covers pulse_width; no substep cap is applied.
    This is a field-driven filament proxy without calibrated wear or heat.
    """
    if not math.isfinite(pulse_width) or pulse_width <= 0:
        raise ValueError("pulse_width must be finite and > 0")
    if not isinstance(n_cycles, int) or isinstance(n_cycles, bool) or n_cycles < 1:
        raise ValueError("n_cycles must be a positive integer")
    chain = BirthDeathChain(n_max=config.n_max,
                           capture_rate=lambda n: 0.0,
                           emission_rate=lambda n: 0.0)
    sampler = GillespieSampler(chain=chain, seed=seed)
    n = 0
    resistances, starts, set_counts, reset_counts = [], [], [], []
    for _ in range(n_cycles):
        starts.append(n)
        set_filament_rates(chain, config, set_field)
        n, _ = sampler.run_trajectory(pulse_width, n)
        set_counts.append(n)
        r_on = filament_resistance(n, config)
        set_filament_rates(chain, config, reset_field)
        n, _ = sampler.run_trajectory(pulse_width, n)
        reset_counts.append(n)
        resistances.append((r_on, filament_resistance(n, config)))
    r_arr = np.asarray(resistances)
    ratios = r_arr[:, 1] / r_arr[:, 0]
    log_ratios = np.log10(ratios)
    return {
        'r_on_ohm': r_arr[:, 0],
        'r_off_ohm': r_arr[:, 1],
        'ratios': ratios,
        'log_ratios': log_ratios,
        'cycle_variability': float(np.std(log_ratios)),
        'mean_ratio': float(np.mean(ratios)),
        'initial_counts': np.asarray(starts),
        'set_counts': np.asarray(set_counts),
        'reset_counts': np.asarray(reset_counts),
        'cycle_end_times_s': 2 * pulse_width * np.arange(1, n_cycles + 1),
        'time_s': 2 * pulse_width * n_cycles,
        'requested_time_s': 2 * pulse_width * n_cycles,
        'completed': True,
        'stop_reason': 'completed',
        'seed': seed,
        'damage_model': 'unavailable',
    }
