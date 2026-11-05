"""Native ownership, signed-energy restart and audited atomic transactions."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pytest
from test_energy_coordinate_transport import transport_case,BUDGET
from test_three_temperature import case
from tcad.core._bindings import PyDeviceSimulator
from tcad.solver.energy_coordinate_transport import initialize_energy_coordinates,energy_coordinate_step,_pack
from tcad.solver.device_energy_coordinate_transport import DeviceEnergyCoordinateTransport as Device
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.postprocess.device_energy_coordinate_transport import audit_device_energy_coordinate_step


def assert_owned(device):
    snapshot=device.native_state();state=device.state;t=snapshot['raw']['transport']
    assert snapshot['time_s']==state.thermal.time_s and tuple(snapshot['raw']['excess'])==state.excess_J_m3
    for key,field,dtype in (('n','n_m3',np.longdouble),('p','p_m3',np.longdouble),('temperature_n','electron_temperature_K',float),
        ('temperature_p','hole_temperature_K',float),('temperature_l','temperature_K',float)):
        np.testing.assert_array_equal(np.asarray(t[key],dtype),getattr(state.thermal,field))
        assert not getattr(state.thermal,field).flags.writeable


@pytest.mark.parametrize('count,a,c',[(1,-20000,20000),(2,-20000,20000),(2,0,0),(2,-.4,.3)])
def test_two_owned_steps_match_functional_raw_results_exactly(count,a,c):
    model,initial=transport_case(count,a,c);device=Device(model,initial)
    expected=initialize_energy_coordinates(model,initial);assert_owned(device)
    for dt in (2e-14,3e-14):
        old=device.state;expected,r=energy_coordinate_step(model,expected,dt,**BUDGET)
        actual,report=device.advance(dt,**BUDGET)
        assert report['raw']==r['raw'] and actual.excess_J_m3==expected.excess_J_m3
        assert audit_device_energy_coordinate_step(model,old,actual,report,**BUDGET)['valid']
        assert report['native_device_session_integrated'] and report['independent_audit']['native_device_session_integrated']
        assert not report['complete_device_energy'] and not report['physical_validated'];assert_owned(device)
        if a==-20000:assert any(0<abs(Decimal(e))<Decimal('1e-70') for e in actual.excess_J_m3)


def test_restart_keeps_sub_temperature_resolution_energy_and_future_step_exact():
    model,initial=transport_case();device=Device(model,initial)
    checkpoint,_=device.advance(2e-14,**BUDGET)
    restarted=Device(model,checkpoint)
    assert restarted.state.excess_J_m3==checkpoint.excess_J_m3
    assert any(0<abs(Decimal(e))<Decimal('1e-100') for e in checkpoint.excess_J_m3)
    actual,r=device.advance(3e-14,**BUDGET);again,rr=restarted.advance(3e-14,**BUDGET)
    assert actual.excess_J_m3==again.excess_J_m3 and r==rr;assert_owned(restarted)


@pytest.mark.parametrize('failure',['budget','audit','decode','publication','interrupt'])
def test_failure_preserves_accepted_native_state_and_retry_is_identical(monkeypatch,failure):
    model,initial=transport_case();device=Device(model,initial);old=device.state;before=device.native_state()
    def reject(*a,**k):raise ValueError('injected candidate decoding failure')
    def allocation(*a,**k):raise MemoryError('injected publication allocation failure')
    def interrupt(*a,**k):raise KeyboardInterrupt('injected interruption')
    with monkeypatch.context() as patch:
        if failure=='audit':patch.setattr('tcad.postprocess.device_energy_coordinate_transport.audit_device_energy_coordinate_step',lambda *a,**k:dict(valid=False))
        elif failure=='decode':patch.setattr('tcad.solver.device_energy_coordinate_transport._view',reject)
        elif failure=='publication':patch.setattr(device,'_publication',allocation)
        elif failure=='interrupt':patch.setattr(device,'_publication',interrupt)
        with pytest.raises((ValueError,RuntimeError,MemoryError,KeyboardInterrupt)):
            device.advance(2e-14,max_nfev=1 if failure=='budget' else 600,**BUDGET)
    assert device.state is old and device.native_state()==before
    retry,r=device.advance(2e-14,**BUDGET);fresh,rr=Device(model,initial).advance(2e-14,**BUDGET)
    assert r==rr and retry.excess_J_m3==fresh.excess_J_m3;assert_owned(device)


def test_native_tokens_pending_state_discard_and_commit_are_exact():
    model,initial=transport_case();device=Device(model,initial);backend=device._backend;before=backend.energy_coordinate_state()
    packed,_=_pack(model,initial,1.,**BUDGET)
    with pytest.raises(RuntimeError,match='immutable'):backend.configure_energy_coordinate(*packed,device.state.excess_J_m3,0.)
    one,token=backend.prepare_energy_coordinate(2e-14,**BUDGET)
    assert backend.energy_coordinate_state()==before
    with pytest.raises(RuntimeError,match='pending'):backend.prepare_energy_coordinate(2e-14,**BUDGET)
    with pytest.raises(RuntimeError,match='stale'):backend.commit_energy_coordinate(token+1)
    backend.discard_energy_coordinate(token)
    with pytest.raises(RuntimeError,match='stale'):backend.commit_energy_coordinate(token)
    two,token2=backend.prepare_energy_coordinate(2e-14,**BUDGET)
    assert one==two and token2>token
    with pytest.raises(RuntimeError,match='stale'):backend.discard_energy_coordinate(token)
    backend.commit_energy_coordinate(token2)
    assert backend.energy_coordinate_state()==two
    with pytest.raises(ValueError,match='accepted'):device.advance(2e-14,**BUDGET)


def test_invalid_native_requests_leave_no_hidden_pending_candidate():
    model,initial=transport_case();device=Device(model,initial);b=device._backend;before=b.energy_coordinate_state()
    for dt,q,p,e,budget in [(0,2e-28,1e-9,1e-27,600),(-1,2e-28,1e-9,1e-27,600),
        (float('nan'),2e-28,1e-9,1e-27,600),(float('inf'),2e-28,1e-9,1e-27,600),
        (2e-14,0,1e-9,1e-27,600),(2e-14,2e-28,-1,1e-27,600),(2e-14,2e-28,1e-9,float('nan'),600),
        (2e-14,2e-28,1e-9,1e-27,True),(2e-14,2e-28,1e-9,1e-27,0)]:
        with pytest.raises(ValueError):b.prepare_energy_coordinate(dt,q,p,e,budget)
        assert b.energy_coordinate_state()==before
    _,token=b.prepare_energy_coordinate(2e-14,**BUDGET);b.discard_energy_coordinate(token)


@pytest.mark.parametrize('damage',['cell_count','clock','parameters','temperature','law','excess'])
def test_native_configuration_rejection_is_retryable(damage):
    model,initial=transport_case();state=initialize_energy_coordinates(model,initial)
    packed,_=_pack(model,initial,1.,**BUDGET);args=deepcopy(list(packed));e=list(state.excess_J_m3);time=0.
    if damage=='cell_count':args[0]=args[0][17:]
    elif damage=='clock':time=float('nan')
    elif damage=='parameters':args[4][0]=-1
    elif damage=='temperature':args[0][10]='0'
    elif damage=='law':args[5][0]='0'
    else:e[0]='-1e10'
    b=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    with pytest.raises(ValueError):b.configure_energy_coordinate(*args,e,time)
    b.configure_energy_coordinate(*packed,state.excess_J_m3,0.)
    assert b.energy_coordinate_state()['time_s']==0.


@pytest.mark.parametrize('direction',['general_first','energy_first','isolated_first','energy_before_isolated','reliability'])
def test_modes_and_reliability_are_mutually_exclusive(direction):
    from test_isolated_relaxation import solver
    from test_isolated_relaxation_device import configure
    isolated,_,_=solver()
    model,initial=transport_case(count=1);state=initialize_energy_coordinates(model,initial)
    packed,_=_pack(model,initial,1.,**BUDGET);b=PyDeviceSimulator(1,1,1,1.,1.,1.)
    general=pack_three_temperature_inputs(model,initial,1.,**BUDGET)
    def energy():b.configure_energy_coordinate(*packed,state.excess_J_m3,0.)
    if direction=='general_first':
        b.configure_three_temperature(*general,0.)
        with pytest.raises(RuntimeError,match='another mode'):energy()
    elif direction=='energy_first':
        energy()
        with pytest.raises(RuntimeError,match='already configured'):b.configure_three_temperature(*general,0.)
    elif direction=='isolated_first':
        configure(b,isolated)
        with pytest.raises(RuntimeError,match='another mode'):energy()
    elif direction=='energy_before_isolated':
        energy()
        with pytest.raises(RuntimeError,match='another mode'):configure(b,isolated)
    else:
        b.begin_reliability_transaction()
        with pytest.raises(RuntimeError,match='reliability'):energy()
        b.rollback_reliability_transaction();energy()


def test_owned_snapshot_configuration_and_legacy_entry_boundaries():
    model,initial=transport_case();device=Device(model,initial);before=device.native_state()
    detached=device.native_state();detached['raw']['excess'][0]='0';detached['raw']['transport']['n'][0]='1'
    assert device.native_state()==before
    model.tau_n[:]=1e-5  # Source object changes cannot alter the captured model.
    b=device._backend
    for call in (b.solve,b.begin_reliability_transaction,b.structured_three_temperature_seed,b.three_temperature_result):
        with pytest.raises((RuntimeError,ValueError)):call()
    assert device.native_state()==before
    device._model.tau_n[:]=1e-4
    with pytest.raises(ValueError,match='immutable'):device.advance(2e-14,**BUDGET)
    assert device.native_state()==before


def test_device_does_not_call_free_transport_or_step_entry(monkeypatch):
    model,initial=transport_case();device=Device(model,initial)
    def deny(*a,**k):raise AssertionError('free transport entry called')
    monkeypatch.setattr('tcad.core._bindings.native_energy_coordinate_transport_raw',deny)
    monkeypatch.setattr('tcad.solver.energy_coordinate_transport.energy_coordinate_step',deny)
    device.advance(2e-14,**BUDGET);assert_owned(device)


def test_physical_clock_uses_the_actual_representable_interval():
    model,initial=transport_case(count=1,a=0,c=0);initial=replace(initial,time_s=1.)
    device=Device(model,initial);new,r=device.advance(1e-13,**BUDGET)
    assert new.thermal.time_s==1.+1e-13 and r['dt_s']==new.thermal.time_s-1.
    before=device.native_state()
    with pytest.raises(ValueError,match='clock'):device.advance(1e-31,**BUDGET)
    assert device.native_state()==before


@pytest.fixture(scope='module')
def accepted():
    model,initial=transport_case();d=Device(model,initial);old=d.state;new,r=d.advance(2e-14,**BUDGET)
    return model,old,new,r


@pytest.mark.parametrize('damage',['scope','owner','transaction','mesh','legacy','integrated','extra','physical'])
def test_device_audit_rejects_forged_transaction_envelopes(accepted,damage):
    model,old,new,r=accepted;r=deepcopy(r)
    key={'owner':'device_state_owner','transaction':'device_transaction','mesh':'device_mesh_mode',
         'legacy':'legacy_StructuredGrid_integrated','integrated':'native_device_session_integrated',
         'extra':'unmodeled_channel','physical':'physical_validated','scope':'scope'}[damage]
    r[key]=True if damage in ('legacy','extra','physical') else False if damage=='integrated' else 'wrong'
    if damage=='physical':assert not audit_device_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']
    else:
        with pytest.raises(ValueError):audit_device_energy_coordinate_step(model,old,new,r,**BUDGET)


def test_concurrent_public_steps_serialize_and_match_sequential_state():
    model,initial=transport_case(a=0,c=0);device=Device(model,initial);serial=Device(model,initial)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:device.advance(2e-14,**BUDGET),range(2)))
    serial.advance(2e-14,**BUDGET);expected,rr=serial.advance(2e-14,**BUDGET)
    assert sorted(v[0].thermal.time_s for v in results)==[2e-14,4e-14]
    assert device.state.excess_J_m3==expected.excess_J_m3 and device.native_state()==serial.native_state();assert_owned(device)


def test_device_audit_replay_is_independent_of_native_physics(accepted,monkeypatch):
    import tcad.core._bindings as native
    from tcad.material.energy_relaxation import EnergyRelaxationPowerLaw
    model,old,new,r=accepted
    def deny(*a,**k):raise AssertionError('production physics called during device audit')
    for name in dir(native):
        if name.startswith('native_') and callable(getattr(native,name)):monkeypatch.setattr(native,name,deny)
    monkeypatch.setattr(EnergyRelaxationPowerLaw,'evaluate',deny)
    for name in ('_poisson','carrier_reservoirs','split_face_transport','energies','conduction'):monkeypatch.setattr(model,name,deny)
    assert audit_device_energy_coordinate_step(model,old,new,r,**BUDGET)['valid']


def test_checkpoint_cannot_forge_a_temperature_view_or_model_identity(accepted):
    model,old,new,r=accepted
    forged=replace(new,thermal=replace(new.thermal,electron_temperature_K=new.thermal.electron_temperature_K+1))
    with pytest.raises(ValueError,match='thermal view'):Device(model,forged)
    model=deepcopy(model);model.tau_p[:]*=2
    with pytest.raises(ValueError,match='configuration'):Device(model,new)
