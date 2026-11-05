from pathlib import Path
import os
import shutil
import subprocess

import pytest

from tests.test_mb_scaled_collision_trace import simple,original
from tcad.postprocess.boltzmann_scaled_collision_compact import audit_mb_scaled_collision_compact as audit
from tcad.postprocess.boltzmann_scaled_collision_trace import audit_mb_scaled_collision_trace as audit_trace

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def probes(tmp_path_factory):
    result={};folder=tmp_path_factory.mktemp('compact_collision')
    for kind in ('compact','trace'):
        supplied=os.environ.get('TCAD_MB_SCALED_COLLISION_'+kind.upper()+'_PROBE')
        if supplied: result[kind]=Path(supplied).resolve(strict=True);continue
        compiler=shutil.which('g++')
        if compiler is None:pytest.skip('standalone binary113 probes need g++/libquadmath')
        binary=folder/kind
        subprocess.run([compiler,'-std=gnu++17','-O2','-I',str(ROOT/'src'),
                        str(ROOT/f'tests/cpp/mb_scaled_collision_{kind}_probe.cpp'),'-lquadmath','-o',str(binary)],
                       capture_output=True,text=True,check=True,timeout=120)
        result[kind]=binary
    return result


@pytest.fixture
def run(probes):
    def call(args,kind='compact',accepted=True):
        raw='\n'.join(s for group in args for s in (str(len(group)),*group))+'\n'
        r=subprocess.run([str(probes[kind])],input=raw,text=True,capture_output=True,timeout=60)
        assert r.returncode==(0 if accepted else 2),r.stderr
        if not accepted:assert not r.stdout;return
        wire=r.stdout.splitlines()
        return wire,(audit if kind=='compact' else audit_trace)(*args,wire)
    return call


def aggregates(wire,kind):
    cursor=9 if kind=='compact' else 7
    result={}
    while cursor<len(wire):
        label=wire[cursor];cursor+=1
        if kind=='compact':cursor+=1
        n=int(wire[cursor]);value=wire[cursor+1:cursor+1+n];cursor+=n+1
        if kind=='trace':n=int(wire[cursor]);cursor+=n+1
        if label.startswith('aggregate.'):result[label]=value
    return result


@pytest.mark.parametrize('index',range(5))
def test_original_second_interval_full_fixed_tau_graph_and_energy_now_fit_saved_proof(run,index):
    args=original(index)
    wire,report=run(args)
    _,legacy=run(args,'trace')
    assert legacy['status']=='evidence_budget_exceeded'
    assert report['full_fixed_tau_energy_gate_passed'] and report['full_final_temperature_bounds_passed']
    assert report['all_division_remainders_retained']
    assert report['evidence_components']<=4096<report['expanded_trace_components']
    assert report['completed_lineages']>=2
    assert set(aggregates(wire,'compact'))=={'aggregate.L','aggregate.un','aggregate.up'}
    assert not report['state_committed'] and not report['nonlinear_root_audited']


@pytest.mark.parametrize('sources',[('0','0','0'),('2e-19','0','0'),('0','-1e-19','0'),
                                   ('0','0','3e-19'),('2e-19','-1e-19','3e-19')])
def test_compact_candidate_is_bit_exact_with_complete_legacy_trace(run,sources):
    args=simple(sources=sources)
    compact,report=run(args);legacy,old=run(args,'trace')
    assert aggregates(compact,'compact')==aggregates(legacy,'trace')
    assert report['expanded_trace_components']==old['evidence_components']
    assert report['arithmetic_records_independently_recomputed']==old['records_audited']
    assert report['full_fixed_tau_energy_gate_passed']


def test_zero_equilibrium_still_has_explicit_zero_division_checkpoints(run):
    _,report=run(simple('0','0'))
    assert report['completed_lineages']==0 and report['saved_checkpoints']==9
    assert report['division_remainder_checkpoints']==6 and report['all_division_remainders_retained']


@pytest.mark.parametrize('tail',['1e-100','-1e-100','1e-300','-1e-300'])
def test_density_microtails_survive_full_replay(run,tail):
    _,report=run(simple(tail=tail))
    assert report['full_fixed_tau_energy_gate_passed']


@pytest.mark.parametrize('damage',['version','precision','status','records','stored','payload','expanded',
                                  'label','kind','remainder','truncated','extra'])
def test_checkpoint_tampering_or_missing_division_evidence_is_rejected(run,damage):
    args=simple();wire,_=run(args);bad=wire.copy()
    if damage=='version':bad[0]='mb_scaled_collision_compact_v2'
    elif damage=='precision':bad[1]='64'
    elif damage=='status':bad[2]='accepted'
    elif damage in ('records','stored','payload','expanded'):
        index={'records':3,'stored':4,'payload':5,'expanded':6}[damage];bad[index]=str(int(bad[index])+1)
    elif damage=='label':bad[9]='source0'
    elif damage=='kind':bad[10]='aggregate_value'
    elif damage=='remainder':
        # Substitute an actual nonzero saved division remainder, retaining
        # valid canonical value grammar so this tests exact numerical replay.
        j=next(j for j,s in enumerate(bad) if s.startswith(('0x','-0x')))
        bad[j]='0x1' if bad[j]!='0x1' else '0x3'
    elif damage=='truncated':bad.pop()
    else:bad.append('0')
    with pytest.raises(ValueError):audit(*args,bad)


@pytest.mark.parametrize('damage',['negative_dt','zero_tau','short_command','trailing_endpoint','negative_volume'])
def test_invalid_input_rejected_before_output(run,damage):
    args=list(simple());args[0]=args[0].copy();args[1]=args[1].copy()
    if damage=='negative_dt':args[1][0]='-1'
    elif damage=='zero_tau':args[1][1]='0'
    elif damage=='short_command':args[1].pop()
    elif damage=='trailing_endpoint':args[0].append('0')
    else:args[0][5]='-1'
    run(args,accepted=False)
