"""Independent series-capacitor and geometry checks for box cut edges."""
import json
from pathlib import Path
import numpy as np
import pytest

from tcad.geometry.device_builder import Box, Device, Material, Region
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.generator import structured_mesh_from_device
from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from tcad.postprocess import audit_transient_dielectric_energy

EPS0 = 8.854187817e-12


def layer_box(axis, lo, hi):
    bounds = [[0., 1e-6] for _ in range(3)]
    bounds[axis] = [lo * 1e-6, hi * 1e-6]
    return Box(*(x for b in bounds for x in b))


def layered(axis=0, nodes=3, overlap=False):
    dev = Device().add_region(Region('base', layer_box(axis, 0, 1),
                                    Material('base', epsilon_r=3.9)))
    dev.add_region(Region('hidden', layer_box(axis, .23, .27),
                         Material('film', epsilon_r=15)))
    if overlap:
        dev.add_region(Region('overlap', layer_box(axis, .25, .31),
                             Material('overlap', epsilon_r=25)))
    shape = [1, 1, 1]
    shape[axis] = nodes
    return structured_mesh_from_device(dev, nx=shape[0], ny=shape[1], nz=shape[2])


def edge_coefficients(mesh, **kwargs):
    return compute_edge_permittivity(mesh, mesh.fields['epsilon'],
        mesh.fields['material_id'], shapes=mesh._material_shapes,
        material_permittivity=mesh._material_permittivity, **kwargs)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('overlap', [False, True])
@pytest.mark.parametrize('samples', [2, 5, 101])
def test_hidden_layers_and_overlap_use_every_interval(axis, overlap, samples):
    mesh = layered(axis, overlap=overlap)
    assert np.all(mesh.fields['material_id'] == 0)
    edges = edge_coefficients(mesh, n_samples=samples)
    resistance = (.42 / 3.9 + .02 / 15 + .06 / 25 if overlap
                  else .46 / 3.9 + .04 / 15)
    expected = EPS0 * .5 / resistance
    plus, minus = edges['xyz'[axis] + '_plus'], edges['xyz'[axis] + '_minus']
    np.testing.assert_allclose(plus[:-1], [expected, EPS0 * 3.9], rtol=5e-15)
    np.testing.assert_array_equal(plus[:-1], minus[1:])
    assert plus[-1] == minus[0] == 0


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('boundary', [0., .137, 1.])
def test_interfaces_at_endpoints_and_arbitrary_positions(axis, boundary):
    mesh = layered(axis, nodes=2)
    # Two covering boxes; later one owns the interface, with zero line measure.
    mesh._material_shapes = [(layer_box(axis, 0, 1), 0),
                             (layer_box(axis, boundary, 1), 1)] if boundary < 1 else [
                                 (layer_box(axis, 0, 1), 0)]
    mesh._material_permittivity = {0: 3.9 * EPS0, 1: 15 * EPS0}
    ids = np.array([1 if boundary == 0 else 0, 1 if boundary < 1 else 0])
    mesh.fields['material_id'] = ids
    mesh.fields['epsilon'] = np.where(ids, 15 * EPS0, 3.9 * EPS0)
    edges = edge_coefficients(mesh)
    expected = EPS0 / (boundary / 3.9 + (1 - boundary) / 15) if boundary < 1 else EPS0 * 3.9
    assert edges['xyz'[axis] + '_plus'][0] == pytest.approx(expected, rel=2e-15)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('path', ['gummel', 'hybrid', 'newton'])
