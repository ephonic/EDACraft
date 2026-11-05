import numpy as np
import pytest
from tcad.mesh.finite_volume_reconstruction import cell_average_quadratic_coefficients as reconstruct
from tcad.mesh.finite_volume_reconstruction import evaluate_cell_quadratics as evaluate

LD=np.longdouble
EPS=np.finfo(LD).eps


@pytest.mark.parametrize('edges', [[0,1,2,3,4], [-2,-1.8,-.7,0,2.5,4], [0,.001,.01,.1,1]])
def test_exact_quadratic_from_integrals_on_nonuniform_cells(edges):
    edges=np.array(edges,dtype=LD);l,r=edges[:-1],edges[1:]
    means=3+2*(l+r)/2+(l*l+l*r+r*r)/3
    coefficients=reconstruct(edges,means)
    xi=np.array([-.5,-.13,0,.22,.5],dtype=LD)
    x=(l+r)[:,None]/2+(r-l)[:,None]*xi
    np.testing.assert_allclose(evaluate(coefficients,xi),3+2*x+x*x,rtol=2048*EPS,atol=2048*EPS)
    assert np.array_equal(coefficients[:,0],means)


def test_nonpolynomial_convergence_at_boundaries():
    errors=[]
    for n in (8,16,32):
        e=np.linspace(LD(0),LD(1),n+1);h=np.diff(e)
        means=np.exp(LD('1.7')*e[:-1])*np.expm1(LD('1.7')*h)/(LD('1.7')*h)
        errors.append(float(np.max(abs(evaluate(reconstruct(e,means),0)-np.exp(LD('1.7')*(e[:-1]+h/2))))))
    assert errors[1]<errors[0]/6 and errors[2]<errors[1]/6


def test_inventory_by_independent_gauss_quadrature_after_limiting():
    e=np.array([0,.1,.4,1,2,3],dtype=LD);means=np.array([.001,.2,3,.1,.002],dtype=LD)
    co=reconstruct(e,means,lower_bound=0)
    x=np.sqrt(LD(3)/5)/2;values=evaluate(co,[-x,0,x])
    quadrature=values@np.array([LD(5)/18,LD(4)/9,LD(5)/18])
    np.testing.assert_allclose(quadrature,means,rtol=256*EPS,atol=256*EPS*max(means))
    np.testing.assert_allclose(np.sum(quadrature*np.diff(e)),np.sum(means*np.diff(e)),rtol=256*EPS,atol=0)
    assert np.min(evaluate(co,np.linspace(-.5,.5,501)))>=0


def test_interior_minimum_is_limited_not_only_endpoints():
    e=np.array([-1.5,-.5,.5,1.5],dtype=LD);l,r=e[:-1],e[1:]
    means=(l*l+l*r+r*r)/3-LD('.2')*(l+r)/2-LD('.02')
    unlimited=reconstruct(e,means)
    assert evaluate(unlimited,-.5)[1]>0 and evaluate(unlimited,.5)[1]>0
    assert evaluate(unlimited,LD('.1'))[1]<0
    co=reconstruct(e,means,lower_bound=0)
    assert evaluate(co,LD('.1'))[1]>=0
    assert np.array_equal(co[:,0],means)


def test_cell_at_floor_becomes_constant_and_preserves_other_means():
    means=np.array([1,0,2,1],dtype=LD);co=reconstruct(np.arange(5),means,lower_bound=0)
    assert np.array_equal(co[1],[0,0,0]) and np.array_equal(co[:,0],means)


def test_signed_fields_and_bounds_are_explicit():
    means=np.array([-3,-1,-2,-4],dtype=LD)
    co=reconstruct(np.arange(5),means)
    assert np.array_equal(co[:,0],means)
    bounded=reconstruct(np.arange(5),means,lower_bound=[-5,-2,-3,-6])
    assert np.all(evaluate(bounded,np.linspace(-.5,.5,101))>=np.array([-5,-2,-3,-6])[:,None])


def test_input_ownership_and_constant_preservation():
    e=np.arange(5,dtype=LD);means=np.full(4,LD('1234567890.123456'))
    co=reconstruct(e,means);expected=means.copy();means[:]=0;e[:]=0
    assert not co.flags.writeable and np.array_equal(evaluate(co,0),expected)
    assert np.all(co[:,1:]==0)
    with pytest.raises(ValueError):co[0,0]=0


@pytest.mark.parametrize('edges,means,bound', [
 ([0,1,2],[1,2],None),([0,1,1,3],[1,2,3],None),([0,1,2,3],[1,np.nan,3],None),
 ([0,1,2,np.inf],[1,2,3],None),([False,True,True,True],[1,2,3],None),
 ([0,1,2,3],[[1,2,3]],None),([0,1,2,3],[1,2,3],True),
 ([0,1,2,3],[1,2,3],[0,0]),([0,1,2,3],[1,2,3],2),
 ([0,1,2,3],[1,2,3],np.inf),([0,1,2,3],[1+1j,2,3],None)
])
def test_invalid_inputs_rejected(edges,means,bound):
    with pytest.raises(ValueError):reconstruct(edges,means,lower_bound=bound)


@pytest.mark.parametrize('xi',[.500001,np.nan,[0,np.inf],True,[[0,.1]],1j])
def test_no_cell_extrapolation_or_invalid_coordinate(xi):
    with pytest.raises(ValueError):evaluate(reconstruct([0,1,2,3],[1,2,3]),xi)


def test_material_energy_inventory_from_separately_reconstructed_kinetic_and_density():
    e=np.array([0,.1,.2,.8,1],dtype=LD);n=np.array([1,4,.1,2],dtype=LD);k=np.array([3,.01,2,1],dtype=LD);band=LD('7.25')
    nc=reconstruct(e,n,lower_bound=0);kc=reconstruct(e,k,lower_bound=0)
    x=np.sqrt(LD(3)/5)/2;w=np.array([LD(5)/18,LD(4)/9,LD(5)/18])
    inventory=np.sum(((evaluate(kc,[-x,0,x])+band*evaluate(nc,[-x,0,x]))@w)*np.diff(e))
    np.testing.assert_allclose(inventory,np.sum((k+band*n)*np.diff(e)),rtol=256*EPS,atol=0)
