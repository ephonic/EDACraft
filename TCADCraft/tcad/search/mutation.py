"""C2 mutation operators for device grammar trees (plan0619.md §C2).

Three mutation families, each producing a new legal ``DeviceTree``:

1. **Parameter mutation** — perturb a resolved geometric/doping parameter
   (thickness, length, doping) and re-emit affected regions.  Implemented by
   re-deriving the template parameter from the tree, perturbing it, and
   rebuilding via ``tree_from_template`` so all downstream Box bounds stay
   consistent (a thickness change shifts every layer above it).

2. **Structural mutation** — change topology at the resolved-node level:
   gate wrap (planar_top → double_y → four_side), layer count, local material
   replacement.  These operate directly on ``RegionNode`` tuples, preserving
   painter order.

3. **Mechanism mutation** — insert a ferroelectric layer (NC effect), insert a
   tunneling source (BTBT), swap source to a Dirac material.  These are the
   "open-space" operators that can produce topologies outside the 14 templates.

Every operator returns a tree that passes ``validate`` (connection rules);
operators that would violate geometry (e.g. inserting FE as the first layer)
return ``None`` instead of an illegal tree, so the search loop can retry.
"""

from __future__ import annotations

import copy
import math
import random
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from .grammar import (
    DeviceTree, RegionNode, ContactSpec, GateStackMeta, MaterialSpec, DopingSpec,
    SILICON, SIO2, GATE_METAL, GRAPHENE, highk_material, ferroelectric_material,
    sige_material, build, validate, tree_from_template, supported_templates,
    KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_WIRE, KIND_OXIDE, KIND_HIGHK,
    KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL, KIND_SUBSTRATE, KIND_BOX,
    WRAP_NONE, WRAP_PLANAR_TOP, WRAP_DOUBLE_Y, WRAP_FOUR_SIDE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_kinds(tree: DeviceTree) -> List[str]:
    return [rn.kind for rn in tree.region_nodes]


def _find_nodes(tree: DeviceTree, kind: str) -> List[int]:
    return [i for i, rn in enumerate(tree.region_nodes) if rn.kind == kind]


def _safe_perturb(value: float, sigma: float, lo: float, hi: float,
                  rng: random.Random) -> float:
    """Multiplicative log-normal perturbation clipped to [lo, hi]."""
    if value <= 0:
        return value
    factor = math.exp(rng.gauss(0.0, sigma))
    return max(lo, min(hi, value * factor))


# ---------------------------------------------------------------------------
# 1. Parameter mutations (rebuild via tree_from_template)
# ---------------------------------------------------------------------------

#: Parameter mutation specs: (param_key, relative_sigma, lo, hi).
#: These are the dimensions a parameter search explores (plan §C2 line 94).
_PARAM_SPECS: Dict[str, Tuple[str, float, float, float]] = {
    # gate length
    "Lg":       ("Lg",       0.20, 5e-9,   200e-9),
    # gate dielectric thickness (tox / t_ox)
    "tox":      ("tox",      0.30, 0.5e-9, 5e-9),
    "t_ox":     ("t_ox",     0.30, 0.5e-9, 5e-9),
    # sheet / wire thickness
    "t_sheet":  ("t_sheet",  0.25, 2e-9,   20e-9),
    "tsi":      ("tsi",      0.25, 2e-9,   20e-9),
    "t_wire":   ("t_wire",   0.25, 2e-9,   20e-9),
    # width
    "W_sheet":  ("W_sheet",  0.25, 5e-9,   100e-9),
    "W":        ("W",        0.25, 5e-9,   500e-9),
    "W_wire":   ("W_wire",   0.25, 3e-9,   50e-9),
    # S/D extension
    "Lsd":      ("Lsd",      0.25, 5e-9,   100e-9),
    # doping (source/channel/drain/uniform)
    "source_doping":  ("source_doping",  0.5, 1e17, 1e21),
    "channel_doping": ("channel_doping", 0.5, 1e14, 1e18),
    "drain_doping":   ("drain_doping",   0.5, 1e18, 1e21),
    "doping":         ("doping",         0.5, 1e18, 1e21),
    "Na":       ("Na", 0.5, 1e14, 1e21),
    "Nd":       ("Nd", 0.5, 1e14, 1e21),
    # FE thickness
    "t_fe":     ("t_fe",     0.30, 1e-9,  15e-9),
}


def mutate_parameter(
    tree: DeviceTree,
    template_name: str,
    params: Dict[str, float],
    rng: Optional[random.Random] = None,
) -> Tuple[Optional[DeviceTree], Dict[str, float]]:
    """Perturb one randomly-chosen parameter and rebuild the tree.

    Returns ``(new_tree, new_params)`` or ``(None, params)`` if the chosen
    parameter is not applicable to this template.  Rebuilding via
    ``tree_from_template`` guarantees all downstream Box bounds stay
    consistent (e.g. changing ``tox`` shifts the gate metal z-position).
    """
    rng = rng or random.Random()
    # Which params does this template accept?
    applicable = [k for k in _PARAM_SPECS if k in params]
    if not applicable:
        return None, params
    key = rng.choice(applicable)
    _, sigma, lo, hi = _PARAM_SPECS[key]
    new_params = dict(params)
    new_params[key] = _safe_perturb(params[key], sigma, lo, hi, rng)
    try:
        new_tree = tree_from_template(template_name, **new_params)
    except (TypeError, ValueError):
        return None, params
    if validate(new_tree):
        return None, params
    return new_tree, new_params


# ---------------------------------------------------------------------------
# 2. Structural mutations (operate on resolved nodes)
# ---------------------------------------------------------------------------

_WRAP_ORDER = [WRAP_PLANAR_TOP, WRAP_DOUBLE_Y, WRAP_FOUR_SIDE]


def mutate_gate_wrap(
    tree: DeviceTree,
    rng: Optional[random.Random] = None,
) -> Optional[DeviceTree]:
    """Change the gate wrap style (planar ↔ double ↔ four-side).

    This is a structural mutation that produces topologies outside the 14
    templates (e.g. a double-gate MOSFET is not a stock template).  Because
    resolved geometry is tied to the original wrap, this operator rebuilds
    a minimal valid gate stack around the existing channel: it keeps the
    channel/source/drain/substrate nodes and replaces the gate region with a
    new wrap-appropriate oxide+metal pair.

    For a search-grade first cut this produces a *plausible* geometry (single
    top oxide for planar, left+right for double, four-side for GAA) rather
    than a byte-exact re-derivation; the trust gate (B5) filters
    non-converging results.
    """
    rng = rng or random.Random()
    if tree.gate_meta is None or tree.gate_meta.wrap == WRAP_NONE:
        return None
    current = tree.gate_meta.wrap
    choices = [w for w in _WRAP_ORDER if w != current]
    new_wrap = rng.choice(choices)

    # Keep non-gate regions (channel/source/drain/substrate/box/wire/via/rail).
    keep_kinds = {
        KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_WIRE,
        KIND_SUBSTRATE, KIND_BOX,
    }
    kept = tuple(rn for rn in tree.region_nodes if rn.kind in keep_kinds)
    if not any(rn.kind == KIND_CHANNEL for rn in kept):
        return None

    # Derive gate region + sheet dimensions from the channel node.
    ch = next(rn for rn in kept if rn.kind == KIND_CHANNEL)
    gx0, gx1, _, W, _, t_sheet = ch.box
    tox = 1.5e-9
    t_gate = 10e-9
    # Reuse existing oxide thickness if present.
    ox_nodes = [rn for rn in tree.region_nodes if rn.kind in (KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE)]
    if ox_nodes:
        # oxide thickness = z-extent of top oxide
        ox = ox_nodes[0]
        tox = ox.box[5] - ox.box[4]

    layer_kinds = (KIND_OXIDE, KIND_METAL)
    new_nodes = list(kept)
    if new_wrap == WRAP_PLANAR_TOP:
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide",
                                    (gx0, gx1, 0, W, t_sheet, t_sheet + tox), SIO2))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal",
                                    (gx0, gx1, 0, W, t_sheet + tox, t_sheet + tox + t_gate), GATE_METAL))
    elif new_wrap == WRAP_DOUBLE_Y:
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_left",
                                    (gx0, gx1, -tox, 0, 0, t_sheet), SIO2))
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_right",
                                    (gx0, gx1, W, W + tox, 0, t_sheet), SIO2))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_left",
                                    (gx0, gx1, -tox - t_gate, -tox, 0, t_sheet), GATE_METAL))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_right",
                                    (gx0, gx1, W + tox, W + tox + t_gate, 0, t_sheet), GATE_METAL))
    else:  # four_side
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_top",
                                    (gx0, gx1, 0, W, t_sheet, t_sheet + tox), SIO2))
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_bottom",
                                    (gx0, gx1, 0, W, -tox, 0), SIO2))
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_left",
                                    (gx0, gx1, -tox, 0, -tox, t_sheet + tox), SIO2))
        new_nodes.append(RegionNode(KIND_OXIDE, "gate_oxide_right",
                                    (gx0, gx1, W, W + tox, -tox, t_sheet + tox), SIO2))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_top",
                                    (gx0, gx1, -tox, W + tox, t_sheet + tox, t_sheet + tox + t_gate), GATE_METAL))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_bottom",
                                    (gx0, gx1, -tox, W + tox, -tox - t_gate, -tox), GATE_METAL))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_left",
                                    (gx0, gx1, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL))
        new_nodes.append(RegionNode(KIND_METAL, "gate_metal_right",
                                    (gx0, gx1, W + tox, W + tox + t_gate, -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL))

    new_meta = GateStackMeta(wrap=new_wrap, layer_kinds=layer_kinds)
    new_tree = DeviceTree(
        name=tree.name + f"_wrap{new_wrap}",
        region_nodes=tuple(new_nodes),
        contacts=tree.contacts,
        gate_meta=new_meta,
    )
    if validate(new_tree):
        return None
    return new_tree


def mutate_material(
    tree: DeviceTree,
    rng: Optional[random.Random] = None,
) -> Optional[DeviceTree]:
    """Replace a region's material with a physically-plausible alternative.

    Targets a channel or source node and swaps its material within a curated
    set (Si ↔ SiGe, or source Si ↔ graphene for the Dirac-source mechanism).
    Dielectric swaps (SiO2 ↔ high-k) target oxide nodes.
    """
    rng = rng or random.Random()
    nodes = list(tree.region_nodes)
    # Pick a mutable target kind.
    channel_idx = _find_nodes(tree, KIND_CHANNEL)
    source_idx = _find_nodes(tree, KIND_SOURCE)
    oxide_idx = [i for i, rn in enumerate(nodes)
                 if rn.kind in (KIND_OXIDE, KIND_HIGHK)]
    targets = channel_idx + source_idx + oxide_idx
    if not targets:
        return None
    idx = rng.choice(targets)
    rn = nodes[idx]

    if rn.kind == KIND_CHANNEL:
        # Si -> SiGe (random Ge fraction) or back to Si.
        ge = rng.uniform(0.1, 0.5)
        new_mat = sige_material(ge) if rng.random() < 0.6 else SILICON
    elif rn.kind == KIND_SOURCE:
        # Si source -> graphene (Dirac-source mechanism) or back.
        new_mat = GRAPHENE if rng.random() < 0.5 else SILICON
    else:  # oxide / highk
        # SiO2 -> high-k or back.
        kappa = rng.uniform(15.0, 40.0)
        new_mat = highk_material(kappa) if rn.kind == KIND_OXIDE else SIO2
        new_kind = KIND_HIGHK if rn.kind == KIND_OXIDE else KIND_OXIDE
        nodes[idx] = replace(rn, material=new_mat, kind=new_kind)
        new_tree = DeviceTree(name=tree.name + "_mat", region_nodes=tuple(nodes),
                              contacts=tree.contacts, gate_meta=tree.gate_meta)
        return None if validate(new_tree) else new_tree

    nodes[idx] = replace(rn, material=new_mat)
    new_tree = DeviceTree(name=tree.name + "_mat", region_nodes=tuple(nodes),
                          contacts=tree.contacts, gate_meta=tree.gate_meta)
    return None if validate(new_tree) else new_tree


# ---------------------------------------------------------------------------
# 3. Mechanism mutations (insert FE / insert BTBT source / back-gate)
# ---------------------------------------------------------------------------

def mutate_insert_ferroelectric(
    tree: DeviceTree,
    kappa_fe: float = 35.0,
    t_fe: float = 4e-9,
    rng: Optional[random.Random] = None,
) -> Optional[DeviceTree]:
    """Insert a ferroelectric layer between the gate dielectric and metal.

    Implements the negative-capacitance mechanism mutation (plan §C2 line 96).
    Requires an existing oxide layer (the FE sits on the channel side of the
    metal, outside the dielectric).  If the tree already has an FE layer, or
    has no oxide, returns None.

    The inserted FE region takes the oxide's xy footprint and occupies a thin
    slab just outside the oxide z-extent (top side only, for planar; the trust
    gate filters geometries that don't converge).  ``validate`` enforces the
    FE-between-dielectric-and-metal rule.
    """
    rng = rng or random.Random()
    if tree.gate_meta is None:
        return None
    if KIND_FERROELECTRIC in tree.gate_meta.layer_kinds:
        return None  # already has FE
    # Need an oxide to sit inside of.
    ox_indices = [i for i, rn in enumerate(tree.region_nodes)
                  if rn.kind in (KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE)]
    if not ox_indices:
        return None

    fe = ferroelectric_material(kappa_fe)
    nodes = list(tree.region_nodes)
    # Insert FE regions just outside each oxide region (same xy, shifted z).
    # For a top oxide (z: t_sheet..t_sheet+tox), FE sits at t_sheet+tox..t_sheet+tox+t_fe.
    insert_at = max(ox_indices) + 1
    fe_nodes: List[RegionNode] = []
    for i in ox_indices:
        ox = nodes[i]
        xmin, xmax, ymin, ymax, zmin, zmax = ox.box
        # Determine which side is "outward" (away from channel at z~0).
        # Top oxide: zmin > 0 -> FE above it. Bottom oxide: zmax < 0 -> FE below.
        if zmin >= 0:
            fe_box = (xmin, xmax, ymin, ymax, zmax, zmax + t_fe)
        else:
            fe_box = (xmin, xmax, ymin, ymax, zmin - t_fe, zmin)
        fe_nodes.append(RegionNode(KIND_FERROELECTRIC, f"fe_{len(fe_nodes)}",
                                   fe_box, fe))
    nodes[insert_at:insert_at] = fe_nodes

    # Update gate_meta layer_kinds: insert FE before the final metal.
    old_kinds = list(tree.gate_meta.layer_kinds)
    if KIND_METAL in old_kinds:
        mi = old_kinds.index(KIND_METAL)
        new_kinds = tuple(old_kinds[:mi] + [KIND_FERROELECTRIC] + old_kinds[mi:])
    else:
        new_kinds = tuple(old_kinds + [KIND_FERROELECTRIC])
    new_meta = GateStackMeta(wrap=tree.gate_meta.wrap, layer_kinds=new_kinds)

    new_tree = DeviceTree(
        name=tree.name + "_fe",
        region_nodes=tuple(nodes),
        contacts=tree.contacts,
        gate_meta=new_meta,
    )
    return None if validate(new_tree) else new_tree


# ---------------------------------------------------------------------------
# Mutation registry
# ---------------------------------------------------------------------------

#: All mutation operators.  Each takes (tree, rng, **kwargs) and returns a new
#: tree or None.  The search loop picks one at random per offspring.
MUTATIONS: Dict[str, Callable] = {
    "parameter": mutate_parameter,
    "gate_wrap": mutate_gate_wrap,
    "material": mutate_material,
    "insert_fe": mutate_insert_ferroelectric,
}


def mutate(
    tree: DeviceTree,
    rng: Optional[random.Random] = None,
    template_name: Optional[str] = None,
    params: Optional[Dict[str, float]] = None,
) -> Optional[DeviceTree]:
    """Apply one randomly-chosen mutation operator.

    ``template_name`` and ``params`` are required for the parameter mutation
    (which rebuilds via ``tree_from_template``); other operators work on the
    resolved tree directly.
    """
    rng = rng or random.Random()
    name = rng.choice(list(MUTATIONS))
    op = MUTATIONS[name]
    if name == "parameter":
        if template_name is None or params is None:
            # Fall back to a structural mutation.
            op = MUTATIONS["material"]
            return op(tree, rng)
        new_tree, _ = op(tree, template_name, params, rng)
        return new_tree
    return op(tree, rng)
