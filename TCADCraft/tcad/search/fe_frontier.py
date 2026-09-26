"""E1 FeFET frontier explorer (plan0918 direction-2, first exploration batch).

Objective space (all maximized)
-------------------------------
``mw_V``             memory window from the FE-slab P-V loop (solver-backed
                     in ``solver`` mode; saturated play-loop analytic form in
                     ``analytic`` mode)
``log10_endurance``  cycles until the M1-cycled window proxy collapses below
                     ``mw_floor_frac`` of its fresh value
``log10_switch_rate`` ``-log10(t_switch)`` with ``t_switch`` the M4 compact
                     KAI domain switching time under the program field

Design variables
----------------
``t_fe_nm``  FE thickness; ``ps`` saturation polarization [C/m^2];
``ec``       coercive field [V/m]; ``overdrive`` program field = overdrive*ec;
``tau0``     Merz prefactor [s]; ``merz_exponent`` Merz-law exponent.

Honesty boundaries (declared, not hidden)
-----------------------------------------
* Endurance uses the ``run_endurance`` window proxy
  ``MW(N) = MW0 * active_fraction(N)``: M1 fatigue scales the switchable
  polarization; Ec-pinning-driven coercive growth is not yet modelled.
* Switching time is the M4 compact KAI waveform model (nucleation-limited,
  exact Avrami update), not a self-consistent transient solve.
* Retention is deliberately NOT an objective in v1: it requires a frozen trap
  spectrum (calibration C-class, physical golden pending).
* ``analytic`` mode exists for C++-free verification: its MW is the exact
  saturated play-loop crossing formula and must agree with ``solver`` mode
  to the sweep resolution.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..physics.ferro_kinetics import (
    AvramiDomainSwitching,
    FieldHistoryCyclingState,
    KaiMultiDomain,
    simulate_kai_waveform,
)
from .attribution import attach_attributions


EPS0 = 8.854187817e-12

#: Avrami completion target used for the switching-time closed form.
_SWITCH_COMPLETION = 0.999


@dataclass
class FeFrontierConfig:
    """Variable bounds and physics constants for the E1 search."""

    t_fe_nm: Tuple[float, float] = (5.0, 40.0)
    ps: Tuple[float, float] = (0.10, 1.40)
    ec: Tuple[float, float] = (0.5e8, 4.0e8)
    overdrive: Tuple[float, float] = (1.25, 2.2)
    tau0: Tuple[float, float] = (1.0e-12, 1.0e-6)
    merz_exponent: Tuple[float, float] = (0.5, 2.0)
    epsilon_r: float = 15.0
    e_bd: float = 6.0e8
    voltage_ceiling: float = 15.0
    mw_floor_frac: float = 0.5
    wakeup_gain: float = 0.15
    fatigue_loss: float = 0.8
    wakeup_cycles: float = 1.0e3
    fatigue_cycles: float = 1.0e6
    fatigue_field_exponent: float = 2.0
    reference_field: float = 3.0e8
    avrami_exponent: float = 1.5
    merz_field: float = 1.0e8
    slab_nodes: int = 41
    sweep_points_per_segment: int = 24
    mutation_sigma: float = 0.18
    endurance_max_cycles: float = 1.0e12
    # Retention axis (M1 TrapKinetics synthetic anchor).
    trap_density_cm2: Tuple[float, float] = (1e10, 1e13)
    trap_capture_tau_s: Tuple[float, float] = (1e-6, 1e-1)
    trap_emission_tau_s: Tuple[float, float] = (1e-4, 1e2)
    retention_time_s: float = 10.0 * 365.25 * 24.0 * 360.0  # ~10 years
    eps_fe_retention: float = 20.0  # FE permittivity for depolarization field
    depol_severity: float = 0.01  # scaling: 0.01 gives retention ~0.5 for Ps/Ec*eps~10

    def bounds(self) -> Dict[str, Tuple[float, float]]:
        return {
            "t_fe_nm": self.t_fe_nm,
            "ps": self.ps,
            "ec": self.ec,
            "overdrive": self.overdrive,
            "tau0": self.tau0,
            "merz_exponent": self.merz_exponent,
            "trap_density_cm2": self.trap_density_cm2,
            "trap_capture_tau_s": self.trap_capture_tau_s,
            "trap_emission_tau_s": self.trap_emission_tau_s,
        }


@dataclass
class FeFrontierCandidate:
    """One evaluated E1 candidate."""

    x: Dict[str, float]
    mw_V: float = float("nan")
    vc_plus: float = float("nan")
    vc_minus: float = float("nan")
    endurance_cycles: float = float("nan")
    t_switch: float = float("nan")
    retention_fraction: float = float("nan")
    trusted: bool = False
    violations: List[str] = field(default_factory=list)
    recheck_deviation: float = 0.0

    @property
    def objectives(self) -> np.ndarray:
        """Maximized objective vector [MW, log10(N_endurance), log10(1/t_sw), retention]."""
        if not self.trusted:
            return np.array([float("-inf")] * 4)
        return np.array([
            self.mw_V,
            float(np.log10(max(self.endurance_cycles, 1.0))),
            float(np.log10(1.0 / max(self.t_switch, 1.0e-30))),
            self.retention_fraction,
        ])

    def as_dict(self) -> Dict[str, float]:
        out = dict(self.x)
        out.update({
            "mw_V": self.mw_V,
            "vc_plus_V": self.vc_plus,
            "vc_minus_V": self.vc_minus,
            "endurance_cycles": self.endurance_cycles,
            "t_switch_s": self.t_switch,
            "retention_fraction": self.retention_fraction,
            "trusted": float(self.trusted),
            "recheck_deviation": self.recheck_deviation,
        })
        out["violations"] = ";".join(self.violations)
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def _clip(x: Dict[str, float], config: FeFrontierConfig) -> Dict[str, float]:
    out = {}
    for name, (lo, hi) in config.bounds().items():
        if name not in x:
            # Backward compatibility: use mid-range default for new keys
            out[name] = 0.5 * (lo + hi)
            continue
        value = float(np.clip(x[name], lo, hi))
        if not np.isfinite(value):
            raise ValueError(f"design variable {name} became non-finite")
        out[name] = value
    return out


def _constraint_violations(x: Dict[str, float], config: FeFrontierConfig) -> List[str]:
    e_prog = x["overdrive"] * x["ec"]
    violations = []
    if e_prog > config.e_bd:
        violations.append(f"E_prog={e_prog:.3e} > E_bd={config.e_bd:.3e}")
    v_prog = e_prog * x["t_fe_nm"] * 1.0e-9
    if v_prog > config.voltage_ceiling:
        violations.append(
            f"program voltage {v_prog:.2f} V exceeds the "
            f"{config.voltage_ceiling:.0f} V CMOS-relevant ceiling"
        )
    return violations


def _landau_coefficients(ps: float, ec: float) -> Tuple[float, float]:
    beta = ec * 3.0 * math.sqrt(3.0) / (2.0 * ps ** 3)
    return -beta * ps * ps, beta


def _bipolar(v_max: float, n_pts: int) -> np.ndarray:
    seg = np.linspace(0.0, v_max, n_pts)
    return np.concatenate([
        seg, seg[::-1][1:], -seg[1:], -seg[::-1][1:],
    ])


def _loop_crossings(v: np.ndarray, p: np.ndarray) -> Tuple[float, float]:
    """First P zero-crossings after the loop's first extremum (per branch).

    Returns (vc_descent, vc_ascent): the descent-branch crossing (P + -> -)
    and the ascent-branch crossing (P - -> +) of the bipolar sequence.
    """
    v = np.asarray(v, dtype=float)
    p = np.asarray(p, dtype=float)
    extremum = int(np.argmax(np.abs(v)))
    descent = float("nan")
    ascent = float("nan")
    sign_prev = np.sign(p[extremum])
    for k in range(extremum + 1, len(v)):
        sign_now = np.sign(p[k])
        if sign_now != sign_prev and sign_now < 0 and np.isnan(descent):
            descent = 0.5 * (v[k - 1] + v[k])
        if sign_now != sign_prev and sign_now > 0 and not np.isnan(descent) and np.isnan(ascent):
            ascent = 0.5 * (v[k - 1] + v[k])
        sign_prev = sign_now
    return descent, ascent


def _slab_loop(
    x: Dict[str, float],
    config: FeFrontierConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Sweep a 1D FE slab P-V loop with the C++ Preisach ensemble."""
    from tcad.core import PyDeviceSimulator

    n = int(config.slab_nodes)
    t_fe = x["t_fe_nm"] * 1.0e-9
    dx = t_fe / (n - 1)
    v_prog = x["overdrive"] * x["ec"] * t_fe
    alpha, beta = _landau_coefficients(x["ps"], x["ec"])
    sim = PyDeviceSimulator(n, 1, 1, dx, 1.0, 1.0)
    sim.set_permittivity(np.full(n, EPS0 * config.epsilon_r))
    sim.set_mobility(np.zeros(n), np.zeros(n))
    sim.set_doping(np.zeros(n))
    sim.set_thermal_voltage(0.0258520)
    sim.set_recombination(np.full(n, 1.0e-7), np.full(n, 1.0e-7))
    sim.set_effective_dos(np.full(n, 1.0e19), np.full(n, 1.0e19))
    sim.set_bandgap(np.full(n, 5.5))
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(n, dtype=np.int8), alpha, beta)
    sim.set_ferroelectric_model(1)
    sim.set_ferroelectric_preisach(x["ps"], x["ec"], 0.0)
    sim.set_dirichlet_potential({0: 0.0, n - 1: 0.0})
    sim.set_electron_bc({0: 0.0, n - 1: 0.0})
    sim.set_hole_bc({0: 0.0, n - 1: 0.0})

    mid = n // 2
    voltages = _bipolar(v_prog, config.sweep_points_per_segment)
    polarization = []
    for v_applied in voltages:
        sim.set_dirichlet_potential({0: float(v_applied), n - 1: 0.0})
        result = sim.solve()
        polarization.append(float(result["P"][mid][0]))
    return voltages, np.asarray(polarization, dtype=float)


