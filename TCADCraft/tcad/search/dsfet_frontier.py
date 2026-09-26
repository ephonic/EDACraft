"""E4 cold-source / Dirac-source FET explorer (plan0918 direction-2).

Design question (comment7 4.2): a graphene Dirac source has a linear DOS
that vanishes at the Dirac point, filtering the Boltzmann hot tail - the
injected electrons are "cold" and the subthreshold swing can beat 60
mV/dec.  The price: the same vanishing DOS throttles the on-current
(source resistance), and the filter needs precise gate-source electrostatics
that short channels destroy.

Compact model (declared)
------------------------
Injection spectrum of the Dirac source with Fermi level ``mu`` above the
Dirac point ``E_D = 0``::

    S(E) = E * f((E - mu)/kT)          (linear DOS, degenerate Fermi tail)

The supply-side energy filter cuts the hot tail at ``E_cut`` (thermally
broadened by ~kT); the gate-controlled barrier ``E_b(Vg) = E_b0 - Vg``
selects how much of the filtered spectrum injects::

    I(Vg) ~ int S(E) * step(E - E_b) * step(E_cut - E) dE

With the filter open (E_b well below E_cut) the swing recovers the
Boltzmann-plus-Dirac-DOS limit ``SS = 60*(1 + kT/w) > 60``: a vanishing DOS
ALONE does not cool the tail.  The steep window is the few-kT region under
the filter edge, where ``I ~ (E_cut - E_b)^2`` and

    SS ~ 1.151 * (E_cut - E_b)  [mV/dec, x in meV]

so sub-60 requires ``E_cut - E_b < 52 meV`` - a ~50 mV gate window, the
quantified narrowness of comment7 4.2.  Degenerate filling (mu rising past
the window) flattens the tail and degrades SS - the Ion-SS tradeoff.
Short-channel source-field rounding smears the barrier cutoff with
``sigma_sc = sigma0 * exp(-Lg/lambda_sc)``; the SS change between nominal
and half-length gates is the robustness axis.

Objectives (all maximized)
--------------------------
``steepness``     -window-averaged SS [mV/dec] over the readout decades
``log10_ion``    log10 on-current at Vg = Vdd
``robustness``   -(SS at 0.5*Lg0) + (SS at Lg0): the flatter the SS
                  degradation under channel scaling, the better

Design variables
----------------
``filter_window_meV`` (w at threshold), ``source_fermi_meV`` (mu),
``lambda_sc_nm`` (source-side screening length), ``vdd``.

Analytic goldens (tests): the Boltzmann-limit closed form SS = 60*w/(w+kT);
the w -> infinity thermal limit 60 mV/dec; monotone degradation with mu and
with lambda_sc; numeric-grid consistency.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts
from .attribution import attach_attributions
K_B_MEV_300K = 25.85  # kT at 300 K [meV]
SS_THERMAL = 60.0  # kT/q * ln10 at 300 K [mV/dec]


def k_b_mev(temperature_K: float = 300.0) -> float:
    """kT in meV at the given temperature."""
    return K_B_MEV_300K * temperature_K / 300.0


@dataclass
class DsFetConfig:
    filter_window_meV: Tuple[float, float] = (80.0, 400.0)
    filter_cutoff_meV: Tuple[float, float] = (60.0, 350.0)
    source_fermi_meV: Tuple[float, float] = (-30.0, 400.0)
    lambda_sc_nm: Tuple[float, float] = (3.0, 30.0)
    vdd: Tuple[float, float] = (0.3, 0.7)
    lg0_nm: float = 20.0
    sigma0_meV: float = 120.0
    ss_decades: float = 3.0
    n_vg: int = 61
    n_energy: int = 401
    mutation_sigma: float = 0.18
    temperature_K: float = 300.0  # NEW: operating temperature

    def bounds(self) -> Dict[str, Tuple[float, float]]:
        return {
            "filter_window_meV": self.filter_window_meV,
            "filter_cutoff_meV": self.filter_cutoff_meV,
            "source_fermi_meV": self.source_fermi_meV,
            "lambda_sc_nm": self.lambda_sc_nm,
            "vdd": self.vdd,
        }


@dataclass
class DsFetCandidate:
    x: Dict[str, float]
    ss_window_mV_per_dec: float = float("nan")
    ss_short_mV_per_dec: float = float("nan")
    ion: float = float("nan")
    ioff: float = float("nan")
    trusted: bool = False
    violations: List[str] = field(default_factory=list)

    @property
    def objectives(self) -> np.ndarray:
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        degradation = self.ss_short_mV_per_dec - self.ss_window_mV_per_dec
        return np.array([
            -self.ss_window_mV_per_dec,
            float(np.log10(max(self.ion, 1e-30))),
            -degradation,
        ])

    def as_dict(self) -> Dict[str, object]:
        out = dict(self.x)
        out.update({
            "ss_window_mV_per_dec": self.ss_window_mV_per_dec,
            "ss_short_mV_per_dec": self.ss_short_mV_per_dec,
            "ion_A_per_um": self.ion,
            "ioff_A_per_um": self.ioff,
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def _spectrum_integral(
    barrier_meV: float,
    mu: float,
    energy_grid: np.ndarray,
    sigma_meV: float = 0.0,
    cutoff_meV: float = float("inf"),
    temperature_K: float = 300.0,
) -> float:
    """Filtered source injection integral.

    ``int E * f((E-mu)/kT) * step(E - barrier) * step(cutoff - E) dE`` with
    Gaussian smearing of the barrier cutoff (``sigma_meV``, short-channel
    rounding) and a thermally broadened supply filter edge at ``cutoff_meV``
    (sharpness ~kT; an arbitrary sharper filter would need its own model).
    """
    kT = k_b_mev(temperature_K)
    fermi = 1.0 / (1.0 + np.exp(np.clip((energy_grid - mu) / kT, -300.0, 300.0)))
    spectrum = energy_grid * fermi
    spectrum = np.where(energy_grid > 0.0, spectrum, 0.0)
    if np.isfinite(cutoff_meV):
        zc = (energy_grid - cutoff_meV) / (kT * math.sqrt(2.0))
        supply = 0.5 * (1.0 - np.vectorize(math.erf)(zc))
        spectrum = spectrum * supply
    if sigma_meV > 0.0:
        # Soft cutoff: 0.5*(1+erf((E-barrier)/sigma)) without scipy.  Floor
        # sigma at two energy-grid steps: an unresolved erf transition
        # (sigma << dE) aliases between grid nodes and makes the trapezoid
        # integral oscillate point to point.
        d_e = float(energy_grid[1] - energy_grid[0]) if len(energy_grid) > 1 else 1.0
        sigma_eff = max(sigma_meV, 2.0 * d_e)
        z = (energy_grid - barrier_meV) / (sigma_eff * math.sqrt(2.0))
        cutoff = 0.5 * (1.0 + np.vectorize(math.erf)(z))
    else:
        cutoff = (energy_grid >= barrier_meV).astype(float)
    return float(np.trapezoid(spectrum * cutoff, energy_grid))


def _transfer_curve(
    x: Dict[str, float],
    config: DsFetConfig,
    lg_nm: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Id(Vg) for a given gate length (arbitrary units, declared scale-free)."""
    kT = k_b_mev(config.temperature_K)
    energy = np.linspace(-50.0, 1200.0, config.n_energy)
    sigma = config.sigma0_meV * math.exp(-lg_nm / x["lambda_sc_nm"])
    vg = np.linspace(0.0, x["vdd"], config.n_vg)
    e_b0 = x["filter_window_meV"] + 0.0
    currents = np.array([
        _spectrum_integral(e_b0 - float(v) * 1000.0, x["source_fermi_meV"],
                           energy, sigma_meV=sigma,
                           cutoff_meV=x["filter_cutoff_meV"],
                           temperature_K=config.temperature_K)
        for v in vg
    ])
    return vg, currents


