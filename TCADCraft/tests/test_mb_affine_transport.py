from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_expanded_flat_face import pair,GEOMETRY
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState,FIELDS,_fingerprint,advance_mb_frozen_finite_volume as frozen
from tcad.solver.boltzmann_affine_transport import advance_mb_affine_transport as advance
from tcad.physics.boltzmann_affine_face import affine_mb_flat_face as face
from tcad.physics.boltzmann_expanded_flat_face import expanded_mb_flat_face as old_face
from tcad.postprocess.boltzmann_affine_transport import audit_affine_mb_face as face_audit,audit_mb_affine_transport as audit

DT=1e-18;EDGE=dict(owner=0,neighbor=1,geometry=GEOMETRY)


def total(raw):return sum(map(Decimal,raw),Decimal(0))


@pytest.mark.parametrize('kind,g',[('bulk',GEOMETRY),('contact',(1e-14,1e-8,0.,.1,.2))])
def test_original_endpoint_moments_match_existing_independent_face(kind,g):
    _,a,b=pair();r=face(a,b,g,face_kind=kind);prior=old_face(a,b,g,face_kind=kind)
    with localcontext() as ctx:
        ctx.prec=10000
        for c,p in zip(r['carriers'],prior['carriers']):
            for key in ('number_expansion','energy_expansion'):
                x=total(c[key]);y=total(p[key]);assert abs(x-y)<=Decimal('1e-28')*abs(y)
    assert r['independent_audit']['valid']


def test_previous_frozen_output_now_supplies_the_next_actual_transport_step():
    _,a,b=pair();first,_=frozen((a,b),[EDGE],DT);new,r=advance(first,[EDGE],DT)
    assert r['independent_audit']['valid'] and all(s.time_s==2*DT for s in new)
    for before,after in zip(first,new):
        assert before.anchor==after.anchor
        for key in FIELDS:assert getattr(after,key)[:len(getattr(before,key))]==getattr(before,key)


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_three_actual_steps_recompute_faces_and_conserve_particle_total_energy(mode):
    _,a,b=pair();states=(a,b);moments=[]
    for _ in range(3):
        faces=[EDGE]
        if mode=='contact':faces=[dict(owner=0,reservoir=replace(b,time_s=states[0].time_s),geometry=(1e-14,1e-8,0.,.1,.2))]
        if mode=='mixed':faces.append(dict(owner=1,reservoir=replace(a,time_s=states[0].time_s),geometry=(1e-14,1e-8,0.,.1,.2)))
        before=deepcopy(states);states,r=advance(states,faces,DT)
        assert r['independent_audit']['valid'] and before!=states
        moments.append(r['transfers'][0]['moment']['carriers'][0]['number_expansion'])
    assert moments[0]!=moments[1]!=moments[2]


@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_micro_density_energy_history_survives_two_consecutive_steps(tail):
    _,a,b=pair();b=a;a=replace(a,electron_excess=(*a.electron_excess,tail))
    first,r=advance((a,b),[EDGE],DT);second,rr=advance(first,[EDGE],DT)
    with localcontext() as ctx:
        ctx.prec=10000
        for state in second:
            assert total(state.electron_density_change)!=0 and total(state.electron_energy_density_change)!=0
            assert float(Decimal(state.anchor.frame[0])+total(state.electron_density_change))==float(state.anchor.frame[0])
    assert rr['independent_audit']['valid']


@pytest.mark.parametrize('tail',['1e-300','-1e-300','1e-1863','-1e-1863'])
def test_affine_density_below_scalar_resolution_changes_energy_flux(tail):
    _,a,b=pair();x=MBFiniteVolumeState(a,(tail,),(),(),(),DT);y=replace(a,time_s=DT)
    r=face(x,y,GEOMETRY)
    assert not r['carriers'][0]['number_expansion']
    assert total(r['carriers'][0]['energy_expansion'])!=0
    assert r['independent_audit']['valid']


def test_extreme_tail_continuation_underflow_rejects_atomically():
    _,a,b=pair();b=a;a=replace(a,electron_excess=(*a.electron_excess,'1e-1863'))
    states,_=frozen((a,b),[EDGE],DT);saved=deepcopy(states)
    with pytest.raises(ValueError,match='range|underflow'):advance(states,[EDGE],DT)
    assert states==saved


