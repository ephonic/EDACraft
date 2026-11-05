"""Reduced dimensions, incident-cell geometry and adaptive native re-solves."""
import numpy as np
import pytest

from tcad.geometry.device_builder import Device, Region, Material, Box
from tcad.mesh.structured_grid import StructuredGrid
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.simulator import Simulator
from test_nonuniform_mesh_pipeline import simulator as dielectric_simulator


LAYOUTS = [(0,), (1,), (2,), (0,1), (0,2), (1,2), (0,1,2)]
CASES = [(layout, axis) for layout in LAYOUTS for axis in layout]


def device():
    return Device().add_region(Region('base', Box(0,1,0,1,0,1), Material('base')))


def grid_for(layout, driver, scale=1.):
    axes = [np.array([.25])*scale for _ in range(3)]
    for axis in layout:
        axes[axis] = np.array([0., .3, 1.])*scale
    axes[driver] = np.array([0., .1, .4, .7, 1.])*scale
    return StructuredGrid(((0.,scale),)*3, *(len(a) for a in axes), axes=axes)


@pytest.mark.parametrize('layout,axis', CASES)
@pytest.mark.parametrize('kind', ['doping', 'epsilon', 'solution'])
def test_localized_jump_marks_active_axis_and_refines_only_its_interval(layout, axis, kind):
    grid = grid_for(layout, axis)
    jump = (grid.flat_coords()[axis] >= .4).astype(float)
    refiner = AdaptiveRefiner(device(), directional_thresholds={a:.5 for a in 'xyz'})
    if kind == 'solution':
        markers = refiner._compute_solution_error_markers(grid, {'phi':jump}, 0, ['phi'])
    else:
        grid.fields[kind] = jump
        markers = refiner._compute_feature_markers(grid)
    expected = np.zeros(tuple(max(n-1,1) for n in grid.shape()), bool)
    selector = [slice(None)]*3; selector[axis] = 1
    expected[tuple(selector)] = True
    for a, name in enumerate('xyz'):
        np.testing.assert_array_equal(markers[name], expected if a == axis else np.zeros_like(expected))
    fine = refiner._refine_from_markers(grid, markers, 1)
    for a, (old, new) in enumerate(zip(grid.axis_coordinates(), fine.axis_coordinates())):
        np.testing.assert_allclose(new, [0.,.1,.25,.4,.7,1.] if a == axis else old,
                                   atol=1e-15, rtol=0.)
    assert fine.control_volumes().sum() == pytest.approx(1., rel=2e-15)
    assert 'epsilon' in fine.fields and len(fine._material_shapes) == 1


@pytest.mark.parametrize('layout,axis', CASES)
@pytest.mark.parametrize('kind', ['doping', 'epsilon', 'solution'])
def test_outer_corner_edges_reach_their_incident_cell(layout, axis, kind):
    grid = grid_for(layout, axis)
    data = np.zeros(grid.shape())
    selector = [-1 if a in layout else 0 for a in range(3)]
    selector[axis] = slice(2, None)
    data[tuple(selector)] = 1.
    values = data.transpose(2,1,0).ravel()
    refiner = AdaptiveRefiner(device(), directional_thresholds={a:.5 for a in 'xyz'})
    if kind == 'solution':
        markers = refiner._compute_solution_error_markers(grid, {'phi':values}, 0, ['phi'])
    else:
        grid.fields[kind] = values
        markers = refiner._compute_feature_markers(grid)
    expected = np.zeros(tuple(max(n-1,1) for n in grid.shape()), bool)
    target = [-1 if a in layout else 0 for a in range(3)]; target[axis] = 1
    expected[tuple(target)] = True
    np.testing.assert_array_equal(markers['xyz'[axis]], expected)


@pytest.mark.parametrize('layout,axis', CASES)
def test_curvature_markers_include_both_sides_of_each_node_without_activating_extrusion(layout, axis):
    grid = grid_for(layout, axis)
    refiner = AdaptiveRefiner(device())
    coord = grid.flat_coords()[axis]
    affine = refiner._compute_solution_error_markers(grid, {'phi':coord}, 0, ['phi'], 'residual')
    assert not any(m.any() for m in affine.values())
    curved = refiner._compute_solution_error_markers(grid, {'phi':coord**2}, 0, ['phi'], 'residual')
    for a,name in enumerate('xyz'):
        assert curved[name].all() if a in layout else not curved[name].any()


@pytest.mark.parametrize('layout,axis', CASES)
def test_level_zero_and_per_axis_caps_preserve_coordinates(layout, axis):
    grid = grid_for(layout, axis)
    refiner = AdaptiveRefiner(device(), max_level=0, axis_refinement={'xyz'[axis]:1})
    markers = {name: np.full(tuple(max(n-1,1) for n in grid.shape()), a in layout)
               for a,name in enumerate('xyz')}
    zero = refiner._refine_from_markers(grid, markers, 0)
    capped = refiner._refine_from_markers(grid, markers, 4)
    for a,coords in enumerate(grid.axis_coordinates()):
        np.testing.assert_array_equal(zero.axis_coordinates()[a], coords)
        assert len(capped.axis_coordinates()[a]) == (2*(len(coords)-1)+1 if a==axis else len(coords))


@pytest.mark.parametrize('layout', LAYOUTS + [()])
def test_public_feature_generation_accepts_explicit_reduced_dimensions(layout):
    shape = tuple(4 if a in layout else 1 for a in range(3))
    refiner = AdaptiveRefiner(device(), base_shape=shape)
    assert refiner.generate_feature_refined_mesh(0).shape() == shape
    assert refiner.generate_feature_refined_mesh(1).shape() == shape


