import numpy as np
import pytest
from tcad.mesh.polyhedral_regions import region_cut_cells
from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson


@pytest.mark.parametrize('scale',[1.,1e-9,1e3])
def test_nonconvex_union_no_double_volume_and_shared_gauss(scale):
    axes=[np.linspace(0,scale,4)]*3
    mesh=region_cut_cells(axes,{'L':[np.array([[1,0,0,.5*scale]]),np.array([[0,1,0,.5*scale]])]})
    np.testing.assert_allclose(mesh.volumes_m3.sum(),.75*scale**3,rtol=1e-13)
    np.testing.assert_allclose(np.sum(mesh.volumes_m3[:,None]*mesh.centroids_m,axis=0)/mesh.volumes_m3.sum(),
        np.array([5/12,5/12,.5])*scale,rtol=1e-13)
    flux=np.array([np.dot(face.centroid_m,face.area_vector_m2) for face in mesh.faces])
    assert mesh.audit_gauss(flux,np.full(len(mesh.volumes_m3),3.),charge_atol_C=1e-12*scale**3)['valid']
    gradient=np.array([.3,-.2,.5])/scale
    bc={f:.2+gradient@face.centroid_m for f,face in enumerate(mesh.faces) if face.neighbor<0}
    result=solve_cut_cell_poisson(mesh,2.,0.,dirichlet_V=bc,charge_atol_C=1e-12*scale)
    assert result['valid']
    np.testing.assert_allclose(result['cell_potential_V'],.2+mesh.centroids_m@gradient,rtol=1e-12,atol=1e-12)


def test_oblique_two_material_partition_and_interface_displacement():
    plane=np.array([1.,.7,.4,.93]);mesh=region_cut_cells([np.linspace(0,1,4)]*3,
        {'a':[plane[None,:]],'b':[-plane[None,:]]})
    np.testing.assert_allclose(mesh.volumes_m3.sum(),1.,rtol=1e-13)
    eps=np.where(mesh.region_ids=='a',2.,7.)
    signed=(mesh.centroids_m@plane[:3]-plane[3])/np.linalg.norm(plane[:3])
    voltage=-signed/eps
    bc={f:-(face.centroid_m@plane[:3]-plane[3])/np.linalg.norm(plane[:3])/eps[face.owner]
        for f,face in enumerate(mesh.faces) if face.neighbor<0}
    result=solve_cut_cell_poisson(mesh,eps,0.,dirichlet_V=bc,charge_atol_C=1e-12)
    assert result['valid'];np.testing.assert_allclose(result['cell_potential_V'],voltage,atol=2e-12)
    assert any(face.neighbor>=0 and mesh.region_ids[face.owner]!=mesh.region_ids[face.neighbor] for face in mesh.faces)
    assert not mesh.region_ids.flags.writeable


def test_overlap_sliver_and_fragment_limit_rejected():
    axes=[np.array([0.,1.])]*3
    with pytest.raises(ValueError,match='overlap'):region_cut_cells(axes,{'a':[[]],'b':[[]]})
    with pytest.raises(ValueError,match='fragment'):region_cut_cells(axes,{'a':[[[1,0,0,.5]]]},max_fragments=1)


def test_unresolved_near_planes_reject_instead_of_merging_material_volume():
    with pytest.raises(ValueError,match='unresolved'):
        region_cut_cells([np.array([0.,1.])]*3,
            {'a':[[[1,0,0,.5]]],'b':[[[-1,0,0,-(.5+2e-14)]]]})
