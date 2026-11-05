"""Physical coordinate controls for the high-level nonuniform mesh pipeline."""
import json
from pathlib import Path

import numpy as np
import pytest

from tcad.geometry.device_builder import Box, Device, Material, Region
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess.fe_readout import polarization_readout
from tcad.postprocess import audit_transient_dielectric_energy
from tcad.simulator import Simulator
from tcad.core import native_constants

EPS0 = 8.854187817e-12


def mesh_for(axis, coordinates=(0., .1, .4, .7, 1.), scale=1e-6, full=False):
    axes = [np.array([0., .3, 1.]) * scale if full else np.array([0.]) for _ in range(3)]
    axes[axis] = np.array(coordinates) * scale
    return StructuredGrid(((0., scale),) * 3, *(len(a) for a in axes), axes=axes)


def simulator(mesh, axis, path='gummel'):
    n = mesh.npts()
    sim = Simulator(mesh)
    low = sim._sim
    low.set_permittivity(np.full(n, 3.9 * EPS0))
    low.set_mobility(np.zeros(n), np.zeros(n))
    low.set_doping(np.zeros(n))
    low.set_effective_dos(np.ones(n), np.ones(n))
    low.set_bandgap(np.full(n, 6.))
    low.set_recombination(np.full(n, 1e100), np.full(n, 1e100))
    low.set_initial_guess(np.zeros(n), np.zeros(n), np.zeros(n))
    xyz = mesh.flat_coords()
    low.set_dirichlet_potential({i: float(.2 * (xyz[axis][i] > 0.)) for i in range(n)
                                if xyz[axis][i] == 0. or xyz[axis][i] == 1e-6})
    low.set_use_newton(path != 'gummel')
    low.set_newton_primary(path == 'newton')
    return sim


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('path', ['gummel', 'hybrid', 'newton'])
@pytest.mark.parametrize('full', [False, True])
def test_high_level_native_affine_solution_uses_physical_distances(axis, path, full):
    mesh = mesh_for(axis, full=full)
    sim = simulator(mesh, axis, path)
    state = sim.run(max_iter=80, tol=1e-12, physical_step=False)
    assert state['converged']
    expected = .2 * mesh.flat_coords()[axis] / 1e-6
    np.testing.assert_allclose(state['phi'], expected, rtol=1e-9, atol=2e-12)
    np.testing.assert_allclose(state['E' + 'xyz'[axis]], -2e5, rtol=1e-9)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('path', ['gummel', 'newton'])
def test_nonuniform_charge_matches_independent_control_volume_matrix(axis, path):
    mesh = mesh_for(axis)
    sim = simulator(mesh, axis, path)
    x = mesh.axis_coordinates()[axis]
    doping = np.array([0., 1., 2., 3., 0.]) * 1e21
    sim._sim.set_doping(doping)
    matrix = np.zeros((5, 5))
    rhs = np.zeros(5)
    matrix[0, 0] = matrix[-1, -1] = 1.
    rhs[-1] = .2
    for i in range(1, 4):
        left, right = 3.9 * EPS0 / np.array([x[i] - x[i - 1], x[i + 1] - x[i]])
        matrix[i, i - 1], matrix[i, i], matrix[i, i + 1] = -left, left + right, -right
        charge = {'si': 1.602176634e-19, 'legacy-charge': 1.602192e-19}[native_constants()['profile']]
        rhs[i] = charge * doping[i] * (x[i + 1] - x[i - 1]) / 2
    state = sim.run(max_iter=100, tol=1e-12, physical_step=False)
    assert state['converged']
    np.testing.assert_allclose(state['phi'], np.linalg.solve(matrix, rhs), rtol=1e-8, atol=2e-11)


@pytest.mark.parametrize('shape', [(5, 1, 1), (1, 5, 1), (1, 1, 5), (5, 3, 4)])
@pytest.mark.parametrize('scale', [1e-30, 1., 1e30])
def test_nonuniform_dual_volume_quadrature_integrates_multilinear_fields(shape, scale):
    axes = [np.linspace(0., 1., n)**2 * scale if n > 1 else np.array([0.]) for n in shape]
    mesh = StructuredGrid(((0., scale),) * 3, *shape, axes=axes)
    volume = mesh.control_volumes()
    assert volume.sum() / scale**3 == pytest.approx(1., rel=2e-15)
    xyz = [a / scale if n > 1 else np.full(mesh.npts(), .5) for a, n in zip(mesh.flat_coords(), shape)]
    x, y, z = xyz
    field = 2 + x + y*z + x*y*z
    assert np.dot(volume / scale**3, field) == pytest.approx(2 + .5 + .25 + .125, rel=3e-15)