def _window_swing(vg: np.ndarray, currents: np.ndarray, decades: float) -> float:
    """Mean subthreshold swing over the usable dynamic range.

    The window adapts to the available on/off ratio (an empty Dirac source
    has only ~1-2 decades - the cold-source Ion penalty itself), and
    saturated intervals (log-difference below 1e-6, where the barrier has
    dropped below the Dirac point and the current no longer follows the
    gate) are excluded from the average.
    """
    ion = float(currents[-1])
    ioff = float(currents[0])
    if not np.isfinite(ion) or ion <= 0.0:
        return float("inf")
    available = math.log10(max(ion / max(ioff, 1e-300), 1.0)) - 0.3
    decades_use = min(decades, available)
    if decades_use < 0.3:
        return float("inf")
    # Restrict to the true subthreshold region: above the floor and below
    # the current where the barrier is ~1kT above the Dirac point (past
    # that the spectrum saturates and the swing flattens artificially).
    ceiling = 0.5 * (ion + max(ioff, 1e-300))
    floor = max(ion / 10.0 ** decades_use, ioff * 1.5, 1e-300)
    log_i = np.log10(np.maximum(currents, 1e-300))
    swings = []
    for k in range(1, len(vg)):
        if floor < currents[k - 1] < ceiling and currents[k] <= ceiling:
            if currents[k] > currents[k - 1]:
                dlog = log_i[k] - log_i[k - 1]
                if dlog > 1.0e-6:
                    swings.append((vg[k] - vg[k - 1]) / dlog)
    if not swings:
        return float("inf")
    return float(np.mean(swings)) * 1000.0


