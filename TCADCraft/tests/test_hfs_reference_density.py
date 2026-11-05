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


from test_hfs_contact_policy import bar as parent_bar, contacts
REFS=[(5e18,0.),(0.,8e18),(5e18,8e18)]
def bar(axis=0,primary=False,driving=0,ii=False,policy=None,layout='ends',refs=None):
    sim=parent_bar(axis,primary,driving,ii,policy,layout)
    if refs is not None:sim.set_high_field_reference_density(*refs)
    return sim

def reference(phi,n,p,driving,policy,layout,refs):
    delta=np.diff(phi)/VT
    bp=delta/np.expm1(delta);bm=-delta/np.expm1(-delta)
    diffusion=[]
    for carrier,mu,vsat,beta,sign,bc,ref in [
        (n,.1,5e4,2.,-1.,contacts(layout)[0],refs[0]),
        (p,.05,4e4,1.,1.,contacts(layout)[1],refs[1])]:
        force=np.abs(np.diff(phi+sign*VT*np.log(np.maximum(carrier+ref,1.)/1e19)))/H
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


@pytest.mark.parametrize('refs',REFS)
@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('policy',[False,True])
@pytest.mark.parametrize('driving',[0,1])
@pytest.mark.parametrize('ii',[False,True])
@pytest.mark.parametrize('layout',['ends','asymmetric','potential_only'])
def test_currents_source_and_gummel_audit(axis,policy,driving,ii,layout,refs):
    # Zero-budget Gummel polishes single-contact chains toward equilibrium.
    # Exporting that state as float64 loses the tiny SG current to cancellation.
    # Keep asymmetric edges measurably out of equilibrium with one Newton step.
    r=bar(axis,primary=layout=='asymmetric',driving=driving,ii=ii,policy=policy,layout=layout,refs=refs).solve()
    assert not r['converged']
    jn,jp,dn,dp,bp,bm,g=reference(r['phi'],r['n'],r['p'],driving,policy,layout,refs)
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


@pytest.mark.parametrize('refs',REFS)
@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('policy',[False,True])
@pytest.mark.parametrize('driving',[0,1])
@pytest.mark.parametrize('ii',[False,True])
def test_initial_newton_residual(axis,policy,driving,ii,refs):
    r=bar(axis,True,driving,ii,policy,refs=refs).solve();stage,=r['nonlinear_history']
    assert stage['solver']=='newton' and len(stage['raw_n_l2'])==1
    jn,jp,*_,g=reference(PHI,N,P,driving,policy,'ends',refs)
    q=float(native_constants()['elementary_charge_C'])
    for j,name,sign in [(jn,'n',-1.),(jp,'p',1.)]:
        residual=sign*np.diff(j)/q-(g[1:-1]*H if ii else 0.)
        assert stage['raw_'+name+'_l2'][0]==pytest.approx(np.linalg.norm(residual),rel=2e-12)



@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('slot',[0,1])
@pytest.mark.parametrize('bad',[-1.,np.nan,np.inf,-np.inf])
def test_invalid_reference_pair_is_atomic(public,slot,bad):
    owner,sim=resistor(public=public);_,pristine=resistor()
    api=owner if public else sim
    assert api.get_high_field_reference_density()==(0.,0.)
    api.set_high_field_reference_density(2.,3.)
    pristine.set_high_field_reference_density(2.,3.)
    before=repr(owner.configuration_snapshot()) if public else None
    pair=[5.,7.];pair[slot]=bad
    with pytest.raises(ValueError,match='finite and nonnegative'):api.set_high_field_reference_density(*pair)
    assert api.get_high_field_reference_density()==(2.,3.)
    if public:assert repr(owner.configuration_snapshot())==before
    same_solution(pristine,sim)

def test_public_configuration_replays_reference_pair():
    a,_=resistor(public=True);b,_=resistor(public=True)
    a.set_high_field_reference_density(5e18,8e18)
    recipe=a.configuration_snapshot()[-1]
    assert recipe==('python','set_high_field_reference_density',{'n0':5e18,'p0':8e18})
    getattr(b,recipe[1])(**recipe[2]);assert b.get_high_field_reference_density()==(5e18,8e18)
    same_solution(a._sim,b._sim)

@pytest.mark.parametrize('axis,primary,driving,ii',DEFAULT_CASES)
def test_default_and_explicit_zero_preserve_parent(axis,primary,driving,ii):
    with open(os.environ['TCAD_HFS_REFERENCE_ORACLE'],encoding='utf8') as f:
        expected=json.load(f)['cases'][str((axis,primary,driving,ii))]
    for refs in [None,(0.,0.)]:
        assert thin_result(bar(axis,primary,driving,ii,refs=refs).solve())==expected

@pytest.mark.parametrize('primary',[False,True])
@pytest.mark.parametrize('change',['quantum','ferro','thermal','statistics','mobility','dos','bandgap','variable_mobility'])
def test_unsupported_reference_scope_rejected_before_solve(primary,change):
    sim=bar(primary=primary,refs=REFS[-1])
    if change=='quantum':sim.set_quantum_enabled(True)
    elif change=='ferro':sim.set_ferroelectric_enabled(True)
    elif change=='thermal':sim.set_thermal_coupling_enabled(True)
    elif change=='statistics':sim.set_statistics_type(1)
    elif change=='mobility':sim.set_mobility_model(1)
    elif change=='dos':sim.set_effective_dos(np.array([1,1,2,1,1.])*1e19,np.full(5,1e19))
    elif change=='bandgap':sim.set_bandgap(np.array([6,6,5,6,6.]))
    else:sim.set_mobility(np.array([.1,.1,.2,.1,.1]),np.full(5,.05))
    with pytest.raises(ValueError,match='nonzero HFS RefDens'):sim.solve()

@pytest.mark.parametrize('shape',[(1,1,1),(3,3,1),(3,3,3)])
def test_reference_geometry_guard(shape):
    sim=PyDeviceSimulator(*shape,H,H,H)
    sim.set_high_field_saturation(True,5e4,4e4,2.,1.,0)
    sim.set_high_field_reference_density(*REFS[-1])
    with pytest.raises(ValueError,match='one-dimensional'):sim.solve()

@pytest.mark.parametrize('driving,enabled',[(0,False),(1,False),(1,True)])
def test_inactive_references_leave_electric_or_disabled_transport_exact(driving,enabled):
    a=bar(driving=driving);b=bar(driving=driving,refs=REFS[-1])
    for sim in [a,b]:sim.set_high_field_saturation(enabled,5e4,4e4,2.,1.,driving)
    assert thin_result(a.solve())==thin_result(b.solve())