@pytest.mark.parametrize('overlap', [False, True])
def test_native_potential_and_flux_match_exact_series_capacitor(axis, path, overlap):
    mesh = layered(axis, overlap=overlap)
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.enable_cut_cell()
    sim._apply_cut_cell()
    low = sim._sim
    low.set_mobility(np.zeros(3), np.zeros(3))
    low.set_doping(np.zeros(3))
    low.set_effective_dos(np.ones(3), np.ones(3))
    low.set_bandgap(np.full(3, 6.))
    low.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    low.set_initial_guess(np.zeros(3), np.zeros(3), np.zeros(3))
    low.set_dirichlet_potential({0: 0., 2: .2})
    low.set_use_newton(path != 'gummel')
    low.set_newton_primary(path == 'newton')
    low.set_gummel_max_iter(80)
    low.set_tolerance(1e-12)
    state = low.solve()
    assert state['converged']
    resistance = (np.array([.42 / 3.9 + .02 / 15 + .06 / 25, .5 / 3.9]) if overlap
                  else np.array([.46 / 3.9 + .04 / 15, .5 / 3.9]))
    expected = .2 * np.r_[0., np.cumsum(resistance)] / resistance.sum()
    np.testing.assert_allclose(state['phi'], expected, rtol=1e-9, atol=2e-12)
    field_flux = -EPS0 / resistance * np.diff(state['phi']) / 1e-6
    np.testing.assert_allclose(field_flux, field_flux[0], rtol=1e-9)
    # Disabling after a solve must restore the default node-only operator.
    sim.enable_cut_cell(False)
    uncorrected = low.solve()
    assert uncorrected['converged']
    np.testing.assert_allclose(uncorrected['phi'], [0., .1, .2], atol=2e-12)
    assert abs(state['phi'][1] - uncorrected['phi'][1]) > .002


@pytest.mark.parametrize('axis', range(3))
def test_transient_charge_and_energy_use_hidden_layer_coefficient(axis):
    mesh = layered(axis)
    sim = Simulator(mesh)
    sim.set_material_from_mesh()
    sim.enable_cut_cell()
    sim._apply_cut_cell()
    low = sim._sim
    low.set_mobility(np.zeros(3), np.zeros(3))
    low.set_doping(np.zeros(3))
    low.set_effective_dos(np.ones(3), np.ones(3))
    low.set_bandgap(np.full(3, 6.))
    low.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    low.set_initial_guess(np.zeros(3), np.zeros(3), np.zeros(3))
    low.set_dirichlet_potential({0: 0., 2: 0.})
    low.set_transient_dt(1e-10)
    low.set_transient_t_final(2e-10)
    low.set_transient_voltage_waveforms([0., 1e-10, 2e-10], {2: [0., .2, 0.]})
    history = low.solve_transient()
    cap = EPS0 * 1e-6 / (.96 / 3.9 + .04 / 15)
    assert len(history) == 3
    for state in history:
        assert state['valid'] and state['dielectric_energy_available']
        voltage = np.interp(state['time_s'], [0., 1e-10, 2e-10], [0., .2, 0.])
        np.testing.assert_allclose(state['electrode_charges_C'], [-cap * voltage, cap * voltage], rtol=1e-9, atol=1e-32)
        assert state['dielectric_energy_J'] == pytest.approx(.5 * cap * voltage**2, rel=1e-9, abs=1e-34)
    report = audit_transient_dielectric_energy(history)
    assert report['valid'] and report['energy_balance_validated']
    assert not report['physical_validated']
    reference = json.loads((Path(__file__).parent / 'data/sentaurus_box_cut_edges.json').read_text())
    for commercial in reference['commercial']:
        np.testing.assert_allclose(history[1]['electrode_charges_C'], commercial['charges_C'],
                                   rtol=reference['relative_budget'], atol=0.)
        np.testing.assert_allclose(history[1]['phi'], commercial['sampled_phi_V'],
                                   rtol=0., atol=.2 * reference['relative_budget'])


@pytest.mark.parametrize('axis', range(3))
def test_homogeneous_edges_are_reciprocal_without_geometry(axis):
    mesh = layered(axis)
    edges = compute_edge_permittivity(mesh, mesh.fields['epsilon'], mesh.fields['material_id'])
    np.testing.assert_array_equal(edges['xyz'[axis] + '_plus'][:-1], edges['xyz'[axis] + '_minus'][1:])


def test_missing_hidden_material_cannot_silently_disappear():
    mesh = layered()
    with pytest.raises(ValueError, match='unsampled material'):
        compute_edge_permittivity(mesh, mesh.fields['epsilon'], mesh.fields['material_id'],
                                 shapes=mesh._material_shapes)


def test_box_values_can_be_inferred_when_all_regions_have_nodes():
    mesh = layered(nodes=101)
    expected = edge_coefficients(mesh)
    actual = compute_edge_permittivity(mesh, mesh.fields['epsilon'], mesh.fields['material_id'], shapes=mesh._material_shapes)
    for key in expected:
        np.testing.assert_array_equal(actual[key], expected[key])


@pytest.mark.parametrize('bad', [0., -1., float('inf'), float('nan'), True, 1j])
def test_invalid_material_values_are_rejected(bad):
    mesh = layered()
    mesh._material_permittivity[1] = bad
    with pytest.raises(ValueError, match='permittivity'):
        edge_coefficients(mesh)


