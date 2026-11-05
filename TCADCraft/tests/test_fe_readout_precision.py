"""Direct FE readout: strict inputs and exact-rational quadrature oracles."""
from fractions import Fraction
from itertools import permutations
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.postprocess import polarization_readout


def mesh(volumes, **fields):
    return SimpleNamespace(npts=lambda: len(volumes),
                           fields={"control_volume": np.asarray(volumes), **fields})


def polarization(values):
    result = np.zeros((len(values), 3))
    result[:, 0] = values
    return result


def rational_mean(values, weights, absolute=False):
    weighted = sum((Fraction(float(w))*Fraction(abs(float(p)) if absolute else float(p))
                    for w, p in zip(weights, values)), Fraction())
    return float(weighted / sum((Fraction(float(w)) for w in weights), Fraction()))


@pytest.mark.parametrize("field", ["P", "fe_alpha", "control_volume", "fe_volume_fraction"])
@pytest.mark.parametrize("kind", ["complex", "string", "bool", "object"])
def test_direct_readout_rejects_coerced_physical_arrays(field, kind):
    P, grid = polarization([.1, .2]), mesh([1., 2.])
    value = P if field == "P" else np.ones(2)
    if kind == "complex":
        value = value.astype(complex) + 1j
    elif kind == "string":
        value = value.astype(str)
    elif kind == "bool":
        value = np.ones_like(value, dtype=bool)
    else:
        value = value.astype(object)
    if field == "P":
        P = value
    else:
        grid.fields[field] = value
    with pytest.raises(ValueError):
        polarization_readout(P, grid)


@pytest.mark.parametrize("mask", [np.array([1, 0], dtype=complex), ["1", "0"],
                                  np.array([1, 0], dtype=object)])
def test_FE_mask_requires_boolean_or_real_binary_values(mask):
    with pytest.raises(ValueError):
        polarization_readout(polarization([.1, .2]), mesh([1., 2.]), fe_mask=mask)


@pytest.mark.parametrize("kind", ["complex", "string", "bool"])
def test_geometry_callback_uses_same_volume_validation(kind):
    types = {"complex": complex, "string": str, "bool": bool}
    grid = SimpleNamespace(npts=lambda: 2, fields={},
                           control_volumes=lambda: np.ones(2).astype(types[kind]))
    with pytest.raises(ValueError):
        polarization_readout(polarization([.1, .2]), grid)


@pytest.mark.parametrize("count", [True, 2., "2", 0, -1])
def test_invalid_mesh_count_is_rejected_as_value_error(count):
    grid = SimpleNamespace(npts=lambda: count, fields={"control_volume": [1., 1.]})
    with pytest.raises(ValueError):
        polarization_readout(polarization([.1, .2]), grid)


@pytest.mark.parametrize("weights,values", [
    ([1e-300, 1e300], [1e300, 0.]),
    ([5e-324, 1e308], [1e308, 0.]),
    ([1e-200, 1e200], [1e200, 0.]),
])
def test_normalization_cannot_erase_representable_cell_contribution(weights, values):
    output = polarization_readout(polarization(values), mesh(weights))
    expected = rational_mean(values, weights)
    np.testing.assert_allclose(output["mean_polarization"], expected, rtol=2e-15, atol=0.)
    np.testing.assert_allclose(output["mean_absolute_polarization"], expected, rtol=2e-15, atol=0.)
    assert output["contributing_nodes"] == 2


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_domain_cancellation_retains_small_residual_in_any_order(order):
    values = np.array([1e308, 1., -1e308])[list(order)]
    output = polarization_readout(polarization(values), mesh(np.ones(3)))
    assert output["mean_polarization"] == pytest.approx(1/3, abs=1e-15)
    np.testing.assert_allclose(output["mean_absolute_polarization"],
                               rational_mean(values, np.ones(3), absolute=True), rtol=2e-15)


@pytest.mark.parametrize("count", [2, 3, 17])
def test_subnormal_constant_polarization_is_not_rounded_away_per_cell(count):
    values = np.full(count, 5e-324)
    output = polarization_readout(polarization(values), mesh(np.ones(count)))
    assert output["mean_polarization"] == 5e-324
    assert output["mean_absolute_polarization"] == 5e-324


@pytest.mark.parametrize("seed", range(10))
def test_wide_range_quadrature_matches_exact_float_input_oracle(seed):
    rng = np.random.default_rng(seed)
    weights = np.ldexp(rng.uniform(.5, 1., 7), rng.integers(-1000, 1001, 7))
    values = np.ldexp(rng.uniform(-1., 1., 7), rng.integers(-1000, 1001, 7))
    output = polarization_readout(polarization(values), mesh(weights))
    for field, absolute in (("mean_polarization", False), ("mean_absolute_polarization", True)):
        expected = rational_mean(values, weights, absolute)
        np.testing.assert_allclose(output[field], expected, rtol=4e-15, atol=0.)


@pytest.mark.parametrize("mask", [[True, False], [1, 0], [1., 0.]])
def test_supported_masks_and_integer_physical_arrays_still_work(mask):
    grid = mesh([2, 3], fe_alpha=np.array([-1, -1]), fe_volume_fraction=np.array([1, 1]))
    P = np.array([[2, 0, 0], [-1, 0, 0]])
    output = polarization_readout(P, grid, fe_mask=mask)
    assert output["mean_polarization"] == 2.
    assert output["fe_volume_m3"] == 2.


@pytest.mark.parametrize("field", ["P", "fe_alpha", "control_volume", "fe_volume_fraction"])
@pytest.mark.parametrize("value", ["1e400", "1e-400"])
def test_extended_precision_values_must_survive_float64_conversion(field, value):
    if np.finfo(np.longdouble).maxexp <= np.finfo(float).maxexp:
        pytest.skip("platform has no wider floating-point input type")
    grid, P = mesh([1., 1.]), polarization([.1, .2]).astype(np.longdouble)
    if field == "P":
        P[0, 0] = np.longdouble(value)
    else:
        array = np.ones(2, dtype=np.longdouble)
        array[0] = np.longdouble(value)
        grid.fields[field] = array
    with pytest.raises(ValueError):
        polarization_readout(P, grid)


@pytest.mark.parametrize("count", [2, 3, 17])
def test_largest_finite_constant_polarization_has_finite_mean(count):
    largest = np.finfo(float).max
    output = polarization_readout(polarization(np.full(count, largest)), mesh(np.ones(count)))
    np.testing.assert_allclose(output["mean_polarization"], largest, rtol=2e-15)
    np.testing.assert_allclose(output["mean_absolute_polarization"], largest, rtol=2e-15)
