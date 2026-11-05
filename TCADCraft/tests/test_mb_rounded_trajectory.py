from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import json
import pytest
from tcad.solver.boltzmann_rounded_trajectory import advance_mb_rounded_trajectory as advance
from tcad.postprocess.boltzmann_rounded_trajectory import (
    audit_mb_rounded_trajectory as audit,record_digest,canonical_bytes,trajectory_contract,
)
from tests.test_mb_accounted_rounding import case,thermal,DT,Q


@pytest.fixture(scope='module')
def controls():
    result={}
    for mode in ('isolated','closed','contact','mixed'):
        cfg,old,faces=case(mode);lines=[]
        new,r=advance(cfg,old,faces,thermal(mode),DT,3,impulses_J=Q,record_sink=lines.append,checkpoint_stride=1)
        header=json.loads(lines[0]);rows=[json.loads(x) for x in lines[1:]]
        result[mode]=(cfg,old,faces,new,r,header,rows)
    return result


def rehash(contract,rows):
    previous=record_digest(contract)
    for row in rows:
        row['previous_sha256']=previous
        row['sha256']=record_digest({k:v for k,v in row.items() if k!='sha256'});previous=row['sha256']


@pytest.mark.parametrize('mode',['isolated','closed','contact','mixed'])
def test_streamed_full_prefix_energy_and_exact_record_replay(controls,mode):
    cfg,old,faces,new,r,header,rows=controls[mode];c=audit(header['contract'],iter(rows),checkpoint_stride=1)
    assert c==r['independent_audit'] and c['valid'] and c['accepted_steps']==3
    assert c['all_actual_prefix_energy_closed'] and c['cumulative_error_allowance_enforced']
    assert len(c['checkpoints'])==3 and c['last_record_sha256']==rows[-1]['sha256']
    assert header['contract_sha256']==record_digest(header['contract'])
    assert json.loads(canonical_bytes(list(map(asdict,new))))==rows[-1]['new']
    assert not c['physical_validated'] and not c['exact_recurrence_preserved']


@pytest.mark.parametrize('damage',['missing','extra','order','index','float_index','bool_index','previous','digest','coverage','endpoint','clock','rounding','source','geometry','material','initial','metadata'])
def test_rehashed_protocol_and_physical_forgeries_rejected(controls,damage):
    cfg,old,faces,new,r,header,source=controls['mixed'];contract=deepcopy(header['contract']);rows=deepcopy(source)
    if damage=='missing':rows.pop()
    elif damage=='extra':rows.append(deepcopy(rows[-1]))
    elif damage=='order':rows.reverse()
    elif damage=='index':rows[0]['index']=1
    elif damage=='float_index':rows[0]['index']=0.
    elif damage=='bool_index':rows[0]['index']=False
    elif damage=='previous':rows[0]['previous_sha256']='0'*64
    elif damage=='digest':rows[0]['sha256']='0'*64
    elif damage=='coverage':rows[0]['extra']=0
    elif damage=='endpoint':rows[0]['new'][0]['endpoint']=contract['initial'][0]['endpoint']
    elif damage=='clock':rows[0]['new'][0]['time_s']=1.
    elif damage=='rounding':rows[0]['report']['rounding']['cells'][0][2]='0'
    elif damage=='source':contract['impulses_J'][0][0]*=2
    elif damage=='geometry':contract['thermal_faces'][0]['geometry'][0]*=2
    elif damage=='material':contract['configurations'][0]['parameters'][6]='0.5'
    elif damage=='initial':contract['initial'][0]['endpoint']=contract['initial'][1]['endpoint']
    else:contract['exact_recurrence_preserved']=True
    if damage not in ('previous','digest'):rehash(contract,rows)
    with pytest.raises(ValueError):audit(contract,rows)


def test_cumulative_bound_exhaustion_rejects_accepted_individual_steps(controls):
    cfg,old,faces,new,r,header,source=controls['mixed'];contract=deepcopy(header['contract']);rows=deepcopy(source)
    checkpoints=r['independent_audit']['checkpoints']
    first=Decimal(checkpoints[0]['global_budgets'][-1]);second=Decimal(checkpoints[1]['global_budgets'][-1])
    contract['energy_atol_J']=float((first+second)/2);rehash(contract,rows)
    with pytest.raises(ValueError,match='cumulative trajectory error allowance exhausted'):audit(contract,rows)


@pytest.mark.parametrize('steps',[0,-1,True,1.5,16385])
def test_invalid_step_counts_fail_before_journal(steps):
    cfg,old,faces=case('mixed');lines=[]
    with pytest.raises(ValueError):advance(cfg,old,faces,thermal('mixed'),DT,steps,record_sink=lines.append)
    assert not lines


@pytest.mark.parametrize('budget',[0.,-1.,float('nan')])
def test_invalid_global_allowance_is_atomic(budget):
    cfg,old,faces=case('mixed');before=list(map(asdict,old));lines=[]
    with pytest.raises(ValueError):advance(cfg,old,faces,thermal('mixed'),DT,2,energy_atol_J=budget,record_sink=lines.append)
    assert before==list(map(asdict,old)) and not lines


def test_saved_audit_claims_never_supply_acceptance_budget(controls):
    cfg,old,faces,new,r,header,source=controls['mixed'];rows=deepcopy(source)
    for row in rows:row['report']['independent_audit']={'valid':True,'global_budgets':['1e100']*6}
    rehash(header['contract'],rows)
    c=audit(header['contract'],rows,checkpoint_stride=1)
    assert c['global_budgets']==r['independent_audit']['global_budgets']


def test_single_pass_record_iterator(controls):
    cfg,old,faces,new,r,header,rows=controls['mixed']
    class Once:
        def __init__(self):self.called=False
        def __iter__(self):
            assert not self.called;self.called=True;yield from rows
    c=audit(header['contract'],Once());assert c['accepted_steps']==3 and len(c['checkpoints'])==1


def test_child_failure_returns_no_partial_trajectory_and_preserves_inputs(monkeypatch):
    import tcad.solver.boltzmann_rounded_trajectory as module
    cfg,old,faces=case('mixed');before=list(map(asdict,old));real=module.advance_mb_rounded_conducting_split;calls=[];lines=[]
    def injected(*a,**kw):
        calls.append(1)
        if len(calls)==2:raise ValueError('injected next interval failure')
        return real(*a,**kw)
    monkeypatch.setattr(module,'advance_mb_rounded_conducting_split',injected)
    with pytest.raises(ValueError,match='injected'):advance(cfg,old,faces,thermal('mixed'),DT,3,record_sink=lines.append)
    assert list(map(asdict,old))==before and len(lines)==2 and all(type(x) is bytes for x in lines)


def test_independent_replay_calls_no_producer(controls,monkeypatch):
    import tcad.solver.boltzmann_rounded_trajectory as module
    cfg,old,faces,new,r,header,rows=controls['mixed']
    def deny(*a,**kw):raise AssertionError('producer called')
    monkeypatch.setattr(module,'advance_mb_rounded_conducting_split',deny)
    assert audit(header['contract'],rows)['valid']
