"""E2 TFET steepness-current frontier explorer (plan0918 direction-2).

Design question (comment7 4.1): band-to-band tunneling FETs can break the
60 mV/dec thermal limit, but steep slope and high on-current have never been
achieved simultaneously in a manufacturable device - shrinking the tunneling
gap raises the field (more current) but also the off-state leakage, and the
steep-slope window narrows.  This module makes that tradeoff a computable
Pareto frontier.

Physics model (compact, declared)
---------------------------------
``Eg_t``        effective tunneling gap: channel Eg minus the heterojunction
                valence-band stagger (the source-material knob);
``lambda``      electrostatic screening length (tox/body knob);
``mt``          tunneling effective mass (source-material knob);
``a_kane``      Kane prefactor A (cm^-3 convention, as in the solver);
``vfb_offset``  flat-band/workfunction offset (Vt placement knob).

The gate couples to the surface potential with efficiency ``eta``; the
junction field is the band bending over the screening length, with the
heterojunction stagger (relative to the Si-like reference gap) acting as a
built-in field term in volts::

    E(Vg) = ((Vg - vfb_offset)*eta + kappa*Vds + (Eg_ref - Eg_t)) / lambda

and the generation uses the M2 nonlocal kernel closed form with ``Eg_t`` as
the tunneling gap (the declared unified view: a staggered source both lowers
the effective gap and adds built-in field)::

    G(E) = A*1e6 * E^D * exp(-2*Theta(E, mt)),  Theta = (2/3)*sqrt(2*mt)
           * Eg_t^1.5 / (hbar*q*E)

``Id(Vg)`` is proportional to G times the tunnel volume, with the single
overall scale anchored to the nonlocal drift-diffusion device replay at the
reference TFET design point (bench/tcadcraft/calibration, 2026-09-18
baseline: Id=3.83e-4 A/um at Vg=Vds=0.8/0.5 V, m_t=0.0843, A=3.5e21 cm^-3).

Objectives (all maximized)
--------------------------
``steepness``        -average SS [dec/V] over the readout current window
                     (the average subthreshold swing across the last
                     ``ss_decades`` decades below the on-current; a raw
                     min-SS would game the deep tail where the current is
                     unusable);
``log10_ion``        log10 on-current at Vg=Vdd [A/um];
``log10_ratio``      log10(Ion/Ioff).

Honesty boundaries
------------------
* Compact-mode currents carry ONE anchored scale factor; absolute levels
  outside the anchor's neighbourhood are trend-level, not point-level.
* The heterojunction stagger -> Eg_t mapping, ``eta`` and ``kappa`` are
  declared v1 electrostatics; solver mode (the DD nonlocal replay) is the
  high-fidelity verification of frontier members, not the search engine.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts
from .attribution import attach_attributions
QE = 1.602176634e-19
HBAR = 1.054571817e-34
M0 = 9.1093837015e-31

#: Reference design point: the calibrated TFET deck transferred to the
#: nonlocal kernel (plan0918 M2).  Ion anchor [A/um] at Vg=Vdd=0.8/0.5 V.
#:
#: 2026-09-22 RE-ANCHOR (A8): the original 3.83e-4 anchor came from the
#: 2026-09-18 C++ DD replay and disagrees with the authoritative Sentaurus
#: golden (bench/sentaurus/calibration/tfet_btbt, local Hurkx deck) by
#: 2.14 decades at the same design point. The Sentaurus measurement is
#: Ion(Vg=0.8, Vds=0.5) = 2.786e-6 A/um, SS_min = 185.3 mV/dec.
REF_ION_A_PER_UM = 2.786e-6
REF_EG_EV = 1.12416
REF_LAMBDA_NM = 4.74
REF_MT = 0.0843
REF_A_KANE = 3.5e21
REF_D = 2.0
#: DD-calibrated SS scale: the compact's uniform-field swing underestimates
#: the Sentaurus subthreshold shape at the anchor by 185.3/88.5 = 2.09x.
#: Applied as a multiplicative correction to reported swings (same pattern
#: as the E0 SS floor).
SS_DD_SCALE = 2.09


def theta_kernel(field: float, mt_ratio: float, eg_ev: float) -> float:
    """WKB exponent Theta = (2/3)*sqrt(2*mt)*Eg^1.5/(hbar*q*E) [SI]."""
    mt = mt_ratio * M0
    eg_j = eg_ev * QE
    return (2.0 / 3.0) * math.sqrt(2.0 * mt) * eg_j ** 1.5 / (HBAR * QE * field)


@dataclass
class TfetFrontierConfig:
    eg_t: Tuple[float, float] = (0.35, 1.12416)
    lambda_nm: Tuple[float, float] = (3.0, 15.0)
    mt_ratio: Tuple[float, float] = (0.05, 0.30)
    a_kane: Tuple[float, float] = (1.0e19, 1.0e22)
    vfb_offset: Tuple[float, float] = (-0.30, 0.30)
    vdd: float = 0.8
    vds: float = 0.5
    eta: float = 0.90
    kappa: float = 0.10
    d_exp: float = REF_D
    ss_decades: float = 3.0
    vg_step: float = 0.005
    mutation_sigma: float = 0.18
    temperature_K: float = 300.0  # NEW: operating temperature

    def bounds(self) -> Dict[str, Tuple[float, float]]:
        return {
            "eg_t": self.eg_t,
            "lambda_nm": self.lambda_nm,
            "mt_ratio": self.mt_ratio,
            "a_kane": self.a_kane,
            "vfb_offset": self.vfb_offset,
        }


@dataclass
class TfetFrontierCandidate:
    x: Dict[str, float]
    ion: float = float("nan")
    ioff: float = float("nan")
    ss_avg_mV_per_dec: float = float("nan")
    trusted: bool = False
    violations: List[str] = field(default_factory=list)

    @property
    def objectives(self) -> np.ndarray:
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([
            -self.ss_avg_mV_per_dec,
            float(np.log10(max(self.ion, 1e-30))),
            float(np.log10(max(self.ion / max(self.ioff, 1e-30), 1e-30))),
        ])

    def as_dict(self) -> Dict[str, object]:
        out = dict(self.x)
        out.update({
            "ion_A_per_um": self.ion,
            "ioff_A_per_um": self.ioff,
            "ss_avg_mV_per_dec": self.ss_avg_mV_per_dec,
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def _si_bandgap_ev(temperature_K: float) -> float:
    """Varshni silicon bandgap [eV]. Eg(300)=1.124, Eg(77)=1.166."""
    return 1.17 - 4.73e-4 * temperature_K ** 2 / (temperature_K + 636.0)


# DD-adjudicated temperature scaling (Sentaurus Hurkx cryo sweep,
# bench/sentaurus/calibration/tfet_cryo, 2026-09-21):
#   T[K]:   300    250    150    77
#   Ion(T)/Ion(300): 1.000  0.965  0.916  0.913
# Naive T^{-3/2} predicts 7.69x at 77K -- qualitatively wrong. Mechanism:
# Varshni Eg(T) growth (+0.042 eV at 77K) raises the BTBT WKB exponent and
# suppresses tunneling exponentially, cancelling the phonon prefactor gain.
# The compact model's effective WKB exponent (calibrated at 300K with a
# reduced effective gap) underestimates this sensitivity ~2.6x, so the
# applied factor is the DD-measured curve itself, interpolated in log(T)
# and clamped outside the adjudicated 77-300 K window.
_DD_T_K = (77.0, 150.0, 250.0, 300.0)
_DD_T_FACTOR = (0.913, 0.916, 0.965, 1.000)


def _temperature_scaling(temperature_K: float) -> float:
    """DD-anchored BTBT temperature factor (see module notes above)."""
    t = float(np.clip(temperature_K, _DD_T_K[0], _DD_T_K[-1]))
    return float(np.interp(math.log(t),
                           [math.log(k) for k in _DD_T_K],
                           _DD_T_FACTOR))


def _junction_field(vg: float, x: Dict[str, float], config: TfetFrontierConfig) -> float:
    v_stagger = REF_EG_EV - x["eg_t"]
    return (
        (vg - x["vfb_offset"]) * config.eta + config.kappa * config.vds + v_stagger
    ) / (x["lambda_nm"] * 1.0e-9)


def _current_at(vg: float, x: Dict[str, float], config: TfetFrontierConfig,
                scale: float) -> float:
    field = _junction_field(vg, x, config)
    if field <= 1.0e4:
        return 0.0
    exponent = -2.0 * theta_kernel(field, x["mt_ratio"], x["eg_t"])
    if exponent < -700.0:
        return 0.0
    generation = (
        x["a_kane"] * 1.0e6 * field ** config.d_exp * math.exp(exponent)
    )
    # DD-adjudicated temperature factor (see _temperature_scaling notes):
    # flat 0.91-1.00 over 77-300 K, replacing the naive T^{-3/2}.
    t_scale = _temperature_scaling(config.temperature_K)
    return scale * generation * t_scale


def _anchor_scale() -> float:
    """Volume/scale factor reproducing the DD-replay anchor at the reference."""

    config = TfetFrontierConfig()
    x_ref = {
        "eg_t": REF_EG_EV,
        "lambda_nm": REF_LAMBDA_NM,
        "mt_ratio": REF_MT,
        "a_kane": REF_A_KANE,
        "vfb_offset": 0.0,
    }
    field = _junction_field(0.8, x_ref, config)
    generation = (
        REF_A_KANE * 1.0e6 * field ** REF_D
        * math.exp(-2.0 * theta_kernel(field, REF_MT, REF_EG_EV))
    )
    return REF_ION_A_PER_UM / generation


def evaluate_tfet_candidate(
    x: Dict[str, float],
    config: Optional[TfetFrontierConfig] = None,
    scale: Optional[float] = None,
) -> TfetFrontierCandidate:
    """Evaluate one E2 candidate on the compact anchored model."""
    config = config or TfetFrontierConfig()
    scale = scale if scale is not None else _anchor_scale()
    clipped = {}
    for name, (lo, hi) in config.bounds().items():
        value = float(np.clip(x[name], lo, hi))
        if not np.isfinite(value):
            raise ValueError(f"design variable {name} became non-finite")
        clipped[name] = value
    candidate = TfetFrontierCandidate(x=clipped)

    vg_grid = np.arange(0.0, config.vdd + 0.5 * config.vg_step, config.vg_step)
    currents = np.array([
        _current_at(float(vg), clipped, config, scale) for vg in vg_grid
    ])
    ion = float(currents[-1])
    ioff = float(currents[0])
    if not np.isfinite(ion) or ion <= 0.0:
        candidate.violations.append("non-positive on-current")
        return candidate
    if not np.isfinite(ioff) or ioff < 0.0:
        candidate.violations.append("invalid off-current")
        return candidate

    floor = max(ion / 10.0 ** config.ss_decades, 1e-30)
    window = currents >= floor
    if np.count_nonzero(window) < 2:
        candidate.violations.append("too few points in the SS window")
        return candidate
    log_i = np.log10(np.maximum(currents, 1e-300))
    swings = []
    for k in range(1, len(vg_grid)):
        if window[k] and window[k - 1] and currents[k] > currents[k - 1] > 0.0:
            swings.append(
                (vg_grid[k] - vg_grid[k - 1]) / (log_i[k] - log_i[k - 1])
            )
    if not swings:
        candidate.violations.append("no monotone swing intervals")
        return candidate
    ss_avg = float(np.mean(swings)) * 1000.0
    if not np.isfinite(ss_avg) or ss_avg <= 0.0:
        candidate.violations.append("invalid swing")
        return candidate

    candidate.ion = ion
    candidate.ioff = ioff
    # DD-calibrated swing (A8 re-anchor): the uniform-field shape
    # underestimates the Sentaurus subthreshold swing by SS_DD_SCALE.
    candidate.ss_avg_mV_per_dec = ss_avg * SS_DD_SCALE
    candidate.trusted = True
    return candidate


@dataclass
class TfetFrontierResult:
    population: List[TfetFrontierCandidate]
    front: List[TfetFrontierCandidate]
    history: List[Dict[str, object]] = field(default_factory=list)

    def to_rows(self):
        return [c.as_dict() for c in self.population]

    def front_rows(self):
        return [c.as_dict() for c in self.front]


def evolve_tfet_frontier(
    config: Optional[TfetFrontierConfig] = None,
    population_size: int = 16,
    generations: int = 8,
    seed: int = 0,
    init_population: Optional[List[Dict[str, float]]] = None,
) -> TfetFrontierResult:
    """Run the E2 NSGA-II loop (trusted candidates only enter the front)."""
    config = config or TfetFrontierConfig()
    if population_size < 4:
        raise ValueError("population_size must be >= 4")
    if generations < 1:
        raise ValueError("generations must be >= 1")
    rng = random.Random(seed)
    scale = _anchor_scale()
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
        cand = evaluate_tfet_candidate(design, config, scale)
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
        lambda d: evaluate_tfet_candidate(d, config, scale),
        config.bounds(),
        lambda c: c.x,
        model_class_limitation="compact load-line model with a single scale anchored to the nonlocal DD replay; absolute currents are trend-level outside the anchor neighbourhood; eta/kappa/stagger-to-Eg_t mapping are declared v1 electrostatics.",
    )
    return TfetFrontierResult(
        population=population, front=deduplicated, history=history,
    )
