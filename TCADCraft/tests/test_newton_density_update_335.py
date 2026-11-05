"""Explicit per-instance log-density updates, replay, and PN cold-start controls."""
import os
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator
from tcad.simulator import Simulator
from test_newton_solver import _make_1d_sim


def test_default_and_instance_isolation():
    a=PyDeviceSimulator(3,1,1,1e-9,1.,1.)
    b=PyDeviceSimulator(3,1,1,1e-9,1.,1.)
    assert a.get_newton_log_density_update()==b.get_newton_log_density_update()=='exponential'
    a.set_newton_log_density_update('additive')
    assert a.get_newton_log_density_update()=='additive'
    assert b.get_newton_log_density_update()=='exponential'
    a.set_newton_log_density_update('exponential')
    assert a.get_newton_log_density_update()=='exponential'


@pytest.mark.parametrize('bad',[None,False,True,0,1,1.0,b'additive','', 'physical','ADDITIVE','additive\0',' exponential',[],{}])
def test_invalid_policy_is_atomic(bad):
    s,mesh=_make_1d_sim()
    s.set_newton_log_density_update('additive')
    before=s.configuration_snapshot()
    with pytest.raises(ValueError):s.set_newton_log_density_update(bad)
    assert s.get_newton_log_density_update()=='additive'
    assert s.configuration_snapshot()==before


@pytest.mark.parametrize('value',['0','1','unexpected'])
def test_legacy_process_environment_has_no_control(monkeypatch,value):
    monkeypatch.setenv('TCAD_ADDITIVE_DENSITY_333',value)
    s=PyDeviceSimulator(3,1,1,1e-9,1.,1.)
    assert s.get_newton_log_density_update()=='exponential'
    s.set_newton_log_density_update('additive')
    assert s.get_newton_log_density_update()=='additive'


@pytest.mark.parametrize('route',['python','native'])
@pytest.mark.parametrize('last',['exponential','additive'])
def test_configuration_clone_replays_last_policy(route,last):
    s,mesh=_make_1d_sim()
    backend=s if route=='python' else s._sim
    backend.set_newton_log_density_update('additive' if last=='exponential' else 'exponential')
    backend.set_newton_log_density_update(last)
    clone=s.clone_on_mesh(mesh,include_initial_guess=False)
    assert clone.get_newton_log_density_update()==last
    s.set_newton_log_density_update('additive' if last=='exponential' else 'exponential')
    assert clone.get_newton_log_density_update()==last


@pytest.mark.parametrize('policy',['exponential','additive'])
@pytest.mark.parametrize('bias',[0.,.1,-.1])
@pytest.mark.parametrize('source',['source_free','SRH','optical'])
def test_PN_cold_start_policies(policy,bias,source):
    s,mesh=_make_1d_sim(vbias_p=bias,use_newton=True)
    s._sim.set_newton_primary(True)
    s.set_newton_log_space(True)
    s.set_newton_log_density_update(policy)
    if source=='SRH':s._sim.set_recombination(np.full(mesh.npts(),1e-7),np.full(mesh.npts(),1e-7))
    if source=='optical':s.set_optical_generation(np.full(mesh.npts(),1e20))
    result=s.run(max_iter=200,tol=1e-8)
    assert result['converged']
    assert all(np.all(np.isfinite(result[k])) for k in ('phi','n','p','Jn_x','Jp_x'))
    assert np.min(result['n'])>0 and np.min(result['p'])>0
    # Existing primary-PN absolute total-current-spread gate (test_newton_solver).
    current=(np.asarray(result['Jn_x'])+np.asarray(result['Jp_x']))[:-1]
    assert float(np.ptp(current))<1e-8


@pytest.mark.parametrize('policy',['exponential','additive'])
def test_PN_insufficient_iteration_budget_is_not_success(policy):
    s,_=_make_1d_sim(vbias_p=.1,use_newton=True)
    s._sim.set_newton_primary(True)
    s.set_newton_log_density_update(policy)
    result=s.run(max_iter=0,tol=1e-8)
    assert not result['converged']
