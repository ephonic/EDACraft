"""Independent II driving forces, SG source and Newton alpha derivatives."""
import json
import os
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator,native_constants
from test_hfs_contact_policy import bar as parent_bar,DEFAULT_CASES,PHI,N,P,H,VT
from test_hfs_reference_density import reference as hfs_reference
from test_transport_parameter_guard import resistor,same_solution
from test_ii_field_floor import thin_result

REFS=[(0.,0.),(5e18,0.),(0.,8e18),(5e18,8e18)]
# enabled, HFS driving, HFS contact policy. II driving is independent of all three.
HFS=[(False,0,True),(True,1,True),(True,0,True),(True,0,False)]
HFREF=(3e18,4e18)
FLOORS=[1e5,3.3e5]
BAD_MODES=[-1,2,1.,True,np.bool_(False),'1',None,1+0j,np.nan,np.inf,2**128]

def bar(axis=0,primary=False,refs=(0.,0.),hfs=HFS[2],layout='ends',floor=1e5,mode=1):
    enabled,driving,policy=hfs
    sim=parent_bar(axis,primary,driving,True,policy,layout)
    sim.set_high_field_saturation(enabled,5e4,4e4,2.,1.,driving)
    sim.set_high_field_reference_density(*HFREF)
    sim.set_ii_driving(mode);sim.set_ii_reference_density(*refs);sim.set_ii_field_floor(floor)
    return sim

def reference(phi,n,p,refs,hfs,layout,floor):
    enabled,driving,policy=hfs
    if enabled:
        jn,jp,dn,dp,bp,bm,_=hfs_reference(phi,n,p,driving,policy,layout,HFREF)
    else:
        delta=np.diff(phi)/VT;bp=delta/np.expm1(delta);bm=-delta/np.expm1(-delta)
        dn=np.full(4,.1*VT/H);dp=np.full(4,.05*VT/H)
        q=float(native_constants()['elementary_charge_C'])
        jn=q*dn*(n[1:]*bp-n[:-1]*bm);jp=q*dp*(p[:-1]*bp-p[1:]*bm)
    q=float(native_constants()['elementary_charge_C']);edge=np.zeros(4)
    for c,ref,sign,a,b,current in [(n,refs[0],-1.,1e5,2e5,jn),(p,refs[1],1.,2e5,3e5,jp)]:
        force=np.abs(np.diff(phi)+sign*VT*np.diff(np.log(np.maximum(c+ref,1e-300))))/H
        alpha=np.zeros(4);active=force>=floor;alpha[active]=a*np.exp(-b/force[active])
        edge+=alpha*np.abs(current)/q
    g=np.zeros(5);g[:-1]+=.5*edge;g[1:]+=.5*edge
    return jn,jp,dn,dp,bp,bm,g

@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('refs',REFS)
@pytest.mark.parametrize('hfs',HFS)
@pytest.mark.parametrize('layout',['ends','asymmetric'])
@pytest.mark.parametrize('floor',FLOORS)
def test_gqf_source_currents_and_audit(axis,refs,hfs,layout,floor):
    r=bar(axis,layout=='asymmetric',refs,hfs,layout,floor).solve();assert not r['converged']
    jn,jp,dn,dp,bp,bm,g=reference(r['phi'],r['n'],r['p'],refs,hfs,layout,floor)
    np.testing.assert_allclose(r['Jn_'+'xyz'[axis]][:-1],jn,rtol=5e-13,atol=0.)
    np.testing.assert_allclose(r['Jp_'+'xyz'[axis]][:-1],jp,rtol=5e-13,atol=0.)
    np.testing.assert_allclose(r['G_ii'],g,rtol=5e-13,atol=0.)
    if layout=='ends':
        audit=r['steady_equation_audit'];assert audit['available']
        for c,d,plus,minus,name in [(r['n'],dn,bm,bp,'electron'),(r['p'],dp,bp,bm,'hole')]:
            diagonal=(d[:-1]*minus[:-1]+d[1:]*plus[1:])*c[1:-1]
            neighbors=d[:-1]*plus[:-1]*c[:-2]+d[1:]*minus[1:]*c[2:];rhs=g[1:-1]*H
            backward=np.max(np.abs(diagonal-neighbors-rhs)/(np.abs(diagonal)+np.abs(neighbors)+np.abs(rhs)))
            assert audit[name+'_backward_error_linf']==pytest.approx(backward,rel=2e-11,abs=2e-15)