def _endurance_cycles(
    x: Dict[str, float],
    config: FeFrontierConfig,
) -> Tuple[float, float]:
    """Cycles until MW(N) = MW0 * active_fraction(N) < MW0 * floor.

    The M1 states are exact exponentials of the cumulative cycle count, so a
    bisection over strided advances converges to the exact collapse cycle;
    ``last_recheck_deviation`` is returned as the striding audit value.
    """
    model = FieldHistoryCyclingState(
        wakeup_cycles=config.wakeup_cycles,
        fatigue_cycles=config.fatigue_cycles,
        wakeup_gain=config.wakeup_gain,
        fatigue_loss=config.fatigue_loss,
        reference_field=config.reference_field,
        fatigue_field_exponent=config.fatigue_field_exponent,
    )
    e_prog = x["overdrive"] * x["ec"]

    def fraction_at(n_cycles: float) -> Tuple[float, float]:
        probe = FieldHistoryCyclingState(
            wakeup_cycles=config.wakeup_cycles,
            fatigue_cycles=config.fatigue_cycles,
            wakeup_gain=config.wakeup_gain,
            fatigue_loss=config.fatigue_loss,
            reference_field=config.reference_field,
            fatigue_field_exponent=config.fatigue_field_exponent,
        )
        # The M1 updates are exact exponentials of the cumulative cycle count,
        # so a single strided advance over the whole segment is exact; the
        # built-in recheck (8-way explicit split of the same segment) audits
        # that exactness for every probe.
        probe.advance_with_recheck(
            float(n_cycles), e_prog,
            stride=float(max(n_cycles, 1.0)), recheck_every=1, recheck_splits=8,
        )
        return probe.active_fraction, probe.last_recheck_deviation

    target = config.mw_floor_frac
    lo, hi = 1.0, config.endurance_max_cycles
    frac_lo, dev = fraction_at(lo)
    if frac_lo < target:
        return 1.0, dev
    frac_hi, dev = fraction_at(hi)
    if frac_hi >= target:
        return hi, dev
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        frac_mid, dev = fraction_at(mid)
        if frac_mid >= target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), dev


