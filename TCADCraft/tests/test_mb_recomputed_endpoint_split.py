from copy import deepcopy
from dataclasses import asdict,replace
from pathlib import Path
from fractions import Fraction
import json
import pytest
from tcad.core import _recomputed_mb as native
from tcad.solver.boltzmann_recomputed_endpoint_split import advance_mb_recomputed_endpoint_split as advance,advance_mb_recomputed_endpoint_collision
from tcad.solver.boltzmann_scaled_transport import MBScaledTransportState,materialize_mb_scaled_state
from tcad.postprocess.boltzmann_recomputed_endpoint_split import audit_mb_recomputed_endpoint_split as audit,audit_mb_recomputed_endpoint_collision
from tcad.postprocess.boltzmann_recomputed_endpoint_powerlaw import audit_mb_recomputed_endpoint_powerlaw,split_mb_recomputed_endpoint_powerlaw,scaled_powerlaw_aggregates
from tcad.postprocess.boltzmann_recomputed_endpoint_collision import audit_mb_recomputed_endpoint_collision_compact
from tcad.postprocess.boltzmann_scaled_transport import _wire,scaled_value_fraction,point,_saved_fingerprint
from tests.test_mb_split_interval import problem,DT

ROOT=Path(__file__).resolve().parents[1];Q=((2e-19,-1e-19,3e-19),(0.,0.,0.))


def case(mode):
    cfg,states,faces=problem(mode);old=tuple(materialize_mb_scaled_state(s)[0] for s in states)
    faces=[{**f,'reservoir':materialize_mb_scaled_state(f['reservoir'])[0]} if 'reservoir' in f else f for f in faces]
    return cfg,old,faces


def original(mode):
    r=json.loads((ROOT/f'docs/validation/mb_scaled_transport_20261024/captured/{mode}.json').read_text())
    old=tuple(MBScaledTransportState(**s) for s in r['old']);middle=tuple(MBScaledTransportState(**s) for s in r['new'])
    faces=[{**f,'reservoir':MBScaledTransportState(**f['reservoir'])} if 'reservoir' in f else f for f in r['faces']]
    return r,old,middle,faces


@pytest.fixture(scope='session')
def controls():
    return {m:(lambda c:(c,advance(*c,DT,impulses_J=Q)))(case(m)) for m in ('isolated','closed','contact','mixed')}


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_complete_scaled_endpoint_split_has_all_energy_rows_and_one_clock(controls,mode):
    (cfg,old,faces),(new,r)=controls[mode]
    check=audit(cfg,old,new,r,faces=faces,dt_s=DT,impulses_J=Q)
    assert check['valid'] and check['whole_interval_particle_energy_closed'] and len(check['global_residuals'])==6
    assert check['source_and_contact_ownership_checked'] and check['auxiliary_clock_projection_checked']
    assert native.precision_bits==113 and not r['complete_device_energy'] and not r['monolithic_coupled_BE']
    for a,b,mid,aux in zip(old,new,r['transported_states'],r['collision_states']):
        assert scaled_value_fraction(b.physical_clock)-scaled_value_fraction(a.physical_clock)==Fraction(DT)
        assert list(b.physical_clock)==list(mid['physical_clock'])
        assert scaled_value_fraction(aux['physical_clock'])-scaled_value_fraction(b.physical_clock)==Fraction(DT)


@pytest.mark.parametrize('kind',['nonzero_ac','constant_tau','equilibrium'])
def test_complete_endpoint_direct_collision_has_actual_energy_closure(kind):
    (cfg,cfg2),old,faces=case('isolated');cfg=cfg
    if kind=='constant_tau':
        values=list(cfg.parameters)
        for k in (6,7,10,11):values[k]='0'
        cfg=replace(cfg,parameters=tuple(values))
    if kind=='equilibrium':
        from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState
        source=MBParticleEnergyState(('1e25','1e25','300',cfg.parameters[0],cfg.parameters[1],'0','0',cfg.parameters[12],cfg.parameters[13],'0'),('0',),('0',),0.,'equilibrium')
        old=(materialize_mb_scaled_state(source)[0],)
    new,r=advance_mb_recomputed_endpoint_collision(cfg,old[0],DT)
    check=audit_mb_recomputed_endpoint_collision(cfg,old[0],new,r,dt_s=DT)
    assert check['valid'] and check['actual_endpoint_graph_checked']
    assert scaled_value_fraction(new.physical_clock)-scaled_value_fraction(old[0].physical_clock)==Fraction(DT)


@pytest.mark.parametrize('mode,cell',[(m,c) for m in ('closed','contact','mixed') for c in (0,1)])
def test_original_third_transport_six_collision_attempts_preserve_budget_boundary(mode,cell):
    r,old,middle,faces=original(mode);state=middle[cell];command=r['source_split_states'][cell]['collision']['command']
    before=asdict(state)
    if (mode,cell) in (('closed',0),('closed',1),('contact',0),('contact',1)):
        packet=native.native_mb_recomputed_endpoint_powerlaw_raw(state.endpoint,command,state.physical_clock)
        assert audit_mb_recomputed_endpoint_powerlaw(state.endpoint,command,state.physical_clock,packet)['valid']
    else:
        with pytest.raises(ValueError,match='budget exceeded'):
            native.native_mb_recomputed_endpoint_powerlaw_raw(state.endpoint,command,state.physical_clock)
    assert asdict(state)==before


