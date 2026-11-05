"""Every steady solver must use the declared conservative face operator."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants


def stack(axis=0, path='gummel', traced=False):
    n=9; shape=[1,1,1];shape[axis]=n
    sim=PyDeviceSimulator(*shape,1e-8,1e-8,1e-8)
    x=np.array([0.,.3,.9,1.6,2.9,4.5,5.7,7.,8.])*1e-8
    getattr(sim,'set_'+ 'xyz'[axis]+'_positions')(x)
    eps=np.full(n,10*8.8542e-12)
    faces=8.8542e-12*np.array([11.7,11.7,11.7,11.7,3.9,3.9,3.9,3.9])
    sim.set_permittivity(eps)
    arrays=[np.array([],dtype=float) for _ in range(6)]
    arrays[2*axis]=np.r_[faces,faces[-1]];arrays[2*axis+1]=np.r_[faces[0],faces]
    sim.set_edge_permittivity(*arrays)
    sim.set_mobility(np.zeros(n),np.zeros(n));sim.set_doping(np.zeros(n))
    sim.set_effective_dos(np.full(n,1e16),np.full(n,1e16));sim.set_bandgap(np.full(n,6.))
    sim.set_recombination(np.full(n,1e100),np.full(n,1e100))
    sim.set_initial_guess(np.zeros(n),np.zeros(n),np.zeros(n))
    sim.set_dirichlet_potential({0:0.,n-1:.2})
    sim.set_use_newton(path!='gummel');sim.set_newton_primary(path=='newton')
    sim.set_gummel_max_iter(80);sim.set_tolerance(1e-12);sim.set_nonlinear_history_enabled(traced)
    expected=np.r_[0.,np.cumsum(np.diff(x)/faces)]
    expected*=.2/expected[-1]
    return sim,x,faces,expected


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('path',['gummel','hybrid','newton'])
def test_explicit_faces_match_series_capacitor_solution_and_constant_displacement(axis,path):
    sim,x,faces,expected=stack(axis,path,traced=True);state=sim.solve()
    assert state['converged']
    np.testing.assert_allclose(state['phi'],expected,rtol=1e-9,atol=2e-12)
    displacement=-faces*np.diff(state['phi'])/np.diff(x)
    np.testing.assert_allclose(displacement,np.full(8,displacement[0]),rtol=1e-9,atol=0.)


@pytest.mark.parametrize('axis',[0,1,2])
def test_replacing_faces_and_clearing_overrides_does_not_reuse_previous_operator(axis):
    sim,x,faces,expected=stack(axis);first=sim.solve()
    np.testing.assert_allclose(first['phi'],expected,rtol=1e-9,atol=2e-12)
    empty=np.array([],dtype=float);sim.set_edge_permittivity(*[empty]*6)
    second=sim.solve();assert second['converged']
    np.testing.assert_allclose(second['phi'],.2*x/x[-1],rtol=1e-9,atol=2e-12)
    assert np.max(abs(second['phi']-first['phi']))>.02


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('side',[0,1])
def test_invalid_face_update_preserves_the_configured_operator(axis,side):
    sim,x,faces,expected=stack(axis)
    arrays=[np.array([],dtype=float) for _ in range(6)]
    arrays[2*axis+side]=np.ones(8)
    with pytest.raises(ValueError,match='size mismatch'): sim.set_edge_permittivity(*arrays)
    state=sim.solve();assert state['converged']
    np.testing.assert_allclose(state['phi'],expected,rtol=1e-9,atol=2e-12)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('path',['gummel','hybrid','newton'])
def test_charged_interfaces_match_independent_finite_volume_matrix(axis,path):
    sim,x,faces,_=stack(axis,path)
    doping=1e21*np.array([0.,1.,2.,3.,4.,0.,0.,0.,0.])
    fraction=np.array([1.,1.,1.,1.,.5,0.,0.,0.,0.])
    sim.set_doping(doping);sim.set_charge_volume_fraction(fraction)
    matrix=np.zeros((9,9));rhs=np.zeros(9)
    matrix[0,0]=matrix[-1,-1]=1.;rhs[-1]=.2
    for i in range(1,8):
        left=faces[i-1]/(x[i]-x[i-1]);right=faces[i]/(x[i+1]-x[i])
        matrix[i,i]=left+right;matrix[i,i-1]=-left;matrix[i,i+1]=-right
        rhs[i]=float(native_constants()['elementary_charge_C'])*doping[i]*fraction[i]*(x[i+1]-x[i-1])/2
    expected=np.linalg.solve(matrix,rhs)
    state=sim.solve();assert state['converged']
    np.testing.assert_allclose(state['phi'],expected,rtol=1e-8,atol=2e-11)
