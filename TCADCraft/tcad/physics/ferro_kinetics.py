"""M1/M4 ferroelectric slow-state kinetics (plan0918 direction-1 work package).

M1 ``FieldHistoryCyclingState`` upgrades the memoryless ``CyclingDegradation``
closed forms into true slow-variable ODE states whose damage accumulates over
the full field history.  All updates are exact first-order solutions over
piecewise-constant segments, so cycle striding over N cycles reproduces N
single-cycle advances to machine precision (verification protocol 2.1/2.3).

M4 ``AvramiDomainSwitching`` / ``KaiMultiDomain`` implement KAI
nucleation-and-growth switching in the additivity (Scheil) form.  The exact
piecewise-constant-field update ``x <- (x^(1/n) + dt/tau(E))^n`` reproduces
the closed-form Avrami fraction ``1 - exp(-(t/tau)^n)`` for any step size,
which is the analytic golden for this kernel.

The old ``CyclingDegradation`` is intentionally untouched; this module is
opt-in and no solver path imports it by default (bit-preserving gate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class FieldHistoryCyclingState:
    """Wake-up/fatigue/imprint states with exact field-history accumulation.

    Damage dynamics in cycle count C for piecewise-constant field E::

        dW/dC = (1 - W) / N_w(E)
        dD/dC = (1 - D) / N_f(E)
        dB/dC = eta * u(E) * (sgn(E) * B_max - B)

    with ``N_w/N_f`` the wake-up/fatigue lifetimes (power-law field
    acceleration, slower at small |E|) and ``B`` a signed imprint-bias state
    saturating at ``B_max``.  Every segment advances the states with the
    exact exponential solution, so the state depends on the full field
    history and is invariant to segment subdivision.  Zero-field segments
    are treated as no-event holds: neither damage, imprint, nor the cycle
    counter advance.
    """

    wakeup_cycles: float = 1.0e3
    fatigue_cycles: float = 1.0e6
    wakeup_gain: float = 0.15
    fatigue_loss: float = 0.8
    reference_field: float = 3.0e8
    fatigue_field_exponent: float = 2.0
    wakeup_field_exponent: float = 0.0
    imprint_rate: float = 0.0
    imprint_field_exponent: float = 1.0
    imprint_field_max: float = 0.0
    cycles: float = field(default=0.0, init=False)
    wakeup_state: float = field(default=0.0, init=False)
    fatigue_state: float = field(default=0.0, init=False)
    imprint_state: float = field(default=0.0, init=False)
    last_recheck_deviation: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        for name in ("wakeup_cycles", "fatigue_cycles", "reference_field"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if self.wakeup_gain < 0.0 or not 0.0 <= self.fatigue_loss <= 1.0:
            raise ValueError("wakeup_gain must be >=0 and fatigue_loss in [0,1]")
        for name in (
            "fatigue_field_exponent",
            "wakeup_field_exponent",
            "imprint_rate",
            "imprint_field_exponent",
            "imprint_field_max",
        ):
            value = getattr(self, name)
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and >= 0")

    def _step(
        self,
        w: float,
        d: float,
        b: float,
        cycles: float,
        electric_field: float,
    ) -> Tuple[float, float, float]:
        field_mag = abs(float(electric_field))
        n_w = self._lifetime(self.wakeup_cycles, self.wakeup_field_exponent, field_mag)
        n_f = self._lifetime(self.fatigue_cycles, self.fatigue_field_exponent, field_mag)
        w_new = 1.0 - (1.0 - w) * np.exp(-cycles / n_w)
        d_new = 1.0 - (1.0 - d) * np.exp(-cycles / n_f)
        sign = 0.0 if electric_field == 0.0 else float(np.sign(electric_field))
        drive = (
            self.imprint_rate
            * (field_mag / self.reference_field) ** self.imprint_field_exponent
        )
        target = sign * self.imprint_field_max
        b_new = target + (b - target) * np.exp(-drive * cycles)
        return float(w_new), float(d_new), float(b_new)

    def _lifetime(self, base: float, exponent: float, field_mag: float) -> float:
        ratio = self.reference_field / max(field_mag, 1.0e-12 * self.reference_field)
        return base * float(ratio) ** exponent

    def advance(self, cycles: float = 1.0, electric_field: float = 0.0) -> float:
        if not np.isfinite(cycles) or cycles <= 0.0:
            raise ValueError("cycles must be finite and > 0")
        if not np.isfinite(electric_field):
            raise ValueError("electric_field must be finite")
        if electric_field == 0.0:
            return self.active_fraction
        self.wakeup_state, self.fatigue_state, self.imprint_state = self._step(
            self.wakeup_state, self.fatigue_state, self.imprint_state,
            cycles, electric_field,
        )
        self.cycles += cycles
        return self.active_fraction

    def advance_with_recheck(
        self,
        cycles: float,
        electric_field: float,
        stride: float = 1000.0,
        recheck_every: int = 8,
        recheck_splits: int = 8,
    ) -> float:
        """Stride over ``cycles`` and periodically recompute the segment
        explicitly from the pre-stride state.

        Exact-exponential updates make strided and explicit trajectories agree
        to machine precision today; the recheck guards future rate
        parameterizations (sub-cycle waveforms, temperature coupling) where
        exactness can silently break.  ``last_recheck_deviation`` records the
        worst observed state deviation across all rechecks.
        """
        if not np.isfinite(stride) or stride <= 0.0:
            raise ValueError("stride must be finite and > 0")
        if recheck_every < 1 or recheck_splits < 1:
            raise ValueError("recheck_every and recheck_splits must be >= 1")
        remaining = float(cycles)
        since_recheck = 0
        self.last_recheck_deviation = 0.0
        while remaining > 0.0:
            step = min(stride, remaining)
            before = (self.wakeup_state, self.fatigue_state, self.imprint_state)
            self.advance(step, electric_field)
            after = (self.wakeup_state, self.fatigue_state, self.imprint_state)
            remaining -= step
            since_recheck += 1
            if since_recheck >= recheck_every or remaining <= 0.0:
                since_recheck = 0
                w, d, b = before
                sub = step / float(recheck_splits)
                for _ in range(recheck_splits):
                    w, d, b = self._step(w, d, b, sub, electric_field)
                deviation = max(
                    abs(w - after[0]), abs(d - after[1]), abs(b - after[2]),
                )
                self.last_recheck_deviation = max(
                    self.last_recheck_deviation, deviation,
                )
        return self.active_fraction

    @property
    def active_fraction(self) -> float:
        wake = 1.0 + self.wakeup_gain * self.wakeup_state
        fatigue = 1.0 - self.fatigue_loss * self.fatigue_state
        return float(np.clip(wake * fatigue, 0.0, 1.0 + self.wakeup_gain))

    def imprint_field(self) -> float:
        return float(self.imprint_state)

    def effective_field(self, applied_field: float) -> float:
        return float(applied_field) + self.imprint_state


@dataclass
class AvramiDomainSwitching:
    """Single-domain KAI switching with exact piecewise-constant-field update.

    Switching progress ``x`` follows the additivity form
    ``dx/dt = (n/tau(E)) * x^((n-1)/n)`` with the exact step solution
    ``x <- (x^(1/n) + dt/tau(E))^n``; the switched fraction is
    ``f = 1 - exp(-x)``.  Under constant field this reproduces the closed-form
    KAI result ``f = 1 - exp(-(t/tau)^n)`` for any step size (analytic
    golden).  ``tau(E)`` uses Merz's power law
    ``tau0 * (merz_field/|E|)^merz_exponent`` above ``onset_field``.

    Domain state machine: opposing field above onset accumulates progress
    toward the opposite orientation; completion (``f >= completion_fraction``)
    flips ``orientation`` and resets progress.  When the field is aligned or
    sub-threshold, partial progress relaxes back with the same field-dependent
    tau (modelled back-switching; documented model choice).
    """

    avrami_exponent: float = 1.5
    tau0: float = 1.0e-9
    onset_field: float = 5.0e7
    merz_field: float = 1.0e8
    merz_exponent: float = 1.0
    completion_fraction: float = 0.999
    orientation: int = -1
    progress: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.avrami_exponent) or self.avrami_exponent <= 0.0:
            raise ValueError("avrami_exponent must be finite and > 0")
        for name in ("tau0", "merz_field"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if not np.isfinite(self.onset_field) or self.onset_field < 0.0:
            raise ValueError("onset_field must be finite and >= 0 (0 disables the threshold)")
        if not np.isfinite(self.merz_exponent) or self.merz_exponent < 0.0:
            raise ValueError("merz_exponent must be finite and >= 0")
        if not 0.0 < self.completion_fraction < 1.0:
            raise ValueError("completion_fraction must lie in (0, 1)")
        if self.orientation not in (-1, 1):
            raise ValueError("orientation must be -1 or +1")
        if not np.isfinite(self.progress) or self.progress < 0.0:
            raise ValueError("progress must be finite and >= 0")

    def tau(self, electric_field: float) -> float:
        field_mag = max(abs(float(electric_field)), 1.0e-12 * self.merz_field)
        return self.tau0 * (self.merz_field / field_mag) ** self.merz_exponent

    @property
    def switched_fraction(self) -> float:
        return float(1.0 - np.exp(-self.progress))

    def polarization(self, ps: float) -> float:
        return float(ps * self.orientation * (1.0 - 2.0 * self.switched_fraction))

    def _accumulate(self, dt: float, electric_field: float) -> None:
        root = self.progress ** (1.0 / self.avrami_exponent)
        self.progress = float((root + dt / self.tau(electric_field)) ** self.avrami_exponent)

    def _relax(self, dt: float, electric_field: float) -> None:
        if self.progress == 0.0:
            return
        decay = np.exp(-dt / self.tau(electric_field))
        root = self.progress ** (1.0 / self.avrami_exponent)
        self.progress = float(max(root * decay, 0.0) ** self.avrami_exponent)

    def advance(self, electric_field: float, dt: float) -> float:
        if not np.isfinite(electric_field):
            raise ValueError("electric_field must be finite")
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and > 0")
        field_sign = 0 if electric_field == 0.0 else int(np.sign(electric_field))
        opposing = (
            field_sign != 0
            and field_sign == -self.orientation
            and abs(electric_field) > self.onset_field
        )
        if opposing:
            self._accumulate(dt, electric_field)
            if self.switched_fraction >= self.completion_fraction:
                self.orientation = -self.orientation
                self.progress = 0.0
        else:
            self._relax(dt, electric_field)
        return self.switched_fraction


@dataclass
class KaiMultiDomain:
    """Weighted multi-domain KAI stack sharing one applied field waveform.

    Each domain is an :class:`AvramiDomainSwitching` with its own onset/tau
    parameters and current orientation.  Weights must sum to one so the net
    polarization is structurally bounded by ``|P| <= Ps``.
    """

    ps: float
    weights: Sequence[float]
    domains: Sequence[AvramiDomainSwitching]

    def __post_init__(self) -> None:
        if not np.isfinite(self.ps) or self.ps <= 0.0:
            raise ValueError("ps must be finite and > 0")
        w = np.asarray(self.weights, dtype=float).ravel()
        d = list(self.domains)
        if w.size != len(d):
            raise ValueError("weights and domains must have equal length")
        if w.size < 1:
            raise ValueError("at least one domain is required")
        if not np.all(np.isfinite(w)) or np.any(w < 0.0):
            raise ValueError("weights must be finite and >= 0")
        if abs(float(np.sum(w)) - 1.0) > 1.0e-9:
            raise ValueError("weights must sum to 1")
        self.weights = w
        self.domains = d

    def advance(self, electric_field: float, dt: float) -> None:
        for domain in self.domains:
            domain.advance(electric_field, dt)

    def polarization(self) -> float:
        total = 0.0
        for w, domain in zip(self.weights, self.domains):
            total += w * domain.polarization(self.ps)
        return float(total)

    def switched_fractions(self) -> np.ndarray:
        return np.asarray([d.switched_fraction for d in self.domains], dtype=float)


def simulate_kai_waveform(
    times: Sequence[float],
    fields: Sequence[float],
    ps: float,
    domain_specs: Optional[List[Tuple[float, dict]]] = None,
) -> dict:
    """Advance a :class:`KaiMultiDomain` stack over a field waveform.

    ``domain_specs`` is a list of ``(weight, AvramiDomainSwitching kwargs)``;
    a single unit-weight default domain is used when omitted.  Returns the
    trajectory of polarization and per-domain switched fractions.
    """
    t = np.asarray(times, dtype=float).ravel()
    f = np.asarray(fields, dtype=float).ravel()
    if t.size != f.size:
        raise ValueError("times and fields must have equal length")
    if t.size < 2 or np.any(np.diff(t) <= 0.0):
        raise ValueError("times must be strictly increasing with >= 2 samples")
    if not np.all(np.isfinite(f)):
        raise ValueError("fields must be finite")
    if domain_specs is None:
        stack = KaiMultiDomain(ps=ps, weights=[1.0], domains=[AvramiDomainSwitching()])
    else:
        weights = [float(w) for w, _ in domain_specs]
        domains = [AvramiDomainSwitching(**kw) for _, kw in domain_specs]
        stack = KaiMultiDomain(ps=ps, weights=weights, domains=domains)
    p_vals = [stack.polarization()]
    f_vals = [stack.switched_fractions().copy()]
    for k in range(1, t.size):
        dt = float(t[k] - t[k - 1])
        stack.advance(float(f[k]), dt)
        p_vals.append(stack.polarization())
        f_vals.append(stack.switched_fractions().copy())
    return {
        "times": t,
        "fields": f,
        "polarization": np.asarray(p_vals, dtype=float),
        "switched_fractions": np.vstack(f_vals),
    }
