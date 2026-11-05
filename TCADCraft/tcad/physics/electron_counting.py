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
  method). For piecewise-constant rates it approximates the matrix exponential
  without a time discretization, using a truncated series and floating-point
  arithmetic. It returns the full finite-state distribution, so tail masses
  can be summed without rare-event sampling. This does not certify relative
  error for arbitrarily small probabilities or experimentally calibrated BER.
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


# Exact powers of two give probability products exponent headroom without
# depending on platform-specific longdouble precision/range. Stochastic
# vectors/matrices scaled by 2**256 and their products fit safely in float64.
_PROBABILITY_SCALE = 256


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
        if (isinstance(self.n_max, (bool, np.bool_))
                or not isinstance(self.n_max, (int, np.integer)) or self.n_max < 1):
            raise ValueError("n_max must be an integer >= 1")
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
            count = self._state_index(count, 'count')
            p0[count] = 1.0
        else:
            p0 = self._probability_vector(p0)
        self.state = p0.copy()

    def _state_index(self, value: int, name: str) -> int:
        if (isinstance(value, (bool, np.bool_))
                or not isinstance(value, (int, np.integer)) or not 0 <= value <= self.n_max):
            raise ValueError(f"{name} must be an integer in [0, n_max]")
        return int(value)

    def _probability_vector(self, values: np.ndarray) -> np.ndarray:
        raw = np.asarray(values)
        if raw.dtype.kind not in 'fiu' or raw.ndim != 1 or raw.size != self.n_max + 1:
            raise ValueError("state must be a one-dimensional real probability vector of length n_max+1")
        if not np.all(np.isfinite(raw)) or np.any(raw < 0.) or np.any(raw > 1.):
            raise ValueError("state must contain finite probabilities in [0, 1] summing to one")
        with np.errstate(under='ignore'):
            p = np.asarray(raw, dtype=float)
        if np.any((raw != 0.) & (p == 0.)):
            raise ValueError("nonzero state probabilities are not representable in float64")
        if abs(math.fsum(p) - 1.) > 1.e-9:
            raise ValueError("state probabilities must sum to one")
        return p

    def _require_state(self) -> np.ndarray:
        if self.state is None:
            raise RuntimeError("chain state uninitialized; call initialize()")
        # state is publicly mutable; recheck before observations and updates.
        return self._probability_vector(self.state)

    def _rates(self) -> Tuple[np.ndarray, np.ndarray]:
        if (not np.all(np.isfinite(self._lam)) or not np.all(np.isfinite(self._mu))
                or np.any(self._lam < 0.) or np.any(self._mu < 0.)):
            raise ValueError("transition rates must be finite and >= 0")
        return self._lam, self._mu

    def advance(self, dt: float) -> np.ndarray:
        """Advance over ``dt`` by a truncated uniformization series.

        The underlying matrix exponential has the semigroup property for
        piecewise-constant rates. Computed steps have series truncation and
        roundoff error; they carry no certified relative rare-tail budget.
        The finite float64 duration is processed atomically across all local
        blocks/squarings. Dimensional rate sums/products may exceed float64;
        unrepresentable positive normalized rates or tiny Poisson parameters
        are rejected without replacing the previously accepted state.
        Internal powers of two protect subnormal contributions from premature
        rounding during sums/products; only the completed request is exported
        to the public probability range. This is not an error certificate.
        """
        if (isinstance(dt, (bool, np.bool_))
                or not isinstance(dt, (int, float, np.integer, np.floating))):
            raise ValueError("dt must be a finite positive real scalar representable in float64")
        try:
            dt = float(dt)
        except (OverflowError, ValueError) as exc:
            raise ValueError("dt must be representable in float64") from exc
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and > 0")
        # Work only on local snapshots. No block or squaring commits state;
        # the complete requested interval succeeds or leaves the old state.
        p = self._require_state().copy()
        rates = self._rates()
        lam, mu = rates[0].copy(), rates[1].copy()
        scale = max(float(np.max(lam)), float(np.max(mu)))
        if scale == 0.0:
            return p.copy()
        # Construct Q/rate without ever adding two large dimensional rates.
        with np.errstate(under='ignore'):
            scaled_lam, scaled_mu = lam / scale, mu / scale
            exit_scaled = scaled_lam + scaled_mu
            rate_scaled = float(np.max(exit_scaled))
            birth, death = scaled_lam / rate_scaled, scaled_mu / rate_scaled
        if np.any((lam > 0.) & (birth == 0.)) or np.any((mu > 0.) & (death == 0.)):
            raise ValueError("positive normalized transition rates are not representable in float64")
        stay = 1.0 - exit_scaled / rate_scaled
        # rate*dt may overflow even when exp(Q*dt) is a valid stochastic
        # matrix. Keep its mantissa and (unbounded Python integer) exponent.
        rm, re = math.frexp(scale)
        sm, se = math.frexp(rate_scaled)
        tm, te = math.frexp(dt)
        mantissa, adjustment = math.frexp(rm * sm * tm)
        exponent = re + se + te + adjustment
        alpha = math.ldexp(mantissa, exponent) if exponent <= 13 else None
        if alpha == 0.0:
            raise ValueError("positive rate-time product is not representable in float64")
        if alpha is None or alpha > 4096.0:
            squarings = exponent - 1 if mantissa == .5 else exponent
            local_alpha = math.ldexp(mantissa, exponent - squarings)
            candidate = self._advance_scaled(p, local_alpha, squarings, birth, death, stay)
        else:
            # Split the dimensionless Poisson parameter without separately
            # rounding a physical sub-duration and multiplying it by the rate.
            n_steps = max(1, int(math.ceil(alpha / 40.0)))
            candidate = np.ldexp(p, _PROBABILITY_SCALE)
            for _ in range(n_steps):
                candidate = self._uniformization_step(
                    candidate, alpha / n_steps, birth, death, stay, _PROBABILITY_SCALE)
                candidate = self._normalize_probability(
                    candidate, _PROBABILITY_SCALE, _PROBABILITY_SCALE)
            candidate = self._normalize_probability(candidate, _PROBABILITY_SCALE)
        candidate = self._probability_vector(candidate)
        self.state = candidate.copy()
        return candidate.copy()

    def _uniformization_step(self, p: np.ndarray, alpha: float,
                             birth: np.ndarray, death: np.ndarray,
                             stay: np.ndarray, binary_scale: int = 0) -> np.ndarray:
        """One local series, without mutating the public chain state."""
        def r_matvec(v: np.ndarray) -> np.ndarray:
            out = np.empty_like(v)
            out[:] = stay * v
            out[1:] += birth[:-1] * v[:-1]
            out[:-1] += death[1:] * v[1:]
            return out

        # A small global tail or weight is not a relative error criterion for
        # remote states: R**k may only reach them after many jumps. Include
        # every positive scaled weight produced by the recurrence. Scale both
        # factors before multiplying: subnormal mass split across Poisson
        # terms can otherwise disappear even in an absorbing state.
        weight = math.ldexp(math.exp(-alpha), _PROBABILITY_SCALE)
        v = np.ldexp(p, _PROBABILITY_SCALE - binary_scale)
        acc = weight * v
        k = 0
        while weight > 0.0:
            k += 1
            weight *= alpha / k
            if weight == 0.0:
                break
            v = r_matvec(v)
            acc += weight * v
            if k > 10_000_000:
                raise RuntimeError("uniformization series failed to converge")
        # Only a finite nonnegative near-unit candidate may be normalized.
        # This removes small mass error, not a certified rare-tail error.
        return self._normalize_probability(acc, 2 * _PROBABILITY_SCALE, binary_scale)

    def _normalize_probability(self, values: np.ndarray, binary_scale: int = 0,
                               output_scale: int = 0) -> np.ndarray:
        # A computed near-unit mass can exceed one by roundoff, including a
        # single absorbing-state entry. Audit before normalization, then apply
        # the strict public probability checks to the normalized candidate.
        raw = np.asarray(values)
        if (raw.dtype.kind not in 'fiu' or raw.ndim != 1 or raw.size != self.n_max + 1
                or not np.all(np.isfinite(raw)) or np.any(raw < 0.)):
            raise ValueError("invalid computed probability distribution")
        mass = math.ldexp(math.fsum(raw), -binary_scale)
        if abs(mass - 1.) > 1.e-9:
            raise ValueError("computed distribution lost probability mass")
        normalized = np.ldexp(raw / mass, output_scale - binary_scale)
        # Only the final requested distribution is rounded to the public
        # float64 range; block boundaries retain the internal exponent range.
        return self._probability_vector(normalized) if output_scale == 0 else normalized

    def _advance_scaled(self, p: np.ndarray, local_alpha: float, squarings: int,
                        birth: np.ndarray, death: np.ndarray,
                        stay: np.ndarray) -> np.ndarray:
        """Positive transition matrix with uniformization and squaring.

        For long holds, O(alpha) repeated vector steps are impractical.
        Build exp(Q*dt/2**s) at alpha <= 1, then square s times. Matrices
        retain a binary scale through squaring and the final matrix-vector
        product. Column normalization removes roundoff in mass, not missing
        physical time.
        No steady-state approximation or timestep cap is used.
        """
        size = self.n_max + 1
        power = np.ldexp(np.eye(size), _PROBABILITY_SCALE)
        weight = math.ldexp(math.exp(-local_alpha), _PROBABILITY_SCALE)
        transition = weight * power
        k = 0
        while weight > 0.0:
            k += 1
            weight *= local_alpha / k
            if weight == 0.0:
                break
            # R is tridiagonal. Apply it directly to each column rather than
            # doing a dense product for every additional rare-tail term.
            next_power = stay[:, None] * power
            next_power[1:] += birth[:-1, None] * power[:-1]
            next_power[:-1] += death[1:, None] * power[1:]
            power = next_power
            transition += weight * power
            if k > 10_000_000:
                raise RuntimeError("uniformization matrix series failed to converge")
        transition = np.ldexp(transition, -_PROBABILITY_SCALE)
        transition = self._normalize_transition(transition, _PROBABILITY_SCALE)
        for _ in range(squarings):
            transition = np.ldexp(transition @ transition, -_PROBABILITY_SCALE)
            transition = self._normalize_transition(transition, _PROBABILITY_SCALE)
        return self._normalize_probability(
            transition @ np.ldexp(p, _PROBABILITY_SCALE), 2 * _PROBABILITY_SCALE)

    @staticmethod
    def _normalize_transition(transition: np.ndarray, binary_scale: int = 0) -> np.ndarray:
        if not np.all(np.isfinite(transition)) or np.any(transition < 0.):
            raise RuntimeError("invalid transition matrix during probability propagation")
        sums = np.ldexp(transition.sum(axis=0), -binary_scale)
        if not np.all(np.isfinite(sums)) or np.any(abs(sums - 1.) > 1.e-9):
            raise RuntimeError("transition matrix lost probability mass")
        return transition / sums

    def stationary(self) -> np.ndarray:
        """Unique stationary distribution, including a unique absorbing class.

        Zero-rate edges can create multiple closed communicating classes. Their
        stationary mixtures are not unique, so this initial-state-independent
        API rejects them instead of choosing one silently. Positive class
        probabilities that cannot be exported in float64 are also rejected.
        """
        lam, mu = self._rates()
        closed = []
        begin = 0
        for end in range(self.n_max + 1):
            # A strongly connected interval extends only across two-way edges.
            if end < self.n_max and lam[end] > 0. and mu[end + 1] > 0.:
                continue
            if mu[begin] == 0. and lam[end] == 0.:
                closed.append((begin, end))
            begin = end + 1
        if len(closed) != 1:
            raise ValueError("stationary distribution is not unique: multiple closed communicating classes")
        begin, end = closed[0]
        log_pi = np.zeros(end - begin + 1)
        for n in range(begin + 1, end + 1):
            # log(lam/mu) loses representable stationary tails if the raw
            # ratio first overflows or underflows. Form the two logs separately.
            log_pi[n - begin] = log_pi[n - begin - 1] + math.log(lam[n - 1]) - math.log(mu[n])
        with np.errstate(under='ignore'):
            weights = np.exp(log_pi - np.max(log_pi))
            weights /= math.fsum(weights)
        if np.any(weights == 0.) or not np.all(np.isfinite(weights)):
            raise ValueError("positive stationary probabilities are not representable in float64")
        pi = np.zeros(self.n_max + 1)
        pi[begin:end + 1] = weights
        return pi

    def mean(self) -> float:
        p = self._require_state()
        return float(np.dot(np.arange(self.n_max + 1, dtype=float), p))

    def survival(self, threshold: int) -> float:
        """P(n >= threshold): the retained-state probability."""
        threshold = self._state_index(threshold, 'threshold')
        p = self._require_state()
        return math.fsum(p[threshold:])

    def tail_below(self, threshold: int) -> float:
        """P(n < threshold), summed directly to retain sub-epsilon tail mass.

        Accuracy is limited by the supplied/computed state probabilities;
        this observation does not certify their propagation error.
        """
        threshold = self._state_index(threshold, 'threshold')
        return math.fsum(self._require_state()[:threshold])


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
        if (not np.isfinite(t_start) or not np.isfinite(t_final)
                or t_final <= t_start):
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
        # A sampled next event beyond the horizon is not elapsed time.
        # Absorbing states likewise remain at their state through t_final.
        return n, float(t_final)

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
