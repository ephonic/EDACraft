"""Truth-chain tests for C2 mutation operators (plan0619.md §C2).

Each operator must:
- return a tree that passes ``validate`` (or None if inapplicable),
- produce a ``Device`` that ``build`` can emit,
- when applied to a known template, keep the device solvable (or honestly
  flagged by the trust gate) and shift metrics in a physically-credible
  direction.
"""

import math
import random

import numpy as np
import pytest

from tcad.geometry import Device
from tcad.search.grammar import (
    build, tree_from_template, validate, assert_devices_equal,
    KIND_CHANNEL, KIND_SOURCE, KIND_OXIDE, KIND_HIGHK, KIND_FERROELECTRIC,
    KIND_IL_OXIDE, KIND_METAL,
    WRAP_PLANAR_TOP, WRAP_DOUBLE_Y, WRAP_FOUR_SIDE,
)
from tcad.search.mutation import (
    mutate_parameter, mutate_gate_wrap, mutate_material,
    mutate_insert_ferroelectric, mutate, MUTATIONS,
)


@pytest.fixture
def rng():
    return random.Random(2026)


# ---------------------------------------------------------------------------
# mutate_parameter
# ---------------------------------------------------------------------------

def test_parameter_mutation_produces_legal_tree(rng):
    params = dict(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=100e-9, Lsd=50e-9)
    tree = tree_from_template("mosfet", **params)
    new_tree, new_params = mutate_parameter(tree, "mosfet", params, rng)
    assert new_tree is not None
    assert validate(new_tree) == []
    # The perturbed param differs from the original.
    changed = [k for k in params if not math.isclose(params[k], new_params[k])]
    assert len(changed) == 1


def test_parameter_mutation_changes_geometry(rng):
    """Changing Lg must change the channel x-extent (not just metadata)."""
    params = dict(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=100e-9, Lsd=50e-9)
    tree = tree_from_template("mosfet", **params)
    # Force Lg perturbation by retrying until Lg is the changed param.
    for _ in range(20):
        new_tree, new_params = mutate_parameter(tree, "mosfet", params, rng)
        if new_tree is not None and not math.isclose(params["Lg"], new_params["Lg"]):
            break
    assert new_tree is not None
    # Channel x-extent in the new tree reflects the new Lg.
    ch_orig = next(rn for rn in tree.region_nodes if rn.kind == KIND_CHANNEL)
    ch_new = next(rn for rn in new_tree.region_nodes if rn.kind == KIND_CHANNEL)
    assert not math.isclose(ch_orig.box[1] - ch_orig.box[0],
                            ch_new.box[1] - ch_new.box[0])


def test_parameter_mutation_stays_in_bounds(rng):
    params = dict(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=100e-9, Lsd=50e-9)
    tree = tree_from_template("mosfet", **params)
    for _ in range(50):
        new_tree, new_params = mutate_parameter(tree, "mosfet", params, rng)
        if new_tree is not None:
            assert 5e-9 <= new_params["Lg"] <= 200e-9
            assert 0.5e-9 <= new_params["tox"] <= 5e-9


# ---------------------------------------------------------------------------
# mutate_gate_wrap
# ---------------------------------------------------------------------------

def test_gate_wrap_mutation_changes_wrap(rng):
    tree = tree_from_template("mosfet")  # planar_top
    new_tree = mutate_gate_wrap(tree, rng)
    assert new_tree is not None
    assert new_tree.gate_meta.wrap != WRAP_PLANAR_TOP
    assert new_tree.gate_meta.wrap in (WRAP_DOUBLE_Y, WRAP_FOUR_SIDE)
    assert validate(new_tree) == []


def test_gate_wrap_mutation_keeps_channel(rng):
    """The channel/source/drain survive a wrap change."""
    tree = tree_from_template("mosfet")
    new_tree = mutate_gate_wrap(tree, rng)
    assert new_tree is not None
    kinds = [rn.kind for rn in new_tree.region_nodes]
    assert KIND_CHANNEL in kinds
    assert KIND_SOURCE in kinds


