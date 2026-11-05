"""Explicit transport charge and native-bound lattice acceptance controls."""
from copy import deepcopy
import json
import sys
import numpy as np
import pytest
from tcad.core import native_constants
from tcad.postprocess.native_thermal import audit_native_lattice_mobility
from test_lattice_mobility_feedback import setup, VT
from test_audited_lattice_driver import case, driver, LatticeStepRejected

SI_Q = 1.602176634e-19
LEGACY_Q = 1.602192e-19
BUDGET = dict(fixed_point_atol_K=1e-7, current_rtol=2e-7, current_atol_A_m2=1e-7)


def audit(result, axes, model='constant', **kwargs):
    n = len(result['phi'])
    return audit_native_lattice_mobility(result, axes, np.full(n, .01), np.full(n, .005),
        np.zeros(n), model, 300., VT, **BUDGET, **kwargs)


def prescribed(axis, sign, charge):
    axes = [np.array([0.])] * 3
    axes[axis] = np.array([0., 1e-7])
    r = dict(converged=True, phi=np.array([0., sign*.02]), n=np.full(2, 1e21),
        p=np.full(2, 2e21), temperature=np.full(2, 300.), thermal_ledger=dict(
            available=True, mobility_temperature_K=np.full(2, 300.),
            mobility_n_m2_V_s=np.full(2, .01), mobility_p_m2_V_s=np.full(2, .005),
            mobility_feedback=False, carrier_reference_temperature_K=300.,
            carrier_reference_VT_V=VT))
    # Uniform density: B(x)-B(-x)=-x makes both conventional currents
    # exactly -q*mu*density*dphi/distance, independent of any audit helper.
    for c, mu, density in [('n', .01, 1e21), ('p', .005, 2e21)]:
        for direction in range(3):
            r['J'+c+'_'+'xyz'[direction]] = np.array([
                -charge*mu*density*sign*.02/1e-7 if direction == axis else 0., 0.])
    return r, axes


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('sign', [-1., 1.])
@pytest.mark.parametrize('charge', [SI_Q, LEGACY_Q, 3e-19])
def test_explicit_charge_matches_independent_prescribed_current(axis, sign, charge):
    result, axes = prescribed(axis, sign, charge)
    saved = deepcopy(result)
    assert audit(result, axes, elementary_charge_C=charge)['valid']
    wrong = audit(result, axes, elementary_charge_C=charge*1.01)
    assert not wrong['valid'] and not wrong['edge_current_valid']
    for key in ('phi', 'n', 'p', 'temperature', 'Jn_x', 'Jn_y', 'Jn_z', 'Jp_x', 'Jp_y', 'Jp_z'):
        np.testing.assert_array_equal(result[key], saved[key])


def test_standalone_default_remains_si():
    result, axes = prescribed(0, 1., SI_Q)
    assert audit(result, axes) == audit(result, axes, elementary_charge_C=SI_Q)
    legacy, axes = prescribed(0, 1., LEGACY_Q)
    assert not audit(legacy, axes)['valid']


@pytest.mark.parametrize('charge', [0., -1., float('nan'), float('inf'), -float('inf'),
    True, False, '1.6e-19', 1.6e-19+0j, [SI_Q], np.array([SI_Q]), None, {}, 10**400])
def test_invalid_charge_rejected(charge):
    result, axes = prescribed(0, 1., SI_Q)
    with pytest.raises(ValueError, match='elementary_charge_C'):
        audit(result, axes, elementary_charge_C=charge)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('model', [0, 1, 2])
@pytest.mark.parametrize('bias', [-.02, .02])
@pytest.mark.parametrize('feedback', [False, True])
def test_explicit_charge_accepts_native_current(axis, model, bias, feedback):
    sim, axes, *_ = setup(axis=axis, model=model, bias=bias, feedback=feedback)
    result = sim.solve()
    assert result['converged']
    q = float(native_constants()['elementary_charge_C'])
    assert audit(result, axes, ['constant', 'arora', 'low_temp'][model], elementary_charge_C=q)['valid']
    bad = deepcopy(result)
    bad['Jn_'+'xyz'[axis]][0] *= 1.01
    assert not audit(bad, axes, ['constant', 'arora', 'low_temp'][model], elementary_charge_C=q)['valid']


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('bias', [-.08, .08])
def test_driver_accepts_bound_native_charge(axis, bias):
    sim, contract = case(axis=axis, bias=bias)
    clock = driver(sim, contract)
    report = clock.step(1e-8)
    assert report['accepted'] and report['mobility_audit']['valid']
    assert clock.accepted_steps == 1 and clock.time_s == 1e-8
    assert not report['complete_device_energy'] and not report['physical_validated']


def records():
    rows=[]
    for axis in range(3):
        for model in range(3):
            for bias in (-.02, .02):
                for feedback in (False, True):
                    sim, axes, *_ = setup(axis=axis, model=model, bias=bias, feedback=feedback)
                    result=sim.solve();assert result['converged']
                    name=['constant','arora','low_temp'][model]
                    default=audit(result,axes,name)
                    try: explicit=audit(result,axes,name,elementary_charge_C=float(native_constants()['elementary_charge_C']))
                    except TypeError as e: explicit={'unsupported':str(e)}
                    rows.append(dict(kind='native',axis=axis,model=model,bias=bias,feedback=feedback,
                        result=result,default=default,explicit=explicit))
    for axis in range(3):
        for bias in (-.08,.08):
            sim,contract=case(axis=axis,bias=bias);clock=driver(sim,contract)
            try: report=clock.step(1e-8)
            except LatticeStepRejected as e: report=e.attempt
            rows.append(dict(kind='driver',axis=axis,bias=bias,report=report,time=clock.time_s,steps=clock.accepted_steps))
    return dict(constants=native_constants(),records=rows)


if __name__=='__main__':
    with open(sys.argv[1],'w') as f:
        json.dump(records(),f,sort_keys=True,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else v.item())
