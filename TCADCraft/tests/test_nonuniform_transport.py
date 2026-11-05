"""Independent transport geometry controls; native fluxes and legacy fallback."""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from tcad.core import native_constants
from tcad.postprocess.current import (
    QE, sg_current_density_1d, sg_current_density_1d_z,
    contact_current_1d, contact_current_2d,
)
from tcad.postprocess.trust import kcl_residual_1d
from tcad.postprocess.mechanism import (
    drift_diffusion_split_1d, attribute_mechanism, btbt_generation,
)


def line_problem():
    x = np.array([0., .1, .4, 1.]) * 1e-6
    mesh = StructuredGrid(((0., 1e-6),) * 3, 4, 1, 1, axes=(x, [0.], [0.]))
    mesh.fields.update(mu_n=np.full(4, .1), mu_p=np.full(4, .05),
                       contact_left=np.array([1, 0, 0, 0]),
                       contact_right=np.array([0, 0, 0, 1]))
    state = dict(phi=np.zeros(4), n=1e20 + 1e26*x, p=1e20 + 2e25*x)
    return SimpleNamespace(mesh=mesh, VT=.02585), state, x


@pytest.mark.parametrize('direction', ['x', 'z'])
@pytest.mark.parametrize('mode', ['diffusion', 'drift'])
def test_sg_affine_limits_are_independent_of_edge_length(direction, mode):
    sim, state, x = line_problem()
    if mode == 'drift':
        state.update(phi=1e4*x, n=np.full(4, 1e20), p=np.full(4, 2e20))
        expected = [-QE*.1*1e20*1e4, -QE*.05*2e20*1e4]
    else:
        expected = [QE*.1*sim.VT*1e26, -QE*.05*sim.VT*2e25]
    fun = sg_current_density_1d if direction == 'x' else sg_current_density_1d_z
    current = fun(state['phi'], state['n'], state['p'], np.diff(x),
                  sim.mesh.fields['mu_n'], sim.mesh.fields['mu_p'], sim.VT)
    for actual, reference in zip(current, expected):
        np.testing.assert_allclose(actual, reference, rtol=2e-14)


@pytest.mark.parametrize('spacing', [0., -1., np.nan, np.inf, [1., 2.],
                                    [[1., 1., 1.]], [1., 0., 1.], [1., np.inf, 1.]])
def test_sg_rejects_invalid_lengths(spacing):
    sim, state, _ = line_problem()
    with pytest.raises(ValueError, match='edge'):
        sg_current_density_1d(state['phi'], state['n'], state['p'], spacing,
                              sim.mesh.fields['mu_n'], sim.mesh.fields['mu_p'], sim.VT)


def test_legacy_contact_kcl_and_mechanism_share_actual_distances():
    sim, state, _ = line_problem()
    expected = QE*sim.VT*(.1*1e26-.05*2e25)
    assert contact_current_1d(sim, state, 'left') == pytest.approx(expected, rel=2e-14, abs=0.)
    assert contact_current_1d(sim, state, 'right') == pytest.approx(-expected, rel=2e-14, abs=0.)
    assert kcl_residual_1d(sim, state) < 1e-14
    assert attribute_mechanism(sim, state).J_diff == pytest.approx(expected, rel=2e-14, abs=0.)


@pytest.mark.parametrize('mode', ['drift', 'diffusion'])
def test_classical_components_use_actual_edges(mode):
    sim, state, x = line_problem()
    state['phi'] = 1e4*x
    split = drift_diffusion_split_1d(state['phi'], state['n'], state['p'], np.diff(x),
                                    sim.mesh.fields['mu_n'], sim.mesh.fields['mu_p'], sim.VT)
    expected = (-QE*.1*(state['n'][:-1]+state['n'][1:])/2*1e4 if mode == 'drift'
                else np.full(3, QE*.1*sim.VT*1e26))
    np.testing.assert_allclose(split['Jn_'+('drift' if mode == 'drift' else 'diff')],
                               expected, rtol=2e-14)