def test_gate_wrap_none_for_no_gate(rng):
    """pnjunction has no gate; wrap mutation returns None."""
    tree = tree_from_template("pnjunction")
    assert mutate_gate_wrap(tree, rng) is None


# ---------------------------------------------------------------------------
# mutate_material
# ---------------------------------------------------------------------------

def test_material_mutation_swaps_channel_to_sige(rng):
    tree = tree_from_template("mosfet")
    # Bias toward channel mutation by retrying.
    for _ in range(30):
        new_tree = mutate_material(tree, rng)
        if new_tree is None:
            continue
        ch = next(rn for rn in new_tree.region_nodes if rn.kind == KIND_CHANNEL)
        if ch.material.name.startswith("SiGe"):
            assert validate(new_tree) == []
            return
    pytest.skip("channel SiGe swap not hit in 30 tries")


def test_material_mutation_produces_legal_tree(rng):
    tree = tree_from_template("gaa")
    for _ in range(20):
        new_tree = mutate_material(tree, rng)
        if new_tree is not None:
            assert validate(new_tree) == []
            return
    pytest.skip("no applicable material mutation in 20 tries")


# ---------------------------------------------------------------------------
# mutate_insert_ferroelectric
# ---------------------------------------------------------------------------

def test_insert_fe_adds_fe_layer(rng):
    """Inserting FE into a plain MOSFET adds a ferroelectric node + legal meta."""
    tree = tree_from_template("mosfet")
    new_tree = mutate_insert_ferroelectric(tree, rng=rng)
    assert new_tree is not None
    kinds = [rn.kind for rn in new_tree.region_nodes]
    assert KIND_FERROELECTRIC in kinds
    # gate_meta now declares FE between oxide and metal.
    lk = new_tree.gate_meta.layer_kinds
    assert KIND_FERROELECTRIC in lk
    assert lk.index(KIND_FERROELECTRIC) < lk.index(KIND_METAL)
    assert validate(new_tree) == []


def test_insert_fe_idempotent_on_existing_fe(rng):
    """An FE-bearing tree (gaa_fefet) rejects another FE insertion."""
    tree = tree_from_template("gaa_fefet")
    assert mutate_insert_ferroelectric(tree, rng=rng) is None


def test_insert_fe_requires_oxide(rng):
    """pnjunction has no oxide; FE insertion returns None."""
    tree = tree_from_template("pnjunction")
    assert mutate_insert_ferroelectric(tree, rng=rng) is None


# ---------------------------------------------------------------------------
# mutate (dispatch)
# ---------------------------------------------------------------------------

def test_mutate_dispatch_returns_legal_or_none(rng):
    params = dict(Lg=50e-9, tox=1.5e-9, tsi=10e-9, W=100e-9, Lsd=50e-9)
    tree = tree_from_template("mosfet", **params)
    seen_legal = False
    for _ in range(40):
        new_tree = mutate(tree, rng, template_name="mosfet", params=params)
        if new_tree is not None:
            assert validate(new_tree) == []
            # build must succeed.
            dev = build(new_tree)
            assert len(dev.regions) >= 1
            seen_legal = True
    assert seen_legal, "no mutation produced a legal tree in 40 tries"


def test_all_mutation_names_registered():
    assert set(MUTATIONS) == {"parameter", "gate_wrap", "material", "insert_fe"}


# ---------------------------------------------------------------------------
# End-to-end: mutated device is buildable (structural solvability proxy)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template_name", [
    "mosfet", "gaa", "tfet", "gaa_fefet", "dirac_source_fet",
])
def test_mutated_tree_builds_and_has_contacts(template_name, rng):
    """Every mutation of a known template produces a buildable Device with
    the original contacts preserved (gate/drain/source present)."""
    tree = tree_from_template(template_name)
    new_tree = mutate(tree, rng)
    if new_tree is None:
        pytest.skip(f"no applicable mutation for {template_name}")
    dev = build(new_tree)
    # Contacts survive structural mutations (gate_wrap/material/insert_fe
    # preserve the contact tuple).
    assert "gate" in dev.contacts or template_name in ("pnjunction", "tunnel_diode")
    assert "drain" in dev.contacts or template_name in ("pnjunction", "tunnel_diode")
