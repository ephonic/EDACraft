from copy import deepcopy
from dataclasses import asdict,replace,FrozenInstanceError
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import json,math
import pytest
from tcad.core import _scaled_transport as native
from tcad.solver.boltzmann_scaled_candidate import MBScaledCollisionCandidate
from tcad.solver.boltzmann_scaled_split import MBScaledFiniteVolumeState
from tcad.solver.boltzmann_particle_energy import MBParticleEnergyState
from tcad.solver.boltzmann_scaled_transport import (
    materialize_mb_scaled_state,advance_mb_scaled_transport as advance,project_mb_scaled_reservoir_clock,MBScaledTransportState,
)
from tcad.postprocess.boltzmann_scaled_transport import (
    point,face_values,split_cell,audit_mb_scaled_transport as audit,scaled_value_fraction,_decode,
    _saved_fingerprint,_wire,audit_scaled_endpoint_import,
)

ROOT=Path(__file__).resolve().parents[1];DT=2e-14


def original(mode):
    r=json.loads((ROOT/'docs/validation/mb_scaled_split_20261024/captured'/(mode+'.json')).read_text())
    sources=[MBScaledFiniteVolumeState(MBScaledCollisionCandidate(**s['collision']),s['time_s'],s['physical_clock']) for s in r['new']]
    converted=[materialize_mb_scaled_state(s) for s in sources];states=tuple(s for s,c in converted);faces=[]
    for f in r['faces']:
        if 'reservoir' in f:
            reservoir,_=materialize_mb_scaled_state(MBParticleEnergyState(**f['reservoir']))
            f={**f,'reservoir':project_mb_scaled_reservoir_clock(reservoir,states[0])}
        faces.append(f)
    return sources,converted,states,faces


@pytest.fixture(scope='session')
def results():
    return {mode:(lambda c:(c,advance(c[2],c[3],DT)))(original(mode)) for mode in ('closed','contact','mixed')}


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_original_third_transport_substage_commits_full_state_and_clock(results,mode):
    (sources,converted,old,faces),(new,r)=results[mode]
    check=audit(old,new,r,faces=faces,dt_s=DT)
    assert native.precision_bits==113 and check['valid'] and check['whole_transport_particle_energy_closed']
    assert not r['collision_included'] and not r['complete_device_energy']
    for a,b in zip(old,new):
        assert scaled_value_fraction(b.physical_clock)-scaled_value_fraction(a.physical_clock)==Fraction(DT)
        assert point(a.endpoint)['values'][:3]==point(b.endpoint)['values'][:3]
        assert point(a.endpoint)['Tl']==point(b.endpoint)['Tl']


@pytest.mark.parametrize('mode,cell',[(m,c) for m in ('closed','contact','mixed') for c in (0,1)])
def test_materialization_retains_original_deep_components_exactly(results,mode,cell):
    (sources,converted,old,faces),_=results[mode];source=sources[cell];state,check=converted[cell];c=source.collision
    assert check['exact_materialization']
    assert audit_scaled_endpoint_import(c.source_endpoint,[c.lattice_increment,c.electron_energy_increment,c.hole_energy_increment],state.endpoint)['valid']
    before=point(state.endpoint)
    assert list(state.physical_clock)==list(source.physical_clock)
    if (mode,cell)!=('contact',1):
        assert min(int(e) for e in _wire(before['values'][5])[4::2]) < -13400


@pytest.mark.parametrize('mode',['closed','contact','mixed'])
def test_transport_owns_boundary_once_and_preserves_lattice(results,mode):
    _,(new,r)=results[mode];check=r['independent_audit']
    assert check['internal_faces_cancelled'] and check['exact_clock_advanced_once']
    assert (any(Decimal(x)!=0 for x in check['outward_contact_transfers']))==(mode!='closed')
    assert Decimal(check['global_residuals'][4])==0


@pytest.mark.parametrize('damage',['frame','lost_tail','clock','cell_proof','face_proof','geometry','source','topology','metadata','missing_cell'])
def test_rehashed_transport_forgeries_are_rejected(results,damage):
    (sources,converted,old,faces),(new,r)=results['mixed'];raw=list(map(asdict,new));report=deepcopy(r);faces=deepcopy(faces)
    if damage=='frame':
        p=list(raw[0]['endpoint']);p[6]='1001';raw[0]['endpoint']=p
    elif damage=='lost_tail':
        p=list(raw[0]['endpoint']);j=next(i for i,x in enumerate(p) if x.startswith(('0x','-0x')));p[j]='0x1';raw[0]['endpoint']=p
    elif damage=='clock':raw[0]['physical_clock']=old[0].physical_clock
    elif damage=='cell_proof':report['cells'][0][-1]='0'
    elif damage=='face_proof':report['transfers'][0]['raw'][-1]='0'
    elif damage=='geometry':faces[0]['geometry']=[1e-17,1e-8,2e-8,.1,.2]
    elif damage=='source':report['transfers'][-1]['raw']=report['transfers'][0]['raw']
    elif damage=='topology':faces[0]['neighbor']=0
    elif damage=='metadata':report['collision_included']=True
    else:raw.pop()
    report['new_sha256']=list(map(_saved_fingerprint,raw))
    try:check=audit(old,raw,report,faces=faces,dt_s=DT)
    except (ValueError,ArithmeticError):return
    assert not check['valid']


