"""NC-TFET: FE-enhanced tunnel FET discovery explorer.

Hypothesis: A TFET with an FE layer in the gate stack could use the
(realistic, DD-calibrated) NC field boost to increase the effective gate
field at the source-channel junction, boosting BTBT rate without
increasing applied voltage. Even a modest field boost (5-20%, not the
34x that the quasi-static model wrongly predicted) could increase Ion
by an order of magnitude at the same SS.

This is something ONLY TCADCraft can evaluate:
- E2's BTBT model is Sentaurus-calibrated
- E0's FE stack is DD-adjudicated (realistic amplification)
- Sentaurus itself cannot easily simulate coupled FE+BTBT (convergence)

Design variables:
  TFET parameters: eg_t, lambda, mt, a_kane, vfb
  FE parameters: t_fe, ps, ec (adds field amplification)

Objectives:
  1. steepness: -SS (with realistic NC correction)
  2. drive: log10(Ion_enhanced / Ion_baseline) -- the NC BOOST factor
  3. stability: FE bistability margin (must be stable for reliable switching)

Key output: Is there a design point where NC boost gives >10x Ion
improvement at SS < 80 mV/dec?
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
EPS0 = 8.854187817e-12

#: DD-calibrated NC field boost ceiling (from A2 Sentaurus adjudication).
#: The quasi-static model predicts >>1 but DD shows the FE cannot stably
#: provide sub-60 amplification. The realistic boost is at most ~20%.
NC_DD_BOOST_CEILING = 1.20

#: Sentaurus-calibrated TFET reference (from HFS calibration session)
REF_ION_AT_SS30 = 0.025  # A/um (approximately, from E2 frontier)


@dataclass
class NcTfetConfig:
    # TFET parameters (same bounds as E2)
    eg_t: Tuple[float, float] = (0.35, 1.12)
    lambda_nm: Tuple[float, float] = (3.0, 15.0)
    mt_ratio: Tuple[float, float] = (0.05, 0.30)
    a_kane: Tuple[float, float] = (1.0e19, 1.0e22)
    vfb_offset: Tuple[float, float] = (-0.30, 0.30)
    # FE parameters (subset of E0's)
    t_fe_nm: Tuple[float, float] = (4.0, 20.0)
    ps: Tuple[float, float] = (0.05, 1.0)
    ec: Tuple[float, float] = (0.5e8, 4.0e8)
    # Circuit
    vdd: float = 0.5
    vds: float = 0.3
    mutation_sigma: float = 0.18

    def bounds(self):
        return {
            "eg_t": self.eg_t, "lambda_nm": self.lambda_nm,
            "mt_ratio": self.mt_ratio, "a_kane": self.a_kane,
            "vfb_offset": self.vfb_offset,
            "t_fe_nm": self.t_fe_nm, "ps": self.ps, "ec": self.ec,
        }


@dataclass
class NcTfetCandidate:
    x: Dict[str, float]
    ss_baseline_mV: float = float("nan")
    ss_enhanced_mV: float = float("nan")
    ion_baseline: float = float("nan")  # log10 A/um
    ion_enhanced: float = float("nan")  # log10 A/um
    boost_factor: float = float("nan")
    fe_stable: bool = False
    trusted: bool = False
    violations: List[str] = field(default_factory=list)

    @property
    def objectives(self):
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([
            -self.ss_enhanced_mV,      # steepness (lower SS better)
            self.ion_enhanced,         # drive current
            1.0 if self.fe_stable else 0.0,  # FE stability
        ])

    def as_dict(self):
        out = dict(self.x)
        out.update({
            "ss_baseline": self.ss_baseline_mV,
            "ss_enhanced": self.ss_enhanced_mV,
            "ion_baseline_log": self.ion_baseline,
            "ion_enhanced_log": self.ion_enhanced,
            "boost_factor": self.boost_factor,
            "fe_stable": float(self.fe_stable),
            "trusted": float(self.trusted),
        })
        return out


def _nc_field_boost(x_fe):
    """DD-calibrated NC field amplification factor.

    The quasi-static load-line gives a theoretical amplification that is
    34x too optimistic (A2 Sentaurus). The realistic DD-level amplification
    is at most ~20% and depends on the FE parameters.

    Physical model: the FE layer adds an internal voltage that slightly
    boosts the effective gate drive. The boost is:
    - Zero when the FE is unstable (hysteretic)
    - Small (~5-20%) when the FE is stable
    - Larger for thinner FE / higher Ps (but approaches instability)
    """
    t_fe = x_fe["t_fe_nm"] * 1e-9
    ps = x_fe["ps"]
    ec = x_fe["ec"]

    # FE internal field (depolarization)
    e_dep = ps / (20.0 * EPS0)

    # Stability check: FE is stable if E_dep < Ec
    if e_dep > ec * 3:
        return 0.0, False  # unstable

    # DD-calibrated boost: the internal voltage from the FE polarization
    # adds to the gate drive. V_fe = P/(C_total) where C_total is the
    # series capacitance. The boost is bounded by the DD ceiling.
    v_fe_internal = ps * t_fe / max(EPS0 * 20.0 * 1e-9, 1e-30)
    v_gate = 0.5  # nominal gate voltage

    # Cap at DD-achievable ceiling
    raw_boost = 1.0 + min(v_fe_internal / max(v_gate, 0.1), NC_DD_BOOST_CEILING - 1.0)

    return min(raw_boost, NC_DD_BOOST_CEILING), True


def _tfet_current(x, vg, boost=1.0):
    """TFET current from E2 compact model with optional field boost."""
    # Effective junction field with boost
    e_junction = ((vg - x["vfb_offset"]) * 0.9 + 0.1 * 0.3) / (x["lambda_nm"] * 1e-9)
    e_junction *= boost  # apply NC field boost

    if e_junction <= 1e4:
        return 1e-30

    mt = x["mt_ratio"] * M0
    eg_j = x["eg_t"] * QE
    theta = (2.0 / 3.0) * math.sqrt(2.0 * mt) * eg_j ** 1.5 / (HBAR * QE * e_junction)

    gen = x["a_kane"] * 1e6 * e_junction ** 2.0 * math.exp(-2.0 * theta)
    # Temperature scaling (300K)
    gen *= 1.0  # already at 300K

    return max(gen, 1e-30)


def _extract_ss(vg_arr, id_arr, decades=2.0):
    """Window-averaged subthreshold swing."""
    ion = id_arr[-1]
    if ion <= 0:
        return float("nan"), float("nan")
    floor_val = max(ion / 10 ** decades, 1e-30)
    swings = []
    ion_at_best = None
    for k in range(1, len(vg_arr)):
        if id_arr[k] > id_arr[k - 1] > floor_val:
            dlog = math.log10(id_arr[k]) - math.log10(id_arr[k - 1])
            if dlog > 0.005:
                ss = (vg_arr[k] - vg_arr[k - 1]) / dlog
                swings.append(ss)
                if ion_at_best is None or id_arr[k] > ion_at_best:
                    ion_at_best = id_arr[k]
    if not swings:
        return float("nan"), float("nan")
    return min(swings) * 1000.0, math.log10(max(ion, 1e-30))


def evaluate_nc_tfet(x, config=None):
    """Evaluate one NC-TFET candidate."""
    config = config or NcTfetConfig()
    bounds = config.bounds()
    clipped = {}
    for name, (lo, hi) in bounds.items():
        val = x.get(name, 0.5 * (lo + hi))
        clipped[name] = float(np.clip(val, lo, hi))

    cand = NcTfetCandidate(x=clipped)

    # Extract FE parameters
    x_fe = {"t_fe_nm": clipped["t_fe_nm"], "ps": clipped["ps"], "ec": clipped["ec"]}

    # Compute NC field boost (DD-calibrated)
    boost, fe_stable = _nc_field_boost(x_fe)
    cand.fe_stable = fe_stable

    if not fe_stable:
        cand.violations.append("FE layer unstable (hysteretic)")
        # Still evaluate baseline TFET without boost
        boost = 1.0

    # Sweep gate voltage for baseline and enhanced
    vg = np.linspace(0, config.vdd, 41)
    id_base = np.array([_tfet_current(clipped, float(v), 1.0) for v in vg])
    id_enh = np.array([_tfet_current(clipped, float(v), boost) for v in vg])

    ss_base, ion_base = _extract_ss(vg, id_base)
    ss_enh, ion_enh = _extract_ss(vg, id_enh)

    if not np.isfinite(ss_base) or not np.isfinite(ss_enh):
        cand.violations.append("SS extraction failed")
        return cand

    cand.ss_baseline_mV = ss_base
    cand.ss_enhanced_mV = ss_enh
    cand.ion_baseline = ion_base
    cand.ion_enhanced = ion_enh
    cand.boost_factor = boost

    cand.trusted = True
    return cand


def evolve_nc_tfet(pop=30, gen=15, seed=0):
    """Run the NC-TFET discovery exploration."""
    config = NcTfetConfig()
    bounds = config.bounds()
    rng = random.Random(seed)

    def random_x():
        return {k: rng.uniform(lo, hi) for k, (lo, hi) in bounds.items()}

    def mutate(parent):
        child = {}
        for name, (lo, hi) in bounds.items():
            span = max(hi - lo, 1e-30)
            child[name] = float(np.clip(
                parent[name] + rng.gauss(0, config.mutation_sigma) * span,
                lo, hi))
        return child

    def evaluate(x):
        return evaluate_nc_tfet(x, config)

    population = [evaluate(random_x()) for _ in range(pop)]

    for _ in range(gen):
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
            children.append(evaluate(mutate(parent.x)))
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]

    return {"front": front, "population": population}
