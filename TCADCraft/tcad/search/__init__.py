"""TCAD device search subsystem: grammar + mutation + evolution (plan0619.md §C)."""

from .grammar import (
    build, validate, tree_from_template, supported_templates,
    template_default_params, assert_devices_equal,
    DeviceTree, RegionNode, ContactSpec, GateStackMeta,
    MaterialSpec, DopingSpec,
    SILICON, SIO2, GATE_METAL, BACKSIDE_METAL, GRAPHENE,
    highk_material, ferroelectric_material, sige_material,
)
from .mutation import (
    mutate, mutate_parameter, mutate_gate_wrap, mutate_material,
    mutate_insert_ferroelectric, MUTATIONS,
)
from .evolution import (
    Candidate, EvolutionResult, Surrogate,
    evolve, evaluate_candidate, compute_perf, compute_novelty,
    non_dominated_sort, crowding_distance, tournament_select,
)

__all__ = [
    # grammar
    "build", "validate", "tree_from_template", "supported_templates",
    "template_default_params", "assert_devices_equal",
    "DeviceTree", "RegionNode", "ContactSpec", "GateStackMeta",
    "MaterialSpec", "DopingSpec",
    "SILICON", "SIO2", "GATE_METAL", "BACKSIDE_METAL", "GRAPHENE",
    "highk_material", "ferroelectric_material", "sige_material",
    # mutation
    "mutate", "mutate_parameter", "mutate_gate_wrap", "mutate_material",
    "mutate_insert_ferroelectric", "MUTATIONS",
    # evolution
    "Candidate", "EvolutionResult", "Surrogate",
    "evolve", "evaluate_candidate", "compute_perf", "compute_novelty",
    "non_dominated_sort", "crowding_distance", "tournament_select",
]
