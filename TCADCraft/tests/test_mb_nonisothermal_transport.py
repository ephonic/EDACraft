from copy import deepcopy
from dataclasses import replace
from decimal import Decimal,localcontext
import pytest
from tests.test_mb_expanded_flat_face import pair,GEOMETRY
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState,FIELDS,_fingerprint
from tcad.physics.boltzmann_affine_face import affine_mb_flat_face as common_face
from tcad.physics.boltzmann_nonisothermal_face import nonisothermal_mb_flat_face as face
from tcad.solver.boltzmann_nonisothermal_transport import advance_mb_nonisothermal_transport as advance
from tcad.postprocess.boltzmann_nonisothermal_transport import audit_nonisothermal_mb_face as face_audit,audit_mb_nonisothermal_transport as audit

DT=1e-18;EDGE=dict(owner=0,neighbor=1,geometry=GEOMETRY)
def total(raw):return sum(map(Decimal,raw),Decimal(0))
def heterogeneous():
    _,a,b=pair();f=list(b.frame);f[2]='305';f[3]='1500';f[4]='2e-20';f[9]='22501'
    return a,replace(b,frame=tuple(f))


@pytest.mark.parametrize('kind,g',[('bulk',GEOMETRY),('contact',(1e-14,1e-8,0.,.1,.2))])
def test_common_lattice_matches_existing_affine_face(kind,g):
    _,a,b=pair();r=face(a,b,g,face_kind=kind);p=common_face(a,b,g,face_kind=kind)
    with localcontext() as ctx:
        ctx.prec=10000
        for c,d in zip(r['carriers'],p['carriers']):
            for key in ('number_expansion','energy_expansion'):
                x=total(c[key]);y=total(d[key]);assert abs(x-y)<=Decimal('1e-28')*abs(y)
    assert r['independent_audit']['valid']


@pytest.mark.parametrize('field',['temperature','capacity','reference','history','volume'])
def test_independent_endpoint_lattice_coordinates_and_spatial_scales(field):
    _,a,b=pair();f=list(b.frame)
    if field=='temperature':f[2]='310'
    if field=='capacity':f[3]='1500'
    if field=='reference':f[2]='305';f[9]='-7500'
    if field=='history':f[9]='10000';f.append('1e-300')
    if field=='volume':f[4]='2e-20'
    b=replace(b,frame=tuple(f));r=face(a,b,GEOMETRY)
    assert r['independent_audit']['valid'] and r['lattice_heterogeneity_supported'] and not r['lattice_flux_included']


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_three_continuous_steps_with_different_lattice_capacity_and_volume(mode):
    a,b=heterogeneous();states=(a,b);moments=[]
    for _ in range(3):
        faces=[EDGE]
        if mode=='contact':faces=[dict(owner=0,reservoir=replace(b,time_s=states[0].time_s),geometry=(1e-14,1e-8,0.,.1,.2))]
        if mode=='mixed':faces.append(dict(owner=1,reservoir=replace(a,time_s=states[0].time_s),geometry=(1e-14,1e-8,0.,.1,.2)))
        states,r=advance(states,faces,DT);assert r['independent_audit']['valid']
        assert states[0].anchor==a and states[1].anchor==b
        moments.append(r['transfers'][0]['moment']['carriers'][0]['number_expansion'])
    assert moments[0]!=moments[1]!=moments[2]


@pytest.mark.parametrize('tail',['1e-300','-1e-300'])
def test_sub_view_lattice_difference_drives_two_actual_steps(tail):
    _,a,b=pair();b=a;a=replace(a,frame=(*a.frame,tail));states=(a,b)
    r=face(a,b,GEOMETRY);assert r['independent_audit']['valid']
    assert r['carriers'][0]['number_expansion'] and r['carriers'][0]['energy_expansion']
    for _ in range(2):states,r=advance(states,[EDGE],DT);assert r['independent_audit']['valid']
    with localcontext() as ctx:
        ctx.prec=10000
        assert total(states[0].electron_density_change)!=0 and total(states[0].electron_energy_density_change)!=0
        assert float(Decimal(a.frame[0])+total(states[0].electron_density_change))==float(a.frame[0])


@pytest.mark.parametrize('representation',['reference_capacity','history'])
def test_equivalent_actual_lattice_temperature_has_exact_zero_flux(representation):
    _,a,b=pair();f=list(a.frame);f[9]='20000';a=replace(a,frame=tuple(f));g=list(f)
    if representation=='reference_capacity':g[2]='310';g[3]='2000'
    else:g[9]='10000';g.append('10000')
    b=replace(a,frame=tuple(g));r=face(a,b,GEOMETRY)
    assert all(not c[key] for c in r['carriers'] for key in ('number_expansion','energy_expansion'))
    assert r['independent_audit']['valid']


