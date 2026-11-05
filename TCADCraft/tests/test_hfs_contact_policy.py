"""Carrier contact HFS selection must agree across every classical operator."""
import json
import os
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants
from test_transport_parameter_guard import resistor, same_solution
from test_ii_field_floor import thin_result

VT=.02585
H=1e-7
PHI=np.array([0.,.025,.07,.13,.205])
N=np.array([2.,2.1,2.2,2.3,2.4])*1e19
P=np.array([1.2,1.25,1.3,1.35,1.4])*1e19
BAD=[0,1,0.,1.,'true',None,[],{},object(),np.nan,np.inf,1+0j]
DEFAULT_CASES=[(axis,primary,driving,ii) for axis in range(3)
               for primary in [False,True] for driving in [0,1] for ii in [False,True]]


def bar(axis=0, primary=False, driving=0, ii=False, policy=None, layout='ends'):
    shape=[1,1,1];shape[axis]=5
    sim=PyDeviceSimulator(*shape,H,H,H)
    sim.set_mobility(np.full(5,.1),np.full(5,.05))
    sim.set_permittivity(np.full(5,11.7*8.854187817e-12))
    sim.set_effective_dos(np.full(5,1e19),np.full(5,1e19))
    sim.set_bandgap(np.full(5,6.))
    sim.set_recombination(np.full(5,1e100),np.full(5,1e100))
    sim.set_dirichlet_potential({0:PHI[0],4:PHI[4]})
    nc,pc=contacts(layout)
    sim.set_electron_bc({i:N[i] for i in nc})
    sim.set_hole_bc({i:P[i] for i in pc})
    sim.set_initial_guess(PHI,N,P)
    sim.set_thermal_voltage(VT)
    sim.set_high_field_saturation(True,5e4,4e4,2.,1.,driving)
    sim.set_ii_params(1e5,2e5,2e5,3e5);sim.set_ii_enabled(ii)
    sim.set_use_newton(primary);sim.set_newton_primary(primary)
    sim.set_gummel_max_iter(1 if primary else 0)
    sim.set_nonlinear_history_enabled(True)
    if policy is not None:sim.set_hfs_quasi_fermi_at_contacts(policy)
    return sim


def contacts(layout):
    return {'ends':({0,4},{0,4}),'asymmetric':({0},{4}),'potential_only':(set(),set())}[layout]


def reference(phi,n,p,driving,policy,layout):
    delta=np.diff(phi)/VT
    bp=delta/np.expm1(delta);bm=-delta/np.expm1(-delta)
    diffusion=[]
    for carrier,mu,vsat,beta,sign,bc in [
        (n,.1,5e4,2.,-1.,contacts(layout)[0]),
        (p,.05,4e4,1.,1.,contacts(layout)[1])]:
        force=np.abs(np.diff(phi+sign*VT*np.log(np.maximum(carrier,1.)/1e19)))/H
        electric=np.abs(np.diff(phi))/H
        select=np.array([driving==1 or (not policy and (i in bc or i+1 in bc)) for i in range(4)])
        force=np.where(select,electric,force)
        diffusion.append(mu*VT/H/(1+(mu*force/vsat)**beta)**(1/beta))
    dn,dp=diffusion;q=float(native_constants()['elementary_charge_C'])
    jn=q*dn*(n[1:]*bp-n[:-1]*bm)
    jp=q*dp*(p[:-1]*bp-p[1:]*bm)
    e=np.abs(np.diff(phi))/H
    edge=(1e5*np.exp(-2e5/e)*np.abs(jn)+2e5*np.exp(-3e5/e)*np.abs(jp))/q
    g=np.zeros(5);g[:-1]+=.5*edge;g[1:]+=.5*edge
    return jn,jp,dn,dp,bp,bm,g


@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('bad',BAD)
def test_invalid_policy_is_atomic(public,bad):
    owner,sim=resistor(public=public);_,pristine=resistor()
    api=owner if public else sim
    api.set_hfs_quasi_fermi_at_contacts(False)
    pristine.set_hfs_quasi_fermi_at_contacts(False)
    before=repr(owner.configuration_snapshot()) if public else None
    with pytest.raises(ValueError,match='must be boolean'):api.set_hfs_quasi_fermi_at_contacts(bad)
    assert api.get_hfs_quasi_fermi_at_contacts() is False
    if public:assert repr(owner.configuration_snapshot())==before
    same_solution(pristine,sim)


