from copy import deepcopy
from dataclasses import asdict,replace
from fractions import Fraction
import importlib,json
import pytest
from tcad.core import _accounted_rounding_mb as native
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState
from tcad.solver.boltzmann_accounted_rounding import round_mb_endpoints,advance_mb_rounded_conducting_split as advance
from tcad.postprocess.boltzmann_accounted_rounding import (
    split_rounding,audit_mb_accounted_rounding as audit_round,audit_mb_rounded_conducting_split as audit,
)
from tcad.postprocess.boltzmann_recomputed_transport import point,endpoint_wire,_wire
from tcad.postprocess.boltzmann_product_range import _binary113
from tcad.postprocess.boltzmann_scaled_split import _saved_fingerprint
from tests.test_mb_recomputed_lattice_transport import case,thermal,DT,Q,original_case,PARENT


@pytest.mark.parametrize('width',[112,113,114,1000,60000])
@pytest.mark.parametrize('sign',[-1,1])
def test_native_rounding_keeps_every_exact_coordinate_difference(width,sign):
    cfg,old,faces=case('isolated');p=point(old[0].endpoint);v=p['values'].copy()
    x=Fraction(sign*((1<<width)+3),1<<(width+100));v[1]=x
    state=replace(old[0],endpoint=tuple(endpoint_wire(list(old[0].endpoint[3:12]),v)))
    new,r=round_mb_endpoints([state]);check=audit_round([state],new,r)
    endpoint,values,tails=split_rounding(r['cells'][0])
    assert values[1]==_binary113(x) and values[1]+tails[1]==x and check['valid']
    assert new[0].time_s==state.time_s and new[0].physical_clock==state.physical_clock


@pytest.mark.parametrize('offset',[1,3,5,7])
@pytest.mark.parametrize('sign',[-1,1])
def test_ties_even_and_round_carry(offset,sign):
    cfg,old,faces=case('isolated');p=point(old[0].endpoint);v=p['values'].copy()
    v[1]=Fraction(sign*((1<<114)+offset),1<<214)
    state=replace(old[0],endpoint=tuple(endpoint_wire(list(old[0].endpoint[3:12]),v)))
    new,r=round_mb_endpoints([state]);assert point(new[0].endpoint)['values'][1]==_binary113(v[1])


@pytest.fixture(scope='session')
def controls():
    rows={}
    for mode in ('isolated','closed','contact','mixed'):
        cfg,old,faces=case(mode);new,r=advance(cfg,old,faces,thermal(mode),DT,impulses_J=Q)
        rows[mode]=(cfg,old,faces,new,r)
    return rows


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_whole_interval_actual_energy_includes_rounding(controls,mode):
    cfg,old,faces,new,r=controls[mode];c=audit(cfg,old,new,r,faces=faces,thermal_faces=thermal(mode),dt_s=DT,impulses_J=Q)
    assert c['valid'] and c['rounding_error_included'] and not c['exact_recurrence_preserved']
    assert c['physical_clock_advanced_once'] and len(c['global_residuals'])==6
    assert not c['complete_device_energy'] and not c['physical_validated']


@pytest.mark.parametrize('damage',['version','precision','count','extra','short','tail','endpoint','frame','clock','metadata','coverage','detached'])
def test_rehashed_rounding_forgeries_rejected(controls,damage):
    cfg,old,faces,new,r=controls['mixed'];r=deepcopy(r);rounded=tuple(MBScaledTransportState(**x) for x in r['rounded_states'])
    rr=r['rounding'];raw=rr['cells'][0]
    if damage=='version':raw[0]='old'
    elif damage=='precision':raw[1]='64'
    elif damage=='count':raw[2]='0'
    elif damage=='extra':raw.append('0')
    elif damage=='short':raw.pop()
    elif damage=='tail':
        endpoint,values,tails=split_rounding(raw);tails[0]+=Fraction(1,1<<200)
        raw[:]=['mb_accounted_rounding_v1','113',str(sum(int(_wire(x)[2]) for x in values+tails)),str(len(endpoint)),*endpoint]
        for x in tails:
            packet=_wire(x);raw.extend((str(len(packet)),*packet))
    elif damage in ('endpoint','frame'):
        p=point(rounded[0].endpoint);v=p['values'].copy();frame=list(rounded[0].endpoint[3:12])
        if damage=='endpoint':v[1]+=Fraction(1,1<<150)
        else:frame[2]='301'
        rounded=(replace(rounded[0],endpoint=tuple(endpoint_wire(frame,v))),*rounded[1:])
    elif damage=='clock':rounded=(replace(rounded[0],time_s=1.,physical_clock=tuple(_wire(Fraction(1)))),*rounded[1:])
    elif damage=='metadata':rr['exact_recurrence_preserved']=True
    elif damage=='coverage':rr['cells'].pop()
    else:rr['cells'][0]=rr['cells'][1]
    rr['new_sha256']=list(map(_saved_fingerprint,rounded))
    with pytest.raises(ValueError):audit_round(old,rounded,rr)


