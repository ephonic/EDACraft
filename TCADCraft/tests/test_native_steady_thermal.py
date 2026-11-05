"""Real C++ thermal states, independent heat-network oracle and corrupt data."""
from copy import deepcopy

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.postprocess import audit_native_steady_thermal

EXTRUSION = np.array([1e-7, 8e-8, 6e-8])
BUDGET = dict(power_atol_W=1e-18, temperature_atol_K=1e-8)


def fixture(*, axis=0, shape=None, graded=True, variable=True, bias=.02):
    if shape is None:
        shape = [1, 1, 1]
        shape[axis] = 5
    axes = [np.array([0.]) if count == 1 else np.linspace(0., 1e-7, count) for count in shape]
    if graded:
        axes[axis] = np.linspace(0., 1., shape[axis])**1.7 * 1e-7
    nx, ny, nz = shape
    size = nx*ny*nz
    coordinates = np.meshgrid(axes[2], axes[1], axes[0], indexing='ij')
    position = coordinates[2-axis].ravel()
    factor1d = .4 + 2.0*axes[axis]/1e-7 if variable else np.ones(shape[axis])
    factor = .4 + 2.0*position/1e-7 if variable else np.ones(size)
    # Match dielectric and transport conductance profiles: constant n=p then
    # satisfies Poisson and both continuity equations at constant terminal J.
    inverse_conductance = np.diff(axes[axis])*(1/factor1d[:-1]+1/factor1d[1:])/2
    phi1d = np.r_[0., np.cumsum(inverse_conductance)]
    phi1d *= bias/phi1d[-1] if bias else 0.
    phi = np.interp(position, axes[axis], phi1d)
    sim = PyDeviceSimulator(nx, ny, nz, *EXTRUSION)
    sim.set_x_positions(axes[0]); sim.set_y_positions(axes[1]); sim.set_z_positions(axes[2])
    sim.set_permittivity(np.ascontiguousarray(1e-10*factor))
    sim.set_mobility(np.ascontiguousarray(.01*factor), np.ascontiguousarray(.005*factor))
    sim.set_doping(np.zeros(size)); sim.set_effective_dos(np.full(size, 1e21), np.full(size, 1e21))
    sim.set_bandgap(np.zeros(size)); sim.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    boundaries = np.flatnonzero((position == 0.) | (position == axes[axis][-1]))
    sim.set_dirichlet_potential({int(n): float(phi[n]) for n in boundaries})
    sim.set_electron_bc({int(n): 1e21 for n in boundaries})
    sim.set_hole_bc({int(n): 1e21 for n in boundaries})
    sim.set_initial_guess(np.ascontiguousarray(phi), np.full(size, 1e21), np.full(size, 1e21))
    sim.set_gummel_max_iter(100); sim.set_tolerance(1e-11)
    sim.set_thermal_coupling_enabled(True)
    conductivity = np.full(size, .001)
    bath = {int(n): 300. for n in boundaries}
    sim.set_thermal_conductivity(conductivity); sim.set_thermal_dirichlet(bath)
    return sim, axes, conductivity, bath


def thermal_oracle_1d(result, x, kappa, bath):
    """Solve the dimensional conductance network without native ledger values."""
    size = len(x)
    area = EXTRUSION[1]*EXTRUSION[2]
    mobile = result['Jn_x']+result['Jp_x']
    if size > 4:
        interior = np.sort(mobile[1:-2])
        mobile = np.full(size, interior[len(interior)//2])
    edge_power = (abs(mobile[:-1]*np.diff(result['phi'])) +
                  abs(result['Jleak_x'][:-1]*np.diff(result['phi']))) * area
    source = np.r_[edge_power/2, 0.] + np.r_[0., edge_power/2]
    conductance = area/np.diff(x)*2/(1/kappa[:-1]+1/kappa[1:])
    matrix = np.zeros((size, size))
    for i, value in enumerate(conductance):
        matrix[i:i+2, i:i+2] += value*np.array([[1., -1.], [-1., 1.]])
    rhs = source.copy()
    for node, temperature in bath.items():
        matrix[node] = 0.
        matrix[node, node] = 1.
        rhs[node] = temperature
    return np.linalg.solve(matrix, rhs), source


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('graded', [False, True])
def test_actual_native_thermal_power_balances_on_each_axis(axis, graded):
    sim, axes, conductivity, bath = fixture(axis=axis, graded=graded)
    result = sim.solve()
    assert result['converged']
    audit = audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)
    assert audit['valid'] and audit['modeled_lattice_power_balance_validated']
    assert audit['source_power_W'] > 0 and audit['direct_bath_deposition_W'] > 0
    assert audit['max_cell_residual_W'] < BUDGET['power_atol_W']
    assert not audit['complete_device_energy'] and not audit['physical_validated']


def test_graded_native_temperature_matches_independent_heat_network():
    sim, axes, conductivity, bath = fixture()
    result = sim.solve()
    expected, source = thermal_oracle_1d(result, axes[0], conductivity, bath)
    np.testing.assert_allclose(result['temperature'], expected, rtol=0., atol=2e-10)
    ledger = result['thermal_ledger']
    np.testing.assert_allclose(ledger['power_density_W_m3']*ledger['node_volumes_m3'], source, rtol=1e-12)
    assert max(result['temperature']) > 300.001


@pytest.mark.parametrize('shape', [(5, 3, 1), (4, 3, 2)])
def test_actual_multidimensional_native_state_closes_heat_balance(shape):
    sim, axes, conductivity, bath = fixture(shape=shape)
    result = sim.solve()
    assert audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)['valid']
    assert result['thermal_ledger']['current_projected'] is False


