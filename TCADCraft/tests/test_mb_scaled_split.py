from copy import deepcopy
from dataclasses import asdict,replace,FrozenInstanceError
from pathlib import Path
import json
import pytest

from tcad.core import _scaled_mb as native
from tcad.solver.boltzmann_scaled_split import advance_mb_scaled_split_interval as advance,MBScaledFiniteVolumeState
from tcad.postprocess.boltzmann_scaled_split import audit_mb_scaled_split_interval as audit,audit_mb_scaled_state,_saved_fingerprint
from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState
from tcad.solver.boltzmann_frozen_finite_volume import MBFiniteVolumeState
from tests.test_mb_split_interval import problem,DT
from tests.test_mb_scaled_powerlaw import original,problem as raw_problem

ROOT=Path(__file__).resolve().parents[1]
Q=((2e-19,-1e-19,3e-19),(0.,0.,0.))


def case(mode):
    cfg,initial,faces=problem(mode)
    data=json.loads((ROOT/'docs/validation/mb_affine_range_witness_20261024/captured'/mode/'states.json').read_text())
    old=[]
    for raw in data['first']:
        anchor=MBParticleEnergyState(**raw['anchor'])
        old.append(MBFiniteVolumeState(**{**raw,'anchor':anchor}))
    faces=[{**f,'reservoir':replace(f['reservoir'],time_s=old[0].time_s)} if 'reservoir' in f else f for f in faces]
    return cfg,tuple(old),faces


@pytest.fixture(scope='session')
def results():
    return {mode:(lambda c:(c,advance(*c,DT,impulses_J=Q)))(case(mode)) for mode in ('closed','contact','mixed')}


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_original_second_spatial_interval_committed_with_all_rows(results,mode):
    (cfg,old,faces),(new,report)=results[mode]
    assert native.precision_bits==113
    assert all(type(s) is MBScaledFiniteVolumeState and s.time_s==old[0].time_s+DT for s in new)
    check=audit(cfg,old,new,report,faces=faces,dt_s=DT,impulses_J=Q)
    assert check['valid'] and check['whole_interval_particle_energy_closed']
    assert check['physical_clock_advanced_once'] and check['source_and_contact_ownership_checked']
    assert all(c['valid'] for c in check['cells']) and len(check['global_residuals'])==6
    assert report['state_commit_integrated'] and not report['complete_device_energy'] and not report['physical_validated']


@pytest.mark.parametrize('mode,cell',[(m,c) for m in ('closed','contact','mixed') for c in (0,1)])
def test_original_endpoint_command_and_deep_state_are_preserved(results,mode,cell):
    _,(new,report)=results[mode];state=new[cell];endpoint,command,clock=original(mode,cell)
    assert list(state.collision.source_endpoint)==endpoint
    # All command scalar values are checked by the independent interval audit.
    assert len(state.collision.command)==len(command)==18
    check=audit_mb_scaled_state(state)
    assert check['valid'] and check['scaled_components_preserved']
    assert check['collision']['root_trials']==9
    assert list(state.physical_clock)==list(state.collision.start_clock)
    assert state.collision.end_clock!=state.physical_clock


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_contact_transfer_is_owned_once_and_internal_faces_cancel(results,mode):
    (cfg,old,faces),(new,report)=results[mode];check=report['independent_audit']
    values=list(map(float,check['outward_contact_transfers']))
    assert (any(x!=0 for x in values))==(mode!='closed')
    assert check['source_and_contact_ownership_checked']


