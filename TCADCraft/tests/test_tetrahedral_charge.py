"""Analytic Gauss-law checks for cell-side tetrahedral contact quadrature."""
from itertools import permutations
import numpy as np
import pytest

from tcad.validation import (integrate_tetrahedral_electrode_charge,
                             tetrahedral_surface_quadrature)


def single():
    return dict(vertices_m=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]]),
        tetrahedra=np.array([[0,1,2,3]]),potential_V=np.array([0.,-2.,3.,-4.]),
        permittivity_F_m=np.array([5.]),polarization_C_m2=np.array([[1.,2.,3.]]),
        contact_triangles=np.array([[0,2,3]]))


def layered():
    x=np.array([[i,j,k] for i in range(3) for j in range(2) for k in range(2)],dtype=float)
    lookup={tuple(v):i for i,v in enumerate(x)};tet=[]
    for i in range(2):
        for order in permutations(range(3)):
            v=np.array([i,0,0]);nodes=[lookup[tuple(v)]]
            for a in order:
                v=v.copy();v[a]+=1;nodes.append(lookup[tuple(v)])
            tet.append(nodes)
    tet=np.array(tet);left=x[tet].mean(axis=1)[:,0]<1
    phi=-2*np.minimum(x[:,0],1)-1.6*np.maximum(x[:,0]-1,0)
    p=np.zeros((len(tet),3));p[:,0]=np.where(left,3.,-1.)
    allfaces=tet[:,np.array([[1,2,3],[0,2,3],[0,1,3],[0,1,2]])].reshape(-1,3)
    faces,counts=np.unique(np.sort(allfaces,axis=1),axis=0,return_counts=True)
    exterior=faces[counts==1]
    return dict(vertices_m=x,tetrahedra=tet,potential_V=phi,
        permittivity_F_m=np.where(left,2.,5.),polarization_C_m2=p),exterior,faces[counts==2]


@pytest.mark.parametrize('order',list(permutations(range(4))))
def test_affine_field_owner_orientation_independent_of_tet_order(order):
    args=single();args['tetrahedra']=np.array([order])
    q=tetrahedral_surface_quadrature(**args)
    np.testing.assert_allclose(q['electric_field_V_m'],[[2,-3,4]],rtol=0,atol=1e-14)
    np.testing.assert_allclose(q['outward_dielectric_normals'],[[-1,0,0]],rtol=0,atol=1e-14)
    np.testing.assert_allclose(q['cell_volumes_m3'],[1/6])
    result=integrate_tetrahedral_electrode_charge(**args)
    assert result['surface_charge_C']==pytest.approx(5.5)
    assert result['surface_area_m2']==pytest.approx(.5)
    assert result['physical_validated'] is False
    assert result['boundary_coverage_verified'] is False


def test_discontinuous_materials_preserve_exact_series_displacement():
    args,faces,internal=layered()
    for plane,sign in [(0,1),(2,-1)]:
        selected=faces[np.all(args['vertices_m'][faces,0]==plane,axis=1)]
        q=integrate_tetrahedral_electrode_charge(**args,contact_triangles=selected)
        assert q['surface_charge_C']==pytest.approx(sign*7,abs=2e-14)
        assert q['surface_area_m2']==pytest.approx(1.)
    q=integrate_tetrahedral_electrode_charge(**args,contact_triangles=faces)
    assert abs(q['surface_charge_C'])<1e-14
    with pytest.raises(ValueError,match='exterior face'):
        tetrahedral_surface_quadrature(**args,contact_triangles=internal[:1])


def test_linear_cell_local_polarization_integrates_divergence_exactly():
    args=single();args['potential_V']=np.zeros(4)
    args['polarization_C_m2']=args['vertices_m'][args['tetrahedra']].copy()
    args['contact_triangles']=np.array([[1,2,3],[0,2,3],[0,1,3],[0,1,2]])
    q=integrate_tetrahedral_electrode_charge(**args)
    assert q['surface_charge_C']==pytest.approx(-3/6,abs=1e-14)