@pytest.mark.parametrize('case', ['missing', 'stale', 'id', 'gap', 'span', 'fractional_id'])
def test_inconsistent_geometry_is_rejected(case):
    mesh = layered()
    if case == 'missing':
        del mesh._material_permittivity[1]
    elif case == 'stale':
        mesh.fields['epsilon'][0] *= 2
    elif case == 'id':
        mesh.fields['material_id'][0] = 1
        mesh.fields['epsilon'][0] = 15 * EPS0
    elif case == 'gap':
        mesh._material_shapes = [(layer_box(0, 0, .1), 0), (layer_box(0, .2, 1), 0)]
    elif case == 'span':
        mesh._material_shapes[1] = (layer_box(0, .23, .23), 1)
    else:
        mesh.fields['material_id'] = np.array([0., .5, 0.])
    with pytest.raises(ValueError):
        edge_coefficients(mesh)


@pytest.mark.parametrize('samples', [0, 1, 2.5, True])
def test_invalid_sample_counts_are_rejected(samples):
    with pytest.raises(ValueError, match='n_samples'):
        edge_coefficients(layered(), n_samples=samples)


def test_all_3d_edges_use_correct_coordinate_line_and_painter_order():
    dev = Device().add_region(Region('base', Box(0, 1, 0, 1, 0, 1), Material('base', epsilon_r=4)))
    dev.add_region(Region('inclusion', Box(.2, .3, .1, .9, .1, .9), Material('inc', epsilon_r=20)))
    mesh = structured_mesh_from_device(dev, nx=3, ny=3, nz=3)
    edges = edge_coefficients(mesh)
    for k in range(3):
        for j in range(3):
            expected = EPS0 * .5 / (.4 / 4 + .1 / 20) if j == k == 1 else EPS0 * 4
            idx = mesh.index(0, j, k)
            assert edges['x_plus'][idx] == pytest.approx(expected, rel=1e-14)
            assert edges['x_minus'][idx + 1] == edges['x_plus'][idx]
    for axis in ['y', 'z']:
        assert np.all((edges[axis + '_plus'] == 0) | (edges[axis + '_plus'] == EPS0 * 4))


def test_no_geometry_harmonic_mean_does_not_overflow_products():
    mesh = StructuredGrid(((0, 1), (0, 1), (0, 1)), 2, 1, 1)
    edges = compute_edge_permittivity(mesh, [1e300, 1e300], [0, 0])
    assert edges['x_plus'][0] == 1e300
    assert edges['x_minus'][1] == 1e300


@pytest.mark.parametrize('method', ['feature', 'solution'])
def test_refined_mesh_keeps_unsampled_material_constants(method):
    from tcad.mesh.adaptive_refiner import AdaptiveRefiner
    dev = Device().add_region(Region('base', layer_box(0, 0, 1), Material('base', epsilon_r=3.9)))
    dev.add_region(Region('hidden', layer_box(0, .23, .27), Material('film', epsilon_r=15)))
    refiner = AdaptiveRefiner(dev, base_resolution=(.5e-6, .5e-6, .5e-6))
    mesh = refiner.generate_feature_refined_mesh(level=0)
    if method == 'solution':
        markers = {a: np.zeros((2, 2, 2), dtype=bool) for a in 'xyz'}
        markers['x'][1, :, :] = True
        mesh = refiner._refine_from_markers(mesh, markers, level=1)
    assert np.all(mesh.fields['material_id'] == 0)
    edges = edge_coefficients(mesh)
    expected = EPS0 * .5 / (.46 / 3.9 + .04 / 15)
    assert edges['x_plus'][mesh.index(0, 1, 1)] == pytest.approx(expected, rel=1e-14)


@pytest.mark.parametrize('count', [3, 5, 9])
def test_series_capacitance_is_independent_of_node_sampling(count):
    mesh = layered(nodes=count)
    edges = edge_coefficients(mesh)['x_plus'][:-1]
    inverse_cap = np.sum(np.diff(mesh.X[:, 0, 0]) / edges) / 1e-12
    expected = EPS0 * 1e-6 / (.96 / 3.9 + .04 / 15)
    assert 1 / inverse_cap == pytest.approx(expected, rel=3e-15)
