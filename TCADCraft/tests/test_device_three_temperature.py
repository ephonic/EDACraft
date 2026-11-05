"""C++ device-owned state, scoped geometry, audited commit and failed retry."""
from copy import deepcopy
import numpy as np
import pytest
from test_three_temperature import case, BUDGET
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from tcad.solver.native_three_temperature_dispatch import pack_three_temperature_inputs
from tcad.core._bindings import PyDeviceSimulator


def assert_owned(device, state):
    native = device.native_state()
    for raw, field, dtype in [('n','n_m3',np.longdouble),('p','p_m3',np.longdouble),
            ('temperature_n','electron_temperature_K',float),('temperature_p','hole_temperature_K',float),
            ('temperature_l','temperature_K',float)]:
        np.testing.assert_array_equal(np.asarray(native[raw], dtype), getattr(state, field))
    assert native['time_s'] == state.time_s


@pytest.mark.parametrize('options', [dict(),dict(contacts=True,voltage=.002),
    dict(contacts=True,voltage=-.002,density_scale=10),dict(contacts=True,voltage=.002,count=4),
    dict(contacts=True,voltage=.002,reverse=True),dict(contacts=True,voltage=.002,nonuniform=True)])
def test_device_two_steps_match_dispatch_reference_and_own_all_five_fields(options):
    model, old = case(**options)
    device = DeviceThreeTemperature(model, old)
    reference = old
    assert_owned(device, old)
    for _ in range(2):
        reference, _ = model.step(reference, 2e-13, **BUDGET)
        state, report = device.advance(2e-13, **BUDGET)
        assert report['independent_audit']['valid']
        assert report['main_DeviceSimulator_scoped_three_temperature_integrated']
        assert not report['legacy_StructuredGrid_three_temperature_integrated']
        assert not report['complete_device_energy'] and not report['physical_validated']
        for field in ('temperature_K','electron_temperature_K','hole_temperature_K'):
            np.testing.assert_allclose(getattr(state, field),getattr(reference, field),rtol=0,atol=1e-6)
        for field in ('n_m3','p_m3'):
            np.testing.assert_allclose(getattr(state,field),getattr(reference,field),rtol=1e-10)
        assert_owned(device,state)


@pytest.mark.parametrize('failure', ['newton','audit','decode'])
def test_failed_candidate_never_changes_accepted_state_and_retry_matches_fresh(monkeypatch, failure):
    model, old = case(contacts=True,voltage=.002)
    device = DeviceThreeTemperature(model, old)
    before = deepcopy(device.native_state())
    with monkeypatch.context() as patch:
        if failure == 'audit':
            patch.setattr('tcad.postprocess.three_temperature_energy.audit_three_temperature_energy',
                          lambda *a,**k:dict(valid=False,reason='injected independent audit rejection'))
        elif failure == 'decode':
            def reject(*a,**k): raise ValueError('injected exported output rejection')
            patch.setattr('tcad.solver.device_three_temperature.decode_three_temperature_output', reject)
        with pytest.raises((ValueError,RuntimeError)):
            device.advance(2e-13, **BUDGET, max_nfev=1 if failure=='newton' else 600)
    assert device.native_state() == before
    assert device.state.time_s == old.time_s
    state, _ = device.advance(2e-13, **BUDGET)
    fresh, _ = DeviceThreeTemperature(model, old).advance(2e-13, **BUDGET)
    for field in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        np.testing.assert_array_equal(getattr(state,field),getattr(fresh,field))
    assert_owned(device,state)