def slab_problem():
    x = np.array([0., .1, .4, 1.])*1e-6
    z = np.array([0., .2, 1.])*1e-6
    mesh = StructuredGrid(((0., 1e-6),)*3, 4, 1, 3, axes=(x, [0.], z))
    for side, axis, endpoint in [('left', 0, 0.), ('right', 0, 1e-6),
                                  ('bottom', 2, 0.), ('top', 2, 1e-6)]:
        mesh.fields['contact_'+side] = mesh.flat_coords()[axis] == endpoint
    return SimpleNamespace(mesh=mesh, VT=.02585), x, z


@pytest.mark.parametrize('side', ['left', 'right', 'bottom', 'top'])
@pytest.mark.parametrize('source', ['native', 'legacy'])
@pytest.mark.parametrize('profile', ['constant', 'affine'])
def test_full_faces_include_correct_endpoints_and_corner_orientation(side, source, profile):
    sim, x, z = slab_problem()
    xx, _, zz = sim.mesh.flat_coords()
    factor = np.ones(12) if profile == 'constant' else 1. + xx/1e-6 + zz/1e-6
    if source == 'native':
        state = {key: value*factor for key, value in
                 [('Jn_x', 2.), ('Jp_x', 0.), ('Jn_z', 5.), ('Jp_z', 0.)]}
        # On each full face, the transverse affine field has mean 1.5;
        # the normal sample is at the inner edge's lower-index node.
        if side in ['left', 'right']:
            normal_position = 0. if side == 'left' else x[-2]/1e-6
            expected = 2e-12*(1. if profile == 'constant' else 1.5+normal_position)
        else:
            normal_position = 0. if side == 'bottom' else z[-2]/1e-6
            expected = 5e-12*(1. if profile == 'constant' else 1.5+normal_position)
    else:
        # Bilinear density: exact diffusion gradient is affine transversely.
        n = 1e20 + 1e26*(xx+zz)
        if profile == 'affine':
            n += 1e32*xx*zz
        sim.mesh.fields.update(mu_n=np.full(12, .1), mu_p=np.zeros(12))
        state = dict(phi=np.zeros(12), n=n, p=np.zeros(12))
        expected = QE*.1*sim.VT*1e26*1e-12*(1. if profile == 'constant' else 1.5)
    if side in ['right', 'top']:
        expected *= -1
    assert contact_current_2d(sim, state, side) == pytest.approx(expected, rel=2e-14, abs=0.)
    assert contact_current_2d(sim, state, side, width=2e-6) == pytest.approx(2*expected, rel=2e-14, abs=0.)


@pytest.mark.parametrize('side', ['left', 'right', 'bottom', 'top'])
def test_finite_contact_thickness_reads_first_free_edge(side):
    sim, _, _ = slab_problem()
    mask = np.zeros((3, 4), bool)
    if side == 'left': mask[:, :2] = True
    elif side == 'right': mask[:, -2:] = True
    elif side == 'bottom': mask[:2, :] = True
    else: mask[-2:, :] = True
    sim.mesh.fields['contact_c'] = mask.ravel()
    state = {key: np.zeros(12) for key in ['Jn_x', 'Jp_x', 'Jn_z', 'Jp_z']}
    edge = (1 if side in ['left', 'right', 'bottom'] else 0)
    flux = state['Jn_x' if side in ['left', 'right'] else 'Jn_z'].reshape(3, 4)
    if side in ['left', 'right']: flux[:, edge] = 2.
    else: flux[edge, :] = 2.
    expected = (1 if side in ['left', 'bottom'] else -1)*2e-12
    assert contact_current_2d(sim, state, 'c') == pytest.approx(expected, rel=2e-14, abs=0.)


