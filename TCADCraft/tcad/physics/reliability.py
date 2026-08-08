"""Stateful reliability models for traps, retention, wake-up and fatigue.

The drift-diffusion solver consumes oxide charge in C/m^3.  This module owns
the missing time/cycle state and advances it with exact first-order updates,
so protocol drivers can feed the resulting charge back into Poisson without
using a time-step-dependent Euler approximation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


Q_E = 1.602176634e-19
K_B_EV = 8.617333262e-5


@dataclass
class TrapKinetics:
    """First-order electron-trap capture/emission model.

    Parameters use SI except energies, which are in eV. ``density`` is the
    volumetric active trap density [m^-3]. ``capture_tau`` and
    ``emission_tau`` are reference time constants at ``reference_temperature``.
    The field acceleration follows a Poole-Frenkel-like ``exp(gamma*sqrt(E))``.
    Filled traps are negatively charged relative to ``neutral_occupancy``.
    """

    density: float
    trap_energy: float = 0.0
    capture_tau: float = 1.0e-3
    emission_tau: float = 1.0e3
    activation_energy: float = 0.0
    field_acceleration: float = 0.0
    neutral_occupancy: float = 0.5
    reference_temperature: float = 300.0
    mask: Optional[np.ndarray] = None
    occupancy: Optional[np.ndarray] = field(default=None, init=False)

    def __post_init__(self) -> None:
        positive = {
            "density": self.density,
            "capture_tau": self.capture_tau,
            "emission_tau": self.emission_tau,
            "reference_temperature": self.reference_temperature,
        }
        for name, value in positive.items():
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if not 0.0 <= self.neutral_occupancy <= 1.0:
            raise ValueError("neutral_occupancy must lie in [0, 1]")
        if self.mask is not None:
            self.mask = np.asarray(self.mask, dtype=bool).ravel()

    def initialize(self, npts: int, occupancy: Optional[float] = None) -> None:
        if npts < 1:
            raise ValueError("npts must be >= 1")
        value = self.neutral_occupancy if occupancy is None else float(occupancy)
        if not 0.0 <= value <= 1.0:
            raise ValueError("initial occupancy must lie in [0, 1]")
        if self.mask is not None and self.mask.size != npts:
            raise ValueError(f"trap mask size {self.mask.size} != npts {npts}")
        self.occupancy = np.full(npts, value, dtype=float)

    def _active_mask(self, npts: int) -> np.ndarray:
        if self.mask is None:
            return np.ones(npts, dtype=bool)
        if self.mask.size != npts:
            raise ValueError(f"trap mask size {self.mask.size} != npts {npts}")
        return self.mask

    def equilibrium_occupancy(self, phi, temperature: float = 300.0) -> np.ndarray:
        """Fermi occupancy for E_t relative to the local intrinsic level."""
        phi = np.asarray(phi, dtype=float).ravel()
        if not np.isfinite(temperature) or temperature <= 0.0:
            raise ValueError("temperature must be finite and > 0")
        arg = np.clip((self.trap_energy - phi) / (K_B_EV * temperature), -80.0, 80.0)
        return 1.0 / (1.0 + np.exp(arg))

    def advance(self, phi, electric_field, dt: float,
                temperature: float = 300.0) -> np.ndarray:
        """Advance occupancy exactly over ``dt`` and return Q_ot [C/m^3]."""
        phi = np.asarray(phi, dtype=float).ravel()
        field_mag = np.asarray(electric_field, dtype=float)
        if field_mag.ndim == 0:
            field_mag = np.full(phi.size, float(field_mag))
        else:
            field_mag = field_mag.ravel()
        if field_mag.size != phi.size:
            raise ValueError("electric_field and phi sizes must match")
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and > 0")
        if not np.all(np.isfinite(phi)) or not np.all(np.isfinite(field_mag)):
            raise ValueError("phi/electric_field must contain finite values")
        if self.occupancy is None or self.occupancy.size != phi.size:
            self.initialize(phi.size)

        active = self._active_mask(phi.size)
        f_eq = self.equilibrium_occupancy(phi, temperature)
        thermal_exponent = -self.activation_energy / K_B_EV * (
            1.0 / temperature - 1.0 / self.reference_temperature
        )
        field_exponent = self.field_acceleration * np.sqrt(np.maximum(np.abs(field_mag), 0.0))
        acceleration = np.exp(np.clip(thermal_exponent + field_exponent, -50.0, 50.0))
        # Use the capture time when the Fermi target is filled and the emission
        # time when it is empty, with a smooth transition for partial
        # occupancy. This retains the exact equilibrium target while allowing
        # physically different stress and recovery time scales.
        rate = acceleration * (
            f_eq / self.capture_tau + (1.0 - f_eq) / self.emission_tau
        )
        decay = np.exp(-np.minimum(rate * dt, 700.0))
        updated = f_eq + (self.occupancy - f_eq) * decay
        self.occupancy[active] = np.clip(updated[active], 0.0, 1.0)
        return self.charge_density()

    def charge_density(self) -> np.ndarray:
        if self.occupancy is None:
            raise RuntimeError("trap state is uninitialized; call initialize/advance first")
        active = self._active_mask(self.occupancy.size)
        charge = np.zeros_like(self.occupancy)
        charge[active] = -Q_E * self.density * (
            self.occupancy[active] - self.neutral_occupancy
        )
        return charge


@dataclass
class CyclingDegradation:
    """Competing wake-up and fatigue state equations versus cycle count."""

    wakeup_cycles: float = 1.0e3
    fatigue_cycles: float = 1.0e6
    wakeup_gain: float = 0.15
    fatigue_loss: float = 0.8
    reference_field: float = 3.0e8
    field_exponent: float = 2.0
    cycles: float = field(default=0.0, init=False)
    wakeup_state: float = field(default=0.0, init=False)
    fatigue_state: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        for name in ("wakeup_cycles", "fatigue_cycles", "reference_field"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if self.wakeup_gain < 0.0 or not 0.0 <= self.fatigue_loss <= 1.0:
            raise ValueError("wakeup_gain must be >=0 and fatigue_loss in [0,1]")

    def advance(self, cycles: float = 1.0, electric_field: float = 0.0) -> float:
        if not np.isfinite(cycles) or cycles <= 0.0:
            raise ValueError("cycles must be finite and > 0")
        self.cycles += float(cycles)
        accel = max(abs(float(electric_field)) / self.reference_field, 1.0e-12)
        accel = accel ** self.field_exponent
        self.wakeup_state = 1.0 - np.exp(-self.cycles / self.wakeup_cycles)
        self.fatigue_state = 1.0 - np.exp(-self.cycles * accel / self.fatigue_cycles)
        return self.active_fraction

    @property
    def active_fraction(self) -> float:
        wake = 1.0 + self.wakeup_gain * self.wakeup_state
        fatigue = 1.0 - self.fatigue_loss * self.fatigue_state
        return float(np.clip(wake * fatigue, 0.0, 1.0 + self.wakeup_gain))
