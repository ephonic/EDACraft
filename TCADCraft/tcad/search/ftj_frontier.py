"""FTJ (Ferroelectric Tunnel Junction) compact explorer (P1-1).

comment7 5.4: TER (tunneling electroresistance) vs on-current tradeoff.
High TER needs thick barriers and strong asymmetric screening; the on-state
current is the tunneling current, exponentially dependent on barrier
thickness — the two requirements point in opposite directions.

Compact model:
    J(P) = A * E^D * exp(-2*Theta(E, m_t, Eg_eff))
    Eg_eff(P) = Eg_0 - Delta * (P/Ps)    # polarization modulates barrier
    TER = J(+P) / J(-P)

Design variables: t_fe, Ps, Eg_0, Delta (barrier modulation), m_t, A
Objectives: log10(TER), log10(J_on), switching voltage (2*Ec*t_fe)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts

QE = 1.602176634e-19
HBAR = 1.054571817e-34
M0 = 9.1093837015e-31

#: A12 DD adjudication (2026-09-23, bench/sentaurus/calibration/ftj_a12):
#: Sentaurus NLM tunneling through the n+Si/HfO2-FE(2nm)/n+Si stack with
#: program +-1.5 V / read +0.1 V gives TER = 5.8 for the frontier design
#: (Ps=0.46, eg0=0.91, delta=0.63, mt=0.23) where the compact predicted
#: ~1e8. The DD barrier modulation backs out to ~0.009 eV effective vs
#: the assumed 0.63 eV -- metallic (Thomas-Fermi) screening in the
#: electrodes absorbs most of the polarization charge. Applied as a
#: modulation efficiency on delta (numerically anchored so the frontier
#: design reproduces TER = 5.8 exactly).
FTJ_DELTA_EFFICIENCY = 0.014881


@dataclass
class FtjConfig:
    t_fe_nm: Tuple[float, float] = (2.0, 10.0)
    ps: Tuple[float, float] = (0.1, 1.0)
    eg0_eV: Tuple[float, float] = (0.5, 3.0)
    delta_eV: Tuple[float, float] = (0.05, 0.8)
    mt_ratio: Tuple[float, float] = (0.05, 0.4)
    a_kane: Tuple[float, float] = (1e18, 1e21)
    mutation_sigma: float = 0.18

    def bounds(self):
        return {
            "t_fe_nm": self.t_fe_nm,
            "ps": self.ps,
            "eg0_eV": self.eg0_eV,
            "delta_eV": self.delta_eV,
            "mt_ratio": self.mt_ratio,
            "a_kane": self.a_kane,
        }


@dataclass
class FtjCandidate:
    x: Dict[str, float]
    ter: float = float("nan")
    j_on: float = float("nan")
    v_switch: float = float("nan")
    trusted: bool = False
    violations: List[str] = field(default_factory=list)
    attribution: Optional[object] = None

    @property
    def objectives(self):
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([
            float(np.log10(max(self.ter, 1.0))),
            float(np.log10(max(self.j_on, 1e-30))),
            -self.v_switch,
        ])

    def as_dict(self):
        out = dict(self.x)
        out.update({
            "ter": self.ter,
            "log10_ter": float(np.log10(max(self.ter, 1.0))),
            "j_on_A_per_m2": self.j_on,
            "v_switch_V": self.v_switch,
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        att = getattr(self, "attribution", None)
        if att is not None:
            out.update(att.as_dict())
        return out


def _theta(field, mt_ratio, eg_ev):
    mt = mt_ratio * M0
    eg_j = eg_ev * QE
    return (2.0 / 3.0) * math.sqrt(2.0 * mt) * eg_j ** 1.5 / (HBAR * QE * field)


def evaluate_ftj(x, config=None):
    config = config or FtjConfig()
    clipped = {}
    for name, (lo, hi) in config.bounds().items():
        if name not in x:
            clipped[name] = 0.5 * (lo + hi)
        else:
            v = float(np.clip(x[name], lo, hi))
            clipped[name] = v
    cand = FtjCandidate(x=clipped)

    t_fe = clipped["t_fe_nm"] * 1e-9
    ps = clipped["ps"]
    eg0 = clipped["eg0_eV"]
    delta = clipped["delta_eV"]
    mt = clipped["mt_ratio"]
    a = clipped["a_kane"] * 1e6

    # Read voltage: small field to avoid switching during read
    v_read = 0.1
    e_read = v_read / t_fe

    # Barrier heights for the two polarization states (clamped positive).
    # A12 DD correction: the effective modulation is delta * efficiency
    # (metallic screening absorbs most of the polarization charge).
    delta_eff = delta * FTJ_DELTA_EFFICIENCY
    eg_up = max(eg0 - delta_eff, 0.05)
    eg_dn = max(eg0 + delta_eff, 0.05)

    # Tunneling currents through the two barrier configurations
    theta_up = _theta(e_read, mt, eg_up)
    theta_dn = _theta(e_read, mt, eg_dn)
    j_up = a * e_read ** 2.0 * math.exp(-2.0 * theta_up) if theta_up < 350 else 0.0
    j_dn = a * e_read ** 2.0 * math.exp(-2.0 * theta_dn) if theta_dn < 350 else 0.0

    if j_up <= 0 or j_dn <= 0:
        cand.violations.append("tunneling current underflow")
        return cand

    ter = j_up / j_dn
    # Cap TER at physically achievable range (WKB exponential artifact
    # guard: real FTJ TER measured up to ~1e7-1e8, Science 2026)
    ter = min(ter, 1.0e8)

    # Switching voltage: 2*Ec*t_fe, estimate Ec from Landau
    ec_est = 2e8 * (0.3 / max(ps, 0.05))  # rough scaling: higher Ps -> lower Ec
    v_switch = 2 * ec_est * t_fe

    cand.ter = ter
    cand.j_on = j_up
    cand.v_switch = v_switch
    cand.trusted = True
    return cand


def evolve_ftj_frontier(config=None, pop=16, gens=8, seed=0):
    config = config or FtjConfig()
    rng = random.Random(seed)
    bounds = config.bounds()
    from .attribution import sensitivity_attribution

    def evaluate(x):
        return evaluate_ftj(x, config)

    designs = [{n: rng.uniform(lo, hi) for n, (lo, hi) in bounds.items()}
               for _ in range(pop)]
    population = [evaluate(d) for d in designs]

    for _ in range(gens):
        objectives = np.vstack([c.objectives for c in population])
        fronts = _non_dominated_fronts(objectives)
        rank = np.empty(len(population), dtype=int)
        crowd = np.zeros(len(population))
        for r, front in enumerate(fronts):
            for i in front:
                rank[i] = r
            fc = _crowding(objectives[front])
            for li, i in enumerate(front):
                crowd[i] = fc[li]
        children = []
        while len(children) < pop:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            child = {}
            for name, (lo, hi) in bounds.items():
                span = max(hi - lo, 1e-30)
                child[name] = float(np.clip(
                    parent.x[name] + rng.gauss(0, config.mutation_sigma) * span, lo, hi))
            children.append(evaluate(child))
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]
    for member in front:
        member.attribution = sensitivity_attribution(
            evaluate, dict(member.x), bounds,
            model_class_limitation=(
                "compact FTJ model: WKB direct tunneling through a "
                "polarization-modulated rectangular barrier; no DE layer, "
                "no series resistance, no domain dynamics. TER is the "
                "ratio of forward/reverse barrier currents at a fixed "
                "read voltage. Literature anchor: Science 2026 sliding-FE "
                "FTJ (1.9e7 TER, 222 A/cm2) as trend-level reference."
            ),
        )
    return {"front": front, "population": population}