def test_affine_contact_and_reverse_orientation():
    _,a,b=pair();states,_=advance((a,b),[EDGE],DT)
    f=face(*states,GEOMETRY);g=face(states[1],states[0],(GEOMETRY[0],GEOMETRY[2],GEOMETRY[1],GEOMETRY[4],GEOMETRY[3]))
    with localcontext() as ctx:
        ctx.prec=10000
        for k in range(2):
            for key in ('number_expansion','energy_expansion'):
                x=total(f['carriers'][k][key]);y=total(g['carriers'][k][key]);assert abs(x+y)<=Decimal('1e-28')*abs(x)


@pytest.mark.parametrize('damage',['normalization','inverse','low_correction','DAG','number','energy','metadata','fingerprint'])
def test_coherent_saved_face_forgery_rejected(damage):
    _,a,b=pair();states,_=advance((a,b),[EDGE],DT);r=deepcopy(face(*states,GEOMETRY));c=r['carriers'][0]
    if damage=='normalization':c['normalization'][0]=c['normalization'][0][-1:]
    if damage=='inverse':c['coefficients'][3]='1'
    if damage=='low_correction':
        assert c['operations'][8]['value'];c['operations'][8]['value']=[]
    if damage=='DAG':c['operations'][3]['value'].append('1e-300')
    if damage=='number':c['number_expansion']=[]
    if damage=='energy':c['energy_expansion']=[]
    if damage=='metadata':r['complete_device_energy']=True
    if damage=='fingerprint':r['owner_sha256']='0'*64
    try:check=face_audit(*states,r,geometry=GEOMETRY)
    except ValueError:return
    assert not check['valid']


@pytest.mark.parametrize('damage',['prefix','particle','energy','clock','topology','temperature'])
def test_second_step_state_forgery_is_rejected_with_recomputed_fingerprints(damage):
    _,a,b=pair();states,_=advance((a,b),[EDGE],DT);new,r=advance(states,[EDGE],DT);new=list(new);r=deepcopy(r)
    if damage=='prefix':new[0]=replace(new[0],electron_density_change=new[0].electron_density_change[1:])
    if damage=='particle':new[0]=replace(new[0],electron_density_change=states[0].electron_density_change)
    if damage=='energy':new[0]=replace(new[0],electron_energy_density_change=states[0].electron_energy_density_change)
    if damage=='clock':new[0]=replace(new[0],time_s=3*DT)
    if damage=='topology':r['transfers'][0]['neighbor']=None
    if damage=='temperature':r['cells'][0]['temperatures_K'][1]='300'
    r['new_sha256']=list(map(_fingerprint,new))
    try:check=audit(states,new,r,faces=[EDGE],dt_s=DT)
    except ValueError:return
    assert not check['valid']


def test_saved_second_step_audits_use_no_native_physics_or_production_laws(monkeypatch):
    _,a,b=pair();first,_=advance((a,b),[EDGE],DT);new,r=advance(first,[EDGE],DT)
    import tcad.core._bindings as native
    def deny(*args,**kwargs):raise AssertionError('native/production physics invoked during independent affine audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr('tcad.physics.boltzmann_affine_face.affine_mb_flat_face',deny)
    monkeypatch.setattr('tcad.solver.boltzmann_affine_transport.advance_mb_affine_transport',deny)
    assert audit(first,new,r,faces=[EDGE],dt_s=DT)['valid']


@pytest.mark.parametrize('damage',['lattice','asynchronous','duplicate','invalid_dt','density_domain'])
def test_unsupported_affine_inputs_reject_without_mutation(damage):
    _,a,b=pair();states=(a,b);faces=[EDGE];dt=DT
    if damage=='lattice':states=(a,replace(b,frame=(*b.frame[:9],'1',*b.frame[10:])))
    if damage=='asynchronous':states=(a,replace(b,time_s=DT))
    if damage=='duplicate':faces=[EDGE,EDGE]
    if damage=='invalid_dt':dt=0.
    if damage=='density_domain':states=(MBFiniteVolumeState(a,('-2e25',),(),(),(),DT),replace(b,time_s=DT))
    saved=deepcopy(states)
    with pytest.raises(ValueError):advance(states,faces,dt)
    assert states==saved
