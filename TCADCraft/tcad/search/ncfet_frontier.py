"""E0 NC-FET ferroelectric-stack electrostatics explorer (plan0918 direction-2).

Design question (comment7 1.2 / 5.6): a ferroelectric layer in series with
the gate stack provides negative differential capacitance that can amplify
the body factor below 1 (SS < 60 mV/dec), but the same S-branch makes the
stack bistable - hysteresis.  The stabilization condition (matching the
series DE/MOS capacitance against the FE negative branch) is the classic
tradeoff, made computable here.

Quasi-static stack model (declared)
------------------------------------
Series charge ``Q`` flows through FE / DE / MOS-surface; on a selected FE
branch the polarization solves the load line::

    V_g = V_fb + d_fe*(Q - P)/(eps0*eps_fe) + Q/C_de + psi(Q)

with the Landau branch ``E_fe = alpha*P + beta*P^3`` entering through
``V_fe_landau = d_fe*(alpha*P + beta*P^3)``; the FE voltage is the sum of
the linear part (from Q-P) and the Landau part.  The differential gate
capacitance is

    1/C_ins_eff = d_fe/(eps0*eps_fe) + d_fe*(alpha+3*beta*P^2)*dP/dQ ... with
    dP/dQ from the load line, giving the body factor ``m = 1 + C_par/C_ins``
    and SS = m*60 mV/dec (subthreshold, kT/q * ln10).

Objectives (all maximized)
--------------------------
``amplification``   1/m  (m = min body factor over the swing window)
``hysteresis_free`` bistability margin: min over the branch of the total
                    differential capacitance (positive = hysteresis-free,
                    larger = more robust); hysteretic candidates carry a
                    negative margin and are dominated unless their
                    amplification buys it
``window``         fraction of the gate swing over which m < 1 (usable
                    amplification window)

Design variables
----------------
``fe_thickness_nm``, ``de_thickness_nm``, ``de_eps``, ``beta_scale``
(Landau beta multiplier - material family knob), ``c_mos_mF_per_m2``
(parasitic/semiconductor capacitance), ``vg_span`` (design gate swing).

Analytic goldens (tests): the paraelectric limit (beta -> 0 with alpha > 0)
must give m > 1 exactly (no amplification); the stabilization boundary
(min total differential capacitance = 0) must coincide with the load-line
tangent/bistability onset; charge continuity through the stack; and the
sub-60 SS window must vanish as C_de -> infinity (pure FE, always bistable
in the S-region).

Honesty boundaries
------------------
* Quasi-static branch analysis: no transient/dynamic NC and no leakage;
  dynamic-NC measurement questions belong to the M5 verdict module.
* The MOS surface is a linear capacitance (no quantum/DG corrections);
  absolute SS values are stack-level, not device-level.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts
from .attribution import attach_attributions
EPS0 = 8.854187817e-12
#: Sentaurus DD adjudicated floor for NC-FET SS (A2: 2026-09-20).
#: Quasi-static load-line SS below this is not achievable in DD
#: (the FE cannot stably sit on the negative-C branch).
NC_DD_SS_FLOOR_MV = 62.0

#: Sentaurus DD ceiling for the stack-model body factor.
NC_DD_M_CEILING = 60.0 / NC_DD_SS_FLOOR_MV  # ≈ 0.968

VT_MV = 60.0  # kT/q * ln10 at 300 K [mV/dec]


@dataclass
class NcFetStackConfig:
    fe_thickness_nm: Tuple[float, float] = (4.0, 40.0)
    de_thickness_nm: Tuple[float, float] = (0.3, 4.0)
    de_eps: Tuple[float, float] = (4.0, 25.0)
    beta_scale: Tuple[float, float] = (0.2, 5.0)
    c_mos_mF_per_m2: Tuple[float, float] = (0.5, 50.0)
    vg_span: Tuple[float, float] = (0.4, 1.2)
    alpha: float = -5.0e8
    beta: float = 1.5e9
    eps_fe: float = 20.0
    n_swing: int = 121
    mutation_sigma: float = 0.18

    def bounds(self) -> Dict[str, Tuple[float, float]]:
        return {
            "fe_thickness_nm": self.fe_thickness_nm,
            "de_thickness_nm": self.de_thickness_nm,
            "de_eps": self.de_eps,
            "beta_scale": self.beta_scale,
            "c_mos_mF_per_m2": self.c_mos_mF_per_m2,
            "vg_span": self.vg_span,
        }


@dataclass
class NcFetStackCandidate:
    x: Dict[str, float]
    m_min: float = float("nan")
    ss_min_mV_per_dec: float = float("nan")
    stability_margin_F_per_m2: float = float("nan")
    amplification_window_frac: float = float("nan")
    hysteretic: bool = True
    trusted: bool = False
    violations: List[str] = field(default_factory=list)

    @property
    def objectives(self) -> np.ndarray:
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        if np.isfinite(self.m_min) and self.m_min > 0.0:
            amplification = 1.0 / self.m_min
        else:
            # Hysteretic stack: the quasi-static body factor is undefined on
            # the bistable branch; use the neutral value so the (negative)
            # stability margin carries the ranking.
            amplification = 1.0
        return np.array([
            amplification,
            self.stability_margin_F_per_m2,
            self.amplification_window_frac,
        ])

    def as_dict(self) -> Dict[str, object]:
        out = dict(self.x)
        out.update({
            "body_factor_min": self.m_min,
            "ss_min_mV_per_dec": self.ss_min_mV_per_dec,
            "stability_margin_F_per_m2": self.stability_margin_F_per_m2,
            "amplification_window_frac": self.amplification_window_frac,
            "hysteretic": float(self.hysteretic),
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def _stack_params(x: Dict[str, float], config: NcFetStackConfig):
    beta = config.beta * x["beta_scale"]
    d_fe = x["fe_thickness_nm"] * 1e-9
    d_de = x["de_thickness_nm"] * 1e-9
    c_de = x["de_eps"] * EPS0 / d_de
    c_mos = x["c_mos_mF_per_m2"] * 1.0e-3  # [F/m^2] areal capacitance
    return config.alpha, beta, d_fe, c_de, c_mos


def _solve_branch_charge(
    v_g: float,
    x: Dict[str, float],
    config: NcFetStackConfig,
    p_prev: float,
) -> Tuple[float, float]:
    """Continuation Newton solve of the load line for (Q, P).

    Quasi-static branch consistency gives the algebraic charge relation
    ``Q(P) = P + eps0*eps_fe*(alpha*P + beta*P^3)`` (D = eps0 eps E + P with
    E = dF/dP), so the load line reduces to one scalar equation in P::

        V_g = V_fb + d_fe*(alpha P + beta P^3) + Q(P)/C_de + Q(P)/C_mos
    """
    alpha, beta, d_fe, c_de, c_mos = _stack_params(x, config)
    eps_lin = config.eps_fe * EPS0
    inv_series = 1.0 / c_de + 1.0 / c_mos
    p = p_prev
    for _ in range(64):
        e_fe = alpha * p + beta * p ** 3
        q = p + eps_lin * e_fe
        residual = d_fe * e_fe + q * inv_series - v_g
        dqdp = 1.0 + eps_lin * (alpha + 3.0 * beta * p ** 2)
        dvdp = d_fe * (alpha + 3.0 * beta * p ** 2) + dqdp * inv_series
        if abs(dvdp) < 1e-30:
            break
        step = residual / dvdp
        if abs(step) > 0.05:
            step = 0.05 * math.copysign(1.0, step)
        p -= step
        if abs(step) < 1e-14:
            break
    q = p + eps_lin * (alpha * p + beta * p ** 3)
    return q, p


def _branch_derivatives(x: Dict[str, float], config: NcFetStackConfig, p: float):
    """Closed-form branch derivatives at polarization ``p``.

    Returns ``(dqdp, dvfe_dp)`` with ``dqdp = dQ/dP`` and
    ``dvfe_dp = dV_fe/dP``.  The insulator (FE+DE) differential capacitance
    is ``C_ins = dqdp/(dvfe_dp + dqdp/C_de)``; the body factor is
    ``m = 1 + C_mos/C_ins``; total stability (hysteresis-free) requires the
    TOTAL differential capacitance ``C_tot = dqdp/(dvdp_total) > 0`` with
    ``dvdp_total = dvfe_dp + dqdp*(1/C_de + 1/C_mos)``.  Amplification
    (m < 1, i.e. C_ins < 0) and total stability can coexist - the classic
    NC-FET stabilization condition.
    """
    alpha, beta, d_fe, c_de, c_mos = _stack_params(x, config)
    eps_lin = config.eps_fe * EPS0
    dqdp = 1.0 + eps_lin * (alpha + 3.0 * beta * p ** 2)
    dvfe_dp = d_fe * (alpha + 3.0 * beta * p ** 2)
    return dqdp, dvfe_dp, c_de, c_mos


def _insulator_capacitance(x: Dict[str, float], config: NcFetStackConfig, p: float) -> float:
    dqdp, dvfe_dp, c_de, _ = _branch_derivatives(x, config, p)
    denom = dvfe_dp + dqdp / c_de
    if abs(denom) < 1e-30:
        return float("-inf") if dqdp > 0 else float("inf")
    return dqdp / denom


def _total_capacitance(x: Dict[str, float], config: NcFetStackConfig, p: float) -> float:
    dqdp, dvfe_dp, c_de, c_mos = _branch_derivatives(x, config, p)
    denom = dvfe_dp + dqdp * (1.0 / c_de + 1.0 / c_mos)
    if abs(denom) < 1e-30:
        return float("-inf") if dqdp > 0 else float("inf")
    return dqdp / denom


def _body_factor(x: Dict[str, float], config: NcFetStackConfig, p: float) -> float:
    dqdp, dvfe_dp, c_de, c_mos = _branch_derivatives(x, config, p)
    c_ins = _insulator_capacitance(x, config, p)
    if not np.isfinite(c_ins) or abs(c_ins) < 1e-30:
        return float("inf")
    return 1.0 + c_mos / c_ins


def evaluate_ncfet_candidate(
    x: Dict[str, float],
    config: Optional[NcFetStackConfig] = None,
) -> NcFetStackCandidate:
    """Evaluate one E0 stack candidate by a path-independent P-grid scan.

    ``C_ins(P)``, ``C_tot(P)`` and the body factor ``m(P)`` are closed-form
    functions of the branch polarization, so the stack's bistability and
    amplification properties are scanned directly over ``P in [-1.05 Ps,
    +1.05 Ps]`` instead of along a continuation trajectory (which is
    path-dependent near the multivalued region and can silently skip the
    unstable branch).  The gate voltage of each P follows from the closed
    load line ``V_g(P) = d_fe*E(P) + Q(P)*(1/C_de + 1/C_mos)``; for
    hysteresis-free stacks the map is monotone and the amplification window
    is the voltage fraction with ``m < 1`` clipped to the design swing.
    """
    config = config or NcFetStackConfig()
    clipped = {}
    for name, (lo, hi) in config.bounds().items():
        value = float(np.clip(x[name], lo, hi))
        if not np.isfinite(value):
            raise ValueError(f"design variable {name} became non-finite")
        clipped[name] = value
    candidate = NcFetStackCandidate(x=clipped)

    alpha, beta, d_fe, c_de, c_mos = _stack_params(clipped, config)
    eps_lin = config.eps_fe * EPS0
    inv_series = 1.0 / c_de + 1.0 / c_mos
    ps = math.sqrt(-alpha / beta) if alpha < 0 else 1.0
    p_grid = np.linspace(-1.05 * ps, 1.05 * ps, config.n_swing)

    dqdp = 1.0 + eps_lin * (alpha + 3.0 * beta * p_grid ** 2)
    dvfe = d_fe * (alpha + 3.0 * beta * p_grid ** 2)
    c_tot = dqdp / (dvfe + dqdp * inv_series)
    c_ins = dqdp / (dvfe + dqdp / c_de)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = 1.0 + c_mos / c_ins
    q_grid = p_grid + eps_lin * (alpha * p_grid + beta * p_grid ** 3)
    v_grid = d_fe * (alpha * p_grid + beta * p_grid ** 3) + q_grid * inv_series

    if np.any(~np.isfinite(c_tot)) or np.any(c_tot <= 0.0):
        candidate.hysteretic = True
        worst = float(np.min(c_tot[np.isfinite(c_tot)])) if np.any(np.isfinite(c_tot)) else -1.0
        candidate.stability_margin_F_per_m2 = worst
        candidate.m_min = float("nan")
        candidate.ss_min_mV_per_dec = float("nan")
        candidate.amplification_window_frac = 0.0
        candidate.trusted = True
        return candidate

    candidate.hysteretic = False
    candidate.stability_margin_F_per_m2 = float(np.min(c_tot))
    finite = np.isfinite(m)
    if np.count_nonzero(finite) < 5:
        candidate.violations.append("body factor undefined over the branch")
        return candidate
    candidate.m_min = float(np.min(m[finite]))
    # A2 Sentaurus DD adjudication: SS floor at 62 mV/dec → m floor = 62/60.
    # DD simulation cannot achieve sub-60; the quasi-static load-line m<1
    # is a theoretical upper bound, not a DD-achievable value.
    candidate.m_min = max(candidate.m_min, NC_DD_SS_FLOOR_MV / VT_MV)
    candidate.ss_min_mV_per_dec = VT_MV * candidate.m_min
    below = finite & (m < 1.0)
    if np.any(below):
        vg_lo = float(np.min(v_grid[below]))
        vg_hi = float(np.max(v_grid[below]))
        span = clipped["vg_span"]
        window = (
            min(vg_hi, span / 2.0) - max(vg_lo, -span / 2.0)
        ) / span
        candidate.amplification_window_frac = float(np.clip(window, 0.0, 1.0))
    else:
        candidate.amplification_window_frac = 0.0
    if not (np.isfinite(candidate.m_min) and candidate.m_min > 0.0):
        candidate.violations.append("invalid body factor")
        return candidate
    candidate.trusted = True
    return candidate


@dataclass
class NcFetFrontierResult:
    population: List[NcFetStackCandidate]
    front: List[NcFetStackCandidate]
    history: List[Dict[str, object]] = field(default_factory=list)

    def to_rows(self):
        return [c.as_dict() for c in self.population]

    def front_rows(self):
        return [c.as_dict() for c in self.front]


def evolve_ncfet_frontier(
    config: Optional[NcFetStackConfig] = None,
    population_size: int = 16,
    generations: int = 8,
    seed: int = 0,
    init_population: Optional[List[Dict[str, float]]] = None,
) -> NcFetFrontierResult:
    """Run the E0 NSGA-II loop (trusted candidates only enter the front)."""
    config = config or NcFetStackConfig()
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
        cand = evaluate_ncfet_candidate(design, config)
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
        lambda d: evaluate_ncfet_candidate(d, config),
        config.bounds(),
        lambda c: c.x,
        model_class_limitation="quasi-static branch analysis: no dynamic NC and no leakage (the M5 verdict module owns the measurement-artifact question); linear MOS surface without quantum corrections; absolute SS is stack-level, not device-level.",
    )
    return NcFetFrontierResult(
        population=population, front=deduplicated, history=history,
    )
