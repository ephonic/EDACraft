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
from .fe_frontier import (
    FeFrontierConfig, FeFrontierCandidate, FeFrontierResult,
    evaluate_fe_candidate, evolve_fe_frontier,
)
from .mlc_frontier import (
    MlcFrontierConfig, MlcFrontierCandidate, MlcFrontierResult,
    evaluate_mlc_candidate, evolve_mlc_frontier,
)
from .tfet_frontier import (
    TfetFrontierConfig, TfetFrontierCandidate, TfetFrontierResult,
    evaluate_tfet_candidate, evolve_tfet_frontier,
)
from .ncfet_frontier import (
    NcFetStackConfig, NcFetStackCandidate, NcFetFrontierResult,
    evaluate_ncfet_candidate, evolve_ncfet_frontier,
)
from .dsfet_frontier import (
    DsFetConfig, DsFetCandidate, DsFetFrontierResult,
    evaluate_dsfet_candidate, evolve_dsfet_frontier,
)
from .attribution import Attribution, attach_attributions, sensitivity_attribution
from .cross_discovery import (
    CrossDiscoveryConfig,
    CrossDiscoveryCandidate,
    run_cross_discovery,
    classify_tree,
    structural_signature,
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
    # E1 FeFET frontier
    "FeFrontierConfig", "FeFrontierCandidate", "FeFrontierResult",
    "evaluate_fe_candidate", "evolve_fe_frontier",
    # E3 MLC state-design frontier
    "MlcFrontierConfig", "MlcFrontierCandidate", "MlcFrontierResult",
    "evaluate_mlc_candidate", "evolve_mlc_frontier",
    # E2 TFET steepness-current frontier
    "TfetFrontierConfig", "TfetFrontierCandidate", "TfetFrontierResult",
    "evaluate_tfet_candidate", "evolve_tfet_frontier",
    # E0 NC-FET stack electrostatics frontier
    "NcFetStackConfig", "NcFetStackCandidate", "NcFetFrontierResult",
    "evaluate_ncfet_candidate", "evolve_ncfet_frontier",
    # E4 cold-source / Dirac-source FET frontier
    "DsFetConfig", "DsFetCandidate", "DsFetFrontierResult",
    "evaluate_dsfet_candidate", "evolve_dsfet_frontier",
    # frontier-member mechanism attribution
    "Attribution", "attach_attributions", "sensitivity_attribution",
    # cross-tier topology x mechanism discovery
    "CrossDiscoveryConfig", "CrossDiscoveryCandidate", "run_cross_discovery",
    "classify_tree", "structural_signature",
]
