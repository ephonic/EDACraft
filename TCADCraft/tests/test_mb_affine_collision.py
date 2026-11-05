from dataclasses import replace,asdict
from copy import deepcopy
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_particle_energy import make,expand
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState as State
from tcad.solver.boltzmann_affine_collision import advance_mb_affine_collision as advance
from tcad.postprocess.boltzmann_affine_collision import audit_mb_affine_collision as audit
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport as transport

def initial(tail='1e20'):
    cfg,s=make();a=expand(cfg,s)
    return cfg,State(a,(tail,),('-1e19',),('1e3',),('-2e3',),1e-18)

@pytest.mark.parametrize('tail',['1e20','-1e20','1e-300','-1e-300'])
def test_full_density_collision_repeated_and_physical_closure(tail):
    cfg,old=initial(tail)
    for _ in range(2):
        new,r=advance(cfg,old,2e-14)
        assert r['independent_audit']['valid'] and new.electron_density_change==old.electron_density_change
        assert new.anchor.frame[:len(old.anchor.frame)]==old.anchor.frame
        assert new.electron_energy_density_change[:len(old.electron_energy_density_change)]==old.electron_energy_density_change
        old=new

@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_pure_density_microscopic_response_survives_scalar_resolution(tail):
    cfg,s=make();a=replace(expand(cfg,s),electron_excess=('0',),hole_excess=('0',))
    old=State(a,(tail,),(),(),(),1e-18);new,r=advance(cfg,old,2e-14)
    assert r['independent_audit']['valid'] and r['lineage_groups']
    assert any(Decimal(v)!=0 for row in r['lineage_groups'] for v in row['operations'][10]['value'])
    assert new.electron_density_change==(tail,)

@pytest.mark.parametrize('q',[(0.,0.,0.),(2e-19,-1e-19,3e-19),(1e-300,-1e-300,1e-300)])
def test_independent_sources_and_lossless_original_input(q):
    cfg,s=make();old=expand(cfg,s);new,r=advance(cfg,old,2e-14,impulses_J=q)
    assert r['independent_audit']['valid'] and audit(cfg,old,new,r,dt_s=2e-14,impulses_J=q)['valid']

def test_transport_collision_transport_with_distinct_evolving_lattices():
    cfg,s=make();a=expand(cfg,s);b=replace(a,electron_excess=('0',),hole_excess=('0',))
    states,_=transport((a,b),[dict(owner=0,neighbor=1,geometry=(1e-14,1e-8,2e-8,.1,.2))],1e-18)
    collided=tuple(advance(cfg,s,2e-14)[0] for s in states)
    states,r=transport(collided,[dict(owner=0,neighbor=1,geometry=(1e-14,1e-8,2e-8,.1,.2))],1e-18)
    assert r['independent_audit']['valid'] and collided[0].anchor.frame!=collided[1].anchor.frame

def test_zero_equilibrium_exact_zero_no_lattice_growth():
    cfg,s=make();old=replace(expand(cfg,s),electron_excess=('0',),hole_excess=('0',));new,r=advance(cfg,old,2e-14)
    assert new.anchor==old and new.electron_energy_density_change==() and new.hole_energy_density_change==()
    assert Decimal(r['independent_audit']['global_energy_budget_J'])==0

@pytest.mark.parametrize('damage',['density_low','delta_low','quotient','D','dag','exchange','lattice','energy','anchor','prefix','clock','source','metadata','view'])
def test_rehashed_saved_forgeries_rejected(damage):
    cfg,old=initial('1e-300');new,r=advance(cfg,old,2e-14);r=deepcopy(r)
    if damage=='density_low':r['densities'][0][0]='0'
    if damage=='delta_low':r['excess'][0][0]='0'
    if damage=='quotient':r['lattice_quotients'][0]='0'
    if damage=='D':r['denominator'][-1]='1'
    if damage=='dag':r['lineage_groups'][0]['operations'][1]['value']=['0']
    if damage=='exchange':r['lineage_groups'][0]['operations'][10]['value']=['0']
    if damage=='lattice':new=replace(new,anchor=replace(new.anchor,frame=(*new.anchor.frame,'1e-300')))
    if damage=='energy':new=replace(new,electron_energy_density_change=(*new.electron_energy_density_change,'1e-300'))
    if damage=='anchor':new=replace(new,anchor=replace(new.anchor,electron_excess=('0',)))
    if damage=='prefix':new=replace(new,electron_density_change=('1e-299',))
    if damage=='clock':new=replace(new,time_s=1.)
    if damage=='source':r['impulses_J'][0]='1e-100'
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='view':r['temperatures_K'][1]='650'
    from tcad.postprocess.boltzmann_affine_transport import _fingerprint
    r['new_sha256']=_fingerprint(new)
    try:result=audit(cfg,old,new,r,dt_s=2e-14)
    except ValueError:return
    assert not result['valid']

def test_saved_audit_denies_native_production_and_law(monkeypatch):
    cfg,old=initial();new,r=advance(cfg,old,2e-14)
    import tcad.core._bindings as native
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    import tcad.solver.boltzmann_affine_collision as production
    def deny(*a,**k):raise AssertionError('production/native physics in audit')
    for k in dir(native):
        if k.startswith(('native_','three_temperature_')) and callable(getattr(native,k)):monkeypatch.setattr(native,k,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny);monkeypatch.setattr(production,'advance_mb_affine_collision',deny)
    assert audit(cfg,old,new,r,dt_s=2e-14)['valid']

@pytest.mark.parametrize('a,c',[(.6,0.),(0.,-.2),(-20000.,20000.)])
def test_nonconstant_law_explicitly_rejected(a,c):
    cfg,s=make(a,c)
    with pytest.raises(ValueError,match='constant tau'):advance(cfg,expand(cfg,s),2e-14)

@pytest.mark.parametrize('dt,q',[(0.,(0.,0.,0.)),(2e-14,(1.,0.,0.))])
def test_failure_atomic(dt,q):
    cfg,old=initial();before=asdict(old)
    with pytest.raises((ValueError,RuntimeError)):advance(cfg,old,dt,impulses_J=q)
    assert asdict(old)==before
