from copy import deepcopy
from fractions import Fraction
import json
import pytest
from tcad.solver.boltzmann_rounded_trajectory import advance_mb_rounded_trajectory
from tcad.postprocess.boltzmann_time_refinement import audit_mb_time_refinement as audit
from tcad.postprocess.boltzmann_rounded_trajectory import trajectory_contract,record_digest
from tests.test_mb_accounted_rounding import case,thermal,DT,Q


@pytest.fixture(scope='module')
def levels():
    cfg,old,faces=case('mixed');contracts=[];records=[]
    for level in range(4):
        factor=1<<level;lines=[]
        new,r=advance_mb_rounded_trajectory(cfg,old,faces,thermal('mixed'),DT/factor,factor,
            impulses_J=[[x/factor for x in q] for q in Q],record_sink=lines.append)
        contracts.append(json.loads(lines[0])['contract']);records.append([json.loads(x) for x in lines[1:]])
    return contracts,records


def test_four_levels_recompute_full_proofs_and_compare_same_clock(levels):
    contracts,records=levels;r=audit(contracts,records)
    assert r['levels']==4 and r['steps']==[1,2,4,8] and r['common_time_samples']==1
    assert len(r['maximum_temperature_differences_K'])==3 and len(r['observed_orders'])==2
    assert r['exact_source_power_matched'] and r['exact_common_clocks_matched']
    assert all(a['valid'] and a['all_actual_prefix_energy_closed'] for a in r['independent_trajectory_audits'])
    assert not any(r[k] for k in ('temporal_order_qualified','discretization_error_bound_established','physical_validated','complete_device_energy'))


@pytest.mark.parametrize('number',[0,1,2,6])
def test_rejects_insufficient_or_excessive_levels(number):
    with pytest.raises(ValueError,match='three to five'):audit([{}]*number,[[]]*number)


def test_stream_count_must_match_contracts(levels):
    c,r=levels
    with pytest.raises(ValueError,match='three to five'):audit(c,r[:-1])


@pytest.mark.parametrize('damage',['dt','steps','source','initial','faces','thermal','budget','metadata','extra'])
def test_contract_mismatch_rejected_before_consuming_records(levels,damage):
    c,r=deepcopy(levels)
    if damage=='dt':c[1]['dt_s']*=1.01
    elif damage=='steps':c[1]['steps']+=1
    elif damage=='source':c[1]['impulses_J'][0][0]*=1.01
    elif damage=='initial':c[1]['initial']=deepcopy(c[0]['initial']);c[1]['initial'][0]['time_s']+=DT
    elif damage=='faces':c[1]['faces'][0]['geometry'][0]*=1.01
    elif damage=='thermal':c[1]['thermal_faces'][0]['geometry'][0]*=1.01
    elif damage=='budget':c[1]['energy_atol_J']/=2
    elif damage=='metadata':c[1]['physical_validated']=True
    elif damage=='extra':c[1]['extra']=0
    def forbidden():raise AssertionError('stream consumed before contract rejection');yield
    with pytest.raises(ValueError):audit(c,[forbidden() for _ in c])


@pytest.mark.parametrize('damage',['missing','extra','endpoint','source_proof'])
def test_rehashed_saved_physical_forgeries_are_independently_rejected(levels,damage):
    c,r=deepcopy(levels)
    if damage=='missing':r[2].pop()
    elif damage=='extra':r[2].append(deepcopy(r[2][-1]));r[2][-1]['index']+=1
    elif damage=='endpoint':r[2][0]['new'][0]['endpoint']=deepcopy(c[2]['initial'][0]['endpoint'])
    elif damage=='source_proof':r[2][0]['report']['conducting']['carrier_split']['collisions'][0]['command'][0]='0'
    previous=record_digest(c[2])
    for row in r[2]:
        row['previous_sha256']=previous;row['sha256']=record_digest({k:v for k,v in row.items() if k!='sha256'});previous=row['sha256']
    with pytest.raises((ValueError,AssertionError)):audit(c,r)


def test_each_stream_is_consumed_once(levels):
    c,r=levels
    class Once:
        def __init__(self,rows):self.rows=rows;self.called=False
        def __iter__(self):
            assert not self.called;self.called=True;yield from self.rows
    assert audit(c,[Once(rows) for rows in r])['valid']


def test_sample_resource_budget_rejects_before_reading(levels):
    c,r=deepcopy(levels);contracts=[]
    for level,x in enumerate(c[:3]):
        initial=x['initial']*16;cfg=x['configurations']*16
        contracts.append(trajectory_contract(cfg,initial,x['faces'],x['thermal_faces'],DT/(1<<level),256*(1<<level),
            impulses_J=x['impulses_J']*16))
    with pytest.raises(ValueError,match='sample budget'):audit(contracts,[iter(()) for _ in contracts])


@pytest.mark.parametrize('exponent',[-4000,4000])
def test_observed_order_avoids_float_ratio_underflow_and_overflow(exponent):
    from tcad.postprocess.boltzmann_time_refinement import _observed_order
    r=Fraction(1<<exponent) if exponent>0 else Fraction(1,1<<(-exponent))
    assert _observed_order(r)==exponent


def test_controls_are_snapshotted_before_arbitrary_streams_run(levels):
    c,r=deepcopy(levels)
    def mutate():
        c[1]['impulses_J'][0][0]*=2
        yield from r[0]
    result=audit(c,[mutate(),*r[1:]])
    assert result['valid'] and result['exact_source_power_matched']


def test_yielded_rows_are_detached_before_iterator_can_mutate_them(levels):
    c,r=deepcopy(levels)
    def mutate():
        for row in r[2]:
            yield row
            row['new'][0]['endpoint']=deepcopy(c[2]['initial'][0]['endpoint'])
            row['new'][0]['time_s']=1.
    result=audit(c,[r[0],r[1],mutate(),r[3]])
    assert result['valid'] and result['full_interval_proofs_recomputed']
