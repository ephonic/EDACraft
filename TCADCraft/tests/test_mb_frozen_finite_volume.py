from copy import deepcopy
from dataclasses import replace,asdict
from decimal import Decimal,localcontext
import hashlib,json
import pytest
from tests.test_mb_expanded_flat_face import pair,GEOMETRY
from tcad.solver.boltzmann_frozen_finite_volume import advance_mb_frozen_finite_volume as advance
from tcad.postprocess.boltzmann_frozen_finite_volume import audit_mb_frozen_finite_volume as audit

DT=1e-18
INTERNAL=dict(owner=0,neighbor=1,geometry=GEOMETRY)


def hash_state(s):return hashlib.sha256(json.dumps(asdict(s),sort_keys=True,separators=(',',':')).encode()).hexdigest()


@pytest.mark.parametrize('mode',['closed','contact','mixed','unequal_volume','isolated'])
def test_actual_frozen_fv_update_closes_submitted_particle_and_total_energy(mode):
    _,a,b=pair();states=(a,b);faces=[INTERNAL]
    if mode=='contact':faces=[dict(owner=0,reservoir=b,geometry=(1e-14,1e-8,0.,.1,.2))]
    if mode=='mixed':faces.append(dict(owner=1,reservoir=a,geometry=(1e-14,1e-8,0.,.1,.2)))
    if mode=='unequal_volume':states=(a,replace(b,frame=(*b.frame[:4],'3e-20',*b.frame[5:])))
    if mode=='isolated':faces=[]
    saved=deepcopy(states);new,r=advance(states,faces,DT)
    assert states==saved and all(s.time_s==DT for s in new)
    assert r['independent_audit']['valid'] and r['independent_audit']['global_particle_energy_closed']
    assert not r['complete_device_energy'] and not r['repeat_transport_supported']
    if mode in ('closed','unequal_volume'):
        assert all(Decimal(x)==0 for x in r['independent_audit']['outward_contact_transfers'])
    if mode=='isolated':assert all(not s.electron_density_change and not s.electron_energy_density_change for s in new)


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
@pytest.mark.parametrize('background',[False,True])
def test_micro_density_and_energy_changes_remain_authoritative(tail,background):
    _,a,b=pair();b=a if background else replace(a,electron_excess=('0',),hole_excess=('0',))
    a=replace(b,electron_excess=(*b.electron_excess,tail),hole_excess=(*b.hole_excess,tail))
    new,r=advance((a,b),[INTERNAL],DT)
    with localcontext() as ctx:
        ctx.prec=10000
        for state in new:
            for field in ('electron_density_change','hole_density_change','electron_energy_density_change','hole_energy_density_change'):
                assert sum(map(Decimal,getattr(state,field)))!=0
            assert float(Decimal(state.anchor.frame[0])+sum(map(Decimal,state.electron_density_change)))==float(state.anchor.frame[0])
    assert r['independent_audit']['valid']


def test_large_band_particle_energy_transfers_and_tiny_tail_coexist():
    _,a,b=pair();a=replace(a,frame=(*a.frame[:5],'1e-17','-1e-17',*a.frame[7:]),electron_excess=(*a.electron_excess,'1e-1863'))
    b=replace(b,frame=(*b.frame[:5],'1e-17','-1e-17',*b.frame[7:]))
    new,r=advance((a,b),[INTERNAL],DT)
    assert r['independent_audit']['valid']
    assert any(abs(Decimal(x))<Decimal('1e-1800') for x in new[0].electron_energy_density_change)


@pytest.mark.parametrize('damage',['particle','energy','anchor','clock','face_integral','face_moment','topology','metadata','temperature'])
def test_coherently_rehashed_saved_fv_forgery_is_rejected(damage):
    _,a,b=pair();new,r=advance((a,b),[INTERNAL],DT);new=list(new);r=deepcopy(r)
    if damage=='particle':new[0]=replace(new[0],electron_density_change=())
    if damage=='energy':new[0]=replace(new[0],electron_energy_density_change=())
    if damage=='anchor':new[0]=replace(new[0],anchor=replace(a,electron_excess=('0',)))
    if damage=='clock':new[0]=replace(new[0],time_s=2*DT)
    if damage=='face_integral':r['transfers'][0]['integrated'][0]=[]
    if damage=='face_moment':r['transfers'][0]['moment']['carriers'][0]['number_expansion']=[]
    if damage=='topology':r['transfers'][0]['neighbor']=None
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='temperature':r['cells'][0]['temperatures_K'][1]='300'
    r['new_sha256']=[hash_state(s) for s in new]
    try:result=audit((a,b),new,r,faces=[INTERNAL],dt_s=DT)
    except ValueError:return
    assert not result['valid']


def test_deleting_quotient_low_part_rejects_even_inside_physical_budget():
    _,a,b=pair();new,r=advance((a,b),[INTERNAL],DT);new=list(new)
    values=list(new[0].electron_density_change);assert len(values)>1
    # Quotient entries alternate high and nonzero residual correction for this fixture.
    del values[1];new[0]=replace(new[0],electron_density_change=tuple(values))
    r=deepcopy(r);r['new_sha256']=[hash_state(s) for s in new]
    result=audit((a,b),new,r,faces=[INTERNAL],dt_s=DT)
    assert not result['valid'] and not result['cells'][0]['quotients_binary_exact']


def test_saved_replay_uses_no_native_or_production_solver(monkeypatch):
    _,a,b=pair();new,r=advance((a,b),[INTERNAL],DT)
    import tcad.core._bindings as native
    def deny(*args,**kwargs):raise AssertionError('native physics invoked during independent saved audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr('tcad.solver.boltzmann_frozen_finite_volume.advance_mb_frozen_finite_volume',deny)
    monkeypatch.setattr('tcad.physics.boltzmann_expanded_flat_face.expanded_mb_flat_face',deny)
    assert audit((a,b),new,r,faces=[INTERNAL],dt_s=DT)['valid']


@pytest.mark.parametrize('damage',['duplicate','self','owner_bool','negative_dt','huge_dt','asynchronous','repeat','clock_resolution'])
def test_unsupported_fv_problem_rejects_atomically(damage):
    _,a,b=pair();states=(a,b);faces=[INTERNAL];dt=DT
    if damage=='duplicate':faces=[INTERNAL,dict(owner=1,neighbor=0,geometry=GEOMETRY)]
    if damage=='self':faces=[dict(owner=0,neighbor=0,geometry=GEOMETRY)]
    if damage=='owner_bool':faces=[dict(owner=False,neighbor=1,geometry=GEOMETRY)]
    if damage=='negative_dt':dt=-DT
    if damage=='huge_dt':dt=1.
    if damage=='asynchronous':states=(a,replace(b,time_s=DT))
    if damage=='repeat':states=advance(states,faces,dt)[0]
    if damage=='clock_resolution':states=(replace(a,time_s=1.),replace(b,time_s=1.))
    saved=deepcopy(states)
    with pytest.raises(ValueError):advance(states,faces,dt)
    assert states==saved