def test_all_pinned_heat_goes_directly_to_baths():
    sim, axes, conductivity, _ = fixture()
    bath = {n: 300. for n in range(5)}
    sim.set_thermal_dirichlet(bath)
    result = sim.solve()
    audit = audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)
    assert audit['valid']
    assert audit['direct_bath_deposition_W'] == pytest.approx(audit['source_power_W'])
    assert audit['free_node_residuals_W'].size == 0


def test_two_baths_can_exchange_heat_with_zero_electrical_power():
    sim, axes, conductivity, bath = fixture(graded=False, variable=False, bias=0.)
    # Pure dielectric: avoid a relative Poisson norm dominated by tiny carrier
    # cancellation at an exactly zero potential and zero-charge reference.
    sim.set_mobility(np.zeros(5), np.zeros(5))
    sim.set_effective_dos(np.full(5, 1e16), np.full(5, 1e16))
    sim.set_bandgap(np.full(5, 6.))
    sim.set_electron_bc({0: 0., 4: 0.}); sim.set_hole_bc({0: 0., 4: 0.})
    sim.set_initial_guess(np.zeros(5), np.zeros(5), np.zeros(5))
    bath[4] = 350.
    sim.set_thermal_dirichlet(bath)
    result = sim.solve()
    audit = audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)
    assert audit['valid']
    np.testing.assert_allclose(result['temperature'], np.linspace(300., 350., 5), atol=1e-9)
    assert min(result['thermal_ledger']['bath_heat_W']) < 0
    assert max(result['thermal_ledger']['bath_heat_W']) > 0


@pytest.fixture(scope='module')
def actual():
    sim, axes, conductivity, bath = fixture()
    return sim.solve(), axes, conductivity, bath


@pytest.mark.parametrize('field', ['source_power_W', 'outward_heat_W', 'balance_residual_W', 'max_cell_residual_W'])
def test_nanodevice_scalar_power_errors_are_rejected(actual, field):
    result, axes, conductivity, bath = actual
    bad = deepcopy(result)
    bad['thermal_ledger'][field] += 1e-14
    assert not audit_native_steady_thermal(bad, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)['valid']


@pytest.mark.parametrize('field', ['power_density_W_m3', 'flux_x_W', 'bath_heat_W', 'node_volumes_m3'])
def test_forged_native_arrays_are_rejected(actual, field):
    result, axes, conductivity, bath = actual
    bad = deepcopy(result)
    bad['thermal_ledger'][field] *= 1.1
    assert not audit_native_steady_thermal(bad, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)['valid']


def test_wrong_temperature_is_rejected_despite_positive_native_flags(actual):
    result, axes, conductivity, bath = actual
    bad = deepcopy(result)
    bad['temperature'][2] += .001
    assert not audit_native_steady_thermal(bad, axes, conductivity, bath, extrusion_m=EXTRUSION, **BUDGET)['valid']


def test_disabled_and_failed_solves_do_not_publish_valid_thermal_ledger():
    sim, _, _, _ = fixture()
    sim.set_thermal_coupling_enabled(False)
    assert not sim.solve()['thermal_ledger']['available']
    sim.set_thermal_coupling_enabled(True)
    sim.set_gummel_max_iter(0)
    sim.set_initial_guess(np.zeros(5), np.full(5, 2e21), np.full(5, 1e21))
    result = sim.solve()
    assert not result['converged'] and not result['thermal_ledger']['available']


@pytest.mark.parametrize('value', [0., -1., np.nan, np.inf])
def test_invalid_thermal_inputs_raise_python_exceptions(value):
    sim, _, _, _ = fixture()
    with pytest.raises(ValueError): sim.set_thermal_conductivity(np.full(5, value))
    with pytest.raises(ValueError): sim.set_ambient_temperature(value)
    with pytest.raises(ValueError): sim.set_thermal_dirichlet({0: value})
    with pytest.raises(ValueError): sim.set_thermal_dirichlet({5: 300.})


@pytest.mark.parametrize('budget', [True, '1e-18', 0., np.nan])
def test_audit_rejects_invalid_power_budget(actual, budget):
    result, axes, conductivity, bath = actual
    with pytest.raises(ValueError):
        audit_native_steady_thermal(result, axes, conductivity, bath, extrusion_m=EXTRUSION,
                                    power_atol_W=budget, temperature_atol_K=1e-8)
