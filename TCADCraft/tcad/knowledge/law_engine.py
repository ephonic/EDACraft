"""D3+D4 law library engine (plan0619.md §D3+D4).

A *law* maps a structural trigger (``applies_when``) to one or more hard
physical *constraints* that a candidate must satisfy before the expensive
solver is invoked.  Laws live in ``laws.json`` and are evaluated by
:func:`check_all_laws`, which is wired into :func:`tcad.search.evolution.evolve`
as a pre-solver gate (after ``validate``, before ``evaluate_candidate``):
a tree violating any applicable law is rejected without consuming solver
budget — the search's "law constraint reduces wasted solves / false
positives" exit criterion (plan §D3 line 123).

Design notes
------------
* **Geometry is derived from the tree, not ``Candidate.params``.**
  ``_mutate_for_search`` discards the new params returned by
  ``mutate_parameter`` (``evolution.py:73``), and structural/mechanism
  operators never touch params at all — the child carries the parent's
  param dict (``evolution.py:441,469``).  The tree's region boxes are the
  single source of truth, exactly as ``mutate_gate_wrap``
  (``mutation.py:176-180``) and ``mutate_insert_ferroelectric``
  (``mutation.py:302-323``) already derive ``tox``/``t_fe`` from
  ``box[5]-box[4]`` (the z-extent).

* **The engine is the only coupling point between the law library and the
  tree.**  ``extract_geometry`` centralizes every box→quantity derivation so
  laws never reach into ``DeviceTree`` internals directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..search.grammar import (
    DeviceTree, RegionNode,
    KIND_CHANNEL, KIND_SOURCE, KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE,
    KIND_FERROELECTRIC,
)

#: Kinds that count as the gate dielectric (oxide family, excluding FE which
#: is a separate mechanism layer).
_DIELECTRIC_KINDS = (KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE)


# ---------------------------------------------------------------------------
# Geometry extraction (tree → scalar quantities)
# ---------------------------------------------------------------------------

def _z_extent(box) -> float:
    """Z-extent (thickness) of a region box: box[5] - box[4]."""
    return float(box[5] - box[4])


def _x_extent(box) -> float:
    """X-extent (length) of a region box: box[1] - box[0]."""
    return float(box[1] - box[0])


def extract_geometry(tree: DeviceTree) -> Dict[str, Any]:
    """Derive scalar geometry/material quantities from a tree's region boxes.

    This is the **only** function that reads ``DeviceTree`` internals for the
    law engine; all laws key off the returned dict.  Quantities:

    * ``tox``        — gate-oxide (or high-k/IL) thickness [m], z-extent of
                       the first dielectric region; ``None`` if none.
    * ``t_fe``       — ferroelectric layer thickness [m], z-extent of the
                       first FE region; ``None`` if no FE.
    * ``kappa_fe``   — FE permittivity (``material.epsilon_r``); ``None`` if no FE.
    * ``kappa_highk``— high-k permittivity; ``None`` if no high-k.
    * ``Lg``         — gate length [m], x-extent of the first dielectric
                       region (the oxide sits over the channel, so its
                       x-span is exactly Lg); ``None`` if no dielectric.
    * ``channel_Eg`` — channel bandgap [eV] (``material.Eg`` of the channel
                       region); ``None`` if no channel.
    * ``source_material`` — source region material ``name`` (e.g.
                       ``"Graphene"``, ``"Silicon"``); ``None`` if no source.
    * ``has_fe``, ``has_highk`` — convenience booleans.
    """
    out: Dict[str, Any] = {
        "tox": None, "t_fe": None, "kappa_fe": None, "kappa_highk": None,
        "Lg": None, "channel_Eg": None, "source_material": None,
        "has_fe": False, "has_highk": False,
    }
    for rn in tree.region_nodes:
        if rn.kind in _DIELECTRIC_KINDS:
            if out["tox"] is None:
                out["tox"] = _z_extent(rn.box)
                out["Lg"] = _x_extent(rn.box)  # oxide x-span == gate length
            if rn.kind == KIND_HIGHK:
                out["has_highk"] = True
                out["kappa_highk"] = float(rn.material.epsilon_r)
        elif rn.kind == KIND_FERROELECTRIC:
            if out["t_fe"] is None:
                out["t_fe"] = _z_extent(rn.box)
                out["kappa_fe"] = float(rn.material.epsilon_r)
            out["has_fe"] = True
        elif rn.kind == KIND_CHANNEL:
            out["channel_Eg"] = float(rn.material.Eg)
        elif rn.kind == KIND_SOURCE:
            out["source_material"] = rn.material.name
    return out


# ---------------------------------------------------------------------------
# Constraint evaluation
# ---------------------------------------------------------------------------

def _eval_constraint(geom: Dict[str, Any], c: Dict[str, Any]) -> Optional[str]:
    """Evaluate one constraint against the extracted geometry.

    Returns ``None`` if satisfied, or a violation message string if not.
    Supported ``c["type"]``:

    * ``"range"``  — ``geom[c["field"]]`` must be in ``[min, max]``.
    * ``"ratio"``  — ``geom[c["numerator"]] / geom[c["denominator"]]`` must
                     be in ``[min, max]``.

    A relative tolerance of ``1e-9`` is applied at the boundaries so that
    floating-point rounding in the box arithmetic (e.g. ``Lg`` derived as
    ``box[1]-box[0]`` from ``tsi+tox`` recomposition) does not spuriously
    trip a boundary that is satisfied in exact arithmetic.
    """
    ctype = c.get("type")
    if ctype == "range":
        key = c["field"]
        val = geom.get(key)
        if val is None:
            # Field absent (e.g. no FE -> kappa_fe is None): the constraint
            # is not applicable; treat as satisfied.
            return None
        lo, hi = c["min"], c["max"]
        tol = max(abs(lo), abs(hi), abs(val)) * 1e-9
        if not (lo - tol <= val <= hi + tol):
            return c.get("msg", f"{key}={val} outside [{lo}, {hi}]")
        return None
    if ctype == "ratio":
        num = geom.get(c["numerator"])
        den = geom.get(c["denominator"])
        if num is None or den is None or den == 0:
            return None  # not applicable
        ratio = num / den
        lo, hi = c["min"], c["max"]
        tol = max(abs(lo), abs(hi), abs(ratio)) * 1e-9
        if not (lo - tol <= ratio <= hi + tol):
            return c.get("msg", f"{c['numerator']}/{c['denominator']}={ratio} outside [{lo}, {hi}]")
        return None
    return None  # unknown constraint type: pass (fail-open, not fail-closed)


# ---------------------------------------------------------------------------
# applies_when predicate
# ---------------------------------------------------------------------------

def _applies(geom: Dict[str, Any], when: Dict[str, Any]) -> bool:
    """Return True if the law's ``applies_when`` trigger matches the geometry."""
    if when.get("always"):
        return True
    if "has_kind" in when:
        kind = when["has_kind"]
        if kind == "ferroelectric":
            if not geom.get("has_fe"):
                return False
        elif kind == "highk":
            if not geom.get("has_highk"):
                return False
        # other has_kind values could be added; default: check has_fe/has_highk
    if "source_material" in when:
        if geom.get("source_material") != when["source_material"]:
            return False
    return True


