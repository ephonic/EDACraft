"""Manufactured independent exchange controls, not physical validation."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from test_commercial_volume_energy import fixture,audit


def parent_auditor():
    path=Path(__file__).resolve().parents[1]/'docs/validation/collision_exchange_20261022/before/tcad/postprocess/commercial_volume_energy.py'
    spec=importlib.util.spec_from_file_location('frozen_collision_parent',path)
    mod=importlib.util.module_from_spec(spec)
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(mod)
    finally:sys.dont_write_bytecode=previous
    return mod.audit_sentaurus_mesh_integrals


def old_audit(rows,**kw):
    # Keep the fixture's exact original options without duplicating its constants.
    options={}
    def capture(samples,**kwargs):
        options.update(kwargs)
    previous=audit.__globals__['audit_sentaurus_mesh_integrals']
    audit.__globals__['audit_sentaurus_mesh_integrals']=capture
    try:audit(rows,**kw)
    finally:audit.__globals__['audit_sentaurus_mesh_integrals']=previous
    return parent_auditor()(rows,**options)


def forged_rows(species,sign,compensation):
    rows=fixture();total=0.
    for i,row in enumerate(rows[1:],1):
        power=sign*1e-10
        row['collision_power_W'][species]=power
        total+=(row['time_s']-rows[i-1]['time_s'])*power
        row['storage_J'][species]+=total
        row['storage_J'][compensation]-=total
    return rows


@pytest.mark.parametrize('species',['electrons','holes','lattice'])
@pytest.mark.parametrize('sign',[-1,1])
@pytest.mark.parametrize('compensation',['material_bands','electrostatic'])
def test_fictitious_storage_cannot_hide_nonconservative_collision(species,sign,compensation):
    rows=forged_rows(species,sign,compensation);before=deepcopy(rows)
    old=old_audit(rows);new=audit(rows)
    assert old['accepted']
    assert all(new[k] for k in ('full_storage_balance_valid','reservoir_balances_valid','particle_balance_valid','current_balance_valid'))
    assert not new['accepted'] and not new['internal_collision_balance_valid']
    assert rows==before


@pytest.mark.parametrize('sign',[-1,1])
def test_joule_compensation_and_relative_turnover_do_not_authorize_exchange(sign):
    rows=fixture()
    for row in rows[1:]:
        row['collision_power_W']['electrons']=sign*100.
        row['joule_power_W']['electrons']=-sign*100.
    assert old_audit(rows,energy_rtol=1.)['accepted']
    new=audit(rows,energy_rtol=1.)
    assert not new['accepted']
    assert all(c['internal_collision_budget_J']==1e-28 for c in new['checkpoints'])


@pytest.mark.parametrize('sign',[-1,1])
def test_canceling_later_interval_cannot_erase_earlier_failure(sign):
    rows=fixture()
    for i,power in ((1,sign*1e-10),(2,-sign*5e-11)):
        rows[i]['collision_power_W']['electrons']=power
        rows[i]['joule_power_W']['electrons']=-power
    assert old_audit(rows)['accepted']
    r=audit(rows)
    assert abs(r['checkpoints'][-1]['cumulative_internal_collision_residual_J'])<1e-28
    assert all(not c['internal_collision_balance_valid'] for c in r['checkpoints'])
    assert not r['accepted']


@pytest.mark.parametrize('sign',[-1,1])
def test_small_step_bias_cannot_accumulate_past_original_budget(sign):
    rows=fixture()
    for i,row in enumerate(rows[1:],1):
        p=sign*.75e-28/(row['time_s']-rows[i-1]['time_s'])
        row['collision_power_W']['electrons']=p
        row['joule_power_W']['electrons']=-p
    r=audit(rows)
    assert r['checkpoints'][0]['internal_collision_balance_valid']
    assert all(abs(c['step_internal_collision_residual_J'])<1e-28 for c in r['checkpoints'])
    assert not r['accepted'] and not r['checkpoints'][-1]['internal_collision_balance_valid']


@pytest.mark.parametrize('power',[1e-10,-1e-10])
def test_conservative_electron_lattice_exchange_remains_accepted(power):
    rows=fixture();amount=0.
    for i,row in enumerate(rows[1:],1):
        row['collision_power_W'].update(electrons=power,lattice=-power)
        amount+=(row['time_s']-rows[i-1]['time_s'])*power
        row['storage_J']['electrons']+=amount
        row['storage_J']['lattice']-=amount
    assert old_audit(rows)['accepted']
    r=audit(rows)
    assert r['accepted'] and r['internal_collision_balance_valid']


def test_zero_exchange_and_zero_budget_are_exact():
    rows=fixture()
    for row in rows:
        row['storage_J'].update(electrons=4e-18,holes=5e-18,lattice=6e-18)
        for port in row['ports'].values():
            port['inward_heat_W']={s:0. for s in ('electrons','holes','lattice')}
    r=audit(rows,energy_atol_J=0.,energy_rtol=0.)
    assert r['accepted']
    for c in r['checkpoints']:
        assert c['internal_collision_budget_J']==0.
        assert c['step_internal_collision_residual_J']==0.
        assert c['cumulative_internal_collision_residual_J']==0.
