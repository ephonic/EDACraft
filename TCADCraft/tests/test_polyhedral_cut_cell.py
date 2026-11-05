"""Analytic clipped volumes and independent affine-D Gauss control."""
import numpy as np
import pytest
from tcad.mesh.polyhedral_cut_cell import convex_cut_cells


@pytest.mark.parametrize('scale',[1.,1e-9,1e3])
def test_oblique_tetrahedron_exact_volume_centroid(scale):
    mesh=convex_cut_cells([np.array([0.,1.])*scale]*3,[[1,1,1,scale]])
    np.testing.assert_allclose(mesh.volumes_m3,[scale**3/6],rtol=2e-14)
    np.testing.assert_allclose(mesh.centroids_m,[[scale/4]*3],rtol=2e-14)
    assert len(mesh.faces)==4
    np.testing.assert_allclose(sum(f.area_vector_m2 for f in mesh.faces),np.zeros(3),atol=scale**2*1e-14)


@pytest.mark.parametrize('offset',[.63,.97,1.41,2.37])
def test_nonuniform_shared_faces_affine_gauss_and_flux_negative_control(offset):
    axes=[np.array([0.,.17,.53,1.]),np.array([0.,.23,.61,1.]),np.array([0.,.19,.72,1.])]
    mesh=convex_cut_cells(axes,[[1.,.7,1.2,offset]])
    assert any(f.neighbor>=0 for f in mesh.faces)
    matrix=np.array([[2.,.4,-.3],[-.1,1.3,.5],[.2,.7,-.6]])
    flux=np.array([np.dot(matrix@f.centroid_m+[.2,-.3,.4],f.area_vector_m2) for f in mesh.faces])
    report=mesh.audit_gauss(flux,np.full(len(mesh.volumes_m3),np.trace(matrix)),charge_atol_C=2e-14)
    assert report['valid']
    flux[0]+=.01
    assert not mesh.audit_gauss(flux,np.full(len(mesh.volumes_m3),np.trace(matrix)),charge_atol_C=2e-14)['valid']


def test_closed_internal_flux_cancels_and_clipped_volume_is_not_edge_fraction():
    axes=[np.array([0.,.5,1.])]*3
    mesh=convex_cut_cells(axes,[[1,1,1,1.1]])
    flux=np.zeros(len(mesh.faces))
    for k,f in enumerate(mesh.faces):
        if f.neighbor>=0:flux[k]=k+.2
    assert abs(mesh.divergence_integrals(flux).sum())<1e-12
    # Inclusion-exclusion exact volume of {x+y+z<=1.1} within unit cube.
    np.testing.assert_allclose(mesh.volumes_m3.sum(),(1.1**3-3*.1**3)/6,rtol=1e-14)


@pytest.mark.parametrize('planes',[[[0,0,0,1]],[[1,1,1,np.nan]],[[1,1,1]]])
def test_invalid_halfspaces(planes):
    with pytest.raises(ValueError):convex_cut_cells([[0.,1.]]*3,planes)


def test_box_and_empty_intersection():
    mesh=convex_cut_cells([[0.,.4,1.]]*3,[])
    np.testing.assert_allclose(mesh.volumes_m3.sum(),1.,rtol=1e-14)
    with pytest.raises(ValueError):mesh.volumes_m3[0]=9
    with pytest.raises(ValueError):mesh.faces[0].area_vector_m2[0]=9
    empty=convex_cut_cells([[0.,1.]]*3,[[1,0,0,-1]])
    assert empty.volumes_m3.size==0 and empty.faces==()


@pytest.mark.parametrize('length',[1.,1e-8])
def test_actual_skew_cut_poisson_affine_patch_with_vector_polarization(length):
    from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
    axes=[np.array([0.,.17,.53,1.])*length]*3
    mesh=convex_cut_cells(axes,[[1.,.7,1.2,1.41*length]])
    direction=np.array([.2,-.3,.4])/length
    voltage={i:.1+direction@f.centroid_m for i,f in enumerate(mesh.faces) if f.neighbor<0}
    epsilon=2e-10;polarization=np.array([.01,-.02,.03])*epsilon/length
    result=solve_cut_cell_poisson(mesh,epsilon,0.,dirichlet_V=voltage,
        polarization_C_m2=polarization,charge_atol_C=epsilon*length*1e-11)
    assert result['valid'] and not result['transport_coupled']
    np.testing.assert_allclose(result['cell_potential_V'],.1+mesh.centroids_m@direction,rtol=1e-11,atol=1e-12)
    np.testing.assert_allclose(result['electric_field_V_m'],np.broadcast_to(-direction,(len(mesh.volumes_m3),3)),rtol=1e-10)
    exact=np.array([(-epsilon*direction+polarization)@f.area_vector_m2 for f in mesh.faces])
    np.testing.assert_allclose(result['integrated_D_flux_C'],exact,rtol=1e-10,atol=epsilon*length*1e-13)


def test_charged_oblique_cut_poisson_refines_and_conserves():
    from tcad.solver.cut_cell_poisson import solve_cut_cell_poisson
    errors=[]
    for n in (3,6):
        mesh=convex_cut_cells([np.linspace(0,1,n+1)]*3,[[1,.7,1.2,1.41]])
        voltage={i:float(np.sum(f.centroid_m**2)) for i,f in enumerate(mesh.faces) if f.neighbor<0}
        result=solve_cut_cell_poisson(mesh,1.,-6.,dirichlet_V=voltage,charge_atol_C=2e-11)
        assert result['valid']
        errors.append(np.sqrt(np.sum(mesh.volumes_m3*(result['cell_potential_V']-np.sum(mesh.centroids_m**2,axis=1))**2)/mesh.volumes_m3.sum()))
    assert errors[1]<.6*errors[0]