@pytest.mark.parametrize('mode,cell',[(m,c) for m in ('closed','contact','mixed') for c in (0,1)])
def test_original_fixed_reference_tau_prefix_is_exactly_auditable_or_resource_rejected(mode,cell):
    r,old,middle,faces=original(mode);state=middle[cell];c=r['source_split_states'][cell]['collision']['command']
    command=[c[14],c[2],c[3],*c[15:]]
    try:packet=native.native_mb_recomputed_endpoint_collision_compact_raw(state.endpoint,command)
    except ValueError as exc:assert 'budget exceeded' in str(exc);return
    check=audit_mb_recomputed_endpoint_collision_compact(state.endpoint,command,packet)
    assert check['status'] in ('complete','evidence_budget_exceeded')
    if check['status']=='evidence_budget_exceeded':assert not check['full_fixed_tau_energy_gate_passed'] and check['requested_components']>4096


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_original_complete_third_split_preserves_atomic_acceptance_boundary(mode):
    r,old,middle,faces=original(mode);cfg=problem(mode)[0];before=list(map(asdict,old))
    if mode=='mixed':
        with pytest.raises(ValueError,match='budget exceeded'):advance(cfg,old,faces,DT,impulses_J=Q)
    else:
        new,report=advance(cfg,old,faces,DT,impulses_J=Q)
        assert audit(cfg,old,new,report,faces=faces,dt_s=DT,impulses_J=Q)['valid']
    assert list(map(asdict,old))==before


@pytest.mark.parametrize('damage',['endpoint','clock','auxiliary','source','dt','configuration','packet','transport','metadata','coverage'])
def test_rehashed_complete_split_forgeries_are_rejected(controls,damage):
    (cfg,old,faces),(new,report)=controls['mixed'];raw=list(map(asdict,new));r=deepcopy(report)
    if damage=='endpoint':raw[0]['endpoint']=old[0].endpoint
    elif damage=='clock':raw[0]['physical_clock']=r['collision_states'][0]['physical_clock'];raw[0]['time_s']=r['collision_states'][0]['time_s']
    elif damage=='auxiliary':r['collision_states'][0]['physical_clock']=new[0].physical_clock;r['collision_states'][0]['time_s']=new[0].time_s
    elif damage=='source':r['collisions'][0]['command'][15]='1e-19'
    elif damage=='dt':r['collisions'][0]['command'][14]='1e-14'
    elif damage=='configuration':cfg=(replace(cfg[0],parameters=(*cfg[0].parameters[:6],'0.7',*cfg[0].parameters[7:])),cfg[1])
    elif damage=='packet':r['collisions'][0]['root_packet'][-1]='0'
    elif damage=='transport':r['transport']['cells'][0][-1]='0'
    elif damage=='metadata':r['complete_device_energy']=True
    else:r['collisions'].pop()
    r['new_sha256']=list(map(_saved_fingerprint,raw))
    for i in range(min(len(r['collisions']),len(raw))):r['collisions'][i]['new_sha256']=_saved_fingerprint(r['collision_states'][i])
    try:check=audit(cfg,old,raw,r,faces=faces,dt_s=DT,impulses_J=Q)
    except (ValueError,ArithmeticError):return
    assert not check['valid']


@pytest.mark.parametrize('damage',['clock','chosen_tau','evidence','history','aggregate','source_endpoint','input_clock','extreme_a','truncated','extra'])
def test_saved_endpoint_root_cannot_detach_from_full_source(controls,damage):
    (cfg,old,faces),(new,r)=controls['isolated'];report=r['collisions'][0];mid=r['transported_states'][0]
    endpoint=list(mid['endpoint']);clock=list(mid['physical_clock']);command=report['command'].copy();packet=report['root_packet'].copy()
    if damage=='clock':j=7+4*int(packet[2]);packet[j+4]='0x1'
    elif damage=='chosen_tau':packet[4]='1e-12'
    elif damage=='evidence':packet[6]='0'
    elif damage=='history':packet[8]='1e-13'
    elif damage=='aggregate':packet[-2]='0x1'
    elif damage=='source_endpoint':endpoint[3]='2e25'
    elif damage=='input_clock':clock=_wire(Fraction(7e-14))
    elif damage=='extreme_a':command[6]='-20000'
    elif damage=='truncated':packet.pop()
    else:packet.append('0')
    with pytest.raises((ValueError,ArithmeticError)):audit_mb_recomputed_endpoint_powerlaw(endpoint,command,clock,packet)