def test_reverse_orientation_with_independent_thermal_frames():
    a,b=heterogeneous();f=face(a,b,GEOMETRY);g=face(b,a,(GEOMETRY[0],GEOMETRY[2],GEOMETRY[1],GEOMETRY[4],GEOMETRY[3]))
    with localcontext() as ctx:
        ctx.prec=10000
        for x,y in zip(f['carriers'],g['carriers']):
            for key in ('number_expansion','energy_expansion'):assert abs(total(x[key])+total(y[key]))<=Decimal('1e-28')*abs(total(x[key]))


def test_prior_common_lattice_interface_retains_its_explicit_contract():
    with pytest.raises(ValueError,match='common lattice'):common_face(*heterogeneous(),GEOMETRY)


@pytest.mark.parametrize('damage',['quotient','quotient_low','thermal_owner','thermal_neighbor','swap_thermal','normalization','DAG','number','energy','scope','metadata','lattice_flux','fingerprint'])
def test_saved_face_thermal_and_arithmetic_forgeries_rejected(damage):
    a,b=heterogeneous();r=deepcopy(face(a,b,GEOMETRY));c=r['carriers'][0]
    if damage=='quotient':r['lattice_quotients'][1]=[]
    if damage=='quotient_low':
        q=r['lattice_quotients'][1];assert len(q)>=2 and q[-1]!='0';q.pop()
    if damage=='thermal_owner':r['thermal_expansions'][0].append('1e-300')
    if damage=='thermal_neighbor':r['thermal_expansions'][1]=r['thermal_expansions'][1][-1:]
    if damage=='swap_thermal':r['thermal_expansions'].reverse()
    if damage=='normalization':c['normalization'][2]=[]
    if damage=='DAG':c['operations'][3]['value'].append('1e-300')
    if damage=='number':c['number_expansion']=[]
    if damage=='energy':c['energy_expansion']=[]
    if damage=='scope':r['scope']='flat_MB_affine_density_energy_face'
    if damage=='metadata':r['lattice_heterogeneity_supported']=False
    if damage=='lattice_flux':r['lattice_flux_included']=True
    if damage=='fingerprint':r['neighbor_sha256']='0'*64
    try:result=face_audit(a,b,r,geometry=GEOMETRY)
    except ValueError:return
    assert not result['valid']


@pytest.mark.parametrize('damage',['anchor','prefix','energy','clock','topology','view'])
def test_saved_second_step_forgeries_with_rehashed_states_rejected(damage):
    states,_=advance(heterogeneous(),[EDGE],DT);new,r=advance(states,[EDGE],DT);new=list(new);r=deepcopy(r)
    if damage=='anchor':new[0]=replace(new[0],anchor=replace(new[0].anchor,frame=(*new[0].anchor.frame,'1e-300')))
    if damage=='prefix':new[0]=replace(new[0],electron_density_change=new[0].electron_density_change[1:])
    if damage=='energy':new[0]=replace(new[0],electron_energy_density_change=states[0].electron_energy_density_change)
    if damage=='clock':new[0]=replace(new[0],time_s=3*DT)
    if damage=='topology':r['transfers'][0]['neighbor']=None
    if damage=='view':r['cells'][1]['temperatures_K'][0]='301'
    r['new_sha256']=list(map(_fingerprint,new))
    try:result=audit(states,new,r,faces=[EDGE],dt_s=DT)
    except ValueError:return
    assert not result['valid']


def test_saved_audit_requires_no_native_or_production_constitutive_law(monkeypatch):
    states=heterogeneous();new,r=advance(states,[EDGE],DT)
    import tcad.core._bindings as native
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    import tcad.physics.boltzmann_nonisothermal_face as production_face
    import tcad.solver.boltzmann_nonisothermal_transport as production_solver
    def deny(*args,**kwargs):raise AssertionError('native or production physics used during saved audit')
    for name in dir(native):
        if name.startswith(('native_','three_temperature_')) and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny);monkeypatch.setattr(production_face,'nonisothermal_mb_flat_face',deny);monkeypatch.setattr(production_solver,'advance_mb_nonisothermal_transport',deny)
    r.pop('independent_audit');assert audit(states,new,r,faces=[EDGE],dt_s=DT)['valid']


@pytest.mark.parametrize('damage',['band','clock','capacity','duplicate','dt'])
def test_unsupported_problems_reject_atomically(damage):
    a,b=heterogeneous();faces=[EDGE];dt=DT
    if damage=='band':b=replace(b,frame=(*b.frame[:5],'1e-22',*b.frame[6:]))
    if damage=='clock':b=replace(b,time_s=DT)
    if damage=='capacity':b=replace(b,frame=(*b.frame[:3],'-1500',*b.frame[4:]))
    if damage=='duplicate':faces=[EDGE,EDGE]
    if damage=='dt':dt=0.
    states=(a,b);before=deepcopy(states)
    with pytest.raises(ValueError):advance(states,faces,dt)
    assert states==before
