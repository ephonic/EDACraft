"""State history must survive public NumPy writes and Python round trips."""
from copy import copy, deepcopy
from dataclasses import fields, replace
import pickle
import numpy as np
import pytest

from tcad.solver.cut_cell_transport import CutCellState
from tcad.solver.fermi_electrothermal import FermiSpectralState
from tcad.solver.three_temperature import ThreeTemperatureState
from tcad.solver.device_three_temperature import DeviceThreeTemperature
from test_adaptive_three_temperature import closed, OPTIONS
from test_three_temperature import BUDGET
from test_device_three_temperature import assert_owned
from test_structured_three_temperature import structured_case

TYPES = (CutCellState, FermiSpectralState, ThreeTemperatureState)
SHARED = ('n_m3','p_m3','trap_fraction','temperature_K')
NAMES = SHARED+('electron_temperature_K','hole_temperature_K')
PAIRS = [(cls, name) for cls in TYPES for name in (NAMES if cls is ThreeTemperatureState else SHARED)]


def make(cls):
    density = np.array([np.longdouble('1e25'), np.nextafter(np.longdouble('1e25'), np.longdouble(np.inf))])
    values = dict(n_m3=density, p_m3=density[::-1], trap_fraction=np.array([.3,.4]),
                  temperature_K=np.array([300.,310.]), time_s=2e-12)
    if cls is ThreeTemperatureState:
        values.update(electron_temperature_K=np.array([360.,370.]), hole_temperature_K=np.array([260.,270.]))
    return cls(**values), values


def assert_frozen(state):
    for f in fields(state):
        if f.name == 'time_s':continue
        a = getattr(state, f.name)
        assert not a.flags.writeable and memoryview(a).readonly
        with pytest.raises(ValueError):a.flags.writeable = True
        with pytest.raises(ValueError):a.flat[0] = 0


@pytest.mark.parametrize('cls,name', PAIRS)
def test_write_flag_array_views_and_memoryviews_cannot_modify_state(cls, name):
    state, values = make(cls); a = getattr(state, name); expected = a.copy()
    for alias in (a, a.view(), np.asarray(a), a.reshape(-1)):
        with pytest.raises(ValueError):alias.setflags(write=True)
        with pytest.raises(ValueError):alias[0] = 0
        assert memoryview(alias).readonly
    with pytest.raises(TypeError):memoryview(a).cast('B')[0] = 0
    working = a.copy(); working[0] = 0
    np.testing.assert_array_equal(a, expected)
    assert not np.shares_memory(a, values[name])


@pytest.mark.parametrize('cls', TYPES)
def test_inputs_remain_mutable_and_detached_and_density_precision_is_preserved(cls):
    state, values = make(cls)
    expected = {f.name:getattr(state,f.name).copy() for f in fields(state) if f.name != 'time_s'}
    for name, a in values.items():
        if name != 'time_s':a[:] = 1
    for name, a in expected.items():np.testing.assert_array_equal(getattr(state,name), a)
    if cls is not CutCellState:
        assert state.n_m3.dtype == np.dtype(np.longdouble)
        if np.finfo(np.longdouble).nmant > np.finfo(float).nmant:
            assert np.any(state.n_m3 != state.n_m3.astype(float).astype(np.longdouble))
            assert state.n_m3[0] != state.n_m3[1]
    assert_frozen(state)


@pytest.mark.parametrize('cls', TYPES)
@pytest.mark.parametrize('clone', [copy, deepcopy, replace])
def test_copy_deepcopy_and_dataclass_replace_reconstruct_frozen_detached_state(cls, clone):
    state, _ = make(cls); new = clone(state)
    assert type(new) is cls and new is not state and new.time_s == state.time_s
    assert_frozen(new)
    for f in fields(state):
        if f.name == 'time_s':continue
        a, b = getattr(state,f.name), getattr(new,f.name)
        np.testing.assert_array_equal(a, b)
        assert a.dtype == b.dtype and not np.shares_memory(a, b)
    pair = deepcopy([state,state]); assert pair[0] is pair[1]


@pytest.mark.parametrize('cls', TYPES)
@pytest.mark.parametrize('protocol', range(pickle.HIGHEST_PROTOCOL+1))
def test_all_pickle_protocols_restore_frozen_fields_and_exact_density_values(cls, protocol):
    state, _ = make(cls); new = pickle.loads(pickle.dumps(state, protocol=protocol))
    assert type(new) is cls and new.time_s == state.time_s
    assert_frozen(new)
    for f in fields(state):np.testing.assert_array_equal(getattr(state,f.name),getattr(new,f.name))


@pytest.mark.parametrize('cls', TYPES)
def test_protocol5_writable_out_of_band_buffers_cannot_alias_restored_state(cls):
    state, _ = make(cls); buffers=[]
    payload=pickle.dumps(state, protocol=5, buffer_callback=buffers.append)
    supplied=[bytearray(b.raw()) for b in buffers]
    new=pickle.loads(payload,buffers=supplied)
    for b in supplied:b[:] = bytes(len(b))
    assert_frozen(new)
    for f in fields(state):np.testing.assert_array_equal(getattr(state,f.name),getattr(new,f.name))


@pytest.mark.parametrize('mode', ['fixed','adaptive','trajectory'])
def test_all_native_entry_paths_keep_accepted_and_trial_history_frozen(mode):
    model, initial=closed(); device=DeviceThreeTemperature(model,initial)
    assert_frozen(initial); assert_frozen(device.state)
    if mode == 'fixed':final, report=device.advance(1e-15,**BUDGET)
    elif mode == 'adaptive':final, report=device.advance_adaptive(1e-15,**OPTIONS)
    else:
        report=device.run_transient([0.,1e-15],initial_step_s=1e-13,maximum_step_s=1e-13,**OPTIONS)
        final=report['final_state']; assert report['trajectory_energy_audit']['valid']
    def walk(value):
        if isinstance(value,CutCellState):assert_frozen(value)
        elif isinstance(value,dict):
            for v in value.values():walk(v)
        elif isinstance(value,(list,tuple)):
            for v in value:walk(v)
    walk(report); walk(deepcopy(report)); walk(pickle.loads(pickle.dumps(report)))
    assert_owned(device,final)


def test_mutation_attempt_in_precommit_hook_cannot_damage_rollback_or_later_retry():
    model, initial=closed(); device=DeviceThreeTemperature(model,initial)
    before=deepcopy(device.native_state()); old=device.state
    def reject(report):
        assert_frozen(old)
        raise RuntimeError('rejected after blocked public state mutation')
    device._decorate_report=reject
    with pytest.raises(RuntimeError,match='blocked public state mutation'):
        device.advance(1e-15,**BUDGET)
    assert device.state is old and device.native_state() == before
    device._decorate_report=lambda r: None
    final, _=device.advance(1e-15,**BUDGET)
    assert_owned(device,final); assert_frozen(old); assert_frozen(final)


def test_structured_migration_and_public_empty_trajectory_preserve_immutable_cell_state():
    source,initial,material=structured_case((3,1,1),contacts=True)
    before=source._sim.structured_three_temperature_seed()
    r=source.run_three_temperature(initial,[initial.time_s],**material,
        initial_step_s=1e-13,maximum_step_s=1e-13,**{k:v for k,v in OPTIONS.items() if k not in BUDGET})
    assert source._sim.structured_three_temperature_seed() == before
    assert_frozen(initial); assert_frozen(r['initial_state']); assert_frozen(r['final_state'])
    assert r['trajectory_energy_audit']['valid']; assert_owned(r['device'],r['final_state'])
