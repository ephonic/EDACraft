"""PCM (Phase-Change Memory) resistance drift model.

comment7 2.2: PCM's fatal flaw is resistance drift originating from
structural relaxation of the amorphous phase. The amorphous resistance
increases over time as the glass relaxes toward a lower-energy state.

Physical model:
- Amorphous phase resistance follows a power-law drift:
  R(t) = R_0 * (t / t_0)^ν
  where ν ≈ 0.05-0.15 is the drift exponent
- The drift is thermally activated (faster at higher temperature)
- Crystallization (the competing process) follows Avrami kinetics (M4)
- RESET state: amorphous → drift + potential crystallization
- SET state: crystalline → stable (no drift)

Infrastructure reuse: M4 AvramiDomainSwitching for crystallization kinetics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass
class PcmConfig:
    """PCM drift and crystallization parameters."""
    # Drift parameters
    drift_exponent: float = 0.10       # ν (typical: 0.05-0.15)
    drift_activation_eV: float = 0.3    # structural relaxation barrier
    t_ref_s: float = 1e-9              # reference time
    temperature_K: float = 300.0

    # Crystallization parameters (Avrami)
    avrami_n: float = 2.0              # growth dimensionality
    crystallization_rate_1_s: float = 1e-5   # rate at reference temp
    crystallization_activation_eV: float = 3.0  # high barrier (slow at 300K)

    # Resistance parameters
    r_amorphous_ohm: float = 1e6       # RESET (amorphous) resistance
    r_crystalline_ohm: float = 1e3     # SET (crystalline) resistance

    # Time grid
    t_start_s: float = 1e-9
    t_end_s: float = 1e4               # ~3 hours

    def bounds(self):
        return {
            "drift_exponent": (0.02, 0.20),
            "drift_activation_eV": (0.1, 0.6),
            "crystallization_rate_1_s": (1e-5, 1e-1),
            "crystallization_activation_eV": (1.0, 3.5),
        }


@dataclass
class PcmState:
    """State of a PCM cell after RESET."""
    config: PcmConfig
    r_initial_ohm: float = 1e6
    elapsed_s: float = 0.0
    crystallized_fraction: float = 0.0

    def drift_factor(self, t: float) -> float:
        """Resistance drift multiplier: R(t)/R(0) = (t/t_ref)^ν."""
        if t <= self.config.t_ref_s:
            return 1.0
        # Temperature-accelerated drift
        kT = 8.617e-5 * self.config.temperature_K
        thermal_boost = math.exp(
            -self.config.drift_activation_eV / kT + 
            self.config.drift_activation_eV / (8.617e-5 * 300.0))
        effective_nu = self.config.drift_exponent * min(thermal_boost, 10.0)
        return (t / self.config.t_ref_s) ** min(effective_nu, 0.5)

    def crystallization_advance(self, dt: float) -> float:
        """Advance crystallization by dt using Avrami kinetics.

        f(t) = 1 - exp(-(∫k(T)dt)^n) where k is the rate.
        """
        cfg = self.config
        kT = 8.617e-5 * cfg.temperature_K
        k = cfg.crystallization_rate_1_s * math.exp(
            -(cfg.crystallization_activation_eV - 2.0) / kT)
        # Incremental Avrami: track cumulative "Avrami time"
        x = -math.log(max(1.0 - self.crystallized_fraction, 1e-30))
        x_new = (x ** (1.0 / cfg.avrami_n) + k * dt) ** cfg.avrami_n
        return min(1.0 - math.exp(-x_new), 1.0)

    def advance(self, dt: float) -> float:
        """Advance both drift and crystallization by dt; return R(t)."""
        self.elapsed_s += dt
        self.crystallized_fraction = self.crystallization_advance(dt)

        # Drifted amorphous resistance
        r_drift = self.r_initial_ohm * self.drift_factor(self.elapsed_s)

        # Effective resistance: crystalline and amorphous in parallel
        f = self.crystallized_fraction
        r_amorphous = r_drift
        r_crystalline = self.config.r_crystalline_ohm

        if f < 1e-10:
            return r_amorphous
        if f > 1.0 - 1e-10:
            return r_crystalline

        # Percolation-weighted parallel combination
        # Below percolation threshold, crystalline domains are isolated
        # Above threshold, they form conducting pathways
        f_c = 0.3  # percolation threshold
        if f < f_c:
            # Isolated crystalline domains: negligible conductance
            return r_amorphous
        else:
            # Percolating network forms
            g_am = (1.0 - f) / r_amorphous
            g_cr = f / r_crystalline
            return 1.0 / (g_am + g_cr)

    @property
    def resistance_ohm(self) -> float:
        return self.advance(0.0) if self.elapsed_s > 0 else self.r_initial_ohm


def simulate_retention_drift(
    config: PcmConfig,
    r_initial: float = 1e6,
    n_points: int = 50,
) -> Dict[str, np.ndarray]:
    """Simulate PCM resistance drift over time.

    Returns time array [s], resistance array [ohm], and derived metrics.
    """
    # Log-spaced time grid
    t_grid = np.logspace(
        math.log10(config.t_start_s),
        math.log10(config.t_end_s),
        n_points,
    )

    state = PcmState(config=config, r_initial_ohm=r_initial)
    times = [0.0]
    resistances = [r_initial]

    for t_target in t_grid:
        dt = t_target - times[-1]
        if dt <= 0:
            continue
        r = state.advance(dt)
        times.append(t_target)
        resistances.append(r)

    t_arr = np.array(times)
    r_arr = np.array(resistances)

    # Drift exponent from log-log fit (excluding crystallization onset)
    # Use the first half of the data (before crystallization dominates)
    n_fit = max(len(t_arr) // 2, 5)
    log_t = np.log10(np.maximum(t_arr[1:n_fit], 1e-30))
    log_r = np.log10(np.maximum(r_arr[1:n_fit], 1e-30))
    if len(log_t) > 2 and np.std(log_t) > 0:
        slope = np.polyfit(log_t, log_r, 1)[0]
    else:
        slope = 0.0

    return {
        'time_s': t_arr,
        'resistance_ohm': r_arr,
        'drift_exponent_fit': slope,
        'r_initial_ohm': r_initial,
        'r_final_ohm': float(r_arr[-1]),
        'drift_ratio': float(r_arr[-1] / max(r_arr[0], 1e-30)),
        'crystallized_fraction': state.crystallized_fraction,
    }
