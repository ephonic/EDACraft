"""Disconnected polygon chords and tapered primitive dielectric controls."""
import math

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator
from tcad.geometry.shapes import Box, Cone, Cylinder, Prism
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.edge_intersections import prepare_line_intervals
from tcad.mesh.structured_grid import StructuredGrid


U = np.array([[.15, -.1], [.45, -.1], [.45, .1], [.35, .1],
              [.35, -.05], [.25, -.05], [.25, .1], [.15, .1]])


def evaluate(grid, regions, values, samples=5):
    xyz = grid.flat_coords()
    ids = np.full(grid.npts(), -1, dtype=int)
    for shape, mid in regions:
        ids[shape.contains(*xyz)] = mid
    eps = np.array([values[mid] for mid in ids])
    edges = compute_edge_permittivity(grid, eps, ids, regions, n_samples=samples,
                                      material_permittivity=values)
    return edges, eps


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('scale', [1e-90, 1., 1e90])
@pytest.mark.parametrize('reverse,close', [(False, False), (True, False), (False, True)])
def test_concave_prism_hidden_disconnected_chords(axis, scale, reverse, close):
    vertices = U[:, ::-1] if axis == 1 else U.copy()
    if reverse:
        vertices = vertices[::-1]
    if close:
        vertices = np.vstack([vertices, vertices[0]])
    prism = Prism(vertices * scale, -.1 * scale, .1 * scale)
    sizes = [1, 1, 1]
    sizes[axis] = 2
    grid = StructuredGrid(((0, scale),) * 3, *sizes)
    background = Box(0, scale, 0, scale, 0, scale)
    for samples in [2, 5, 97]:
        edges, _ = evaluate(grid, [(background, 0), (prism, 1)], {0: 4., 1: 20.}, samples)
        expected = 1 / (.8 / 4 + .2 / 20)
        assert edges['xyz'[axis] + '_plus'][0] == pytest.approx(expected, rel=5e-15)
        assert edges['xyz'[axis] + '_minus'][1] == edges['xyz'[axis] + '_plus'][0]


@pytest.mark.parametrize('z', [-.2, -.1, 0., .1, .2])
@pytest.mark.parametrize('y,intervals', [(-.2, []), (-.075, [(.15, .45)]),
                                       (0., [(.15, .25), (.35, .45)]), (.2, [])])
def test_concave_prism_caps_notch_and_misses(z, y, intervals):
    found = prepare_line_intervals(Prism(U, -.1, .1))([0., y, z], 0)
    expected = intervals if -.1 <= z <= .1 else []
    np.testing.assert_allclose(np.asarray(found).reshape(-1, 2), np.asarray(expected).reshape(-1, 2), atol=1e-16)


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('point', [(0., 0.), (.15, 0.), (.2, 0.), (.3, 0.), (.4, 0.), (.45, 0.), (.3, -.1)])
def test_prism_axial_lines_keep_geometry_boundary_membership(reverse, point):
    prism = Prism(U[::-1] if reverse else U, -.1, .1)
    inside = prism.contains(np.array([point[0]]), np.array([point[1]]), np.array([0.]))[0]
    found = prepare_line_intervals(prism)([*point, 0.], 2)
    assert found == ([(-.1, .1)] if inside else [])


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('scale', [1e-90, 1., 1e90])
@pytest.mark.parametrize('offset', [0., .03, .05, .051])
def test_cone_hidden_transverse_chord_and_tangency(axis, scale, offset):
    center = [.0, .0]
    center[axis] = .25
    center[1 - axis] = offset
    cone = Cone('z', *(np.array(center) * scale), -.1 * scale, .1 * scale, .025 * scale, .075 * scale)
    sizes = [1, 1, 1]
    sizes[axis] = 2
    grid = StructuredGrid(((0, scale),) * 3, *sizes)
    edges, _ = evaluate(grid, [(Box(0, scale, 0, scale, 0, scale), 0), (cone, 1)], {0: 4., 1: 20.})
    chord = 2 * math.sqrt(max(0., .05**2 - offset**2))
    assert edges['xyz'[axis] + '_plus'][0] == pytest.approx(1 / ((1 - chord) / 4 + chord / 20), rel=5e-15)


@pytest.mark.parametrize('radii', [(0., .1), (.025, .075), (.1, 0.), (.075, .025), (.05, .05)])
@pytest.mark.parametrize('distance', [0., .025, .05, .075, .1, .11])
def test_cone_axial_taper_and_cylinder_limit(radii, distance):
    cone = Cone('z', 0., 0., .2, .4, *radii)
    intervals = prepare_line_intervals(cone)([distance, 0., 0.], 2)
    actual = sum(b - a for a, b in intervals)
    low, high = sorted(radii)
    fraction = (1. if distance <= low else 0. if distance >= high
                else (high - distance) / (high - low))
    assert actual == pytest.approx(.2 * fraction, rel=1e-14, abs=1e-16)
    if radii[0] == radii[1]:
        assert intervals == prepare_line_intervals(Cylinder('z', 0., 0., .2, .4, radii[0]))([distance, 0., 0.], 2)


