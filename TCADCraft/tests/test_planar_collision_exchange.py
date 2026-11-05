"""Independent profile-based controls; no physical validation is implied."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from tcad.postprocess.commercial_transient_energy import audit_sentaurus_planar_transient
from test_commercial_transient_energy import sample,ARGS,X,AREA,VOLUME,KB,Q


def parent_auditor():
    path=Path(__file__).resolve().parents[1]/'docs/validation/planar_collision_20261022/before/tcad/postprocess/commercial_transient_energy.py'
    spec=importlib.util.spec_from_file_location('frozen_planar_parent',path)
    mod=importlib.util.module_from_spec(spec)
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(mod)
    finally:sys.dont_write_bytecode=previous
    return mod.audit_sentaurus_planar_transient


def audit(rows,**kwargs):
    return audit_sentaurus_planar_transient(rows,**(ARGS|kwargs))


def old_audit(rows,**kwargs):
    return parent_auditor()(rows,**(ARGS|kwargs))


EXTRA={'step_internal_collision_residual_J','cumulative_internal_collision_residual_J',
       'internal_collision_budget_J','internal_collision_balance_valid'}
def strip(value):
    if isinstance(value,dict):return {k:strip(v) for k,v in value.items() if k not in EXTRA}
    if isinstance(value,list):return [strip(v) for v in value]
    return value


def forged_rows(species,sign,compensation):
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    field=1e5
    mask=np.array([0.,1.,1.,0.])
    band_capacity=np.trapezoid(mask,X)*AREA*Q*1e21
    for row in rows:
        row['electric_field_V_m'][:]=field
        energy=sign*1e-10*row['time_s']
        temperature,capacity={'electrons':('Tn_K',1.5*KB*1e21*VOLUME),
            'holes':('Tp_K',1.5*KB*2e21*VOLUME),'lattice':('Tl_K',VOLUME)}[species]
        row[temperature]+=energy/capacity
        row['collision_power_W'][species]=sign*1e-10
        if compensation=='electrostatic':
            row['electric_field_V_m'][:]=np.sqrt(field**2-2*energy/(ARGS['permittivity_F_m']*VOLUME))
        else:
            row['Ec_eV']-=energy/band_capacity*mask
    return rows


@pytest.mark.parametrize('species',['electrons','holes','lattice'])
@pytest.mark.parametrize('sign',[-1,1])
@pytest.mark.parametrize('compensation',['material_bands','electrostatic'])
def test_profile_storage_compensation_cannot_authorize_collision(species,sign,compensation):
    rows=forged_rows(species,sign,compensation);before=deepcopy(rows)
    old=old_audit(rows);new=audit(rows)
    assert old['accepted']
    assert all(new[k] for k in ('full_storage_balance_valid','reservoir_balances_valid','particle_balance_valid','current_balance_valid'))
    assert not new['accepted'] and not new['internal_collision_balance_valid']
    assert not new['complete_device_energy'] and not new['physical_validated']
    for a,b in zip(rows,before):
        for k,v in a.items():
            if isinstance(v,np.ndarray):assert np.array_equal(v,b[k])
            else:assert v==b[k]


@pytest.mark.parametrize('sign',[-1,1])
def test_joule_compensation_with_large_relative_budget_still_fails(sign):
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    for row in rows[1:]:
        row['collision_power_W']['electrons']=sign*100.
        row['joule_power_W']['electrons']=-sign*100.
    assert old_audit(rows,energy_rtol=1.)['accepted']
    r=audit(rows,energy_rtol=1.)
    assert not r['accepted']
    assert all(c['internal_collision_budget_J']==ARGS['energy_atol_J'] for c in r['checkpoints'])


@pytest.mark.parametrize('sign',[-1,1])
def test_final_zero_cannot_hide_failed_intervals(sign):
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    for i,power in ((1,sign*1e-10),(2,-sign*5e-11)):
        rows[i]['collision_power_W']['electrons']=power
        rows[i]['joule_power_W']['electrons']=-power
    assert old_audit(rows)['accepted']
    r=audit(rows)
    assert abs(r['checkpoints'][-1]['cumulative_internal_collision_residual_J'])<ARGS['energy_atol_J']
    assert all(not c['internal_collision_balance_valid'] for c in r['checkpoints'])
    assert not r['accepted']


@pytest.mark.parametrize('sign',[-1,1])
def test_small_steps_cannot_exceed_prefix_budget(sign):
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    for i,row in enumerate(rows[1:],1):
        power=sign*.75*ARGS['energy_atol_J']/(row['time_s']-rows[i-1]['time_s'])
        row['collision_power_W']['holes']=power
        row['joule_power_W']['holes']=-power
    r=audit(rows)
    assert r['checkpoints'][0]['internal_collision_balance_valid']
    assert all(abs(c['step_internal_collision_residual_J'])<ARGS['energy_atol_J'] for c in r['checkpoints'])
    assert not r['accepted'] and not r['checkpoints'][-1]['internal_collision_balance_valid']


@pytest.mark.parametrize('sign',[-1,1])
def test_conservative_exchange_preserves_every_old_report_field(sign):
    rows=[sample(t) for t in (0.,1e-12,3e-12)]
    for row in rows:
        energy=sign*1e-10*row['time_s']
        row['Tn_K']+=energy/(1.5*KB*1e21*VOLUME)
        row['Tl_K']-=energy/VOLUME
        row['collision_power_W'].update(electrons=sign*1e-10,lattice=-sign*1e-10)
    r=audit(rows)
    assert r['accepted'] and r['internal_collision_balance_valid']
    assert strip(r)==old_audit(rows)


def test_exact_zero_budget_and_initial_state_has_no_interval():
    rows=[sample(t) for t in (0.,1e-12)]
    rows[0]['collision_power_W']['electrons']=1e20
    r=audit(rows,energy_atol_J=0.,energy_rtol=0.)
    assert r['accepted'] and strip(r)==old_audit(rows,energy_atol_J=0.,energy_rtol=0.)
    c=r['checkpoints'][0]
    assert c['step_internal_collision_residual_J']==c['cumulative_internal_collision_residual_J']==c['internal_collision_budget_J']==0.
