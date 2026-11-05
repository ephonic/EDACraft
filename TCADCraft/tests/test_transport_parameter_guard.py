"""Rejected transport configuration must preserve the next native solution."""
import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator


def resistor(public=False):
    nx = 9
    if public:
        mesh = StructuredGrid(((0., 1e-6), (0., 1.), (0., 1.)), nx, 1, 1)
        owner = Simulator(mesh)
        sim = owner._sim
    else:
        owner = sim = PyDeviceSimulator(nx, 1, 1, 1e-6/(nx-1), 1., 1.)
    sim.set_permittivity(np.full(nx, 8.854187817e-12*11.7))
    sim.set_mobility(np.full(nx, .1), np.full(nx, .035))
    sim.set_doping(np.full(nx, 1e21))
    sim.set_thermal_voltage(.0258520)
    sim.set_recombination(np.full(nx, 1e-7), np.full(nx, 1e-7))
    sim.set_effective_dos(np.full(nx, 2.8e25), np.full(nx, 1.04e25))
    sim.set_bandgap(np.full(nx, 1.12))
    sim.set_dirichlet_potential({0: .2, nx-1: 0.})
    sim.set_electron_bc({0: 1e21, nx-1: 1e21})
    sim.set_hole_bc({0: 1e5, nx-1: 1e5})
    return owner, sim


def same_solution(pristine, rejected):
    a, b = pristine.solve(), rejected.solve()
    assert a['converged'] and b['converged']
    for key in ('phi', 'n', 'p', 'Jn_x', 'Jp_x', 'G_ii'):
        np.testing.assert_array_equal(a[key], b[key], err_msg=key)
    return a


@pytest.mark.parametrize('enabled', [False, True])
def test_hfs_invalid_driving_preserves_solution(enabled):
    _, pristine = resistor()
    _, rejected = resistor()
    for sim in (pristine, rejected):
        sim.set_high_field_saturation(enabled, 5e4, 4e4, 2., 1., 1)
    with pytest.raises(ValueError, match='driving'):
        rejected.set_high_field_saturation(not enabled, 1e4, 2e4, 1., 2., 7)
    same_solution(pristine, rejected)


@pytest.mark.parametrize('slot', range(4))
@pytest.mark.parametrize('bad', [-1., 0., np.nan, np.inf, -np.inf])
def test_hfs_rejects_invalid_numeric(slot, bad):
    _, sim = resistor()
    args = [5e4, 4e4, 2., 1.]
    args[slot] = bad
    with pytest.raises(ValueError, match='finite and > 0'):
        sim.set_high_field_saturation(False, *args, 1)


@pytest.mark.parametrize('slot', range(4))
@pytest.mark.parametrize('bad', [-1., np.nan, np.inf, -np.inf])
def test_ii_rejects_invalid_coefficients(slot, bad):
    _, sim = resistor()
    args = [10., 0., 20., 0.]
    args[slot] = bad
    with pytest.raises(ValueError, match='finite and nonnegative'):
        sim.set_ii_params(*args)


@pytest.mark.parametrize('enabled', [False, True])
def test_ii_rejection_preserves_coefficients_and_enable(enabled):
    _, pristine = resistor()
    _, rejected = resistor()
    for sim in (pristine, rejected):
        sim.set_ii_params(10., 0., 20., 0.)
        sim.set_ii_enabled(enabled)
    with pytest.raises(ValueError, match='nonnegative'):
        rejected.set_ii_params(30., 40., 50., -1.)
    result = same_solution(pristine, rejected)
    assert (np.max(result['G_ii']) > 0.) == enabled


def test_zero_ii_coefficients_are_legal_and_inactive():
    _, pristine = resistor()
    _, zero = resistor()
    zero.set_ii_params(0., 0., 0., 0.)
    zero.set_ii_enabled(True)
    result = same_solution(pristine, zero)
    assert np.count_nonzero(result['G_ii']) == 0


@pytest.mark.parametrize('enabled', [False, True])
def test_public_missing_mesh_field_is_transactional(enabled):
    owner_a, pristine = resistor(public=True)
    owner_b, rejected = resistor(public=True)
    for owner in (owner_a, owner_b):
        owner.set_impact_ionization(enabled, 10., 0., 20., 0.)
    owner_b.mesh.fields['ii_A_n'] = np.full(9, 10.)
    before = repr(owner_b.configuration_snapshot())
    with pytest.raises(KeyError):
        owner_b.set_impact_ionization(not enabled, from_mesh=True)
    assert repr(owner_b.configuration_snapshot()) == before
    result = same_solution(pristine, rejected)
    assert (np.max(result['G_ii']) > 0.) == enabled


def test_public_invalid_mesh_outliers_preserve_solution_and_recipe():
    owner_a, pristine = resistor(public=True)
    owner_b, rejected = resistor(public=True)
    for owner in (owner_a, owner_b):
        owner.set_impact_ionization(True, 10., 0., 20., 0.)
    names = ('ii_A_n', 'ii_B_n', 'ii_A_p', 'ii_B_p')
    owner_b.mesh.fields['mu_n'] = np.ones(9)
    for name in names:
        for bad in (-1., np.nan, np.inf, -np.inf):
            owner_b.mesh.fields.update({key: np.full(9, 10.) for key in names})
            owner_b.mesh.fields[name][4] = bad
            before = repr(owner_b.configuration_snapshot())
            with pytest.raises(ValueError, match='finite and nonnegative'):
                owner_b.set_impact_ionization(False, from_mesh=True)
            assert repr(owner_b.configuration_snapshot()) == before
    same_solution(pristine, rejected)


@pytest.mark.parametrize('enabled', [False, True])
def test_public_invalid_explicit_coefficients_preserve_state(enabled):
    owner_a, pristine = resistor(public=True)
    owner_b, rejected = resistor(public=True)
    for owner in (owner_a, owner_b):
        owner.set_impact_ionization(enabled, 10., 0., 20., 0.)
    before = repr(owner_b.configuration_snapshot())
    with pytest.raises(ValueError, match='nonnegative'):
        owner_b.set_impact_ionization(not enabled, 30., 40., 50., -1.)
    assert repr(owner_b.configuration_snapshot()) == before
    same_solution(pristine, rejected)


def test_public_valid_mesh_sampling_replays():
    from copy import deepcopy
    a, _ = resistor(public=True)
    b, _ = resistor(public=True)
    a.mesh.fields['mu_n'] = np.ones(9)
    for name, value in zip(('ii_A_n', 'ii_B_n', 'ii_A_p', 'ii_B_p'),
                           (10., 0., 20., 0.)):
        a.mesh.fields[name] = np.full(9, value)
    a.set_impact_ionization(True, from_mesh=True)
    # Replay the recorded public call and owned mesh overrides, as remeshing does.
    recipe = a.configuration_snapshot()[-1]
    kwargs = deepcopy(recipe[2])
    b.mesh.fields.update(kwargs.pop('_mesh_overrides'))
    for name in kwargs.pop('_mesh_removed'):
        b.mesh.fields.pop(name, None)
    getattr(b, recipe[1])(**kwargs)
    result = same_solution(a._sim, b._sim)
    assert np.max(result['G_ii']) > 0.