def test_linear_p_uses_face_nodes_and_keeps_cell_local_material_jump():
    args,faces,_=layered();p=args['polarization_C_m2']
    args['polarization_C_m2']=np.repeat(p[:,None,:],4,axis=1)
    selected=faces[np.all(args['vertices_m'][faces,0]==0,axis=1)]
    q=integrate_tetrahedral_electrode_charge(**args,contact_triangles=selected)
    assert q['surface_charge_C']==pytest.approx(7.)


def test_rotation_translation_and_micrometre_scaling():
    args=single();theta=.73
    r=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1]])
    args['vertices_m']=(args['vertices_m']@r.T+np.array([4.,-2.,7.]))*1e-6
    args['potential_V']*=1e-6
    args['polarization_C_m2']=args['polarization_C_m2']@r.T
    q=integrate_tetrahedral_electrode_charge(**args)
    assert q['surface_charge_C']==pytest.approx(5.5e-12,rel=2e-14)


@pytest.mark.parametrize('name,value',[
    ('vertices_m',np.zeros((4,3))),
    ('vertices_m',np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0]])),
    ('vertices_m',np.full((4,3),np.nan)),
    ('vertices_m',np.zeros((4,2))),
    ('vertices_m',np.ones((4,3),complex)),
    ('potential_V',np.zeros((4,1))),
    ('potential_V',np.full(4,np.inf)),
    ('permittivity_F_m',np.array([0.])),
    ('permittivity_F_m',np.array([-1.])),
    ('permittivity_F_m',5.),
    ('polarization_C_m2',np.zeros((4,3))),
    ('polarization_C_m2',np.zeros((1,3,3))),
    ('tetrahedra',np.array([[0,1,2,4]])),
    ('tetrahedra',np.array([[0,1,2,-1]])),
    ('tetrahedra',np.array([[0,1,2,3.]])),
    ('tetrahedra',np.array([[0,1,2,2]])),
    ('tetrahedra',np.array([[0,1,2,3],[3,2,1,0]])),
    ('contact_triangles',np.array([[0,2,2]])),
    ('contact_triangles',np.array([[0,2,3],[3,2,0]])),
    ('contact_triangles',np.empty((0,3),int)),
    ('contact_triangles',np.array([[True,False,True]])),
])
def test_malformed_or_degenerate_inputs_fail(name,value):
    args=single();args[name]=value
    with pytest.raises((ValueError,TypeError)):
        tetrahedral_surface_quadrature(**args)


def test_nonexistent_contact_face_fails():
    args=single();args['vertices_m']=np.vstack([args['vertices_m'],[3,3,3]])
    args['potential_V']=np.r_[args['potential_V'],0]
    args['contact_triangles']=np.array([[0,2,4]])
    with pytest.raises(ValueError,match='exterior face'):
        tetrahedral_surface_quadrature(**args)


@pytest.mark.parametrize('tips,match',[
    ([[0,0,1],[0,0,-1],[.2,.2,2]],'nonmanifold'),
    ([[0,0,1],[.2,.2,2]],'same side'),
])
def test_invalid_volume_adjacency_is_rejected(tips,match):
    x=np.array([[0,0,0],[1,0,0],[0,1,0],*tips],float)
    tet=np.array([[0,1,2,i] for i in range(3,len(x))])
    with pytest.raises(ValueError,match=match):
        tetrahedral_surface_quadrature(x,tet,np.zeros(len(x)),np.ones(len(tet)),
            np.zeros((len(tet),3)),np.array([[0,1,3]]))


@pytest.mark.parametrize('scale',[1e-150,1e150])
def test_unrepresentable_physical_volume_fails_explicitly(scale):
    args=single();args['vertices_m']*=scale
    with pytest.raises(ValueError,match='range'):
        tetrahedral_surface_quadrature(**args)


def test_returned_quadrature_does_not_alias_input_arrays():
    args=single();q=tetrahedral_surface_quadrature(**args)
    for name in ('electric_field_V_m','polarization_C_m2','permittivity_F_m'):
        q[name][...]=99
    assert args['polarization_C_m2'][0,0]==1.
    assert args['permittivity_F_m'][0]==5.