@pytest.mark.parametrize('axis', range(3))
def test_nonuniform_fe_readout_uses_geometric_dual_weights(axis):
    mesh = mesh_for(axis, coordinates=[0., .1, 1.], scale=1.)
    P = np.zeros((3, 3))
    P[:, axis] = [0., 1., 0.]
    out = polarization_readout(P, mesh, polar_axis=axis)
    assert out['mean_polarization'] == pytest.approx(.5)
    assert out['fe_volume_m3'] == pytest.approx(1.)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('method', ['prolongate', 'raw', 'restrict'])
def test_grid_transfer_preserves_affine_physical_fields(axis, method):
    source = mesh_for(axis, scale=1., full=True)
    target = mesh_for(axis, coordinates=[0., .05, .2, .5, .8, 1.], scale=1., full=True)
    x, y, z = source.flat_coords()
    source.add_field('u', 2 + 3*x - y + .5*z + x*y*z)
    expected = lambda grid: 2 + 3*grid.flat_coords()[0] - grid.flat_coords()[1] + .5*grid.flat_coords()[2] + np.prod(grid.flat_coords(), axis=0)
    if method == 'raw':
        found = AdaptiveRefiner._prolongate_data(source, target, source.fields['u'])
    elif method == 'restrict':
        found = AdaptiveRefiner.restrict(source, target, 'u')
    else:
        found = AdaptiveRefiner.prolongate(source, target, 'u')
    np.testing.assert_allclose(found, expected(target), rtol=2e-15, atol=2e-15)


@pytest.mark.parametrize('axis', range(3))
def test_adaptive_generated_mesh_reaches_native_with_actual_coordinates(axis):
    dev = Device().add_region(Region('base', Box(0., 1e-6, 0., 1e-6, 0., 1e-6), Material('base')))
    refiner = AdaptiveRefiner(dev, base_resolution=(.5e-6,) * 3)
    coarse = refiner.generate_feature_refined_mesh(level=0)
    markers = {a: np.zeros((2, 2, 2), dtype=bool) for a in 'xyz'}
    selector = [slice(None)] * 3
    selector[axis] = 0
    markers['xyz'[axis]][tuple(selector)] = True
    fine = refiner._refine_from_markers(coarse, markers, level=1)
    np.testing.assert_allclose(fine.axis_coordinates()[axis] / 1e-6, [0., .25, .5, 1.])
    sim = simulator(fine, axis)
    state = sim.run(max_iter=80, tol=1e-12, physical_step=False)
    assert state['converged']
    np.testing.assert_allclose(state['phi'], .2 * fine.flat_coords()[axis] / 1e-6, atol=2e-12, rtol=1e-9)


@pytest.mark.parametrize('axis', range(3))
def test_nonuniform_residual_marker_annihilates_affine_field_and_detects_curvature(axis):
    mesh = mesh_for(axis, coordinates=[0., .1, .4, .7, 1.], scale=1., full=True)
    refiner = AdaptiveRefiner(Device())
    x = mesh.flat_coords()[axis]
    affine = refiner._compute_solution_error_markers(mesh, {'phi': x}, level=0, fields=['phi'], mode='residual')
    assert not any(m.any() for m in affine.values())
    curved = refiner._compute_solution_error_markers(mesh, {'phi': x*x}, level=0, fields=['phi'], mode='residual')
    assert all(m.any() for m in curved.values())


@pytest.mark.parametrize('axis', range(3))
def test_doping_gradient_marker_uses_each_local_edge_length(axis):
    mesh = mesh_for(axis, coordinates=[0., .1, 1.], scale=1., full=True)
    mesh.add_field('doping', mesh.flat_coords()[axis])
    refiner = AdaptiveRefiner(Device(), directional_thresholds={a: 1.1 for a in 'xyz'})
    assert not any(m.any() for m in refiner._compute_feature_markers(mesh).values())


@pytest.mark.parametrize('axis', range(3))
def test_solution_gradient_marker_uses_local_spacing(axis):
    mesh = mesh_for(axis, coordinates=[0., .1, 1.], scale=150., full=True)
    refiner = AdaptiveRefiner(Device())
    marked = refiner._compute_solution_error_markers(mesh, {'phi': mesh.flat_coords()[axis]},
                                                    level=0, fields=['phi'], mode='gradient')
    assert not any(m.any() for m in marked.values())


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('full', [False, True])
def test_global_error_indicator_uses_physical_metric_and_ignores_singletons(axis, full):
    mesh = mesh_for(axis, coordinates=[0., .1, .4, .7, 1.], scale=2., full=full)
    refiner = AdaptiveRefiner(Device())
    field = mesh.flat_coords()[axis]
    gradient = refiner._compute_global_error(mesh, {'phi': field}, ['phi'], 'gradient')
    residual = refiner._compute_global_error(mesh, {'phi': field}, ['phi'], 'residual')
    assert gradient == pytest.approx(.5, rel=1e-14)
    assert residual < 1e-13