@pytest.mark.parametrize('damage',['clock','clock_wire','increment','source','dt','config','endpoint','missing_cell','transport','boundary','metadata','interval'])
def test_rehashed_saved_interval_forgeries_rejected(results,damage):
    (cfg,old,faces),(new,report)=results['mixed'];raw=list(map(asdict,new));r=deepcopy(report)
    if damage=='clock':raw[0]['time_s']+=DT
    elif damage=='clock_wire':raw[0]['physical_clock']=raw[0]['collision']['end_clock']
    elif damage=='increment':raw[0]['collision']['lattice_increment']=('mb_scaled_value_v1','113','0')
    elif damage in ('source','dt','config'):
        c=list(raw[0]['collision']['command']);c[{'source':15,'dt':14,'config':6}[damage]]='0.7';raw[0]['collision']['command']=c
    elif damage=='endpoint':raw[0]['collision']['source_endpoint']=raw[1]['collision']['source_endpoint']
    elif damage=='missing_cell':raw.pop()
    elif damage=='transport':r['transported_states'][0]['electron_energy_density_change']=('1e-19',)
    elif damage=='boundary':r['transport']['transfers'][-1]['integrated'][2]=['0']
    elif damage=='metadata':r['complete_device_energy']=True
    else:r['physical_interval_s'][1]+=DT
    r['new_sha256']=list(map(_saved_fingerprint,raw))
    try:check=audit(cfg,old,raw,r,faces=faces,dt_s=DT,impulses_J=Q)
    except (ValueError,ArithmeticError):return
    assert not check['valid']


@pytest.mark.parametrize('damage',['cell2_native_failure','final_audit_failure','negative_dt','source_count','unsynchronized','scaled_input'])
def test_transaction_failure_returns_no_partial_state(results,monkeypatch,damage):
    import tcad.solver.boltzmann_scaled_split as module
    (cfg,old,faces),(new,r)=results['closed'];before=list(map(asdict,old));q=Q;dt=DT
    if damage=='cell2_native_failure':
        real=native.native_mb_scaled_powerlaw_raw;calls=[]
        def fail_second(*args):
            calls.append(1)
            if len(calls)==2:raise ValueError('injected second-cell failure')
            return real(*args)
        monkeypatch.setattr(native,'native_mb_scaled_powerlaw_raw',fail_second)
    elif damage=='final_audit_failure':monkeypatch.setattr(module,'audit_mb_scaled_split_interval',lambda *a,**kw:{'valid':False})
    elif damage=='negative_dt':dt=-DT
    elif damage=='source_count':q=Q[:1]
    elif damage=='unsynchronized':old=(old[0],replace(old[1],time_s=old[1].time_s+DT));before=list(map(asdict,old))
    else:old=new;before=list(map(asdict,old))
    with pytest.raises(ValueError):advance(cfg,old,faces,dt,impulses_J=q)
    assert list(map(asdict,old))==before


@pytest.mark.parametrize('damage',['numeric','generator','oversize','nul','long','missing','extreme_a'])
def test_binding_rejects_bad_inputs_without_mutation(damage):
    args=[list(x) for x in raw_problem()]
    if damage=='numeric':args[0][1]=1
    elif damage=='generator':args[0]=iter(args[0])
    elif damage=='oversize':args[0]=['0']*25001
    elif damage=='nul':args[0][1]='1\0'
    elif damage=='long':args[0][1]='1'*65
    elif damage=='missing':args[2]=[]
    else:args[1][6]='-20000'
    with pytest.raises(ValueError):native.native_mb_scaled_powerlaw_raw(*args)


def test_saved_replay_uses_no_native_or_solver(results,monkeypatch):
    import tcad.core._bindings as legacy
    import tcad.solver.boltzmann_scaled_split as split
    import tcad.solver.boltzmann_nonisothermal_transport as transport
    def deny(*a,**kw):raise AssertionError('producer called during saved replay')
    for module in (legacy,native):
        for name in dir(module):
            if name.startswith('native_') and callable(getattr(module,name)):monkeypatch.setattr(module,name,deny)
    monkeypatch.setattr(split,'advance_mb_scaled_split_interval',deny)
    monkeypatch.setattr(transport,'advance_mb_nonisothermal_transport',deny)
    for (cfg,old,faces),(new,r) in results.values():
        assert audit(cfg,old,new,r,faces=faces,dt_s=DT,impulses_J=Q)['valid']


def test_committed_state_is_immutable(results):
    _,(new,r)=results['closed']
    with pytest.raises(FrozenInstanceError):new[0].time_s+=DT
    with pytest.raises(FrozenInstanceError):new[0].collision.root_packet=()
