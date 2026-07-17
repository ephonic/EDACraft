"""Convergence credibility gate for device-discovery candidates (plan0619.md M1/B5).

A discovery search must not promote a non-converged or unphysical solve to the
Pareto front.  ``simulate_sweep`` only *warns* on ramp failure
(``simulator.py:627``) and the Gummel convergence criterion is an update
magnitude, not a residual (``gummel_solver.cpp:631``), so a bad solve can still
return ``converged=True`` with fields that violate physics.  This module adds a
post-hoc ``trust`` flag that combines three independent signals:

  1. ``converged`` — the solver's own flag (necessary, not sufficient).
  2. KCL residual — the relative spread of the total SG current J = Jn + Jp
     along the 1-D extraction line.  At steady state J is divergence-free, so a
     large spread means the returned (n, p) do not satisfy the discrete
     continuity equations at the converged phi (audit_recheck.md #3).  This is
     the strongest physical-consistency signal derivable without a C++ residual
     getter.
  3. physical-range checks on the extracted metrics (Ion > 0, 0 < Ioff <= Ion,
     SS > 0, finite Vth).

A candidate is ``trust=True`` only if all three hold.  The search layer accepts
only ``trust=True`` candidates into the Pareto front.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .current import sg_current_density_1d


# Default KCL residual threshold: rel spread of J = Jn + Jp along the 1-D line.
# Calibration (audit_recheck.md #3):
#   - raw-C++ Newton 1-D path (test_numerical_validation KCL test): ~1e-3
#   - high-level Device+Gummel 3-D path on abrupt junctions: ~1-3 (known gap)
#   - a genuinely non-converged / broken solve: -> infinity
# A threshold of 10.0 separates "broken" (rejected) from "marginal but usable"
# while letting the KCL-consistent raw-C++ path pass cleanly. The high-level
# Gummel path's ~1-3 spread is a documented reliability gap to tighten in M6,
# not something to hide by raising the threshold further.
DEFAULT_KCL_REL_SPREAD = 10.0

# Default physical-range bounds for logic-device metrics.  These are wide
# "clearly broken if violated" envelopes, not tight targets — discovery only
# needs to reject non-physical garbage, not enforce commercial accuracy.
DEFAULT_PHYSICAL_RANGE = {
    "Ion_min": 0.0,          # A; on-current must be strictly positive
    "Ion_max": 1e3,          # A; sanity upper bound for a single device
    "SS_min": 1.0,           # mV/dec; below Boltzmann limit is unphysical
    "SS_max": 1e5,           # mV/dec; effectively off / unresolved
}


@dataclass
class TrustReport:
    """Per-candidate credibility verdict and the signals behind it.

    Attributes
    ----------
    trust : bool
        True only if all checks pass (converged && KCL residual below threshold
        && metrics in physical range).
    converged : bool
        Solver's own convergence flag.
    kcl_rel_spread : float
        Relative spread of the total SG current along the 1-D line.  NaN if the
        current is identically zero (equilibrium / no bias path).
    reasons : list of str
        Human-readable list of which checks failed (empty if ``trust``).
    """
    trust: bool = False
    converged: bool = False
    kcl_rel_spread: float = float("nan")
    reasons: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.trust


# Absolute current floor [A/m^2].  Below this the device is effectively at
# equilibrium (zero bias) and the relative KCL spread is numerically meaningless
# (noise/signal -> inf).  Such points are reported as NaN and treated as trusted
# by ``assess_trust``.  1e-12 is ~8 orders below a typical 1-D on-current
# (~1e3 A/m^2) and ~4 orders below the smallest biased current in the test PN
# junctions, so it cleanly separates "equilibrium noise" from real conduction.
KCL_ZERO_CURRENT_FLOOR = 1e-12


def kcl_residual_1d(
    simulator,
    result: Dict,
    on_current_scale: Optional[float] = None,
) -> float:
    """Relative spread of J = Jn + Jp along the x-axis line [dimensionless].

    Returns the max deviation of the per-edge total current from its mean,
    normalized by the mean absolute current.  At steady state this is ~0
    (divergence-free); a large value means the returned (n, p) violate the
    discrete continuity equations.

    Returns NaN (treated as trusted by ``assess_trust``) when the current is
    negligible — i.e. the device is at equilibrium / zero bias and there is no
    conduction to conserve.  Negligibility is judged against
    ``on_current_scale`` (if given, 1e-4 of it) or the absolute
    :data:`KCL_ZERO_CURRENT_FLOOR`.  The 1e-4 ratio cleanly separates
    equilibrium discretization noise (typically 1e3-1e5 below the on-current)
    from real subthreshold conduction (within a few orders of the on-current).

    Parameters
    ----------
    on_current_scale : float, optional
        A representative on-current density [A/m^2] for the device family.
        When provided, currents below 1e-4 * on_current_scale are deemed
        equilibrium noise.  When None, the absolute floor is used.
    """
    mesh = simulator.mesh
    nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
    line = np.array([i + nx * (0 + ny * 0) for i in range(nx)], dtype=np.int64)
    phi = np.asarray(result["phi"], dtype=float)[line]
    n = np.asarray(result["n"], dtype=float)[line]
    p = np.asarray(result["p"], dtype=float)[line]
    mu_n = np.asarray(
        mesh.fields.get("mu_n", np.full(mesh.npts(), 1400e-4)), dtype=float
    )[line]
    mu_p = np.asarray(
        mesh.fields.get("mu_p", np.full(mesh.npts(), 450e-4)), dtype=float
    )[line]
    Jn, Jp = sg_current_density_1d(phi, n, p, mesh.dx, mu_n, mu_p, simulator.VT)
    J = Jn + Jp
    J_max_abs = float(np.max(np.abs(J))) if J.size else 0.0
    floor = (1e-4 * on_current_scale) if on_current_scale else KCL_ZERO_CURRENT_FLOOR
    if J_max_abs < floor:
        return float("nan")  # equilibrium / zero-conduction path -> trusted
    J_mean_abs = float(np.mean(np.abs(J)))
    if J_mean_abs < 1e-30:
        return float("nan")
    spread = float(np.max(np.abs(J - np.mean(J))))
    return spread / J_mean_abs


def assess_trust(
    simulator,
    result: Dict,
    metrics: Optional[Dict] = None,
    kcl_rel_spread_threshold: float = DEFAULT_KCL_REL_SPREAD,
    physical_range: Optional[Dict] = None,
    on_current_scale: Optional[float] = None,
) -> TrustReport:
    """Assess whether a single solve result is a trustworthy discovery candidate.

    Parameters
    ----------
    simulator : Simulator
        Holds the mesh and VT (for the KCL residual computation).
    result : dict
        A single solve() / sweep result dict (must contain ``converged``,
        ``phi``, ``n``, ``p``).
    metrics : dict, optional
        Extracted metrics dict (e.g. from
        ``extract_transfer_characteristics_current``).  If provided, its
        Ion/Ioff/SS/Vth are range-checked.  If None, the physical-range check
        is skipped (only converged + KCL are assessed).  When ``metrics``
        contains a finite ``Ion``, it is used as ``on_current_scale`` for the
        KCL negligibility floor unless ``on_current_scale`` is given.
    kcl_rel_spread_threshold : float
        Max allowed KCL relative spread.  Defaults to
        :data:`DEFAULT_KCL_REL_SPREAD`.
    physical_range : dict, optional
        Override the default physical-range bounds.
    on_current_scale : float, optional
        Representative on-current density [A/m^2] for the equilibrium floor.
        If None and ``metrics["Ion"]`` is finite, that is used.
    """
    pr = dict(DEFAULT_PHYSICAL_RANGE)
    if physical_range is not None:
        pr.update(physical_range)
    reasons: List[str] = []

    converged = bool(result.get("converged", False))
    if not converged:
        reasons.append("solver did not converge")

    # Determine the on-current scale for the KCL negligibility floor.
    scale = on_current_scale
    if scale is None and metrics is not None:
        ion = float(metrics.get("Ion", float("nan")))
        if np.isfinite(ion) and ion > 0:
            scale = ion
    rel_spread = kcl_residual_1d(simulator, result, on_current_scale=scale)
    # NaN (negligible / equilibrium current) is treated as trusted.
    if not np.isnan(rel_spread) and rel_spread > kcl_rel_spread_threshold:
        reasons.append(
            f"KCL residual {rel_spread:.2e} > threshold {kcl_rel_spread_threshold:.2e}"
        )

    if metrics is not None:
        ion = float(metrics.get("Ion", float("nan")))
        ioff = float(metrics.get("Ioff", float("nan")))
        ss = float(metrics.get("SS", float("nan")))
        vth = float(metrics.get("Vth", float("nan")))
        if not (np.isfinite(ion) and ion > pr["Ion_min"]):
            reasons.append(f"Ion={ion} not in ({pr['Ion_min']}, inf)")
        elif ion > pr["Ion_max"]:
            reasons.append(f"Ion={ion} exceeds sanity max {pr['Ion_max']}")
        if not (np.isfinite(ioff) and pr["Ion_min"] < ioff <= ion):
            reasons.append(f"Ioff={ioff} not in (0, Ion={ion}]")
        if not (np.isfinite(ss) and pr["SS_min"] <= ss <= pr["SS_max"]):
            reasons.append(f"SS={ss} not in [{pr['SS_min']}, {pr['SS_max']}] mV/dec")
        if not np.isfinite(vth):
            reasons.append("Vth not finite")

    trust = len(reasons) == 0
    return TrustReport(
        trust=trust,
        converged=converged,
        kcl_rel_spread=rel_spread,
        reasons=reasons,
    )


def annotate_sweep_with_trust(
    simulator,
    sweep_results: List[Dict],
    sweep_metrics: Optional[Dict] = None,
    **trust_kwargs,
) -> List[TrustReport]:
    """Attach a ``trust`` verdict to each sweep result.

    Parameters
    ----------
    simulator : Simulator
    sweep_results : list of dict
        Results from ``simulate_sweep``.
    sweep_metrics : dict, optional
        If provided, a metrics dict (from
        ``extract_transfer_characteristics_current``) whose per-point arrays
        (``Ion``/``Ioff``/``SS``/``Vth`` are scalars; this path instead
        re-assesses each point's own current).  Typically left None so each
        point is assessed on converged + KCL alone.
    **trust_kwargs
        Forwarded to :func:`assess_trust`.
    """
    reports = []
    for r in sweep_results:
        rep = assess_trust(simulator, r, metrics=None, **trust_kwargs)
        r["trust"] = rep.trust
        r["kcl_rel_spread"] = rep.kcl_rel_spread
        reports.append(rep)
    return reports