@pytest.mark.parametrize('axis', range(3))
def test_high_level_nonuniform_transient_retains_charge_and_energy_closure(axis):
    mesh = mesh_for(axis)
    sim = simulator(mesh, axis)
    low = sim._sim
    low.set_dirichlet_potential({0: 0., mesh.npts() - 1: 0.})
    low.set_transient_dt(1e-10)
    low.set_transient_t_final(2e-10)
    low.set_transient_voltage_waveforms([0., 1e-10, 2e-10], {mesh.npts() - 1: [0., .2, 0.]})
    history = sim.run_transient(max_iter=80, tol=1e-12)
    cap = 3.9 * EPS0 * 1e-6
    assert len(history) == 3
    for state in history:
        voltage = np.interp(state['time_s'], [0., 1e-10, 2e-10], [0., .2, 0.])
        assert state['valid'] and state['dielectric_energy_available']
        np.testing.assert_allclose(state['phi'], voltage * mesh.flat_coords()[axis] / 1e-6, atol=2e-12, rtol=1e-9)
        np.testing.assert_allclose(state['electrode_charges_C'], [-cap * voltage, cap * voltage], rtol=1e-9, atol=1e-32)
        assert state['dielectric_energy_J'] == pytest.approx(.5 * cap * voltage**2, rel=1e-9, abs=1e-34)
    report = audit_transient_dielectric_energy(history)
    assert report['valid'] and report['energy_balance_validated']
    assert not report['physical_validated']


@pytest.mark.parametrize('coordinates', [[], [0., 1.], [0., .5, .5], [1., .5, 0.],
    [0., float('nan'), 1.], [0., float('inf'), 1.], [.01, .5, 1.], [0., .5, .99], [0., .5j, 1.]])
def test_invalid_axes_rejected(coordinates):
    with pytest.raises(ValueError):
        StructuredGrid(((0., 1.),) * 3, 3, 1, 1, axes=(coordinates, [0.], [0.]))


@pytest.mark.parametrize('case', ['tensor', 'flat', 'nodes', 'shape'])
def test_inconsistent_geometry_rejected_before_native_construction(case):
    mesh = mesh_for(0, full=True)
    if case == 'tensor':
        mesh.X[1, 1, 1] += 1e-9
    elif case == 'flat':
        mesh._flat_x[0] += 1e-9
    elif case == 'nodes':
        mesh.node_coords[0, 0] += 1e-9
    else:
        mesh.X = mesh.X[:-1]
    with pytest.raises(ValueError):
        Simulator(mesh)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('coordinates', [[0., .1, .5, 1.], [0., .2, .24, .26, .3, .8, 1.]])
def test_nonuniform_hidden_film_matches_both_executed_sentaurus_references(axis, coordinates):
    mesh = mesh_for(axis, coordinates=coordinates)
    length = 1e-6
    bounds = [[0., length] for _ in range(3)]
    bounds[axis] = [.23 * length, .27 * length]
    regions = [(Box(0., length, 0., length, 0., length), 0), (Box(*(v for b in bounds for v in b)), 1)]
    ids = np.zeros(mesh.npts(), dtype=int)
    ids[regions[1][0].contains(*mesh.flat_coords())] = 1
    values = {0: 3.9 * EPS0, 1: 15 * EPS0}
    eps = np.array([values[mid] for mid in ids])
    edges = compute_edge_permittivity(mesh, eps, ids, regions, material_permittivity=values)
    sim = simulator(mesh, axis)
    sim._sim.set_permittivity(eps)
    sim._sim.set_edge_permittivity(*(edges[a + s] for a in 'xyz' for s in ['_plus', '_minus']))
    state = sim.run(max_iter=80, tol=1e-12, physical_step=False)
    assert state['converged']
    x = mesh.axis_coordinates()[axis]
    resistance = np.r_[0., np.cumsum(np.diff(x) / edges['xyz'[axis] + '_plus'][:-1])]
    np.testing.assert_allclose(state['phi'], .2 * resistance / resistance[-1], rtol=1e-9, atol=2e-12)
    charge = edges['xyz'[axis] + '_plus'][:-1] * np.diff(state['phi']) / np.diff(x) * length**2
    np.testing.assert_allclose(charge, charge[0], rtol=1e-9)
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / 'tests/data/sentaurus_box_cut_edges.json').read_text())
    for ref in fixture['commercial']:
        assert abs(charge[0] / ref['charges_C'][1] - 1) <= fixture['relative_budget']
