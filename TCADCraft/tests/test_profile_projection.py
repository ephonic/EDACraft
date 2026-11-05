"""Analytic integrals, narrow-cell cancellation and invalid-support controls."""
import numpy as np
import pytest
from tcad.mesh.profile_projection import piecewise_linear_cell_averages as project


@pytest.mark.parametrize('shift,scale',[(0.,1.),(3.,1.),(0.,1e-7)])
def test_nonuniform_cells_integrate_known_piecewise_affine_primitive(shift,scale):
    # f(t)=2+3t below 0.4; f(t)=4-2t above it (continuous at 0.4).
    knots=np.array([0.,.1,.4,.7,1.],np.longdouble)
    values=np.where(knots<=.4,2+3*knots,4-2*knots)
    edges=np.array([0.,.03,.31,.57,.92,1.],np.longdouble)
    def F(t):
        if t<=.4:return 2*t+1.5*t*t
        return 4*t-t*t-.4
    expected=np.array([(F(b)-F(a))/(b-a) for a,b in zip(edges[:-1],edges[1:])])
    result=project(shift+scale*knots,values,shift+scale*edges)
    np.testing.assert_allclose(result,expected,rtol=2e-14,atol=1e-14)
    np.testing.assert_allclose(np.dot(result,np.diff(edges)),F(1),rtol=2e-14)


def test_density_inventory_differs_from_midpoint_sampling_across_a_kink():
    x=[0.,.2,1.];density=[1.,5.,1.];edges=[0.,.5,1.]
    values=project(x,density,edges)
    # Triangle of height 4 on top of a unit background: integral = 3.
    assert abs(np.dot(values,np.diff(edges))-3)<1e-15
    midpoint=np.interp([.25,.75],x,density)
    assert abs(np.dot(midpoint,np.diff(edges))-3)>.1


def test_narrow_target_cell_does_not_subtract_large_prefix_integrals():
    ld=np.longdouble
    x=np.array([0,1,2],dtype=ld);edges=np.array([0,1,1+ld('1e-12'),2],dtype=ld)
    result=project(x,[1e20,2.,4.],edges)
    expected=2+(edges[2]-edges[1])
    assert abs(result[1]-expected)<ld('1e-17')


def test_signed_material_energy_and_particle_components_commute_with_projection():
    x=[0.,.1,.6,1.];n=np.array([1.,4.,2.,3.]);kinetic=np.array([3.,-1.,5.,2.])
    edges=[0.,.04,.3,.8,1.];band=-7.
    total=project(x,kinetic+band*n,edges)
    np.testing.assert_allclose(total,project(x,kinetic,edges)+band*project(x,n,edges),rtol=1e-15,atol=1e-15)


def test_positive_profile_is_bounded_and_inputs_and_result_are_detached():
    x=np.array([0.,.17,.54,1.]);y=np.array([2.,11.,1.,4.]);edges=np.linspace(0,1,17)
    old=[a.copy() for a in (x,y,edges)]
    result=project(x,y,edges)
    assert np.all(result>=1) and np.all(result<=11)
    assert result.dtype==np.dtype(np.longdouble)
    result[:]=0
    for a,b in zip((x,y,edges),old):np.testing.assert_array_equal(a,b)


def test_source_knot_insertion_preserves_the_same_declared_profile():
    a=project([0.,.5,1.],[1.,3.,2.],[0.,.2,.7,1.])
    b=project([0.,.25,.5,.75,1.],[1.,2.,3.,2.5,2.],[0.,.2,.7,1.])
    np.testing.assert_allclose(a,b,rtol=32*np.finfo(np.longdouble).eps,atol=0)


@pytest.mark.parametrize('kind',['x_bool','y_bool','edge_bool','complex','nan','infinite',
    'unaligned','matrix','empty','one_sample','duplicate_x','reversed_x','duplicate_edge',
    'reversed_edge','left_extrapolation','right_truncation'])
def test_invalid_profiles_or_changed_support_are_rejected(kind):
    x=[0.,.4,1.];y=[1.,2.,3.];e=[0.,.5,1.]
    if kind=='x_bool':x=np.array(x,bool)
    if kind=='y_bool':y=np.array(y,bool)
    if kind=='edge_bool':e=np.array(e,bool)
    if kind=='complex':y=np.array(y,complex)
    if kind=='nan':y[1]=np.nan
    if kind=='infinite':x[1]=np.inf
    if kind=='unaligned':y=[1.,2.]
    if kind=='matrix':y=[[1.,2.,3.]]
    if kind=='empty':x=[];y=[]
    if kind=='one_sample':x=[0.];y=[1.]
    if kind=='duplicate_x':x=[0.,0.,1.]
    if kind=='reversed_x':x=[0.,1.,.4]
    if kind=='duplicate_edge':e=[0.,0.,1.]
    if kind=='reversed_edge':e=[0.,1.,.5]
    if kind=='left_extrapolation':e=[-.1,.5,1.]
    if kind=='right_truncation':e=[0.,.5,.9]
    with pytest.raises(ValueError):project(x,y,e)
