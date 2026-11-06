"""Explicit cache release bounds factor lifetime without changing history."""
import copy
import gc
import weakref

import numpy as np
import pytest

from test_sheet_reused_gmres import device, transient
from test_sheet_coupled import assert_state_equal, check_fluxes


def assert_physics_equal(a,b):
    for key in ('phi_V','Fn_eV','Fp_eV','dielectric_phi_V','trap_occupancy'):
        np.testing.assert_allclose(a[key],b[key],rtol=0.,atol=1e-10)
    for key in ('n_m2','p_m2'):
        np.testing.assert_allclose(a[key],b[key],rtol=1e-9,atol=0.)
    for key,floor in (('contact_charge_C',1e-26),('terminal_total_currents_A',1e-15)):
        for terminal in a[key]:
            np.testing.assert_allclose(a[key][terminal],b[key][terminal],rtol=1e-8,atol=floor)
    assert a['accepted']==b['accepted'] and a['time_s']==b['time_s']


def test_release_dc_cache_preserves_state_and_releases_sole_factor_reference():
    run=transient();state=run.state;drive=copy.deepcopy(run._drive)
    factor=weakref.ref(run._device._linear_factor)
    assert factor() is not None
    assert run.clear_linear_cache() is True
    gc.collect()
    assert factor() is None
    assert run.clear_linear_cache() is False
    assert run.time_s==0. and run._drive==drive
    assert_state_equal(run.state,state)


@pytest.mark.parametrize('contact,material',(('linear','graphene'),('thermionic','mos2'),('dirac','graphene')))
def test_cleared_cache_rebuild_matches_retained_cache_and_independent_fluxes(contact,material):
    retained=transient(device(contact=contact,material=material));cleared=copy.deepcopy(retained)
    for dt,gate in ((2e-12,.025),(2e-12,-.01),(1e-12,.015)):
        assert cleared.clear_linear_cache()
        expected=retained.step(dt_s=dt,top_gate_voltage_V=gate,drain_voltage_V=.003,tolerance=1e-12,max_iter=120)
        result=cleared.step(dt_s=dt,top_gate_voltage_V=gate,drain_voltage_V=.003,tolerance=1e-12,max_iter=120)
        assert result['accepted'];check_fluxes(cleared._device,result)
        assert_physics_equal(result,expected)
        stats=cleared.state['linear_solver_diagnostics']
        assert stats['factorizations']==1 and not stats['reused_initial_factor']
        assert stats['max_accepted_true_scaled_residual_linf']<=1e-14
    following=cleared.step(dt_s=1e-12,top_gate_voltage_V=.016,tolerance=1e-12)
    assert following['linear_solver_diagnostics']['factorizations']==0


def test_release_does_not_mutate_factor_shared_with_another_driver():
    run=transient();other=copy.deepcopy(run);factor=other._device._linear_factor
    assert run._device._linear_factor is factor
    run.clear_linear_cache()
    assert other._device._linear_factor is factor
    state=other.step(dt_s=2e-12,top_gate_voltage_V=.015,tolerance=1e-12)
    assert state['accepted']


@pytest.mark.parametrize('failure',('factorization','nonlinear'))
def test_failure_after_explicit_release_retains_accepted_history(monkeypatch,failure):
    import tcad.solver._sheet_linear as linear
    run=transient();reference=copy.deepcopy(run);run.clear_linear_cache()
    state=run.state;drive=copy.deepcopy(run._drive)
    with monkeypatch.context() as m:
        if failure=='factorization':
            def fail(*a,**k):raise MemoryError('injected factor allocation failure')
            m.setattr(linear,'splu',fail)
            with pytest.raises(MemoryError,match='factor allocation'):
                run.step(dt_s=2e-12,top_gate_voltage_V=.025,tolerance=1e-12)
        else:
            result=run.step(dt_s=2e-12,top_gate_voltage_V=.2,drain_voltage_V=.04,max_iter=1,tolerance=1e-12)
            assert not result['accepted']
    assert run._device._linear_factor is None and run.time_s==0. and run._drive==drive
    assert_state_equal(run.state,state)
    actual=run.step(dt_s=2e-12,top_gate_voltage_V=.015,tolerance=1e-12)
    expected=reference.step(dt_s=2e-12,top_gate_voltage_V=.015,tolerance=1e-12)
    assert_physics_equal(actual,expected)


def test_direct_backend_without_newton_cache_is_noop():
    run=transient(device(method='direct'));state=run.state
    assert run.clear_linear_cache() is False
    assert_state_equal(run.state,state)
