from copy import deepcopy
from dataclasses import asdict,replace
from fractions import Fraction
from pathlib import Path
import json
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
import math
import pytest
from tcad.core import _recomputed_lattice_mb as native
from tcad.solver.boltzmann_recomputed_lattice_transport import apply_mb_recomputed_lattice_stage as apply,advance_mb_recomputed_conducting_endpoint_split as advance
from tcad.postprocess.boltzmann_recomputed_lattice_transport import audit_mb_recomputed_lattice_stage as audit_stage,audit_mb_recomputed_conducting_endpoint_split as audit,face_values,split_lattice_recomputed_cell
from tcad.postprocess.boltzmann_recomputed_transport import point,endpoint_wire
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tests.test_mb_recomputed_endpoint_split import case,DT,Q

G=(1e-13,1e-8,2e-8,1.,2.)
EDGE=dict(owner=0,neighbor=1,geometry=G)
BATH=dict(owner=0,bath_temperature_K=290.,geometry=(1e-13,1e-8,0.,1.,1.))


def thermal(mode):
    return [] if mode=='isolated' else [deepcopy(EDGE)] if mode=='closed' else [deepcopy(BATH)] if mode=='contact' else [deepcopy(EDGE),deepcopy(BATH)]


def hot():
    cfg,states,faces=case('isolated');a,b=states;frame=list(b.endpoint[3:12]);frame[2]='310'
    p=point(b.endpoint);b=replace(b,endpoint=tuple(endpoint_wire(frame,p['values'])))
    return cfg,(a,b)


@pytest.fixture(scope='session')
def controls():
    result={}
    for mode in ('isolated','closed','contact','mixed'):
        cfg,old,faces=case(mode);tf=thermal(mode);new,r=advance(cfg,old,faces,tf,DT,impulses_J=Q)
        result[mode]=(cfg,old,faces,tf,new,r)
    return result


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_complete_split_conducts_heat_and_preserves_one_physical_interval(controls,mode):
    cfg,old,faces,tf,new,r=controls[mode]
    check=audit(cfg,old,new,r,faces=faces,thermal_faces=tf,dt_s=DT,impulses_J=Q)
    assert check['valid'] and check['whole_interval_particle_energy_closed'] and len(check['global_residuals'])==6
    assert check['physical_clock_advanced_once'] and r['lattice_flux_included'] and not r['field_work_included']
    assert not r['complete_device_energy'] and not r['physical_validated']
    assert new[0].physical_clock==tuple(r['pre_lattice_states'][0]['physical_clock'])
    if mode!='isolated':assert any(point(a.endpoint)['Tl']!=point(b['endpoint'])['Tl'] for a,b in zip(new,r['pre_lattice_states']))


@pytest.mark.parametrize('faces',[[EDGE],[BATH],[EDGE,BATH],[]],ids=['internal','bath','both','insulated'])
def test_lattice_stage_keeps_carrier_energy_and_exact_clock(faces):
    cfg,old=hot();new,r=apply(old,faces,DT)
    check=audit_stage(old,new,r,faces=faces,dt_s=DT)
    assert check['valid'] and check['physical_clock_preserved'] and check['internal_heat_faces_cancelled']
    for a,b in zip(old,new):assert a.physical_clock==b.physical_clock and a.time_s==b.time_s and point(a.endpoint)['n']==point(b.endpoint)['n']
    if faces:
        assert point(new[0].endpoint)['Tl']>point(old[0].endpoint)['Tl'] if faces==[EDGE] else point(new[0].endpoint)['Tl']!=point(old[0].endpoint)['Tl']
    else:assert new==old