@pytest.mark.parametrize('damage',['second_collision','last_audit','materializer','negative_dt','configuration_count'])
def test_complete_split_failure_is_atomic(controls,monkeypatch,damage):
    import tcad.solver.boltzmann_recomputed_endpoint_split as solver
    (cfg,old,faces),_=controls['closed'];before=list(map(asdict,old));dt=DT
    def deny(*a,**kw):raise ValueError('injected failure')
    if damage=='second_collision':
        real=native.native_mb_recomputed_endpoint_powerlaw_raw;calls=[]
        def second(*a):
            calls.append(1)
            if len(calls)==2:raise ValueError('injected second collision')
            return real(*a)
        monkeypatch.setattr(native,'native_mb_recomputed_endpoint_powerlaw_raw',second)
    elif damage=='last_audit':monkeypatch.setattr(solver,'audit_mb_recomputed_endpoint_split',lambda *a,**kw:dict(valid=False))
    elif damage=='materializer':monkeypatch.setattr(native,'native_mb_recomputed_endpoint_apply_raw',deny)
    elif damage=='negative_dt':dt=-DT
    else:cfg=cfg[:1]
    with pytest.raises(ValueError):advance(cfg,old,faces,dt,impulses_J=Q)
    assert list(map(asdict,old))==before


@pytest.mark.parametrize('damage',['precision','short_command','negative_clock','noncanonical_clock','extreme_a','nul','long_token'])
def test_native_endpoint_wire_validation(controls,damage):
    _,(_,r)=controls['isolated'];mid=r['transported_states'][0];endpoint=list(mid['endpoint']);command=r['collisions'][0]['command'].copy();clock=list(mid['physical_clock'])
    if damage=='precision':endpoint[1]='64'
    elif damage=='short_command':command.pop()
    elif damage=='negative_clock':clock=_wire(Fraction(-1))
    elif damage=='noncanonical_clock':clock=['mb_scaled_value_v1','113','2','0x1','0','0x10000000000000000000000001','100']
    elif damage=='extreme_a':command[6]='-20000'
    elif damage=='nul':command[0]='1000\0'
    else:command[0]='1'*65
    with pytest.raises(ValueError):native.native_mb_recomputed_endpoint_powerlaw_raw(endpoint,command,clock)


def test_saved_complete_split_replay_calls_no_producer(controls,monkeypatch):
    def deny(*a,**kw):raise AssertionError('producer called during replay')
    for name in dir(native):
        if name.startswith('native_'):monkeypatch.setattr(native,name,deny)
    for (cfg,old,faces),(new,r) in controls.values():assert audit(cfg,old,new,r,faces=faces,dt_s=DT,impulses_J=Q)['valid']


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_recomputed_certificate_preserves_legacy_control_aggregates(controls,mode):
    from tcad.core import _endpoint_mb as legacy
    from tcad.postprocess.boltzmann_endpoint_powerlaw import split_mb_endpoint_powerlaw as old_split,scaled_powerlaw_aggregates as old_values
    (_,old,_),(new,r)=controls[mode]
    for mid,collision in zip(r['transported_states'],r['collisions']):
        command=collision['command'];clock=mid['physical_clock'];endpoint=mid['endpoint']
        old_packet=legacy.native_mb_endpoint_powerlaw_raw(endpoint,command,clock)
        a=old_split(old_packet);b=split_mb_recomputed_endpoint_powerlaw(collision['root_packet'])
        assert a['chosen']==b['chosen'] and a['history']==b['history']
        assert old_values(a['proof'])==scaled_powerlaw_aggregates(b['proof'])
        assert int(b['proof'][4])==3 and b['evidence']<=a['evidence']
        from tcad.postprocess.boltzmann_recomputed_endpoint_collision import _records,_uncached_expected
        fixed=[command[14],*b['chosen'][1:],*command[15:]]
        records,details=_records(tuple(endpoint),tuple(fixed))
        assert records==tuple(_uncached_expected(endpoint,fixed))
        assert _records.cache_info().maxsize==8
        details=collision['independent_audit']['root']['full_fixed_tau_audit']
        assert details['all_division_remainders_independently_recomputed']
        assert details['all_division_remainders_serialized'] is False


@pytest.mark.parametrize('damage',['legacy_version','records','expanded','stored','budget','blocker','aggregate_value'])
def test_recompute_proof_rejects_false_work_and_aggregate_certificates(controls,damage):
    (_,_,_),(_,report)=controls['isolated'];mid=report['transported_states'][0];collision=report['collisions'][0]
    parts=split_mb_recomputed_endpoint_powerlaw(collision['root_packet']);proof=parts['proof'].copy()
    fixed=[collision['command'][14],*parts['chosen'][1:],*collision['command'][15:]]
    if damage=='legacy_version':proof[0]='mb_endpoint_collision_compact_v1'
    elif damage=='records':proof[3]=str(int(proof[3])-1)
    elif damage=='expanded':proof[6]='0'
    elif damage=='stored':proof[4]='0'
    elif damage=='budget':proof[5]='0'
    elif damage=='blocker':proof[7]='lineage0.1'
    else:proof[-2]='0x1'
    with pytest.raises((ValueError,ArithmeticError)):
        audit_mb_recomputed_endpoint_collision_compact(mid['endpoint'],fixed,proof)