# ---------------------------------------------------------------------------
# Law object + checking
# ---------------------------------------------------------------------------

@dataclass
class Law:
    """One structural-trigger → physical-constraint rule."""
    id: str
    name: str
    effect: str
    applies_when: Dict[str, Any]
    constraints: List[Dict[str, Any]]
    rationale: str = ""

    def applies(self, geom: Dict[str, Any]) -> bool:
        return _applies(geom, self.applies_when)

    def violations(self, geom: Dict[str, Any]) -> List[str]:
        """Violation messages for all failed constraints (empty = satisfied)."""
        if not self.applies(geom):
            return []
        out = []
        for c in self.constraints:
            msg = _eval_constraint(geom, c)
            if msg is not None:
                out.append(f"[{self.id}] {msg}")
        return out


def check_law(tree: DeviceTree, law: Law) -> Optional[str]:
    """Return the first violation message for a single law, or None if clean.

    Convenience for single-law testing; :func:`check_all_laws` collects all.
    """
    geom = extract_geometry(tree)
    vs = law.violations(geom)
    return vs[0] if vs else None


def check_all_laws(tree: DeviceTree, laws: List[Law]) -> List[str]:
    """Return all violation messages across all applicable laws (empty = pass).

    This is the pre-solver gate wired into ``evolve()``: a non-empty return
    rejects the candidate before the expensive solve.
    """
    geom = extract_geometry(tree)
    out: List[str] = []
    for law in laws:
        out.extend(law.violations(geom))
    return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_DEFAULT_LAWS_PATH = Path(__file__).resolve().parent / "laws.json"


def load_laws(path: Optional[str] = None) -> List[Law]:
    """Load laws from a JSON file (default: the package ``laws.json``).

    The JSON schema is ``{"laws": [ {id, name, effect, applies_when,
    constraints, rationale}, ... ]}``.
    """
    p = Path(path) if path else _DEFAULT_LAWS_PATH
    with open(p) as f:
        data = json.load(f)
    laws = []
    for entry in data.get("laws", []):
        laws.append(Law(
            id=entry["id"],
            name=entry.get("name", entry["id"]),
            effect=entry.get("effect", ""),
            applies_when=entry.get("applies_when", {}),
            constraints=entry.get("constraints", []),
            rationale=entry.get("rationale", ""),
        ))
    return laws