@pytest.mark.parametrize('defect', ['ambiguous', 'disconnected', 'full', 'badmask', 'ny', 'width'])
def test_surface_rejects_unsupported_geometry(defect):
    sim, _, _ = slab_problem()
    mask = np.zeros((3, 4), bool)
    if defect == 'ambiguous': mask[:2, :2] = True
    elif defect == 'disconnected': mask[:, [0, 2]] = True
    else: mask[:] = True
    sim.mesh.fields['contact_c'] = mask.ravel() if defect != 'badmask' else np.ones(2)
    if defect == 'ny': sim.mesh.ny = 2
    with pytest.raises(ValueError):
        contact_current_2d(sim, {}, 'c', width=0. if defect == 'width' else None)


def test_partial_corner_has_explicit_normal_and_dual_face_measure():
    sim, _, _ = slab_problem()
    mask = np.zeros(12); mask[0] = 1
    sim.mesh.fields['contact_c'] = mask
    state = dict(Jn_x=np.full(12, 2.), Jp_x=np.zeros(12),
                 Jn_z=np.full(12, 5.), Jp_z=np.zeros(12))
    assert contact_current_2d(sim, state, 'c') == pytest.approx(2.*.1e-6*1e-6, rel=2e-14, abs=0.)
    assert contact_current_2d(sim, state, 'c', normal='bottom') == pytest.approx(5.*.05e-6*1e-6, rel=2e-14, abs=0.)


@pytest.mark.parametrize('source', ['native', 'legacy'])
def test_exported_leakage_is_added_once_and_kcl_uses_total(source):
    sim, state, _ = line_problem()
    state['Jleak_x'] = np.full(4, 3.)
    if source == 'native':
        state.update(Jn_x=np.full(4, 1.), Jp_x=np.full(4, 2.))
        expected = 6.
    else:
        expected = QE*sim.VT*(.1*1e26-.05*2e25)+3.
    assert contact_current_1d(sim, state, 'left') == pytest.approx(expected, rel=2e-14, abs=0.)
    assert kcl_residual_1d(sim, state) < 1e-14


def test_native_flux_preference_survives_cancellation_and_checks_lengths():
    sim, state, _ = line_problem()
    state.update(n=np.full(4, 1e300), Jn_x=np.full(4, 1e-8), Jp_x=np.zeros(4))
    assert contact_current_1d(sim, state, 'left') == 1e-8
    assert kcl_residual_1d(sim, state) < 1e-14
    state['Jp_x'] = np.zeros(3)
    with pytest.raises(ValueError): contact_current_1d(sim, state, 'left')


@pytest.mark.parametrize('source', ['native', 'legacy'])
def test_kcl_preserves_uniform_raw_solver_facade(source):
    mesh = SimpleNamespace(nx=4, ny=1, nz=1, dx=1e-7, fields={}, npts=lambda: 4)
    sim = SimpleNamespace(mesh=mesh, VT=.02585)
    state = dict(phi=np.zeros(4), n=np.arange(4)*1e20, p=np.zeros(4))
    if source == 'native':
        state.update(Jn_x=np.full(4, 2.), Jp_x=np.zeros(4))
    assert kcl_residual_1d(sim, state) < 1e-14


@pytest.mark.parametrize('profile', ['constant', 'affine'])
def test_btbt_integrates_physical_nonuniform_control_volumes(profile):
    sim, _, _ = slab_problem()
    xx, _, zz = sim.mesh.flat_coords()
    g = np.full(12, 1e30) if profile == 'constant' else 1e30*(1+xx/1e-6+zz/1e-6)
    _, current = btbt_generation(dict(G_btbt=g), sim.mesh)
    assert current == pytest.approx(QE*1e30*1e-18*(1 if profile == 'constant' else 2), rel=2e-15, abs=0.)


