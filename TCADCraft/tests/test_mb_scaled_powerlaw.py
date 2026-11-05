from dataclasses import replace,FrozenInstanceError
from decimal import Decimal
from pathlib import Path
import copy,json,os,shutil,subprocess

import pytest

from tests.test_mb_scaled_collision_trace import simple
from tcad.postprocess.boltzmann_scaled_powerlaw import audit_mb_scaled_powerlaw as audit,split_mb_scaled_powerlaw
from tcad.solver.boltzmann_scaled_candidate import scaled_candidate_from_saved,audit_mb_scaled_candidate

ROOT=Path(__file__).resolve().parents[1]


def original(mode,cell):
    folder=ROOT/'docs/validation/mb_affine_range_witness_20261024/captured'/mode
    tokens=(folder/f'cell{cell}.txt').read_text().split();n=int(tokens[0]);endpoint=tokens[1:1+n]
    size=int(tokens[n+1]);command=tokens[n+2:]
    assert size==len(command)==18
    data=json.loads((folder/'states.json').read_text())
    clock=[format(Decimal.from_float(data['transported'][cell]['time_s']),'.36E')]
    return endpoint,command,clock


def problem(kind='none'):
    endpoint,fixed=simple(sources=('2e-19','-1e-19','3e-19') if kind=='sources' else ('0','0','0'))
    command=['1000','1e-20','3e-13','2e-13','150','5e24','0.6','-0.2','150','5e24','0.6','-0.2','150','700',fixed[0],*fixed[3:]]
    if kind=='constant':
        for j in (6,7,10,11):command[j]='0'
    return endpoint,command,['4e-14']


@pytest.fixture(scope='session')
def probe(tmp_path_factory):
    supplied=os.environ.get('TCAD_MB_SCALED_POWERLAW_PROBE')
    if supplied:return Path(supplied).resolve(strict=True)
    compiler=shutil.which('g++')
    if compiler is None:pytest.skip('standalone binary113 root needs g++/libquadmath')
    binary=tmp_path_factory.mktemp('scaled_root')/'probe'
    subprocess.run([compiler,'-std=gnu++17','-O2','-I',str(ROOT/'src'),
                    str(ROOT/'tests/cpp/mb_scaled_powerlaw_probe.cpp'),'-lquadmath','-o',str(binary)],
                   capture_output=True,text=True,check=True,timeout=120)
    return binary


@pytest.fixture(scope='session')
def run(probe):
    cache={}
    def call(args,accepted=True):
        before=copy.deepcopy(args);key=tuple(tuple(x) for x in args)
        if key not in cache or not accepted:
            raw='\n'.join(s for group in args for s in (str(len(group)),*group))+'\n'
            r=subprocess.run([str(probe)],input=raw,text=True,capture_output=True,timeout=180)
            assert r.returncode==(0 if accepted else 2),r.stderr
            assert args==before
            if not accepted:assert not r.stdout;return r.stderr
            cache[key]=r.stdout.splitlines()
        wire=cache[key].copy()
        return wire,audit(*args,wire)
    return call


@pytest.mark.parametrize('mode,cell',[(m,k) for m in ('closed','contact','mixed') for k in (0,1)])
def test_original_six_cells_pass_actual_state_nonlinear_BE_and_energy(run,mode,cell):
    args=original(mode,cell);wire,report=run(args)
    assert report['valid'] and report['actual_state_nonlinear_BE_passed']
    assert report['combined_saved_evidence_components']<=4096
    state,check=scaled_candidate_from_saved(*args,wire)
    assert state.source_endpoint==tuple(args[0]) and check['exact_saved_clock_identity_checked']
    assert audit_mb_scaled_candidate(state)['candidate_state_energy_audited']
    assert not report['application_state_committed'] and not report['whole_spatial_interval_audited']


@pytest.mark.parametrize('kind',['none','sources','constant'])
def test_simple_bounded_nonlinear_and_constant_laws(run,kind):
    _,report=run(problem(kind))
    assert report['valid'] and report['actual_state_constitutive_decimal_precision']==180


def test_explicit_scaled_clock_preserves_increment_beyond_scalar_ulp(run):
    args=list(problem());args[2]=['1e100']
    _,report=run(args)
    assert report['exact_saved_clock_identity_checked']


def test_equilibrium_has_no_nonlinear_exchange_rows(run):
    args=list(problem());args[0]=simple('0','0')[0]
    _,report=run(args)
    assert report['nonlinear_lineage_checks']==[] and report['valid']


@pytest.mark.parametrize('damage',['version','precision','trials','evidence','chosen','trace_tau','clock','aggregate','truncated','extra'])
def test_saved_root_forgeries_rejected_on_actual_state(run,damage):
    args=problem();wire,_=run(args);bad=wire.copy();parts=split_mb_scaled_powerlaw(wire)
    if damage=='version':bad[0]='mb_scaled_powerlaw_v2'
    elif damage=='precision':bad[1]='64'
    elif damage=='trials':bad[2]=str(int(bad[2])+1)
    elif damage=='evidence':bad[6]=str(int(bad[6])+1)
    elif damage=='chosen':bad[3]='300'
    elif damage=='trace_tau':bad[8]='1e-13'
    elif damage=='clock':
        j=7+4*parts['trials'];bad[j+4]='0x1'
    elif damage=='aggregate':
        j=max(j for j,s in enumerate(bad) if s.startswith(('0x','-0x')));bad[j]='0x1'
    elif damage=='truncated':bad.pop()
    else:bad.append('0')
    with pytest.raises(ValueError):audit(*args,bad)


@pytest.mark.parametrize('damage',['endpoint','increment','clock','command'])
def test_candidate_cannot_detach_saved_state_from_source_and_proof(run,damage):
    args=problem();wire,_=run(args);state,_=scaled_candidate_from_saved(*args,wire)
    if damage=='endpoint':
        values=list(state.source_endpoint);values[1]='2e25';state=replace(state,source_endpoint=tuple(values))
    elif damage=='increment':state=replace(state,lattice_increment=('mb_scaled_value_v1','113','0'))
    elif damage=='clock':state=replace(state,end_clock=state.start_clock)
    else:
        values=list(state.command);values[6]='0.7';state=replace(state,command=tuple(values))
    with pytest.raises(ValueError):audit_mb_scaled_candidate(state)


@pytest.mark.parametrize('damage',['extreme_a','extreme_tau','negative_clock','frame_mismatch','negative_dt','short_command','missing_clock'])
def test_invalid_or_outside_bounded_branch_rejected_atomically(run,damage):
    args=[x.copy() for x in problem()]
    if damage=='extreme_a':args[1][6]='-20000'
    elif damage=='extreme_tau':args[1][2]='1e-8'
    elif damage=='negative_clock':args[2][0]='-1'
    elif damage=='frame_mismatch':args[1][0]='999'
    elif damage=='negative_dt':args[1][14]='-1'
    elif damage=='short_command':args[1].pop()
    else:args[2]=[]
    run(args,False)


def test_saved_candidate_factory_is_immutable_and_calls_no_producer(run,monkeypatch):
    args=problem();wire,_=run(args)
    def forbidden(*a,**kw):raise AssertionError('producer called during saved state reconstruction')
    monkeypatch.setattr(subprocess,'run',forbidden)
    state,report=scaled_candidate_from_saved(*args,wire)
    assert report['valid']
    with pytest.raises(FrozenInstanceError):state.end_clock=state.start_clock