@pytest.mark.parametrize('damage',['face','conductance','volume_remainder','carrier_compensation','compensation_remainder','evidence','endpoint','clock','extra_face','missing_cell','metadata','dt','bath','geometry','expanded','version','extra_token','truncated','serialized_claim','expanded_budget'])
def test_rehashed_full_interval_forgeries_are_rejected(controls,damage):
    cfg,old,faces,tf,new,source=controls['mixed'];r=deepcopy(source);tf=deepcopy(tf);new=list(new);dt=DT
    if damage=='face':r['lattice']['faces'][0][-2]='0x1'
    elif damage=='conductance':r['lattice']['faces'][0][2]='1'
    elif damage in ('volume_remainder','carrier_compensation','compensation_remainder'):
        raw=r['lattice']['cells'][0];index={'volume_remainder':0,'carrier_compensation':5,'compensation_remainder':6}[damage]
        p=point(new[0].endpoint);v=p['values'].copy();v[index]+=Fraction(1,1<<1000)
        endpoint=endpoint_wire(list(new[0].endpoint[3:12]),v);new[0]=replace(new[0],endpoint=tuple(endpoint))
        before=int(raw[2]);after=sum(int(__import__('tcad.postprocess.boltzmann_recomputed_transport',fromlist=['_wire'])._wire(x)[2]) for x in v)
        raw[2]=str(after);raw[3]=str(int(raw[3])+after-before);raw[4]=str(len(endpoint));raw[5:]=endpoint
    elif damage=='evidence':r['lattice']['cells'][0][2]='0'
    elif damage=='endpoint':new[0]=replace(new[0],endpoint=old[0].endpoint)
    elif damage=='clock':new[0]=replace(new[0],time_s=old[0].time_s,physical_clock=old[0].physical_clock)
    elif damage=='extra_face':r['lattice']['faces'].append(r['lattice']['faces'][0])
    elif damage=='missing_cell':r['lattice']['cells'].pop()
    elif damage=='expanded':r['lattice']['cells'][0][3]='0'
    elif damage=='version':r['lattice']['cells'][0][0]='mb_lattice_cell_v1'
    elif damage=='extra_token':r['lattice']['cells'][0].append('0')
    elif damage=='truncated':r['lattice']['cells'][0].pop()
    elif damage=='serialized_claim':r['lattice']['division_remainders_serialized']=True
    elif damage=='expanded_budget':r['lattice']['cells'][0][3]='8193'
    elif damage=='metadata':r['field_work_included']=True
    elif damage=='dt':dt*=2
    elif damage=='bath':tf[1]['bath_temperature_K']=295.
    else:tf[0]['geometry']=(2e-10,*G[1:])
    r['new_sha256']=list(map(_saved_fingerprint,new));r['lattice']['new_sha256']=r['new_sha256']
    with pytest.raises((ValueError,ArithmeticError)):audit(cfg,old,new,r,faces=faces,thermal_faces=tf,dt_s=dt,impulses_J=Q)


@pytest.mark.parametrize('damage',['self','outside','bool','duplicate','geometry','kind','bath','extra','negative_dt','zero_budget','unsynchronized','CFL'])
def test_bad_stage_requests_are_atomic(damage):
    cfg,old=hot();faces=[deepcopy(EDGE)];dt=DT;budget=1e-27
    if damage=='self':faces[0]['neighbor']=0
    elif damage=='outside':faces[0]['owner']=2
    elif damage=='bool':faces[0]['owner']=True
    elif damage=='duplicate':faces.append(deepcopy(EDGE))
    elif damage=='geometry':faces[0]['geometry']=(-1.,*G[1:])
    elif damage=='kind':faces[0]['geometry']=(G[0],G[1],0.,*G[3:])
    elif damage=='bath':faces=[{**BATH,'bath_temperature_K':float('nan')}]
    elif damage=='extra':faces[0]['ignored']=True
    elif damage=='negative_dt':dt=-DT
    elif damage=='zero_budget':budget=0.
    elif damage=='unsynchronized':old=(old[0],replace(old[1],time_s=2.**-40,physical_clock=('mb_scaled_value_v1','113','1','0x1','-40')))
    else:faces[0]['geometry']=(1e6,*G[1:])
    before=list(map(asdict,old))
    with pytest.raises(ValueError):apply(old,faces,dt,energy_atol_J=budget)
    assert list(map(asdict,old))==before


@pytest.mark.parametrize('damage',['nul','long','precision','nonstring','type','short','trailing','bad_count'])
def test_native_wire_validation(damage):
    cfg,old=hot();endpoint=list(old[0].endpoint);g=[str(DT)]
    if damage=='nul':g[0]='1\0'
    elif damage=='long':g[0]='1'*65
    elif damage=='precision':endpoint[1]='64'
    elif damage=='nonstring':g[0]=1
    elif damage=='type':g='bad'
    elif damage=='short':g.pop()
    elif damage=='trailing':endpoint.append('0')
    else:endpoint[12]='99999'
    with pytest.raises(ValueError):native.cell(endpoint,['mb_lattice_transfers_v1','113','0'],g)



