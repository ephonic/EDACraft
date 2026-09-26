"""M3 stored-electron counting probability (plan0918 direction-1 work package).

Comment7 2.1: at scaled storage nodes a programmed state holds a single-digit
electron count, so retention/endurance/BER are probability statements, not
deterministic curves.  This module makes the counting explicit through the
birth-death master equation for the stored-electron number ``n``::

    dP(n)/dt = lam(n-1)*P(n-1) + mu(n+1)*P(n+1) - (lam(n)+mu(n))*P(n)

with ``lam`` the capture (programming/charge-gain) rate and ``mu`` the
emission (loss) rate.  Two deliberately independent numerical engines cover
the same equation:

* :class:`BirthDeathChain` - direct integration via uniformization (Jensen's
  method).  The step is exact for piecewise-constant rates (semigroup, no
  timestep error), pure numpy, and returns the *full distribution*, so tail
  quantities like -5 sigma BER come from the exact CDF with no rare-event
  sampling problem for the O(10-100) state spaces of MLC cells.
* :class:`GillespieSampler` - exact stochastic simulation algorithm (SSA)
  trajectories over the same rates; used as the cross-validation engine and
  for first-passage (retention) statistics.

Analytic goldens (tests/test_electron_counting.py):

* constant-rate Poisson limit, linear-rate binomial closed form,
* detailed-balance stationary product form,
* mean-field degeneration to the deterministic rate equation for linear
  rates (the M1 ``TrapKinetics`` mean-field limit),
* step-size independence (exact semigroup) and probability conservation,
* SSA-vs-master-equation distribution agreement within statistical bounds.

The module is opt-in; no solver path imports it by default.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

import numpy as np


@dataclass
class BirthDeathChain:
    """Master equation for the stored-electron count ``n = 0..n_max``.

    ``capture_rate(n)`` is the rate for ``n -> n+1`` (evaluated at the
    departure state; forced to zero at ``n_max``); ``emission_rate(n)`` is
    the rate for ``n -> n-1`` (forced to zero at 0).
    """

    n_max: int
    capture_rate: Callable[[int], float]
    emission_rate: Callable[[int], float]
    state: Optional[np.ndarray] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.n_max < 1:
            raise ValueError("n_max must be >= 1")
        self._lam = np.zeros(self.n_max + 1)
        self._mu = np.zeros(self.n_max + 1)
        for n in range(self.n_max + 1):
            lam = float(self.capture_rate(n)) if n < self.n_max else 0.0
            mu = float(self.emission_rate(n)) if n > 0 else 0.0
            if not np.isfinite(lam) or lam < 0.0:
                raise ValueError(f"capture_rate({n}) must be finite and >= 0")
            if not np.isfinite(mu) or mu < 0.0:
                raise ValueError(f"emission_rate({n}) must be finite and >= 0")
            self._lam[n] = lam
            self._mu[n] = mu

    def initialize(self, p0: Optional[np.ndarray] = None, count: int = 0) -> None:
        """Set the initial distribution (default: all mass at ``count``)."""
        if p0 is None:
            p0 = np.zeros(self.n_max + 1)
            if not 0 <= count <= self.n_max:
                raise ValueError("count must lie in [0, n_max]")
            p0[count] = 1.0
        else:
            p0 = np.asarray(p0, dtype=float).ravel()
            if p0.size != self.n_max + 1:
                raise ValueError("p0 must have length n_max+1")
            if np.any(p0 < 0.0) or abs(float(np.sum(p0)) - 1.0) > 1.0e-9:
                raise ValueError("p0 must be a probability vector")
        self.state = p0.copy()

    def _require_state(self) -> np.ndarray:
        if self.state is None:
            raise RuntimeError("chain state uninitialized; call initialize()")
        return self.state

    def _rates(self) -> Tuple[np.ndarray, np.ndarray]:
        return self._lam, self._mu

    def advance(self, dt: float) -> np.ndarray:
        """Advance the distribution exactly over ``dt`` (uniformization).

        For piecewise-constant rates the update is the exact matrix
        exponential of the generator, so one step of ``dt`` and ``m`` steps
        of ``dt/m`` agree to roundoff (exact semigroup).
        """
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and > 0")
        p = self._require_state()
        lam, mu = self._rates()
        exit_rate = lam + mu
        lam_total = float(np.max(exit_rate))
        if lam_total <= 0.0:
            return p.copy()
        alpha = lam_total * dt

        def r_matvec(v: np.ndarray) -> np.ndarray:
            out = np.empty_like(v)
            out[:] = (1.0 - exit_rate / lam_total) * v
            out[1:] += (lam[:-1] / lam_total) * v[:-1]
            out[:-1] += (mu[1:] / lam_total) * v[1:]
            return out

        # Poisson-weighted Neumann series with tail truncation at 1e-18.
        weight = math.exp(-alpha)
        total = weight
        acc = weight * p
        v = p.copy()
        k = 0
        cutoff = alpha + 12.0 * np.sqrt(max(alpha, 1.0)) + 40.0
        while (k < cutoff) or (weight > 1e-18 and total < 1.0 - 1e-16):
            k += 1
            weight *= alpha / k
            v = r_matvec(v)
            acc += weight * v
            total += weight
            if k > 10_000_000:
                raise RuntimeError("uniformization series failed to converge")
        # Renormalize away the truncated tail (error ~1e-16).
        acc /= float(np.sum(acc))
        self.state = acc
        return acc

    def stationary(self) -> np.ndarray:
        """Stationary distribution from the detailed-balance product form."""
        lam, mu = self._rates()
        log_pi = np.zeros(self.n_max + 1)
        for n in range(1, self.n_max + 1):
            if mu[n] <= 0.0:
                log_pi[n:] = -np.inf
                break
            ratio = lam[n - 1] / mu[n]
            log_pi[n] = log_pi[n - 1] + (np.log(ratio) if ratio > 0.0 else -np.inf)
        finite = np.isfinite(log_pi)
        pi = np.zeros(self.n_max + 1)
        if np.any(finite):
            m = np.max(log_pi[finite])
            pi[finite] = np.exp(log_pi[finite] - m)
        pi /= float(np.sum(pi))
        return pi

    def mean(self) -> float:
        p = self._require_state()
        return float(np.dot(np.arange(self.n_max + 1, dtype=float), p))

    def survival(self, threshold: int) -> float:
        """P(n >= threshold): the retained-state probability."""
        if not 0 <= threshold <= self.n_max:
            raise ValueError("threshold must lie in [0, n_max]")
        p = self._require_state()
        return float(np.sum(p[threshold:]))

    def tail_below(self, threshold: int) -> float:
        """P(n < threshold): the raw BER-style tail mass, exact from the CDF."""
        return 1.0 - self.survival(threshold)


@dataclass
class GillespieSampler:
    """Exact SSA trajectories over a :class:`BirthDeathChain`'s rates."""

    chain: BirthDeathChain
    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def run_trajectory(
        self, t_final: float, n0: int, t_start: float = 0.0,
    ) -> Tuple[int, float]:
        """Advance one exact trajectory; return (final count, final time)."""
        if not np.isfinite(t_final) or t_final <= t_start:
            raise ValueError("t_final must be finite and > t_start")
        if not 0 <= n0 <= self.chain.n_max:
            raise ValueError("n0 must lie in [0, n_max]")
        lam, mu = self.chain._rates()
        t = float(t_start)
        n = int(n0)
        while t < t_final:
            total = lam[n] + mu[n]
            if total <= 0.0:
                break
            t += self._rng.exponential(1.0 / total)
            if t >= t_final:
                break
            if self._rng.random() * total < lam[n]:
                n += 1
            else:
                n -= 1
        return n, t

    def sample_counts(
        self, t_final: float, n0: int, n_samples: int,
    ) -> np.ndarray:
        """Empirical distribution of the stored count at ``t_final``."""
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")
        counts = np.empty(n_samples, dtype=int)
        for s in range(n_samples):
            n, _ = self.run_trajectory(t_final, n0)
            counts[s] = n
        return counts

    def sample_first_passage(
        self,
        threshold: int,
        n0: int,
        n_samples: int,
        t_max: float,
    ) -> np.ndarray:
        """First-passage times to ``n < threshold`` (NaN when not reached)."""
        if not 0 <= threshold <= self.chain.n_max:
            raise ValueError("threshold must lie in [0, n_max]")
        if not np.isfinite(t_max) or t_max <= 0.0:
            raise ValueError("t_max must be finite and > 0")
        lam, mu = self.chain._rates()
        times = np.full(n_samples, np.nan)
        for s in range(n_samples):
            t = 0.0
            n = int(n0)
            while n >= threshold and t < t_max:
                total = lam[n] + mu[n]
                if total <= 0.0:
                    t = np.inf
                    break
                t += self._rng.exponential(1.0 / total)
                if self._rng.random() * total < lam[n]:
                    n += 1
                else:
                    n -= 1
            times[s] = t if t <= t_max else np.nan
        return times