@pytest.mark.parametrize('damage',['second_cell','final_audit','clock','duplicate','negative_dt'])
def test_failed_transport_is_atomic(results,monkeypatch,damage):
    import tcad.solver.boltzmann_scaled_transport as solver
    (sources,converted,old,faces),_=results['closed'];before=list(map(asdict,old));dt=DT
    if damage=='second_cell':
        real=native.native_mb_scaled_cell_raw;calls=[]
        def second(*args):
            calls.append(1)
            if len(calls)==2:raise ValueError('injected second cell failure')
            return real(*args)
        monkeypatch.setattr(native,'native_mb_scaled_cell_raw',second)
    elif damage=='final_audit':monkeypatch.setattr(solver,'audit_mb_scaled_transport',lambda *a,**kw:{'valid':False})
    elif damage=='clock':old=(old[0],replace(old[1],physical_clock=_wire(Fraction(1e-13)),time_s=1e-13));before=list(map(asdict,old))
    elif damage=='duplicate':faces=[*faces,*faces]
    else:dt=-DT
    with pytest.raises(ValueError):advance(old,faces,dt)
    assert list(map(asdict,old))==before


def test_saved_transport_replay_calls_no_producer(results,monkeypatch):
    import tcad.solver.boltzmann_scaled_transport as solver
    def deny(*a,**kw):raise AssertionError('producer called during saved replay')
    for name in dir(native):
        if name.startswith('native_'):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(solver,'advance_mb_scaled_transport',deny)
    for (sources,converted,old,faces),(new,r) in results.values():assert audit(old,new,r,faces=faces,dt_s=DT)['valid']


def simple(bands=('0','0')):
    source=MBParticleEnergyState(('1e25','1e25','300','1000','1e-20',*bands,'150','700','0'),('1000',),('-2000',),0.,'test')
    return materialize_mb_scaled_state(source)[0]


@pytest.mark.parametrize('bands',[('0','0'),('1e-21','-1e-21')])
def test_zero_flux_repetition_and_exact_clock(bands):
    a=simple(bands);states=(a,a);faces=[dict(owner=0,neighbor=1,geometry=(1e-18,1e-8,2e-8,.1,.2))]
    for step in range(4):states,r=advance(states,faces,DT)
    assert states[0].endpoint==a.endpoint and scaled_value_fraction(states[0].physical_clock)==4*Fraction(DT)
    assert all(Decimal(x)==0 for x in r['independent_audit']['global_residuals'])


@pytest.mark.parametrize('bands',[('0','0'),('1e-21','-1e-21')])
def test_nonzero_closed_flux_with_fixed_bands(bands):
    a=simple(bands)
    source=MBParticleEnergyState(('1e25','1e25','300','1000','1e-20',*bands,'150','700','0'),('2000',),('-1000',),0.,'test')
    b,_=materialize_mb_scaled_state(source)
    new,r=advance((a,b),[dict(owner=0,neighbor=1,geometry=(1e-18,1e-8,2e-8,.1,.2))],DT)
    assert new[0].endpoint!=a.endpoint and r['independent_audit']['whole_transport_particle_energy_closed']


def test_heterogeneous_capacity_volume_and_lattice_are_preserved():
    from tests.test_mb_nonisothermal_transport import heterogeneous,EDGE
    a,b=heterogeneous();states=tuple(materialize_mb_scaled_state(s)[0] for s in (a,b))
    new,r=advance(states,[EDGE],1e-18)
    assert r['independent_audit']['whole_transport_particle_energy_closed']
    assert point(states[0].endpoint)['Tl']!=point(states[1].endpoint)['Tl']
    for a,b in zip(states,new):assert point(a.endpoint)['values'][0]==point(b.endpoint)['values'][0]


@pytest.mark.parametrize('damage',['wrong_view','noncanonical_partition'])
def test_clock_constructor_requires_exact_view_and_canonical_partition(damage):
    a=simple()
    if damage=='wrong_view':clock=a.physical_clock;view=math.ulp(0.)
    else:
        value=Fraction(1+(1<<100)+(1<<200));view=float(value)
        clock=('mb_scaled_value_v1','113','2','0x1','0',hex(1+(1<<100)),'100')
    with pytest.raises(ValueError):MBScaledTransportState(a.endpoint,view,clock)


def test_saved_state_is_immutable(results):
    _,(new,r)=results['closed']
    with pytest.raises(FrozenInstanceError):new[0].endpoint=()


@pytest.mark.parametrize('damage',['negative_dt','extra_endpoint','bad_precision','empty_clock','nonstring'])
def test_native_wire_errors_rejected(results,damage):
    (sources,converted,old,faces),_=results['closed'];endpoint=list(old[0].endpoint);command=['2e-14'];clock=list(old[0].physical_clock)
    if damage=='negative_dt':command=['-1']
    elif damage=='extra_endpoint':endpoint.append('0')
    elif damage=='bad_precision':endpoint[1]='64'
    elif damage=='empty_clock':clock=[]
    else:endpoint[0]=0
    with pytest.raises(ValueError):native.native_mb_scaled_cell_raw(endpoint,['mb_scaled_transfers_v1','113','0'],command,clock)
