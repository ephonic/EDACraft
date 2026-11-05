from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import json
import pytest
from tcad.solver.boltzmann_weak_trajectory import advance_mb_weak_trajectory as advance
from tcad.postprocess.boltzmann_weak_trajectory import audit_mb_weak_trajectory as audit,weak_trajectory_contract,SCOPE
from tcad.postprocess.boltzmann_rounded_trajectory import canonical_bytes,record_digest
from tcad.postprocess.boltzmann_recomputed_transport import _wire,scaled_value_fraction
from tcad.postprocess.boltzmann_weak_space_time import _validated_grid
from docs.validation.mb_weak_trajectory_20261024.cases import control,ROOT,PARENT

@pytest.fixture(scope='module')
def cases():
    result={}
    for mode in ('isolated','closed','contact','mixed'):
        c,old,faces=control(mode);lines=[];before=list(map(asdict,old))
        new,report=advance(c['configurations'],old,faces,c['thermal_faces'],c['dt_s'],c['steps'],impulses_J=c['impulses_J'],record_sink=lines.append,checkpoint_stride=1)
        assert before==list(map(asdict,old))
        header,*rows=map(json.loads,lines);assert len(rows)==3
        result[mode]=(c,old,new,report,header['contract'],rows)
    return result

@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_complete_weak_intervals_have_all_six_rows_and_every_prefix(cases,mode):
    c,old,new,report,contract,rows=cases[mode];check=audit(contract,iter(rows),checkpoint_stride=1)
    assert check==report['independent_audit'] and check['accepted_steps']==3
    assert check['all_actual_prefix_energy_closed'] and check['cumulative_error_allowance_enforced']
    assert len(check['checkpoints'])==3 and all(len(x['global_residuals'])==6 for x in check['checkpoints'])
    assert contract['scope']==SCOPE and not check['complete_device_energy'] and not check['physical_validated']
    for index,row in enumerate(rows,1):
        assert all(s['physical_clock']==_wire(Fraction(c['dt_s'])*index) for s in row['new'])
        b=row['report']['conducting']['carrier_split']
        assert all(s['physical_clock']==_wire(Fraction(c['dt_s'])*(index+1)) for s in b['collision_states'])
        assert row['report']['independent_audit']['physical_clock_advanced_once']

def test_first_full_interval_contains_same_weak_collisions_as_phase161(cases):
    c,old,new,report,contract,rows=cases['mixed'];saved=json.loads((ROOT/'docs/validation/mb_weak_collision_20261024/captured.json').read_bytes())['cases'][0]
    b=rows[0]['report']['conducting']['carrier_split']
    for local,packet,aux in zip(saved['collisions'],b['collisions'],b['collision_states']):
        assert local['report']['root_packet']==packet['root_packet'] and local['new']==aux
    assert rows[0]['report']['conducting']['lattice']['faces']

def rechain(contract,rows):
    previous=record_digest(contract)
    for row in rows:
        row['previous_sha256']=previous;row['sha256']=record_digest({k:v for k,v in row.items() if k!='sha256'});previous=row['sha256']

@pytest.mark.parametrize('damage',['clock','aux_clock','projection','source','root','lattice','rounding','metadata','configuration','bath','contact','coverage'])
def test_rehashed_full_interval_physics_forgeries_are_rejected(cases,damage):
    c,old,new,report,contract,rows=cases['mixed'];contract=deepcopy(contract);rows=deepcopy(rows);r=rows[-1]['report'];b=r['conducting']['carrier_split']
    if damage=='clock':rows[-1]['new'][0]['time_s']*=2
    elif damage=='aux_clock':b['collision_states'][0]['physical_clock']=rows[-1]['new'][0]['physical_clock'];b['collision_states'][0]['time_s']=rows[-1]['new'][0]['time_s']
    elif damage=='projection':r['conducting']['pre_lattice_states'][0]=b['collision_states'][0]
    elif damage=='source':contract['impulses_J'][0][0]*=2
    elif damage=='root':b['collisions'][0]['root_packet'][0]='mb_recomputed_endpoint_powerlaw_v1'
    elif damage=='lattice':r['conducting']['lattice']['faces'][0][-1]='wrong'
    elif damage=='rounding':r['rounding']['cells'][0][-1]='wrong'
    elif damage=='metadata':r['complete_device_energy']=True
    elif damage=='configuration':contract['configurations'][0]['parameters'][6]='0.7'
    elif damage=='bath':contract['thermal_faces'][-1]['bath_temperature_K']=301.
    elif damage=='contact':contract['faces'][-1]['geometry'][0]*=2
    else:b['collisions'].pop()
    rechain(contract,rows)
    with pytest.raises((ValueError,ArithmeticError)):audit(contract,iter(rows))

