from pathlib import Path
import copy
import json
import os
import shutil
import subprocess

import pytest

from tcad.postprocess.boltzmann_scaled_collision_trace import audit_mb_scaled_collision_trace as audit

ROOT=Path(__file__).resolve().parents[1]


def simple(en='1000',ep='-2000',sources=('0','0','0'),tail=None):
    groups=[['1e25','1e25','300','1000','1e-20','0','0','150','700','0'],
            [en],[ep],[] if tail is None else [tail],[],[],[]]
    endpoint=[s for group in groups for s in (str(len(group)),*group)]
    command=['2e-14','3e-13','2e-13',*sources]
    return endpoint,command


def original(index):
    case=json.loads((ROOT/'tests/data/mb_product_range_witness.json').read_text())['cases'][index]
    path=ROOT/'docs/validation/mb_affine_range_witness_20261024/captured'/case['mode']/f'cell{case["cell"]}.txt'
    tokens=path.read_text().split();endpoint=tokens[1:1+int(tokens[0])]
    diagnostic=json.loads((ROOT/case['diagnostic_record']).read_text())
    command=next(line.split()[1:] for line in diagnostic['stderr'].splitlines() if line.startswith('COLLISION_COMMAND '))
    return endpoint,command


@pytest.fixture(scope='session')
def probe(tmp_path_factory):
    path=os.environ.get('TCAD_MB_SCALED_COLLISION_TRACE_PROBE')
    if path: return Path(path).resolve(strict=True)
    compiler=shutil.which('g++')
    if compiler is None: pytest.skip('standalone binary113 collision trace needs g++/libquadmath')
    binary=tmp_path_factory.mktemp('collision_trace')/'probe'
    subprocess.run([compiler,'-std=gnu++17','-O2','-I',str(ROOT/'src'),
                    str(ROOT/'tests/cpp/mb_scaled_collision_trace_probe.cpp'),'-lquadmath','-o',str(binary)],
                   capture_output=True,text=True,check=True,timeout=120)
    return binary


@pytest.fixture
def run(probe):
    def call(args,accepted=True):
        before=copy.deepcopy(args)
        raw='\n'.join(s for group in args for s in (str(len(group)),*group))+'\n'
        r=subprocess.run([str(probe)],input=raw,text=True,capture_output=True,timeout=60)
        assert r.returncode==(0 if accepted else 2),r.stderr
        assert args==before
        if not accepted:
            assert not r.stdout
            return r.stderr
        wire=r.stdout.splitlines()
        return wire,audit(*args,wire)
    return call


@pytest.mark.parametrize('sources',[('0','0','0'),('2e-19','0','0'),('0','-1e-19','0'),
                                   ('0','0','3e-19'),('2e-19','-1e-19','3e-19')])
def test_full_electron_hole_and_source_lineages_pass_physical_energy_gate(run,sources):
    _,report=run(simple(sources=sources))
    assert report['full_fixed_tau_trace_audited']
    assert report['full_fixed_tau_energy_gate_passed']
    assert report['completed_lineages']==2+sum(x!='0' for x in sources)
    assert not report['state_committed'] and not report['physical_time_advanced']


def test_zero_exchange_and_no_sources_is_a_complete_empty_lineage_transaction(run):
    _,report=run(simple('0','0'))
    assert report['full_fixed_tau_energy_gate_passed'] and report['completed_lineages']==0


@pytest.mark.parametrize('tail',['1e-100','-1e-100','1e-300','-1e-300'])
def test_density_tail_inputs_are_exactly_replayed_and_budget_remains_explicit(run,tail):
    _,report=run(simple(tail=tail))
    assert report['evidence_components']<=4096
    assert report['full_fixed_tau_trace_audited'] or report['requested_components']>4096


@pytest.mark.parametrize('index',range(5))
def test_original_second_interval_inputs_have_independently_audited_budget_stop(run,index):
    _,report=run(original(index))
    assert report['status']=='evidence_budget_exceeded'
    assert report['requested_components']>4096
    assert not report['full_fixed_tau_energy_gate_passed']
    assert not report['state_committed']


@pytest.mark.parametrize('damage',['version','precision','status','count','payload','label','value','remainder','truncated','extra'])
def test_tampered_trace_is_rejected_independently(run,damage):
    args=simple();wire,_=run(args);bad=wire.copy()
    if damage=='version':bad[0]='mb_scaled_collision_trace_v2'
    elif damage=='precision':bad[1]='64'
    elif damage=='status':bad[2]='accepted'
    elif damage=='count':bad[3]=str(int(bad[3])+1)
    elif damage=='payload':bad[4]=str(int(bad[4])+1)
    elif damage=='label':bad[7]='thermal'
    elif damage=='value':
        j=next(j for j,s in enumerate(bad) if s.startswith('0x'));bad[j]='0x1'
    elif damage=='remainder':
        j=9+int(bad[8]);bad[j:j+4]=['5','mb_scaled_value_v1','113','1','0x1','0']
    elif damage=='truncated':bad.pop()
    else:bad.append('0')
    with pytest.raises(ValueError):audit(*args,bad)


@pytest.mark.parametrize('damage',['false_complete','wrong_blocker','wrong_requested','within_budget'])
def test_budget_stop_cannot_be_promoted_to_success_or_falsified(run,damage):
    args=original(0);wire,_=run(args);bad=wire.copy()
    if damage=='false_complete':bad[2]='complete';bad[5]='-';bad[6]='0'
    elif damage=='wrong_blocker':bad[5]='lineage99.0'
    elif damage=='wrong_requested':bad[6]=str(int(bad[6])+1)
    else:bad[6]='4096'
    with pytest.raises(ValueError):audit(*args,bad)


@pytest.mark.parametrize('damage',['negative_dt','zero_tau','short_command','trailing_endpoint','negative_volume'])
def test_invalid_input_rejected_atomically(run,damage):
    args=list(simple());args[0]=args[0].copy();args[1]=args[1].copy()
    if damage=='negative_dt':args[1][0]='-1'
    elif damage=='zero_tau':args[1][1]='0'
    elif damage=='short_command':args[1].pop()
    elif damage=='trailing_endpoint':args[0].append('0')
    else:args[0][5]='-1'
    run(args,False)
