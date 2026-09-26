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


@dataclass
class FilamentState:
    """State of a single filament."""
    chain: BirthDeathChain
    config: FilamentConfig
    field_V_per_m: float = 0.0

    def step(self, dt: float) -> np.ndarray:
        """Advance filament state by dt.

        Field polarity matters: positive field drives vacancy migration
        (filament growth); negative field drives rupture ( Joule heating
        and vacancy dispersal). Zero field = thermal equilibrium only.
        """
        cfg = self.config
        # Update the chain rates based on field polarity
        self.chain._lam[:] = 0.0
        self.chain._mu[:] = 0.0
        if self.field_V_per_m > 0:
            # SET: field-driven growth + thermal rupture
            lam = cfg.growth_rate(self.field_V_per_m)
            for n in range(cfg.n_max + 1):
                if n < cfg.n_max:
                    self.chain._lam[n] = lam
                if n > 0:
                    self.chain._mu[n] = cfg.rupture_rate(n)
        elif self.field_V_per_m < 0:
            # RESET: field-enhanced rupture (negative bias disperses vacancies)
            # Growth stops; rupture is enhanced by the reverse field
            rupture_boost = cfg.growth_rate(abs(self.field_V_per_m))
            for n in range(cfg.n_max + 1):
                if n < cfg.n_max:
                    self.chain._lam[n] = 0.0  # no growth during reset
                if n > 0:
                    self.chain._mu[n] = cfg.rupture_rate(n) + rupture_boost
        else:
            # Zero field: thermal equilibrium only
            for n in range(cfg.n_max + 1):
                if n < cfg.n_max:
                    self.chain._lam[n] = cfg.growth_rate(0.0)
                if n > 0:
                    self.chain._mu[n] = cfg.rupture_rate(n)
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
) -> Dict[str, float]:
    """Simulate the forming process (bounded computation).

    Uses small dt steps to keep the uniformization series manageable
    (rate*dt should be << 1000 for the Poisson-weighted Neumann series).
    """
    # Cap effective dt to keep uniformization tractable
    cfg = config
    est_rate = cfg.growth_rate(field_V_per_m)
    safe_dt = min(t_max / n_steps, 100.0 / max(est_rate, 1.0))
    actual_steps = max(int(math.ceil(t_max / safe_dt)), 1)

    chain = BirthDeathChain(
        n_max=cfg.n_max,
        capture_rate=lambda n: 0.0,
        emission_rate=lambda n: 0.0,
    )
    chain.initialize(count=0)
    state = FilamentState(chain=chain, config=cfg, field_V_per_m=field_V_per_m)

    for _ in range(min(actual_steps, 200)):  # hard cap for speed
        state.step(safe_dt)
        if state.is_conducting:
            break

    return {
        'formed': float(state.is_conducting),
        'expected_resistance': state.expected_resistance,
        'p_conducting': float(np.sum(chain.state[cfg.n_conducting:])),
        'mean_size': float(np.dot(np.arange(cfg.n_max + 1), chain.state)),
    }


def simulate_cycling(
    config: FilamentConfig,
    set_field: float = 1.5e8,
    reset_field: float = -0.5e8,
    pulse_width: float = 1e-6,
    n_cycles: int = 20,
    seed: int = 0,
) -> Dict[str, np.ndarray]:
    """Simulate multiple SET/RESET cycles; measure cycle-to-cycle variability.

    Uses short pulse widths to keep the uniformization tractable.
    """
    # Cap effective rates for tractability, but use enough sub-steps
    est_rate = config.growth_rate(set_field)
    safe_dt = min(pulse_width, 50.0 / max(est_rate, 1.0))
    n_sub = max(int(math.ceil(pulse_width / safe_dt)), 1)
    n_sub = min(n_sub, 50)  # cap sub-steps for speed

    resistances = []
    for _ in range(n_cycles):
        chain = BirthDeathChain(
            n_max=config.n_max,
            capture_rate=lambda n: 0.0,
            emission_rate=lambda n: 0.0,
        )
        chain.initialize(count=0)
        state = FilamentState(chain=chain, config=config)

        # SET: apply positive field (filament grows, multiple sub-steps)
        state.field_V_per_m = set_field
        for _ in range(n_sub):
            state.step(safe_dt)
        r_on = state.expected_resistance

        # RESET: apply negative field (filament ruptures)
        state.field_V_per_m = reset_field
        for _ in range(n_sub):
            state.step(safe_dt)
        r_off = state.expected_resistance
        resistances.append((r_on, r_off))

    r_arr = np.array(resistances)
    ratios = r_arr[:, 1] / np.maximum(r_arr[:, 0], 1.0)  # R_off/R_on (>1)
    log_ratios = np.log10(np.maximum(ratios, 1e-30))
    return {
        'r_on_ohm': r_arr[:, 0],
        'r_off_ohm': r_arr[:, 1],
        'ratios': ratios,
        'cycle_variability': float(np.std(log_ratios))
        if np.all(np.isfinite(log_ratios)) else 0.0,
        'mean_ratio': float(np.mean(ratios))
        if np.all(np.isfinite(ratios)) else 1.0,
    }
