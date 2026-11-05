"""Native port fluxes against independent FV divergence and resistor networks."""
from itertools import product
import json
from math import fsum
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator, native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.postprocess import terminal_currents_native
from tcad.postprocess.current import contact_current_1d, contact_current_2d
from tcad.validation.conservation import ConservationTest

SHAPES = [(5, 1, 1), (1, 5, 1), (1, 1, 5),
          (5, 4, 1), (5, 1, 4), (1, 5, 4), (5, 4, 3)]


def problem(shape, graded, layout=0):
    spans = np.array([2., 3., 4.]) * 1e-6
    axes = [np.linspace(0., 1., count) ** (1.4 if graded else 1.) * span
            for count, span in zip(shape, spans)]
    mesh = StructuredGrid(tuple((0., span) for span in spans), *shape, axes=axes)
    coordinates = np.array([mesh.ijk(i) for i in range(mesh.npts())])
    primary = next(a for a, n in enumerate(shape) if n > 1)
    owners = np.zeros(mesh.npts(), dtype=int)
    owners[coordinates[:, primary] == 0] = 1
    owners[coordinates[:, primary] == shape[primary] - 1] = 2
    if layout == 1:
        owners[coordinates[:, primary] == 1] = 1  # Finite-thickness reservoir.
        center = tuple(n // 2 for n in shape)
        owners[mesh.index(*center)] = 3
    elif layout == 2:
        owners[:] = 0
        owners[0] = owners[1] = 1
        owners[-1] = 2
        owners[mesh.npts() // 2] = 3
    for i in range(1, owners.max() + 1):
        mesh.fields['contact_c' + str(i)] = owners == i
    return SimpleNamespace(mesh=mesh, VT=.02585), axes, owners


def reference_widths(sim, axes):
    # Reflected exterior half-faces give full native endpoint cells.
    spans = [(sim.mesh.xmin, sim.mesh.xmax), (sim.mesh.ymin, sim.mesh.ymax),
             (sim.mesh.zmin, sim.mesh.zmax)]
    widths = []
    for values, span in zip(axes, spans):
        faces = (np.array(span) if len(values) == 1 else
                 np.r_[values[0] - (values[1] - values[0]) / 2,
                       (values[:-1] + values[1:]) / 2,
                       values[-1] + (values[-1] - values[-2]) / 2])
        widths.append(np.diff(faces))
    return widths


def reference_edges(sim, axes):
    m = sim.mesh
    widths = reference_widths(sim, axes)
    for k, j, i in product(range(m.nz), range(m.ny), range(m.nx)):
        xyz = [i, j, k]
        left = m.index(*xyz)
        for a, values in enumerate(axes):
            if xyz[a] + 1 == len(values):
                continue
            other = xyz.copy()
            other[a] += 1
            area = np.prod([widths[b][xyz[b]] for b in range(3) if b != a])
            yield a, left, m.index(*other), area, values[xyz[a] + 1] - values[xyz[a]]


def zero_fields(sim):
    return {carrier + '_' + axis: np.zeros(sim.mesh.npts())
            for carrier in ['Jn', 'Jp', 'Jleak'] for axis in 'xyz'}


@pytest.mark.parametrize('shape', SHAPES)
@pytest.mark.parametrize('graded', [False, True])
@pytest.mark.parametrize('layout', [0, 1, 2])
def test_all_ports_equal_independent_node_divergence(shape, graded, layout):
    sim, axes, owners = problem(shape, graded, layout)
    rng = np.random.default_rng(184)
    fields = {key: rng.normal(size=sim.mesh.npts()) for key in zero_fields(sim)}
    divergence = np.zeros(sim.mesh.npts())
    for axis, left, right, area, _ in reference_edges(sim, axes):
        if owners[left] and owners[right]:
            continue  # Reservoir-to-reservoir faces are outside the free volume.
        current = area * fsum(fields[c + '_' + 'xyz'[axis]][left]
                              for c in ['Jn', 'Jp', 'Jleak'])
        divergence[left] += current
        divergence[right] -= current
    actual = terminal_currents_native(sim, fields)
    expected = {'c' + str(i): float(sum(divergence[owners == i]))
                for i in range(1, owners.max() + 1)}
    scale = max(abs(divergence))
    for name, value in expected.items():
        assert actual[name] == pytest.approx(value, rel=1e-13, abs=scale*1e-14)
    assert abs(fsum(actual.values()) + sum(divergence[owners == 0])) < scale*1e-13
    # A returned current dictionary must not silently turn imbalance into KCL.
    check = ConservationTest(check_energy=False, tolerance=1e-12, current_atol_A=0.)
    if abs(fsum(actual.values())) > 1e-10 * max(abs(v) for v in actual.values()):
        assert not check.run(lambda: dict(converged=True, terminal_currents_A=actual)).passed


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('graded', [False, True])
def test_constant_native_flux_has_exact_area_sign_and_1d_limit(axis, graded):
    shape = [1, 1, 1]
    shape[axis] = 5
    sim, axes, _ = problem(tuple(shape), graded)
    fields = zero_fields(sim)
    for c, value in [('Jn', 1.25), ('Jp', -.5), ('Jleak', .125)]:
        fields[c + '_' + 'xyz'[axis]][:] = value
    expected = .875 * np.prod([sum(w) for a, w in enumerate(reference_widths(sim, axes)) if a != axis])
    assert terminal_currents_native(sim, fields) == pytest.approx({'c1': expected, 'c2': -expected}, rel=1e-14)
    if axis == 0:
        assert contact_current_1d(sim, fields, 'c1') * expected/.875 == pytest.approx(expected)


def test_native_endpoint_measure_is_explicitly_distinct_from_half_face_quadrature():
    sim, axes, _ = problem((5, 1, 4), True)
    fields = zero_fields(sim)
    fields['Jn_x'][:] = 2.
    native = terminal_currents_native(sim, fields)['c1']
    physical = contact_current_2d(sim, fields, 'c1')
    z = axes[2]
    ratio = (z[-1] - z[0] + (z[1] - z[0] + z[-1] - z[-2]) / 2) / (z[-1] - z[0])
    assert native == pytest.approx(physical * ratio, rel=1e-14)
    assert native != pytest.approx(physical, rel=1e-3, abs=0.)


def test_finite_thickness_contact_includes_transverse_lateral_faces():
    sim, axes, _ = problem((5, 4, 3), True, 2)
    fields = zero_fields(sim)
    # c1 is nodes 0 and 1. Only its y/z faces conduct, not its x face.
    fields['Jn_y'][0:2] = [2., 3.]
    fields['Jleak_z'][0:2] = [5., 7.]
    w = reference_widths(sim, axes)
    expected = 2*w[0][0]*w[2][0] + 3*w[0][1]*w[2][0] + 5*w[0][0]*w[1][0] + 7*w[0][1]*w[1][0]
    assert terminal_currents_native(sim, fields)['c1'] == pytest.approx(expected, rel=1e-14)


@pytest.mark.parametrize('shape', SHAPES)
@pytest.mark.parametrize('graded', [False, True])
@pytest.mark.parametrize('newton', [False, True])
def test_public_multiterminal_resistor_matches_independent_harmonic_network(shape, graded, newton):
    sim, axes, owners = problem(shape, graded, 1)
    m = sim.mesh
    edges = list(reference_edges(sim, axes))
    matrix = np.zeros((m.npts(), m.npts()))
    for _, left, right, area, distance in edges:
        c = area / distance
        matrix[left, left] += c
        matrix[right, right] += c
        matrix[left, right] -= c
        matrix[right, left] -= c
    voltage = np.array([0., .012, -.003, .004])[owners]
    rhs = np.zeros(m.npts())
    for idx in np.flatnonzero(owners):
        matrix[idx] = 0.
        matrix[idx, idx] = 1.
        rhs[idx] = voltage[idx]
    potential = np.linalg.solve(matrix, rhs)
    density = 1e16
    low = PyDeviceSimulator(*shape, *(hi-lo for lo, hi in
        [(m.xmin, m.xmax), (m.ymin, m.ymax), (m.zmin, m.zmax)]))
    for values, setter in zip(axes, [low.set_x_positions, low.set_y_positions, low.set_z_positions]):
        setter(values)
    low.set_permittivity(np.full(m.npts(), 11.7*8.854187817e-12))
    low.set_mobility(np.full(m.npts(), .1), np.full(m.npts(), .05))
    low.set_doping(np.zeros(m.npts()))
    low.set_effective_dos(np.full(m.npts(), density), np.full(m.npts(), density))
    low.set_bandgap(np.zeros(m.npts()))
    low.set_recombination(np.full(m.npts(), 1e100), np.full(m.npts(), 1e100))
    low.set_dirichlet_potential({int(i): voltage[i] for i in np.flatnonzero(owners)})
    bc = {int(i): density for i in np.flatnonzero(owners)}
    low.set_electron_bc(bc)
    low.set_hole_bc(bc)
    low.set_initial_guess(potential, np.full(m.npts(), density), np.full(m.npts(), density))
    low.set_use_newton(newton)
    low.set_newton_primary(newton)
    low.set_newton_use_log_space(newton)
    low.set_gummel_max_iter(80)
    low.set_tolerance(1e-10)
    result = low.solve()
    assert result['converged']
    np.testing.assert_allclose(result['phi'], potential, atol=2e-11, rtol=2e-9)
    for key in ['n', 'p']:
        np.testing.assert_allclose(result[key], density, rtol=2e-9)
    q = float(native_constants()['elementary_charge_C'])
    expected = {name: 0. for name in ['c1', 'c2', 'c3']}
    for _, left, right, area, distance in edges:
        if bool(owners[left]) == bool(owners[right]):
            continue
        current = q*.15*density*(potential[left] - potential[right])*area/distance
        if owners[left]: expected['c'+str(owners[left])] += current
        else: expected['c'+str(owners[right])] -= current
    actual = terminal_currents_native(sim, result)
    scale = max(abs(v) for v in expected.values())
    assert scale > 0.
    for name in expected:
        assert abs(actual[name] - expected[name]) < 2e-8*scale
    check = ConservationTest(check_energy=False, tolerance=1e-7, current_atol_A=0.)
    assert check.run(lambda: dict(result, terminal_currents_A=actual)).passed
    broken = dict(actual)
    name = max(broken, key=lambda k: abs(broken[k]))
    broken[name] *= 1.2
    assert not check.run(lambda: dict(result, terminal_currents_A=broken)).passed
    print(json.dumps(dict(tensor_native_resistor=True, profile=native_constants()['profile'],
        shape=shape, graded=graded, newton=newton, converged=True,
        terminal_currents_A=actual, independent_reference_A=expected,
        maximum_scaled_current_error=max(abs(actual[k]-expected[k]) for k in expected)/scale,
        normalized_kcl_error=abs(fsum(actual.values()))/scale,
        initial_guess='independent_harmonic_solution_and_uniform_carriers')))


@pytest.mark.parametrize('defect', ['overlap', 'empty', 'fractional', 'nan_mask', 'mask_size',
    'missing', 'flux_size', 'nan_flux', 'inf_flux', 'complex_flux', 'flux_shape', 'one_contact'])
def test_incomplete_or_invalid_port_inputs_raise(defect):
    sim, _, _ = problem((5, 4, 3), True)
    fields = zero_fields(sim)
    if defect == 'overlap':sim.mesh.fields['contact_c2'] = sim.mesh.fields['contact_c1'].copy()
    elif defect == 'empty':sim.mesh.fields['contact_c1'] = np.zeros(sim.mesh.npts())
    elif defect in ['fractional', 'nan_mask']:
        mask = sim.mesh.fields['contact_c1'].astype(float)
        mask[0] = .5 if defect == 'fractional' else np.nan
        sim.mesh.fields['contact_c1'] = mask
    elif defect == 'mask_size':sim.mesh.fields['contact_c1'] = np.ones(2)
    elif defect == 'one_contact':del sim.mesh.fields['contact_c2']
    elif defect == 'missing':del fields['Jleak_y']
    elif defect == 'flux_size':fields['Jn_z'] = np.zeros(2)
    elif defect == 'flux_shape':fields['Jn_z'] = np.zeros((3, 20))
    elif defect == 'complex_flux':fields['Jn_z'] = fields['Jn_z'].astype(complex)
    else:fields['Jn_z'][0] = np.nan if defect == 'nan_flux' else np.inf
    with pytest.raises(ValueError):terminal_currents_native(sim, fields)


def test_component_summation_preserves_small_leakage_after_large_cancellation():
    sim, _, _ = problem((5, 1, 1), False)
    fields = zero_fields(sim)
    fields['Jn_x'][:] = 1e20
    fields['Jp_x'][:] = -1e20
    fields['Jleak_x'][:] = 1e-8
    area = (sim.mesh.ymax-sim.mesh.ymin)*(sim.mesh.zmax-sim.mesh.zmin)
    assert terminal_currents_native(sim, fields) == pytest.approx({'c1': 1e-8*area, 'c2': -1e-8*area}, rel=1e-14, abs=0.)


@pytest.mark.parametrize('value', [1e308, 1e-320])
def test_unrepresentable_face_current_is_rejected(value):
    sim, _, _ = problem((5, 1, 1), False)
    # A huge current overflows its face; a tiny current underflows a face.
    fields = zero_fields(sim)
    fields['Jn_x'][:] = value
    if value > 1:
        sim.mesh = StructuredGrid(((0., 1.), (0., 10.), (0., 10.)), 5, 1, 1)
        sim.mesh.fields.update(contact_c1=np.array([1,0,0,0,0]), contact_c2=np.array([0,0,0,0,1]))
    with pytest.raises(ValueError):terminal_currents_native(sim, fields)