@pytest.mark.parametrize('failure',['second_cell','last_audit'])
def test_full_split_failure_does_not_mutate_inputs(controls,monkeypatch,failure):
    import tcad.solver.boltzmann_recomputed_lattice_transport as solver
    cfg,old,faces,tf,new,r=controls['closed'];before=list(map(asdict,old));real=native.cell;count=[]
    def deny(*a,**kw):raise ValueError('injected lattice failure')
    if failure=='last_audit':monkeypatch.setattr(solver,'audit_mb_recomputed_conducting_endpoint_split',deny)
    else:
        def second(*a):
            count.append(1)
            if len(count)==2:return deny()
            return real(*a)
        monkeypatch.setattr(native,'cell',second)
    with pytest.raises(ValueError,match='injected'):advance(cfg,old,faces,tf,DT,impulses_J=Q)
    assert list(map(asdict,old))==before


def test_saved_full_split_replay_calls_no_producer(controls,monkeypatch):
    from tcad.core import _recomputed_mb,_scaled_transport,_lattice_mb
    def deny(*a,**kw):raise AssertionError('producer called in replay')
    for module in (native,_recomputed_mb,_scaled_transport,_lattice_mb):
        for name in dir(module):
            if name.startswith('native_') or name in ('face','bath','cell'):monkeypatch.setattr(module,name,deny)
    for cfg,old,faces,tf,new,r in controls.values():assert audit(cfg,old,new,r,faces=faces,thermal_faces=tf,dt_s=DT,impulses_J=Q)['valid']


def test_restricted_heat_operator_has_first_order_temporal_convergence():
    cfg,old=hot();states=[]
    for state in old:
        p=point(state.endpoint);frame=list(state.endpoint[3:12]);frame[3]='1048576';frame[4]='8.67361737988403547205962240695953369140625e-19'
        values=p['values'].copy();values[0]=Fraction()
        states.append(replace(state,endpoint=tuple(endpoint_wire(frame,values))))
    states=tuple(states);faces=[dict(owner=0,neighbor=1,geometry=(2.**-19,1.,1.,1.,1.))]
    duration=2.**-24;errors=[]
    exact=305.-5.*math.exp(-2.*2.**20*duration)
    for steps in (4,8,16):
        current=states
        for j in range(steps):current,r=apply(current,faces,duration/steps)
        errors.append(abs(float(point(current[0].endpoint)['Tl'])-exact))
    assert 1.9<errors[0]/errors[1]<2.1 and 1.9<errors[1]/errors[2]<2.1


def test_heterogeneous_three_cell_heat_network_is_orientation_independent():
    cfg,old=hot();third=point(old[1].endpoint);frame=list(old[1].endpoint[3:12]);frame[2]='290';frame[3]='2000';frame[4]='2e-20'
    states=(*old,replace(old[1],endpoint=tuple(endpoint_wire(frame,third['values']))))
    faces=[deepcopy(EDGE),dict(owner=1,neighbor=2,geometry=G),deepcopy(BATH),{**BATH,'owner':2,'bath_temperature_K':330.}]
    new,r=apply(states,faces,DT)
    flipped=[]
    for f in faces:
        if 'neighbor' in f:
            area,do,dn,ko,kn=f['geometry'];flipped.append(dict(owner=f['neighbor'],neighbor=f['owner'],geometry=(area,dn,do,kn,ko)))
        else:flipped.append(f)
    mirrored,s=apply(states,flipped,DT)
    assert new==mirrored and r['independent_audit']['valid'] and s['independent_audit']['valid']


def test_zero_flux_unstable_step_is_rejected_by_CFL_guard():
    cfg,states,faces=case('isolated')
    with pytest.raises(ValueError,match='CFL'):apply(states,[{**EDGE,'geometry':(1e6,*G[1:])}],DT)


@pytest.mark.parametrize('factor',[1.,1.01])
def test_exact_CFL_boundary(factor):
    cfg,states=hot();old=[]
    for state in states:
        p=point(state.endpoint);frame=list(state.endpoint[3:12]);frame[3]='1048576';frame[4]='8.67361737988403547205962240695953369140625e-19';v=p['values'].copy();v[0]=Fraction()
        old.append(replace(state,endpoint=tuple(endpoint_wire(frame,v))))
    faces=[dict(owner=0,neighbor=1,geometry=(2.**-19,1.,1.,1.,1.))]
    if factor>1:
        with pytest.raises(ValueError,match='CFL'):apply(old,faces,factor*2.**-20)
    else:
        new,r=apply(old,faces,2.**-20)
        assert float(point(new[0].endpoint)['Tl'])==310. and float(point(new[1].endpoint)['Tl'])==300.


ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'docs/validation/mb_lattice_transport_20261024'