@pytest.mark.parametrize('axis',[0,1,2])
@pytest.mark.parametrize('refs',REFS)
@pytest.mark.parametrize('hfs',HFS)
@pytest.mark.parametrize('floor',FLOORS)
def test_initial_gqf_newton_residual(axis,refs,hfs,floor):
    r=bar(axis,True,refs,hfs,floor=floor).solve();stage,=r['nonlinear_history']
    assert stage['solver']=='newton' and len(stage['raw_n_l2'])==1
    jn,jp,*_,g=reference(PHI,N,P,refs,hfs,'ends',floor)
    q=float(native_constants()['elementary_charge_C'])
    for j,name,sign in [(jn,'n',-1.),(jp,'p',1.)]:
        assert stage['raw_'+name+'_l2'][0]==pytest.approx(np.linalg.norm(sign*np.diff(j)/q-g[1:-1]*H),rel=2e-12)

@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('slot',[0,1])
@pytest.mark.parametrize('bad',[-1.,np.nan,np.inf,-np.inf])
def test_invalid_reference_pair_is_atomic(public,slot,bad):
    owner,sim=resistor(public=public);_,pristine=resistor();api=owner if public else sim
    assert api.get_ii_reference_density()==(0.,0.)
    api.set_ii_reference_density(2.,3.);pristine.set_ii_reference_density(2.,3.)
    before=repr(owner.configuration_snapshot()) if public else None
    pair=[5.,7.];pair[slot]=bad
    with pytest.raises(ValueError,match='finite and nonnegative'):api.set_ii_reference_density(*pair)
    assert api.get_ii_reference_density()==(2.,3.)
    if public:assert repr(owner.configuration_snapshot())==before
    same_solution(pristine,sim)

@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('bad',BAD_MODES)
def test_invalid_driving_is_atomic(public,bad):
    owner,sim=resistor(public=public);_,pristine=resistor();api=owner if public else sim
    api.set_ii_driving(1);pristine.set_ii_driving(1)
    before=repr(owner.configuration_snapshot()) if public else None
    with pytest.raises(ValueError,match='must be integer'):api.set_ii_driving(bad)
    assert api.get_ii_driving()==1
    if public:assert repr(owner.configuration_snapshot())==before
    same_solution(pristine,sim)

@pytest.mark.parametrize('public',[False,True])
@pytest.mark.parametrize('mode',[0,1,np.int64(0),np.int64(1)])
def test_driving_integer_values_and_default(public,mode):
    owner,sim=resistor(public=public);api=owner if public else sim
    assert api.get_ii_driving()==0
    api.set_ii_driving(mode);assert api.get_ii_driving()==mode

def test_public_configuration_replays_both_ii_controls():
    a,_=resistor(public=True);b,_=resistor(public=True)
    a.set_ii_driving(1);a.set_ii_reference_density(5e18,8e18)
    recipes=a.configuration_snapshot()[-2:]
    assert recipes==[('python','set_ii_driving',{'driving':1}),('python','set_ii_reference_density',{'n0':5e18,'p0':8e18})]
    for recipe in recipes:getattr(b,recipe[1])(**recipe[2])
    assert b.get_ii_driving()==1 and b.get_ii_reference_density()==(5e18,8e18)
    same_solution(a._sim,b._sim)

@pytest.mark.parametrize('axis,primary,driving,ii',DEFAULT_CASES)
def test_default_and_explicit_field_zero_preserve_parent(axis,primary,driving,ii):
    with open(os.environ['TCAD_II_DRIVING_ORACLE'],encoding='utf8') as f:expected=json.load(f)['cases'][str((axis,primary,driving,ii))]
    for explicit in [False,True]:
        sim=parent_bar(axis,primary,driving,ii)
        if explicit:sim.set_ii_driving(0);sim.set_ii_reference_density(0.,0.)
        assert thin_result(sim.solve())==expected

