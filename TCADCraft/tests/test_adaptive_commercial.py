"""Adaptive local refinement followed by native/static SDevice film controls."""
import json
from pathlib import Path
import numpy as np
import pytest

from tcad.geometry.device_builder import Device, Region, Material, Box
from tcad.mesh.structured_grid import StructuredGrid
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.mesh.cut_cell import compute_edge_permittivity
from test_nonuniform_mesh_pipeline import simulator
from test_adaptive_dimensions import CASES


FIXTURE = json.loads((Path(__file__).parent/'data/sentaurus_box_cut_edges.json').read_text())


def adaptive_film(layout, axis):
    length, eps0 = 1e-6, 8.854187817e-12
    bounds = [[0., length] for _ in range(3)];bounds[axis] = [.23*length, .27*length]
    base = Box(0,length,0,length,0,length)
    film = Box(*(v for b in bounds for v in b))
    dev = Device().add_region(Region('base',base,Material('base',epsilon_r=3.9)))
    dev.add_region(Region('film',film,Material('film',epsilon_r=15.)))
    axes = [np.array([.5])*length for _ in range(3)]
    for a in layout:axes[a]=np.array([0.,.4,1.])*length
    axes[axis]=np.array([0.,.25,.5,1.])*length
    coarse=StructuredGrid(((0.,length),)*3,*(len(a) for a in axes),axes=axes)
    for name,data in dev.sample_on_grid(*coarse.flat_coords()).items():coarse.add_field(name,data)
    fine=AdaptiveRefiner(dev).refine_from_solution(coarse,{'phi':coarse.flat_coords()[axis]/length},
        fields=['phi'],combine='intersection')
    assert fine.shape()[axis]==6
    for a in range(3):
        if a!=axis:np.testing.assert_array_equal(fine.axis_coordinates()[a],coarse.axis_coordinates()[a])
    records=[]
    for name,mesh in [('coarse',coarse),('refined',fine)]:
        ids=film.contains(*mesh.flat_coords()).astype(int)
        eps=np.where(ids==1,15.,3.9)*eps0
        edges=compute_edge_permittivity(mesh,eps,ids,[(base,0),(film,1)],
                                       material_permittivity={0:3.9*eps0,1:15.*eps0})
        sim=simulator(mesh,axis);sim._sim.set_permittivity(eps)
        sim._sim.set_edge_permittivity(*(edges[a+s] for a in 'xyz' for s in ['_plus','_minus']))
        if records:
            guess=AdaptiveRefiner._prolongate_data(coarse,mesh,coarse_state['phi'])
            sim._sim.set_initial_guess(guess,np.zeros(mesh.npts()),np.zeros(mesh.npts()))
        state=sim.run(max_iter=80,tol=1e-12,physical_step=False)
        assert state['converged']
        if name=='coarse':coarse_state=state
        x=mesh.flat_coords()[axis]
        overlap=np.clip(x-.23*length,0.,.04*length)
        resistance=(x-overlap)/(3.9*eps0)+overlap/(15.*eps0)
        denominator=.96*length/(3.9*eps0)+.04*length/(15.*eps0)
        expected=.2*resistance/denominator
        error=float(max(abs(state['phi']-expected)))
        assert error<2e-10
        hshape=[1,1,1];hshape[axis]=mesh.shape()[axis]-1
        distances=np.diff(mesh.axis_coordinates()[axis]).reshape(hshape)
        edge_slice=[slice(None)]*3;edge_slice[axis]=slice(None,-1)
        edge_eps=mesh.to_3d(edges['xyz'[axis]+'_plus'])[tuple(edge_slice)]
        charges=(edge_eps*np.diff(mesh.to_3d(state['phi']),axis=axis)/distances*length**2).ravel()
        differences=[float(max(abs(charges/ref['charges_C'][1]-1))) for ref in FIXTURE['commercial']]
        assert max(differences)<FIXTURE['relative_budget']
        records.append(dict(mesh=name,shape=mesh.shape(),coordinates_m=[c.tolist() for c in mesh.axis_coordinates()],
            series_phi_max_absolute_error_V=error,charges_C=charges.tolist(),
            commercial_charge_max_relative_error=max(differences)))
    return dict(active_axes=list(layout),driving_axis=axis,records=records)


@pytest.mark.parametrize('layout,axis',CASES)
def test_adaptive_mesh_transfers_and_native_resolves_match_existing_sentaurus_film(layout,axis):
    adaptive_film(layout,axis)