def original_case(mode):
    source=json.loads((ROOT/f'docs/validation/mb_recomputed_endpoint_20261024/captured/original_{mode}.json').read_text())
    old=tuple(MBScaledTransportState(**s) for s in source['old'])
    faces=[{**f,'reservoir':MBScaledTransportState(**f['reservoir'])} if 'reservoir' in f else f for f in source['faces']]
    return source,old,faces


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_new_certificate_preserves_legacy_complete_endpoints_and_fluxes(controls,mode):
    row=next(x for x in json.loads((PARENT/'captured.json').read_text())['full'] if x['mode']==mode)
    cfg,old,faces,tf,new,r=controls[mode]
    assert [list(s.endpoint) for s in new]==[s['endpoint'] for s in row['new']]
    assert r['lattice']['faces']==row['report']['lattice']['faces']
    assert not r['lattice']['division_remainders_serialized']
    for current,legacy in zip(r['lattice']['cells'],row['report']['lattice']['cells']):
        assert int(current[2])<=int(legacy[2]) and int(current[3])==int(legacy[2])


@pytest.mark.parametrize('mode,counts',[('closed',[1994,1994]),('contact',[1721,123])])
def test_original_saved_third_states_accept_heat_with_complete_endpoints(mode,counts):
    row=next(x for x in json.loads((PARENT/'captured.json').read_text())['continuations'] if x['mode']==mode)
    old=tuple(MBScaledTransportState(**s) for s in row['old']);before=list(map(asdict,old))
    new,r=apply(old,row['faces'],row['dt_s'])
    assert audit_stage(old,new,r,faces=row['faces'],dt_s=row['dt_s'])['valid']
    assert [int(raw[2]) for raw in r['cells']]==counts
    assert max(int(raw[3]) for raw in r['cells'])>4096
    assert list(map(asdict,old))==before and all(a.physical_clock==b.physical_clock for a,b in zip(old,new))


@pytest.fixture(scope='session')
def original_whole():
    result={}
    for mode in ('closed','contact'):
        source,old,faces=original_case(mode);tf=thermal(mode)
        new,r=advance(source['configurations'],old,faces,tf,source['dt_s'],impulses_J=source['impulses_J'])
        result[mode]=(source,old,faces,tf,new,r)
    return result


@pytest.mark.parametrize('mode',['closed','contact'])
def test_original_third_whole_interval_includes_heat_and_one_physical_clock(original_whole,mode):
    source,old,faces,tf,new,r=original_whole[mode]
    check=audit(source['configurations'],old,new,r,faces=faces,thermal_faces=tf,dt_s=source['dt_s'],impulses_J=source['impulses_J'])
    assert check['valid'] and check['whole_interval_particle_energy_closed']
    assert [list(s['endpoint']) for s in r['pre_lattice_states']]==[s['endpoint'] for s in source['full_split_attempt']['new']]
    assert new[0].physical_clock==tuple(source['full_split_attempt']['new'][0]['physical_clock'])


@pytest.mark.parametrize('mode',['closed','contact'])
def test_next_complete_attempt_is_atomic_or_independently_closed(original_whole,mode):
    source,old,faces,tf,entered,r=original_whole[mode];before=list(map(asdict,entered))
    faces=[{**f,'reservoir':replace(f['reservoir'],time_s=entered[0].time_s,physical_clock=entered[0].physical_clock)} if 'reservoir' in f else f for f in faces]
    try:new,r=advance(source['configurations'],entered,faces,tf,source['dt_s'],impulses_J=source['impulses_J'])
    except ValueError as exc:assert 'budget exceeded' in str(exc)
    else:assert audit(source['configurations'],entered,new,r,faces=faces,thermal_faces=tf,dt_s=source['dt_s'],impulses_J=source['impulses_J'])['valid']
    assert list(map(asdict,entered))==before


def test_original_mixed_still_rejects_before_heat_and_preserves_inputs(monkeypatch):
    source,old,faces=original_case('mixed');before=list(map(asdict,old));called=[]
    def deny(*a):called.append(True);raise AssertionError('heat called after carrier failure')
    monkeypatch.setattr(native,'cell',deny)
    with pytest.raises(ValueError,match='budget exceeded'):advance(source['configurations'],old,faces,thermal('mixed'),source['dt_s'],impulses_J=source['impulses_J'])
    assert not called and list(map(asdict,old))==before