def evaluate_dsfet_candidate(
    x: Dict[str, float],
    config: Optional[DsFetConfig] = None,
) -> DsFetCandidate:
    """Evaluate one E4 candidate (numeric-grid compact model)."""
    config = config or DsFetConfig()
    clipped = {}
    for name, (lo, hi) in config.bounds().items():
        value = float(np.clip(x[name], lo, hi))
        if not np.isfinite(value):
            raise ValueError(f"design variable {name} became non-finite")
        clipped[name] = value
    candidate = DsFetCandidate(x=clipped)

    if clipped["vdd"] * 1000.0 <= clipped["filter_window_meV"]:
        candidate.violations.append(
            "vdd below the filter window: the on state is never reached"
        )
        return candidate
    if clipped["filter_cutoff_meV"] >= clipped["filter_window_meV"]:
        candidate.violations.append(
            "supply filter open at Vg=0 (cutoff above the barrier): no off state"
        )
        return candidate
    vg, currents = _transfer_curve(clipped, config, config.lg0_nm)
    ion = float(currents[-1])
    ioff = float(currents[0])
    if not np.isfinite(ion) or ion <= 0.0:
        candidate.violations.append("non-positive on-current")
        return candidate
    if not np.isfinite(ioff) or ioff < 0.0:
        candidate.violations.append("invalid off-current")
        return candidate
    ss_long = _window_swing(vg, currents, config.ss_decades)
    if not np.isfinite(ss_long) or ss_long <= 0.0:
        candidate.violations.append("no monotone swing intervals")
        return candidate

    vg_s, currents_s = _transfer_curve(clipped, config, 0.5 * config.lg0_nm)
    ss_short = _window_swing(vg_s, currents_s, config.ss_decades)
    if not np.isfinite(ss_short) or ss_short <= 0.0:
        ss_short = 10.0 * ss_long  # heavily degraded: cap at 10x

    candidate.ss_window_mV_per_dec = ss_long
    candidate.ss_short_mV_per_dec = ss_short
    candidate.ion = ion
    candidate.ioff = ioff
    candidate.trusted = True
    return candidate


@dataclass
class DsFetFrontierResult:
    population: List[DsFetCandidate]
    front: List[DsFetCandidate]
    history: List[Dict[str, object]] = field(default_factory=list)

    def to_rows(self):
        return [c.as_dict() for c in self.population]

    def front_rows(self):
        return [c.as_dict() for c in self.front]


def evolve_dsfet_frontier(
    config: Optional[DsFetConfig] = None,
    population_size: int = 16,
    generations: int = 8,
    seed: int = 0,
    init_population: Optional[List[Dict[str, float]]] = None,
) -> DsFetFrontierResult:
    """Run the E4 NSGA-II loop (trusted candidates only enter the front)."""
    config = config or DsFetConfig()
    if population_size < 4:
        raise ValueError("population_size must be >= 4")
    if generations < 1:
        raise ValueError("generations must be >= 1")
    rng = random.Random(seed)
    bounds = config.bounds()

    designs: List[Dict[str, float]] = []
    if init_population:
        designs.extend(
            {k: float(np.clip(d[k], *bounds[k])) for k in bounds}
            for d in init_population
        )
    while len(designs) < population_size:
        designs.append({
            name: rng.uniform(lo, hi) for name, (lo, hi) in bounds.items()
        })

    history: List[Dict[str, object]] = []

    def evaluate(design):
        cand = evaluate_dsfet_candidate(design, config)
        history.append(cand.as_dict())
        return cand

    population = [evaluate(d) for d in designs]

    for _ in range(generations):
        objectives = np.vstack([c.objectives for c in population])
        fronts = _non_dominated_fronts(objectives)
        rank = np.empty(len(population), dtype=int)
        crowd = np.zeros(len(population))
        for r, front in enumerate(fronts):
            for i in front:
                rank[i] = r
            front_crowd = _crowding(objectives[front])
            for local_i, i in enumerate(front):
                crowd[i] = front_crowd[local_i]
        children = []
        while len(children) < population_size:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            child = {}
            for name, (lo, hi) in bounds.items():
                span = max(hi - lo, 1e-30)
                child[name] = float(np.clip(
                    parent.x[name] + rng.gauss(0.0, config.mutation_sigma) * span,
                    lo, hi,
                ))
            children.append(evaluate(child))
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]
    deduplicated = []
    seen = set()
    for cand in front:
        key = tuple(np.round(cand.objectives, 9))
        if key not in seen:
            seen.add(key)
            deduplicated.append(cand)
    attach_attributions(
        deduplicated,
        lambda d: evaluate_dsfet_candidate(d, config),
        config.bounds(),
        lambda c: c.x,
        model_class_limitation="scale-free compact injection model: SS is stack-level, not device-level; the supply filter edge is thermally broadened (kT) - sharper filters need their own model; source transport resistance is not resolved.",
    )
    return DsFetFrontierResult(
        population=population, front=deduplicated, history=history,
    )