def _switch_time(x: Dict[str, float], config: FeFrontierConfig) -> float:
    """M4 KAI closed-form switching time under the constant program field.

    Under constant field the exact Avrami update gives
    ``x(t) = (t / tau(E))^n`` (analytic golden of the M4 kernel), so the
    completion time is ``tau(E) * (-ln(1 - f_c))^(1/n)``.
    """
    domain = AvramiDomainSwitching(
        avrami_exponent=config.avrami_exponent,
        tau0=x["tau0"],
        onset_field=0.0,
        merz_field=config.merz_field,
        merz_exponent=x["merz_exponent"],
        completion_fraction=_SWITCH_COMPLETION,
        orientation=-1,
    )
    e_prog = x["overdrive"] * x["ec"]
    tau = domain.tau(e_prog)
    x_target = -math.log(1.0 - _SWITCH_COMPLETION)
    return tau * x_target ** (1.0 / config.avrami_exponent)


def evaluate_fe_candidate(
    x: Dict[str, float],
    config: Optional[FeFrontierConfig] = None,
    evaluator: str = "analytic",
) -> FeFrontierCandidate:
    """Evaluate one E1 candidate.

    ``evaluator="solver"`` runs the C++ Preisach slab loop; ``"analytic"``
    uses the exact saturated play-loop crossing formula
    ``MW = 2*t_fe*Ec*(overdrive - 1)`` (crossings at E = E_peak - Ec and
    E = E_min + Ec for a saturated symmetric loop).
    """
    config = config or FeFrontierConfig()
    x = _clip(x, config)
    candidate = FeFrontierCandidate(x=x)
    candidate.violations = _constraint_violations(x, config)
    if candidate.violations:
        return candidate

    t_fe = x["t_fe_nm"] * 1.0e-9
    if evaluator == "solver":
        voltages, polarization = _slab_loop(x, config)
        vc_descent, vc_ascent = _loop_crossings(voltages, polarization)
        if not (np.isfinite(vc_descent) and np.isfinite(vc_ascent)):
            candidate.violations.append("loop did not cross zero within the sweep")
            return candidate
        candidate.mw_V = vc_descent - vc_ascent
        candidate.vc_plus = vc_descent
        candidate.vc_minus = vc_ascent
    elif evaluator == "analytic":
        half_window_field = x["overdrive"] * x["ec"] - x["ec"]
        candidate.mw_V = 2.0 * t_fe * half_window_field
        candidate.vc_plus = t_fe * (x["overdrive"] * x["ec"] - x["ec"])
        candidate.vc_minus = -candidate.vc_plus
    else:
        raise ValueError(f"unknown evaluator mode: {evaluator}")

    if not np.isfinite(candidate.mw_V) or candidate.mw_V <= 0.0:
        candidate.violations.append("non-positive memory window")
        return candidate

    # A10/A11 DD adjudications (2026-09-23, bench/sentaurus/calibration/
    # fefet_memory_window/fefet_{a10,tfe30}): the bare saturated-loop MW
    # formula ignores the series-loaded in-device operation. Sentaurus
    # measured MW=0.366 V at the golden design (t_fe=10nm, Ec=5e7) where
    # the bare formula gives 0.500 V; RAISING Ec to 1.59e8 COLLAPSES the
    # window to 0.016 V, and THICKENING t_fe to 30nm collapses it to
    # 0.039 V (mechanism: the in-device FE field stays sub-coercive; both
    # higher Ec and thicker t_fe push switching further out of reach).
    # Three-point anchored correction, each factor capped at 1:
    #   MW_dd = MW_bare * 0.73 * (5e7/Ec)^3.4 * (10nm/t_fe)^2.6
    mw_factor = 0.73 * (5.0e7 / x["ec"]) ** 3.4 \
        * (10.0 / x["t_fe_nm"]) ** 2.6
    candidate.mw_V *= min(mw_factor, 1.0)
    if not np.isfinite(candidate.mw_V) or candidate.mw_V <= 0.0:
        candidate.violations.append("non-positive DD-corrected memory window")
        return candidate

    candidate.endurance_cycles, candidate.recheck_deviation = _endurance_cycles(x, config)
    candidate.t_switch = _switch_time(x, config)

    # Retention axis: depolarization-driven retention loss.
    # E_dep = Ps/(eps_fe*eps0); the ratio E_dep/Ec determines whether the
    # stored polarization is stable against depolarization back-switching.
    # Physical scaling: retention = 1/(1 + (E_dep/Ec)^2 * depol_factor).
    # High-Ps materials (AlScN) have poor retention; high-Ec stabilizes.
    # This creates the Ps↔Ec↔retention tradeoff with MW = 2*t_fe*Ec*(κ-1).
    e_dep = x["ps"] / (config.eps_fe_retention * 8.854187817e-12)
    depol_ratio = e_dep / max(x["ec"], 1e-30)
    candidate.retention_fraction = float(
        1.0 / (1.0 + depol_ratio ** 2 * config.depol_severity)
    )

    candidate.trusted = (
        np.isfinite(candidate.endurance_cycles)
        and candidate.endurance_cycles >= 1.0
        and np.isfinite(candidate.t_switch)
        and candidate.t_switch > 0.0
        and candidate.recheck_deviation <= 1.0e-9
        and np.isfinite(candidate.retention_fraction)
        and candidate.retention_fraction >= 0.0
    )
    return candidate