@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('value',[True,False,np.bool_(True),np.bool_(False)])
def test_boolean_values_and_default(public,value):
    owner,sim=resistor(public=public);api=owner if public else sim
    assert api.get_hfs_quasi_fermi_at_contacts() is True
    api.set_hfs_quasi_fermi_at_contacts(value)
    assert api.get_hfs_quasi_fermi_at_contacts() is bool(value)


def test_public_configuration_replays_policy():
    a,_=resistor(public=True);b,_=resistor(public=True)
    a.set_hfs_quasi_fermi_at_contacts(False)
    recipe=a.configuration_snapshot()[-1]
    assert recipe==('python','set_hfs_quasi_fermi_at_contacts',{'enabled':False})
    getattr(b,recipe[1])(**recipe[2]);assert b.get_hfs_quasi_fermi_at_contacts() is False
    same_solution(a._sim,b._sim)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('policy',[False,True])
@pytest.mark.parametrize('driving',[0,1])
@pytest.mark.parametrize('ii',[False,True])
@pytest.mark.parametrize('layout',['ends','asymmetric','potential_only'])
def test_currents_source_and_gummel_audit(axis,policy,driving,ii,layout):
    # Zero-budget Gummel polishes single-contact chains toward equilibrium.
    # Exporting that state as float64 loses the tiny SG current to cancellation.
    # Keep asymmetric edges measurably out of equilibrium with one Newton step.
    r=bar(axis,primary=layout=='asymmetric',driving=driving,ii=ii,policy=policy,layout=layout).solve()
    assert not r['converged']
    jn,jp,dn,dp,bp,bm,g=reference(r['phi'],r['n'],r['p'],driving,policy,layout)
    label='xyz'[axis]
    np.testing.assert_allclose(r['Jn_'+label][:-1],jn,rtol=5e-13,atol=0.)
    np.testing.assert_allclose(r['Jp_'+label][:-1],jp,rtol=5e-13,atol=0.)
    if ii:np.testing.assert_allclose(r['G_ii'],g,rtol=5e-13,atol=0.)
    else:np.testing.assert_array_equal(r['G_ii'],np.zeros(5))
    if layout=='ends':
        audit=r['steady_equation_audit'];assert audit['available']
        for c,d,plus,minus,name in [(r['n'],dn,bm,bp,'electron'),(r['p'],dp,bp,bm,'hole')]:
            diagonal=(d[:-1]*minus[:-1]+d[1:]*plus[1:])*c[1:-1]
            neighbors=d[:-1]*plus[:-1]*c[:-2]+d[1:]*minus[1:]*c[2:]
            rhs=g[1:-1]*H if ii else np.zeros(3)
            backward=np.max(np.abs(diagonal-neighbors-rhs)/(np.abs(diagonal)+np.abs(neighbors)+np.abs(rhs)))
            assert audit[name+'_backward_error_linf']==pytest.approx(backward,rel=2e-11,abs=2e-15)


@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('policy',[False,True])
@pytest.mark.parametrize('driving',[0,1])
@pytest.mark.parametrize('ii',[False,True])
def test_initial_newton_residual(axis,policy,driving,ii):
    r=bar(axis,True,driving,ii,policy).solve();stage,=r['nonlinear_history']
    assert stage['solver']=='newton' and len(stage['raw_n_l2'])==1
    jn,jp,*_,g=reference(PHI,N,P,driving,policy,'ends')
    q=float(native_constants()['elementary_charge_C'])
    for j,name,sign in [(jn,'n',-1.),(jp,'p',1.)]:
        residual=sign*np.diff(j)/q-(g[1:-1]*H if ii else 0.)
        assert stage['raw_'+name+'_l2'][0]==pytest.approx(np.linalg.norm(residual),rel=2e-12)


@pytest.mark.parametrize('axis,primary,driving,ii',DEFAULT_CASES)
def test_default_and_explicit_true_preserve_parent(axis,primary,driving,ii):
    with open(os.environ['TCAD_HFS_CONTACT_ORACLE'],encoding='utf8') as f:
        expected=json.load(f)['cases'][str((axis,primary,driving,ii))]
    for policy in [None,True]:
        assert thin_result(bar(axis,primary,driving,ii,policy).solve())==expected
