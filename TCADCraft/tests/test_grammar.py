"""Truth-chain tests for the device grammar tree (plan0619.md §C1).

Verifies that ``build(tree_from_template(name, **p))`` is structurally
identical to ``Device.name(**p)`` for every reverse-induced template, that
``validate`` catches illegal connection rules, and that the grammar can
express template-external topologies (C2 mutation precondition).
"""

import math
import pytest

from tcad.geometry import Device
from tcad.search.grammar import (
    build, tree_from_template, assert_devices_equal, validate,
    DeviceTree, RegionNode, ContactSpec, GateStackMeta,
    MaterialSpec, DopingSpec, SILICON, SIO2, GATE_METAL, GRAPHENE,
    highk_material, ferroelectric_material, sige_material,
    KIND_CHANNEL, KIND_SOURCE, KIND_DRAIN, KIND_OXIDE, KIND_HIGHK,
    KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL,
    WRAP_PLANAR_TOP, WRAP_DOUBLE_Y, WRAP_FOUR_SIDE,
)


# ---------------------------------------------------------------------------
# Equivalence baseline: build(tree_from_template(name, **p)) == Device.name(**p)
# ---------------------------------------------------------------------------

# (template_name, default_params, nondefault_params) for each reverse-induced template.
# nondefault_params verifies parametric pass-through (not hardcoded constants).
EQUIV_CASES = [
    ("pnjunction", {}, dict(L=2e-6, W=1.5e-6, H=0.8e-6, x_junction=0.7e-6, Na=2e16, Nd=3e16)),
    ("tunnel_diode", {}, dict(Lp=30e-9, Ln=25e-9, W=15e-9, H=12e-9, Na=6e20, Nd=4e20)),
    ("mosfet", {}, dict(Lg=80e-9, tox=2e-9, tsi=8e-9, W=120e-9, Lsd=40e-9, Vg=0.5, Vd=0.3, Vs=0.1)),
    ("finfet", {}, dict(Lg=40e-9, tox=2e-9, tsi=8e-9, Hfin=40e-9, Lsd=25e-9, tgate=8e-9, Vg=0.4, Vd=0.2)),
    ("gaa", {}, dict(Lg=30e-9, tox=2e-9, t_sheet=4e-9, W_sheet=25e-9, Lsd=25e-9, t_gate=8e-9, t_box=12e-9, Vg=0.4, Vd=0.3)),
    ("junctionless_fet", {}, dict(Lg=20e-9, tox=2e-9, t_wire=6e-9, W_wire=6e-9, Lsd=20e-9, t_gate=8e-9, doping=2e19, Vg=0.5, Vd=0.4)),
    ("gaa_highk", {}, dict(Lg=15e-9, t_ox=1.2e-9, t_sheet=4e-9, W_sheet=18e-9, Lsd=18e-9, t_gate=8e-9, kappa=30.0, Vg=0.4, Vd=0.3)),
    ("gaa_fefet", {}, dict(Lg=18e-9, t_fe=6e-9, t_ox=1.2e-9, t_sheet=4e-9, W_sheet=18e-9, Lsd=18e-9, t_gate=8e-9, kappa_fe=40.0, Vg=0.4, Vd=0.3)),
    ("bspdn_gaa", {}, dict(Lg=25e-9, tox=2e-9, t_sheet=4e-9, W_sheet=25e-9, Lsd=25e-9, t_gate=8e-9, t_bs_metal=18e-9, t_via=45e-9, t_substrate=28e-9, Vdd=0.75, Vg=0.4, Vd=0.3)),
    ("tfet", {}, dict(Lg=25e-9, tox=2e-9, t_sheet=4e-9, W_sheet=18e-9, Lsd=18e-9, t_gate=8e-9, source_doping=6e20, channel_doping=2e15, drain_doping=2e20, Vg=0.4, Vd=0.4)),
    ("heterojunction_tfet", {}, dict(Lg=25e-9, tox=2e-9, t_sheet=4e-9, W_sheet=18e-9, Lsd=18e-9, L_source_hj=8e-9, t_gate=8e-9, ge_fraction=0.3, source_doping=6e20, channel_doping=2e15, drain_doping=2e20, Vg=0.4, Vd=0.4)),
    ("graphene_source_tfet", {}, dict(Lg=18e-9, tox=1.2e-9, t_sheet=4e-9, W_sheet=18e-9, Lsd=18e-9, t_gate=8e-9, t_box=12e-9, source_doping=6e20, channel_doping=2e15, drain_doping=2e20, Vg=0.4, Vd=0.35)),
    ("dirac_source_fet", {}, dict(Lg=25e-9, tox=2e-9, t_sheet=4e-9, W_sheet=25e-9, Lsd=25e-9, t_gate=8e-9, t_box=12e-9, source_doping=2e18, channel_doping=2e16, drain_doping=2e20, Vg=0.4, Vd=0.35)),
    ("dirac_source_fefet", {}, dict(Lg=25e-9, t_fe=5e-9, t_ox=1.2e-9, t_sheet=4e-9, W_sheet=25e-9, Lsd=25e-9, t_gate=8e-9, kappa_fe=40.0, source_doping=2e18, channel_doping=2e16, drain_doping=2e20, Vg=0.4, Vd=0.35)),
]


@pytest.mark.parametrize("template_name, nondefault", [(n, nd) for n, _, nd in EQUIV_CASES])
def test_grammar_equiv_default(template_name, nondefault):
    """build(tree_from_template(name)) == Device.name() at default params."""
    dev_direct = getattr(Device, template_name)()
    tree = tree_from_template(template_name)
    dev_built = build(tree)
    assert_devices_equal(dev_direct, dev_built, ignore_region_names=True)