@pytest.mark.parametrize('damage',['missing','extra','wrong_scope','skip_index'])
def test_journal_protocol_and_coverage_fail_closed(cases,damage):
    c,old,new,report,contract,rows=cases['mixed'];contract=deepcopy(contract);rows=deepcopy(rows)
    if damage=='missing':rows.pop()
    elif damage=='extra':rows.append(deepcopy(rows[-1]));rows[-1]['index']+=1
    elif damage=='wrong_scope':contract['scope']='accounted_rounded_trajectory_v1'
    else:rows[1]['index']+=1
    rechain(contract,rows)
    with pytest.raises(ValueError):audit(contract,iter(rows))

def test_iterator_cannot_shorten_declared_trajectory(cases):
    c,old,new,report,contract,rows=cases['mixed'];contract=deepcopy(contract)
    def source():
        contract['steps']=1
        yield deepcopy(rows[0])
    with pytest.raises(ValueError,match='missing records'):audit(contract,source())

def test_iterator_cannot_mutate_previous_private_row(cases):
    c,old,new,report,contract,rows=cases['mixed'];rows=deepcopy(rows)
    def source():
        yield rows[0]
        rows[0]['new'][0]['time_s']=100.
        yield rows[1]
        yield rows[2]
    assert audit(contract,source())['valid']

def test_second_interval_failure_preserves_inputs_and_only_partial_journal(monkeypatch):
    import tcad.solver.boltzmann_weak_interval as interval
    c,old,faces=control();before=list(map(asdict,old));real=interval.advance_mb_weak_endpoint_collision;calls=[];lines=[]
    def fail(*args,**kw):
        calls.append(1)
        if len(calls)==3:raise ValueError('injected second interval')
        return real(*args,**kw)
    monkeypatch.setattr(interval,'advance_mb_weak_endpoint_collision',fail)
    with pytest.raises(ValueError,match='injected second interval'):advance(c['configurations'],old,faces,c['thermal_faces'],c['dt_s'],3,impulses_J=c['impulses_J'],record_sink=lines.append)
    assert before==list(map(asdict,old)) and len(lines)==2
    header,row=map(json.loads,lines)
    with pytest.raises(ValueError,match='missing records'):audit(header['contract'],[row])

def grid():
    data=json.loads((PARENT/'jobs_v2.json').read_bytes());result=[]
    for row in data['contract_grid']:
        c=row[2];new=weak_trajectory_contract(c['configurations'],c['initial'],c['faces'],c['thermal_faces'],c['dt_s']/2,c['steps']*2,impulses_J=[[x/2 for x in q] for q in c['impulses_J']])
        result.append([row[1],c,new])
    return data,result

def test_mixed_version_grid_matches_full_physical_controls():
    data,g=grid();owned,n=_validated_grid(g,data['length_m'],data['area_m2']);assert n==5760 and owned==g

@pytest.mark.parametrize('damage',['constant_law','version','source_power','initial_metadata'])
def test_mixed_version_grid_rejects_incompatible_controls(damage):
    data,g=grid()
    if damage=='constant_law':
        for row in g:
            for c in row:
                for cfg in c['configurations']:
                    for k in (6,7,10,11):cfg['parameters'][k]='0'
    elif damage=='version':g[0][2]['scope']='unknown'
    elif damage=='source_power':g[0][2]['impulses_J'][0][0]*=2
    else:g[0][2]['physical_validated']=True
    with pytest.raises(ValueError):_validated_grid(g,data['length_m'],data['area_m2'])

def test_independent_trajectory_does_not_call_native(cases,monkeypatch):
    from tcad.core import _weak_collision_mb,_lattice_mb,_recomputed_lattice_mb,_accounted_rounding_mb,_scaled_transport
    def deny(*args,**kw):raise AssertionError('native forbidden')
    for module in (_weak_collision_mb,_lattice_mb,_recomputed_lattice_mb,_accounted_rounding_mb,_scaled_transport):
        for name in vars(module):
            if name.startswith('native_') or name in ('face','bath','cell','endpoint'):monkeypatch.setattr(module,name,deny)
    c,old,new,report,contract,rows=cases['mixed'];assert audit(contract,iter(rows))['valid']