def test_native_device_owns_immutable_configuration_and_tokenized_candidate():
    model, old = case()
    backend = PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    packed = pack_three_temperature_inputs(model,old,1.,2e-28,1e-9,1e-27)
    backend.configure_three_temperature(*packed,old.time_s)
    before = backend.three_temperature_state()
    with pytest.raises(RuntimeError,match='immutable'):backend.configure_three_temperature(*packed,old.time_s)
    raw, token = backend.prepare_three_temperature(2e-13,2e-28,1e-9,1e-27)
    assert backend.three_temperature_state() == before
    with pytest.raises(RuntimeError,match='pending'):backend.prepare_three_temperature(2e-13,2e-28,1e-9,1e-27)
    with pytest.raises(RuntimeError,match='stale'):backend.commit_three_temperature(token+1)
    backend.discard_three_temperature(token)
    with pytest.raises(RuntimeError,match='stale'):backend.commit_three_temperature(token)
    raw2, token2 = backend.prepare_three_temperature(2e-13,2e-28,1e-9,1e-27)
    assert raw == raw2 and token2 > token
    with pytest.raises(RuntimeError,match='stale'):backend.discard_three_temperature(token)
    backend.commit_three_temperature(token2)
    assert backend.three_temperature_state()['time_s'] == 2e-13
    result=backend.three_temperature_result()
    for key,field in [('Tn_K','temperature_n'),('Tp_K','temperature_p'),('Tl_K','temperature_l')]:
        np.testing.assert_array_equal(result[key],raw2[field])
    with pytest.raises(RuntimeError,match='legacy'):backend.solve()
    assert backend.three_temperature_state()['time_s']==2e-13
    assert backend.three_temperature_result()==result


def test_model_snapshot_and_density_low_bits_are_preserved():
    model, old = case(count=1,uniform=True)
    from tcad.solver.three_temperature import ThreeTemperatureState
    density = np.array([np.longdouble('10000000000000000000000001')])
    old = ThreeTemperatureState(density,density,old.trap_fraction,old.temperature_K,0.,
                                old.electron_temperature_K,old.hole_temperature_K)
    device = DeviceThreeTemperature(model,old)
    model.tau_n[:] = 1e-5
    assert_owned(device,old)
    state,_ = device.advance(2e-13,**BUDGET)
    np.testing.assert_array_equal(state.n_m3,density)
    assert_owned(device,state)


def test_scoped_device_does_not_call_free_dispatch_entry(monkeypatch):
    model,old = case()
    device = DeviceThreeTemperature(model,old)
    def forbidden(*a,**k):raise AssertionError('free dispatch must not own this step')
    monkeypatch.setattr('tcad.core._bindings.native_three_temperature_dispatch_raw',forbidden)
    state,report = device.advance(2e-13,**BUDGET)
    assert report['independent_audit']['valid']
    assert_owned(device,state)


def test_initial_state_is_an_owned_immutable_copy_and_configuration_edits_are_rejected():
    model,old=case()
    device=DeviceThreeTemperature(model,old)
    assert device.state is not old
    for field in ('n_m3','p_m3','temperature_K','electron_temperature_K','hole_temperature_K'):
        assert not getattr(device.state,field).flags.writeable
        assert not np.shares_memory(getattr(device.state,field),getattr(old,field))
    before=device.native_state()
    device._model.tau_n[:]=1e-10
    with pytest.raises(ValueError,match='immutable'):device.advance(2e-13,**BUDGET)
    assert device.native_state()==before


@pytest.mark.parametrize('dt', [0.,-1.,float('nan'),float('inf')])
def test_native_invalid_step_leaves_no_pending_candidate(dt):
    model,old=case()
    backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    backend.configure_three_temperature(*pack_three_temperature_inputs(model,old,1.,2e-28,1e-9,1e-27),0.)
    before=backend.three_temperature_state()
    with pytest.raises(ValueError):backend.prepare_three_temperature(dt,2e-28,1e-9,1e-27)
    assert backend.three_temperature_state()==before
    _,token=backend.prepare_three_temperature(2e-13,2e-28,1e-9,1e-27)
    backend.discard_three_temperature(token)


@pytest.mark.parametrize('damage', ['cell_count','clock','parameters','temperature','tau'])
def test_native_configuration_rejection_is_retryable(damage):
    model,old = case()
    args = list(pack_three_temperature_inputs(model,old,1.,2e-28,1e-9,1e-27))
    args = deepcopy(args);time=0.
    if damage=='cell_count':args[0]=args[0][21:]
    elif damage=='clock':time=float('nan')
    elif damage=='parameters':args[-1][0]=-1.
    elif damage=='temperature':args[0][17]='0'
    else:args[0][19]='0'
    backend=PyDeviceSimulator(model.nc,1,1,1.,1.,1.)
    with pytest.raises(ValueError):backend.configure_three_temperature(*args,time)
    backend.configure_three_temperature(*pack_three_temperature_inputs(model,old,1.,2e-28,1e-9,1e-27),0.)
    assert backend.three_temperature_state()['time_s']==0.
