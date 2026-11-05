"""Analytic chord controls, painter overlap and native line-operator checks."""
import math

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.geometry.shapes import Box, Sphere, Cylinder
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.structured_grid import StructuredGrid


def line(axis, scale=1., nodes=3):
    shape = [1, 1, 1]
    shape[axis] = nodes
    return StructuredGrid(tuple((0., scale) for _ in range(3)), *shape)


def evaluate(grid, regions, values, **kwargs):
    x, y, z = grid.flat_coords()
    ids = np.full(grid.npts(), -1, dtype=int)
    for shape, mid in regions:
        ids[shape.contains(x, y, z)] = mid
    eps = np.array([values[mid] for mid in ids])
    edges = compute_edge_permittivity(grid, eps, ids, regions,
                                      material_permittivity=values, **kwargs)
    return edges, eps, ids


def base(scale):
    return Box(0, scale, 0, scale, 0, scale)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('scale', [1e-90, 1., 1e90])
@pytest.mark.parametrize('offset', [(0., 0.), (.03, 0.), (.03, .04)])
def test_sphere_hidden_chord_is_independent_of_sample_count(axis, scale, offset):
    grid = line(axis, scale)
    center = np.zeros(3)
    center[axis] = .25
    center[[a for a in range(3) if a != axis]] = offset
    sphere = Sphere(*(center * scale), .07 * scale)
    chord = 2 * math.sqrt(.07**2 - sum(d**2 for d in offset))
    expected = .5 / ((.5 - chord) / 4 + chord / 20)
    for samples in [2, 5, 97]:
        edges, _, ids = evaluate(grid, [(base(scale), 0), (sphere, 1)], {0: 4., 1: 20.}, n_samples=samples)
        assert np.all(ids == 0)
        plus, minus = edges['xyz'[axis] + '_plus'], edges['xyz'[axis] + '_minus']
        np.testing.assert_allclose(plus[:-1], [expected, 4.], rtol=5e-15)
        np.testing.assert_array_equal(plus[:-1], minus[1:])


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('cylinder_axis', range(3))
@pytest.mark.parametrize('scale', [1e-90, 1., 1e90])
def test_cylinder_axial_caps_and_radial_chords(axis, cylinder_axis, scale):
    grid = line(axis, scale)
    transverse = [a for a in range(3) if a != cylinder_axis]
    center = np.zeros(3)
    if axis == cylinder_axis:
        center[transverse] = [.03, .04]
        lo, hi = .2, .3
        chord = hi - lo
    else:
        center[axis] = .25
        center[next(a for a in transverse if a != axis)] = .03
        lo, hi = -.1, .1
        chord = 2 * math.sqrt(.07**2 - .03**2)
    cylinder = Cylinder('xyz'[cylinder_axis], *(center[transverse] * scale), lo * scale, hi * scale, .07 * scale)
    edges, _, ids = evaluate(grid, [(base(scale), 0), (cylinder, 1)], {0: 4., 1: 20.})
    assert np.all(ids == 0)
    expected = .5 / ((.5 - chord) / 4 + chord / 20)
    np.testing.assert_allclose(edges['xyz'[axis] + '_plus'][:-1], [expected, 4.], rtol=5e-15)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('kind', ['sphere', 'cylinder'])
@pytest.mark.parametrize('location', ['tangent', 'miss', 'endpoint'])
def test_tangent_missing_and_material_endpoint(axis, kind, location):
    grid = line(axis)
    transverse = [a for a in range(3) if a != axis]
    center = np.zeros(3)
    center[axis] = .25
    center[transverse[0]] = .125 if location == 'tangent' else .126
    radius = .125
    if location == 'endpoint':
        center[axis] = .125
        center[transverse[0]] = 0.
    if kind == 'sphere':
        shape = Sphere(*center, radius)
    else:
        axial = transverse[1]
        cyl_transverse = [a for a in range(3) if a != axial]
        shape = Cylinder('xyz'[axial], *center[cyl_transverse], -.1, .1, radius)
    edges, _, _ = evaluate(grid, [(base(1), 0), (shape, 1)], {0: 4., 1: 20.})
    expected = .5 / (.25 / 4 + .25 / 20) if location == 'endpoint' else 4.
    assert edges['xyz'[axis] + '_plus'][0] == pytest.approx(expected, rel=5e-15)