@pytest.mark.parametrize('damage',['nul','long','type','sequence','short','trailing'])
def test_native_invalid_wire(damage):
    cfg,old,faces=case('isolated');raw=list(old[0].endpoint)
    if damage=='nul':raw[3]='1\0'
    elif damage=='long':raw[3]='1'*65
    elif damage=='type':raw[3]=1
    elif damage=='sequence':raw='wrong'
    elif damage=='short':raw.pop()
    else:raw.append('0')
    with pytest.raises(ValueError):native.endpoint(raw)


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_original_third_interval_has_accounted_rounding_and_full_energy_gate(mode):
    source,old,faces=original_case(mode);before=list(map(asdict,old))
    new,r=advance(source['configurations'],old,faces,thermal(mode),source['dt_s'],impulses_J=source['impulses_J'])
    c=audit(source['configurations'],old,new,r,faces=faces,thermal_faces=thermal(mode),dt_s=source['dt_s'],impulses_J=source['impulses_J'])
    assert c['valid'] and c['rounding_error_included'] and not c['exact_recurrence_preserved']
    assert list(map(asdict,old))==before and new[0].time_s==6e-14


@pytest.mark.parametrize('mode',['closed','contact'])
def test_original_exact_third_output_advances_with_explicit_rounding(mode):
    saved=json.loads((PARENT.parent/'mb_recomputed_lattice_20261024/captured.json').read_text())
    row=next(x for x in saved['full'] if x['kind']=='original_third_interval' and x['mode']==mode)
    old=tuple(MBScaledTransportState(**x) for x in row['new']);faces=[dict(f) for f in row['faces']]
    for f in faces:
        if 'reservoir' in f:
            f['reservoir']=MBScaledTransportState(**{**f['reservoir'],'time_s':old[0].time_s,'physical_clock':old[0].physical_clock})
    before=list(map(asdict,old));new,r=advance(row['configurations'],old,faces,row['thermal_faces'],row['dt_s'],impulses_J=row['impulses_J'])
    assert audit(row['configurations'],old,new,r,faces=faces,thermal_faces=row['thermal_faces'],dt_s=row['dt_s'],impulses_J=row['impulses_J'])['valid']
    assert new[0].time_s==8e-14 and list(map(asdict,old))==before


@pytest.mark.parametrize('budget',[0.,-1.,1e-100])
def test_inadequate_rounding_budget_rejects_atomically(budget):
    source,old,faces=original_case('mixed');before=list(map(asdict,old))
    with pytest.raises(ValueError):round_mb_endpoints(old,energy_atol_J=budget)
    assert list(map(asdict,old))==before


def test_complete_failure_is_atomic(controls,monkeypatch):
    cfg,old,faces,new,r=controls['mixed'];before=list(map(asdict,old))
    import tcad.solver.boltzmann_accounted_rounding as module
    def deny(*a,**kw):raise ValueError('injected final audit failure')
    monkeypatch.setattr(module,'audit_mb_rounded_conducting_split',deny)
    with pytest.raises(ValueError,match='injected'):advance(cfg,old,faces,thermal('mixed'),DT,impulses_J=Q)
    assert list(map(asdict,old))==before


def test_saved_replay_does_not_call_native(controls,monkeypatch):
    cfg,old,faces,new,r=controls['mixed']
    def deny(*a,**kw):raise AssertionError('producer called')
    monkeypatch.setattr(native,'endpoint',deny)
    assert audit(cfg,old,new,r,faces=faces,thermal_faces=thermal('mixed'),dt_s=DT,impulses_J=Q)['valid']


@pytest.mark.parametrize('raw',[[],['mb_accounted_rounding_v1'],['mb_accounted_rounding_v1','113'],['mb_accounted_rounding_v1','113','0']])
def test_independent_truncated_framing_raises_value_error(raw):
    with pytest.raises(ValueError):split_rounding(raw)
