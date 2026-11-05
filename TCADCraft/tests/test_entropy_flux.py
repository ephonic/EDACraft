import numpy as np
import pytest
from tcad.physics.entropy_flux import (carrier_entropy_forces,
    entropy_flux_pairing, limit_entropy_flux)

LD = np.longdouble
EPS = np.finfo(LD).eps


def forces(**kwargs):
    args = dict(temperature_owner_K=400, temperature_neighbor_K=700,
        chemical_owner_J=LD('-2e-20'), chemical_neighbor_J=LD('-3e-20'),
        charge_C=LD('-1.602176634e-19'), potential_owner_V=.1,
        potential_neighbor_V=.3, potential_face_V=.18)
    args.update(kwargs)
    return carrier_entropy_forces(**args)


def test_spectral_identity_independently_in_total_energy_coordinates():
    f = forces(); j = LD('1.3e12'); material = LD('2.1e-8')
    total = material+LD('-1.602176634e-19')*LD(.18)*j
    electro_o = LD('-2e-20')+LD('-1.602176634e-19')*LD(.1)
    electro_n = LD('-3e-20')+LD('-1.602176634e-19')*LD(.3)
    expected = j*(electro_o/400-electro_n/700)+total*(LD(1)/700-LD(1)/400)
    np.testing.assert_allclose(entropy_flux_pairing([j, material], f), expected, rtol=64*EPS)


def test_common_electrostatic_gauge_shift():
    original = forces(); shifted = forces(potential_owner_V=LD(.1)+2,
        potential_neighbor_V=LD(.3)+2, potential_face_V=LD(.18)+2)
    np.testing.assert_allclose(shifted, original, rtol=128*EPS)


def test_material_energy_origin_shift_with_matching_energy_flux():
    f = forces(); shift = LD('4e-19'); j = LD('1e12'); u = LD('2e-8')
    changed = forces(chemical_owner_J=LD('-2e-20')+shift,
                     chemical_neighbor_J=LD('-3e-20')+shift)
    np.testing.assert_allclose(entropy_flux_pairing([j, u+shift*j], changed),
        entropy_flux_pairing([j, u], f), rtol=256*EPS)


def test_face_orientation_reversal():
    f = forces(); reverse = carrier_entropy_forces(700, 400, LD('-3e-20'),
        LD('-2e-20'), charge_C=LD('-1.602176634e-19'),
        potential_owner_V=.3, potential_neighbor_V=.1, potential_face_V=.18)
    assert np.array_equal(reverse, -f)
    lo = np.array([2, -1], dtype=LD); hi = -3*lo
    if entropy_flux_pairing(lo, f) < 0: lo, hi = -lo, -hi
    a = limit_entropy_flux(lo, hi, f); b = limit_entropy_flux(-lo, -hi, reverse)
    assert np.array_equal(a.flux, -b.flux)
    assert a.high_order_fraction == b.high_order_fraction


def test_one_weight_preserves_shared_particle_and_energy_flux():
    low = np.array([[3, 1], [2, 4]], dtype=LD)
    high = np.array([[-5, 2], [4, 8]], dtype=LD)
    f = np.array([[1, 1], [1, 1]], dtype=LD)
    result = limit_entropy_flux(low, high, f)
    assert 0 < result.high_order_fraction[0] < LD(4)/7
    assert result.high_order_fraction[1] == 1
    np.testing.assert_allclose(result.flux, low+result.high_order_fraction[:, None]*(high-low),
                               rtol=64*EPS, atol=64*EPS)
    # A face enters its two adjacent cell ledgers with exactly opposite signs.
    assert np.array_equal(result.flux+(-result.flux), np.zeros((2, 2)))
    assert np.all(result.entropy_production >= 0)


def test_admissible_candidate_kept_exactly_and_detached():
    high = np.array([[3, -0.], [4, 1]], dtype=LD)
    result = limit_entropy_flux([[1, 0], [1, 0]], high, [1, 0])
    assert np.array_equal(result.flux, high)
    assert np.signbit(result.flux[0, 1])
    high[:] = -20
    assert result.flux[0, 0] == 3
    for value in (result.flux, result.high_order_fraction, result.entropy_production):
        assert value.flags.owndata and not value.flags.writeable


def test_zero_baseline_rejects_negative_candidate_without_positive_floor():
    result = limit_entropy_flux([0, 1], [-1, 2], [1, 0])
    assert result.high_order_fraction == 0
    assert np.array_equal(result.flux, [0, 1])
    assert result.entropy_production == 0


def test_negative_baseline_is_rejected_even_when_candidate_positive():
    with pytest.raises(ValueError, match='baseline'):
        limit_entropy_flux([-1, 0], [2, 0], [1, 0])


def test_broadcast_faces_and_zero_force():
    result = limit_entropy_flux([1, 1], [[2, 3], [-4, -5]], [[0, 0], [1, 0]])
    assert result.flux.shape == (2, 2)
    assert result.high_order_fraction[0] == 1
    assert np.all(result.entropy_production >= 0)
    assert forces(temperature_owner_K=[300, 400]).shape == (2, 2)


def test_large_opposing_components_do_not_form_overflowing_difference():
    large = np.finfo(LD).max/4
    result = limit_entropy_flux([large, 0], [-large, 0], [1, 0])
    assert np.all(np.isfinite(result.flux)) and result.entropy_production >= 0


def test_random_affine_crossings():
    rng = np.random.default_rng(23513)
    low = rng.uniform(.1, 10, (200, 2)).astype(LD)
    high = -rng.uniform(.1, 10, (200, 2)).astype(LD)
    f = rng.uniform(.1, 10, (200, 2)).astype(LD)
    result = limit_entropy_flux(low, high, f)
    assert np.all((result.high_order_fraction >= 0) & (result.high_order_fraction <= 1))
    assert np.all(entropy_flux_pairing(result.flux, f) >= 0)
    np.testing.assert_allclose(result.flux, (1-result.high_order_fraction[:, None])*low+
        result.high_order_fraction[:, None]*high, rtol=64*EPS, atol=64*EPS)


@pytest.mark.parametrize('bad', [np.nan, np.inf, 1j, '3', True])
def test_bad_force_input(bad):
    with pytest.raises(ValueError): forces(chemical_owner_J=bad)


@pytest.mark.parametrize('bad', [0, -1, [300, 0]])
def test_nonpositive_temperature(bad):
    with pytest.raises(ValueError): forces(temperature_owner_K=bad)


@pytest.mark.parametrize('bad', [1, [1], [1, 2, 3], [[1, 2], [1, np.nan]], [1j, 2]])
def test_malformed_flux(bad):
    with pytest.raises(ValueError): limit_entropy_flux([1, 2], bad, [1, 1])


def test_incompatible_broadcast():
    with pytest.raises(ValueError): limit_entropy_flux(np.ones((3, 2)), np.ones((4, 2)), [1, 1])
