"""Cross-tier device discovery: grammar topologies x mechanism kernels.

This module bridges the two direction-1/2 asset families:

* the topology layer (``tcad.search.grammar`` + ``mutation``): structural
  templates, mechanism mutations (insert ferroelectric layer), gate-wrap and
  material operators, and the D3+D4 law library;
* the mechanism layer (M1-M5 kernels and the E-series compact evaluators):
  fast physics objectives for FE-bearing and tunnel-bearing candidates.

Pipeline per generation
-----------------------
1. structural + mechanism + parameter mutations of the current population
   (insert-FE turns a baseline host into an FE vehicle - topology
   discovery);
2. every candidate passes ``check_all_laws`` (hard structural-physics
   gate) before evaluation;
3. candidates are classified by topology class:
   ``fe`` (ferroelectric in the gate stack) -> evaluated with the E1
   compact physics (MW / endurance via M1 / switching via M4);
   ``tunnel`` (graphene or SiGe source) -> evaluated with the E2 compact
   physics (steepness / on-current / ratio);
   ``baseline`` -> logic hosts; they act as stepping stones for future
   insertions and carry no mechanism objectives;
4. per-class Pareto fronts (vector NSGA-II machinery shared with the
   E-series) with novelty measured by structural signature distance to the
   evaluated archive, and full ``Attribution`` on front members.

Honesty boundaries
------------------
* The compact evaluators do not resolve the host topology: two different
  hosts carrying the same FE stack parameters evaluate identically.  The
  topology question this layer answers is *which structural classes can
  carry the mechanism*, not the host-specific performance - DD-tier
  replay of discovered vehicles is the high-fidelity follow-up.
* Mechanism material parameters (Ps/Ec family, overdrive, Merz knobs) are
  bridge-level mutation parameters, not grammar-node properties; they are
  reported alongside the structural signature.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .attribution import attach_attributions
from .dsfet_frontier import DsFetConfig
from .fe_frontier import (
    FeFrontierConfig,
    _crowding,
    _non_dominated_fronts,
    evaluate_fe_candidate,
)
from .grammar import (
    KIND_FERROELECTRIC,
    KIND_OXIDE,
    KIND_SOURCE,
    DeviceTree,
    tree_from_template,
    validate,
)
from .mutation import (
    mutate_gate_wrap,
    mutate_insert_ferroelectric,
    mutate_material,
    mutate_parameter,
)
from .tfet_frontier import evaluate_tfet_candidate

#: Bridge-level mechanism parameters mutated alongside the tree structure.
FE_BRIDGE_PARAMS = {
    "fe_ps": (0.10, 1.40),
    "fe_ec": (0.5e8, 4.0e8),
    "fe_overdrive": (1.3, 2.1),
    "fe_tau0": (1.0e-12, 1.0e-7),
    "fe_merz": (0.5, 2.0),
}
TUNNEL_BRIDGE_PARAMS = {
    "tunnel_eg": (0.4, 1.12),
    "tunnel_mt": (0.05, 0.3),
    "tunnel_a": (5.0e19, 5.0e21),
    "tunnel_vfb": (-0.25, 0.25),
}


@dataclass
class CrossDiscoveryConfig:
    population_size: int = 12
    generations: int = 6
    seed: int = 0
    insert_fe_probability: float = 0.35
    # Multi-mechanism: BTBT insertion (adds tunneling source to a baseline)
    insert_btbt_probability: float = 0.0
    gate_wrap_probability: float = 0.2
    parameter_sigma: float = 0.15
    fe_evaluator: str = "analytic"

    def bounds(self) -> Dict[str, Tuple[float, float]]:
        merged = dict(FE_BRIDGE_PARAMS)
        merged.update(TUNNEL_BRIDGE_PARAMS)
        return merged


@dataclass
class CrossDiscoveryCandidate:
    tree: DeviceTree
    cls: str = "baseline"
    bridge: Dict[str, float] = field(default_factory=dict)
    objectives_raw: np.ndarray = field(default_factory=lambda: np.array([]))
    novelty: float = 0.0
    signature: str = ""
    law_violations: List[str] = field(default_factory=list)
    attribution: Optional[object] = None
    origin: str = "seed"

    @property
    def objectives(self) -> np.ndarray:
        if self.cls == "baseline" or not np.all(np.isfinite(self.objectives_raw)):
            return np.array([float("-inf")] * 2)
        return np.array([self.novelty, float(np.min(self.objectives_raw))])

    def as_dict(self) -> Dict[str, object]:
        out = {
            "class": self.cls,
            "signature": self.signature,
            "novelty": self.novelty,
            "objectives_raw": list(self.objectives_raw),
            "law_violations": ";".join(self.law_violations),
            "origin": self.origin,
            "valid": float(not self.law_violations),
        }
        out.update({k: v for k, v in self.bridge.items()})
        attribution = getattr(self, "attribution", None)
        if attribution is not None:
            out.update(attribution.as_dict())
        return out


def structural_signature(tree: DeviceTree) -> str:
    kinds = tuple(sorted(node.kind for node in tree.region_nodes))
    wrap = getattr(tree.gate_meta, "wrap", "none") if tree.gate_meta else "none"
    return f"{kinds}|{wrap}"


def classify_tree(tree: DeviceTree) -> str:
    kinds = {node.kind for node in tree.region_nodes}
    if KIND_FERROELECTRIC in kinds:
        return "fe"
    for node in tree.region_nodes:
        if node.kind == KIND_SOURCE and node.material is not None:
            name = getattr(node.material, "name", "")
            if "Graphene" in name or "SiGe" in name or "Ge" == name:
                return "tunnel"
    return "baseline"


def has_btbt_enhanced_source(tree: DeviceTree) -> bool:
    """Check if the tree has a heterojunction or low-bandgap source that
    would enhance BTBT (multi-mechanism discovery: FE + BTBT = NC-TFET)."""
    for node in tree.region_nodes:
        if node.kind == KIND_SOURCE and node.material is not None:
            name = getattr(node.material, "name", "")
            eg = getattr(node.material, "Eg", None)
            if eg is not None and eg < 0.8:
                return True
            if "SiGe" in name or "Ge" == name:
                return True
    return False


def _tree_fe_thickness_nm(tree: DeviceTree) -> Optional[float]:
    for node in tree.region_nodes:
        if node.kind == KIND_FERROELECTRIC:
            zmin, zmax = node.box[4], node.box[5]
            return abs(zmax - zmin) * 1e9
    return None


def _tree_oxide_thickness_nm(tree: DeviceTree) -> float:
    for node in tree.region_nodes:
        if node.kind == KIND_OXIDE:
            zmin, zmax = node.box[4], node.box[5]
            return max(abs(zmax - zmin) * 1e9, 0.3)
    return 1.0


def _default_bridge(rng: random.Random, cls: str) -> Dict[str, float]:
    bridge: Dict[str, float] = {}
    if cls == "fe":
        for name, (lo, hi) in FE_BRIDGE_PARAMS.items():
            bridge[name] = rng.uniform(lo, hi)
    elif cls == "tunnel":
        for name, (lo, hi) in TUNNEL_BRIDGE_PARAMS.items():
            bridge[name] = rng.uniform(lo, hi)
    return bridge


def _mutate_bridge(
    bridge: Dict[str, float], rng: random.Random, sigma: float,
) -> Dict[str, float]:
    child = dict(bridge)
    for name, (lo, hi) in FE_BRIDGE_PARAMS.items():
        if name in child or rng.random() < 0.3:
            base = child.get(name, 0.5 * (lo + hi))
            child[name] = float(np.clip(
                base + rng.gauss(0.0, sigma) * (hi - lo), lo, hi))
    for name, (lo, hi) in TUNNEL_BRIDGE_PARAMS.items():
        if name in child or rng.random() < 0.3:
            base = child.get(name, 0.5 * (lo + hi))
            child[name] = float(np.clip(
                base + rng.gauss(0.0, sigma) * (hi - lo), lo, hi))
    return child


def _evaluate_class(
    candidate: CrossDiscoveryCandidate,
    fe_config: FeFrontierConfig,
) -> np.ndarray:
    if candidate.cls == "fe":
        t_fe = _tree_fe_thickness_nm(candidate.tree)
        if t_fe is None:
            return np.array([float("-inf")] * 3)
        x = {
            "t_fe_nm": float(np.clip(t_fe, *fe_config.t_fe_nm)),
            "ps": candidate.bridge.get("fe_ps", 0.5),
            "ec": candidate.bridge.get("fe_ec", 2.0e8),
            "overdrive": candidate.bridge.get("fe_overdrive", 1.6),
            "tau0": candidate.bridge.get("fe_tau0", 1e-9),
            "merz_exponent": candidate.bridge.get("fe_merz", 1.0),
        }
        result = evaluate_fe_candidate(x, fe_config, evaluator="analytic")
        if not result.trusted:
            return np.array([float("-inf")] * 3)
        return np.array([
            result.mw_V,
            float(np.log10(max(result.endurance_cycles, 1.0))),
            float(np.log10(1.0 / max(result.t_switch, 1e-30))),
        ])
    if candidate.cls == "tunnel":
        x = {
            "eg_t": candidate.bridge.get("tunnel_eg", 0.9),
            "lambda_nm": float(np.clip(
                _tree_oxide_thickness_nm(candidate.tree) * 3.0, 3.0, 15.0)),
            "mt_ratio": candidate.bridge.get("tunnel_mt", 0.1),
            "a_kane": candidate.bridge.get("tunnel_a", 1e21),
            "vfb_offset": candidate.bridge.get("tunnel_vfb", 0.0),
        }
        result = evaluate_tfet_candidate(x)
        if not result.trusted:
            return np.array([float("-inf")] * 3)
        return result.objectives
    return np.array([])


def _novelty(sig: str, archive: List[str]) -> float:
    if not archive:
        return 1.0
    return float(np.mean([sig != other for other in archive]))


def run_cross_discovery(
    seed_templates: Optional[List[str]] = None,
    config: Optional[CrossDiscoveryConfig] = None,
) -> Dict[str, object]:
    """Run the cross-tier discovery loop.

    Returns per-class Pareto fronts (with attributions), the structural
    signature archive, and discovery statistics.
    """
    config = config or CrossDiscoveryConfig()
    rng = random.Random(config.seed)
    from ..knowledge import check_all_laws as _check_laws
    from ..knowledge import load_laws as _load_laws
    check_all_laws = _check_laws
    load_laws = _load_laws
    laws = load_laws()
    fe_config = FeFrontierConfig()
    seed_templates = seed_templates or ["mosfet", "tfet", "gaa"]

    population: List[CrossDiscoveryCandidate] = []
    for name in seed_templates:
        tree = tree_from_template(name)
        cls = classify_tree(tree)
        candidate = CrossDiscoveryCandidate(
            tree=tree, cls=cls, bridge=_default_bridge(rng, cls),
            signature=structural_signature(tree), origin=f"seed:{name}",
        )
        candidate.objectives_raw = _evaluate_class(candidate, fe_config)
        population.append(candidate)

    archive: List[str] = []
    while len(population) < config.population_size:
        parent = rng.choice(population)
        child_tree = mutate_gate_wrap(parent.tree, rng) if rng.random() < 0.5 else parent.tree
        cls = classify_tree(child_tree)
        cand = CrossDiscoveryCandidate(
            tree=child_tree, cls=cls, bridge=_mutate_bridge(
                _default_bridge(rng, cls), rng, config.parameter_sigma),
            signature=structural_signature(child_tree), origin="seed:wrap",
        )
        cand.objectives_raw = _evaluate_class(cand, fe_config)
        population.append(cand)

    for cand in population:
        archive.append(cand.signature)

    history: List[Dict[str, object]] = []
    for cand in population:
        history.append(cand.as_dict())

    for _ in range(config.generations):
        for cand in population:
            cand.novelty = _novelty(cand.signature, archive)
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

        children: List[CrossDiscoveryCandidate] = []
        attempts = 0
        max_attempts = 40 * config.population_size
        while len(children) < config.population_size:
            attempts += 1
            if attempts > max_attempts:
                break
            i, j = rng.sample(range(len(population)), 2)
            if rank[i] < rank[j] or (rank[i] == rank[j] and crowd[i] >= crowd[j]):
                parent = population[i]
            else:
                parent = population[j]
            tree = parent.tree
            origin = "mutate"
            if rng.random() < config.insert_fe_probability:
                # Sample inside the nc_stability law window: kappa in
                # [20, 50], t_fe/tox in [1, 5] with tox read from the host.
                tox_nm = _tree_oxide_thickness_nm(tree)
                ratio = rng.uniform(1.1, 4.9)
                mutated = mutate_insert_ferroelectric(
                    tree,
                    kappa_fe=rng.uniform(21.0, 49.0),
                    t_fe=ratio * tox_nm * 1e-9,
                    rng=rng,
                )
                if mutated is not None:
                    tree = mutated
                    origin = "insert_fe"
            # Multi-mechanism: BTBT source material mutation (opt-in)
            if rng.random() < config.insert_btbt_probability:
                mutated_src = mutate_material(tree, rng)
                if mutated_src is not None:
                    tree = mutated_src
                    origin = origin + "+mat_mut"
            if rng.random() < config.gate_wrap_probability:
                wrapped = mutate_gate_wrap(tree, rng)
                if wrapped is not None:
                    tree = wrapped
                    origin = origin + "+wrap"
            violations = [str(v) for v in check_all_laws(tree, laws)]
            # validate() returns the (possibly empty) error list: truthy
            # means structural errors, so BOTH gates reject on non-empty.
            if violations or validate(tree):
                continue
            cls = classify_tree(tree)
            bridge = _mutate_bridge(parent.bridge, rng, config.parameter_sigma)
            child = CrossDiscoveryCandidate(
                tree=tree, cls=cls, bridge=bridge,
                signature=structural_signature(tree), origin=origin,
                law_violations=[],
            )
            child.objectives_raw = _evaluate_class(child, fe_config)
            archive.append(child.signature)
            children.append(child)
            history.append(child.as_dict())
        if children:
            population = children

    for cand in population:
        cand.novelty = _novelty(cand.signature, archive)

    fronts: Dict[str, List[CrossDiscoveryCandidate]] = {"fe": [], "tunnel": []}
    for cls in ("fe", "tunnel"):
        members = [c for c in population if c.cls == cls and c.objectives.size == 2
                   and np.all(np.isfinite(c.objectives_raw))]
        if len(members) >= 1:
            objs = np.vstack([c.objectives for c in members])
            front_idx = _non_dominated_fronts(objs)[0]
            fronts[cls] = [members[i] for i in front_idx]
            from .attribution import sensitivity_attribution
            all_bounds = config.bounds()
            midpoints = {
                k: 0.5 * (lo + hi) for k, (lo, hi) in all_bounds.items()
            }
            for member in fronts[cls]:
                member.attribution = sensitivity_attribution(
                    lambda bridge, _m=member, _cls=cls, _fe=fe_config:
                        _reEvaluateCandidate(_m, bridge, _cls, _fe),
                    {**midpoints, **member.bridge},
                    all_bounds,
                    model_class_limitation=(
                        "cross-tier compact bridge: the evaluator does not "
                        "resolve the host topology; topology discovery "
                        "answers which structural classes can carry the "
                        "mechanism, not host-specific performance. DD-tier "
                        "replay is the high-fidelity follow-up."
                    ),
                )
    stats = {
        "evaluated": len(history),
        "distinct_signatures": len(set(archive)),
        "fe_candidates": sum(1 for h in history if h["class"] == "fe"),
        "tunnel_candidates": sum(1 for h in history if h["class"] == "tunnel"),
        "insert_fe_origins": sum(
            1 for h in history if "insert_fe" in str(h.get("origin", ""))),
    }
    return {"fronts": fronts, "history": history, "archive": archive, "stats": stats}


def _reEvaluateCandidate(member, bridge, cls, fe_config):
    clone = CrossDiscoveryCandidate(
        tree=member.tree, cls=cls, bridge=dict(bridge),
        signature=member.signature,
    )
    clone.objectives_raw = _evaluate_class(clone, fe_config)
    return clone
