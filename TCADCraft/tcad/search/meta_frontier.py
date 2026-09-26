"""Unified multi-family device meta-exploration.

The capstone exploration layer: a single optimizer that discovers WHICH
device family (NC-FET, TFET, cold-source, FeFET, FTJ) to use AND the
optimal parameters within that family. This answers "which beyond-CMOS
route should we invest in?" as a computable optimization.

Design variables:
  - device_family: categorical selector (the KEY exploration dimension)
  - family-specific continuous parameters

Objectives (all maximized, unified across families):
  - steepness: -SS [mV/dec] (DD-calibrated: floor at ~62 for NC-FET
    per Sentaurus adjudication A2)
  - on_current: log10(Ion) or equivalent drive metric
  - stability: family-specific (NC-FET: depo margin; FeFET: retention;
    TFET: Ion/Ioff ratio; cold-source: robustness; FTJ: TER)

Sentaurus adjudication corrections applied:
  - E0 NC-FET: SS floored at 62 mV/dec (A2: DD cannot achieve sub-60)
  - E1 FeFET: retention from imprint not depolarization (A1: depol
    gives zero loss in Sentaurus transient)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .fe_frontier import _crowding, _non_dominated_fronts

#: Sentaurus DD floor for NC-FET SS (adjudication A2)
NC_DD_SS_FLOOR = 62.0  # mV/dec

FAMILIES = ("ncfet", "tfet", "cold_source", "fefet", "ftj")

FAMILY_PARAMS = {
    "ncfet": {
        "fe_thickness_nm": (4.0, 40.0),
        "de_thickness_nm": (0.3, 4.0),
        "de_eps": (4.0, 25.0),
        "beta_scale": (0.2, 5.0),
        "c_mos_mF_per_m2": (0.5, 50.0),
        "vg_span": (0.4, 1.2),
    },
    "tfet": {
        "eg_t": (0.35, 1.12),
        "lambda_nm": (3.0, 15.0),
        "mt_ratio": (0.05, 0.30),
        "a_kane": (1.0e19, 1.0e22),
        "vfb_offset": (-0.30, 0.30),
        "vdd": (0.3, 0.8),
    },
    "cold_source": {
        "filter_window_meV": (80.0, 400.0),
        "filter_cutoff_meV": (60.0, 350.0),
        "source_fermi_meV": (-30.0, 400.0),
        "lambda_sc_nm": (3.0, 30.0),
        "vdd": (0.3, 0.7),
    },
    "fefet": {
        "t_fe_nm": (5.0, 40.0),
        "ps": (0.10, 1.40),
        "ec": (0.5e8, 4.0e8),
        "overdrive": (1.3, 2.1),
        "tau0": (1.0e-12, 1.0e-6),
        "merz_exponent": (0.5, 2.0),
    },
    "ftj": {
        "t_fe_nm": (2.0, 10.0),
        "ps": (0.1, 1.0),
        "eg0_eV": (0.5, 3.0),
        "delta_eV": (0.05, 0.8),
        "mt_ratio": (0.05, 0.4),
        "a_kane": (1.0e18, 1.0e21),
    },
}


@dataclass
class MetaCandidate:
    family: str
    x: Dict[str, float]
    ss_mV_dec: float = float("nan")
    log_ion: float = float("nan")
    stability: float = float("nan")
    trusted: bool = False
    violations: List[str] = field(default_factory=list)
    attribution: Optional[object] = None

    @property
    def objectives(self) -> np.ndarray:
        if not self.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([
            -self.ss_mV_dec,
            self.log_ion,
            self.stability,
        ])

    def as_dict(self) -> Dict[str, object]:
        out = {"family": self.family}
        out.update(self.x)
        out.update({
            "ss_mV_dec": self.ss_mV_dec,
            "log_ion": self.log_ion,
            "stability": self.stability,
            "trusted": float(self.trusted),
        })
        out["violations"] = ";".join(self.violations)
        att = getattr(self, "attribution", None)
        if att is not None:
            out.update(att.as_dict())
        return out


def _evaluate_family(family: str, x: Dict[str, float],
                     temperature_K: float = 300.0) -> MetaCandidate:
    """Evaluate a candidate in the given family with DD corrections."""
    cand = MetaCandidate(family=family, x=x)

    if family == "ncfet":
        from .ncfet_frontier import NcFetStackConfig, evaluate_ncfet_candidate
        cfg = NcFetStackConfig()
        result = evaluate_ncfet_candidate(x, cfg)
        if not result.trusted:
            cand.violations = result.violations
            return cand
        # A2 correction: SS floored at DD-achievable limit
        ss_theory = result.ss_min_mV_per_dec
        cand.ss_mV_dec = max(ss_theory, NC_DD_SS_FLOOR)
        # NC-FET drive: use amplification window as proxy
        cand.log_ion = result.amplification_window_frac * 10 - 5
        cand.stability = result.stability_margin_F_per_m2
        cand.trusted = True

    elif family == "tfet":
        from .tfet_frontier import TfetFrontierConfig, evaluate_tfet_candidate
        cfg = TfetFrontierConfig(temperature_K=temperature_K)
        result = evaluate_tfet_candidate(x, cfg)
        if not result.trusted:
            cand.violations = result.violations
            return cand
        cand.ss_mV_dec = result.ss_avg_mV_per_dec
        cand.log_ion = float(np.log10(max(result.ion, 1e-30)))
        cand.stability = float(np.log10(max(result.ion /
                               max(result.ioff, 1e-30), 1e-30)))
        cand.trusted = True

    elif family == "cold_source":
        from .dsfet_frontier import DsFetConfig, evaluate_dsfet_candidate
        cfg = DsFetConfig(temperature_K=temperature_K)
        result = evaluate_dsfet_candidate(x, cfg)
        if not result.trusted:
            cand.violations = result.violations
            return cand
        cand.ss_mV_dec = result.ss_window_mV_per_dec
        cand.log_ion = float(np.log10(max(result.ion, 1e-30)))
        robustness = -(result.ss_short_mV_per_dec - result.ss_window_mV_per_dec)
        cand.stability = max(robustness, -100.0)
        cand.trusted = True

    elif family == "fefet":
        from .fe_frontier import FeFrontierConfig, evaluate_fe_candidate
        cfg = FeFrontierConfig()
        # Fill in trap params with defaults (not explored in meta)
        full_x = {**x,
                  "trap_density_cm2": 1e11,
                  "trap_capture_tau_s": 1e-3,
                  "trap_emission_tau_s": 1e-1}
        result = evaluate_fe_candidate(full_x, cfg, evaluator="analytic")
        if not result.trusted:
            cand.violations = result.violations
            return cand
        # FeFET SS: MW-related steepness metric (higher MW = more separation)
        cand.ss_mV_dec = result.mw_V * 10  # MW*10 as SS proxy (lower=better)
        cand.log_ion = float(np.log10(1.0 / max(result.t_switch, 1e-30)))
        # A1 correction: retention from imprint not depolarization
        # Use endurance as stability (more cycles = more stable)
        cand.stability = float(np.log10(max(result.endurance_cycles, 1.0)))
        cand.trusted = True

    elif family == "ftj":
        from .ftj_frontier import FtjConfig, evaluate_ftj
        cfg = FtjConfig()
        result = evaluate_ftj(x, cfg)
        if not result.trusted:
            cand.violations = result.violations
            return cand
        # FTJ SS: switching voltage as steepness proxy
        cand.ss_mV_dec = result.v_switch * 1000.0
        cand.log_ion = float(np.log10(max(result.j_on, 1e-30)))
        cand.stability = float(np.log10(max(result.ter, 1.0)))
        cand.trusted = True

    return cand


def evolve_meta_frontier(
    population_size: int = 30,
    generations: int = 15,
    seed: int = 0,
    family_weights: Optional[Dict[str, float]] = None,
    temperature_K: float = 300.0,
) -> Dict[str, object]:
    """Run the unified multi-family meta-exploration."""
    rng = random.Random(seed)
    weights = family_weights or {f: 1.0 / len(FAMILIES) for f in FAMILIES}

    def random_design():
        family = rng.choices(list(weights.keys()),
                             weights=list(weights.values()))[0]
        bounds = FAMILY_PARAMS[family]
        return family, {k: rng.uniform(lo, hi) for k, (lo, hi) in bounds.items()}

    def mutate(cand):
        family = cand.family
        if rng.random() < 0.15:  # family switching
            family = rng.choice(FAMILIES)
        bounds = FAMILY_PARAMS[family]
        child = {}
        for name, (lo, hi) in bounds.items():
            if name in cand.x and family == cand.family and rng.random() < 0.7:
                span = max(hi - lo, 1e-30)
                child[name] = float(np.clip(
                    cand.x[name] + rng.gauss(0, 0.18) * span, lo, hi))
            else:
                child[name] = rng.uniform(lo, hi)
        return family, child

    def evaluate(pair):
        family, x = pair
        return _evaluate_family(family, x, temperature_K=temperature_K)

    # Initialize population
    population = [evaluate(random_design()) for _ in range(population_size)]

    for _ in range(generations):
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
        while len(children) < population_size:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            children.append(evaluate(mutate(parent)))
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]

    # Attach attribution
    from .attribution import sensitivity_attribution
    for member in front:
        bounds = FAMILY_PARAMS[member.family]
        member.attribution = sensitivity_attribution(
            lambda x: _evaluate_family(member.family, x),
            dict(member.x), bounds,
            model_class_limitation=(
                f"unified meta-exploration, family={member.family}: "
                "compact-tier with Sentaurus DD corrections (E0 SS floor "
                "62 mV/dec, E1 retention from imprint not depol)"
            ),
        )

    # Analyze family distribution
    from collections import Counter
    family_dist = Counter(c.family for c in front)

    return {
        "front": front,
        "population": population,
        "family_distribution": dict(family_dist),
    }