# ---------------------------------------------------------------------------
# Generic vector-objective NSGA-II (maximization)
# ---------------------------------------------------------------------------

def _vec_dominates(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.all(a >= b) and np.any(a > b))


def _non_dominated_fronts(objectives: np.ndarray) -> List[List[int]]:
    n = objectives.shape[0]
    dominated_count = np.zeros(n, dtype=int)
    dominates_set: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if _vec_dominates(objectives[i], objectives[j]):
                dominates_set[i].append(j)
                dominated_count[j] += 1
    fronts: List[List[int]] = []
    current = [i for i in range(n) if dominated_count[i] == 0]
    placed = 0
    while current:
        fronts.append(sorted(current))
        placed += len(current)
        next_front: List[int] = []
        for i in current:
            for j in dominates_set[i]:
                dominated_count[j] -= 1
                if dominated_count[j] == 0:
                    next_front.append(j)
        current = next_front
    if placed < n:
        raise RuntimeError("non-dominated sort failed to place all candidates")
    return fronts


def _crowding(objectives: np.ndarray) -> np.ndarray:
    n = objectives.shape[0]
    dists = np.zeros(n)
    if n <= 2:
        return np.full(n, float("inf"))
    for k in range(objectives.shape[1]):
        order = np.argsort(objectives[:, k])
        values = objectives[order, k]
        vmin, vmax = values[0], values[-1]
        dists[order[0]] = float("inf")
        dists[order[-1]] = float("inf")
        if vmax > vmin:
            for idx in range(1, n - 1):
                dists[order[idx]] += (values[idx + 1] - values[idx - 1]) / (vmax - vmin)
    return dists