def test_mixed_primitives_integrate_all_overlaps_in_painter_order():
    grid = line(0, nodes=2)
    regions = [(base(1), 0), (Sphere(.35, 0, 0, .15), 1),
               (Cylinder('z', .45, 0, -.1, .1, .1), 2),
               (Box(.4, .45, 0, 1, 0, 1), 3)]
    values = {0: 4., 1: 12., 2: 20., 3: 8.}
    expected = 1 / (.65 / 4 + .15 / 12 + .15 / 20 + .05 / 8)
    edges, _, _ = evaluate(grid, regions, values)
    assert edges['x_plus'][0] == pytest.approx(expected, rel=3e-15)
    regions[1], regions[2] = regions[2], regions[1]
    expected = 1 / (.65 / 4 + .25 / 12 + .05 / 20 + .05 / 8)
    edges, _, _ = evaluate(grid, regions, values)
    assert edges['x_plus'][0] == pytest.approx(expected, rel=3e-15)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('kind', ['sphere', 'cylinder'])
@pytest.mark.parametrize('path', ['gummel', 'newton'])
def test_native_line_potential_and_displacement_match_series_solution(axis, kind, path):
    scale = 1e-6
    grid = line(axis, scale)
    center = np.zeros(3)
    center[axis] = .25 * scale
    if kind == 'sphere':
        shape = Sphere(*center, .05 * scale)
    else:
        axial = next(a for a in range(3) if a != axis)
        transverse = [a for a in range(3) if a != axial]
        shape = Cylinder('xyz'[axial], *center[transverse], -.1 * scale, .1 * scale, .05 * scale)
    eps0 = 8.854187817e-12
    edges, eps, _ = evaluate(grid, [(base(scale), 0), (shape, 1)], {0: 4 * eps0, 1: 20 * eps0})
    sim = PyDeviceSimulator(grid.nx, grid.ny, grid.nz, grid.dx, grid.dy, grid.dz)
    sim.set_permittivity(eps)
    sim.set_edge_permittivity(*(edges[a + s] for a in 'xyz' for s in ['_plus', '_minus']))
    sim.set_mobility(np.zeros(3), np.zeros(3))
    sim.set_doping(np.zeros(3))
    sim.set_effective_dos(np.ones(3), np.ones(3))
    sim.set_bandgap(np.full(3, 6.))
    sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    sim.set_initial_guess(np.zeros(3), np.zeros(3), np.zeros(3))
    sim.set_dirichlet_potential({0: 0., 2: .2})
    sim.set_use_newton(path == 'newton')
    sim.set_newton_primary(path == 'newton')
    sim.set_tolerance(1e-12)
    state = sim.solve()
    assert state['converged']
    resistance = np.array([.4 / 4 + .1 / 20, .5 / 4])
    expected = .2 * np.r_[0., np.cumsum(resistance)] / resistance.sum()
    np.testing.assert_allclose(state['phi'], expected, rtol=1e-9, atol=2e-12)
    flux = -edges['xyz'[axis] + '_plus'][:-1] * np.diff(state['phi']) / (.5 * scale)
    np.testing.assert_allclose(flux, flux[0], rtol=1e-9)


@pytest.mark.parametrize('shape', [Sphere(.25, 0, 0, 0), Sphere(.25, 0, 0, -.1),
    Sphere(float('inf'), 0, 0, .1), Cylinder('bad', .25, 0, -.1, .1, .05),
    Cylinder('z', .25, 0, .1, -.1, .05), Cylinder('z', .25, 0, -.1, .1, float('nan'))])
def test_invalid_curved_geometry_is_rejected(shape):
    grid = line(0)
    with pytest.raises(ValueError):
        compute_edge_permittivity(grid, np.full(3, 4.), np.zeros(3),
            [(base(1), 0), (shape, 1)], material_permittivity={0: 4., 1: 20.})


def test_inclusion_crossing_no_grid_edge_remains_unresolved():
    grid = StructuredGrid(((0, 1), (0, 1), (0, 1)), 2, 2, 2)
    edges, _, _ = evaluate(grid, [(base(1), 0), (Sphere(.5, .5, .5, .1), 1)], {0: 4., 1: 20.})
    for values in edges.values():
        assert np.all((values == 0) | (values == 4))