def test_concave_prism_mixed_with_cone_and_box_obeys_painter_order():
    grid = StructuredGrid(((0, 1),) * 3, 2, 1, 1)
    regions = [(Box(0, 1, 0, 1, 0, 1), 0), (Prism(U, -.1, .1), 1),
               (Cone('z', .25, 0., -.1, .1, .025, .075), 2)]
    values = {0: 4., 1: 12., 2: 20.}
    edges, _ = evaluate(grid, regions, values)
    assert edges['x_plus'][0] == pytest.approx(1 / (.75 / 4 + .15 / 12 + .1 / 20), rel=5e-15)
    regions[1], regions[2] = regions[2], regions[1]
    edges, _ = evaluate(grid, regions, values)
    assert edges['x_plus'][0] == pytest.approx(1 / (.75 / 4 + .2 / 12 + .05 / 20), rel=5e-15)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('kind', ['cone', 'prism'])
@pytest.mark.parametrize('newton', [False, True])
def test_native_potential_and_displacement_match_independent_series_solution(axis, kind, newton):
    length = 1e-6
    sizes = [1, 1, 1]
    sizes[axis] = 3
    grid = StructuredGrid(((0, length),) * 3, *sizes)
    if axis == 2:
        shape = (Cone('z', 0., 0., .2 * length, .3 * length, 0., .1 * length)
                 if kind == 'cone' else Prism(np.array([[-.1, -.1], [.1, -.1], [.1, .1], [-.1, .1]]) * length, .2 * length, .3 * length))
        chord = .1
    elif kind == 'cone':
        center = np.zeros(2)
        center[axis] = .25 * length
        shape = Cone('z', *center, -.1 * length, .1 * length, .025 * length, .075 * length)
        chord = .1
    else:
        shape = Prism((U[:, ::-1] if axis == 1 else U) * length, -.1 * length, .1 * length)
        chord = .2
    eps0 = 8.854187817e-12
    edges, eps = evaluate(grid, [(Box(0, length, 0, length, 0, length), 0), (shape, 1)], {0: 4 * eps0, 1: 20 * eps0})
    sim = PyDeviceSimulator(*sizes, grid.dx, grid.dy, grid.dz)
    sim.set_permittivity(eps)
    sim.set_edge_permittivity(*(edges[a + s] for a in 'xyz' for s in ['_plus', '_minus']))
    sim.set_mobility(np.zeros(3), np.zeros(3))
    sim.set_doping(np.zeros(3))
    sim.set_effective_dos(np.ones(3), np.ones(3))
    sim.set_bandgap(np.full(3, 6.))
    sim.set_recombination(np.full(3, 1e100), np.full(3, 1e100))
    sim.set_initial_guess(np.zeros(3), np.zeros(3), np.zeros(3))
    sim.set_dirichlet_potential({0: 0., 2: .2})
    sim.set_use_newton(newton)
    sim.set_newton_primary(newton)
    sim.set_tolerance(1e-12)
    state = sim.solve()
    assert state['converged']
    resistance = np.array([(.5 - chord) / 4 + chord / 20, .5 / 4])
    expected = .2 * np.r_[0., np.cumsum(resistance)] / resistance.sum()
    np.testing.assert_allclose(state['phi'], expected, rtol=1e-9, atol=2e-12)
    flux = -edges['xyz'[axis] + '_plus'][:-1] * np.diff(state['phi']) / (.5 * length)
    np.testing.assert_allclose(flux, flux[0], rtol=1e-9)


@pytest.mark.parametrize('vertices', [
    [[0, 0], [1, 1], [0, 1], [1, 0]],  # self crossing
    [[0, 0], [1, 0], [.5, 0], [1, 1], [0, 1]],  # adjacent reversal
    [[0, 0], [1, 0], [1, 1], [.5, 0], [0, 1]],  # nonadjacent touch
    [[0, 0], [1, 0], [1, 1], [1, 0], [0, 1]],  # repeated vertex
    [[0, 0], [1, 1], [2, 2]],  # zero area
    [[0, 0], [1, 0], [float('nan'), 1]],
])
def test_non_simple_or_degenerate_prism_rejected(vertices):
    with pytest.raises(ValueError):
        prepare_line_intervals(Prism(vertices, 0., 1.))


@pytest.mark.parametrize('rmin,rmax', [(-.1, .1), (.1, -.1), (0., 0.), (float('nan'), .1), (.1, float('inf')), (True, .1)])
def test_invalid_cone_radii_rejected(rmin, rmax):
    with pytest.raises(ValueError):
        prepare_line_intervals(Cone('z', 0., 0., 0., 1., rmin, rmax))


def test_unsupported_cone_axis_and_stale_prism_path_are_rejected():
    with pytest.raises(ValueError, match='z axis'):
        prepare_line_intervals(Cone('x', 0., 0., 0., 1., 0., .1))
    prism = Prism(U, 0., 1.)
    prism.vertices = U + 1.
    with pytest.raises(ValueError, match='cached'):
        prepare_line_intervals(prism)
