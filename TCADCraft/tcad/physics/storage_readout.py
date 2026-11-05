"""Finite-count storage readout and coding metrics for a declared channel.

Rows of C are written symbols, columns are decoded symbols. Fixed priors
give mutual information, not capacity, net density or an ECC guarantee.
The default code is fixed-width binary-reflected Gray; non-power-of-two
alphabets have unused bit words. This module supplies no experimental rates.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Optional, Sequence

import numpy as np

from .electron_counting import BirthDeathChain

SCHEMA = "finite_count_storage_readout_v1"
MASS_ATOL = 1e-12


def _probabilities(values, name: str, dimensions: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if (array.ndim != dimensions or not np.all(np.isfinite(array))
            or np.any(array < 0)):
        raise ValueError(f"{name} must be finite nonnegative probabilities")
    return array


def symbol_priors(n_levels: int, priors=None) -> np.ndarray:
    if not isinstance(n_levels, int) or isinstance(n_levels, bool) or n_levels < 2:
        raise ValueError("n_levels must be an integer >= 2")
    p = np.full(n_levels, 1 / n_levels) if priors is None else _probabilities(priors, "priors", 1)
    if p.size != n_levels or abs(math.fsum(p) - 1) > MASS_ATOL:
        raise ValueError("priors must have one entry per symbol and sum to one")
    return p.copy()


def binary_codewords(n_levels: int, codes: Optional[Sequence[str]] = None) -> tuple[str, ...]:
    if not isinstance(n_levels, int) or isinstance(n_levels, bool) or n_levels < 2:
        raise ValueError("n_levels must be an integer >= 2")
    if codes is None:
        bits = (n_levels - 1).bit_length()
        return tuple(f"{i ^ (i >> 1):0{bits}b}" for i in range(n_levels))
    words = tuple(codes)
    if (len(words) != n_levels or not all(isinstance(w, str) and w for w in words)
            or len(set(words)) != n_levels
            or len({len(w) for w in words}) != 1
            or any(set(w) - {"0", "1"} for w in words)):
        raise ValueError("codes must be distinct binary strings of one fixed positive width")
    return words


@dataclass
class StorageReadout:
    confusion_matrix: np.ndarray
    priors: np.ndarray
    codewords: tuple[str, ...]
    symbol_error_rate: float
    bit_error_rate: float
    mutual_information_bits: float
    input_entropy_bits: float
    symbol_error_by_written: np.ndarray
    bit_error_by_written: np.ndarray
    row_mass_error: float

    @property
    def worst_symbol_error(self) -> float:
        return float(np.max(self.symbol_error_by_written))

    @property
    def worst_bit_error(self) -> float:
        return float(np.max(self.bit_error_by_written))

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "confusion_matrix": self.confusion_matrix.tolist(),
            "symbol_priors": self.priors.tolist(),
            "codewords": list(self.codewords),
            "code_bits": len(self.codewords[0]),
            "unused_codewords": 2 ** len(self.codewords[0]) - len(self.codewords),
            "symbol_error_rate": self.symbol_error_rate,
            "bit_error_rate": self.bit_error_rate,
            "mutual_information_bits": self.mutual_information_bits,
            "input_entropy_bits": self.input_entropy_bits,
            "symbol_error_by_written": self.symbol_error_by_written.tolist(),
            "bit_error_by_written": self.bit_error_by_written.tolist(),
            "worst_symbol_error": self.worst_symbol_error,
            "worst_bit_error": self.worst_bit_error,
            "row_mass_error": self.row_mass_error,
            "information_scope": "fixed_prior_mutual_information_not_capacity_or_net_density",
        }


def channel_metrics(confusion, priors=None, codes=None) -> StorageReadout:
    c = _probabilities(confusion, "confusion matrix", 2)
    if c.shape[0] < 2 or c.shape[0] != c.shape[1]:
        raise ValueError("confusion matrix must be square with at least two symbols")
    mass_error = float(np.max(np.abs(c.sum(axis=1) - 1)))
    if mass_error > MASS_ATOL:
        raise ValueError("each confusion row must sum to one")
    k = len(c)
    p = symbol_priors(k, priors)
    words = binary_codewords(k, codes)
    hamming = np.array([[sum(a != b for a, b in zip(left, right))
                         for right in words] for left in words], dtype=float)
    # Sum actual error events rather than subtracting near-one success.
    off_diagonal = c.copy()
    np.fill_diagonal(off_diagonal, 0)
    symbol_errors = off_diagonal.sum(axis=1)
    bit_errors = (c * hamming).sum(axis=1) / len(words[0])
    joint = p[:, None] * c
    output = joint.sum(axis=0)
    support = joint > 0
    safe_output = np.broadcast_to(output, c.shape)
    information = float(np.sum(joint[support] * (
        np.log2(c[support]) - np.log2(safe_output[support]))))
    input_support = p > 0
    entropy = float(-np.sum(p[input_support] * np.log2(p[input_support])))
    # Suppress only roundoff beyond the information-theoretic bounds.
    information = min(max(information, 0.0), entropy)
    return StorageReadout(c.copy(), p, words, float(p @ symbol_errors),
                          float(p @ bit_errors), information, entropy,
                          symbol_errors, bit_errors, mass_error)


def decode_distributions(distributions, thresholds, priors=None, codes=None) -> StorageReadout:
    """Decode integer counts: n >= ceil(threshold) selects the upper bin."""
    probabilities = _probabilities(distributions, "count distributions", 2)
    k, count_states = probabilities.shape
    edges = np.asarray(thresholds, dtype=float)
    if (k < 2 or count_states < 2 or edges.ndim != 1 or len(edges) != k - 1
            or not np.all(np.isfinite(edges))):
        raise ValueError("one finite threshold is required between each pair of symbols")
    boundaries = np.ceil(edges)
    if (boundaries[0] < 1 or boundaries[-1] >= count_states
            or np.any(np.diff(boundaries) <= 0)):
        raise ValueError("integer decision bins must be nonempty and strictly ordered")
    if np.max(np.abs(probabilities.sum(axis=1) - 1)) > MASS_ATOL:
        raise ValueError("each count distribution must sum to one")
    cuts = [0, *boundaries.astype(int).tolist(), count_states]
    confusion = np.column_stack([probabilities[:, lo:hi].sum(axis=1)
                                 for lo, hi in zip(cuts[:-1], cuts[1:])])
    return channel_metrics(confusion, priors, codes)


@lru_cache(maxsize=4096)
def _retained_count(n_max: int, initial: int, capture: float, loss: float,
                    duration: float, audit_overflow: bool) -> tuple[np.ndarray, float]:
    chain = BirthDeathChain(n_max, lambda n: capture, lambda n: loss * n)
    chain.initialize(count=initial)
    if duration > 0:
        chain.advance(duration)
    result = chain.state.copy()
    result.flags.writeable = False
    overflow = 0.0
    if audit_overflow and capture > 0 and duration > 0:
        # Absorbing extra state counts any attempt to leave the numerical
        # domain. End-point occupancy alone misses paths that left and returned.
        extended = BirthDeathChain(n_max + 1, lambda n: capture,
                                  lambda n: 0 if n == n_max + 1 else loss * n)
        extended.initialize(count=initial)
        extended.advance(duration)
        overflow = float(extended.state[-1])
    return result, overflow


def electron_storage_readout(counts, n_max: int, capture_rate: float,
                             loss_rate: float, duration: float, *,
                             priors=None, codes=None, numerical_upper_boundary=True,
                             overflow_tolerance=1e-10) -> tuple[StorageReadout, dict]:
    """Finite-state readout with explicit physical/numerical cap semantics.

    For a numerical cap, the absorbing-domain escape probability bounds
    the effect of artificially reflecting paths at that cap. This estimate
    does not certify floating-point tails or validate material rate data.
    """
    values = np.asarray(counts)
    if (values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values))
            or np.any(values != np.rint(values)) or np.any(np.diff(values) <= 0)):
        raise ValueError("programmed counts must be distinct increasing integers")
    if not isinstance(n_max, (int, np.integer)) or isinstance(n_max, bool) or n_max < 1:
        raise ValueError("n_max must be a positive integer")
    if values[0] < 0 or values[-1] > n_max:
        raise ValueError("programmed counts must lie in the chain domain")
    for name, value in (("capture_rate", capture_rate), ("loss_rate", loss_rate),
                        ("duration", duration), ("overflow_tolerance", overflow_tolerance)):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and >= 0")
    integer_counts = values.astype(int)
    if not isinstance(numerical_upper_boundary, bool):
        raise ValueError("numerical_upper_boundary must be boolean")
    if overflow_tolerance > 1:
        raise ValueError("overflow_tolerance must not exceed one")
    distributions, escapes = zip(*[_retained_count(
        int(n_max), int(count), float(capture_rate), float(loss_rate), float(duration),
        bool(numerical_upper_boundary)) for count in integer_counts])
    thresholds = (integer_counts[:-1] + integer_counts[1:]) / 2.0
    readout = decode_distributions(np.vstack(distributions), thresholds, priors, codes)
    max_escape = max(escapes)
    validation = {
        "numerical_valid": max_escape <= overflow_tolerance,
        "trust_scope": "numerical_consistency_of_declared_finite_state_model",
        "physical_validated": False,
        "rate_model": "constant_capture_linear_per_electron_loss",
        "capture_rate_per_s": capture_rate,
        "loss_rate_per_electron_s": loss_rate,
        "duration_s": duration,
        "programmed_counts": integer_counts.tolist(),
        "decision_thresholds": thresholds.tolist(),
        "decision_boundaries": np.ceil(thresholds).astype(int).tolist(),
        "decision_tie": "upper_symbol",
        "chain_max_count": int(n_max),
        "upper_boundary": "numerical_reflection_audited" if numerical_upper_boundary
                          else "declared_physical_capacity_reflection",
        "domain_escape_probability_by_written": list(escapes),
        "max_domain_escape_probability": max_escape,
        "overflow_tolerance": overflow_tolerance,
        "row_mass_error": readout.row_mass_error,
        "probability_tail_accuracy": "not_certified_below_float_and_domain_error_budgets",
        "read_model": "ideal_integer_count_no_measurement_noise",
    }
    if not validation["numerical_valid"]:
        validation["failure_reason"] = "numerical_count_domain_escape_exceeds_tolerance"
    return readout, validation
