"""Frontier-member mechanism attribution (plan0918 direction-2 governance).

The exploration governance (plan0918 section 5) requires that a candidate
only enters a reported Pareto front with a non-empty mechanism attribution:
the front must answer *why* a member is there, not only *that* it is there.

Method (declared)
-----------------
One-at-a-time local sensitivity: for each design variable ``x_i`` the
candidate is re-evaluated with ``x_i`` nudged by ``delta_frac`` of its
bound span (clipped); the effect is the Euclidean change of the objective
vector.  The contributions are normalized to unit sum and the dominant
variable is reported.  This is a *design-space* attribution (which knob the
member lives by); physics-channel attribution (drift vs tunneling vs
polarization, :mod:`tcad.postprocess.mechanism`) remains the device-level
tool and both statements are complementary.

Every attribution carries ``model_class_limitation`` - the explorer's
declared boundary - so a front report can never present a mechanism claim
without its model scope (comment7 7.5: results must not be explained toward
whatever the model can express).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class Attribution:
    """Normalized sensitivity attribution for one frontier member."""

    contributions: Dict[str, float]
    dominant: str
    method: str = "one_at_a_time_local_sensitivity"
    delta_frac: float = 0.05
    model_class_limitation: str = ""
    base_objectives: Optional[Tuple[float, ...]] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "attribution_method": self.method,
            "attribution_contributions": dict(
                sorted(self.contributions.items(), key=lambda kv: -kv[1])
            ),
            "attribution_dominant": self.dominant,
            "model_class_limitation": self.model_class_limitation,
        }


def sensitivity_attribution(
    evaluate_fn: Callable[[Dict[str, float]], object],
    x: Dict[str, float],
    bounds: Dict[str, Tuple[float, float]],
    delta_frac: float = 0.05,
    model_class_limitation: str = "",
) -> Attribution:
    """Compute the OAT sensitivity attribution for one candidate.

    ``evaluate_fn`` must return a candidate object exposing an
    ``objectives`` ndarray (all frontier candidates do).  Untrusted
    perturbed evaluations contribute zero effect for that variable (the
    boundary cliff itself is reported through the violation, not by
    extrapolating).
    """
    if not 0.0 < delta_frac < 1.0:
        raise ValueError("delta_frac must lie in (0, 1)")
    base = evaluate_fn(dict(x))
    base_obj = np.asarray(base.objectives, dtype=float)
    trusted_base = bool(getattr(base, "trusted", True))
    effects: Dict[str, float] = {}
    for name, (lo, hi) in bounds.items():
        step = delta_frac * (hi - lo)
        nudged = dict(x)
        nudged[name] = float(np.clip(float(x[name]) + step, lo, hi))
        if nudged[name] == float(x[name]):
            effects[name] = 0.0
            continue
        perturbed = evaluate_fn(nudged)
        pert_obj = np.asarray(perturbed.objectives, dtype=float)
        if not trusted_base or not bool(getattr(perturbed, "trusted", True)):
            effects[name] = 0.0
            continue
        effects[name] = float(np.linalg.norm(pert_obj - base_obj))
    total = sum(effects.values())
    if total > 0.0:
        contributions = {k: v / total for k, v in effects.items()}
    else:
        contributions = {k: 0.0 for k in effects}
    dominant = max(contributions, key=contributions.get) if contributions else ""
    return Attribution(
        contributions=contributions,
        dominant=dominant,
        delta_frac=delta_frac,
        model_class_limitation=model_class_limitation,
        base_objectives=tuple(float(v) for v in base_obj),
    )


def attach_attributions(
    front: List[object],
    evaluate_fn: Callable[[Dict[str, float]], object],
    bounds: Dict[str, Tuple[float, float]],
    to_design: Callable[[object], Dict[str, float]],
    model_class_limitation: str = "",
    delta_frac: float = 0.05,
) -> None:
    """Attach ``candidate.attribution`` (an :class:`Attribution`) in place.

    ``to_design`` maps a frontier candidate to its pure design-variable
    dict (several explorers carry discrete fields like the MLC level count
    outside the continuous bounds).
    """
    for cand in front:
        x = to_design(cand)
        cand.attribution = sensitivity_attribution(
            evaluate_fn, x, bounds, delta_frac=delta_frac,
            model_class_limitation=model_class_limitation,
        )