@pytest.mark.parametrize('refs',REFS[1:])
@pytest.mark.parametrize('hfs',HFS)
def test_electric_field_ignores_references(refs,hfs):
    assert thin_result(bar(refs=refs,hfs=hfs,mode=0).solve())==thin_result(bar(hfs=hfs,mode=0).solve())

@pytest.mark.parametrize('refs',REFS)
@pytest.mark.parametrize('hfs',HFS)
def test_disabled_ii_ignores_driving_and_references(refs,hfs):
    a=bar(refs=refs,hfs=hfs);b=bar(hfs=hfs,mode=0)
    for sim in [a,b]:sim.set_ii_enabled(False)
    assert thin_result(a.solve())==thin_result(b.solve())

@pytest.mark.parametrize('primary',[False,True])
@pytest.mark.parametrize('change',['quantum','ferro','thermal','statistics','mobility','dos','bandgap','variable_mobility'])
def test_unsupported_gqf_scope_rejected(primary,change):
    sim=bar(primary=primary,hfs=HFS[0])
    if change=='quantum':sim.set_quantum_enabled(True)
    elif change=='ferro':sim.set_ferroelectric_enabled(True)
    elif change=='thermal':sim.set_thermal_coupling_enabled(True)
    elif change=='statistics':sim.set_statistics_type(1)
    elif change=='mobility':sim.set_mobility_model(1)
    elif change=='dos':sim.set_effective_dos(np.array([1,1,2,1,1.])*1e19,np.full(5,1e19))
    elif change=='bandgap':sim.set_bandgap(np.array([6,6,5,6,6.]))
    else:sim.set_mobility(np.array([.1,.1,.2,.1,.1]),np.full(5,.05))
    with pytest.raises(ValueError,match='II GradQuasiFermi'):sim.solve()

@pytest.mark.parametrize('shape',[(1,1,1),(3,3,1),(3,3,3)])
def test_gqf_geometry_guard(shape):
    sim=PyDeviceSimulator(*shape,H,H,H);sim.set_ii_enabled(True);sim.set_ii_driving(1)
    with pytest.raises(ValueError,match='II GradQuasiFermi'):sim.solve()

@pytest.mark.parametrize('mode',[0,1])
@pytest.mark.parametrize('refs',[REFS[0],REFS[-1]])
def test_transient_avalanche_remains_explicitly_unsupported(mode,refs):
    sim=bar(refs=refs,hfs=HFS[0],mode=mode)
    with pytest.raises(ValueError,match='transient currently supports'):sim.solve_transient()

@pytest.mark.parametrize('above',[False,True])
@pytest.mark.parametrize('carrier',['n','p'])
@pytest.mark.parametrize('ref',[0.,1e19])
def test_zero_electric_field_can_have_gqf_avalanche(above,carrier,ref):
    sim=bar(hfs=HFS[0],refs=(ref,ref));force=1e5*(1.1 if above else .9)
    shifted=2e19*np.exp(np.arange(5)*force*H/VT);varying=shifted-ref
    n=varying if carrier=='n' else np.full(5,2e19)
    p=varying if carrier=='p' else np.full(5,2e19)
    phi=np.zeros(5);sim.set_initial_guess(phi,n,p)
    sim.set_dirichlet_potential(dict(enumerate(phi)))
    sim.set_electron_bc(dict(enumerate(n)));sim.set_hole_bc(dict(enumerate(p)))
    r=sim.solve();q=float(native_constants()['elementary_charge_C'])
    current=q*(.1 if carrier=='n' else .05)*VT/H*np.abs(np.diff(varying))
    a,b=(1e5,2e5) if carrier=='n' else (2e5,3e5)
    actualforce=VT*np.abs(np.diff(np.log(varying+ref)))/H
    edge=a*np.exp(-b/actualforce)*current/q if above else np.zeros(4)
    g=np.zeros(5);g[:-1]+=.5*edge;g[1:]+=.5*edge
    np.testing.assert_allclose(r['G_ii'],g,rtol=5e-13,atol=0.)
    assert bool(np.max(r['G_ii'])>0.) is above