@pytest.mark.parametrize('kind', ['shape', 'inactive', 'level', 'mode', 'combine'])
def test_refinement_rejects_invalid_requests(kind):
    grid = grid_for((0,), 0); refiner = AdaptiveRefiner(device())
    markers = {a:np.zeros((4,1,1),bool) for a in 'xyz'}
    with pytest.raises(ValueError):
        if kind == 'shape':
            markers['x'] = np.zeros((4,0,0),bool);refiner._refine_from_markers(grid,markers,1)
        elif kind == 'inactive':
            markers['y'][:] = True;refiner._refine_from_markers(grid,markers,1)
        elif kind == 'level': refiner._refine_from_markers(grid,markers,-1)
        elif kind == 'mode': refiner.refine_from_solution(grid,{},mode='typo')
        else: refiner.refine_from_solution(grid,{},combine='typo')


@pytest.mark.parametrize('kwargs', [dict(base_shape=(0,1,1)),dict(base_shape=(3,1)),
    dict(base_shape=(3.,1,1)),dict(base_shape=(True,1,1)),dict(max_level=-1),
    dict(refinement_ratio=1),dict(refinement_ratio=2.5),dict(axis_refinement={'x':-1})])
def test_invalid_controller_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError): AdaptiveRefiner(device(), **kwargs)


@pytest.mark.parametrize('layout,axis', CASES)
@pytest.mark.parametrize('combine', ['union', 'intersection'])
def test_combining_feature_and_solution_markers_remains_directional(layout, axis, combine):
    grid = grid_for(layout,axis); x=grid.flat_coords()[axis]
    grid.fields['doping'] = (x>=.4).astype(float)
    refiner = AdaptiveRefiner(device(),directional_thresholds={a:.5 for a in 'xyz'})
    # Solution flags only the other interval; intersection must remain coarse.
    fine=refiner.refine_from_solution(grid,{'phi':(x>=.7).astype(float)},fields=['phi'],combine=combine)
    np.testing.assert_allclose(fine.axis_coordinates()[axis],
        [0.,.1,.25,.4,.55,.7,1.] if combine=='union' else [0.,.1,.4,.7,1.],atol=1e-15,rtol=0.)


@pytest.mark.parametrize('layout,axis', CASES)
def test_charge_curvature_drives_refinement_and_native_re_solve(layout, axis):
    grid=grid_for(layout,axis,scale=1e-6)
    dev=Device().add_region(Region('base',Box(0,1e-6,0,1e-6,0,1e-6),Material('base')))
    refiner=AdaptiveRefiner(dev)
    def solve(mesh,guess=None):
        sim=dielectric_simulator(mesh,axis)
        charge=-2*3.9*8.854187817e-12*.2/1e-12/1.602176634e-19
        sim._sim.set_doping(np.full(mesh.npts(),charge))
        if guess is not None:sim._sim.set_initial_guess(guess,np.zeros(mesh.npts()),np.zeros(mesh.npts()))
        state=sim.run(max_iter=80,tol=1e-12,physical_step=False)
        assert state['converged']
        np.testing.assert_allclose(state['phi'],.2*(mesh.flat_coords()[axis]/1e-6)**2,atol=2e-11,rtol=2e-9)
        return state
    coarse=solve(grid)
    fine=refiner.refine_from_solution(grid,coarse,fields=['phi'],mode='residual')
    assert fine.shape()[axis]>grid.shape()[axis]
    for a in range(3):
        if a not in layout:np.testing.assert_array_equal(fine.axis_coordinates()[a],grid.axis_coordinates()[a])
    guess=refiner._prolongate_data(grid,fine,coarse['phi'])
    assert np.isfinite(guess).all()
    solve(fine,guess)


@pytest.mark.parametrize('layout,axis', CASES)
def test_public_adaptive_loop_solves_reduced_dimensional_neutral_resistor(layout, axis):
    # Constant coefficients make the exact neutral solution affine. The
    # derivative indicator is intentionally not treated as an error bound.
    mat=Material('neutral',epsilon_r=11.7,Eg=0.,Nc=1e10,Nv=1e10,mu_n=1000.,mu_p=500.)
    dev=Device().add_region(Region('base',Box(0,1e-6,0,1e-6,0,1e-6),mat))
    for side,lo,hi,voltage in [('low',-1e-12,1e-12,0.),('high',1e-6-1e-12,1e-6+1e-12,.01)]:
        bounds=[[-1e-12,1e-6+1e-12] for _ in range(3)];bounds[axis]=[lo,hi]
        dev.add_contact(side,Box(*(v for b in bounds for v in b)),voltage=voltage)
    shape=tuple(5 if a==axis else 3 if a in layout else 1 for a in range(3))
    refiner=AdaptiveRefiner(dev,base_shape=shape)
    sim=Simulator(refiner.generate_feature_refined_mesh(0));sim.set_material_from_mesh()
    grids,states,history=refiner.run_adaptive_solve(sim,max_rounds=2,initial_level=0,
        error_fields=['phi'],verbose=False,sim_kwargs=dict(max_iter=80,tol=1e-10,physical_step=False))
    assert len(grids)==len(states)==2
    assert all(len(values)==2 for values in history.values())
    assert grids[0].shape()[axis]==5 and grids[1].shape()[axis]==9
    for mesh,state in zip(grids,states):
        assert state['converged']
        for a in range(3):
            if a != axis:assert mesh.shape()[a]==shape[a]
        np.testing.assert_allclose(state['phi'],.01*mesh.flat_coords()[axis]/1e-6,atol=2e-12,rtol=2e-9)
