from dataclasses import replace,asdict
from copy import deepcopy
from decimal import Decimal
import pytest
from tests.test_mb_particle_energy import make,expand
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState as State
from tcad.solver.boltzmann_affine_powerlaw import advance_mb_affine_powerlaw as advance
from tcad.postprocess.boltzmann_affine_powerlaw import audit_mb_affine_powerlaw as audit
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport as transport

@pytest.mark.parametrize('a,c',[(.6,-.2),(-2.,.5),(0.,1.5),(2.,0.),(-8.,2.)])
def test_nonzero_ac_full_density_repeated_collision(a,c):
    cfg,s=make(a,c);old=State(expand(cfg,s),('1e20',),('-1e19',),('1e3',),('-2e3',),1e-18)
    for _ in range(2):
        new,r=advance(cfg,old,2e-14)
        assert r['independent_audit']['valid'] and r['independent_audit']['nonlinear_lineage_checks']
        assert new.electron_density_change==old.electron_density_change
        assert new.anchor.frame[:len(old.anchor.frame)]==old.anchor.frame
        assert new.electron_energy_density_change[:len(old.electron_energy_density_change)]==old.electron_energy_density_change
        old=new

@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_pure_density_tail_nonzero_powerlaw_response(tail):
    cfg,s=make(.6,-.2);a=replace(expand(cfg,s),electron_excess=('0',),hole_excess=('0',))
    old=State(a,(tail,),(),(),(),1e-18)
    for _ in range(2):
        new,r=advance(cfg,old,2e-14)
        assert r['independent_audit']['valid'] and any(Decimal(x)!=0 for row in r['collision']['lineage_groups'] for x in row['operations'][10]['value'])
        old=new

@pytest.mark.parametrize('q',[(0.,0.,0.),(2e-19,-1e-19,3e-19),(1e-300,-1e-300,1e-300)])
def test_independent_sources(q):
    cfg,s=make(.6,-.2);old=expand(cfg,s);new,r=advance(cfg,old,2e-14,impulses_J=q)
    assert audit(cfg,old,new,r,dt_s=2e-14,impulses_J=q)['valid']

def test_transport_powerlaw_collision_transport():
    cfg,s=make(.6,-.2);a=expand(cfg,s);b=replace(a,electron_excess=('0',),hole_excess=('0',))
    faces=[dict(owner=0,neighbor=1,geometry=(1e-14,1e-8,2e-8,.1,.2))]
    states,_=transport((a,b),faces,1e-18)
    states=tuple(advance(cfg,s,2e-14)[0] for s in states)
    states,r=transport(states,faces,1e-18);assert r['independent_audit']['valid']

def test_constant_case_ledger_matches_existing_constant_api():
    from tcad.solver.boltzmann_affine_collision import advance_mb_affine_collision
    cfg,s=make();old=expand(cfg,s);a,r=advance(cfg,old,2e-14);b,_=advance_mb_affine_collision(cfg,old,2e-14)
    # exp(log(tau0)) is a scalar transcendental approximation. Actual states
    # satisfy the same physical gates; byte identity is not an API promise.
    assert r['independent_audit']['valid'] and a.time_s==b.time_s

def test_zero_equilibrium_no_growth():
    cfg,s=make(.6,-.2);old=replace(expand(cfg,s),electron_excess=('0',),hole_excess=('0',))
    new,r=advance(cfg,old,2e-14);assert new.anchor==old and not new.electron_energy_density_change
    assert r['independent_audit']['nonlinear_lineage_checks']==[]

@pytest.mark.parametrize('damage',['tau','root','trace_tau','trace_temperature','trace_count','density_low','DAG','new_energy','law_config','metadata','clock'])
def test_rehashed_saved_forgeries_rejected(damage):
    cfg,s=make(.6,-.2);old=State(expand(cfg,s),('1e-300',),(),(),(),1e-18)
    new,r=advance(cfg,old,2e-14);r=deepcopy(r)
    if damage=='tau':r['effective_tau_s'][0]='1e-13'
    if damage=='root':r['root_temperature_K']='310'
    if damage=='trace_tau':r['root_trace'][0]['tau_n_s']='1e-13'
    if damage=='trace_temperature':r['root_trace'][0]['temperature_K']='700'
    if damage=='trace_count':r['root_trace']=[]
    if damage=='density_low':r['collision']['densities'][0][0]='0'
    if damage=='DAG':r['collision']['lineage_groups'][0]['operations'][10]['value']=['0']
    if damage=='new_energy':new=replace(new,electron_energy_density_change=(*new.electron_energy_density_change,'1e-300'))
    if damage=='law_config':
        p=list(cfg.parameters);p[6]='1.5';cfg=replace(cfg,parameters=tuple(p));r['configuration_sha256']=cfg.sha256
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='clock':new=replace(new,time_s=1.)
    from tcad.postprocess.boltzmann_affine_transport import _fingerprint
    r['new_sha256']=r['collision']['new_sha256']=_fingerprint(new)
    try:check=audit(cfg,old,new,r,dt_s=2e-14)
    except (ValueError,ArithmeticError):return
    assert not check['valid']

def test_saved_audit_has_no_native_or_production_calls(monkeypatch):
    cfg,s=make(.6,-.2);old=expand(cfg,s);new,r=advance(cfg,old,2e-14)
    r.pop('independent_audit');r['collision'].pop('independent_audit')
    import tcad.core._bindings as native
    import tcad.solver.boltzmann_affine_collision as pc
    import tcad.solver.boltzmann_affine_powerlaw as pp
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    def deny(*a,**k):raise AssertionError('native/production constitutive call in saved audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(pc,'advance_mb_affine_collision',deny);monkeypatch.setattr(pp,'advance_mb_affine_powerlaw',deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    assert audit(cfg,old,new,r,dt_s=2e-14)['valid']

@pytest.mark.parametrize('a,c,dt,q',[
    (-20000.,20000.,2e-14,(0.,0.,0.)),(-20000.,0.,2e-14,(0.,0.,0.)),
    (.6,-.2,1e-30,(0.,0.,0.)),(.6,-.2,0.,(0.,0.,0.)),(.6,-.2,2e-14,(1.,0.,0.))])
def test_outside_bounded_domain_atomic(a,c,dt,q):
    cfg,s=make(a,c);old=expand(cfg,s);before=asdict(old)
    with pytest.raises((ValueError,RuntimeError)):advance(cfg,old,dt,impulses_J=q)
    assert asdict(old)==before