def native_resistor(axis, layout, density=1e16):
    """Neutral intrinsic resistor: affine phi and constant n=p solve all equations."""
    coords = np.array(([0., .1, .4, .7, 1.] if layout == 0 else
                       [0., .01, .04, .5, .95, 1.])) * .6e-6
    axes = [np.array([0.]), np.array([0.]), np.array([0.])]
    axes[axis] = coords
    transverse = 2 if axis == 0 else 0
    axes[transverse] = np.array([0., .05, .2, .4])*1e-6
    bbox = [(0., 1e-6)]*3
    bbox[axis] = (0., .6e-6); bbox[transverse] = (0., .4e-6)
    mesh = StructuredGrid(tuple(bbox), *(len(a) for a in axes), axes=axes)
    xx = mesh.flat_coords()[axis]
    mesh.fields.update(mu_n=np.full(mesh.npts(), .1), mu_p=np.full(mesh.npts(), .05),
                       contact_low=xx == 0., contact_high=xx == coords[-1])
    sim = Simulator(mesh)
    low = sim._sim; size = mesh.npts()
    low.set_permittivity(np.full(size, 11.7*8.8542e-12))
    low.set_mobility(mesh.fields['mu_n'], mesh.fields['mu_p'])
    low.set_doping(np.zeros(size)); low.set_effective_dos(np.full(size, density), np.full(size, density))
    low.set_bandgap(np.zeros(size)); low.set_recombination(np.full(size, 1e100), np.full(size, 1e100))
    contacts = np.flatnonzero(mesh.fields['contact_low'] | mesh.fields['contact_high'])
    potential = .01*(1-xx/.6e-6)
    low.set_dirichlet_potential({int(i): float(potential[i]) for i in contacts})
    low.set_electron_bc({int(i): density for i in contacts})
    low.set_hole_bc({int(i): density for i in contacts})
    low.set_initial_guess(potential, np.full(size, density), np.full(size, density))
    low.set_use_newton(False)
    state = sim.run(max_iter=80, tol=1e-12, physical_step=False)
    assert state['converged']
    np.testing.assert_allclose(state['phi'], potential, atol=2e-12, rtol=2e-10)
    np.testing.assert_allclose(state['n'], density, rtol=2e-10)
    np.testing.assert_allclose(state['p'], density, rtol=2e-10)
    charge = {'si': 1.602176634e-19, 'legacy-charge': 1.602192e-19}[native_constants()['profile']]
    expected = charge*.15*density*.01/.6e-6*.4e-6*1e-6
    currents = {}
    for source in ['native', 'legacy']:
        fields = state if source == 'native' else {k: state[k] for k in ['phi', 'n', 'p']}
        current = [contact_current_2d(sim, fields, name) for name in ['low', 'high']]
        np.testing.assert_allclose(current, [expected, -expected], rtol=2e-10, atol=0.)
        currents[source] = current
    return dict(axis='xyz'[axis], layout=layout, expected_A=expected, currents_A=currents,
                coordinates_m=[a.tolist() for a in axes])


@pytest.mark.parametrize('axis', [0, 2])
@pytest.mark.parametrize('layout', [0, 1])
def test_native_mobile_solution_and_legacy_postprocessing_match_exact_resistor(axis, layout):
    native_resistor(axis, layout)


@pytest.mark.parametrize('case', json.loads((Path(__file__).parent/'data/sentaurus_parallel_mixed.json').read_text())['cases'], ids=lambda c: c['name'])
@pytest.mark.parametrize('axis', [0, 2])
@pytest.mark.parametrize('layout', [0, 1])
def test_existing_sentaurus_steady_conducting_branch_replay(case, axis, layout):
    raw = case['raw']
    density = np.sqrt(raw['Pos(0.3,0.2) eDensity'][0]*raw['Pos(0.3,0.2) hDensity'][0])*1e6
    record = native_resistor(axis, layout, density)
    reference = np.array([raw['left eCurrent'][-1]+raw['left hCurrent'][-1],
                          raw['right eCurrent'][-1]+raw['right hCurrent'][-1]])
    # Reuse the prior fixed 0.2% budget. This replays only the final steady
    # conducting Si branch, with measured ni; not the oxide/transient geometry.
    for current in record['currents_A'].values():
        np.testing.assert_allclose(current, reference, rtol=.002, atol=0.)