@pytest.mark.parametrize("template_name, nondefault", [(n, nd) for n, _, nd in EQUIV_CASES])
def test_grammar_equiv_nondefault(template_name, nondefault):
    """build(tree_from_template(name, **p)) == Device.name(**p) at non-default params.

    This guards against hardcoded constants in the grammar: if a Box bound or
    doping were hardcoded to the template default, this test would catch it.
    """
    dev_direct = getattr(Device, template_name)(**nondefault)
    tree = tree_from_template(template_name, **nondefault)
    dev_built = build(tree)
    assert_devices_equal(dev_direct, dev_built, ignore_region_names=True)


# ---------------------------------------------------------------------------
# validate: connection rules
# ---------------------------------------------------------------------------

def _valid_mosfet_tree():
    return tree_from_template("mosfet")


def test_validate_legal_tree():
    tree = _valid_mosfet_tree()
    errors = validate(tree)
    assert errors == [], f"legal tree flagged: {errors}"


def test_validate_rejects_metal_first():
    """Gate stack with metal as the first (dielectric) layer is illegal."""
    tree = DeviceTree(
        name="bad",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        gate_meta=GateStackMeta(wrap=WRAP_PLANAR_TOP, layer_kinds=(KIND_METAL, KIND_OXIDE)),
    )
    errors = validate(tree)
    assert any("first layer must be a dielectric" in e for e in errors)


def test_validate_rejects_fe_as_last_layer():
    """Ferroelectric must be between dielectric and metal, not last."""
    tree = DeviceTree(
        name="bad",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        gate_meta=GateStackMeta(
            wrap=WRAP_PLANAR_TOP,
            layer_kinds=(KIND_OXIDE, KIND_FERROELECTRIC),
        ),
    )
    errors = validate(tree)
    assert any("ferroelectric layer must be between" in e for e in errors)
    assert any("last layer must be metal" in e for e in errors)


def test_validate_rejects_fe_as_first_layer():
    tree = DeviceTree(
        name="bad",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        gate_meta=GateStackMeta(
            wrap=WRAP_PLANAR_TOP,
            layer_kinds=(KIND_FERROELECTRIC, KIND_METAL),
        ),
    )
    errors = validate(tree)
    assert any("first layer must be a dielectric" in e for e in errors)
    assert any("ferroelectric layer must be between" in e for e in errors)


def test_validate_accepts_fe_between_oxide_and_metal():
    tree = DeviceTree(
        name="ok",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        gate_meta=GateStackMeta(
            wrap=WRAP_FOUR_SIDE,
            layer_kinds=(KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL),
        ),
    )
    errors = validate(tree)
    assert errors == [], f"legal FE stack flagged: {errors}"


def test_validate_rejects_unknown_contact():
    tree = DeviceTree(
        name="bad",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        contacts=(ContactSpec("body_tie", (0, 1, 0, 1, 0, 1), 0.0),),
    )
    errors = validate(tree)
    assert any("unknown contact name 'body_tie'" in e for e in errors)


# ---------------------------------------------------------------------------
# C2 precondition: grammar can express template-external topologies
# ---------------------------------------------------------------------------

def test_mutation_wrap_change_produces_legal_device():
    """Changing mosfet's planar_top wrap to double_y builds a valid Device.

    This is the C2 mutation precondition: the grammar must be able to express
    topologies outside the 14 templates (a double-gate mosfet is not a stock
    template).  build() must succeed; the result is a structurally-valid Device.
    """
    tree = tree_from_template("mosfet")
    new_meta = GateStackMeta(wrap=WRAP_DOUBLE_Y, layer_kinds=tree.gate_meta.layer_kinds)
    mutated = DeviceTree(
        name=tree.name, region_nodes=tree.region_nodes,
        contacts=tree.contacts, gate_meta=new_meta,
    )
    # build should still succeed (geometry is resolved; meta is advisory)
    dev = build(mutated)
    assert dev.regions is not None
    # validate reports no layer-order errors (wrap change is legal)
    errors = validate(mutated)
    assert errors == [], f"wrap-mutated tree flagged: {errors}"


def test_mutation_insert_fe_layer_validates():
    """Inserting an FE layer between oxide and metal is a legal mutation.

    Constructs a tree whose gate_meta declares an IL/FE/metal stack (as in
    gaa_fefet) and confirms validate accepts it.  This is the structural
    precondition for the C2 'insert ferroelectric layer' mechanism mutation.
    """
    tree = DeviceTree(
        name="fe_mutation",
        region_nodes=(RegionNode(KIND_CHANNEL, "ch", (0, 1, 0, 1, 0, 1)),),
        gate_meta=GateStackMeta(
            wrap=WRAP_FOUR_SIDE,
            layer_kinds=(KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL),
        ),
    )
    assert validate(tree) == []


# ---------------------------------------------------------------------------
# Material spec presets
# ---------------------------------------------------------------------------

def test_sige_material_parametric():
    """SiGe material varies with ge_fraction (heterojunction_tfet dependency)."""
    m0 = sige_material(0.0)
    m4 = sige_material(0.4)
    assert m0.name == "SiGe_x0.00"
    assert m4.name == "SiGe_x0.40"
    # Eg decreases with Ge fraction
    assert m4.Eg < m0.Eg
    # epsilon_r increases with Ge fraction
    assert m4.epsilon_r > m0.epsilon_r
    # At x=0 it reduces to silicon-like values
    assert abs(m0.Eg - 1.12) < 1e-12


def test_ferroelectric_material_has_landau_params():
    m = ferroelectric_material(35.0)
    assert m.fe_alpha == -5.0e8
    assert m.fe_beta == 1.5e10
    assert m.epsilon_r == 35.0
    assert m.mu_n == 0.0