def _mutate_design(
    x: Dict[str, float],
    config: FeFrontierConfig,
    rng: random.Random,
) -> Dict[str, float]:
    child = {}
    for name, (lo, hi) in config.bounds().items():
        scale = max(hi - lo, 1.0e-30)
        delta = rng.gauss(0.0, config.mutation_sigma) * scale
        child[name] = float(np.clip(x[name] + delta, lo, hi))
    return child


@dataclass
class FeFrontierResult:
    """Outcome of one E1 evolution run."""

    population: List[FeFrontierCandidate]
    front: List[FeFrontierCandidate]
    history: List[Dict[str, float]] = field(default_factory=list)

    def to_rows(self) -> List[Dict[str, float]]:
        return [c.as_dict() for c in self.population]

    def front_rows(self) -> List[Dict[str, float]]:
        return [c.as_dict() for c in self.front]


def evolve_fe_frontier(
    config: Optional[FeFrontierConfig] = None,
    population_size: int = 16,
    generations: int = 8,
    seed: int = 0,
    evaluator: str = "analytic",
    init_population: Optional[List[Dict[str, float]]] = None,
) -> FeFrontierResult:
    """Run the E1 NSGA-II loop (trusted candidates only enter the front)."""
    config = config or FeFrontierConfig()
    if population_size < 4:
        raise ValueError("population_size must be >= 4")
    if generations < 1:
        raise ValueError("generations must be >= 1")
    rng = random.Random(seed)
    bounds = config.bounds()

    def random_design() -> Dict[str, float]:
        return {
            name: rng.uniform(lo, hi) for name, (lo, hi) in bounds.items()
        }

    designs: List[Dict[str, float]] = []
    if init_population:
        designs.extend(_clip(d, config) for d in init_population)
    while len(designs) < population_size:
        designs.append(random_design())

    history: List[Dict[str, float]] = []
    population = [evaluate_fe_candidate(d, config, evaluator) for d in designs]
    for cand in population:
        history.append(cand.as_dict())

    for _ in range(generations):
        objectives = np.vstack([c.objectives for c in population])
        fronts = _non_dominated_fronts(objectives)
        rank = np.empty(len(population), dtype=int)
        crowd = np.zeros(len(population))
        for r, front in enumerate(fronts):
            for i in front:
                rank[i] = r
            front_obj = objectives[front]
            front_crowd = _crowding(front_obj)
            for local_i, i in enumerate(front):
                crowd[i] = front_crowd[local_i]

        children: List[FeFrontierCandidate] = []
        while len(children) < population_size:
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            child_x = _mutate_design(parent.x, config, rng)
            child = evaluate_fe_candidate(child_x, config, evaluator)
            children.append(child)
            history.append(child.as_dict())
        population = children

    objectives = np.vstack([c.objectives for c in population])
    fronts = _non_dominated_fronts(objectives)
    front = [population[i] for i in fronts[0] if population[i].trusted]
    attach_attributions(
        front,
        lambda d: evaluate_fe_candidate(d, config, evaluator),
        config.bounds(),
        lambda c: c.x,
        model_class_limitation="endurance uses the MW(N)=MW0*active_fraction proxy; switching time is the M4 compact waveform model; retention is not modelled (trap-spectrum physical golden pending); the memory window is a saturated-play-loop compact slab, not a full FeFET stack.",
    )
    return FeFrontierResult(population=population, front=front, history=history)
